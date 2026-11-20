import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

import main as app_module
import app.database as db_module
from app.documents.parsers import build_candidate_projects_from_sheets
from app.documents.parsers import parse_document_evidence
from app.integrations import object_storage
from app.services.auth import create_session_token


def make_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "llama-server")
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
    app_module.init_db()

    def override_db():
        with session_factory() as db:
            yield db

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    return TestClient(app_module.app), session_factory


def create_csv_job(client, tmp_path: Path):
    csv_path = tmp_path / "tour.csv"
    csv_path.write_text(
        "项目名称,预算城市,艺人,场馆\n北京首演,北京,测试艺人,北京剧院\n上海加场,上海,测试艺人,上海剧院\n",
        encoding="utf-8",
    )
    project = client.post(
        "/projects",
        json={"name": "批量导入容器项目", "artist_name": "测试艺人", "city": "全国"},
    ).json()["data"]
    evidence = client.post(
        "/evidences/upload",
        json={
            "project_id": project["id"],
            "name": "tour.csv",
            "file_url": str(csv_path),
            "evidence_type": "spreadsheet",
        },
    ).json()["data"]
    job = client.post(
        f"/evidences/{evidence['id']}/parse-jobs",
        json={"parse_scope": "batch_projects"},
    ).json()["data"]
    run = client.post(f"/document-parse-jobs/{job['id']}/run")
    assert run.status_code == 200
    return run.json()["data"]


def test_confirmed_mapping_rebuilds_candidates_and_rejects_duplicate_targets():
    sheets = [{
        "name": "巡演",
        "rows": [
            ["项目名称", "预算城市", "艺人"],
            ["北京首演", "北京", "测试艺人"],
        ],
    }]

    candidates, mapping = build_candidate_projects_from_sheets(
        sheets,
        {"巡演": {"项目名称": "name", "预算城市": "city", "艺人": "artist_name"}},
    )

    assert mapping["巡演"]["预算城市"] == "city"
    assert candidates == [{
        "name": "北京首演",
        "city": "北京",
        "artist_name": "测试艺人",
        "type": "concert",
        "source_sheet": "巡演",
        "source_row": 2,
    }]

    with pytest.raises(ValueError, match="重复目标字段"):
        build_candidate_projects_from_sheets(
            sheets,
            {"巡演": {"项目名称": "name", "预算城市": "name", "艺人": "artist_name"}},
        )


def test_mapping_confirmation_selection_override_and_idempotency(monkeypatch, tmp_path):
    client, session_factory = make_client(monkeypatch)
    try:
        job = create_csv_job(client, tmp_path)

        no_payload = client.post(
            f"/document-parse-jobs/{job['id']}/confirm-projects",
        )
        assert no_payload.status_code == 400

        before_mapping = client.post(
            f"/document-parse-jobs/{job['id']}/confirm-projects",
            json={"idempotency_key": "batch-001", "selected_rows": [0]},
        )
        assert before_mapping.status_code == 400
        assert "mapping" in before_mapping.json()["detail"].lower()

        mapping = client.post(
            f"/document-parse-jobs/{job['id']}/confirm-mapping",
            json={
                "mapping": {
                    "tour": {
                        "项目名称": "name",
                        "预算城市": "city",
                        "艺人": "artist_name",
                        "场馆": "venue",
                    }
                }
            },
        )
        assert mapping.status_code == 200
        mapped_job = mapping.json()["data"]
        assert mapped_job["result"]["mapping_status"] == "confirmed"
        assert mapped_job["result"]["candidate_projects"][0]["city"] == "北京"

        flat_mapping = client.post(
            f"/document-parse-jobs/{job['id']}/confirm-mapping",
            json={
                "field_mapping": {
                    "项目名称": "name",
                    "预算城市": "city",
                    "艺人": "artist_name",
                    "场馆": "venue",
                }
            },
        )
        assert flat_mapping.status_code == 200
        assert flat_mapping.json()["data"]["result"]["candidate_projects"][1]["city"] == "上海"

        payload = {
            "idempotency_key": "batch-001",
            "selected_rows": [1],
            "overrides": {"1": {"city": "苏州", "venue": "苏州文化中心"}},
        }
        first = client.post(
            f"/document-parse-jobs/{job['id']}/confirm-projects",
            json=payload,
        )
        assert first.status_code == 200
        projects = first.json()["data"]["projects"]
        assert len(projects) == 1
        assert projects[0]["name"] == "上海加场"
        assert projects[0]["city"] == "苏州"

        retry = client.post(
            f"/document-parse-jobs/{job['id']}/confirm-projects",
            json=payload,
        )
        assert retry.status_code == 200
        assert retry.json()["data"]["projects"][0]["id"] == projects[0]["id"]

        with session_factory() as db:
            imported = db.query(app_module.Project).filter(
                app_module.Project.name == "上海加场",
            ).all()
            assert len(imported) == 1
    finally:
        app_module.app.dependency_overrides.clear()


