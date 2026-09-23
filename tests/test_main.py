import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
import main as app_module
import app.config as config_module
import app.database as db_module
import app.routes as routes_module


def test_database_url_example_lives_in_config_file():
    assert config_module.DATABASE_URL == config_module.DATABASE_URL_EXAMPLE
    assert config_module.DATABASE_URL_EXAMPLE.endswith("/ip_actor_platform?charset=utf8mb4")
    with open(db_module.__file__, encoding="utf-8") as database_file:
        assert "mysql+pymysql://root:123456789@127.0.0.1:3306/ip_actor_platform?charset=utf8mb4" not in database_file.read()


def test_database_engine_options_match_database_driver():
    assert app_module.resolve_database_url({"DATABASE_URL": "mysql+pymysql://root:pw@127.0.0.1:3306/ip_actor_platform"}) == "mysql+pymysql://root:pw@127.0.0.1:3306/ip_actor_platform"
    assert app_module.create_engine_kwargs("sqlite://") == {
        "connect_args": {"check_same_thread": False},
    }
    assert app_module.create_engine_kwargs("mysql+pymysql://root:pw@127.0.0.1:3306/ip_actor_platform") == {}


def test_database_url_uses_config_when_env_is_missing(monkeypatch):
    assert app_module.resolve_database_url({}) == config_module.DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:pw@127.0.0.1:3306/ip_actor_platform")
    assert app_module.resolve_database_url() == "mysql+pymysql://root:pw@127.0.0.1:3306/ip_actor_platform"


def test_llama_server_timeout_allows_local_generation():
    assert config_module.LLAMA_SERVER_TIMEOUT_SECONDS >= 90


def make_temp_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", session_factory)
    monkeypatch.setattr(app_module, "engine", engine)
    monkeypatch.setattr(app_module, "SessionLocal", session_factory)

    return session_factory


def test_init_db_seeds_empty_database(monkeypatch):
    session_factory = make_temp_session(monkeypatch)

    app_module.init_db()

    db = session_factory()
    try:
        assert db.query(app_module.Artist).count() == 3
        assert db.query(app_module.Show).count() == 3
    finally:
        db.close()


