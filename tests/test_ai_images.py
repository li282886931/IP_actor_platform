import io
import json

import pytest
from PIL import Image

from test_ai_user_isolation import ai_client, login
from app.integrations import object_storage as storage
from app.models import AIGeneration


def image_bytes(fmt="PNG"):
    out = io.BytesIO()
    Image.new("RGB", (12, 8), "blue").save(out, format=fmt)
    return out.getvalue()


@pytest.fixture
def image_service(monkeypatch):
    from app.integrations import image_generation
    calls = {"downloads": [], "uploads": [], "signs": []}
    content = image_bytes()

    class Response:
        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def download(url, **kwargs):
        calls["downloads"].append((url, kwargs))
        return Response()

    class Bucket:
        bucket_name = "image-bucket"

        def put_object(self, key, body, headers):
            calls["uploads"].append((key, body.read(), headers))

        def sign_url(self, method, key, ttl):
            calls["signs"].append((method, key, ttl))
            return f"https://image-bucket.oss-cn-hangzhou.aliyuncs.com/{key}?signature={len(calls['signs'])}"

    monkeypatch.setenv("OSS_PROVIDER", "aliyun-oss")
    monkeypatch.setenv("ALIYUN_OSS_BUCKET", "image-bucket")
    monkeypatch.setenv("ALIYUN_OSS_PUBLIC_BASE_URL", "")
    monkeypatch.setattr(storage, "create_aliyun_oss_bucket", Bucket)
    monkeypatch.setattr(image_generation.requests, "get", download)
    return calls


def test_image_endpoints_require_login(ai_client):
    client, _, _ = ai_client
    assert client.post("/ai/generate/image", json={"prompt": "舞台"}).status_code == 401
    assert client.get("/ai/images/1").status_code == 401


@pytest.mark.parametrize("payload", [
    {"prompt": "  "}, {"prompt": "x" * 2001},
    {"prompt": "舞台", "image_size": "invalid"},
    {"prompt": "舞台", "generation_nonce": "../escape"},
])
def test_image_input_validation(ai_client, monkeypatch, payload):
    client, _, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    assert client.post("/ai/generate/image", headers=headers, json=payload).status_code == 422


def test_generate_upload_replay_refresh_and_ownership(ai_client, monkeypatch, image_service):
    client, sessions, _ = ai_client
    headers, identity = login(client, monkeypatch, "b_user")
    payload = {"prompt": "写实蓝色灯光舞台", "image_size": "portrait_4_3", "generation_nonce": "one"}
    response = client.post("/ai/generate/image", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["image_url"].startswith("https://")
    assert data["expires_in_seconds"] == 3600
    assert data["width"] == 12 and data["height"] == 8
    url, options = image_service["downloads"][0]
    assert url == "https://copilot-cn.bytedance.net/api/ide/v1/text_to_image"
    assert options["params"]["image_size"] == "portrait_4_3"
    assert payload["prompt"] in options["params"]["prompt"]
    assert options["allow_redirects"] is False
    key, content, headers_put = image_service["uploads"][0]
    assert key.startswith(f'ai-images/{identity["current_tenant"]["id"]}/{identity["user"]["id"]}/')
    assert content == image_bytes()
    assert headers_put["Content-Type"] == "image/png"
    with sessions() as db:
        record = db.query(AIGeneration).filter_by(type="image").one()
        assert "signature=" not in record.result
        assert json.loads(record.result)["object_key"] == key
    repeat = client.post("/ai/generate/image", headers=headers, json=payload)
    assert repeat.json()["data"]["id"] == data["id"]
    assert len(image_service["uploads"]) == len(image_service["downloads"]) == 1
    refreshed = client.get(f'/ai/images/{data["id"]}', headers=headers)
    assert refreshed.json()["data"]["image_url"] != data["image_url"]
    assert client.post("/ai/generate/image", headers=headers, json={**payload, "prompt": "另一个画面"}).status_code == 409
    other, _ = login(client, monkeypatch, "root")
    assert client.get(f'/ai/images/{data["id"]}', headers=other).status_code == 404
    assert client.post("/ai/generate/image", headers=other, json=payload).json()["data"]["id"] != data["id"]


@pytest.mark.parametrize("failure", ["config", "download", "upload", "html", "oversized"])
def test_failures_do_not_persist_or_leak_secrets(ai_client, monkeypatch, image_service, failure):
    from app.integrations import image_generation
    client, sessions, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    def fail(*args, **kwargs):
        raise RuntimeError("SECRET_ACCESS_KEY")
    if failure == "config":
        monkeypatch.setattr(storage, "create_aliyun_oss_bucket", fail)
    elif failure == "download":
        monkeypatch.setattr(image_generation.requests, "get", fail)
    elif failure == "upload":
        class Broken:
            def put_object(self, *args, **kwargs):
                fail()
        monkeypatch.setattr(storage, "create_aliyun_oss_bucket", Broken)
    else:
        class BadResponse:
            def raise_for_status(self): pass
            def iter_content(self, chunk_size):
                yield b"<html>login required</html>" if failure == "html" else b"x" * (image_generation.MAX_IMAGE_BYTES + 1)
            def __enter__(self): return self
            def __exit__(self, *args): pass
        monkeypatch.setattr(image_generation.requests, "get", lambda *args, **kwargs: BadResponse())
    response = client.post("/ai/generate/image", headers=headers, json={"prompt": "舞台"})
    assert response.status_code in (502, 503)
    assert "SECRET_ACCESS_KEY" not in response.text
    with sessions() as db:
        assert db.query(AIGeneration).filter_by(type="image").count() == 0
    if failure == "config":
        assert not image_service["downloads"]


@pytest.mark.parametrize("fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")])
def test_validate_actual_image_bytes(fmt, mime):
    from app.integrations.image_generation import validate_image
    assert validate_image(image_bytes(fmt))["content_type"] == mime
    with pytest.raises(Exception):
        validate_image(image_bytes(fmt)[:20])


