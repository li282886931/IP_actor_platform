from app.core.responses import json_ok
from app.database import get_db
from app.models import Tenant
from app.models import User
from app.models import UserGroup
from app.models import AIGeneration, TenantMember, Artist, Order
from app.schemas import UserCreateIn
from app.schemas import UserUpdateIn
from app.services import GROUPS
from app.services import create_session_token
from app.services import get_or_create_default_context
from app.services import hash_password
from app.services import resolve_request_context
from app.services import serialize_user
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Header
from sqlalchemy.orm import Session
from typing import Optional


router = APIRouter()

def validate_artist_binding(db, group_code, artist_id):
    if artist_id is None:
        return
    if group_code != 'Artist':
        raise HTTPException(status_code=400, detail='Only artist accounts can bind an artist')
    if not db.get(Artist, artist_id):
        raise HTTPException(status_code=400, detail='Artist not found')

def require_binding_admin(db, authorization):
    context = resolve_request_context(db, authorization=authorization or '')
    if context.user.group_code != 'root':
        raise HTTPException(status_code=403, detail='Only administrators can manage artist bindings')


@router.get('/user-groups')
def list_user_groups(db: Session = Depends(get_db)):
    get_or_create_default_context(db)
    return json_ok([
        {"code": group["code"], "name": group["name"], "role": group["role"]}
        for group in GROUPS
    ])

@router.get('/users')
def list_users(db: Session = Depends(get_db)):
    get_or_create_default_context(db)
    users = db.query(User).filter(User.status == 'active').order_by(User.id.asc()).all()
    return json_ok([serialize_user(user) for user in users])

@router.post('/users')
def create_user(payload: UserCreateIn, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    tenant, _ = get_or_create_default_context(db)
    if payload.group_code not in {group["code"] for group in GROUPS}:
        raise HTTPException(status_code=400, detail='Invalid user group')
    if payload.group_code == 'Artist' or payload.artist_id is not None:
        require_binding_admin(db, authorization)
    validate_artist_binding(db, payload.group_code, payload.artist_id)
    existing = db.query(User).filter(User.account == payload.account).first()
    if existing:
        raise HTTPException(status_code=409, detail='User already exists')
    user = User(
        account=payload.account,
        name=payload.name,
        phone=payload.phone or '',
        password_hash=hash_password(payload.password),
        group_code=payload.group_code,
        artist_id=payload.artist_id,
        status='active',
    )
    group = db.query(UserGroup).filter(UserGroup.tenant_id == tenant.id, UserGroup.name == payload.group_code).first()
    if group:
        user.group_id = group.id
    db.add(user)
    db.commit()
    db.refresh(user)
    return json_ok(serialize_user(user))

@router.patch('/users/{user_id}')
def update_user(user_id: int, payload: UserUpdateIn, db: Session = Depends(get_db), authorization: Optional[str] = Header(default=None)):
    tenant, _ = get_or_create_default_context(db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    next_group = payload.group_code if payload.group_code is not None else user.group_code
    if user.artist_id is not None or next_group == 'Artist' or 'artist_id' in payload.model_fields_set:
        require_binding_admin(db, authorization)
    if 'artist_id' in payload.model_fields_set:
        validate_artist_binding(db, next_group, payload.artist_id)
        user.artist_id = payload.artist_id
    if next_group != 'Artist':
        user.artist_id = None
    if payload.group_code is not None:
        if payload.group_code not in {group["code"] for group in GROUPS}:
            raise HTTPException(status_code=400, detail='Invalid user group')
        group = db.query(UserGroup).filter(UserGroup.tenant_id == tenant.id, UserGroup.name == payload.group_code).first()
        if group:
            user.group_id = group.id
        user.group_code = payload.group_code
    if payload.name is not None:
        user.name = payload.name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.status is not None:
        user.status = payload.status
    db.commit()
    db.refresh(user)
    return json_ok(serialize_user(user))

@router.delete('/users/{user_id}')
def delete_user(user_id: int, db: Session = Depends(get_db)):
    get_or_create_default_context(db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    if user.account == 'root':
        raise HTTPException(status_code=400, detail='Root user cannot be deleted')
    db.query(AIGeneration).filter(AIGeneration.user_id == user.id).update(
        {AIGeneration.user_id: None}, synchronize_session=False,
    )
    db.query(TenantMember).filter(TenantMember.user_id == user.id).delete(synchronize_session=False)
    db.query(Order).filter(Order.user_id == user.id).update({Order.user_id: None}, synchronize_session=False)
    db.delete(user)
    db.commit()
    return json_ok({"deleted": True})

@router.get('/tenants')
def list_tenants(db: Session = Depends(get_db)):
    get_or_create_default_context(db)
    tenants = db.query(Tenant).order_by(Tenant.id.asc()).all()
    return json_ok([{"id": tenant.id, "name": tenant.name, "status": tenant.status} for tenant in tenants])

@router.post('/tenants/switch')
def switch_tenant(
    tenant_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    request_context = resolve_request_context(
        db,
        authorization=authorization or '',
        tenant_header=str(tenant_id),
    )
    tenant = request_context.tenant
    return json_ok({
        "token": create_session_token(request_context.user.id, tenant.id),
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
    })
