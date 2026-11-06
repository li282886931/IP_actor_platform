import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Artist, AgentPermission, AlertEvent, Assumption, Decision, DocumentParseJob,
    Evidence, Fact, Gate, Project, ProjectActual, ProjectAnalysisJob,
    ProjectWorkPlan, ProjectVersion, MemberInvitation, Notification,
    PrivacyConsent, ReportShare, Risk, Show, Task, TicketingSnapshot, Tenant,
    TenantMember, TourPlan, TourStop, User, UserSetting, Venue,
)
from app.schemas import MiniappScreenData
from app.services import serialize_project, serialize_user, serialize_version
from .common import (
    ScreenRequestContext, _empty_state, _get_current_version, _get_project,
    _screen_context, _user_names,
)


def _artist_item(artist: Artist) -> dict:
    return {
        "id": f"artist-{artist.id}",
        "entity_type": "artist",
        "title": artist.name,
        "description": artist.tags or None,
        "status": "available",
        "value": str(artist.heat_score),
        "context": {
            "artist_id": artist.id,
            "fan_count": artist.fan_count,
            "risk_level": artist.risk_level,
            "profile": artist.profile or {},
        },
    }


def _discovery_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id in {"S04", "S09"}:
        shows_query = db.query(Show)
        keyword = context.keyword.strip()
        if keyword:
            like = f"%{keyword}%"
            shows_query = shows_query.filter(
                (Show.title.like(like))
                | (Show.artist_name.like(like))
                | (Show.city.like(like))
                | (Show.venue.like(like))
            )
        shows = shows_query.order_by(Show.id.desc()).all()
        value_evidence = [
            {
                "title": show.title,
                "metric": show.price or None,
                "source_label": "当前机会",
                "context": {"show_id": show.id},
            }
            for show in shows[:3]
        ]
        return {
            "screen_id": screen_id,
            "summary": {
                "title": "发现演出" if screen_id == "S04" else "搜索演出",
                "subtitle": "来自真实演出数据",
                "highlight": str(len(shows)),
            },
            "items": [
                {
                    "id": f"show-{show.id}",
                    "entity_type": "show",
                    "title": show.title,
                    "description": " · ".join(filter(None, [
                        show.artist_name,
                        show.city,
                        show.date,
                        show.venue,
                    ])) or None,
                    "status": show.status,
                    "value": show.price or None,
                    "details": show.description or None,
                    "context": {
                        "show_id": show.id,
                        "artist_id": show.artist_id,
                        "poster_url": show.poster_url,
                    },
                }
                for show in shows
            ],
            "options": {
                "keyword": keyword,
                "value_evidence": value_evidence if screen_id == "S04" else [],
                "quick_start": {"target_screen": "S13"} if screen_id == "S04" else None,
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无演出", "当前没有可展示的真实演出") if not shows else None,
        }

    status = "completed" if screen_id in {"S06", "S07"} else "opportunity"
    shows = db.query(Show).filter(Show.status == status).order_by(Show.id.desc()).all()
    title = "真实案例" if status == "completed" else "真实机会"
    empty_title = "暂无真实案例" if status == "completed" else "暂无真实机会"
    return {
        "screen_id": screen_id,
        "summary": {
            "title": title,
            "subtitle": "仅展示已有业务记录",
            "highlight": str(len(shows)),
        },
        "items": [
            {
                "id": f"show-{show.id}",
                "entity_type": "show",
                "title": show.title,
                "description": " · ".join(filter(None, [show.artist_name, show.city, show.venue])) or None,
                "status": show.status,
                "value": show.price or None,
                "details": show.description or None,
                "context": {"show_id": show.id, "artist_id": show.artist_id},
            }
            for show in shows
        ],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state(empty_title, f"尚无标记为{title}的演出记录") if not shows else None,
    }


def _discovery_dashboard_screen(db: Session, context: ScreenRequestContext) -> dict:
    projects = db.query(Project).filter(Project.tenant_id == context.tenant_id).all()
    active_projects = [project for project in projects if project.status != "archived"]
    return {
        "screen_id": "S05",
        "summary": {
            "title": "业务概览",
            "subtitle": "当前客户空间的真实项目",
            "highlight": str(len(active_projects)),
        },
        "items": [
            {
                "id": f"project-{project.id}",
                "entity_type": "project",
                "title": project.name,
                "description": " · ".join(filter(None, [project.artist_name, project.city])) or None,
                "status": project.status,
                "context": {"project_id": project.id},
            }
            for project in sorted(projects, key=lambda item: item.id, reverse=True)
        ],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无项目", "创建项目后可查看业务概览", "S13") if not projects else None,
    }


def _portfolio_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S19":
        artist_ids = [
            artist_id
            for (artist_id,) in db.query(Project.artist_id).filter(
                Project.tenant_id == context.tenant_id,
                Project.artist_id.isnot(None),
            ).distinct().all()
        ]
        artists = (
            db.query(Artist)
            .filter(Artist.id.in_(artist_ids))
            .order_by(Artist.heat_score.desc(), Artist.id.desc())
            .all()
            if artist_ids else []
        )
        return {
            "screen_id": screen_id,
            "summary": {
                "title": "艺人候选",
                "subtitle": "来自当前客户空间项目",
                "highlight": str(len(artists)),
            },
            "items": [_artist_item(artist) for artist in artists],
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无艺人候选", "先在项目中选择真实艺人") if not artists else None,
        }

    if screen_id == "S20":
        artist = db.query(Artist).filter(Artist.id == context.artist_id).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")
        artist_payload = {
            "id": artist.id,
            "name": artist.name,
            "tags": artist.tags,
            "heat_score": artist.heat_score,
            "fan_count": artist.fan_count,
            "risk_level": artist.risk_level,
            "profile": artist.profile or {},
        }
        return {
            "screen_id": screen_id,
            "summary": {
                "title": artist.name,
                "subtitle": artist.tags or None,
                "highlight": str(artist.heat_score),
            },
            "items": [_artist_item(artist)],
            "options": {"artist": artist_payload},
            "context": _screen_context(context),
            "empty_state": None,
        }

    project = _get_project(db, context)
    if screen_id == "S21":
        artists = db.query(Artist).order_by(Artist.heat_score.desc(), Artist.id.desc()).all()
        return {
            "screen_id": screen_id,
            "summary": {"title": f"{project.name}艺人对比", "subtitle": "真实艺人库", "highlight": str(len(artists))},
            "items": [_artist_item(artist) for artist in artists],
            "options": {"selected_artist_id": project.artist_id},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无可比艺人", "艺人库暂无真实记录") if not artists else None,
        }

    venues = db.query(Venue).filter(
        Venue.tenant_id == context.tenant_id,
    ).order_by(Venue.city.asc(), Venue.name.asc()).all()
    if screen_id == "S22":
        city_rows = {}
        for venue in venues:
            aggregate = city_rows.setdefault(venue.city, {
                "venue_count": 0,
                "total_capacity": 0,
                "quoted_venue_count": 0,
            })
            aggregate["venue_count"] += 1
            aggregate["total_capacity"] += venue.capacity or 0
            aggregate["quoted_venue_count"] += int(venue.quote is not None)
        items = [
            {
                "id": f"city-{city}",
                "entity_type": "city",
                "title": city,
                "description": f"{values['venue_count']} 个真实场馆",
                "value": str(values["total_capacity"]) if values["total_capacity"] else None,
                "context": {"city": city, **values},
            }
            for city, values in sorted(city_rows.items())
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": f"{project.name}城市对比", "subtitle": "按真实场馆数据聚合", "highlight": str(len(items))},
            "items": items,
            "options": {"selected_city": project.city},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无城市候选", "当前客户空间尚无场馆数据") if not items else None,
        }

    if screen_id == "S23":
        projects = db.query(Project).filter(
            Project.tenant_id == context.tenant_id,
            Project.schedule != "",
        ).order_by(Project.schedule.asc(), Project.id.asc()).all()
        return {
            "screen_id": screen_id,
            "summary": {"title": f"{project.name}档期选择", "subtitle": "来自已保存项目档期", "highlight": str(len(projects))},
            "items": [
                {
                    "id": f"schedule-{item.id}",
                    "entity_type": "project_schedule",
                    "title": item.schedule,
                    "description": item.name,
                    "status": item.status,
                    "context": {"project_id": item.id, "schedule": item.schedule},
                }
                for item in projects
            ],
            "options": {"selected_schedule": project.schedule},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无档期候选", "尚无项目保存了真实档期") if not projects else None,
        }

    items = [
        {
            "id": f"venue-{venue.id}",
            "entity_type": "venue",
            "title": venue.name,
            "description": " · ".join(filter(None, [venue.city, venue.address])) or None,
            "status": venue.fire_safety_status,
            "value": str(venue.quote) if venue.quote is not None else None,
            "details": venue.transport_notes or None,
            "context": {
                "venue_id": venue.id,
                "city": venue.city,
                "capacity": venue.capacity,
                "quote": venue.quote,
                "fire_safety_status": venue.fire_safety_status,
                "source": venue.source,
            },
        }
        for venue in venues
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": f"{project.name}场馆候选", "subtitle": "当前客户空间真实场馆", "highlight": str(len(items))},
        "items": items,
        "options": {"selected_venue_id": project.venue_id},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无场馆候选", "先录入真实场馆容量与报价") if not items else None,
    }
