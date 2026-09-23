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
    assert calls[0]["timeout"] == config_module.LLAMA_SERVER_TIMEOUT_SECONDS

    db = session_factory()
    try:
        generation = db.query(app_module.AIGeneration).one()
        assert generation.result == "Local llama copy"
    finally:
        db.close()


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
            json={"account": "operator@ruiyinchang.com", "name": "运营负责人"},
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
