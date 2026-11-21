import pytest

from app.integrations import connector_runtime
from app.models import ConnectorDefinition, DataAsset, DataRecord, DataSource, Evidence
from test_main import app_module, make_test_client


@pytest.fixture
def execution_api(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    project = client.post(
        "/projects",
        json={"name": "真实连接器执行项目", "city": "杭州", "artist_name": "测试艺人"},
    ).json()["data"]
    monkeypatch.setenv(
        "ANALYSIS_ALLOWED_ORIGINS",
        "https://api.example.org,https://mcp.example.org",
    )
    monkeypatch.setattr(
        "app.integrations.live_reads.validate_public_host",
        lambda url: None,
    )
    yield client, sessions, project
    connector_runtime.SKILL_RUNNER_REGISTRY.clear()
    app_module.app.dependency_overrides.clear()


def create_source(client, project, connector_key, **overrides):
    payload = {
        "name": f"{connector_key}-{project['id']}",
        "source_kind": "mcp" if "mcp" in connector_key else "api",
        "connector_key": connector_key,
        "status": "active",
        "credential_ref": f"{connector_key}_prod",
        "scope_config": {
            "endpoint": (
                "https://mcp.example.org/mcp"
                if "mcp" in connector_key
                else "https://api.example.org/read"
            ),
            "read_only": True,
            "project_ids": [project["id"]],
            "tool": "fetch",
            "url_argument": "url",
        },
    }
    payload.update(overrides)
    return client.post("/data-sources", json=payload).json()["data"]


def create_job(client, project, source, parameters=None):
    return client.post("/external-data/jobs", json={
        "project_id": project["id"],
        "source_type": source["source_kind"],
        "provider": source["connector_key"],
        "query": "采集公开依据",
        "purpose": "connector_execution",
        "parameters": {
            "data_source_id": source["id"],
            **(parameters or {}),
        },
    }).json()["data"]


@pytest.mark.parametrize("connector_key", ["agent_api", "custom_rest_api"])
def test_active_rest_connectors_call_real_adapter_and_write_idempotently(
    execution_api, monkeypatch, connector_key,
):
    client, sessions, project = execution_api
    source = create_source(client, project, connector_key)
    monkeypatch.setenv(
        f"DATA_CONNECTOR_SECRET_{connector_key.upper()}_PROD",
        "private-token",
    )
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"capacity": 1800, "secret": "must-not-persist"}, {}

    monkeypatch.setattr("app.integrations.live_reads.request_json", request)
    asset_ids = []
    for _ in range(2):
        job = create_job(client, project, source)
        result = client.post(f"/external-data/jobs/{job['id']}/run").json()["data"]
        assert result["status"] == "completed"
        assert result["result"]["network_called"] is True
        assert result["result"]["requires_human_verification"] is True
        assert "private-token" not in str(result)
        assert "must-not-persist" not in str(result)
        asset_ids.append(result["result"]["asset"]["id"])

    assert asset_ids[0] == asset_ids[1]
    assert calls[0][0:2] == ("GET", "https://api.example.org/read")
    assert calls[0][2]["headers"]["Authorization"] == "Bearer private-token"
    with sessions() as db:
        assert db.query(DataAsset).filter_by(data_source_id=source["id"]).count() == 1
        assert db.query(DataRecord).count() == 1
        evidence = db.query(Evidence).filter_by(project_id=project["id"]).one()
        assert evidence.status == "needs_review"
        assert evidence.meta["requires_human_verification"] is True
        assert "must-not-persist" not in str(evidence.meta)


@pytest.mark.parametrize("connector_key", ["mcp_web", "custom_mcp"])
def test_active_mcp_connectors_use_parameters_url_and_write_evidence(
    execution_api, monkeypatch, connector_key,
):
    client, sessions, project = execution_api
    source = create_source(client, project, connector_key)
    monkeypatch.setenv(
        f"DATA_CONNECTOR_SECRET_{connector_key.upper()}_PROD",
        "mcp-private-token",
    )
    calls = []

    def request(method, url, **kwargs):
        body = kwargs["json"]
        calls.append(body)
        if body["method"] == "initialize":
            return {"jsonrpc": "2.0", "id": body["id"], "result": {
                "protocolVersion": "2025-03-26",
            }}, {"Mcp-Session-Id": "session-1"}
        if body["method"] == "notifications/initialized":
            return None, {}
        if body["method"] == "tools/list":
            return {"jsonrpc": "2.0", "id": body["id"], "result": {"tools": [{
                "name": "fetch",
                "annotations": {"readOnlyHint": True},
            }]}}, {}
        assert body["params"]["arguments"]["url"] == "https://news.example.org/show"
        return {"jsonrpc": "2.0", "id": body["id"], "result": {
            "content": [{"type": "text", "text": "公开活动资料"}],
        }}, {}

    monkeypatch.setattr("app.integrations.live_reads.request_json", request)
    job = create_job(
        client,
        project,
        source,
        {"url": "https://news.example.org/show"},
    )
    result = client.post(f"/external-data/jobs/{job['id']}/run").json()["data"]
    assert result["status"] == "completed"
    assert result["result"]["asset"]["records"][0]["value_json"]["text"] == "公开活动资料"
    assert [call["method"] for call in calls] == [
        "initialize", "notifications/initialized", "tools/list", "tools/call",
    ]
    with sessions() as db:
        assert db.query(Evidence).filter_by(
            project_id=project["id"],
            status="needs_review",
        ).count() == 1


