import json

import pytest

from test_main import app_module, make_test_client
from test_ai_user_isolation import login
from app.models import DataSource, Evidence, Project, Tenant


@pytest.fixture
def live(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    headers, identity = login(client, monkeypatch, "b_user")
    with sessions() as db:
        project = Project(name="实时研判项目", city="杭州", tenant_id=identity["current_tenant"]["id"],
                          created_by=identity["user"]["id"])
        db.add(project)
        db.flush()
        api = DataSource(tenant_id=project.tenant_id, name="场馆接口", source_kind="api",
                         connector_key="agent_api", status="active", credential_ref="VENUE",
                         scope_config={"endpoint": "https://api.example.org/venues", "read_only": True,
                                       "project_ids": [project.id], "roles": ["B"],
                                       "query": {"city": "{city}"}})
        mcp = DataSource(tenant_id=project.tenant_id, name="公开资料网页", source_kind="mcp",
                         connector_key="mcp_web", status="active",
                         scope_config={"endpoint": "https://mcp.example.org/mcp", "tool": "fetch",
                                       "url_argument": "url", "read_only": True,
                                       "project_ids": [project.id], "roles": ["B"]})
        db.add_all([api, mcp])
        db.commit()
        ids = project.id, api.id, mcp.id
    monkeypatch.setenv("ANALYSIS_ALLOWED_ORIGINS", "https://api.example.org,https://mcp.example.org")
    monkeypatch.setenv("DATA_CONNECTOR_SECRET_VENUE", "private-key")
    monkeypatch.setenv("LLAMA_SERVER_URL", "")
    yield client, sessions, headers, ids
    app_module.app.dependency_overrides.clear()


def test_agent_lists_only_authorized_sources_and_reads_api_into_pending_evidence(live, monkeypatch):
    from app.integrations import live_reads
    client, sessions, headers, (pid, api, _) = live
    monkeypatch.setattr(live_reads, "validate_public_host", lambda url: None)
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"capacity": 1800, "unit": "人", "token": "never-show"}, {}

    monkeypatch.setattr(live_reads, "request_json", request)
    data = client.get(f"/agent/sources?project_id={pid}", headers=headers).json()["data"]
    assert len(data) == 2
    assert "private-key" not in str(data) and "VENUE" not in str(data)
    payload = {"project_id": pid, "message": "场馆容量依据是什么", "reads": [{"source_id": api}]}
    result = client.post("/agent/chat", headers=headers, json=payload)
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["readings"][0]["status"] == "completed"
    assert data["readings"][0]["requires_human_verification"]
    assert "1800" in data["answer"] and "never-show" not in result.text
    assert calls[0][0] == "GET"
    assert calls[0][2]["params"] == {"city": "杭州"}
    assert calls[0][2]["headers"]["Authorization"] == "Bearer private-key"
    repeat = client.post("/agent/chat", headers=headers, json=payload).json()["data"]
    assert repeat["readings"][0]["evidence_id"] == data["readings"][0]["evidence_id"]
    with sessions() as db:
        evidence = db.query(Evidence).filter(Evidence.project_id == pid).one()
        assert evidence.status == "needs_review"
        assert evidence.meta["captured_at"] and evidence.meta["content_hash"]
        assert "never-show" not in str(evidence.meta)


