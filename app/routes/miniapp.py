from app.core.responses import json_ok
from app.database import get_db
from app.miniapp.entities import EntityRequestContext
from app.miniapp.entities import build_miniapp_entity_detail
from app.miniapp.screens import SCREEN_PROVIDERS
from app.miniapp.screens import ScreenRequestContext
from app.miniapp.screens import build_miniapp_screen
from app.models import Artist
from app.models import Project
from app.models import TenantMember
from app.models import User
from app.models import Venue
from app.schemas import ArtistOut
from app.services import resolve_request_context
from app.services import serialize_project
from app.services import serialize_user
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Header
from sqlalchemy.orm import Session
from typing import Optional


router = APIRouter()


PUBLIC_MINIAPP_SCREENS = frozenset({'S01', 'S04', 'S06', 'S07', 'S08', 'S09'})


@router.get('/miniapp/search')
def search_miniapp_entities(
    q: str,
    authorization: Optional[str] = Header(default=None),
    tenant_header: Optional[str] = Header(default=None, alias='X-Tenant-Id'),
    db: Session = Depends(get_db),
):
    keyword = ' '.join((q or '').strip().split())
    if not keyword:
        raise HTTPException(status_code=422, detail='Search keyword is required')
    request_context = resolve_request_context(
        db,
        authorization=authorization or '',
        tenant_header=tenant_header,
    )
    tenant_id = request_context.tenant.id
    like = f"%{keyword}%"

    artists = db.query(Artist).filter(
        (Artist.name.like(like)) | (Artist.tags.like(like))
    ).order_by(Artist.heat_score.desc(), Artist.id.asc()).limit(8).all()
    projects = db.query(Project).filter(
        Project.tenant_id == tenant_id,
        (
            (Project.name.like(like))
            | (Project.artist_name.like(like))
            | (Project.city.like(like))
            | (Project.venue.like(like))
        ),
    ).order_by(Project.id.desc()).limit(8).all()
    venues = db.query(Venue).filter(
        Venue.tenant_id == tenant_id,
        (Venue.name.like(like)) | (Venue.city.like(like)),
    ).order_by(Venue.city.asc(), Venue.name.asc()).limit(8).all()
    members = db.query(User).join(
        TenantMember,
        TenantMember.user_id == User.id,
    ).filter(
        TenantMember.tenant_id == tenant_id,
        User.status == 'active',
        (User.name.like(like)) | (User.account.like(like)) | (User.phone.like(like)),
    ).order_by(User.name.asc(), User.id.asc()).limit(8).all()
    cities = sorted({venue.city for venue in venues if venue.city and keyword in venue.city})[:8]

    groups = [
        {
            "entity_type": "artist",
            "label": "艺人 / IP",
            "items": [
                {
                    "entity_type": "artist",
                    "entity_id": artist.id,
                    "label": artist.name,
                    "description": artist.tags or '',
                    "value": ArtistOut.model_validate(artist).model_dump(),
                }
                for artist in artists
            ],
        },
        {
            "entity_type": "project",
            "label": "历史项目",
            "items": [
                {
                    "entity_type": "project",
                    "entity_id": project.id,
                    "label": project.name,
                    "description": ' · '.join(filter(None, [project.artist_name, project.city, project.venue])),
                    "value": serialize_project(project),
                }
                for project in projects
            ],
        },
        {
            "entity_type": "venue",
            "label": "场馆",
            "items": [
                {
                    "entity_type": "venue",
                    "entity_id": venue.id,
                    "label": venue.name,
                    "description": ' · '.join(filter(None, [
                        venue.city,
                        f"{venue.capacity} 人" if venue.capacity is not None else '',
                    ])),
                    "value": {
                        "id": venue.id,
                        "name": venue.name,
                        "city": venue.city,
                        "address": venue.address,
                        "capacity": venue.capacity,
                        "quote": venue.quote,
                    },
                }
                for venue in venues
            ],
        },
        {
            "entity_type": "city",
            "label": "城市",
            "items": [
                {
                    "entity_type": "city",
                    "entity_id": f"city:{city}",
                    "label": city,
                    "description": "已有场馆城市",
                    "value": city,
                }
                for city in cities
            ],
        },
        {
            "entity_type": "member",
            "label": "团队成员",
            "items": [
                {
                    "entity_type": "member",
                    "entity_id": member.id,
                    "label": member.name,
                    "description": member.account or member.phone or '',
                    "value": serialize_user(member),
                }
                for member in members
            ],
        },
    ]
    return json_ok({
        "keyword": keyword,
        "groups": [group for group in groups if group["items"]],
    })

@router.get('/miniapp/screens/{screen_id}')
def get_miniapp_screen(
    screen_id: str,
    project_id: Optional[int] = None,
    version_id: Optional[int] = None,
    task_id: Optional[int] = None,
    artist_id: Optional[int] = None,
    keyword: str = '',
    authorization: Optional[str] = Header(default=None),
    tenant_header: Optional[str] = Header(default=None, alias='X-Tenant-Id'),
    db: Session = Depends(get_db),
):
    if screen_id not in SCREEN_PROVIDERS:
        raise HTTPException(status_code=400, detail='Unknown miniapp screen')

    tenant_id = None
    user_id = None
    if screen_id not in PUBLIC_MINIAPP_SCREENS:
        request_context = resolve_request_context(
            db,
            authorization=authorization or '',
            tenant_header=tenant_header,
        )
        tenant_id = request_context.tenant.id
        user_id = request_context.user.id

    data = build_miniapp_screen(
        screen_id,
        ScreenRequestContext(
            tenant_id=tenant_id,
            user_id=user_id,
            project_id=project_id,
            version_id=version_id,
            task_id=task_id,
            artist_id=artist_id,
            keyword=keyword,
        ),
        db,
    )
    return json_ok(data.model_dump())

@router.get('/miniapp/entities/{entity_type}/{entity_id}')
def get_miniapp_entity_detail(
    entity_type: str,
    entity_id: int,
    authorization: Optional[str] = Header(default=None),
    tenant_header: Optional[str] = Header(default=None, alias='X-Tenant-Id'),
    db: Session = Depends(get_db),
):
    tenant_id = None
    user_id = None
    if entity_type != "show":
        request_context = resolve_request_context(
            db,
            authorization=authorization or '',
            tenant_header=tenant_header,
        )
        tenant_id = request_context.tenant.id
        user_id = request_context.user.id
    data = build_miniapp_entity_detail(
        entity_type,
        entity_id,
        EntityRequestContext(tenant_id=tenant_id, user_id=user_id),
        db,
    )
    return json_ok(data.model_dump())
