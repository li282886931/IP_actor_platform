import json
import os
from typing import Optional

from .config import REDIS_CACHE_TTL_SECONDS, REDIS_URL


_redis_client = None
_redis_checked = False


def get_redis_client():
    global _redis_checked, _redis_client
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis
    except ImportError:
        return None

    redis_url = os.environ.get('REDIS_URL', REDIS_URL)
    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.8,
        )
        client.ping()
    except Exception:
        return None
    _redis_client = client
    return _redis_client


def redis_get_json(key: str):
    client = get_redis_client()
    if not client:
        return None
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def redis_set_json(key: str, value: dict, ttl_seconds: Optional[int] = None):
    client = get_redis_client()
    if not client:
        return False
    ttl = ttl_seconds if ttl_seconds is not None else int(os.environ.get('REDIS_CACHE_TTL_SECONDS', REDIS_CACHE_TTL_SECONDS))
    try:
        payload = json.dumps(value, ensure_ascii=False)
        if ttl > 0:
            client.setex(key, ttl, payload)
        else:
            client.set(key, payload)
        return True
    except Exception:
        return False


def redis_delete(key: str):
    client = get_redis_client()
    if not client:
        return False
    try:
        client.delete(key)
        return True
    except Exception:
        return False