def test_skill_execution_uses_only_registered_runner_and_is_idempotent(
    execution_api,
):
    client, sessions, project = execution_api
    with sessions() as db:
        definition = ConnectorDefinition(
            key="custom_skill",
            name="自定义 Skill",
            source_kind="skill",
            domain="general",
            builtin=1,
            auth_type="none",
            adapter_key="custom_skill",
            availability="runner_required",
            enabled=1,
        )
        db.add(definition)
        db.flush()
        source = DataSource(
            tenant_id=project["tenant_id"],
            name="画像归纳 Skill",
            source_kind="skill",
            connector_key="custom_skill",
            definition_id=definition.id,
            status="active",
            scope_config={"project_ids": [project["id"]]},
        )
        db.add(source)
        db.commit()
        source_id = source.id

    calls = []

    def runner(**kwargs):
        calls.append(kwargs)
        return {"summary": "画像待人工核验", "confidence": 70}

    connector_runtime.register_skill_runner("custom_skill", runner)
    asset_ids = []
    for _ in range(2):
        source_data = {
            "id": source_id,
            "source_kind": "skill",
            "connector_key": "custom_skill",
        }
        job = create_job(client, project, source_data, {"topic": "艺人画像"})
        result = client.post(f"/external-data/jobs/{job['id']}/run").json()["data"]
        assert result["status"] == "completed"
        asset_ids.append(result["result"]["asset"]["id"])

    assert asset_ids[0] == asset_ids[1]
    assert len(calls) == 2
    assert all(call["connection_test"] is False for call in calls)
    with sessions() as db:
        assert db.query(DataAsset).filter_by(data_source_id=source_id).count() == 1
        assert db.query(DataRecord).count() == 1
        assert db.query(Evidence).filter_by(
            project_id=project["id"],
            source=f"connector-source:{source_id}",
            status="needs_review",
        ).count() == 1


@pytest.mark.parametrize(
    ("case", "expected_reason"),
    [
        ("missing_source", "Data source is required"),
        ("inactive", "Data source is disabled"),
        ("missing_credential", "Connector credential is not configured"),
        ("invalid_endpoint", "Connector endpoint is invalid"),
        ("missing_runner", "Skill runner is not registered"),
    ],
)
def test_execution_preconditions_block_without_network(
    execution_api, monkeypatch, case, expected_reason,
):
    client, sessions, project = execution_api
    monkeypatch.setattr(
        "app.integrations.live_reads.request_json",
        lambda *args, **kwargs: pytest.fail("network must not be called"),
    )
    if case == "missing_source":
        job = client.post("/external-data/jobs", json={
            "project_id": project["id"],
            "source_type": "api",
            "provider": "agent_api",
            "query": "采集",
            "parameters": {},
        }).json()["data"]
    elif case == "missing_runner":
        with sessions() as db:
            definition = ConnectorDefinition(
                key="custom_skill",
                name="无执行器 Skill",
                source_kind="skill",
                domain="general",
                builtin=1,
                auth_type="none",
                adapter_key="custom_skill",
                availability="runner_required",
                enabled=1,
            )
            db.add(definition)
            db.flush()
            row = DataSource(
                tenant_id=project["tenant_id"],
                name="无执行器 Skill",
                source_kind="skill",
                connector_key="custom_skill",
                definition_id=definition.id,
                status="active",
            )
            db.add(row)
            db.commit()
            source = {"id": row.id, "source_kind": "skill", "connector_key": "custom_skill"}
        job = create_job(client, project, source)
    else:
        overrides = {}
        if case == "inactive":
            overrides["status"] = "disabled"
        if case == "invalid_endpoint":
            overrides["scope_config"] = {
                "endpoint": "http://127.0.0.1/private",
                "read_only": True,
            }
        source = create_source(client, project, "agent_api", **overrides)
        if case != "missing_credential":
            monkeypatch.setenv("DATA_CONNECTOR_SECRET_AGENT_API_PROD", "configured")
        job = create_job(client, project, source)

    result = client.post(f"/external-data/jobs/{job['id']}/run").json()["data"]
    assert result["status"] == "blocked"
    assert result["result"]["network_called"] is False
    assert result["result"]["reason"] == expected_reason


def test_execution_exception_is_redacted_and_creates_no_rows(
    execution_api, monkeypatch,
):
    client, sessions, project = execution_api
    source = create_source(client, project, "agent_api")
    monkeypatch.setenv("DATA_CONNECTOR_SECRET_AGENT_API_PROD", "top-secret")
    monkeypatch.setattr(
        "app.integrations.live_reads.request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("Authorization Bearer top-secret failed")
        ),
    )
    job = create_job(client, project, source)
    result = client.post(f"/external-data/jobs/{job['id']}/run").json()["data"]
    assert result["status"] == "failed"
    assert result["result"]["network_called"] is True
    assert "top-secret" not in str(result)
    assert "Authorization" not in str(result)
    with sessions() as db:
        assert db.query(DataAsset).count() == 0
        assert db.query(DataRecord).count() == 0
        assert db.query(Evidence).filter_by(
            project_id=project["id"],
            source=f"connector-source:{source['id']}",
        ).count() == 0


def test_execution_without_project_is_blocked_before_network(
    execution_api, monkeypatch,
):
    client, _, project = execution_api
    source = create_source(client, project, "agent_api")
    monkeypatch.setenv("DATA_CONNECTOR_SECRET_AGENT_API_PROD", "configured")
    monkeypatch.setattr(
        "app.integrations.live_reads.request_json",
        lambda *args, **kwargs: pytest.fail("network must not be called"),
    )
    job = client.post("/external-data/jobs", json={
        "source_type": "api",
        "provider": "agent_api",
        "query": "采集",
        "parameters": {"data_source_id": source["id"]},
    }).json()["data"]
    result = client.post(f"/external-data/jobs/{job['id']}/run").json()["data"]
    assert result["status"] == "blocked"
    assert result["result"] == {
        "reason": "Project is required",
        "network_called": False,
    }