def test_mcp_uses_handshake_session_tool_catalog_and_real_call(live, monkeypatch):
    from app.integrations import live_reads
    client, _, headers, (pid, _, mcp) = live
    monkeypatch.setattr(live_reads, "validate_public_host", lambda url: None)
    calls = []

    def request(method, url, **kwargs):
        body = kwargs["json"]
        calls.append(body)
        if body["method"] == "initialize":
            return {"jsonrpc": "2.0", "id": body["id"], "result": {
                "protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                "serverInfo": {"name": "test", "version": "1"}}}, {"Mcp-Session-Id": "session1"}
        assert kwargs["headers"]["Mcp-Session-Id"] == "session1"
        if body["method"] == "notifications/initialized":
            return None, {}
        if body["method"] == "tools/list":
            return {"jsonrpc": "2.0", "id": body["id"], "result": {"tools": [
                {"name": "fetch", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}}
            ]}}, {}
        assert body["params"] == {"name": "fetch", "arguments": {"url": "https://news.example.org/show"}}
        return {"jsonrpc": "2.0", "id": body["id"], "result": {
            "content": [{"type": "text", "text": "官方活动介绍：档期待确认"}]}}, {}

    monkeypatch.setattr(live_reads, "request_json", request)
    response = client.post("/agent/chat", headers=headers, json={
        "project_id": pid, "message": "查看公开资料",
        "reads": [{"source_id": mcp, "url": "https://news.example.org/show"}],
    })
    assert response.status_code == 200, response.text
    reading = response.json()["data"]["readings"][0]
    assert reading["status"] == "completed" and "官方活动介绍" in reading["excerpt"]
    assert [c["method"] for c in calls] == ["initialize", "notifications/initialized", "tools/list", "tools/call"]


def test_live_reads_require_real_identity_project_and_source_scope(live, monkeypatch):
    client, sessions, headers, (pid, api, _) = live
    payload = {"project_id": pid, "message": "读取", "reads": [{"source_id": api}]}
    assert client.post("/agent/chat", json=payload).status_code == 401
    root, _ = login(client, monkeypatch, "root")
    assert client.post("/agent/chat", headers=root, json=payload).status_code == 403
    brand, _ = login(client, monkeypatch, "brand_user")
    assert client.post("/agent/chat", headers=brand, json=payload).status_code == 403
    with sessions() as db:
        foreign = Tenant(name="其他空间")
        db.add(foreign)
        db.flush()
        source = DataSource(tenant_id=foreign.id, name="私有来源", source_kind="api", connector_key="agent_api")
        db.add(source)
        db.commit()
        alien = source.id
    assert client.post("/agent/chat", headers=headers, json={**payload, "reads": [{"source_id": alien}]}).status_code == 403
    assert client.get(f"/agent/sources?project_id={pid}").status_code == 401


def test_failed_reads_are_explicit_and_do_not_create_evidence(live, monkeypatch):
    from app.integrations import live_reads
    client, sessions, headers, (pid, api, _) = live
    monkeypatch.setattr(live_reads, "validate_public_host", lambda url: None)
    monkeypatch.setattr(live_reads, "request_json", lambda *a, **kw: (_ for _ in ()).throw(ValueError("secret")))
    response = client.post("/agent/chat", headers=headers, json={
        "project_id": pid, "message": "读取", "reads": [{"source_id": api}]})
    reading = response.json()["data"]["readings"][0]
    assert reading["status"] == "failed" and "secret" not in response.text
    with sessions() as db:
        assert db.query(Evidence).filter(Evidence.project_id == pid).count() == 0


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://169.254.169.254/latest",
                               "file:///etc/passwd", "https://user:password@example.org"])
def test_public_web_target_rejects_local_and_credential_urls(url):
    from app.integrations.live_reads import validate_public_host
    with pytest.raises(ValueError):
        validate_public_host(url)


def test_streamable_http_reads_utf8_sse_response_and_ignores_notifications(monkeypatch):
    from app.integrations import live_reads
    class Response:
        status_code = 200
        headers = {"Content-Type": "text/event-stream"}
        def raise_for_status(self): pass
        def iter_content(self, chunk_size):
            # Open SSE streams must deliver small events without filling a 4KiB buffer.
            assert chunk_size == 1
            raw = ('data: {"jsonrpc":"2.0","method":"ping"}\n\n'
                   'data: {"jsonrpc":"2.0","id":4,"result":{"content":[{"type":"text","text":"中文资料"}]}}\n\n').encode()
            yield raw[:50]
            yield raw[50:]
        def close(self): pass
    class Session:
        trust_env = False
        def request(self, *a, **kw):
            assert kw["allow_redirects"] is False and kw["stream"] is True
            return Response()
        def close(self): pass
    monkeypatch.setattr(live_reads.requests, "Session", Session)
    result, _ = live_reads.request_json("POST", "https://mcp.example.org/mcp", json={"id": 4})
    assert result["result"]["content"][0]["text"] == "中文资料"


def test_unconfigured_or_write_sources_are_not_executed(live, monkeypatch):
    from app.integrations import live_reads
    client, sessions, headers, (pid, api, _) = live
    with sessions() as db:
        source = db.get(DataSource, api)
        source.scope_config = {**source.scope_config, "read_only": False}
        db.commit()
    monkeypatch.setattr(live_reads, "request_json", lambda *a, **kw: pytest.fail("must not call network"))
    response = client.post("/agent/chat", headers=headers, json={
        "project_id": pid, "message": "读取", "reads": [{"source_id": api}]})
    assert response.json()["data"]["readings"][0]["status"] == "blocked"


