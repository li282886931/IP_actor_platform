from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main as app_module


def make_temp_session(monkeypatch, tmp_path, *, existing_file=False):
    db_path = tmp_path / "demo.db"
    if existing_file:
        db_path.touch()

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(app_module, "DB_FILE", str(db_path))
    monkeypatch.setattr(app_module, "engine", engine)
    monkeypatch.setattr(app_module, "SessionLocal", session_factory)

    return session_factory


def test_init_db_seeds_existing_empty_database_file(monkeypatch, tmp_path):
    session_factory = make_temp_session(monkeypatch, tmp_path, existing_file=True)

    app_module.init_db()

    db = session_factory()
    try:
        assert db.query(app_module.Artist).count() == 3
        assert db.query(app_module.Show).count() == 3
    finally:
        db.close()


def test_ai_generate_returns_nested_result_and_records_generation(monkeypatch, tmp_path):
    session_factory = make_temp_session(monkeypatch, tmp_path)
    app_module.init_db()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)

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
                "show_name": "Demo Show",
                "artist": "Demo Artist",
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


def test_list_shows_returns_seeded_data(monkeypatch, tmp_path):
    session_factory = make_temp_session(monkeypatch, tmp_path)
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
