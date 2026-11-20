import configparser
import io
import os
import re
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import HTTPException

from app.config import (
    ALIYUN_OSS_ACCESS_KEY_ID,
    ALIYUN_OSS_ACCESS_KEY_SECRET,
    ALIYUN_OSS_BUCKET,
    ALIYUN_OSS_CONFIG_PATH,
    ALIYUN_OSS_ENDPOINT,
    ALIYUN_OSS_PUBLIC_BASE_URL,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECURE,
    OSS_PROVIDER,
)

ALIYUN_OSS_PROVIDER = 'aliyun-oss'
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


def current_oss_provider():
    return os.environ.get('OSS_PROVIDER', OSS_PROVIDER).strip().lower()


def minio_bucket_name():
    return os.environ.get('MINIO_BUCKET', MINIO_BUCKET).strip()


def minio_secure_enabled():
    value = os.environ.get('MINIO_SECURE')
    if value is None:
        return bool(MINIO_SECURE)
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def aliyun_oss_bucket_name():
    return os.environ.get('ALIYUN_OSS_BUCKET', ALIYUN_OSS_BUCKET).strip()


def aliyun_public_base_url():
    return os.environ.get('ALIYUN_OSS_PUBLIC_BASE_URL', ALIYUN_OSS_PUBLIC_BASE_URL).strip().rstrip('/')


