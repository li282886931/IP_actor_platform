import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import config
from app.models import Tenant, TenantMember, User, UserGroup


GROUPS = [
    {"code": "root", "name": "超级管理员", "permissions": ["user:manage"], "role": "B"},
    {"code": "B", "name": "主办方", "permissions": ["project:read", "project:write", "finance:calculate", "decision:write", "task:write"], "role": "B"},
    {"code": "Brand", "name": "品牌方", "permissions": ["project:read"], "role": "Brand"},
    {"code": "G", "name": "政府 / 文旅", "permissions": ["project:read"], "role": "G"},
    {"code": "C", "name": "观众端", "permissions": ["show:read"], "role": "C"},
    {"code": "Investor", "name": "资方", "permissions": ["investment:read"], "role": "Investor"},
    {"code": "Artist", "name": "艺人", "permissions": ["artist:own:read"], "role": "Artist"},
]


DEFAULT_USERS = [
    {"account": "root", "name": "超级管理员", "group_code": "root"},
    {"account": "b_user", "name": "主办方用户", "group_code": "B"},
    {"account": "brand_user", "name": "品牌方用户", "group_code": "Brand"},
    {"account": "g_user", "name": "政府文旅用户", "group_code": "G"},
    {"account": "c_user", "name": "观众用户", "group_code": "C"},
    {"account": "investor_user", "name": "资方用户", "group_code": "Investor"},
    {"account": "artist_user", "name": "艺人用户", "group_code": "Artist"},
]


@dataclass(frozen=True)
class RequestContext:
    tenant: Tenant
    user: User


def resolve_request_context(
    db: Session,
    *,
    authorization: str,
    tenant_header: Optional[str] = None,
) -> RequestContext:
    scheme, _, token = (authorization or '').partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail='Invalid or missing session token')

    try:
        user_id, token_tenant_id = parse_session_token(token)
        tenant_id = int(tenant_header) if tenant_header else token_tenant_id
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail='Invalid session token')

    user = db.query(User).filter(User.id == user_id, User.status == 'active').first()
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.status == 'active').first()
    if not user or not tenant:
        raise HTTPException(status_code=401, detail='Session context is no longer available')

    member = db.query(TenantMember).filter(
        TenantMember.tenant_id == tenant.id,
        TenantMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail='Tenant access denied')
    return RequestContext(tenant=tenant, user=user)


PASSWORD_HASH_ALGORITHM = 'pbkdf2_sha256'


PASSWORD_HASH_ITERATIONS = 120_000


SESSION_TOKEN_VERSION = 'v1'


def hash_password(password: str):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), bytes.fromhex(salt), PASSWORD_HASH_ITERATIONS
    )
    return f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}${salt}${digest.hex()}"


def _legacy_hash_password(password: str):
    return hashlib.sha256(f"ruiyinchang:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str):
    if not password_hash:
        return False
    if password_hash.startswith(f"{PASSWORD_HASH_ALGORITHM}$"):
        try:
            _, iterations, salt, expected = password_hash.split('$')
            digest = hashlib.pbkdf2_hmac(
                'sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iterations)
            )
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(digest.hex(), expected)
    return hmac.compare_digest(_legacy_hash_password(password), password_hash)


def password_needs_rehash(password_hash: str):
    return not (password_hash or '').startswith(
        f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}$"
    )


def _b64url_encode(data: bytes):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str):
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


def create_session_token(user_id: int, tenant_id: int):
    payload = {
        "uid": int(user_id),
        "tid": int(tenant_id),
        "exp": int(time.time()) + config.TOKEN_TTL_SECONDS,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f"{SESSION_TOKEN_VERSION}.{payload_b64}".encode('ascii')
    signature = hmac.new(config.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256)
    return f"{SESSION_TOKEN_VERSION}.{payload_b64}.{_b64url_encode(signature.digest())}"


def parse_session_token(token: str) -> Tuple[int, int]:
    try:
        version, payload_b64, signature_b64 = token.split('.')
    except ValueError:
        raise ValueError('malformed token')
    if version != SESSION_TOKEN_VERSION:
        raise ValueError('unsupported token version')

    signing_input = f"{version}.{payload_b64}".encode('ascii')
    expected = hmac.new(config.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256)
    try:
        provided = _b64url_decode(signature_b64)
    except (binascii.Error, ValueError):
        raise ValueError('invalid signature')
    if not hmac.compare_digest(expected.digest(), provided):
        raise ValueError('invalid signature')

    try:
        payload = json.loads(_b64url_decode(payload_b64))
        user_id = int(payload['uid'])
        tenant_id = int(payload['tid'])
        expires_at = int(payload['exp'])
    except (binascii.Error, KeyError, TypeError, ValueError):
        raise ValueError('invalid payload')
    if expires_at < int(time.time()):
        raise ValueError('token expired')
    return user_id, tenant_id


def group_role(group_code: str):
    for group in GROUPS:
        if group["code"] == group_code:
            return group["role"]
    return "C"


def can_manage_users(group_code: str):
    return group_code == "root"


def get_or_create_default_context(db: Session, *, account='root', name='超级管理员'):
    tenant = db.query(Tenant).order_by(Tenant.id.asc()).first()
    if not tenant:
        tenant = Tenant(name='锐音场默认空间', status='active')
        db.add(tenant)
        db.flush()

    groups_by_code = {}
    for item in GROUPS:
        group = db.query(UserGroup).filter(
            UserGroup.tenant_id == tenant.id,
            UserGroup.name == item["code"],
        ).first()
        if not group:
            group = UserGroup(
                tenant_id=tenant.id,
                name=item["code"],
                description=item["name"],
                permission_set=item["permissions"],
                data_scope='all_projects',
            )
            db.add(group)
            db.flush()
        groups_by_code[item["code"]] = group

    for item in DEFAULT_USERS:
        default_user = db.query(User).filter(User.account == item["account"]).first()
        if not default_user:
            default_user = User(
                account=item["account"],
                name=item["name"],
                password_hash=hash_password('123456'),
                group_id=groups_by_code[item["group_code"]].id,
                group_code=item["group_code"],
                status='active',
            )
            db.add(default_user)
            db.flush()
        else:
            default_user.password_hash = default_user.password_hash or hash_password('123456')
            default_user.group_id = groups_by_code[item["group_code"]].id
            default_user.group_code = item["group_code"]
            default_user.status = default_user.status or 'active'

    user = db.query(User).filter(User.account == account).first()
    if not user:
        user = User(
            account=account,
            name=name or account,
            password_hash=hash_password('123456'),
            group_id=groups_by_code['B'].id,
            group_code='B',
            status='active',
        )
        db.add(user)
        db.flush()

    member = db.query(TenantMember).filter(
        TenantMember.tenant_id == tenant.id,
        TenantMember.user_id == user.id,
    ).first()
    if not member:
        member = TenantMember(tenant_id=tenant.id, user_id=user.id, role='admin')
        db.add(member)

    db.commit()
    db.refresh(tenant)
    db.refresh(user)
    return tenant, user


def get_default_tenant_id(db: Session):
    tenant, _ = get_or_create_default_context(db)
    return tenant.id
