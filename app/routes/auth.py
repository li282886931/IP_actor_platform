from app.core.responses import json_ok
from app.database import get_db
from app.infrastructure.cache import redis_delete
from app.infrastructure.cache import redis_get_json
from app.infrastructure.cache import redis_set_json
from app.integrations import wechat as wechat_integration
from app.models import User
from app.models import TenantMember, UserGroup
from app.schemas import WebLoginIn
from app.schemas import WechatLoginIn
from app.services import create_session_token
from app.services import get_or_create_default_context
from app.services import hash_password
from app.services import password_needs_rehash
from app.services import serialize_user
from app.services import verify_password
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from sqlalchemy.orm import Session
from urllib.parse import quote
import random
import uuid


router = APIRouter()

def ensure_login_membership(db: Session, tenant, user):
    group = db.query(UserGroup).filter(
        UserGroup.id == user.group_id, UserGroup.tenant_id == tenant.id,
    ).first()
    if not group:
        raise HTTPException(status_code=403, detail='Account is not linked to this tenant')
    member = db.query(TenantMember).filter(
        TenantMember.tenant_id == tenant.id, TenantMember.user_id == user.id,
    ).first()
    if not member:
        db.add(TenantMember(tenant_id=tenant.id, user_id=user.id, role='member'))
        db.commit()


CAPTCHA_TTL_SECONDS = 300
_captcha_fallback_store = {}


def captcha_cache_key(captcha_id: str):
    return f"auth:captcha:{captcha_id}"

def generate_captcha_code(length: int = 4):
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(random.choice(alphabet) for _ in range(length))

def build_captcha_svg(code: str):
    width = 132
    height = 44
    line_palette = ['#dbe6ff', '#c5d6ff', '#e8eefc']
    lines = []
    for index, color in enumerate(line_palette):
        offset = 6 + index * 12
        lines.append(
            f'<line x1="{offset}" y1="{8 + index * 7}" x2="{width - offset}" y2="{height - 8 - index * 5}" '
            f'stroke="{color}" stroke-width="1.2" opacity="0.85" />'
        )
    glyphs = []
    for index, char in enumerate(code):
        x = 18 + index * 26
        y = 29 + (-1 if index % 2 else 1)
        rotation = (-8 + index * 5)
        glyphs.append(
            f'<text x="{x}" y="{y}" font-size="24" font-family="Arial, sans-serif" font-weight="700" '
            f'fill="#203356" transform="rotate({rotation} {x} {y})">{char}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" rx="8" fill="#f3f7ff" />'
        + ''.join(lines)
        + ''.join(glyphs)
        + '</svg>'
    )
    return svg

def store_captcha_challenge(captcha_id: str, code: str, ttl_seconds: int = CAPTCHA_TTL_SECONDS):
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
    payload = {"code": code.upper(), "expires_at": expires_at}
    if not redis_set_json(captcha_cache_key(captcha_id), payload, ttl_seconds=ttl_seconds):
        _captcha_fallback_store[captcha_id] = payload

def load_captcha_challenge(captcha_id: str):
    payload = redis_get_json(captcha_cache_key(captcha_id))
    if payload is None:
        payload = _captcha_fallback_store.get(captcha_id)
    if not payload:
        return None
    expires_at = payload.get('expires_at')
    if expires_at:
        try:
            expires_at_value = datetime.fromisoformat(expires_at)
        except ValueError:
            expires_at_value = datetime.now(timezone.utc) - timedelta(seconds=1)
        if expires_at_value <= datetime.now(timezone.utc):
            delete_captcha_challenge(captcha_id)
            return None
    return payload

def delete_captcha_challenge(captcha_id: str):
    redis_delete(captcha_cache_key(captcha_id))
    _captcha_fallback_store.pop(captcha_id, None)

def validate_captcha_challenge(captcha_id: str, captcha_code: str):
    payload = load_captcha_challenge(captcha_id)
    delete_captcha_challenge(captcha_id)
    if not payload:
        return False
    return (captcha_code or '').strip().upper() == (payload.get('code') or '').upper()

@router.post('/auth/web-login')
def web_login(payload: WebLoginIn, db: Session = Depends(get_db)):
    if not validate_captcha_challenge(payload.captcha_id, payload.captcha_code):
        raise HTTPException(status_code=401, detail='Invalid captcha')
    tenant, _ = get_or_create_default_context(db)
    user = db.query(User).filter(User.account == payload.account, User.status == 'active').first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid account or password')
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
    ensure_login_membership(db, tenant, user)
    token = create_session_token(user.id, tenant.id)
    return json_ok({
        "token": token,
        "user": serialize_user(user),
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
        "source": "web",
    })

@router.get('/auth/captcha')
def issue_auth_captcha():
    captcha_id = uuid.uuid4().hex
    captcha_code = generate_captcha_code()
    store_captcha_challenge(captcha_id, captcha_code, ttl_seconds=CAPTCHA_TTL_SECONDS)
    captcha_svg = build_captcha_svg(captcha_code)
    return json_ok({
        "captcha_id": captcha_id,
        "captcha_image": f"data:image/svg+xml,{quote(captcha_svg)}",
        "expires_in_seconds": CAPTCHA_TTL_SECONDS,
    })

@router.post('/auth/wechat-login')
def wechat_login(payload: WechatLoginIn, request: Request, db: Session = Depends(get_db)):
    tenant, _ = get_or_create_default_context(db)
    session = wechat_integration.exchange_wechat_login_code(payload.code, request)
    phone_number = wechat_integration.fetch_wechat_phone_number(payload.phone_code, request)
    user = db.query(User).filter(User.phone == phone_number, User.status == 'active').first()
    if not user:
        raise HTTPException(status_code=403, detail='Phone number is not linked to any account')

    ensure_login_membership(db, tenant, user)
    openid = session.get('openid') or ''
    unionid = session.get('unionid') or ''
    if openid:
        existing_openid_user = db.query(User).filter(User.openid == openid).first()
        if existing_openid_user and existing_openid_user.id != user.id:
            raise HTTPException(status_code=409, detail='WeChat account is already linked to another user')
        user.openid = openid
    if unionid:
        existing_unionid_user = db.query(User).filter(User.unionid == unionid).first()
        if existing_unionid_user and existing_unionid_user.id != user.id:
            raise HTTPException(status_code=409, detail='WeChat account is already linked to another user')
        user.unionid = unionid

    user.name = payload.name or user.name
    user.status = 'active'
    db.commit()
    db.refresh(user)
    return json_ok({
        "token": create_session_token(user.id, tenant.id),
        "user": serialize_user(user),
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
        "source": "wechat",
    })
