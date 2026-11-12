"""Deployment contracts and bootstrap behavior without a production database."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def bootstrap():
    spec = importlib.util.spec_from_file_location("deployment_bootstrap", ROOT / "deploy/bootstrap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deployment_env():
    return {
        "MYSQL_ROOT_PASSWORD": "test-root-password-only",
        "MYSQL_PASSWORD": "test-db-password-only",
        "REDIS_PASSWORD": "test-redis-password-only",
        "MINIO_ROOT_USER": "test-minio",
        "MINIO_ROOT_PASSWORD": "test-minio-password-only",
        "SECRET_KEY": "test-signing-key-" * 4,
        "INITIAL_ROOT_PASSWORD": "test-account-password-only",
    }


def test_database_and_cache_urls_escape_passwords():
    module = bootstrap()
    env = {**deployment_env(), "MYSQL_PASSWORD": "p@ss:/#?% word-long", "REDIS_PASSWORD": "redis-password@:/#?%",
           "MYSQL_USER": "actor", "MYSQL_DATABASE": "ip_actor_platform"}
    result = module.runtime_environment(env)
    parsed = make_url(result["DATABASE_URL"])
    assert parsed.drivername == "mysql+pymysql"
    assert parsed.host == "mysql" and parsed.password == env["MYSQL_PASSWORD"]
    assert parsed.query["charset"] == "utf8mb4"
    assert result["REDIS_URL"] == "redis://:redis-password%40%3A%2F%23%3F%25@redis:6379/0"


@pytest.mark.parametrize("key", ["MYSQL_PASSWORD", "REDIS_PASSWORD", "SECRET_KEY", "INITIAL_ROOT_PASSWORD"])
def test_runtime_rejects_missing_secrets_without_echoing_values(key):
    env = deployment_env()
    env[key] = ""
    with pytest.raises(ValueError, match=key) as error:
        bootstrap().runtime_environment(env)
    assert env["MYSQL_ROOT_PASSWORD"] not in str(error.value)


def test_bootstrap_retires_only_insecure_seed_accounts_and_preserves_existing_root(monkeypatch):
    from test_main import make_test_client, app_module
    from app.models import User
    from app.services.auth import hash_password, verify_password
    client, sessions = make_test_client(monkeypatch)
    module = bootstrap()
    try:
        with sessions() as db:
            module.initialize_accounts(db, "new-root-password-for-deployment")
            root = db.query(User).filter_by(account="root").one()
            assert verify_password("new-root-password-for-deployment", root.password_hash)
            role = db.query(User).filter_by(account="b_user").one()
            assert role.status == "disabled" and not verify_password("123456", role.password_hash)
            role.password_hash = hash_password("existing-role-password")
            role.status = "active"
            db.commit()
            module.initialize_accounts(db, "must-not-overwrite-existing-root")
            assert verify_password("new-root-password-for-deployment", root.password_hash)
            assert role.status == "active" and verify_password("existing-role-password", role.password_hash)
    finally:
        app_module.app.dependency_overrides.clear()


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI is needed to render Compose")
def test_compose_contract_renders_and_keeps_database_private(tmp_path):
    env_file = tmp_path / "deployment.env"
    env_file.write_text("\n".join(f"{k}={v}" for k, v in deployment_env().items()))
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), "-f", str(ROOT / "docker-compose.yml"),
         "config", "--format", "json"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    services = config["services"]
    assert set(services) == {"web", "backend", "mysql", "redis", "minio"}
    for name in ("backend", "mysql", "redis"):
        assert not services[name].get("ports")
    assert services["backend"]["depends_on"]["mysql"]["condition"] == "service_healthy"
    assert services["backend"]["environment"]["LLAMA_SERVER_URL"] == ""
    assert services["web"]["build"]["args"]["VITE_API_BASE_URL"] == "/api"
    assert len(config["volumes"]) == 4


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker CLI is needed to render Compose")
def test_compose_rejects_empty_configuration():
    result = subprocess.run(
        ["docker", "compose", "--env-file", "/dev/null", "-f", str(ROOT / "docker-compose.yml"), "config", "--quiet"],
        capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
    assert result.returncode != 0
    assert "required" in result.stderr.lower()


def test_secret_generation_is_private_unique_and_never_overwrites(tmp_path):
    module = bootstrap()
    target = tmp_path / "deployment.env"
    module.generate_environment(ROOT / "deployment.env.example", target)
    original = target.read_text()
    assert target.stat().st_mode & 0o777 == 0o600
    values = dict(line.split("=", 1) for line in original.splitlines() if line and not line.startswith("#"))
    module.runtime_environment(values)
    names = ("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "REDIS_PASSWORD",
             "MINIO_ROOT_PASSWORD", "SECRET_KEY", "INITIAL_ROOT_PASSWORD")
    assert len({values[name] for name in names}) == len(names)
    with pytest.raises(FileExistsError):
        module.generate_environment(ROOT / "deployment.env.example", target)
    assert target.read_text() == original