def aliyun_file_url(bucket: str, object_key: str):
    public_base = aliyun_public_base_url()
    if public_base:
        return f"{public_base}/{object_key}"
    return f"oss://{bucket}/{object_key}"


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
    endpoint = os.environ.get('ALIYUN_OSS_ENDPOINT', ALIYUN_OSS_ENDPOINT).strip()
    access_key_id = os.environ.get('ALIYUN_OSS_ACCESS_KEY_ID', ALIYUN_OSS_ACCESS_KEY_ID).strip()
    access_key_secret = os.environ.get('ALIYUN_OSS_ACCESS_KEY_SECRET', ALIYUN_OSS_ACCESS_KEY_SECRET).strip()

    config_path = os.environ.get('ALIYUN_OSS_CONFIG_PATH', ALIYUN_OSS_CONFIG_PATH)
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
    if provider == 'aliyun-oss':
        bucket = aliyun_oss_bucket_name()
        if not bucket:
            raise HTTPException(status_code=500, detail='ALIYUN_OSS_BUCKET is required')
        headers = {"Content-Type": content_type}
        try:
            upload_url = create_aliyun_oss_bucket().sign_url("PUT", object_key, 900, headers=headers)
        except Exception:
            raise HTTPException(status_code=502, detail='Aliyun OSS upload URL generation failed') from None
        return {
            "provider": "aliyun-oss",
            "bucket": bucket,
            "upload_url": upload_url,
            "method": "PUT",
            "headers": headers,
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
    except Exception:
        raise HTTPException(status_code=502, detail='MinIO upload URL generation failed') from None

    return {
        "provider": "minio",
        "bucket": bucket,
        "upload_url": upload_url,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
        "expires_in_seconds": 900,
    }


def create_download_target(provider: str, bucket: str, object_key: str, expires=900):
    if not 1 <= expires <= 3600:
        raise ValueError('下载签名有效期必须在 1 到 3600 秒之间')
    if provider == 'aliyun-oss':
        url = create_aliyun_oss_bucket().sign_url('GET', object_key, expires)
    elif provider == 'minio':
        url = create_minio_client().presigned_get_object(
            bucket,
            object_key,
            expires=timedelta(seconds=expires),
        )
    else:
        raise ValueError('对象存储未配置，无法生成下载签名')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise ValueError('对象下载地址必须使用 HTTPS')
    return {
        'url': url,
        'method': 'GET',
        'headers': {},
        'expires_in_seconds': expires,
    }


def download_object_to_tempfile(
    provider: str,
    bucket: str,
    object_key: str,
    max_bytes=MAX_DOCUMENT_BYTES,
):
    suffix = Path(object_key).suffix
    temporary = tempfile.NamedTemporaryFile(prefix='document-', suffix=suffix, delete=False)
    path = Path(temporary.name)
    response = None
    try:
        if provider == 'minio':
            client = create_minio_client()
            stat = client.stat_object(bucket, object_key)
            if stat.size > max_bytes:
                raise ValueError('远端文件超过 20 MB 限制')
            response = client.get_object(bucket, object_key)
            chunks = response.stream(64 * 1024)
        elif provider == 'aliyun-oss':
            aliyun_bucket = create_aliyun_oss_bucket()
            meta = aliyun_bucket.get_object_meta(object_key)
            size = getattr(meta, 'content_length', 0)
            if size and size > max_bytes:
                raise ValueError('远端文件超过 20 MB 限制')
            response = aliyun_bucket.get_object(object_key)
            chunks = iter(lambda: response.read(64 * 1024), b'')
        else:
            raise ValueError('对象存储未配置，无法下载远端资料')

        written = 0
        for chunk in chunks:
            written += len(chunk)
            if written > max_bytes:
                raise ValueError('远端文件超过 20 MB 限制')
            temporary.write(chunk)
        temporary.close()
        return path
    except Exception:
        temporary.close()
        path.unlink(missing_ok=True)
        raise
    finally:
        if response is not None:
            close = getattr(response, 'close', None)
            if close:
                close()
            release_conn = getattr(response, 'release_conn', None)
            if release_conn:
                release_conn()


def local_report_storage_dir():
    path = os.path.abspath(os.path.join(os.getcwd(), "storage", "reports"))
    os.makedirs(path, exist_ok=True)
    return path


def store_generated_report(provider: str, object_key: str, content: bytes, content_type: str):
    if provider == 'aliyun-oss':
        bucket = aliyun_oss_bucket_name()
        if not bucket:
            raise HTTPException(status_code=500, detail='ALIYUN_OSS_BUCKET is required')
        try:
            create_aliyun_oss_bucket().put_object(object_key, io.BytesIO(content), headers={"Content-Type": content_type})
        except Exception:
            raise HTTPException(status_code=502, detail='Aliyun OSS report upload failed') from None
        return {
            "provider": "aliyun-oss",
            "bucket": bucket,
            "object_key": object_key,
            "file_url": aliyun_file_url(bucket, object_key),
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
    except Exception:
        raise HTTPException(status_code=502, detail='MinIO report upload failed') from None
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


def configured_image_bucket():
    """Images must be stored in real Aliyun OSS, never a placeholder."""
    if current_oss_provider() != ALIYUN_OSS_PROVIDER:
        raise HTTPException(503, '图片存储未启用，请配置 OSS_PROVIDER=aliyun-oss')
    try:
        return create_aliyun_oss_bucket()
    except Exception:
        raise HTTPException(503, '图片存储未配置完整，请检查阿里 OSS 桶、Endpoint 和访问凭据') from None


def generated_image_link(metadata: dict, bucket=None):
    if metadata['bucket'] != aliyun_oss_bucket_name():
        raise HTTPException(503, '图片所在 OSS 桶与当前配置不一致，请检查存储配置')
    bucket = bucket or configured_image_bucket()
    public_base = aliyun_public_base_url()
    try:
        if public_base:
            url = f"{public_base}/{quote(metadata['object_key'], safe='/')}"
            ttl = None
        else:
            url = bucket.sign_url('GET', metadata['object_key'], 3600)
            ttl = 3600
        if urlsplit(url).scheme != 'https' or not urlsplit(url).netloc:
            raise ValueError('HTTPS required')
    except Exception:
        raise HTTPException(503, '无法生成 HTTPS 图片链接，请检查 OSS Endpoint 或 CDN 配置') from None
    return {**metadata, 'image_url': url, 'expires_in_seconds': ttl}


def store_generated_image(bucket, object_key: str, content: bytes, metadata: dict):
    try:
        bucket.put_object(object_key, io.BytesIO(content), headers={"Content-Type": metadata['content_type']})
    except Exception:
        raise HTTPException(502, '图片上传阿里 OSS 失败，请检查写入权限后重试') from None
    return {
        'provider': ALIYUN_OSS_PROVIDER, 'bucket': aliyun_oss_bucket_name(),
        'object_key': object_key, 'size': len(content), **metadata,
    }
