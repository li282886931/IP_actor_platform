import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location("configure_aliyun_oss", ROOT / "deploy/configure_aliyun_oss.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def inputs(tmp_path, endpoint="oss-cn-beijing.aliyuncs.com", key="test-key", secret="test-secret"):
    env = tmp_path / "deployment.env"
    env.write_text("MYSQL_PASSWORD=original-password\nOSS_PROVIDER=local-placeholder\nALIYUN_OSS_BUCKET=\n"
                   "IMAGE_GENERATION_AUTHORIZATION='Bearer original-image-token'\n# preserve comment\n")
    config = tmp_path / "ossutilconfig"
    config.write_text(f"[Credentials]\nendpoint={endpoint}\naccessKeyID={key}\naccessKeySecret={secret}\n")
    return env, config


def test_configuration_injects_credentials_preserves_other_values_and_creates_private_backup(tmp_path):
    env, config = inputs(tmp_path)
    original = env.read_text()
    result = module().configure(env, config, "ruiyinchang")
    content = env.read_text()
    assert "OSS_PROVIDER='aliyun-oss'" in content
    assert "ALIYUN_OSS_ENDPOINT='https://oss-cn-beijing.aliyuncs.com'" in content
    assert "ALIYUN_OSS_BUCKET='ruiyinchang'" in content
    assert "ALIYUN_OSS_ACCESS_KEY_ID='test-key'" in content
    assert "ALIYUN_OSS_ACCESS_KEY_SECRET='test-secret'" in content
    assert "MYSQL_PASSWORD=original-password" in content and "# preserve comment" in content
    assert "IMAGE_GENERATION_AUTHORIZATION='Bearer original-image-token'" in content
    assert content.count("ALIYUN_OSS_BUCKET=") == 1
    backup = Path(result["backup_path"])
    assert backup.read_text() == original
    assert backup.stat().st_mode & 0o777 == env.stat().st_mode & 0o777 == 0o600
    assert "test-key" not in json.dumps(result) and "test-secret" not in json.dumps(result)
    assert result["image_authorization_configured"] is True


def test_ossutil_v2_default_profile_is_supported(tmp_path):
    env, config = inputs(tmp_path, endpoint="http://oss-cn-beijing.aliyuncs.com")
    config.write_text(config.read_text().replace("[Credentials]", "[default]") + "region=cn-beijing\n")
    result = module().configure(env, config, "ruiyinchang")
    assert result["endpoint"] == "https://oss-cn-beijing.aliyuncs.com"
    assert "ALIYUN_OSS_ACCESS_KEY_ID='test-key'" in env.read_text()


@pytest.mark.parametrize("endpoint,key,secret,bucket", [
    ("", "key", "secret", "ruiyinchang"),
    ("oss-cn-beijing.aliyuncs.com", "", "secret", "ruiyinchang"),
    ("oss-cn-beijing.aliyuncs.com", "key", "", "ruiyinchang"),
    ("https://username:password@example.com", "key", "secret", "ruiyinchang"),
    ("oss-cn-beijing.aliyuncs.com", "key", "secret", "../escape"),
])
def test_invalid_configuration_does_not_modify_environment(tmp_path, endpoint, key, secret, bucket):
    env, config = inputs(tmp_path, endpoint, key, secret)
    original = env.read_bytes()
    with pytest.raises(ValueError):
        module().configure(env, config, bucket)
    assert env.read_bytes() == original
    assert not list(tmp_path.glob("*backup*"))


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI needed")
def test_credentials_survive_compose_parsing_and_are_only_in_backend(tmp_path):
    env, config = inputs(tmp_path, secret="secret$literal#value")
    module().configure(env, config, "ruiyinchang")
    with env.open("a") as stream:
        stream.write("\nMYSQL_ROOT_PASSWORD=test-only-password\nREDIS_PASSWORD=test-only-password\n"
                     "SECRET_KEY=test-only-signing-key\nINITIAL_ROOT_PASSWORD=test-only-password\n")
    result = subprocess.run(["docker", "compose", "--env-file", str(env), "-f", str(ROOT / "docker-compose.yml"),
                             "config", "--format", "json"], capture_output=True, text=True,
                            env={"PATH": os.environ["PATH"]})
    assert result.returncode == 0
    services = json.loads(result.stdout)["services"]
    backend = services["backend"]["environment"]
    # Canonical Compose output escapes dollars for a future Compose parse.
    assert backend["ALIYUN_OSS_ACCESS_KEY_SECRET"] == "secret$$literal#value"
    environment = subprocess.run(["docker", "compose", "--env-file", str(env), "-f", str(ROOT / "docker-compose.yml"),
                                  "config", "--environment"], capture_output=True, text=True,
                                 env={"PATH": os.environ["PATH"]})
    assert environment.returncode == 0
    assert "ALIYUN_OSS_ACCESS_KEY_SECRET=secret$literal#value" in environment.stdout.splitlines()
    assert backend["OSS_PROVIDER"] == "aliyun-oss"
    assert backend["IMAGE_GENERATION_AUTHORIZATION"] == "Bearer original-image-token"
    for name in ("web", "mysql", "redis"):
        assert "ALIYUN_OSS_ACCESS_KEY_SECRET" not in services[name].get("environment", {})
