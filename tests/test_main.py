import os
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
import main as app_module
import app.config as config_module
import app.database as db_module
import app.routes as routes_module


def write_minimal_docx(path: Path, paragraphs: list[str]):
    document_xml = "".join(
        f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{document_xml}</w:body></w:document>""",
        )


def write_minimal_xlsx(path: Path, rows: list[list[object]]):
    def cell_ref(row_index: int, column_index: int):
        return f"{chr(ord('A') + column_index)}{row_index}"

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            ref = cell_ref(row_index, column_index)
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>""",
        )


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
    assert config_module.LLAMA_SERVER_TIMEOUT_SECONDS >= 300


def test_backend_schema_sql_contains_all_model_tables():
    schema_path = Path(app_module.__file__).parent / "app" / "schema.sql"
    assert schema_path.exists()
    schema_sql = schema_path.read_text(encoding="utf-8")
    table_names = {table.name for table in app_module.Base.metadata.sorted_tables}

    for table_name in table_names:
        assert f"CREATE TABLE {table_name}" in schema_sql

    assert "ENGINE=InnoDB" in schema_sql
    assert "FOREIGN KEY" in schema_sql
    assert "project_analysis_jobs" in schema_sql


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
    app_module.init_db()

    db = session_factory()
    try:
        assert db.query(app_module.Artist).count() == 13
        assert db.query(app_module.Show).count() == 3
        caiqin = db.query(app_module.Artist).filter(app_module.Artist.name == "蔡琴").one()
        assert caiqin.profile["age"] == "约68岁"
        assert "丝绒歌后" in caiqin.profile["market_positioning"]
        assert "不要告别" in caiqin.profile["touring_box_office_reference"]
        liu_xiaoqing = db.query(app_module.Artist).filter(app_module.Artist.name == "刘晓庆").one()
        assert liu_xiaoqing.risk_level >= 4
        assert "反面参照" in liu_xiaoqing.profile["cooperation_recommendation"]
        assert db.query(app_module.Artist).filter(app_module.Artist.name == "费玉清类").one().profile["market_positioning"] == "已封麦"
        shows = db.query(app_module.Show).order_by(app_module.Show.id.asc()).all()
        assert [show.title for show in shows] == ["周杰伦·北京演唱会", "五月天·上海演唱会", "林俊杰小巨蛋特别场"]
        assert all(show.poster_url.startswith("https://copilot-cn.bytedance.net/api/ide/v1/text_to_image?") for show in shows)
        assert len({show.poster_url for show in shows}) == 3
        assert "image_size=landscape_4_3" in shows[0].poster_url
        assert "%E5%91%A8%E6%9D%B0%E4%BC%A6" in shows[0].poster_url
        zhao = db.query(app_module.Artist).filter(app_module.Artist.name == "赵雅芝").one()
        assert zhao.profile["market_dossier"]["sheet_count"] == 8
        assert zhao.profile["market_dossier"]["row_count"] == 108
        project = db.query(app_module.Project).filter(app_module.Project.name == "赵雅芝大秀市场分析").one()
        assert project.artist_name == "赵雅芝"
        assert db.query(app_module.Evidence).filter(app_module.Evidence.project_id == project.id).count() == 108
        assert db.query(app_module.ExternalDataJob).filter(app_module.ExternalDataJob.project_id == project.id).count() == 69
        assert db.query(app_module.Fact).filter(app_module.Fact.project_id == project.id).count() >= 60
        assert db.query(app_module.Assumption).filter(app_module.Assumption.project_id == project.id).count() >= 30
        duplicate_evidence_urls = (
            db.query(app_module.Evidence.file_url)
            .filter(app_module.Evidence.project_id == project.id)
            .group_by(app_module.Evidence.file_url)
            .having(func.count(app_module.Evidence.id) > 1)
            .all()
        )
        assert duplicate_evidence_urls == []
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


def test_oss_upload_reservation_creates_evidence_after_completion(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={"name": "OSS 资料上传项目", "artist_name": "测试艺人", "city": "北京"},
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        initiate_response = client.post(
            "/oss/uploads/initiate",
            json={
                "project_id": project["id"],
                "file_name": "venue-contract.pdf",
                "content_type": "application/pdf",
                "evidence_type": "contract",
                "source": "venue",
            },
        )
        assert initiate_response.status_code == 200
        upload = initiate_response.json()["data"]
        assert upload["status"] == "pending"
        assert upload["provider"] == "local-placeholder"
        assert upload["object_key"].startswith(f"projects/{project['id']}/")
        assert upload["upload_url"].endswith(upload["object_key"])
        assert upload["headers"]["Content-Type"] == "application/pdf"

        complete_response = client.post(
            f"/oss/uploads/{upload['id']}/complete",
            json={
                "file_url": "oss://bucket/projects/venue-contract.pdf",
                "size": 1024,
                "checksum": "sha256-local",
                "metadata": {"stage": "contract-review"},
            },
        )
        assert complete_response.status_code == 200
        completed = complete_response.json()["data"]
        assert completed["upload"]["status"] == "completed"
        assert completed["evidence"]["project_id"] == project["id"]
        assert completed["evidence"]["file_url"] == "oss://bucket/projects/venue-contract.pdf"
        assert completed["evidence"]["metadata"]["object_key"] == upload["object_key"]
        assert completed["evidence"]["metadata"]["size"] == 1024
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.OSSUpload).count() == 1
        assert db.query(app_module.Evidence).filter(app_module.Evidence.project_id == project["id"]).count() == 1
    finally:
        db.close()