def test_binary_xls_is_explicitly_unsupported(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch)
    xls_path = tmp_path / "legacy.xls"
    xls_path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1legacy")
    try:
        project = client.post("/projects", json={"name": "旧表格导入"}).json()["data"]
        evidence = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "name": "legacy.xls",
                "file_url": str(xls_path),
                "evidence_type": "spreadsheet",
            },
        ).json()["data"]
        job = client.post(
            f"/evidences/{evidence['id']}/parse-jobs",
            json={"parse_scope": "batch_projects"},
        ).json()["data"]
        response = client.post(f"/document-parse-jobs/{job['id']}/run")
        assert response.status_code == 422
        assert "不支持旧版二进制 Excel" in response.json()["detail"]
    finally:
        app_module.app.dependency_overrides.clear()


def test_create_download_target_for_aliyun_and_minio_requires_https(monkeypatch):
    class FakeAliyunBucket:
        def sign_url(self, method, object_key, expires):
            assert (method, object_key, expires) == ("GET", "projects/1/a.pdf", 600)
            return "https://oss.example.com/projects/1/a.pdf?signature=ali"

    class FakeMinioClient:
        def presigned_get_object(self, bucket, object_key, expires):
            assert bucket == "evidence"
            assert object_key == "projects/1/a.pdf"
            assert int(expires.total_seconds()) == 600
            return "https://minio.example.com/evidence/projects/1/a.pdf?signature=minio"

    monkeypatch.setattr(object_storage, "create_aliyun_oss_bucket", lambda: FakeAliyunBucket())
    monkeypatch.setattr(object_storage, "create_minio_client", lambda: FakeMinioClient())

    aliyun = object_storage.create_download_target(
        "aliyun-oss", "evidence", "projects/1/a.pdf", expires=600,
    )
    minio = object_storage.create_download_target(
        "minio", "evidence", "projects/1/a.pdf", expires=600,
    )

    assert aliyun == {
        "url": "https://oss.example.com/projects/1/a.pdf?signature=ali",
        "method": "GET",
        "headers": {},
        "expires_in_seconds": 600,
    }
    assert minio["url"].startswith("https://")

    monkeypatch.setattr(
        object_storage,
        "create_minio_client",
        lambda: type("Client", (), {
            "presigned_get_object": lambda self, *args, **kwargs: "http://minio.local/file",
        })(),
    )
    with pytest.raises(ValueError, match="HTTPS"):
        object_storage.create_download_target("minio", "evidence", "projects/1/a.pdf")


def test_mixed_pdf_uses_text_and_ocr_with_page_metadata(monkeypatch, tmp_path):
    from app.documents import ocr

    pdf_path = tmp_path / "mixed.pdf"
    pdf_path.write_bytes(b"%PDF-fake")
    ocr_timeouts = []

    class FakePixmap:
        width = 1200
        height = 1600

        def tobytes(self, output):
            assert output == "png"
            return b"png-page"

    class FakePage:
        def __init__(self, text):
            self.text = text

        def get_text(self):
            return self.text

        def get_pixmap(self, dpi):
            assert dpi == 150
            return FakePixmap()

    class FakeDocument:
        def __init__(self, pages):
            self.pages = pages
            self.page_count = len(pages)

        def __getitem__(self, index):
            return self.pages[index]

        def close(self):
            pass

    monkeypatch.setattr(
        ocr,
        "_open_pdf",
        lambda path: FakeDocument([FakePage("第一页已有正文"), FakePage("")]),
    )

    def fake_ocr(image_bytes, language, timeout):
        assert image_bytes == b"png-page"
        assert language == "chi_sim+eng"
        ocr_timeouts.append(timeout)
        return "第二页扫描文字"

    monkeypatch.setattr(ocr, "_ocr_png_bytes", fake_ocr)

    result = ocr.extract_text_with_ocr(pdf_path, "pdf")

    assert result["extraction_method"] == "text+ocr"
    assert result["page_count"] == 2
    assert result["ocr_pages"] == [2]
    assert result["extracted_text"] == "第一页已有正文\n第二页扫描文字"
    assert [page["status"] for page in result["pages"]] == ["text", "ocr"]
    assert ocr_timeouts and 0 < ocr_timeouts[0] <= 120


