import pytest
from sqlalchemy import inspect, text

from test_main import app_module, ai_routes, auth_routes, db_module, make_test_client, make_temp_session
from app.models import Tenant, TenantMember, User
from app.services.auth import create_session_token, get_or_create_default_context


@pytest.fixture
def ai_client(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    monkeypatch.setenv("LLAMA_SERVER_URL", "")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)
    cache = {}
    monkeypatch.setattr(ai_routes, "redis_get_json", cache.get)
    monkeypatch.setattr(ai_routes, "redis_set_json", lambda key, value: cache.update({key: value}))
    try:
        yield client, sessions, cache
    finally:
        app_module.app.dependency_overrides.clear()


def login(client, monkeypatch, account):
    monkeypatch.setattr(auth_routes, "validate_captcha_challenge", lambda *args: True)
    response = client.post("/auth/web-login", json={
        "account": account, "password": "123456",
        "captcha_id": "test", "captcha_code": "ABCD",
    })
    assert response.status_code == 200
    data = response.json()["data"]
    return {"Authorization": f'Bearer {data["token"]}'}, data


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
@pytest.mark.parametrize("token", ["", "Bearer forged-token"])
def test_generation_rejects_missing_or_forged_login(ai_client, route, token):
    client, sessions, cache = ai_client
    response = client.post(route, headers={"Authorization": token}, json={"type": "poster"})
    assert response.status_code == 401
    with sessions() as db:
        assert db.query(app_module.AIGeneration).count() == 0
    assert not cache


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
def test_generation_and_cache_belong_to_each_logged_in_user(ai_client, monkeypatch, route):
    client, sessions, cache = ai_client
    payload = {"type": "poster", "show_name": "同一演出", "generation_nonce": "same-request"}
    identities = []
    for account in ["root", "b_user"]:
        headers, data = login(client, monkeypatch, account)
        identities.append((data["current_tenant"]["id"], data["user"]["id"]))
        response = client.post(route, json=payload, headers=headers)
        assert response.status_code == 200
        assert "cache_hit" not in response.text
        repeat = client.post(route, json=payload, headers=headers)
        assert repeat.status_code == 200
        assert '"cache_hit": true' in repeat.text or '"cache_hit":true' in repeat.text
    with sessions() as db:
        records = db.query(app_module.AIGeneration).order_by(app_module.AIGeneration.id).all()
        assert [(record.tenant_id, record.user_id) for record in records] == identities
    assert len(cache) == 2


def test_generation_rejects_foreign_tenant_and_separates_authorized_spaces(ai_client):
    client, sessions, cache = ai_client
    with sessions() as db:
        tenant, user = get_or_create_default_context(db)
        other = Tenant(name="另一个空间", status="active")
        db.add(other)
        db.commit()
        token = create_session_token(user.id, tenant.id)
        other_id = other.id
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(other_id)}
    payload = {"type": "poster", "generation_nonce": "same"}
    assert client.post("/ai/generate", headers=headers, json=payload).status_code == 403
    with sessions() as db:
        db.add(TenantMember(tenant_id=other_id, user_id=user.id, role="member"))
        db.commit()
    assert client.post("/ai/generate", headers=headers, json=payload).status_code == 200
    headers.pop("X-Tenant-Id")
    assert client.post("/ai/generate", headers=headers, json=payload).status_code == 200
    assert len(cache) == 2


def test_new_account_can_generate_after_login_and_membership_is_not_duplicated(ai_client, monkeypatch):
    client, sessions, _ = ai_client
    response = client.post("/users", json={
        "account": "new_promoter", "name": "新主办方", "password": "123456", "group_code": "B",
    })
    assert response.status_code == 200
    for _ in range(2):
        headers, identity = login(client, monkeypatch, "new_promoter")
        assert client.post("/ai/generate", headers=headers, json={"type": "poster"}).status_code == 200
    with sessions() as db:
        assert db.query(TenantMember).filter(
            TenantMember.user_id == identity["user"]["id"],
            TenantMember.tenant_id == identity["current_tenant"]["id"],
        ).count() == 1


def test_deleting_account_preserves_unassigned_generation_without_foreign_key_errors(ai_client, monkeypatch):
    client, sessions, _ = ai_client
    with db_module.engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    user = client.post("/users", json={
        "account": "retired_promoter", "name": "待注销主办方", "password": "123456", "group_code": "B",
    }).json()["data"]
    headers, _ = login(client, monkeypatch, "retired_promoter")
    assert client.post("/ai/generate", headers=headers, json={"type": "poster"}).status_code == 200
    assert client.delete(f'/users/{user["id"]}').status_code == 200
    with sessions() as db:
        assert db.query(TenantMember).filter(TenantMember.user_id == user["id"]).count() == 0
        assert db.query(app_module.AIGeneration).one().user_id is None
    assert client.post("/ai/generate", headers=headers, json={"type": "poster"}).status_code == 401


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
def test_disabled_account_cannot_use_existing_token(ai_client, route):
    client, sessions, _ = ai_client
    with sessions() as db:
        tenant, user = get_or_create_default_context(db)
        token = create_session_token(user.id, tenant.id)
        user.status = "disabled"
        db.commit()
    assert client.post(
        route, headers={"Authorization": f"Bearer {token}"}, json={"type": "poster"},
    ).status_code == 401


def test_existing_generation_table_upgrades_without_claiming_legacy_rows(monkeypatch):
    sessions = make_temp_session(monkeypatch)
    with db_module.engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE ai_generations (id INTEGER PRIMARY KEY, type VARCHAR(64), "
            "prompt TEXT, result TEXT, created_at DATETIME)"
        ))
        connection.execute(text(
            "INSERT INTO ai_generations (id, type, prompt, result) VALUES (1, 'poster', '旧输入', '旧结果')"
        ))
    app_module.init_db()
    app_module.init_db()
    columns = {column["name"] for column in inspect(db_module.engine).get_columns("ai_generations")}
    assert {"tenant_id", "user_id"} <= columns
    with sessions() as db:
        old = db.query(app_module.AIGeneration).one()
        assert old.tenant_id is None and old.user_id is None
        assert old.result == "旧结果"
