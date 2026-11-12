import os
import warnings

DATABASE_URL_ENV = 'DATABASE_URL'
DATABASE_URL_EXAMPLE = 'mysql+pymysql://root:123456789@127.0.0.1:3306/ip_actor_platform?charset=utf8mb4'
DATABASE_URL = DATABASE_URL_EXAMPLE

LLAMA_SERVER_URL = 'http://127.0.0.1:8080/v1/chat/completions'
LLAMA_SERVER_MODEL = 'local-model'
LLAMA_SERVER_TIMEOUT_SECONDS = 300
LLAMA_SERVER_MAX_TOKENS = int(os.environ.get('LLAMA_SERVER_MAX_TOKENS', '800'))

OSS_PROVIDER = 'local-placeholder'
MINIO_ENDPOINT = '127.0.0.1:9000'
MINIO_BUCKET = 'ip-actor-platform'
MINIO_SECURE = False

REDIS_URL = 'redis://127.0.0.1:6379/0'
REDIS_CACHE_TTL_SECONDS = 3600

WECHAT_MINIAPP_APPID = os.environ.get('WECHAT_MINIAPP_APPID', '')
WECHAT_MINIAPP_SECRET = os.environ.get('WECHAT_MINIAPP_SECRET', '')
WECHAT_MINIAPP_MOCK_PHONE_NUMBER = os.environ.get('WECHAT_MINIAPP_MOCK_PHONE_NUMBER', '')
WECHAT_API_TIMEOUT_SECONDS = int(os.environ.get('WECHAT_API_TIMEOUT_SECONDS', '10'))

DEFAULT_SECRET_KEY = 'dev-only-insecure-secret-key'
SECRET_KEY = os.environ.get('SECRET_KEY', DEFAULT_SECRET_KEY)
TOKEN_TTL_SECONDS = int(os.environ.get('TOKEN_TTL_SECONDS', str(12 * 3600)))

if SECRET_KEY == DEFAULT_SECRET_KEY:
    warnings.warn(
        'SECRET_KEY is not set; using the built-in development key. '
        'Set the SECRET_KEY environment variable in production.',
        stacklevel=1,
    )
