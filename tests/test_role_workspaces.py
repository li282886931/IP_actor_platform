import pytest
from sqlalchemy import inspect, text

from test_main import app_module, db_module, make_test_client, make_temp_session
from test_ai_user_isolation import login
from app.models import Artist, Gate, Project, ProjectVersion, Risk, Tenant, TenantMember, User
from app.services.auth import create_session_token, get_or_create_default_context


@pytest.fixture
def workspace_client(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    yield client, sessions
    app_module.app.dependency_overrides.clear()


@pytest.mark.parametrize("account,role,route", [
    ("investor_user", "Investor", "/workspaces/investor"),
    ("artist_user", "Artist", "/workspaces/artist"),
])
def test_new_roles_login_and_access_only_own_workspace(workspace_client, monkeypatch, account, role, route):
    client, sessions = workspace_client
    headers, identity = login(client, monkeypatch, account)
    assert identity["user"]["role"] == role
    assert client.get(route, headers=headers).status_code == 200
    other = "/workspaces/artist" if role == "Investor" else "/workspaces/investor"
    assert client.get(other, headers=headers).status_code == 403
    assert client.get(route).status_code == 401
    b_headers, _ = login(client, monkeypatch, "b_user")
    assert client.get(route, headers=b_headers).status_code == 403


def test_artist_binding_validation_and_explicit_unbinding(workspace_client):
    client, sessions = workspace_client
    with sessions() as db:
        artist_id = db.query(Artist).first().id
        tenant, root = get_or_create_default_context(db)
        headers = {"Authorization": f"Bearer {create_session_token(root.id, tenant.id)}"}
    payload = {"account": "bound_artist", "name": "艺人账号", "password": "123456",
               "group_code": "Artist", "artist_id": artist_id}
    assert client.post("/users", json=payload).status_code == 401
    response = client.post("/users", json=payload, headers=headers)
    assert response.status_code == 200
    user = response.json()["data"]
    assert user["artist_id"] == artist_id
    assert client.patch(f'/users/{user["id"]}', json={"artist_id": 999999}, headers=headers).status_code == 400
    assert client.patch(f'/users/{user["id"]}', json={"artist_id": None}, headers=headers).json()["data"]["artist_id"] is None
    assert client.patch(f'/users/{user["id"]}', json={"artist_id": artist_id}, headers=headers).status_code == 200
    assert client.patch(f'/users/{user["id"]}', json={"group_code": "Investor"}, headers=headers).json()["data"]["artist_id"] is None
    payload["account"] = "invalid_binding"
    payload["group_code"] = "Investor"
    assert client.post("/users", json=payload, headers=headers).status_code == 400


def test_workspaces_filter_tenant_and_artist_and_read_current_version(workspace_client, monkeypatch):
    client, sessions = workspace_client
    investor_headers, investor = login(client, monkeypatch, "investor_user")
    artist_headers, artist_identity = login(client, monkeypatch, "artist_user")
    tenant_id = investor["current_tenant"]["id"]
    with sessions() as db:
        artist = db.query(Artist).first()
        user = db.get(User, artist_identity["user"]["id"])
        user.artist_id = artist.id
        foreign = Tenant(name="外部空间")
        db.add(foreign)
        db.flush()
        projects = [
            Project(tenant_id=tenant_id, name="我的机会", artist_id=artist.id),
            Project(tenant_id=tenant_id, name="仅同名", artist_name=artist.name),
            Project(tenant_id=foreign.id, name="其他空间", artist_id=artist.id),
        ]
        db.add_all(projects)
        db.flush()
        old = ProjectVersion(project_id=projects[0].id, version_no=1, input_snapshot={}, finance_result={"net_profit": 123})
        current = ProjectVersion(project_id=projects[0].id, version_no=2, input_snapshot={}, finance_result={
            "status": "calculated", "funding_gap": 0, "roi": 0, "net_profit": 0,
        })
        db.add_all([old, current])
        db.flush()
        projects[0].current_version_id = current.id
        db.add_all([Risk(project_id=projects[0].id, title="待核验合同"),
                    Gate(project_id=projects[0].id, name="资金保障")])
        db.commit()
        project_id, other_tenant_id = projects[0].id, foreign.id
    data = client.get("/workspaces/investor", headers=investor_headers).json()["data"]
    assert "其他空间" not in [p["name"] for p in data["projects"]]
    row = next(p for p in data["projects"] if p["id"] == project_id)
    assert row["version"]["version_no"] == 2
    assert row["version"]["finance_result"]["funding_gap"] == 0
    assert row["risks"][0]["title"] == "待核验合同"
    assert row["gates"][0]["name"] == "资金保障"
    artist_data = client.get("/workspaces/artist", headers=artist_headers).json()["data"]
    assert [p["name"] for p in artist_data["projects"]] == ["我的机会"]
    assert "available_funds" not in artist_data["projects"][0]
    assert artist_data["artist"]["name"] != ""
    forbidden = {**investor_headers, "X-Tenant-Id": str(other_tenant_id)}
    assert client.get("/workspaces/investor", headers=forbidden).status_code == 403
    with sessions() as db:
        db.add(TenantMember(tenant_id=other_tenant_id, user_id=investor["user"]["id"]))
        db.commit()
    assert [p["name"] for p in client.get("/workspaces/investor", headers=forbidden).json()["data"]["projects"]] == ["其他空间"]


def test_non_admin_cannot_rebind_artist_and_disabled_session_is_rejected(workspace_client, monkeypatch):
    client, sessions = workspace_client
    headers, identity = login(client, monkeypatch, "artist_user")
    assert client.patch(f'/users/{identity["user"]["id"]}', headers=headers, json={"artist_id": None}).status_code == 403
    with sessions() as db:
        db.get(User, identity["user"]["id"]).status = "disabled"
        db.commit()
    assert client.get("/workspaces/artist", headers=headers).status_code == 401


def test_unbound_artist_empty_and_user_column_upgrade_is_idempotent(workspace_client, monkeypatch):
    client, _ = workspace_client
    headers, _ = login(client, monkeypatch, "artist_user")
    data = client.get("/workspaces/artist", headers=headers).json()["data"]
    assert data["artist"] is None and data["projects"] == []
    make_temp_session(monkeypatch)
    with db_module.engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, account VARCHAR(255), name VARCHAR(255), "
                                "openid VARCHAR(128), unionid VARCHAR(128), phone VARCHAR(64), group_id INTEGER, "
                                "status VARCHAR(64), created_at DATETIME)"))
    app_module.init_db()
    app_module.init_db()
    assert "artist_id" in {c["name"] for c in inspect(db_module.engine).get_columns("users")}
