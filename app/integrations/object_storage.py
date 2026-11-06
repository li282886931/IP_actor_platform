import io
import os
import re
import uuid
from datetime import timedelta

from fastapi import HTTPException

from app.config import MINIO_BUCKET, MINIO_ENDPOINT, MINIO_SECURE, OSS_PROVIDER


def current_oss_provider():
    return os.environ.get('OSS_PROVIDER', OSS_PROVIDER).strip().lower()


def minio_bucket_name():
    return os.environ.get('MINIO_BUCKET', MINIO_BUCKET).strip()


def minio_secure_enabled():
    value = os.environ.get('MINIO_SECURE')
    if value is None:
        return bool(MINIO_SECURE)
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def create_minio_client():
    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError('MinIO SDK is not installed') from exc

    access_key = os.environ.get('MINIO_ACCESS_KEY') or ''
    secret_key = os.environ.get('MINIO_SECRET_KEY') or ''
    if not access_key or not secret_key:
        raise RuntimeError('MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required')

    return Minio(
        os.environ.get('MINIO_ENDPOINT', MINIO_ENDPOINT),
        access_key=access_key,
        secret_key=secret_key,
        secure=minio_secure_enabled(),
    )


def ensure_minio_bucket(client, bucket: str):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def create_upload_target(provider: str, object_key: str, content_type: str):
    if provider != 'minio':
        return {
            "provider": "local-placeholder",
            "bucket": "",
            "upload_url": f"/oss/local-placeholder/{object_key}",
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "expires_in_seconds": 900,
        }

    bucket = minio_bucket_name()
    if not bucket:
        raise HTTPException(status_code=500, detail='MINIO_BUCKET is required')
    try:
        client = create_minio_client()
        ensure_minio_bucket(client, bucket)
        expires = timedelta(seconds=900)
        upload_url = client.presigned_put_object(bucket, object_key, expires=expires)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'MinIO upload URL generation failed: {exc}') from exc

    return {
        "provider": "minio",
        "bucket": bucket,
        "upload_url": upload_url,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
        "expires_in_seconds": 900,
    }


def local_report_storage_dir():
    path = os.path.abspath(os.path.join(os.getcwd(), "storage", "reports"))
    os.makedirs(path, exist_ok=True)
    return path


def store_generated_report(provider: str, object_key: str, content: bytes, content_type: str):
    if provider != 'minio':
        storage_dir = local_report_storage_dir()
        filename = f"{uuid.uuid4().hex}-{safe_object_name(os.path.basename(object_key))}"
        local_path = os.path.join(storage_dir, filename)
        with open(local_path, 'wb') as report_file:
            report_file.write(content)
        return {
            "provider": "local-placeholder",
            "bucket": "",
            "object_key": object_key,
            "file_url": f"oss://local-placeholder/{object_key}",
            "local_path": local_path,
            "size": len(content),
        }

    bucket = minio_bucket_name()
    if not bucket:
        raise HTTPException(status_code=500, detail='MINIO_BUCKET is required')
    try:
        client = create_minio_client()
        ensure_minio_bucket(client, bucket)
        client.put_object(bucket, object_key, io.BytesIO(content), length=len(content), content_type=content_type)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'MinIO report upload failed: {exc}') from exc
    return {
        "provider": "minio",
        "bucket": bucket,
        "object_key": object_key,
        "file_url": f"minio://{bucket}/{object_key}",
        "local_path": "",
        "size": len(content),
    }


def safe_object_name(file_name: str):
    sanitized = re.sub(r'[^A-Za-z0-9._-]+', '-', file_name.strip()).strip('.-')
    return sanitized or 'upload.bin'