def test_oss_upload_initiate_uses_minio_presigned_url_when_enabled(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)
    monkeypatch.setenv("OSS_PROVIDER", "minio")
    monkeypatch.setenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "root")
    monkeypatch.setenv("MINIO_SECRET_KEY", "123456789")
    monkeypatch.setenv("MINIO_BUCKET", "ip-actor-test")

    calls = []

    class FakeMinioClient:
        def bucket_exists(self, bucket):
            calls.append(("bucket_exists", bucket))
            return False

        def make_bucket(self, bucket):
            calls.append(("make_bucket", bucket))

        def presigned_put_object(self, bucket, object_key, expires):
            calls.append(("presigned_put_object", bucket, object_key, int(expires.total_seconds())))
            return f"http://127.0.0.1:9000/{bucket}/{object_key}?signature=fake"

        def stat_object(self, bucket, object_key):
            calls.append(("stat_object", bucket, object_key))

    monkeypatch.setattr(routes_module, "create_minio_client", lambda: FakeMinioClient())

    try:
        project_response = client.post(
            "/projects",
            json={"name": "MinIO 上传项目", "artist_name": "测试艺人", "city": "北京"},
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        initiate_response = client.post(
            "/oss/uploads/initiate",
            json={
                "project_id": project["id"],
                "file_name": "minio-contract.pdf",
                "content_type": "application/pdf",
                "evidence_type": "contract",
                "source": "venue",
            },
        )
        assert initiate_response.status_code == 200
        upload = initiate_response.json()["data"]
        assert upload["provider"] == "minio"
        assert upload["bucket"] == "ip-actor-test"
        assert upload["method"] == "PUT"
        assert upload["upload_url"].startswith("http://127.0.0.1:9000/ip-actor-test/")
        assert upload["headers"]["Content-Type"] == "application/pdf"
        assert calls[0] == ("bucket_exists", "ip-actor-test")
        assert calls[1] == ("make_bucket", "ip-actor-test")
        assert calls[2][0] == "presigned_put_object"

        complete_response = client.post(
            f"/oss/uploads/{upload['id']}/complete",
            json={"size": 2048, "checksum": "sha256-minio"},
        )
        assert complete_response.status_code == 200
        completed = complete_response.json()["data"]
        assert completed["upload"]["file_url"] == f"minio://ip-actor-test/{upload['object_key']}"
        assert completed["evidence"]["file_url"] == completed["upload"]["file_url"]
        assert calls[-1] == ("stat_object", "ip-actor-test", upload["object_key"])
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        saved_upload = db.query(app_module.OSSUpload).one()
        assert saved_upload.provider == "minio"
        assert saved_upload.bucket == "ip-actor-test"
    finally:
        db.close()


def test_feasibility_report_uploads_generated_docx_to_minio(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)
    monkeypatch.setenv("OSS_PROVIDER", "minio")
    monkeypatch.setenv("MINIO_BUCKET", "ip-actor-test")

    calls = []

    class FakeMinioClient:
        def bucket_exists(self, bucket):
            calls.append(("bucket_exists", bucket))
            return True

        def make_bucket(self, bucket):
            calls.append(("make_bucket", bucket))

        def put_object(self, bucket, object_key, data, length, content_type):
            content = data.read()
            calls.append(("put_object", bucket, object_key, length, content_type, content[:2]))

    monkeypatch.setattr(routes_module, "create_minio_client", lambda: FakeMinioClient())

    try:
        project_response = client.post(
            "/projects",
            json={
                "name": "MinIO 可研项目",
                "artist_name": "测试艺人",
                "city": "上海",
                "venue": "测试场馆",
                "expected_attendance": 1000,
                "avg_ticket_price": 500,
                "artist_fee": 100000,
                "venue_cost": 60000,
                "marketing_cost": 20000,
                "production_cost": 50000,
            },
        )
        project = project_response.json()["data"]

        report_response = client.post(f"/projects/{project['id']}/feasibility-report", json={"use_ai_copy": False})
        assert report_response.status_code == 200
        report = report_response.json()["data"]
        assert report["file_url"].startswith("minio://ip-actor-test/")
        assert report["download_url"] == report["file_url"]
        assert report["evidence"]["metadata"]["provider"] == "minio"
        assert calls[0] == ("bucket_exists", "ip-actor-test")
        assert calls[1][0] == "put_object"
        assert calls[1][1] == "ip-actor-test"
        assert calls[1][2].endswith(f"/project-{project['id']}-feasibility-report.docx")
        assert calls[1][3] > 0
        assert calls[1][4] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert calls[1][5] == b"PK"
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        evidence = db.query(app_module.Evidence).filter(
            app_module.Evidence.project_id == project["id"],
            app_module.Evidence.evidence_type == "feasibility_report",
        ).one()
        assert evidence.file_url.startswith("minio://ip-actor-test/")
        assert evidence.meta["local_path"] == ""
    finally:
        db.close()


def test_external_data_async_job_can_be_run_and_queried(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={"name": "外部数据采集项目", "artist_name": "测试艺人", "city": "上海"},
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        create_response = client.post(
            "/external-data/jobs",
            json={
                "project_id": project["id"],
                "source_type": "web",
                "provider": "mcp",
                "query": "测试艺人 上海 演唱会 热度",
                "purpose": "artist_heat",
                "parameters": {"time_range": "30d"},
            },
        )
        assert create_response.status_code == 200
        job = create_response.json()["data"]
        assert job["status"] == "queued"
        assert job["provider"] == "mcp"
        assert job["parameters"]["time_range"] == "30d"

        run_response = client.post(f"/external-data/jobs/{job['id']}/run")
        assert run_response.status_code == 200
        completed = run_response.json()["data"]
        assert completed["status"] == "completed"
        assert completed["result"]["source_type"] == "web"
        assert completed["result"]["provider"] == "mcp"
        assert completed["result"]["requires_human_verification"] is True

        get_response = client.get(f"/external-data/jobs/{job['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["data"]["status"] == "completed"

        list_response = client.get(f"/external-data/jobs?project_id={project['id']}")
        assert list_response.status_code == 200
        assert list_response.json()["data"][0]["id"] == job["id"]
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.ExternalDataJob).filter(app_module.ExternalDataJob.project_id == project["id"]).count() == 1
    finally:
        db.close()


def test_data_source_assets_and_disabled_connector_execution_are_traceable(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={"name": "数据资产项目", "artist_name": "测试艺人", "city": "上海"},
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        source_response = client.post(
            "/data-sources",
            json={
                "name": "主办方资料库",
                "source_kind": "organizer_file",
                "connector_key": "organizer_files",
                "status": "disabled",
                "scope_config": {"project_ids": [project["id"]]},
            },
        )
        assert source_response.status_code == 200
        source = source_response.json()["data"]
        assert source["status"] == "disabled"
        assert source["credential_ref"] == ""
        assert source["scope_config"]["project_ids"] == [project["id"]]

        health_response = client.post(f"/data-sources/{source['id']}/health-check")
        assert health_response.status_code == 200
        assert health_response.json()["data"] == {
            "data_source_id": source["id"],
            "connector_key": "organizer_files",
            "status": "disabled",
            "can_fetch": False,
            "reason": "Data source is disabled",
        }

        asset_response = client.post(
            "/data-assets",
            json={
                "project_id": project["id"],
                "data_source_id": source["id"],
                "asset_type": "financial_sheet",
                "source_uri": "oss://organizer/finance-v1.xlsx",
                "content_hash": "finance-v1",
                "raw_payload_ref": "oss://raw/finance-v1.xlsx",
                "records": [
                    {
                        "entity_type": "project",
                        "entity_id": str(project["id"]),
                        "metric_key": "available_funds",
                        "value_json": {"amount": 2000000},
                        "unit": "CNY",
                        "record_status": "observed",
                        "lineage": {"field": "资金余额", "parser_version": "v1"},
                    },
                ],
            },
        )
        assert asset_response.status_code == 200
        asset = asset_response.json()["data"]
        assert asset["status"] == "received"
        assert asset["records"][0]["metric_key"] == "available_funds"
        assert asset["records"][0]["lineage"]["parser_version"] == "v1"

        records_response = client.get(
            f"/data-records?entity_type=project&entity_id={project['id']}&metric_key=available_funds"
        )
        assert records_response.status_code == 200
        assert records_response.json()["data"][0]["asset_id"] == asset["id"]

        run_response = client.post(
            "/external-data/jobs",
            json={
                "project_id": project["id"],
                "source_type": "api",
                "provider": "organizer_files",
                "query": "同步主办方资料",
                "purpose": "project_documents",
                "parameters": {"data_source_id": source["id"]},
            },
        )
        assert run_response.status_code == 200
        job = run_response.json()["data"]
        blocked_response = client.post(f"/external-data/jobs/{job['id']}/run")
        assert blocked_response.status_code == 200
        assert blocked_response.json()["data"]["status"] == "blocked"
        assert blocked_response.json()["data"]["result"]["reason"] == "Data source is disabled"
    finally:
        app_module.app.dependency_overrides.clear()


def test_active_amap_and_qweather_connectors_block_without_resolvable_credentials(monkeypatch):
    client, _ = make_test_client(monkeypatch)
    network_calls = []

    def fail_get(*args, **kwargs):
        network_calls.append((args, kwargs))
        raise AssertionError("Connector must not call the network without a resolved credential")

    monkeypatch.setattr(routes_module.requests, "get", fail_get)
    monkeypatch.delenv("DATA_CONNECTOR_SECRET_AMAP_PROD", raising=False)
    monkeypatch.delenv("DATA_CONNECTOR_SECRET_QWEATHER_PROD", raising=False)

    try:
        project = client.post(
            "/projects",
            json={"name": "连接器阻断项目", "city": "杭州"},
        ).json()["data"]
        sources = []
        for name, connector_key, credential_ref in (
            ("高德场馆与交通", "amap", "amap_prod"),
            ("和风天气", "qweather", "qweather_prod"),
        ):
            source_response = client.post(
                "/data-sources",
                json={
                    "name": name,
                    "source_kind": "authorized_api",
                    "connector_key": connector_key,
                    "status": "active",
                    "credential_ref": credential_ref,
                },
            )
            assert source_response.status_code == 200
            sources.append(source_response.json()["data"])

        for source in sources:
            health = client.post(f"/data-sources/{source['id']}/health-check")
            assert health.status_code == 200
            assert health.json()["data"]["can_fetch"] is False
            assert health.json()["data"]["reason"] == "Connector credential is not configured"
            job = client.post(
                "/external-data/jobs",
                json={
                    "project_id": project["id"],
                    "source_type": "api",
                    "provider": source["connector_key"],
                    "query": "杭州",
                    "parameters": {"data_source_id": source["id"]},
                },
            ).json()["data"]
            response = client.post(f"/external-data/jobs/{job['id']}/run")
            assert response.status_code == 200
            result = response.json()["data"]
            assert result["status"] == "blocked"
            assert result["result"]["network_called"] is False
            assert result["result"]["reason"] == "Connector credential is not configured"
    finally:
        app_module.app.dependency_overrides.clear()

    assert network_calls == []


def test_amap_connector_normalizes_venue_poi_response_without_exposing_credentials(monkeypatch):
    client, _ = make_test_client(monkeypatch)
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "1",
                "pois": [{
                    "id": "B0FFH0",
                    "name": "杭州奥体中心体育馆",
                    "address": "浙江省杭州市滨江区飞虹路3号",
                    "location": "120.217,30.229",
                    "type": "体育休闲服务;运动场馆",
                    "tel": "0571-00000000",
                }],
            }

    def fake_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(routes_module.requests, "get", fake_get)
    monkeypatch.setenv("DATA_CONNECTOR_SECRET_AMAP_PROD", "amap-secret")

    try:
        project = client.post(
            "/projects",
            json={"name": "高德场馆项目", "city": "杭州"},
        ).json()["data"]
        source = client.post(
            "/data-sources",
            json={
                "name": "高德场馆",
                "source_kind": "authorized_api",
                "connector_key": "amap",
                "status": "active",
                "credential_ref": "amap_prod",
            },
        ).json()["data"]
        job = client.post(
            "/external-data/jobs",
            json={
                "project_id": project["id"],
                "source_type": "api",
                "provider": "amap",
                "query": "杭州奥体中心",
                "purpose": "venue_search",
                "parameters": {
                    "data_source_id": source["id"],
                    "operation": "venue_search",
                    "city": "杭州",
                    "keywords": "奥体中心",
                },
            },
        ).json()["data"]

        response = client.post(f"/external-data/jobs/{job['id']}/run")
        assert response.status_code == 200
        result = response.json()["data"]
        assert result["status"] == "completed"
        assert result["result"]["asset"]["asset_type"] == "venue_registry"
        assert result["result"]["asset"]["status"] == "parsed"
        assert result["result"]["asset"]["records"][0] == {
            "id": result["result"]["asset"]["records"][0]["id"],
            "asset_id": result["result"]["asset"]["id"],
            "entity_type": "venue",
            "entity_id": "B0FFH0",
            "metric_key": "venue_poi",
            "value_json": {
                "name": "杭州奥体中心体育馆",
                "address": "浙江省杭州市滨江区飞虹路3号",
                "location": "120.217,30.229",
                "type": "体育休闲服务;运动场馆",
                "telephone": "0571-00000000",
            },
            "unit": "",
            "confidence": 90,
            "record_status": "observed",
            "lineage": {
                "connector_key": "amap",
                "operation": "venue_search",
                "source_id": source["id"],
            },
        }
        assert "amap-secret" not in str(result)
    finally:
        app_module.app.dependency_overrides.clear()

    assert calls == [{
        "url": "https://restapi.amap.com/v5/place/text",
        "params": {"key": "amap-secret", "keywords": "奥体中心", "city": "杭州"},
        "timeout": 10,
    }]


def test_qweather_connector_normalizes_daily_forecast_response_without_exposing_credentials(monkeypatch):
    client, _ = make_test_client(monkeypatch)
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "code": "200",
                "updateTime": "2026-10-10T09:00+08:00",
                "daily": [{
                    "fxDate": "2026-10-11",
                    "tempMax": "25",
                    "tempMin": "16",
                    "textDay": "晴",
                    "textNight": "多云",
                    "windScaleDay": "3",
                    "humidity": "60",
                }],
            }

    def fake_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(routes_module.requests, "get", fake_get)
    monkeypatch.setenv("DATA_CONNECTOR_SECRET_QWEATHER_PROD", "qweather-secret")

    try:
        project = client.post(
            "/projects",
            json={"name": "天气风险项目", "city": "杭州"},
        ).json()["data"]
        source = client.post(
            "/data-sources",
            json={
                "name": "和风天气",
                "source_kind": "authorized_api",
                "connector_key": "qweather",
                "status": "active",
                "credential_ref": "qweather_prod",
            },
        ).json()["data"]
        job = client.post(
            "/external-data/jobs",
            json={
                "project_id": project["id"],
                "source_type": "api",
                "provider": "qweather",
                "query": "杭州天气",
                "purpose": "weather_risk",
                "parameters": {
                    "data_source_id": source["id"],
                    "operation": "daily_forecast",
                    "location": "101210101",
                },
            },
        ).json()["data"]

        response = client.post(f"/external-data/jobs/{job['id']}/run")
        assert response.status_code == 200
        result = response.json()["data"]
        assert result["status"] == "completed"
        assert result["result"]["asset"]["asset_type"] == "weather_forecast"
        assert result["result"]["asset"]["records"][0]["entity_type"] == "city"
        assert result["result"]["asset"]["records"][0]["entity_id"] == "101210101"
        assert result["result"]["asset"]["records"][0]["metric_key"] == "weather_forecast_daily"
        assert result["result"]["asset"]["records"][0]["value_json"] == {
            "date": "2026-10-11",
            "temp_max": 25,
            "temp_min": 16,
            "text_day": "晴",
            "text_night": "多云",
            "wind_scale_day": "3",
            "humidity": 60,
        }
        assert result["result"]["asset"]["records"][0]["lineage"]["connector_key"] == "qweather"
        assert "qweather-secret" not in str(result)
    finally:
        app_module.app.dependency_overrides.clear()

    assert calls == [{
        "url": "https://devapi.qweather.com/v7/weather/3d",
        "params": {"key": "qweather-secret", "location": "101210101"},
        "timeout": 10,
    }]


def test_active_unmanaged_connector_keeps_existing_placeholder_execution(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        source = client.post(
            "/data-sources",
            json={
                "name": "主办方接口预留",
                "source_kind": "authorized_api",
                "connector_key": "organizer_files",
                "status": "active",
                "credential_ref": "organizer_secret_ref",
            },
        ).json()["data"]
        job = client.post(
            "/external-data/jobs",
            json={
                "source_type": "api",
                "provider": "organizer_files",
                "query": "同步主办方资料",
                "parameters": {"data_source_id": source["id"]},
            },
        ).json()["data"]

        response = client.post(f"/external-data/jobs/{job['id']}/run")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "completed"
        assert response.json()["data"]["result"]["requires_human_verification"] is True
    finally:
        app_module.app.dependency_overrides.clear()


def test_data_quality_issue_can_only_be_resolved_within_current_tenant(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        source = client.post(
            "/data-sources",
            json={
                "name": "质量核验来源",
                "source_kind": "manual",
                "connector_key": "organizer_files",
            },
        ).json()["data"]
        asset = client.post(
            "/data-assets",
            json={
                "data_source_id": source["id"],
                "asset_type": "contract",
            },
        ).json()["data"]

        from app.models import DataQualityIssue

        db = session_factory()
        try:
            tenant = app_module.get_or_create_default_context(db)[0]
            issue = DataQualityIssue(
                tenant_id=tenant.id,
                asset_id=asset["id"],
                issue_type="missing_field",
                severity="high",
                details={"field": "签约主体"},
            )
            db.add(issue)
            db.commit()
            db.refresh(issue)
            issue_id = issue.id
        finally:
            db.close()

        resolve_response = client.post(f"/data-quality-issues/{issue_id}/resolve")
        assert resolve_response.status_code == 200
        resolved = resolve_response.json()["data"]
        assert resolved["status"] == "resolved"
        assert resolved["resolved_by"] is not None
        assert resolved["resolved_at"] is not None
    finally:
        app_module.app.dependency_overrides.clear()


def test_monitoring_rule_creates_one_alert_notification_and_predefined_task(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        project = client.post(
            "/projects",
            json={"name": "预警项目", "artist_name": "测试艺人", "city": "上海"},
        ).json()["data"]
        source = client.post(
            "/data-sources",
            json={
                "name": "售票指标来源",
                "source_kind": "platform_metric",
                "connector_key": "ticketing_api",
            },
        ).json()["data"]
        client.post(
            "/data-assets",
            json={
                "project_id": project["id"],
                "data_source_id": source["id"],
                "asset_type": "ticketing",
                "records": [
                    {
                        "entity_type": "project",
                        "entity_id": str(project["id"]),
                        "metric_key": "refund_rate",
                        "value_json": {"value": 0.35},
                        "record_status": "observed",
                        "lineage": {"field": "退款率"},
                    },
                ],
            },
        )
        rule_response = client.post(
            "/monitoring-rules",
            json={
                "name": "退款率异常",
                "rule_type": "ticketing",
                "condition_json": {
                    "metric_key": "refund_rate",
                    "operator": "gt",
                    "threshold": 0.2,
                    "task_type": "verify_ticketing",
                },
                "severity_policy": "important",
                "notification_policy": {"recipients": ["project_owner"]},
            },
        )
        assert rule_response.status_code == 200
        rule = rule_response.json()["data"]

        first = client.post(f"/monitoring-rules/{rule['id']}/evaluate?project_id={project['id']}")
        assert first.status_code == 200
        assert first.json()["data"]["created"] is True
        alert = first.json()["data"]["alert"]
        assert alert["status"] == "open"
        assert alert["severity"] == "important"
        assert alert["task"]["title"] == "核验售票数据"

        second = client.post(f"/monitoring-rules/{rule['id']}/evaluate?project_id={project['id']}")
        assert second.status_code == 200
        assert second.json()["data"]["created"] is False
        alerts = client.get(f"/alerts?project_id={project['id']}&status=open")
        assert len(alerts.json()["data"]) == 1
    finally:
        app_module.app.dependency_overrides.clear()


def test_alert_can_be_acknowledged_then_resolved(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        project = client.post("/projects", json={"name": "预警状态项目"}).json()["data"]
        source = client.post(
            "/data-sources",
            json={"name": "预警状态来源", "source_kind": "manual", "connector_key": "ticketing_api"},
        ).json()["data"]
        client.post(
            "/data-assets",
            json={
                "project_id": project["id"],
                "data_source_id": source["id"],
                "asset_type": "ticketing",
                "records": [{
                    "entity_type": "project",
                    "entity_id": str(project["id"]),
                    "metric_key": "refund_rate",
                    "value_json": {"value": 0.3},
                }],
            },
        )
        rule = client.post(
            "/monitoring-rules",
            json={
                "name": "退款预警",
                "rule_type": "ticketing",
                "condition_json": {"metric_key": "refund_rate", "operator": "gt", "threshold": 0.2},
            },
        ).json()["data"]
        alert = client.post(
            f"/monitoring-rules/{rule['id']}/evaluate?project_id={project['id']}"
        ).json()["data"]["alert"]

        acknowledged = client.post(f"/alerts/{alert['id']}/acknowledge")
        assert acknowledged.status_code == 200
        assert acknowledged.json()["data"]["status"] == "acknowledged"
        resolved = client.post(f"/alerts/{alert['id']}/resolve")
        assert resolved.status_code == 200
        assert resolved.json()["data"]["status"] == "resolved"
        assert resolved.json()["data"]["resolved_at"] is not None
    finally:
        app_module.app.dependency_overrides.clear()


def test_project_work_events_are_idempotent_and_only_material_changes_refresh_the_plan(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        project = client.post(
            "/projects",
            json={
                "name": "项目陪跑测试",
                "artist_name": "测试艺人",
                "city": "杭州",
                "avg_ticket_price": 500,
                "artist_fee": 100000,
            },
        ).json()["data"]
        initial = client.post(
            f"/projects/{project['id']}/work-events",
            json={
                "event_type": "project_created",
                "business_key": "project-created",
                "payload": {"source": "manual"},
                "idempotency_key": "project-created-1",
            },
        )
        assert initial.status_code == 200
        initial_data = initial.json()["data"]
        assert initial_data["created"] is True
        assert initial_data["work_plan"]["version_no"] == 1
        assert initial_data["decision_snapshot"]["input_lineage"]["data_record_ids"] == []

        repeated = client.post(
            f"/projects/{project['id']}/work-events",
            json={
                "event_type": "project_created",
                "business_key": "project-created",
                "payload": {"source": "manual"},
                "idempotency_key": "project-created-1",
            },
        )
        assert repeated.status_code == 200
        assert repeated.json()["data"]["created"] is False
        assert repeated.json()["data"]["event"]["id"] == initial_data["event"]["id"]

        unchanged = client.post(
            f"/projects/{project['id']}/work-events",
            json={
                "event_type": "manual_review",
                "business_key": "same-input",
                "idempotency_key": "same-input-2",
            },
        )
        assert unchanged.status_code == 200
        assert unchanged.json()["data"]["work_plan_created"] is False
        assert unchanged.json()["data"]["work_plan"]["version_no"] == 1

        source = client.post(
            "/data-sources",
            json={"name": "陪跑资料", "source_kind": "manual", "connector_key": "organizer_files"},
        ).json()["data"]
        client.post(
            "/data-assets",
            json={
                "project_id": project["id"],
                "data_source_id": source["id"],
                "asset_type": "letter",
                "records": [{
                    "entity_type": "project",
                    "entity_id": str(project["id"]),
                    "metric_key": "approval_status",
                    "value_json": {"value": "pending"},
                    "lineage": {"field": "审批状态"},
                }],
            },
        )
        changed = client.post(
            f"/projects/{project['id']}/work-events",
            json={
                "event_type": "data_asset_received",
                "business_key": "letter-v1",
                "idempotency_key": "letter-v1-3",
            },
        )
        assert changed.status_code == 200
        assert changed.json()["data"]["work_plan_created"] is True
        assert changed.json()["data"]["work_plan"]["version_no"] == 2

        snapshots = client.get(f"/projects/{project['id']}/decision-snapshots")
        assert snapshots.status_code == 200
        assert len(snapshots.json()["data"]) == 3
        assert snapshots.json()["data"][0]["input_lineage"]["data_record_ids"]
        assert snapshots.json()["data"][0]["finance_result"] == initial_data["decision_snapshot"]["finance_result"]
    finally:
        app_module.app.dependency_overrides.clear()


def test_conversion_assumptions_require_evidence_and_calibration_candidates_need_approval(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project = client.post(
            "/projects",
            json={"name": "转化校准项目", "artist_name": "测试艺人", "city": "北京"},
        ).json()["data"]
        missing = client.get(f"/projects/{project['id']}/calibration")
        assert missing.status_code == 200
        assert missing.json()["data"]["status"] == "needs_assumption"
        assert missing.json()["data"]["conversion_assumption"] is None

        assumption_response = client.post(
            "/conversion-assumptions",
            json={
                "scope_type": "project",
                "scope_id": str(project["id"]),
                "funnel_stage_from": "want_to_see",
                "funnel_stage_to": "purchase",
                "rate": 0.12,
                "segment": {"city": "北京", "channel": "ticketing"},
                "evidence_ids": [101],
                "confidence": 80,
                "status": "active",
                "effective_from": "2026-01-01T00:00:00+00:00",
            },
        )
        assert assumption_response.status_code == 200
        assumption = assumption_response.json()["data"]
        assert assumption["rate"] == 0.12
        assert assumption["evidence_ids"] == [101]

        cases = client.post(
            "/case-outcomes",
            json={
                "title": "北京同规模已结算项目",
                "outcome_label": "success",
                "scenario": {"city": "北京"},
                "revenue": 1200000,
                "cost": 900000,
                "profit": 300000,
                "occupancy_rate": 0.82,
                "evidence_ids": [101],
            },
        )
        assert cases.status_code == 200
        assert client.get("/case-outcomes?city=北京").json()["data"][0]["title"] == "北京同规模已结算项目"

        from app.models import ForecastCalibration

        db = session_factory()
        try:
            tenant = app_module.get_or_create_default_context(db)[0]
            candidate = ForecastCalibration(
                tenant_id=tenant.id,
                project_id=project["id"],
                conversion_assumption_id=assumption["id"],
                forecast_metric="want_to_see_to_purchase",
                forecast_value=0.12,
                actual_value=0.09,
                error_value=-0.03,
                status="candidate",
                candidate_rate=0.09,
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            candidate_id = candidate.id
        finally:
            db.close()

        pending = client.get(f"/projects/{project['id']}/calibration")
        assert pending.json()["data"]["status"] == "pending_approval"
        assert pending.json()["data"]["candidate"]["status"] == "candidate"

        approved = client.post(f"/calibration-candidates/{candidate_id}/approve")
        assert approved.status_code == 200
        approved_data = approved.json()["data"]
        assert approved_data["candidate"]["status"] == "approved"
        assert approved_data["conversion_assumption"]["id"] != assumption["id"]
        assert approved_data["conversion_assumption"]["rate"] == 0.09
    finally:
        app_module.app.dependency_overrides.clear()


def test_document_parse_job_extracts_docx_and_writes_review_candidates(monkeypatch, tmp_path):
    client, session_factory = make_test_client(monkeypatch)
    docx_path = tmp_path / "venue-contract.docx"
    write_minimal_docx(
        docx_path,
        [
            "项目名称：杭州音乐节",
            "艺人：测试艺人",
            "城市：杭州",
            "场馆：城市公园",
            "档期：2026-10-01",
            "预计人数：20000",
            "平均票价：399",
            "审批：需补充营业性演出批文",
            "风险：雨季天气影响户外执行",
        ],
    )

    try:
        project_response = client.post(
            "/projects",
            json={"name": "DOCX 资料解析项目", "artist_name": "测试艺人", "city": "杭州"},
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        evidence_response = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "name": "场馆合同.docx",
                "file_url": str(docx_path),
                "evidence_type": "contract",
                "source": "venue",
            },
        )
        assert evidence_response.status_code == 200
        evidence = evidence_response.json()["data"]

        create_job_response = client.post(
            f"/evidences/{evidence['id']}/parse-jobs",
            json={"purpose": "project_evidence"},
        )
        assert create_job_response.status_code == 200
        job = create_job_response.json()["data"]
        assert job["status"] == "queued"
        assert job["file_kind"] == "docx"
        assert job["parse_scope"] == "single_project"

        run_response = client.post(f"/document-parse-jobs/{job['id']}/run")
        assert run_response.status_code == 200
        completed = run_response.json()["data"]
        assert completed["status"] == "completed"
        assert completed["result"]["requires_human_verification"] is True
        assert "杭州音乐节" in completed["result"]["extracted_text"]
        assert completed["result"]["candidate_facts"][0]["content"].startswith("项目名称：杭州音乐节")
        assert completed["result"]["created_records"]["facts"]
        assert completed["result"]["created_records"]["assumptions"]
        assert completed["result"]["created_records"]["risks"]
        assert completed["result"]["created_records"]["gates"]
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.DocumentParseJob).count() == 1
        fact = db.query(app_module.Fact).filter(app_module.Fact.project_id == project["id"]).one()
        assert fact.status == "pending"
        assert "杭州音乐节" in fact.content
        assert db.query(app_module.Assumption).filter(app_module.Assumption.project_id == project["id"]).one().status == "active"
        assert db.query(app_module.Risk).filter(app_module.Risk.project_id == project["id"]).one().status == "open"
        assert db.query(app_module.Gate).filter(app_module.Gate.project_id == project["id"]).one().status == "pending"
    finally:
        db.close()


def test_spreadsheet_parse_job_extracts_xlsx_candidates_and_confirms_multiple_projects(monkeypatch, tmp_path):
    client, session_factory = make_test_client(monkeypatch)
    xlsx_path = tmp_path / "tour-budget.xlsx"
    write_minimal_xlsx(
        xlsx_path,
        [
            ["项目名称", "艺人", "城市", "场馆", "档期", "预计人数", "平均票价", "艺人费", "场租", "宣发费", "制作费"],
            ["巡演北京站", "测试艺人", "北京", "北京场馆", "2026-10-01", 12000, 680, 2000000, 800000, 500000, 700000],
            ["巡演上海站", "测试艺人", "上海", "上海场馆", "2026-10-08", 10000, 780, 2100000, 900000, 550000, 750000],
        ],
    )

    try:
        host_project_response = client.post(
            "/projects",
            json={"name": "巡演批量导入", "artist_name": "测试艺人", "city": "全国"},
        )
        assert host_project_response.status_code == 200
        host_project = host_project_response.json()["data"]

        evidence_response = client.post(
            "/evidences/upload",
            json={
                "project_id": host_project["id"],
                "name": "巡演城市预算表.xlsx",
                "file_url": str(xlsx_path),
                "evidence_type": "spreadsheet",
                "source": "finance",
            },
        )
        assert evidence_response.status_code == 200
        evidence = evidence_response.json()["data"]

        job_response = client.post(
            f"/evidences/{evidence['id']}/parse-jobs",
            json={"parse_scope": "batch_projects", "purpose": "tour_budget_import"},
        )
        assert job_response.status_code == 200
        job = job_response.json()["data"]
        assert job["file_kind"] == "spreadsheet"
        assert job["parse_scope"] == "batch_projects"

        run_response = client.post(f"/document-parse-jobs/{job['id']}/run")
        assert run_response.status_code == 200
        parsed = run_response.json()["data"]
        assert len(parsed["result"]["candidate_projects"]) == 2
        assert parsed["result"]["candidate_projects"][0]["name"] == "巡演北京站"
        assert parsed["result"]["candidate_projects"][0]["venue_cost"] == 800000
        assert parsed["result"]["field_mapping"]["艺人"] == "artist_name"
        assert parsed["result"]["requires_mapping_confirmation"] is True

        confirm_response = client.post(f"/document-parse-jobs/{job['id']}/confirm-projects")
        assert confirm_response.status_code == 200
        confirmed = confirm_response.json()["data"]
        assert len(confirmed["projects"]) == 2
        assert {project["city"] for project in confirmed["projects"]} == {"北京", "上海"}
        assert all(project["current_version_id"] for project in confirmed["projects"])
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.DocumentParseJob).count() == 1
        assert db.query(app_module.Project).filter(app_module.Project.artist_name == "测试艺人").count() == 3
        project_ids = [project.id for project in db.query(app_module.Project).filter(app_module.Project.artist_name == "测试艺人").all()]
        assert db.query(app_module.ProjectVersion).filter(app_module.ProjectVersion.project_id.in_(project_ids)).count() == 3
    finally:
        db.close()


def test_project_analysis_job_builds_human_review_recommendation(monkeypatch, tmp_path):
    client, session_factory = make_test_client(monkeypatch)
    docx_path = tmp_path / "analysis-source.docx"
    write_minimal_docx(
        docx_path,
        [
            "项目名称：杭州音乐节",
            "艺人：测试艺人",
            "风险：雨季天气影响户外执行",
            "审批：需补充营业性演出批文",
        ],
    )

    try:
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
        project = project_response.json()["data"]
        finance_response = client.post(
            "/finance/calculate",
            json={
                "project_id": project["id"],
                "expected_attendance": 20000,
                "avg_ticket_price": 399,
                "artist_fee": 2600000,
                "venue_cost": 900000,
                "marketing_cost": 500000,
                "production_cost": 1200000,
            },
        )
        assert finance_response.status_code == 200

        evidence_response = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "name": "项目资料.docx",
                "file_url": str(docx_path),
                "evidence_type": "document",
                "source": "operator",
            },
        )
        evidence = evidence_response.json()["data"]
        parse_job = client.post(f"/evidences/{evidence['id']}/parse-jobs", json={}).json()["data"]
        assert client.post(f"/document-parse-jobs/{parse_job['id']}/run").status_code == 200

        external_response = client.post(
            "/external-data/jobs",
            json={
                "project_id": project["id"],
                "source_type": "web",
                "provider": "mcp",
                "query": "杭州 音乐节 天气 交通 舆情",
                "purpose": "market_risk",
            },
        )
        external_job = external_response.json()["data"]
        assert client.post(f"/external-data/jobs/{external_job['id']}/run").status_code == 200

        create_response = client.post(
            f"/projects/{project['id']}/analysis-jobs",
            json={"purpose": "investment_decision"},
        )
        assert create_response.status_code == 200
        analysis_job = create_response.json()["data"]
        assert analysis_job["status"] == "completed"
        assert analysis_job["version_id"] == finance_response.json()["data"]["version_id"]
        assert analysis_job["result"]["requires_human_verification"] is True
        assert analysis_job["result"]["recommendation"] in {"advance", "conditional_advance", "pause", "reject"}
        assert analysis_job["result"]["inputs"]["facts"]["pending"] >= 1
        assert analysis_job["result"]["inputs"]["risks"]["open"] >= 1
        assert analysis_job["result"]["human_review_questions"]

        get_response = client.get(f"/projects/{project['id']}/analysis-jobs/{analysis_job['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["data"]["id"] == analysis_job["id"]
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.ProjectAnalysisJob).count() == 1
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
    assert calls[0]["json"]["chat_template_kwargs"] == {"enable_thinking": False}
    prompt = calls[0]["json"]["messages"][0]["content"]
    assert prompt.startswith("/no_think")
    assert "本次创作批次" in prompt
    assert "完整宣发方案" in prompt
    assert "传播定位" in prompt
    assert "短视频脚本" in prompt
    assert "禁止编造" in prompt
    assert calls[0]["timeout"] == config_module.LLAMA_SERVER_TIMEOUT_SECONDS

    db = session_factory()
    try:
        generation = db.query(app_module.AIGeneration).one()
        assert generation.result == "Local llama copy"
    finally:
        db.close()


def test_extract_llama_server_text_does_not_expose_reasoning_content():
    assert routes_module.extract_llama_server_text({
        "choices": [
            {"message": {"content": "", "reasoning_content": "Reasoning model output"}}
        ]
    }) is None


def test_ai_generate_strips_think_blocks_from_final_result(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "<think>internal reasoning</think>\n传播定位\n最终文案"}}
                ]
            }

    monkeypatch.setattr(routes_module.requests, "post", lambda *args, **kwargs: FakeResponse())

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        response = TestClient(app_module.app).post(
            "/ai/generate",
            json={"type": "poster", "show_name": "见面会", "artist": "大牛", "city": "上海"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()["data"]["result"]
    assert "<think>" not in result
    assert "internal reasoning" not in result
    assert result == "传播定位\n最终文案"


def test_ai_generate_stream_returns_sse_progress_and_clean_final(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")

    class FakeStreamResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=False):
            lines = [
                'data: {"choices":[{"delta":{"reasoning_content":"先定位目标客群"}}]}'.encode("utf-8"),
                'data: {"choices":[{"delta":{"content":"<think>判断传播角度</think>传播定位"}}]}'.encode("utf-8"),
                'data: {"choices":[{"delta":{"content":"\\n最终文案：村庄见面会"}}]}'.encode("utf-8"),
                b'data: [DONE]',
            ]
            yield from lines

    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        return FakeStreamResponse()

    monkeypatch.setattr(routes_module.requests, "post", fake_post)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        with TestClient(app_module.app).stream(
            "POST",
            "/ai/generate/stream",
            json={"type": "poster", "show_name": "见面会", "artist": "大牛", "city": "上海"},
        ) as response:
            body = response.read().decode("utf-8")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"event": "progress"' in body
    assert '"event": "thought"' in body
    assert '"event": "final"' in body
    assert "先定位目标客群" in body
    assert "判断传播角度" in body
    assert "<think>" not in body
    assert "传播定位\\n最终文案：村庄见面会" in body
    assert calls[0]["json"]["stream"] is True


def test_ai_generate_stream_moves_plain_analysis_preamble_to_thought(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_TOKEN", raising=False)
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")

    class FakeStreamResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=False):
            lines = [
                'data: {"choices":[{"delta":{"content":"我们需要先判断传播策略。"}}]}'.encode("utf-8"),
                'data: {"choices":[{"delta":{"content":"传播定位\\n最终文案"}}]}'.encode("utf-8"),
                b'data: [DONE]',
            ]
            yield from lines

    monkeypatch.setattr(routes_module.requests, "post", lambda *args, **kwargs: FakeStreamResponse())

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        with TestClient(app_module.app).stream(
            "POST",
            "/ai/generate/stream",
            json={"type": "poster", "show_name": "见面会", "artist": "大牛", "city": "上海"},
        ) as response:
            body = response.read().decode("utf-8")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert '"event": "thought"' in body
    assert "我们需要先判断传播策略" in body
    assert '"result": "传播定位\\n最终文案"' in body


def test_ai_generate_returns_cached_result_from_redis(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")
    monkeypatch.setattr(
        routes_module,
        "redis_get_json",
        lambda key: {"status": "completed", "result": "Redis cached copy"},
    )
    monkeypatch.setattr(routes_module, "redis_set_json", lambda *args, **kwargs: None)

    def fail_post(*args, **kwargs):
        raise AssertionError("llama server should not be called on cache hit")

    monkeypatch.setattr(routes_module.requests, "post", fail_post)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        response = TestClient(app_module.app).post(
            "/ai/generate",
            json={
                "type": "poster",
                "show_name": "见面会",
                "artist": "大牛",
                "city": "上海",
                "generation_nonce": "same-request",
            },
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"] == {"result": "Redis cached copy", "cache_hit": True}


def test_ai_generate_stream_returns_cached_thought_and_result_from_redis(monkeypatch):
    session_factory = make_temp_session(monkeypatch)
    app_module.init_db()
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")
    monkeypatch.setattr(
        routes_module,
        "redis_get_json",
        lambda key: {
            "status": "completed",
            "thought": "缓存中的思考过程",
            "result": "缓存中的最终文案",
        },
    )
    monkeypatch.setattr(routes_module, "redis_set_json", lambda *args, **kwargs: None)

    def fail_post(*args, **kwargs):
        raise AssertionError("llama server should not be called on cache hit")

    monkeypatch.setattr(routes_module.requests, "post", fail_post)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    try:
        with TestClient(app_module.app).stream(
            "POST",
            "/ai/generate/stream",
            json={
                "type": "poster",
                "show_name": "见面会",
                "artist": "大牛",
                "city": "上海",
                "generation_nonce": "same-request",
            },
        ) as response:
            body = response.read().decode("utf-8")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "命中 Redis 生成缓存" in body
    assert '"event": "thought"' in body
    assert "缓存中的思考过程" in body
    assert '"result": "缓存中的最终文案"' in body


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


def test_dashboard_analytics_uses_live_platform_data(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={
                "name": "看板验证项目",
                "artist_name": "周杰伦",
                "city": "北京",
                "venue": "国家体育场",
                "schedule": "2026-09-10",
                "expected_attendance": 1000,
                "avg_ticket_price": 500,
                "artist_fee": 100000,
                "venue_cost": 60000,
                "marketing_cost": 20000,
                "production_cost": 50000,
            },
        )
        project = project_response.json()["data"]

        finance_response = client.post(
            "/finance/calculate",
            json={
                "project_id": project["id"],
                "expected_attendance": 1000,
                "avg_ticket_price": 500,
                "artist_fee": 100000,
                "venue_cost": 60000,
                "marketing_cost": 20000,
                "production_cost": 50000,
            },
        )
        assert finance_response.status_code == 200

        task_response = client.post(
            "/tasks",
            json={"project_id": project["id"], "title": "核对票务通道"},
        )
        assert task_response.status_code == 200

        show_response = client.get("/shows")
        show_id = show_response.json()["data"][0]["id"]
        order_response = client.post(
            f"/shows/{show_id}/order",
            json={"name": "观众一", "phone": "13800000000"},
        )
        assert order_response.status_code == 200

        analytics_response = client.get("/analytics/dashboard")
    finally:
        app_module.app.dependency_overrides.clear()

    assert analytics_response.status_code == 200
    data = analytics_response.json()["data"]
    assert data["summary"]["active_projects"] >= 1
    assert data["summary"]["pending_tasks"] >= 1
    assert data["summary"]["reservations"] == 1
    assert data["summary"]["on_sale_shows"] == 3
    assert data["summary"]["neutral_profit_total"] == 270000
    assert any(item["key"] == "neutral_profit_total" for item in data["metrics"])


def test_ticketing_summary_lists_show_reservations(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        shows_response = client.get("/shows")
        show = shows_response.json()["data"][0]
        order_response = client.post(
            f"/shows/{show['id']}/order",
            json={"name": "票务用户", "phone": "13900000000"},
        )
        assert order_response.status_code == 200

        summary_response = client.get("/ticketing/summary")
    finally:
        app_module.app.dependency_overrides.clear()

    assert summary_response.status_code == 200
    data = summary_response.json()["data"]
    assert data["summary"]["total_shows"] == 3
    assert data["summary"]["on_sale_shows"] == 3
    assert data["summary"]["reservation_count"] == 1
    assert data["shows"][0]["reservation_count"] == 1
    assert data["orders"][0]["show_title"] == show["title"]
    assert data["orders"][0]["phone"] == "13900000000"


def test_root_login_and_user_management(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        login_response = login_with_captcha(client, monkeypatch, "root", "123456")
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

        brand_login = login_with_captcha(client, monkeypatch, "brand-user", "abc123")
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

        old_password_login = login_with_captcha(client, monkeypatch, "brand-user", "abc123")
        assert old_password_login.status_code == 401

        new_password_login = login_with_captcha(client, monkeypatch, "brand-user", "newpass123")
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
            response = login_with_captcha(client, monkeypatch, account, "123456")
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


def test_batch_task_actions_only_update_selected_tasks(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project = client.post(
            "/projects",
            json={"name": "批量任务项目", "artist_name": "测试艺人", "city": "北京"},
        ).json()["data"]
        tasks = [
            client.post(
                "/tasks",
                json={
                    "project_id": project["id"],
                    "title": title,
                    "description": f"{title}详情",
                },
            ).json()["data"]
            for title in ["任务一", "任务二", "任务三"]
        ]

        response = client.post(
            "/tasks/actions/batch",
            json={
                "task_ids": [tasks[0]["id"], tasks[2]["id"]],
                "action": "accept",
            },
        )

        assert response.status_code == 200
        result = response.json()["data"]
        assert result["action"] == "accept"
        assert result["updated_count"] == 2
        assert {task["id"] for task in result["tasks"]} == {
            tasks[0]["id"],
            tasks[2]["id"],
        }
        assert all(task["status"] == "in_progress" for task in result["tasks"])
        assert all(task["assignee_id"] is not None for task in result["tasks"])
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        persisted = {
            task.id: task
            for task in db.query(app_module.Task).filter(
                app_module.Task.id.in_([task["id"] for task in tasks]),
            ).all()
        }
        assert persisted[tasks[0]["id"]].status == "in_progress"
        assert persisted[tasks[1]["id"]].status == "pending"
        assert persisted[tasks[1]["id"]].assignee_id is None
        assert persisted[tasks[2]["id"]].status == "in_progress"
    finally:
        db.close()


def test_batch_reject_returns_tasks_to_pending_and_records_reason(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project = client.post(
            "/projects",
            json={"name": "拒绝任务项目", "artist_name": "测试艺人", "city": "上海"},
        ).json()["data"]
        task = client.post(
            "/tasks",
            json={
                "project_id": project["id"],
                "title": "核验场馆",
                "description": "核验场馆档期和报价",
            },
        ).json()["data"]
        accepted = client.post(
            "/tasks/actions/batch",
            json={"task_ids": [task["id"]], "action": "accept"},
        )
        assert accepted.status_code == 200

        rejected = client.post(
            "/tasks/actions/batch",
            json={
                "task_ids": [task["id"]],
                "action": "reject",
                "reason": "当前档期冲突",
            },
        )

        assert rejected.status_code == 200
        rejected_task = rejected.json()["data"]["tasks"][0]
        assert rejected_task["status"] == "pending"
        assert rejected_task["assignee_id"] is None
        assert rejected_task["assignee_name"] is None
        assert rejected_task["rejection_reason"] == "当前档期冲突"
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        persisted = db.query(app_module.Task).filter(app_module.Task.id == task["id"]).one()
        assert persisted.status == "pending"
        assert persisted.assignee_id is None
        assert persisted.rejection_reason == "当前档期冲突"
    finally:
        db.close()


def fetch_login_captcha(client, monkeypatch, code="AB12"):
    monkeypatch.setattr(routes_module, "generate_captcha_code", lambda length=4: code)
    response = client.get("/auth/captcha")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["captcha_id"]
    assert payload["captcha_image"].startswith("data:image/svg+xml")
    assert payload["expires_in_seconds"] == 300
    return payload


def login_with_captcha(client, monkeypatch, account, password, *, generated_code="AB12", captcha_code=None, headers=None):
    captcha = fetch_login_captcha(client, monkeypatch, generated_code)
    response = client.post(
        "/auth/web-login",
        json={
            "account": account,
            "password": password,
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha_code or generated_code,
        },
        headers=headers or {},
    )
    return response


def test_web_login_requires_valid_backend_captcha(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        invalid_captcha_login = login_with_captcha(
            client,
            monkeypatch,
            "root",
            "123456",
            generated_code="Z9K2",
            captcha_code="WRNG",
        )
        assert invalid_captcha_login.status_code == 401
        assert invalid_captcha_login.json()["detail"] == "Invalid captcha"

        valid_captcha_login = login_with_captcha(
            client,
            monkeypatch,
            "root",
            "123456",
            generated_code="Z9K2",
        )
        assert valid_captcha_login.status_code == 200
        assert valid_captcha_login.json()["data"]["user"]["account"] == "root"
    finally:
        app_module.app.dependency_overrides.clear()


def test_phase1_project_decision_flow(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        login_response = login_with_captcha(
            client,
            monkeypatch,
            "root",
            "123456",
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
        assert task["project_name"] == "北京大型演唱会测算"
        assert task["assignee_name"] is None
        assert task["evidence_count"] == 0

        tasks_response = client.get(f"/tasks?project_id={project['id']}")
        assert tasks_response.status_code == 200
        assert tasks_response.json()["data"][0]["title"] == "确认场地安全资料"
        assert tasks_response.json()["data"][0]["project_name"] == "北京大型演唱会测算"
        assert tasks_response.json()["data"][0]["evidence_count"] == 0
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        assert db.query(app_module.Project).filter(app_module.Project.name == "北京大型演唱会测算").count() == 1
        assert db.query(app_module.ProjectVersion).filter(app_module.ProjectVersion.project_id == project["id"]).count() == 2
        assert db.query(app_module.Decision).filter(app_module.Decision.project_id == project["id"]).count() == 1
        assert db.query(app_module.Task).filter(app_module.Task.project_id == project["id"]).count() == 1
    finally:
        db.close()


def test_project_feasibility_report_generates_docx_and_evidence(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={
                "name": "北京大型演唱会可研",
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

        fact_response = client.post(
            "/facts",
            json={
                "project_id": project["id"],
                "title": "场地方已确认档期",
                "content": "档期锁定 2026-09-10",
                "source": "venue",
            },
        )
        assert fact_response.status_code == 200
        risk_response = client.post(
            "/risks",
            json={
                "project_id": project["id"],
                "title": "审批进度风险",
                "level": "medium",
                "mitigation": "提前准备营业性演出批文材料",
            },
        )
        assert risk_response.status_code == 200

        report_response = client.post(
            f"/projects/{project['id']}/feasibility-report",
            json={
                "tax_fee_rate": 0.15,
                "sponsorship_income": 1000000,
                "merchandise_income": 500000,
                "use_ai_copy": False,
            },
        )
        assert report_response.status_code == 200
        report = report_response.json()["data"]
        assert report["project_id"] == project["id"]
        assert report["evidence"]["evidence_type"] == "feasibility_report"
        assert report["evidence"]["file_url"].startswith("oss://local-placeholder/")
        assert report["download_url"].startswith("/reports/files/")
        assert report["file_name"].endswith(".docx")
        assert report["calculation_result"]["formula_version"] == "feasibility-v1"
        assert report["calculation_result"]["scenarios"]["neutral"]["occupancy_rate"] == 0.8
        assert report["calculation_result"]["scenarios"]["neutral"]["gross_ticket_revenue"] == 26112000
        assert report["calculation_result"]["scenarios"]["neutral"]["net_ticket_revenue"] == 22195200
        assert report["calculation_result"]["scenarios"]["neutral"]["total_income"] == 23695200
        assert report["calculation_result"]["scenarios"]["neutral"]["net_profit"] == 1095200
        assert report["calculation_result"]["breakeven_occupancy_rate"] == 0.8146

        download_response = client.get(report["download_url"])
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    finally:
        app_module.app.dependency_overrides.clear()

    db = session_factory()
    try:
        evidence = db.query(app_module.Evidence).filter(
            app_module.Evidence.project_id == project["id"],
            app_module.Evidence.evidence_type == "feasibility_report",
        ).one()
        assert evidence.name.endswith(".docx")
        assert evidence.meta["calculation_result"]["scenarios"]["neutral"]["net_profit"] == 1095200
        assert Path(evidence.meta["local_path"]).exists()
    finally:
        db.close()


def test_project_feasibility_report_requires_complete_finance_inputs(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={
                "name": "缺参数项目",
                "artist_name": "测试艺人",
                "city": "北京",
                "expected_attendance": 48000,
                "avg_ticket_price": 680,
            },
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]

        report_response = client.post(f"/projects/{project['id']}/feasibility-report", json={})
        assert report_response.status_code == 400
        assert report_response.json()["detail"]["status"] == "pending_input"
        assert "artist_fee" in report_response.json()["detail"]["missing_fields"]
    finally:
        app_module.app.dependency_overrides.clear()


def test_full_backend_plan_api_flow(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)
    monkeypatch.setattr(
        routes_module,
        "exchange_wechat_login_code",
        lambda login_code, _request=None: {"openid": "wx-openid-001", "unionid": "wx-union-001", "session_key": "session-key"},
    )
    monkeypatch.setattr(
        routes_module,
        "fetch_wechat_phone_number",
        lambda phone_code, _request=None: "13800000000",
    )

    try:
        db = session_factory()
        operator = db.query(app_module.User).filter(app_module.User.account == "b_user").one()
        operator.phone = "13800000000"
        db.commit()
        db.close()

        wechat_response = client.post(
            "/auth/wechat-login",
            json={"code": "wx-code-001", "phone_code": "wx-phone-code-001", "name": "微信用户"},
        )
        assert wechat_response.status_code == 200
        wechat_data = wechat_response.json()["data"]
        assert wechat_data["source"] == "wechat"
        assert wechat_data["user"]["phone"] == "13800000000"
        assert wechat_data["user"]["account"] == "b_user"

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
        accept_response = client.post(f"/tasks/{task['id']}/accept")
        assert accept_response.status_code == 200
        accepted_task = accept_response.json()["data"]
        assert accepted_task["status"] == "in_progress"
        assert accepted_task["assignee_id"] is not None
        assert accepted_task["project_name"] == "杭州音乐节"

        submit_response = client.post(
            f"/tasks/{task['id']}/submit",
            json={"result": "审批材料已提交", "evidence_ids": [evidence["id"]]},
        )
        assert submit_response.status_code == 200
        submitted_task = submit_response.json()["data"]
        assert submitted_task["status"] == "submitted"
        assert submitted_task["evidence_ids"] == [evidence["id"]]
        assert submitted_task["project_name"] == "杭州音乐节"
        assert submitted_task["evidence_count"] == 1

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
        assert db.query(app_module.Fact).filter(app_module.Fact.project_id == project["id"]).count() == 1
        assert db.query(app_module.Evidence).filter(app_module.Evidence.project_id == project["id"]).count() == 1
        assert db.query(app_module.Assumption).filter(app_module.Assumption.project_id == project["id"]).count() == 1
        assert db.query(app_module.Gate).filter(app_module.Gate.project_id == project["id"]).count() == 1
        assert db.query(app_module.Risk).filter(app_module.Risk.project_id == project["id"]).count() == 1
        assert db.query(app_module.ReportShare).filter(app_module.ReportShare.project_id == project["id"]).count() == 1
    finally:
        db.close()


def test_show_recommendations_use_user_order_history(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    db = session_factory()
    try:
        jay_beijing = db.query(app_module.Show).filter(app_module.Show.title == "周杰伦·北京演唱会").one()
        jay_shanghai = app_module.Show(
            title="周杰伦·上海加场",
            artist_name="周杰伦",
            city="上海",
            date="2026-10-01",
            venue="上海体育场",
            price="580-1580",
            status="on_sale",
            description="周杰伦巡演上海加场",
        )
        mayday_beijing = app_module.Show(
            title="五月天·北京演唱会",
            artist_name="五月天",
            city="北京",
            date="2026-11-01",
            venue="国家体育馆",
            price="480-1280",
            status="on_sale",
            description="五月天北京站",
        )
        db.add_all([jay_shanghai, mayday_beijing])
        db.flush()
        db.add(app_module.Order(show_id=jay_beijing.id, name="观众A", phone="13800000000"))
        db.commit()
    finally:
        db.close()

    try:
        response = client.get("/shows/recommendations?phone=13800000000")
        assert response.status_code == 200
        recommendations = response.json()["data"]
        assert recommendations[0]["title"] == "周杰伦·上海加场"
        assert "你预约过周杰伦相关演出" in recommendations[0]["recommendation_reason"]
        assert all(item["title"] != "周杰伦·北京演唱会" for item in recommendations)
        assert any(item["title"] == "五月天·北京演唱会" and "你关注过北京场次" in item["recommendation_reason"] for item in recommendations)
    finally:
        app_module.app.dependency_overrides.clear()


def test_show_recommendations_fall_back_to_popular_shows_without_history(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)

    db = session_factory()
    try:
        mayday = db.query(app_module.Show).filter(app_module.Show.title == "五月天·上海演唱会").one()
        db.add_all([
            app_module.Order(show_id=mayday.id, name="观众A", phone="13800000001"),
            app_module.Order(show_id=mayday.id, name="观众B", phone="13800000002"),
        ])
        db.commit()
    finally:
        db.close()

    try:
        response = client.get("/shows/recommendations?phone=13999999999")
        assert response.status_code == 200
        recommendations = response.json()["data"]
        assert recommendations[0]["title"] == "五月天·上海演唱会"
        assert recommendations[0]["recommendation_reason"] == "近期预约热度较高"
    finally:
        app_module.app.dependency_overrides.clear()


def test_show_poster_prefers_uploaded_image_evidence_and_falls_back_to_ai(monkeypatch):
    client, _ = make_test_client(monkeypatch)

    try:
        project_response = client.post(
            "/projects",
            json={
                "name": "周杰伦北京站资料",
                "artist_name": "周杰伦",
                "city": "北京",
                "venue": "鸟巢",
            },
        )
        assert project_response.status_code == 200
        project = project_response.json()["data"]
        evidence_response = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "name": "用户上传海报",
                "file_url": "https://oss.example.com/posters/jay-beijing.jpg",
                "evidence_type": "image",
                "source": "user_upload",
            },
        )
        assert evidence_response.status_code == 200

        response = client.get("/shows")
        assert response.status_code == 200
        shows = response.json()["data"]
        jay = next(show for show in shows if show["title"] == "周杰伦·北京演唱会")
        mayday = next(show for show in shows if show["title"] == "五月天·上海演唱会")
        assert jay["poster_url"] == "https://oss.example.com/posters/jay-beijing.jpg"
        assert mayday["poster_url"].startswith("https://copilot-cn.bytedance.net/api/ide/v1/text_to_image?")
        assert "landscape_4_3" in mayday["poster_url"]
    finally:
        app_module.app.dependency_overrides.clear()


def test_wechat_login_rejects_unbound_phone_number(monkeypatch):
    client, _ = make_test_client(monkeypatch)
    monkeypatch.setattr(
        routes_module,
        "exchange_wechat_login_code",
        lambda login_code, _request=None: {"openid": "wx-openid-unbound", "unionid": "wx-union-unbound", "session_key": "session-key"},
    )
    monkeypatch.setattr(
        routes_module,
        "fetch_wechat_phone_number",
        lambda phone_code, _request=None: "13911112222",
    )

    try:
        response = client.post(
            "/auth/wechat-login",
            json={"code": "wx-code-unbound", "phone_code": "wx-phone-unbound", "name": "未绑定用户"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Phone number is not linked to any account"
    finally:
        app_module.app.dependency_overrides.clear()


def test_wechat_login_uses_local_mock_phone_when_wechat_credentials_are_missing(monkeypatch):
    monkeypatch.delenv("WECHAT_MINIAPP_APPID", raising=False)
    monkeypatch.delenv("WECHAT_MINIAPP_SECRET", raising=False)
    monkeypatch.setenv("WECHAT_MINIAPP_MOCK_PHONE_NUMBER", "13800000000")
    client, session_factory = make_test_client(monkeypatch)

    try:
        db = session_factory()
        user = db.query(app_module.User).filter(app_module.User.account == "b_user").one()
        user.phone = "13800000000"
        db.commit()
        db.close()

        response = client.post(
            "/auth/wechat-login",
            json={"code": "local-dev-login-code", "phone_code": "local-dev-phone-code", "name": "本地微信用户"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["source"] == "wechat"
        assert data["user"]["account"] == "b_user"
        assert data["user"]["phone"] == "13800000000"
    finally:
        app_module.app.dependency_overrides.clear()


def test_wechat_login_allows_local_devtools_placeholders_without_env_mock(monkeypatch):
    monkeypatch.delenv("WECHAT_MINIAPP_APPID", raising=False)
    monkeypatch.delenv("WECHAT_MINIAPP_SECRET", raising=False)
    monkeypatch.delenv("WECHAT_MINIAPP_MOCK_PHONE_NUMBER", raising=False)
    client, session_factory = make_test_client(monkeypatch)

    try:
        db = session_factory()
        user = db.query(app_module.User).filter(app_module.User.account == "b_user").one()
        user.phone = "13800000000"
        db.commit()
        db.close()

        response = client.post(
            "/auth/wechat-login",
            json={
                "code": "local-devtools-login-code",
                "phone_code": "local-devtools-phone-code",
                "name": "开发工具用户",
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["source"] == "wechat"
        assert data["user"]["account"] == "b_user"
        assert data["user"]["phone"] == "13800000000"
    finally:
        app_module.app.dependency_overrides.clear()


def test_wechat_login_allows_any_local_request_without_wechat_credentials(monkeypatch):
    monkeypatch.delenv("WECHAT_MINIAPP_APPID", raising=False)
    monkeypatch.delenv("WECHAT_MINIAPP_SECRET", raising=False)
    monkeypatch.delenv("WECHAT_MINIAPP_MOCK_PHONE_NUMBER", raising=False)
    client, session_factory = make_test_client(monkeypatch)

    try:
        db = session_factory()
        user = db.query(app_module.User).filter(app_module.User.account == "b_user").one()
        user.phone = "13800000000"
        db.commit()
        db.close()

        response = client.post(
            "/auth/wechat-login",
            json={"code": "wx-devtools-code", "phone_code": "wx-devtools-phone", "name": "开发工具用户"},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user"]["account"] == "b_user"
        assert data["user"]["phone"] == "13800000000"
    finally:
        app_module.app.dependency_overrides.clear()
