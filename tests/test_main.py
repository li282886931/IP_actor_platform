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
        assert db.query(app_module.Fact).filter(app_module.Fact.project_id == project["id"]).count() == 1
        assert db.query(app_module.Evidence).filter(app_module.Evidence.project_id == project["id"]).count() == 1
        assert db.query(app_module.Assumption).filter(app_module.Assumption.project_id == project["id"]).count() == 1
        assert db.query(app_module.Gate).filter(app_module.Gate.project_id == project["id"]).count() == 1
        assert db.query(app_module.Risk).filter(app_module.Risk.project_id == project["id"]).count() == 1
        assert db.query(app_module.ReportShare).filter(app_module.ReportShare.project_id == project["id"]).count() == 1
    finally:
        db.close()
