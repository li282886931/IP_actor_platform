import pytest
from sqlalchemy import inspect, text

from test_main import app_module, db_module, make_test_client, make_temp_session
from test_ai_user_isolation import login
from app.models import DataSource, Notification, Order, Project, Show, Task, Tenant, TenantMember, User


@pytest.fixture
def client_db(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    try:
        yield client, sessions
    finally:
        app_module.app.dependency_overrides.clear()


@pytest.mark.parametrize("account,route", [
    ("b_user", "business"), ("brand_user", "brand"),
    ("g_user", "government"), ("c_user", "audience"),
    ("investor_user", "investor"), ("artist_user", "artist"),
])
def test_each_role_has_authenticated_workspace(client_db, monkeypatch, account, route):
    client, _ = client_db
    headers, identity = login(client, monkeypatch, account)
    response = client.get(f"/workspaces/{route}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["personal"]["user_id"] == identity["user"]["id"]
    assert client.get(f"/workspaces/{route}").status_code == 401
    if account != "root":
        assert client.get("/workspaces/admin", headers=headers).status_code == 403
        for other in ["business", "brand", "government", "audience", "investor", "artist"]:
            if other != route:
                assert client.get(f"/workspaces/{other}", headers=headers).status_code == 403


def test_personal_inbox_and_project_data_are_scoped(client_db, monkeypatch):
    client, sessions = client_db
    headers, identity = login(client, monkeypatch, "brand_user")
    other_headers, other = login(client, monkeypatch, "b_user")
    uid, tid = identity["user"]["id"], identity["current_tenant"]["id"]
    with sessions() as db:
        foreign = Tenant(name="外部")
        db.add(foreign)
        db.flush()
        own = Project(tenant_id=tid, name="品牌候选", available_funds=987654)
        alien = Project(tenant_id=foreign.id, name="不应出现")
        db.add_all([own, alien])
        db.flush()
        db.add_all([
            Task(project_id=own.id, assignee_id=uid, title="我的任务", status="in_progress",
                 description="场地授权核验", result="已联系场地", rejection_reason="需有效日期"),
            Task(project_id=own.id, assignee_id=other["user"]["id"], title="别人的任务", result="其他账号私有结果"),
            Task(project_id=alien.id, assignee_id=uid, title="其他空间任务", description="跨空间私有要求"),
            Notification(tenant_id=tid, user_id=uid, business_key="own", title="我的消息"),
            Notification(tenant_id=tid, user_id=other["user"]["id"], business_key="other", title="私人消息"),
        ])
        db.commit()
        foreign_id = foreign.id
    data = client.get("/workspaces/brand", headers=headers).json()["data"]
    assert [t["title"] for t in data["personal"]["tasks"]] == ["我的任务"]
    task = data["personal"]["tasks"][0]
    assert task["project_name"] == "品牌候选"
    assert task["assignee_id"] == uid
    assert task["assignee_name"] == identity["user"]["name"]
    assert {"description", "result", "rejection_reason", "evidence_count"} <= task.keys()
    assert task["status"] == "in_progress" and task["description"] == "场地授权核验"
    assert task["result"] == "已联系场地" and task["rejection_reason"] == "需有效日期"
    assert "其他账号私有结果" not in str(data) and "跨空间私有要求" not in str(data)
    assert [n["title"] for n in data["personal"]["notifications"]] == ["我的消息"]
    assert "不应出现" not in str(data)
    assert "available_funds" not in str(data) and "987654" not in str(data)
    assert client.get("/workspaces/brand", headers=other_headers).status_code == 403
    assert client.get("/workspaces/brand", headers={**headers, "X-Tenant-Id": str(foreign_id)}).status_code == 403


def test_reservations_owned_idempotent_and_not_claimed_by_phone(client_db, monkeypatch):
    client, sessions = client_db
    first, one = login(client, monkeypatch, "c_user")
    with sessions() as db:
        show_id = db.query(Show).first().id
        db.add(Order(show_id=show_id, name="历史", phone="13800000000"))
        db.commit()
    client.post("/users", json={"account": "second_audience", "name": "乙", "password": "123456", "group_code": "C"})
    second, two = login(client, monkeypatch, "second_audience")
    payload = {"name": "同名", "phone": "13800000000"}
    a = client.post(f"/shows/{show_id}/order", headers=first, json=payload)
    repeat = client.post(f"/shows/{show_id}/order", headers=first, json=payload)
    b = client.post(f"/shows/{show_id}/order", headers=second, json=payload)
    assert a.json()["data"]["order_id"] == repeat.json()["data"]["order_id"]
    assert a.json()["data"]["order_id"] != b.json()["data"]["order_id"]
    for headers, identity in [(first, one), (second, two)]:
        data = client.get("/workspaces/audience", headers=headers).json()["data"]
        assert len(data["reservations"]) == 1
        assert data["reservations"][0]["id"] in [a.json()["data"]["order_id"], b.json()["data"]["order_id"]]
    with sessions() as db:
        assert db.query(Order).count() == 3
    assert client.post(f"/shows/{show_id}/order", headers={"Authorization": "Bearer forged"}, json=payload).status_code == 401
    host, _ = login(client, monkeypatch, "b_user")
    assert client.post(f"/shows/{show_id}/order", headers=host, json=payload).status_code == 403
    with sessions() as db:
        space = Tenant(name="第二空间")
        db.add(space)
        db.flush()
        db.add(TenantMember(tenant_id=space.id, user_id=one["user"]["id"]))
        db.commit()
        sid = space.id
    alternate = {**first, "X-Tenant-Id": str(sid)}
    assert client.get("/workspaces/audience", headers=alternate).json()["data"]["reservations"] == []
    assert client.post(f"/shows/{show_id}/order", headers=alternate, json=payload).status_code == 200
    assert client.delete(f'/users/{two["user"]["id"]}').status_code == 200
    with sessions() as db:
        assert db.get(Order, b.json()["data"]["order_id"]).user_id is None


def test_legacy_orders_upgrade_without_attribution(monkeypatch):
    sessions = make_temp_session(monkeypatch)
    with db_module.engine.begin() as connection:
        connection.execute(text("CREATE TABLE orders (id INTEGER PRIMARY KEY, show_id INTEGER, name VARCHAR(255), phone VARCHAR(64))"))
        connection.execute(text("INSERT INTO orders VALUES (1, NULL, '历史', '13800000000')"))
    app_module.init_db()
    app_module.init_db()
    assert {"tenant_id", "user_id"} <= {c["name"] for c in inspect(db_module.engine).get_columns("orders")}
    with sessions() as db:
        row = db.get(Order, 1)
        assert row.name == "历史" and row.user_id is None and row.tenant_id is None


def test_root_has_no_business_workspace(client_db, monkeypatch):
    client, sessions = client_db
    headers, identity = login(client, monkeypatch, "root")
    with sessions() as db:
        db.add(DataSource(tenant_id=identity["current_tenant"]["id"], name="安全数据源",
                          source_kind="api", connector_key="api", credential_ref="private-secret",
                          scope_config={"password": "never-emit"}))
        db.commit()
    for route in ["admin", "business", "brand", "government", "audience", "investor", "artist"]:
        response = client.get(f"/workspaces/{route}", headers=headers)
        assert response.status_code == 403
        assert "安全数据源" not in response.text and "private-secret" not in response.text
    created = client.post("/users", headers=headers, json={
        "account": "root_created_host", "name": "新主办方", "password": "123456", "group_code": "B",
    })
    assert created.status_code == 200
    assert created.json()["data"]["group_code"] == "B"
