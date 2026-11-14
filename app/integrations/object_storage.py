import configparser
import io
import os
import re
import uuid
from datetime import timedelta

from fastapi import HTTPException

from app.config import (
    ALIYUN_OSS_ACCESS_KEY_ID,
    ALIYUN_OSS_ACCESS_KEY_SECRET,
    ALIYUN_OSS_BUCKET,
    ALIYUN_OSS_CONFIG_PATH,
    ALIYUN_OSS_ENDPOINT,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECURE,
    OSS_PROVIDER,
)

ALIYUN_OSS_PROVIDER = 'aliyun-oss'


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


def aliyun_oss_bucket_name():
    return os.environ.get('ALIYUN_OSS_BUCKET', ALIYUN_OSS_BUCKET).strip()


def load_aliyun_oss_config():
    """读取阿里云 OSS 访问配置。

    优先级：环境变量（ALIYUN_OSS_ENDPOINT / ALIYUN_OSS_ACCESS_KEY_ID /
    ALIYUN_OSS_ACCESS_KEY_SECRET）> 线上服务器 ossutil 配置文件。

    ossutil 的 .ossutilconfig 为标准 INI 格式，例如：
        [Credentials]
        language=CH
        endpoint=oss-cn-hangzhou.aliyuncs.com
        accessKeyID=LTAI...
        accessKeySecret=...
    """
    endpoint = ALIYUN_OSS_ENDPOINT.strip()
    access_key_id = ALIYUN_OSS_ACCESS_KEY_ID.strip()
    access_key_secret = ALIYUN_OSS_ACCESS_KEY_SECRET.strip()

    config_path = ALIYUN_OSS_CONFIG_PATH
    missing = not endpoint or not access_key_id or not access_key_secret
    if missing and config_path and os.path.exists(config_path):
        parser = configparser.ConfigParser()
        parser.read(config_path)
        if parser.has_section('Credentials'):
            endpoint = endpoint or (parser.get('Credentials', 'endpoint', fallback='') or '').strip()
            access_key_id = access_key_id or (parser.get('Credentials', 'accessKeyID', fallback='') or '').strip()
            access_key_secret = access_key_secret or (parser.get('Credentials', 'accessKeySecret', fallback='') or '').strip()

    return {
        'endpoint': endpoint,
        'access_key_id': access_key_id,
        'access_key_secret': access_key_secret,
    }


def _aliyun_oss_endpoint_url(endpoint: str):
    endpoint = (endpoint or '').strip()
    if not endpoint:
        return ''
    if endpoint.startswith('http://') or endpoint.startswith('https://'):
        return endpoint
    return f'https://{endpoint}'


def create_aliyun_oss_bucket():
    try:
        import oss2
    except ImportError as exc:
        raise RuntimeError('oss2 SDK is not installed; add "oss2" to requirements') from exc

    creds = load_aliyun_oss_config()
    if not creds['access_key_id'] or not creds['access_key_secret']:
        raise RuntimeError('Aliyun OSS credentials are not configured; check /root/.ossutilconfig')
    endpoint = _aliyun_oss_endpoint_url(creds['endpoint'])
    if not endpoint:
        raise RuntimeError('Aliyun OSS endpoint is not configured')
    bucket_name = aliyun_oss_bucket_name()
    if not bucket_name:
        raise RuntimeError('ALIYUN_OSS_BUCKET is required')

    auth = oss2.Auth(creds['access_key_id'], creds['access_key_secret'])
    return oss2.Bucket(auth, endpoint, bucket_name)


def create_upload_target(provider: str, object_key: str, content_type: str):
    if provider == ALIYUN_OSS_PROVIDER:
        try:
            bucket = create_aliyun_oss_bucket()
            expires = timedelta(seconds=900)
            upload_url = bucket.sign_url('PUT', object_key, expires, headers={'Content-Type': content_type})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f'Aliyun OSS upload URL generation failed: {exc}') from exc
        return {
            "provider": ALIYUN_OSS_PROVIDER,
            "bucket": bucket.bucket_name,
            "upload_url": upload_url,
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "expires_in_seconds": 900,
        }

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
    if provider == ALIYUN_OSS_PROVIDER:
        try:
            bucket = create_aliyun_oss_bucket()
            bucket.put_object(object_key, content, headers={'Content-Type': content_type})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f'Aliyun OSS report upload failed: {exc}') from exc
        return {
            "provider": ALIYUN_OSS_PROVIDER,
            "bucket": bucket.bucket_name,
            "object_key": object_key,
            "file_url": f"oss://{bucket.bucket_name}/{object_key}",
            "local_path": "",
            "size": len(content),
        }

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