def test_ocr_safety_limits(monkeypatch, tmp_path):
    from app.documents import ocr

    oversized = tmp_path / "oversized.png"
    with oversized.open("wb") as file:
        file.seek(20 * 1024 * 1024)
        file.write(b"x")
    with pytest.raises(ocr.DocumentExtractionError, match="20 MB"):
        ocr.extract_text_with_ocr(oversized, "image")

    small = tmp_path / "large-pixels.png"
    small.write_bytes(b"fake")
    monkeypatch.setattr(ocr, "_image_size", lambda path: (5001, 5000))
    with pytest.raises(ocr.DocumentExtractionError, match="2500"):
        ocr.extract_text_with_ocr(small, "image")

    pdf_path = tmp_path / "long.pdf"
    pdf_path.write_bytes(b"%PDF")
    fake_doc = type("FakeDocument", (), {"page_count": 21, "close": lambda self: None})()
    monkeypatch.setattr(ocr, "_open_pdf", lambda path: fake_doc)
    with pytest.raises(ocr.DocumentExtractionError, match="20 页"):
        ocr.extract_text_with_ocr(pdf_path, "pdf")


def test_download_object_to_tempfile_streams_and_enforces_size(monkeypatch):
    class FakeResponse:
        def stream(self, amount=64 * 1024):
            yield b"remote-"
            yield b"evidence"

        def close(self):
            pass

        def release_conn(self):
            pass

    class FakeMinio:
        def stat_object(self, bucket, object_key):
            assert (bucket, object_key) == ("evidence", "projects/1/a.pdf")
            return type("Stat", (), {"size": 15})()

        def get_object(self, bucket, object_key):
            return FakeResponse()

    monkeypatch.setattr(object_storage, "create_minio_client", lambda: FakeMinio())
    path = object_storage.download_object_to_tempfile(
        "minio",
        "evidence",
        "projects/1/a.pdf",
    )
    try:
        assert path.suffix == ".pdf"
        assert path.read_bytes() == b"remote-evidence"
    finally:
        path.unlink()

    class TooLargeMinio(FakeMinio):
        def stat_object(self, bucket, object_key):
            return type("Stat", (), {"size": 20 * 1024 * 1024 + 1})()

    monkeypatch.setattr(object_storage, "create_minio_client", lambda: TooLargeMinio())
    with pytest.raises(ValueError, match="20 MB"):
        object_storage.download_object_to_tempfile(
            "minio",
            "evidence",
            "projects/1/a.pdf",
        )


def test_ocr_failure_marks_job_for_manual_input_without_facts(monkeypatch, tmp_path):
    from app.documents import ocr

    client, session_factory = make_client(monkeypatch)
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"not-a-real-image")
    monkeypatch.setattr(
        ocr,
        "extract_text_with_ocr",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ocr.DocumentExtractionError("Tesseract OCR 未安装，需人工录入")
        ),
    )
    try:
        project = client.post("/projects", json={"name": "扫描材料项目"}).json()["data"]
        evidence = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "name": "scan.png",
                "file_url": str(image_path),
                "evidence_type": "image",
            },
        ).json()["data"]
        job = client.post(
            f"/evidences/{evidence['id']}/parse-jobs",
            json={},
        ).json()["data"]
        response = client.post(f"/document-parse-jobs/{job['id']}/run")

        assert response.status_code == 200
        failed = response.json()["data"]
        assert failed["status"] == "failed"
        assert failed["result"]["needs_manual_input"] is True
        assert failed["result"]["candidate_facts"] == []
        with session_factory() as db:
            assert db.query(app_module.Fact).filter(
                app_module.Fact.project_id == project["id"],
            ).count() == 0
    finally:
        app_module.app.dependency_overrides.clear()


def test_missing_document_never_generates_candidate_facts():
    evidence = type("Evidence", (), {
        "meta": {},
        "file_url": "/missing/document.txt",
        "name": "missing.txt",
        "source": "operator",
        "evidence_type": "document",
    })()

    result = parse_document_evidence(evidence, "document")

    assert result["needs_manual_input"] is True
    assert result["candidate_facts"] == []
    assert result["candidate_assumptions"] == []
    assert result["candidate_risks"] == []
    assert result["candidate_gates"] == []


