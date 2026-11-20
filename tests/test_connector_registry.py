import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.integrations import connector_runtime
from app.models import DataSource
from app.services.connector_registry import (
    activate_registration,
    begin_test,
    configuration_hash,
    finish_test,
    public_config_complete,
    registration_credential_status,
    registration_status,
    state_before_test,
)
from app.services.serializers import serialize_data_source
from test_ai_user_isolation import login
from test_main import app_module, make_test_client


def definition(**overrides):
    values = {
        "auth_type": "api_key",
        "availability": "available",
        "adapter_key": "amap",
        "config_schema": {"fields": [
            {"name": "operation", "required": True},
        ]},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def source(**overrides):
    values = {
        "status": "pending_config",
        "credential_ref": "",
        "scope_config": {},
        "schedule_config": {},
        "last_test_result": {},
        "last_test_at": None,
        "activated_at": None,
    }
    values.update(overrides)
    return DataSource(**values)


@pytest.mark.parametrize(
    ("availability", "configured", "credential", "expected"),
    [
        ("adapter_required", True, True, "pending_config"),
        ("available", False, False, "pending_config"),
        ("available", True, False, "pending_credentials"),
        ("available", True, True, "pending_test"),
    ],
)
def test_registration_state_before_test(
    monkeypatch, availability, configured, credential, expected,
):
    item = definition(availability=availability)
    registration = source(
        credential_ref="AMAP_PROD" if credential else "",
        scope_config={"operation": "venue_search"} if configured else {},
    )
    monkeypatch.setattr(
        "app.services.connector_registry.connector_credential_is_configured",
        lambda *_: credential,
    )
    assert state_before_test(item, registration) == expected


def test_public_config_and_none_auth_do_not_require_credentials():
    item = definition(auth_type="none")
    registration = source(scope_config={"operation": "venue_search"})
    assert public_config_complete(item, registration.scope_config)
    assert registration_credential_status(registration, item) == "not_required"
    assert state_before_test(item, registration) == "pending_test"


def test_only_successful_current_test_can_activate(monkeypatch):
    item = definition()
    registration = source(
        credential_ref="AMAP_PROD",
        scope_config={"operation": "venue_search"},
    )
    monkeypatch.setattr(
        "app.services.connector_registry.connector_credential_is_configured",
        lambda *_: True,
    )
    begin_test(registration, item)
    finish_test(
        registration,
        success=True,
        summary={"code": "connected", "message": "连接测试通过", "capabilities": ["read"]},
    )
    assert registration.status == "ready"
    activate_registration(registration)
    assert registration.status == "active"
    assert registration.activated_at is not None

    registration.scope_config = {"operation": "changed"}
    with pytest.raises(ValueError, match="successful connection test"):
        activate_registration(registration)


def test_failed_test_and_blocked_definition_cannot_activate(monkeypatch):
    registration = source(
        credential_ref="AMAP_PROD",
        scope_config={"operation": "venue_search"},
    )
    monkeypatch.setattr(
        "app.services.connector_registry.connector_credential_is_configured",
        lambda *_: True,
    )
    finish_test(
        registration,
        success=False,
        summary={"code": "connection_failed", "message": "连接测试失败"},
    )
    assert registration.status == "error"
    with pytest.raises(ValueError, match="successful connection test"):
        activate_registration(registration)
    with pytest.raises(ValueError):
        begin_test(registration, definition(availability="contract_required"))


def test_registration_status_and_hash_are_stable(monkeypatch):
    item = definition()
    registration = source(
        credential_ref="AMAP_PROD",
        scope_config={"operation": "venue_search", "project_ids": [2, 1]},
        schedule_config={"cron": "0 1 * * *"},
    )
    initial = configuration_hash(registration)
    registration.scope_config = {
        "project_ids": [2, 1],
        "operation": "venue_search",
    }
    assert configuration_hash(registration) == initial
    assert registration_status(item, None) == "unregistered"
    registration.status = "disabled"
    assert registration_status(item, registration) == "disabled"
    monkeypatch.setattr(
        "app.services.connector_registry.connector_credential_is_configured",
        lambda *_: True,
    )
    registration.status = "pending_config"
    assert registration_status(item, registration) == "pending_test"


def test_missing_credential_fails_before_network(monkeypatch):
    registration = source(
        connector_key="amap",
        credential_ref="AMAP_PROD",
        scope_config={"operation": "venue_search"},
    )
    item = definition(key="amap", capabilities=["read"])
    monkeypatch.delenv("DATA_CONNECTOR_SECRET_AMAP_PROD", raising=False)
    monkeypatch.setattr(
        connector_runtime.requests,
        "get",
        lambda *args, **kwargs: pytest.fail("network called"),
    )
    assert connector_runtime.test_registration(registration, item) == {
        "ok": False,
        "code": "credential_missing",
        "message": "鉴权尚未配置",
        "capabilities": [],
    }


def test_unknown_adapter_and_unregistered_skill_are_never_loaded():
    assert connector_runtime.connector_adapter("some.module:run") is None
    result = connector_runtime.test_registration(
        source(scope_config={}),
        definition(
            key="market_research_skill",
            source_kind="skill",
            auth_type="none",
            adapter_key="market_research_skill",
            availability="runner_required",
            capabilities=["read"],
        ),
    )
    assert result["code"] == "runner_missing"


@pytest.fixture
def registry_api(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    root_headers, _ = login(client, monkeypatch, "root")
    business_headers, _ = login(client, monkeypatch, "b_user")
    yield client, sessions, root_headers, business_headers
    app_module.app.dependency_overrides.clear()


def test_catalog_requires_login_and_lists_complete_catalog(registry_api):
    client, _, root_headers, business_headers = registry_api
    assert client.get("/connector-definitions").status_code == 401
    assert client.get("/connector-definitions", headers=business_headers).status_code == 403
    response = client.get("/connector-definitions", headers=root_headers)
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 61
    assert next(row for row in rows if row["key"] == "amap")["registration"] is None


def test_only_root_can_create_custom_and_builtin_cannot_be_modified(registry_api):
    client, _, root_headers, business_headers = registry_api
    payload = {
        "key": "venue_read_api",
        "name": "场馆只读接口",
        "source_kind": "api",
        "domain": "venue",
        "auth_type": "bearer",
        "config_schema": {"fields": [
            {"name": "endpoint", "type": "url", "required": True},
        ]},
        "capabilities": ["read"],
    }
    assert client.post(
        "/connector-definitions/custom",
        headers=business_headers,
        json=payload,
    ).status_code == 403
    created = client.post(
        "/connector-definitions/custom",
        headers=root_headers,
        json=payload,
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["availability"] == "available"

    rows = client.get("/connector-definitions", headers=root_headers).json()["data"]
    amap_id = next(row["id"] for row in rows if row["key"] == "amap")
    assert client.patch(
        f"/connector-definitions/{amap_id}",
        headers=root_headers,
        json={"name": "覆盖"},
    ).status_code == 403


def test_registration_is_idempotent_and_never_returns_actual_credential(
    registry_api, monkeypatch,
):
    client, _, root_headers, _ = registry_api
    payload = {
        "definition_key": "amap",
        "name": "生产高德",
        "credential_ref": "AMAP_PROD",
        "scope_config": {"operation": "venue_search"},
        "schedule_config": {},
    }
    first = client.post("/data-sources/register", headers=root_headers, json=payload)
    second = client.post("/data-sources/register", headers=root_headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert first.json()["data"]["status"] == "pending_credentials"
    assert "actual-key" not in first.text

    source_id = first.json()["data"]["id"]
    monkeypatch.setenv("DATA_CONNECTOR_SECRET_AMAP_PROD", "actual-key")
    status = client.get(
        f"/data-sources/{source_id}/credential-status",
        headers=root_headers,
    )
    assert status.json()["data"] == {"status": "configured"}
    assert "actual-key" not in status.text


def test_file_connector_can_test_activate_and_disable_without_business_data(registry_api):
    client, sessions, root_headers, _ = registry_api
    registered = client.post("/data-sources/register", headers=root_headers, json={
        "definition_key": "organizer_files",
        "name": "主办方资料入口",
        "scope_config": {},
    }).json()["data"]
    tested = client.post(
        f"/data-sources/{registered['id']}/test",
        headers=root_headers,
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["data"]["status"] == "ready"
    active = client.post(
        f"/data-sources/{registered['id']}/activate",
        headers=root_headers,
    ).json()["data"]
    assert active["status"] == "active"
    disabled = client.post(
        f"/data-sources/{registered['id']}/disable",
        headers=root_headers,
    ).json()["data"]
    assert disabled["status"] == "disabled"
    with sessions() as db:
        from app.models import DataAsset, DataRecord, Evidence
        assert db.query(DataAsset).count() == 0
        assert db.query(DataRecord).count() == 0
        assert db.query(Evidence).filter(Evidence.evidence_type == "connector_test").count() == 0


def test_readonly_api_rejects_non_https_before_network(monkeypatch):
    registration = source(
        connector_key="agent_api",
        credential_ref="",
        scope_config={"endpoint": "http://api.example.org/read", "read_only": True},
    )
    item = definition(
        key="agent_api",
        source_kind="api",
        auth_type="none",
        adapter_key="agent_api",
        capabilities=["read"],
        config_schema={"fields": []},
    )
    monkeypatch.setenv("ANALYSIS_ALLOWED_ORIGINS", "http://api.example.org")
    monkeypatch.setattr(
        connector_runtime.requests,
        "Session",
        lambda: pytest.fail("network called"),
    )
    result = connector_runtime.test_registration(registration, item)
    assert result["code"] == "endpoint_rejected"


def test_mcp_rejects_non_readonly_tool(monkeypatch):
    calls = []

    def request_json(method, url, **kwargs):
        body = kwargs["json"]
        calls.append(body["method"])
        if body["method"] == "initialize":
            return {"id": body["id"], "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
            }}, {"Mcp-Session-Id": "session"}
        if body["method"] == "notifications/initialized":
            return None, {}
        return {"id": body["id"], "result": {"tools": [{
            "name": "fetch",
            "annotations": {"readOnlyHint": False},
        }]}}, {}

    monkeypatch.setenv("ANALYSIS_ALLOWED_ORIGINS", "https://mcp.example.org")
    monkeypatch.setattr(
        "app.integrations.connector_runtime.live_reads.validate_public_host",
        lambda url: None,
    )
    monkeypatch.setattr(
        "app.integrations.connector_runtime.live_reads.request_json",
        request_json,
    )
    result = connector_runtime.test_registration(
        source(scope_config={
            "endpoint": "https://mcp.example.org/mcp",
            "read_only": True,
            "tool": "fetch",
            "url_argument": "url",
        }),
        definition(
            key="mcp_web",
            source_kind="mcp",
            auth_type="none",
            adapter_key="mcp_web",
            capabilities=["read"],
            config_schema={"fields": []},
        ),
    )
    assert result["code"] == "tool_not_readonly"
    assert calls == ["initialize", "notifications/initialized", "tools/list"]


def test_custom_definition_rejects_secret_fields(registry_api):
    client, _, root_headers, _ = registry_api
    response = client.post(
        "/connector-definitions/custom",
        headers=root_headers,
        json={
            "key": "unsafe_api",
            "name": "不安全接口",
            "source_kind": "api",
            "domain": "general",
            "auth_type": "bearer",
            "config_schema": {"fields": [
                {"name": "secret_token", "type": "password", "required": True},
            ]},
            "capabilities": ["read"],
        },
    )
    assert response.status_code == 422


def test_registration_rejects_credentials_inside_public_config(registry_api):
    client, sessions, root_headers, _ = registry_api
    response = client.post(
        "/data-sources/register",
        headers=root_headers,
        json={
            "definition_key": "amap",
            "name": "错误密钥位置",
            "credential_ref": "AMAP_PROD",
            "scope_config": {
                "operation": "venue_search",
                "api_key": "must-not-persist",
            },
        },
    )
    assert response.status_code == 422
    assert "must-not-persist" not in response.text
    with sessions() as db:
        assert db.query(DataSource).filter_by(name="错误密钥位置").count() == 0


def test_legacy_registration_drops_credentials_from_json_config(registry_api):
    client, sessions, _, _ = registry_api
    response = client.post("/data-sources", json={
        "name": "旧接口安全兼容",
        "source_kind": "api",
        "connector_key": "agent_api",
        "credential_ref": "AGENT_API_PROD",
        "scope_config": {
            "endpoint": "https://api.example.org/read",
            "authorization": "Bearer must-not-persist",
            "nested": {"cookie": "must-not-persist"},
        },
        "schedule_config": {"token": "must-not-persist", "cron": "0 1 * * *"},
    })
    assert response.status_code == 200
    assert "must-not-persist" not in response.text
    with sessions() as db:
        registration = db.query(DataSource).filter_by(name="旧接口安全兼容").one()
        assert registration.scope_config == {
            "endpoint": "https://api.example.org/read",
            "nested": {},
        }
        assert registration.schedule_config == {"cron": "0 1 * * *"}


def test_allowlisted_private_endpoint_is_still_rejected_before_network(monkeypatch):
    monkeypatch.setenv("ANALYSIS_ALLOWED_ORIGINS", "https://127.0.0.1")
    monkeypatch.setattr(
        connector_runtime.requests,
        "Session",
        lambda: pytest.fail("network called"),
    )
    result = connector_runtime.test_registration(
        source(scope_config={
            "endpoint": "https://127.0.0.1/read",
            "read_only": True,
        }),
        definition(
            key="agent_api",
            source_kind="api",
            auth_type="none",
            adapter_key="agent_api",
            capabilities=["read"],
            config_schema={"fields": []},
        ),
    )
    assert result["code"] == "endpoint_rejected"


def test_legacy_serializer_adds_registration_fields_and_redacts_test_details():
    registration = source(
        definition_id=7,
        connector_key="amap",
        last_test_result={
            "ok": False,
            "code": "connection_failed",
            "message": "连接失败",
            "token": "must-not-return",
            "capabilities": ["read"],
            "config_hash": "internal-only",
        },
    )
    data = serialize_data_source(registration)
    assert data["definition_id"] == 7
    assert data["last_test_result"] == {
        "ok": False,
        "code": "connection_failed",
        "message": "连接失败",
        "capabilities": ["read"],
    }
    assert "must-not-return" not in str(data)
    assert "internal-only" not in str(data)


def test_vendor_collection_is_idempotent_and_creates_reviewable_evidence(
    registry_api, monkeypatch,
):
    client, sessions, _, _ = registry_api

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "1",
                "pois": [{
                    "id": "venue-1",
                    "name": "测试场馆",
                    "address": "公开地址",
                    "location": "120.0,30.0",
                }],
            }

    monkeypatch.setenv("DATA_CONNECTOR_SECRET_AMAP_PROD", "actual-key")
    monkeypatch.setattr(
        "app.integrations.connectors.requests.get",
        lambda *args, **kwargs: Response(),
    )
    project = client.post(
        "/projects",
        json={"name": "连接器幂等项目", "city": "杭州"},
    ).json()["data"]
    source_data = client.post("/data-sources", json={
        "name": "幂等高德",
        "source_kind": "api",
        "connector_key": "amap",
        "status": "active",
        "credential_ref": "AMAP_PROD",
    }).json()["data"]
    asset_ids = []
    for query in ("第一次采集", "第二次采集"):
        job = client.post("/external-data/jobs", json={
            "project_id": project["id"],
            "source_type": "api",
            "provider": "amap",
            "query": query,
            "parameters": {
                "data_source_id": source_data["id"],
                "operation": "venue_search",
                "city": "杭州",
                "keywords": "测试场馆",
            },
        }).json()["data"]
        result = client.post(
            f"/external-data/jobs/{job['id']}/run",
        ).json()["data"]
        asset_ids.append(result["result"]["asset"]["id"])

    assert asset_ids[0] == asset_ids[1]
    with sessions() as db:
        from app.models import DataAsset, DataRecord, Evidence
        assert db.query(DataAsset).filter_by(
            data_source_id=source_data["id"],
        ).count() == 1
        assert db.query(DataRecord).count() == 1
        evidence = db.query(Evidence).filter_by(
            project_id=project["id"],
            source=f"connector-source:{source_data['id']}",
        ).one()
        assert evidence.status == "needs_review"
        assert evidence.meta["requires_human_verification"] is True