def test_cdn_https_and_bucket_change(ai_client, monkeypatch, image_service):
    client, _, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    monkeypatch.setenv("ALIYUN_OSS_PUBLIC_BASE_URL", "https://images.example.com")
    data = client.post("/ai/generate/image", headers=headers, json={"prompt": "舞台"}).json()["data"]
    assert data["image_url"].startswith("https://images.example.com/ai-images/")
    assert data["expires_in_seconds"] is None
    monkeypatch.setenv("ALIYUN_OSS_BUCKET", "another-bucket")
    assert client.get(f'/ai/images/{data["id"]}', headers=headers).status_code == 503


def test_image_service_authorization_is_forwarded_only_upstream(ai_client, monkeypatch, image_service):
    client, sessions, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    monkeypatch.setenv("IMAGE_GENERATION_AUTHORIZATION", "Bearer image-test-secret")
    response = client.post("/ai/generate/image", headers=headers, json={"prompt": "舞台"})
    assert response.status_code == 200
    assert image_service["downloads"][0][1]["headers"]["Authorization"] == "Bearer image-test-secret"
    assert "image-test-secret" not in response.text
    with sessions() as db:
        record = db.query(AIGeneration).filter_by(type="image").one()
        assert "image-test-secret" not in record.result


def test_redirect_auth_failure_is_not_followed(ai_client, monkeypatch, image_service):
    from app.integrations import image_generation
    client, sessions, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    class AuthResponse:
        status_code = 302
        def raise_for_status(self): pass
        def iter_content(self, chunk_size): yield b'{"code":1001,"message":"Authentication failed"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(image_generation.requests, "get", lambda *args, **kwargs: AuthResponse())
    response = client.post("/ai/generate/image", headers=headers, json={"prompt": "舞台"})
    assert response.status_code == 502
    assert "鉴权" in response.json()["detail"]
    assert not image_service["uploads"]


def test_database_failure_does_not_report_success(ai_client, monkeypatch, image_service):
    client, sessions, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    from sqlalchemy.orm import Session
    original = Session.commit
    def commit(self):
        if any(isinstance(record, AIGeneration) and record.type == "image" for record in self.identity_map.values()):
            raise RuntimeError("private database password")
        return original(self)
    monkeypatch.setattr(Session, "commit", commit)
    response = client.post("/ai/generate/image", headers=headers, json={"prompt": "舞台"})
    assert response.status_code == 502
    assert "private database password" not in response.text
    with sessions() as db:
        assert db.query(AIGeneration).filter_by(type="image").count() == 0


@pytest.mark.parametrize("acquired", [True, False])
def test_mysql_request_lock_releases_on_failure_and_handles_contention(acquired):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.routes.ai_images import request_lock
    commands = []
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement, params):
            commands.append(str(statement))
            return SimpleNamespace(scalar=lambda: int(acquired))
    engine = SimpleNamespace(dialect=SimpleNamespace(name="mysql"), connect=Connection)
    db = SimpleNamespace(get_bind=lambda: engine)
    if acquired:
        with pytest.raises(RuntimeError):
            with request_lock(db, "f" * 64):
                raise RuntimeError("generation failed")
        assert "RELEASE_LOCK" in commands[-1]
    else:
        with pytest.raises(HTTPException) as failure:
            with request_lock(db, "f" * 64):
                pytest.fail("Lock was not acquired")
        assert failure.value.status_code == 409
        assert len(commands) == 1