def test_remote_object_is_materialized_before_document_parsing(monkeypatch, tmp_path):
    client, _ = make_client(monkeypatch)
    remote_copy = tmp_path / "remote.txt"
    remote_copy.write_text("项目名称：远端资料项目\n城市：杭州", encoding="utf-8")
    calls = []

    def fake_download(provider, bucket, object_key, max_bytes=20 * 1024 * 1024):
        calls.append((provider, bucket, object_key, max_bytes))
        materialized = tmp_path / "materialized.txt"
        materialized.write_bytes(remote_copy.read_bytes())
        return materialized

    monkeypatch.setattr(object_storage, "download_object_to_tempfile", fake_download)
    try:
        project = client.post("/projects", json={"name": "远端解析容器项目"}).json()["data"]
        evidence = client.post(
            "/evidences/upload",
            json={
                "project_id": project["id"],
                "name": "remote.txt",
                "file_url": "minio://evidence/projects/1/remote.txt",
                "evidence_type": "document",
                "metadata": {
                    "provider": "minio",
                    "bucket": "evidence",
                    "object_key": "projects/1/remote.txt",
                },
            },
        ).json()["data"]
        job = client.post(
            f"/evidences/{evidence['id']}/parse-jobs",
            json={},
        ).json()["data"]
        response = client.post(f"/document-parse-jobs/{job['id']}/run")

        assert response.status_code == 200
        completed = response.json()["data"]
        assert completed["status"] == "completed"
        assert "远端资料项目" in completed["result"]["extracted_text"]
        assert calls == [(
            "minio",
            "evidence",
            "projects/1/remote.txt",
            20 * 1024 * 1024,
        )]
        assert not (tmp_path / "materialized.txt").exists()
    finally:
        app_module.app.dependency_overrides.clear()


def test_evidence_download_url_requires_session_and_hides_other_tenants(monkeypatch):
    client, session_factory = make_client(monkeypatch)
    monkeypatch.setattr(
        object_storage,
        "create_download_target",
        lambda provider, bucket, object_key, expires=900: {
            "url": "https://objects.example.com/signed",
            "method": "GET",
            "headers": {},
            "expires_in_seconds": expires,
        },
    )
    with session_factory() as db:
        tenant, user = app_module.get_or_create_default_context(db)
        project = app_module.Project(tenant_id=tenant.id, name="下载项目", created_by=user.id)
        db.add(project)
        db.flush()
        evidence = app_module.Evidence(
            project_id=project.id,
            name="proof.pdf",
            file_url="oss://evidence/projects/1/proof.pdf",
            meta={
                "provider": "aliyun-oss",
                "bucket": "evidence",
                "object_key": "projects/1/proof.pdf",
            },
            uploaded_by=user.id,
        )
        db.add(evidence)
        db.commit()
        evidence_id = evidence.id
        headers = {"Authorization": f"Bearer {create_session_token(user.id, tenant.id)}"}

    try:
        assert client.get(f"/evidences/{evidence_id}/download-url").status_code == 401
        response = client.get(
            f"/evidences/{evidence_id}/download-url?expires=600",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["expires_in_seconds"] == 600
        monkeypatch.setattr(
            object_storage,
            "create_download_target",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("SECRET_ACCESS_KEY")
            ),
        )
        failed = client.get(
            f"/evidences/{evidence_id}/download-url",
            headers=headers,
        )
        assert failed.status_code == 502
        assert "SECRET_ACCESS_KEY" not in failed.text

        with session_factory() as db:
            other_tenant = app_module.Tenant(name="其他空间", status="active")
            db.add(other_tenant)
            db.flush()
            other_project = app_module.Project(tenant_id=other_tenant.id, name="其他项目")
            db.add(other_project)
            db.flush()
            other_evidence = app_module.Evidence(
                project_id=other_project.id,
                name="hidden.pdf",
                file_url="oss://hidden/hidden.pdf",
                meta={
                    "provider": "aliyun-oss",
                    "bucket": "hidden",
                    "object_key": "hidden.pdf",
                },
            )
            db.add(other_evidence)
            db.commit()
            hidden_id = other_evidence.id

        hidden = client.get(f"/evidences/{hidden_id}/download-url", headers=headers)
        assert hidden.status_code == 404
    finally:
        app_module.app.dependency_overrides.clear()
