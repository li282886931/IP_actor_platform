"""Inject existing OSS credentials into a backend-only Compose env file."""
import argparse
import configparser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
import uuid


def configure(env_path, config_path, bucket):
    env_path = Path(env_path)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket):
        raise ValueError("Invalid OSS bucket name")
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with Path(config_path).open() as stream:
            parser.read_file(stream)
        section = parser["Credentials"] if parser.has_section("Credentials") else parser["default"]
        endpoint = section.get("endpoint", "").strip()
        key = section.get("accessKeyID", "").strip()
        secret = section.get("accessKeySecret", "").strip()
    except (OSError, configparser.Error, KeyError):
        raise ValueError("Cannot read OSS credentials configuration") from None
    if not endpoint or not key or not secret:
        raise ValueError("OSS endpoint and access credentials are required")
    parts = urlsplit(endpoint if "://" in endpoint else f"https://{endpoint}")
    if (parts.scheme not in ("http", "https") or not parts.hostname
            or not parts.hostname.endswith(".aliyuncs.com") or parts.username or parts.password
            or parts.query or parts.fragment or parts.path not in ("", "/") or parts.port):
        raise ValueError("Invalid OSS endpoint")
    updates = {
        "OSS_PROVIDER": "aliyun-oss",
        "ALIYUN_OSS_ENDPOINT": f"https://{parts.hostname}",
        "ALIYUN_OSS_BUCKET": bucket,
        "ALIYUN_OSS_ACCESS_KEY_ID": key,
        "ALIYUN_OSS_ACCESS_KEY_SECRET": secret,
    }
    if any("\n" in value or "\r" in value or "\0" in value for value in updates.values()):
        raise ValueError("OSS configuration values must be single-line")
    original = env_path.read_text()
    lines = original.splitlines()
    kept = [line for line in lines if line.partition("=")[0].strip() not in updates]
    for name, value in updates.items():
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        kept.append(f"{name}='{escaped}'")
    backup = env_path.with_name(f".deployment-oss-backup-{uuid.uuid4().hex}.env")
    with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        stream.write(original)
    fd, temporary = tempfile.mkstemp(prefix=".oss-config-", suffix=".env", dir=env_path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write("\n".join(kept) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, env_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    authorization = next((line.partition("=")[2].strip().strip("'\"") for line in lines
                          if line.partition("=")[0].strip() == "IMAGE_GENERATION_AUTHORIZATION"), "")
    return {
        "provider": "aliyun-oss", "bucket": bucket,
        "endpoint": updates["ALIYUN_OSS_ENDPOINT"], "backup_path": str(backup),
        "image_authorization_configured": bool(authorization),
    }


if __name__ == "__main__":
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--env", required=True)
    arguments.add_argument("--oss-config", required=True)
    arguments.add_argument("--bucket", required=True)
    options = arguments.parse_args()
    try:
        print(json.dumps(configure(options.env, options.oss_config, options.bucket)))
    except Exception:
        raise SystemExit("OSS configuration failed; original env preserved if validation failed. No credentials printed.") from None