def test_ai_generate_returns_nested_result_and_records_generation(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)
    monkeypatch.setenv("LLAMA_SERVER_URL", "")

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        client = TestClient(app_module.app)
        response = client.post(
            "/ai/generate",
            json={
                "type": "poster",
                "show_name": "Test Show",
                "artist": "Test Artist",
                "city": "Shanghai",
            },
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["result"]
    assert "传播定位" in body["data"]["result"]
    assert "核心文案" in body["data"]["result"]
    assert "投放建议" in body["data"]["result"]

    db = session_factory()
    try:
        assert db.query(app_module.AIGeneration).count() == 1
    finally:
        db.close()


def test_ai_generate_prefers_local_llama_server(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")
    monkeypatch.setenv("LLAMA_SERVER_MODEL", "qwen-local")

    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "Local llama copy"}}
                ]
            }

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(routes_module.requests, "post", fake_post)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        client = TestClient(app_module.app)
        response = client.post(
            "/ai/generate",
            json={
                "type": "poster",
                "show_name": "Test Show",
                "artist": "Test Artist",
                "city": "Shanghai",
            },
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["result"] == "Local llama copy"
    assert calls[0]["url"] == "http://127.0.0.1:18080/v1/chat/completions"
    assert calls[0]["json"]["model"] == "qwen-local"
    assert calls[0]["json"]["max_tokens"] >= 800
    assert isinstance(calls[0]["json"]["seed"], int)
    assert calls[0]["json"]["temperature"] >= 0.9
    prompt = calls[0]["json"]["messages"][0]["content"]
    assert "本次创作批次" in prompt
    assert "完整宣发方案" in prompt
    assert "传播定位" in prompt
    assert "短视频脚本" in prompt
    assert calls[0]["timeout"] == config_module.LLAMA_SERVER_TIMEOUT_SECONDS

    db = session_factory()
    try:
        generation = db.query(app_module.AIGeneration).one()
        assert generation.result == "Local llama copy"
    finally:
        db.close()


def test_extract_llama_server_text_reads_reasoning_content():
    assert routes_module.extract_llama_server_text({
        "choices": [
            {"message": {"content": "", "reasoning_content": "Reasoning model output"}}
        ]
    }) == "Reasoning model output"


def test_list_shows_returns_seeded_data(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        client = TestClient(app_module.app)
        response = client.get("/shows")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert len(body["data"]) == 3


def test_root_login_and_user_management(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        login_response = client.post(
            "/auth/web-login",
            json={"account": "root", "password": "123456"},
        )
        assert login_response.status_code == 200
        login_data = login_response.json()["data"]
        assert login_data["user"]["account"] == "root"
        assert login_data["user"]["group_code"] == "root"
        assert login_data["user"]["can_manage_users"] is True

        groups_response = client.get("/user-groups")
        assert groups_response.status_code == 200
        assert [group["code"] for group in groups_response.json()["data"]] == ["root", "B", "Brand", "G", "C"]

        create_response = client.post(
            "/users",
            json={
                "account": "brand-user",
                "name": "品牌用户",
                "password": "abc123",
                "group_code": "Brand",
            },
        )
        assert create_response.status_code == 200
        created_user = create_response.json()["data"]
        assert created_user["group_code"] == "Brand"
        assert "password" not in created_user

        brand_login = client.post(
            "/auth/web-login",
            json={"account": "brand-user", "password": "abc123"},
        )
        assert brand_login.status_code == 200
        assert brand_login.json()["data"]["user"]["group_code"] == "Brand"

        update_response = client.patch(
            f"/users/{created_user['id']}",
            json={
                "name": "文旅用户",
                "password": "newpass123",
                "group_code": "G",
            },
        )
        assert update_response.status_code == 200
        updated_user = update_response.json()["data"]
        assert updated_user["name"] == "文旅用户"
        assert updated_user["group_code"] == "G"

        old_password_login = client.post(
            "/auth/web-login",
            json={"account": "brand-user", "password": "abc123"},
        )
        assert old_password_login.status_code == 401

        new_password_login = client.post(
            "/auth/web-login",
            json={"account": "brand-user", "password": "newpass123"},
        )
        assert new_password_login.status_code == 200
        assert new_password_login.json()["data"]["user"]["group_code"] == "G"

        users_response = client.get("/users")
        assert users_response.status_code == 200
        assert {user["account"] for user in users_response.json()["data"]} >= {"root", "brand-user"}

        delete_response = client.delete(f"/users/{created_user['id']}")
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["deleted"] is True
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.User).filter(app_module.User.account == "brand-user").first() is None
    finally:
        db.close()


def test_default_business_group_users_can_login(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    expected_users = {
        "b_user": ("B", "B"),
        "brand_user": ("Brand", "Brand"),
        "g_user": ("G", "G"),
        "c_user": ("C", "C"),
    }

    try:
        for account, (group_code, role) in expected_users.items():
            response = client.post(
                "/auth/web-login",
                json={"account": account, "password": "123456"},
            )
            assert response.status_code == 200
            user = response.json()["data"]["user"]
            assert user["account"] == account
            assert user["group_code"] == group_code
            assert user["role"] == role
            assert user["can_manage_users"] is False
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        users = {
            user.account: user.group_code
            for user in db.query(app_module.User).filter(app_module.User.account.in_(expected_users.keys())).all()
        }
        assert users == {account: expected[0] for account, expected in expected_users.items()}
    finally:
        db.close()


def make_test_client(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    return TestClient(app_module.app), session_factory


def test_phase1_project_decision_flow(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        login_response = client.post(
            "/auth/web-login",
            json={"account": "root", "password": "123456"},
            headers={"X-Client-Source": "web"},
        )
        assert login_response.status_code == 200
        login_body = login_response.json()
        assert login_body["code"] == 0
        assert login_body["data"]["token"]
        assert login_body["data"]["current_tenant"]["name"] == "锐音场默认空间"

        project_response = client.post(
            "/projects",
            json={
                "name": "北京大型演唱会测算",
                "artist_name": "周杰伦",
                "city": "北京",
                "venue": "国家体育场",
                "schedule": "2026-09-10",
                "expected_attendance": 48000,
                "avg_ticket_price": 680,
                "artist_fee": 12000000,
                "venue_cost": 3600000,
                "marketing_cost": 1800000,
                "production_cost": 5200000,
            },
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]
        assert project["tenant_id"] == login_body["data"]["current_tenant"]["id"]
        assert project["status"] == "draft"
        assert project["current_version_id"]

        finance_response = client.post(
            "/finance/calculate",
            json={
                "project_id": project["id"],
                "expected_attendance": 48000,
                "avg_ticket_price": 680,
                "artist_fee": 12000000,
                "venue_cost": 3600000,
                "marketing_cost": 1800000,
                "production_cost": 5200000,
            },
        )
        assert finance_response.status_code == 200
        finance = finance_response.json()["data"]
        assert finance["formula_version"] == "finance-v1"
        assert finance["version_id"]
        assert finance["scenarios"]["neutral"]["revenue"] == 32640000
        assert finance["scenarios"]["neutral"]["profit"] == 10040000
        assert finance["breakeven_attendance"] == 33236

        versions_response = client.get(f"/projects/{project['id']}/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()["data"]
        assert len(versions) == 2
        assert versions[-1]["finance_result"]["scenarios"]["neutral"]["profit"] == 10040000

        decision_response = client.post(
            "/decisions",
            json={
                "project_id": project["id"],
                "version_id": versions[-1]["id"],
                "decision_type": "advance",
                "conditions": "完成政策审批和艺人授权后推进",
            },
        )
        assert decision_response.status_code == 200
        decision = decision_response.json()["data"]
        assert decision["decision_type"] == "advance"
        assert decision["project_status"] == "pending_confirmation"

        task_response = client.post(
            "/tasks",
            json={
                "project_id": project["id"],
                "title": "确认场地安全资料",
                "description": "补齐场地方安全承诺与消防批复",
                "due_date": "2026-08-01",
            },
        )
        assert task_response.status_code == 200
        task = task_response.json()["data"]
        assert task["status"] == "pending"

        tasks_response = client.get(f"/tasks?project_id={project['id']}")
        assert tasks_response.status_code == 200
        assert tasks_response.json()["data"][0]["title"] == "确认场地安全资料"
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.Project).count() == 1
        assert db.query(app_module.ProjectVersion).count() == 2
        assert db.query(app_module.Decision).count() == 1
        assert db.query(app_module.Task).count() == 1
    finally:
        db.close()


def test_full_backend_plan_api_flow(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        wechat_response = client.post(
            "/auth/wechat-login",
            json={"code": "wx-code-001", "name": "微信用户", "phone": "13800000000"},
        )
        assert wechat_response.status_code == 200
        wechat_data = wechat_response.json()["data"]
        assert wechat_data["source"] == "wechat"
        assert wechat_data["user"]["phone"] == "13800000000"

        project_response = client.post(
            "/projects",
            json={
                "name": "杭州音乐节",
                "artist_name": "测试艺人",
                "city": "杭州",
                "venue": "城市公园",
                "schedule": "2026-10-01",
                "expected_attendance": 20000,
                "avg_ticket_price": 399,
                "artist_fee": 2600000,
                "venue_cost": 900000,
                "marketing_cost": 500000,
                "production_cost": 1200000,
            },
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        breakeven_response = client.post(
            "/finance/breakeven",
            json={"project_id": project["id"], "target_profit": 1000000},
        )
        assert breakeven_response.status_code == 200
        breakeven = breakeven_response.json()["data"]
        assert breakeven["total_cost"] == 5200000
        assert breakeven["breakeven_attendance"] == 13033
        assert breakeven["target_profit_attendance"] == 15539

        fact_response = client.post(
            "/facts",
            json={
                "project_id": project["id"],
                "title": "场地方已确认档期",
                "content": "档期锁定 2026-10-01",
                "source": "venue",
            },
        )
        assert fact_response.status_code == 200
        fact = fact_response.json()["data"]
        assert fact["status"] == "pending"

        evidence_response = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "fact_id": fact["id"],
                "name": "场地确认函",
                "file_url": "https://example.com/venue.pdf",
                "evidence_type": "document",
                "source": "venue",
            },
        )
        assert evidence_response.status_code == 200
        evidence = evidence_response.json()["data"]
        assert evidence["fact_id"] == fact["id"]
        assert evidence["status"] == "uploaded"

        verify_response = client.post(
            f"/facts/{fact['id']}/verify",
            json={"status": "verified", "comment": "资料一致"},
        )
        assert verify_response.status_code == 200
        verified_fact = verify_response.json()["data"]
        assert verified_fact["status"] == "verified"
        assert verified_fact["verified_by"]

        assumption_response = client.post(
            "/assumptions",
            json={
                "project_id": project["id"],
                "title": "上座率假设",
                "content": "中性情境预计 85% 上座",
                "confidence": 80,
            },
        )
        assert assumption_response.status_code == 200
        assert assumption_response.json()["data"]["confidence"] == 80

        gate_response = client.post(
            "/gates",
            json={
                "project_id": project["id"],
                "name": "政策审批",
                "status": "pending",
                "required_evidence": "营业性演出批文",
            },
        )
        assert gate_response.status_code == 200
        assert gate_response.json()["data"]["status"] == "pending"

        risk_response = client.post(
            "/risks",
            json={
                "project_id": project["id"],
                "title": "天气风险",
                "level": "medium",
                "mitigation": "准备雨棚与退改预案",
            },
        )
        assert risk_response.status_code == 200
        assert risk_response.json()["data"]["level"] == "medium"

        task_response = client.post(
            "/tasks",
            json={
                "project_id": project["id"],
                "title": "提交审批材料",
                "description": "上传批文和消防材料",
            },
        )
        task = task_response.json()["data"]
        submit_response = client.post(
            f"/tasks/{task['id']}/submit",
            json={"result": "审批材料已提交", "evidence_ids": [evidence["id"]]},
        )
        assert submit_response.status_code == 200
        submitted_task = submit_response.json()["data"]
        assert submitted_task["status"] == "submitted"
        assert submitted_task["evidence_ids"] == [evidence["id"]]

        agent_response = client.post(
            "/agent/chat",
            json={"project_id": project["id"], "message": "这个项目下一步做什么？"},
        )
        assert agent_response.status_code == 200
        assert "杭州音乐节" in agent_response.json()["data"]["answer"]

        cases_response = client.get("/cases/search?q=杭州")
        assert cases_response.status_code == 200
        cases = cases_response.json()["data"]
        assert cases[0]["project_id"] == project["id"]

        share_response = client.post(
            f"/reports/{project['id']}/share",
            json={"version_id": project["current_version_id"], "expires_in_days": 7},
        )
        assert share_response.status_code == 200
        share = share_response.json()["data"]
        assert share["project_id"] == project["id"]
        assert share["share_url"].startswith("/shared/reports/")
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.Fact).count() == 1
        assert db.query(app_module.Evidence).count() == 1
        assert db.query(app_module.Assumption).count() == 1
        assert db.query(app_module.Gate).count() == 1
        assert db.query(app_module.Risk).count() == 1
        assert db.query(app_module.ReportShare).count() == 1
    finally:
        db.close()
