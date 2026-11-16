import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.responses import json_ok
from app.database import get_db
from app.integrations.image_generation import generate_image
from app.integrations.object_storage import configured_image_bucket, generated_image_link, store_generated_image
from app.models import AIGeneration
from app.routes.ai import generation_context
from app.services.auth import RequestContext

router = APIRouter()


class AIImageIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    image_size: Literal[
        'square_hd', 'square', 'portrait_4_3', 'portrait_16_9', 'landscape_4_3', 'landscape_16_9',
    ] = 'portrait_4_3'
    generation_nonce: str | None = Field(default=None, min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_-]+$')

    @field_validator('prompt')
    @classmethod
    def nonblank_prompt(cls, value):
        if not value.strip():
            raise ValueError('请填写图片创作描述')
        return value.strip()


@contextmanager
def request_lock(db: Session, key: str):
    """MySQL advisory locks cover workers and replicas; local DBs use bounded file locks."""
    if db.get_bind().dialect.name == 'mysql':
        with db.get_bind().connect() as connection:
            name = f'ai-image:{key[:48]}'
            if connection.execute(text('SELECT GET_LOCK(:name, 280)'), {'name': name}).scalar() != 1:
                raise HTTPException(409, '同一图片请求仍在处理中，请稍后重试')
            try:
                yield
            finally:
                connection.execute(text('SELECT RELEASE_LOCK(:name)'), {'name': name})
    else:
        path = os.path.join(tempfile.gettempdir(), f'ip-actor-image-{int(key[:4], 16) % 128}.lock')
        with open(path, 'a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def own_images(db, context):
    return db.query(AIGeneration).filter_by(
        type='image', tenant_id=context.tenant.id, user_id=context.user.id,
    )


def record_response(record, bucket=None):
    metadata = json.loads(record.result)
    return json_ok({'id': record.id, **generated_image_link(metadata, bucket)})


@router.post('/ai/generate/image')
def create_image(payload: AIImageIn, db: Session = Depends(get_db), context: RequestContext = Depends(generation_context)):
    nonce = payload.generation_nonce or uuid.uuid4().hex
    request_key = hashlib.sha256(f'{context.tenant.id}:{context.user.id}:{nonce}'.encode()).hexdigest()
    fingerprint = f'ai-image-request:{request_key}'
    description = {'prompt': payload.prompt, 'image_size': payload.image_size}
    with request_lock(db, request_key):
        # Authentication performed read-only queries. Start a fresh snapshot after
        # acquiring the lock so a waiting retry sees the previous request's commit.
        db.rollback()
        existing = own_images(db, context).filter_by(prompt=fingerprint).first()
        if existing:
            meta = json.loads(existing.result)
            if any(meta[k] != v for k, v in description.items()):
                raise HTTPException(409, '该请求编号已用于其他图片，请使用新的请求编号')
            return record_response(existing)
        bucket = configured_image_bucket()
        content, image_meta = generate_image(payload.prompt, payload.image_size)
        key = f'ai-images/{context.tenant.id}/{context.user.id}/{request_key}.{image_meta["extension"]}'
        metadata = store_generated_image(bucket, key, content, {**image_meta, **description})
        # Validate link configuration before saving a successful generation.
        response = generated_image_link(metadata, bucket)
        record = AIGeneration(
            type='image', tenant_id=context.tenant.id, user_id=context.user.id,
            prompt=fingerprint, result=json.dumps(metadata, ensure_ascii=False),
        )
        try:
            db.add(record)
            db.flush()
            record_id = record.id
            db.commit()
        except Exception:
            db.rollback()
            raise HTTPException(502, '图片记录保存失败，请重试') from None
    return json_ok({'id': record_id, **response})


@router.get('/ai/images/{image_id}')
def get_image(image_id: int, db: Session = Depends(get_db), context: RequestContext = Depends(generation_context)):
    record = own_images(db, context).filter_by(id=image_id).first()
    if not record:
        raise HTTPException(404, '图片不存在或无权访问')
    return record_response(record)
