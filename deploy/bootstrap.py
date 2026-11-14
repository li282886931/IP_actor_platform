"""Compose startup and exclusive generation of deployment secrets."""
import argparse
import os
from pathlib import Path
import re
import secrets
from urllib.parse import quote


def runtime_environment(environ):
    for name in ("MYSQL_PASSWORD", "REDIS_PASSWORD", "SECRET_KEY", "INITIAL_ROOT_PASSWORD"):
        value = environ.get(name, "")
        if len(value) < 16 or value.lower().startswith(("change-me", "replace-with")):
            raise ValueError(f"{name} is required and must have at least 16 characters")
    user = quote(environ.get("MYSQL_USER", "ip_actor"), safe="")
    password = quote(environ["MYSQL_PASSWORD"], safe="")
    database = quote(environ.get("MYSQL_DATABASE", "ip_actor_platform"), safe="")
    host = environ.get("MYSQL_HOST", "mysql")
    port = int(environ.get("MYSQL_PORT", "3306"))
    redis_host = environ.get("REDIS_HOST", "redis")
    redis_password = quote(environ["REDIS_PASSWORD"], safe="")
    return {
        "DATABASE_URL": f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4",
        "REDIS_URL": f"redis://:{redis_password}@{redis_host}:6379/0",
    }


def initialize_accounts(db, initial_password):
    from app.models import User
    from app.services.auth import DEFAULT_USERS, hash_password, verify_password

    for item in DEFAULT_USERS:
        user = db.query(User).filter_by(account=item["account"]).first()
        if not user or not verify_password("123456", user.password_hash):
            continue
        if user.account == "root":
            user.password_hash = hash_password(initial_password)
        else:
            user.password_hash = hash_password(secrets.token_urlsafe(48))
            user.status = "disabled"
    db.commit()


def generate_environment(template, target):
    content = Path(template).read_text(encoding="utf-8")
    for name in ("MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "REDIS_PASSWORD",
                 "MINIO_ROOT_PASSWORD", "SECRET_KEY", "INITIAL_ROOT_PASSWORD"):
        content = re.sub(rf"^{name}=.*$", f"{name}={secrets.token_hex(32)}", content, flags=re.MULTILINE)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-env", action="store_true")
    args = parser.parse_args()
    if args.generate_env:
        root = Path(__file__).resolve().parents[1]
        generate_environment(root / "deployment.env.example", root / "deployment.env")
        print("Created deployment.env with private permissions; existing files are never overwritten.")
        return
    os.environ.update(runtime_environment(os.environ))
    # Import only after constructing the database URL; app initialization creates its schema.
    from app.main import app
    from app.database import SessionLocal
    import uvicorn

    with SessionLocal() as db:
        initialize_accounts(db, os.environ["INITIAL_ROOT_PASSWORD"])

    workers = int(os.environ.get("WORKERS", "0") or 0)
    if workers <= 0:
        workers = max(1, (os.cpu_count() or 2))
    # Multiple workers handle concurrent requests; init_db() is guarded by a
    # cross-process file lock so concurrent schema initialization stays safe.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, root_path="/api",
                proxy_headers=True, forwarded_allow_ips="*", workers=workers)


if __name__ == "__main__":
    main()