def test_ai_synthesis_uses_evidence_as_untrusted_and_disables_thinking(live, monkeypatch):
    from app.integrations import live_reads
    from app.services import live_analysis
    client, _, headers, (pid, api, _) = live
    monkeypatch.setattr(live_reads, "validate_public_host", lambda url: None)
    monkeypatch.setattr(live_reads, "request_json", lambda *a, **kw: ({"capacity": 1800}, {}))
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1/chat/completions")
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": "<think>hidden</think>依据 [1]，容量待场馆核验。"}}]}
    def post(url, **kwargs):
        assert kwargs["json"]["chat_template_kwargs"]["enable_thinking"] is False
        assert "不可信" in kwargs["json"]["messages"][0]["content"]
        assert "1800" in kwargs["json"]["messages"][1]["content"]
        assert kwargs["timeout"] == 300
        return Response()
    monkeypatch.setattr(live_analysis.requests, "post", post)
    response = client.post("/agent/chat", headers=headers, json={
        "project_id": pid, "message": "评估容量", "reads": [{"source_id": api}], "use_ai": True})
    assert response.json()["data"]["answer_mode"] == "ai"
    assert "<think>" not in response.text and "hidden" not in response.text


def test_analysis_job_keeps_live_evidence_and_requires_auth_on_read(live, monkeypatch):
    from app.integrations import live_reads
    from app.models import ProjectVersion
    client, sessions, headers, (pid, api, _) = live
    monkeypatch.setattr(live_reads, "request_json", lambda *a, **kw: ({"capacity": 1800}, {}))
    with sessions() as db:
        version = ProjectVersion(project_id=pid, version_no=1, finance_result={}, input_snapshot={})
        db.add(version)
        db.commit()
        vid = version.id
    response = client.post(f"/projects/{pid}/analysis-jobs", headers=headers, json={
        "version_id": vid, "purpose": "场馆依据", "reads": [{"source_id": api}]})
    assert response.status_code == 200, response.text
    job = response.json()["data"]
    assert job["result"]["live_readings"][0]["evidence_id"]
    assert job["result"]["requires_human_verification"]
    assert client.get(f"/projects/{pid}/analysis-jobs/{job['id']}").status_code == 401
    assert client.get(f"/projects/{pid}/analysis-jobs/{job['id']}", headers=headers).status_code == 200


def test_missing_credentials_and_disallowed_endpoint_do_not_call_network(live, monkeypatch):
    from app.integrations import live_reads
    client, _, headers, (pid, api, _) = live
    monkeypatch.delenv("DATA_CONNECTOR_SECRET_VENUE")
    monkeypatch.setattr(live_reads, "request_json", lambda *a, **kw: pytest.fail("must not call network"))
    assert client.post("/agent/chat", headers=headers, json={
        "project_id": pid, "message": "读取", "reads": [{"source_id": api}]
    }).json()["data"]["readings"][0]["status"] == "blocked"
    with pytest.raises(ValueError):
        live_reads.validate_endpoint("https://unconfigured.example.org/private")


def test_ai_failure_keeps_source_evidence_and_returns_clear_fallback(live, monkeypatch):
    client, _, headers, (pid, _, _) = live
    data = client.post("/agent/chat", headers=headers, json={
        "project_id": pid, "message": "研判", "use_ai": True
    }).json()["data"]
    assert data["answer_mode"] == "rules" and "待配置" in data["warning"]


@pytest.mark.parametrize("status,size", [(302, 10), (200, 262145)])
def test_http_adapter_rejects_redirects_and_oversized_responses(monkeypatch, status, size):
    from app.integrations import live_reads
    class Response:
        status_code = status
        headers = {"Content-Type": "application/json"}
        def raise_for_status(self): pass
        def iter_content(self, chunk_size):
            yield b"x" * size
        def close(self): pass
    class Session:
        def request(self, *a, **kw): return Response()
        def close(self): pass
    monkeypatch.setattr(live_reads.requests, "Session", Session)
    with pytest.raises(ValueError):
        live_reads.request_json("GET", "https://api.example.org/venues")
