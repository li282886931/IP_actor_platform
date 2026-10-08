import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import (
    Artist,
    AgentPermission,
    AlertEvent,
    Assumption,
    Decision,
    DocumentParseJob,
    Evidence,
    Fact,
    Gate,
    Project,
    ProjectActual,
    ProjectAnalysisJob,
    ProjectWorkPlan,
    ProjectVersion,
    MemberInvitation,
    Notification,
    PrivacyConsent,
    ReportShare,
    Risk,
    Show,
    Task,
    TicketingSnapshot,
    Tenant,
    TenantMember,
    TourPlan,
    TourStop,
    User,
    UserSetting,
    Venue,
)
from .schemas import MiniappScreenData
from .services import serialize_project, serialize_user, serialize_version


@dataclass(frozen=True)
class ScreenRequestContext:
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    version_id: Optional[int] = None
    task_id: Optional[int] = None
    artist_id: Optional[int] = None
    keyword: str = ''


@dataclass(frozen=True)
class ScreenRegistration:
    screen_id: str
    provider_key: str
    domain: str
    required_context: frozenset[str] = field(default_factory=frozenset)


def _registration(
    screen_id: str,
    provider_key: str,
    domain: str,
    *required_context: str,
) -> ScreenRegistration:
    return ScreenRegistration(
        screen_id=screen_id,
        provider_key=provider_key,
        domain=domain,
        required_context=frozenset(required_context),
    )


_REGISTRATIONS = [
    _registration('S01', 'auth_login', 'auth'),
    _registration('S02', 'tenant_select', 'auth', 'user_id'),
    _registration('S03', 'privacy_scope', 'auth', 'tenant_id', 'user_id'),
    _registration('S04', 'discovery_public', 'discovery'),
    _registration('S05', 'discovery_dashboard', 'discovery', 'tenant_id', 'user_id'),
    _registration('S06', 'case_list', 'discovery'),
    _registration('S07', 'case_detail', 'discovery'),
    _registration('S08', 'opportunity_detail', 'discovery'),
    _registration('S09', 'discovery_search', 'discovery'),
    _registration('S10', 'project_list', 'project', 'tenant_id'),
    _registration('S11', 'project_detail', 'project', 'tenant_id', 'project_id'),
    _registration('S12', 'project_versions', 'project', 'tenant_id', 'project_id'),
    _registration('S13', 'project_create_basic', 'project', 'tenant_id', 'user_id'),
    _registration('S14', 'project_create_schedule', 'project', 'tenant_id', 'user_id'),
    _registration('S15', 'project_create_scale', 'project', 'tenant_id', 'user_id'),
    _registration('S16', 'project_create_costs', 'project', 'tenant_id', 'user_id'),
    _registration('S17', 'project_create_review', 'project', 'tenant_id', 'user_id'),
    _registration('S18', 'project_draft', 'project', 'tenant_id', 'user_id'),
    _registration('S19', 'artist_candidates', 'portfolio', 'tenant_id'),
    _registration('S20', 'artist_detail', 'portfolio', 'artist_id'),
    _registration('S21', 'artist_compare', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S22', 'city_compare', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S23', 'schedule_options', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S24', 'venue_options', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S25', 'finance_input', 'finance', 'tenant_id', 'project_id'),
    _registration('S26', 'ticket_tiers', 'finance', 'tenant_id', 'project_id'),
    _registration('S27', 'cost_breakdown', 'finance', 'tenant_id', 'project_id'),
    _registration('S28', 'finance_conservative', 'finance', 'tenant_id', 'project_id'),
    _registration('S29', 'finance_neutral', 'finance', 'tenant_id', 'project_id'),
    _registration('S30', 'finance_optimistic', 'finance', 'tenant_id', 'project_id'),
    _registration('S31', 'finance_breakeven', 'finance', 'tenant_id', 'project_id'),
    _registration('S32', 'finance_sensitivity', 'finance', 'tenant_id', 'project_id'),
    _registration('S33', 'finance_funding_gap', 'finance', 'tenant_id', 'project_id'),
    _registration('S34', 'judgement_summary', 'decision', 'tenant_id', 'project_id'),
    _registration('S35', 'judgement_explanation', 'decision', 'tenant_id', 'project_id'),
    _registration('S36', 'assumption_list', 'evidence', 'tenant_id', 'project_id'),
    _registration('S37', 'fact_list', 'evidence', 'tenant_id', 'project_id'),
    _registration('S38', 'evidence_detail', 'evidence', 'tenant_id', 'project_id'),
    _registration('S39', 'evidence_conflicts', 'evidence', 'tenant_id', 'project_id'),
    _registration('S40', 'evidence_gaps', 'evidence', 'tenant_id', 'project_id'),
    _registration('S41', 'evidence_upload_context', 'evidence', 'tenant_id', 'project_id'),
    _registration('S42', 'document_parse_review', 'evidence', 'tenant_id', 'project_id'),
    _registration('S43', 'risk_list', 'risk', 'tenant_id', 'project_id'),
    _registration('S44', 'risk_detail', 'risk', 'tenant_id', 'project_id'),
    _registration('S45', 'gate_list', 'gate', 'tenant_id', 'project_id'),
    _registration('S46', 'gate_detail', 'gate', 'tenant_id', 'project_id'),
    _registration('S47', 'decision_confirm', 'decision', 'tenant_id', 'project_id', 'version_id'),
    _registration('S48', 'decision_result', 'decision', 'tenant_id', 'project_id'),
    _registration('S49', 'version_compare', 'version', 'tenant_id', 'project_id'),
    _registration('S50', 'report_preview', 'report', 'tenant_id', 'project_id'),
    _registration('S51', 'report_share', 'report', 'tenant_id', 'project_id'),
    _registration('S52', 'agent_dashboard', 'agent', 'tenant_id', 'user_id'),
    _registration('S53', 'agent_plan', 'agent', 'tenant_id', 'project_id'),
    _registration('S54', 'agent_chat', 'agent', 'tenant_id', 'project_id'),
    _registration('S55', 'task_list', 'task', 'tenant_id'),
    _registration('S56', 'task_batch', 'task', 'tenant_id'),
    _registration('S57', 'task_submit', 'task', 'tenant_id', 'task_id'),
    _registration('S58', 'task_block', 'task', 'tenant_id', 'task_id'),
    _registration('S59', 'project_changes', 'agent', 'tenant_id', 'project_id'),
    _registration('S60', 'agent_permissions', 'agent', 'tenant_id', 'user_id'),
    _registration('S61', 'tour_overview', 'tour', 'tenant_id'),
    _registration('S62', 'tour_route', 'tour', 'tenant_id'),
    _registration('S63', 'tour_stop', 'tour', 'tenant_id', 'project_id'),
    _registration('S64', 'ticketing_progress', 'review', 'tenant_id', 'project_id'),
    _registration('S65', 'project_actuals', 'review', 'tenant_id', 'project_id'),
    _registration('S66', 'project_review', 'review', 'tenant_id', 'project_id'),
    _registration('S67', 'account_home', 'account', 'tenant_id', 'user_id'),
    _registration('S68', 'team_members', 'account', 'tenant_id'),
    _registration('S69', 'notifications', 'account', 'tenant_id', 'user_id'),
    _registration('S70', 'user_settings', 'account', 'tenant_id', 'user_id'),
    _registration('S71', 'data_permissions', 'account', 'tenant_id', 'user_id'),
    _registration('S72', 'member_invite', 'account', 'tenant_id', 'user_id'),
    _registration('S73', 'project_empty', 'state', 'tenant_id'),
    _registration('S74', 'analysis_processing', 'state', 'tenant_id', 'project_id'),
    _registration('S75', 'network_failure', 'state', 'user_id'),
    _registration('S76', 'context_unavailable', 'state', 'user_id'),
    _registration('S77', 'permission_denied', 'state', 'user_id'),
    _registration('S78', 'version_changed', 'state', 'tenant_id', 'project_id', 'version_id'),
    _registration('S79', 'validation_error', 'state', 'user_id'),
    _registration('S80', 'archive_confirmation', 'state', 'tenant_id', 'project_id'),
    _registration('S81', 'auth_expired', 'state', 'user_id'),
    _registration('S82', 'developer_connection', 'settings', 'user_id'),
    _registration('S83', 'notification_preferences', 'settings', 'tenant_id', 'user_id'),
    _registration('S84', 'privacy_records', 'settings', 'tenant_id', 'user_id'),
]

SCREEN_PROVIDERS = {
    registration.screen_id: registration
    for registration in _REGISTRATIONS
}


def _screen_context(context: ScreenRequestContext) -> dict:
    return {
        "tenant_id": context.tenant_id,
        "user_id": context.user_id,
        "project_id": context.project_id,
        "version_id": context.version_id,
        "task_id": context.task_id,
        "artist_id": context.artist_id,
    }


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


def _project_list_screen(db: Session, context: ScreenRequestContext) -> dict:
    projects = db.query(Project).filter(
        Project.tenant_id == context.tenant_id,
    ).order_by(Project.id.desc()).all()
    active_count = sum(project.status != 'archived' for project in projects)
    return {
        "screen_id": "S10",
        "summary": {
            "title": "我的项目",
            "subtitle": "快速查看判断、待办和版本变化",
            "highlight": str(active_count),
        },
        "items": [
            {
                "id": f"project-{project.id}",
                "entity_type": "project",
                "title": project.name,
                "description": " · ".join(filter(None, [
                    project.artist_name,
                    project.city,
                    project.schedule,
                ])) or None,
                "status": project.status,
                "context": {"project_id": project.id},
            }
            for project in projects
        ],
        "options": {},
        "context": _screen_context(context),
        "empty_state": {
            "title": "暂无项目",
            "description": "创建项目后可在这里查看判断与待办",
            "action": {
                "label": "创建项目",
                "target_screen": "S13",
            },
        },
    }


def _get_project(db: Session, context: ScreenRequestContext) -> Project:
    project = db.query(Project).filter(
        Project.id == context.project_id,
        Project.tenant_id == context.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return project


def _get_current_version(db: Session, project: Project) -> Optional[ProjectVersion]:
    if project.current_version_id:
        return db.query(ProjectVersion).filter(
            ProjectVersion.id == project.current_version_id,
            ProjectVersion.project_id == project.id,
        ).first()
    return None


def _project_detail_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    response_context = _screen_context(context)
    response_context["version_id"] = current_version.id if current_version else None
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else {}
    )
    neutral = (finance_result.get("scenarios") or {}).get("neutral")
    total_cost = finance_result.get("total_cost")
    available_funds = project.available_funds
    funding_gap = (
        max(total_cost - available_funds, 0)
        if total_cost is not None and available_funds is not None
        else None
    )
    return {
        "screen_id": "S11",
        "summary": {
            "title": project.name,
            "subtitle": " · ".join(filter(None, [
                project.artist_name,
                project.city,
                project.schedule,
            ])) or None,
            "highlight": project.status,
        },
        "items": [{
            "id": f"project-{project.id}",
            "entity_type": "project",
            "title": project.name,
            "description": project.venue or None,
            "status": project.status,
            "context": {
                "project_id": project.id,
                "version_id": current_version.id if current_version else None,
            },
        }],
        "options": {
            "project": serialize_project(project),
            "current_version": serialize_version(current_version) if current_version else None,
            "decision_cockpit": {
                "neutral_profit": neutral.get("profit") if neutral else None,
                "breakeven_attendance": finance_result.get("breakeven_attendance"),
                "maximum_funding_gap": funding_gap,
                "status": finance_result.get("status") or "pending_input",
                "combination": {
                    "artist": project.artist_name or None,
                    "city": project.city or None,
                    "schedule": project.schedule or None,
                    "venue": project.venue or None,
                    "venue_capacity": project.venue_capacity,
                    "ticket_tiers": project.ticket_tiers or [],
                    "available_funds": available_funds,
                },
                "missing_fields": finance_result.get("missing_fields") or [],
            },
        },
        "context": response_context,
        "empty_state": None,
    }


def _project_versions_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    versions = db.query(ProjectVersion).filter(
        ProjectVersion.project_id == project.id,
    ).order_by(ProjectVersion.version_no.asc()).all()
    return {
        "screen_id": "S12",
        "summary": {
            "title": f"{project.name}版本",
            "subtitle": "按创建顺序查看输入与测算变化",
            "highlight": str(len(versions)),
        },
        "items": [
            {
                "id": f"version-{version.id}",
                "entity_type": "project_version",
                "title": f"版本 {version.version_no}",
                "status": version.status,
                "value": str(version.version_no),
                "context": {
                    "project_id": project.id,
                    "version_id": version.id,
                    "is_current": version.id == project.current_version_id,
                    "version": serialize_version(version),
                },
            }
            for version in versions
        ],
        "options": {
            "current_version_id": project.current_version_id,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "暂无项目版本",
            "description": "保存项目后会生成首个版本",
            "action": None,
        },
    }


PROJECT_CREATE_TITLES = {
    "project_create_basic": "创建项目",
    "project_create_schedule": "地点与时间",
    "project_create_scale": "规模与资金",
    "project_create_costs": "成本信息",
    "project_create_review": "确认创建",
}


PROJECT_CANDIDATE_LIMIT = 8


def _candidate_item(
    key: str,
    label: str,
    patch: dict,
    *,
    description: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> dict:
    item = {
        "key": key,
        "label": label,
        "description": description or "",
        "patch": patch,
    }
    if entity_type is not None and entity_id is not None:
        item["entity_type"] = entity_type
        item["entity_id"] = entity_id
    return item


def _candidate_group(key: str, label: str, field: str, items: list[dict]) -> dict:
    return {
        "key": key,
        "label": label,
        "field": field,
        "search_mode": "remote" if field in {"artist_name", "city", "venue", "source_project_id"} else "local",
        "items": items[:PROJECT_CANDIDATE_LIMIT],
    }


def _ranked_values(values: list[str]) -> list[str]:
    normalized = [value.strip() for value in values if value and value.strip()]
    counts = Counter(normalized)
    latest_index = {
        value: index
        for index, value in enumerate(normalized)
    }
    return sorted(
        counts,
        key=lambda value: (-counts[value], -latest_index[value], value),
    )[:PROJECT_CANDIDATE_LIMIT]


def _numeric_candidate_group(
    projects: list[Project],
    key: str,
    label: str,
    field_name: str,
    unit: str,
) -> dict:
    values = _ranked_values([
        str(getattr(project, field_name))
        for project in projects
        if getattr(project, field_name) is not None
        and getattr(project, field_name) > 0
    ])
    return _candidate_group(key, label, field_name, [
        _candidate_item(
            f"{field_name}-{value}",
            f"{int(value):,} {unit}",
            {field_name: int(value)},
        )
        for value in values
    ])


def _project_candidate_groups(
    db: Session,
    tenant_id: int,
    screen_id: str,
) -> list[dict]:
    projects = db.query(Project).filter(
        Project.tenant_id == tenant_id,
    ).order_by(Project.id.desc()).all()
    venues = db.query(Venue).filter(
        Venue.tenant_id == tenant_id,
    ).order_by(Venue.id.desc()).all()
    artists = db.query(Artist).order_by(
        Artist.heat_score.desc(),
        Artist.id.desc(),
    ).limit(PROJECT_CANDIDATE_LIMIT).all()
    tour_stops = db.query(TourStop).join(
        TourPlan,
        TourPlan.id == TourStop.tour_plan_id,
    ).filter(
        TourPlan.tenant_id == tenant_id,
    ).order_by(TourStop.id.desc()).all()
    shows = db.query(Show).order_by(Show.id.desc()).limit(PROJECT_CANDIDATE_LIMIT).all()

    if screen_id == "S13":
        project_items = []
        for project in projects:
            patch = {
                key: value
                for key, value in {
                    "name": project.name,
                    "type": project.type,
                    "artist_id": project.artist_id,
                    "artist_name": project.artist_name,
                    "city": project.city,
                    "venue_id": project.venue_id,
                    "venue": project.venue,
                    "schedule": project.schedule,
                    "expected_attendance": project.expected_attendance,
                    "available_funds": project.available_funds,
                    "avg_ticket_price": project.avg_ticket_price,
                    "artist_fee": project.artist_fee,
                    "venue_cost": project.venue_cost,
                    "marketing_cost": project.marketing_cost,
                    "production_cost": project.production_cost,
                    "venue_capacity": project.venue_capacity,
                    "source_project_id": project.id,
                }.items()
                if value not in (None, "")
            }
            project_items.append(_candidate_item(
                f"project-{project.id}",
                project.name,
                patch,
                description=" · ".join(filter(None, [
                    project.artist_name,
                    project.city,
                    project.venue,
                ])),
                entity_type="project",
                entity_id=project.id,
            ))
        return [
            _candidate_group("projects", "近期项目", "source_project_id", project_items),
            _candidate_group("artists", "热门艺人", "artist_name", [
                _candidate_item(
                    f"artist-{artist.id}",
                    artist.name,
                    {"artist_id": artist.id, "artist_name": artist.name},
                    description=artist.tags or "",
                    entity_type="artist",
                    entity_id=artist.id,
                )
                for artist in artists
            ]),
            _candidate_group("project_types", "常用项目类型", "type", [
                _candidate_item(
                    f"project_type-{project_type}",
                    project_type,
                    {"type": project_type},
                )
                for project_type in _ranked_values([project.type for project in projects])
            ]),
        ]

    if screen_id == "S14":
        city_values = _ranked_values(
            [project.city for project in projects]
            + [venue.city for venue in venues]
            + [stop.city for stop in tour_stops]
            + [show.city for show in shows]
        )
        schedule_values = _ranked_values(
            [project.schedule for project in projects]
            + [stop.scheduled_at for stop in tour_stops]
            + [show.date for show in shows]
        )
        return [
            _candidate_group("cities", "常用城市", "city", [
                _candidate_item(f"city-{city}", city, {"city": city})
                for city in city_values
            ]),
            _candidate_group("venues", "高频场馆", "venue", [
                _candidate_item(
                    f"venue-{venue.id}",
                    venue.name,
                    {
                        "venue_id": venue.id,
                        "venue": venue.name,
                        "city": venue.city,
                        **({"venue_capacity": venue.capacity} if venue.capacity else {}),
                    },
                    description=" · ".join(filter(None, [
                        venue.city,
                        f"容量 {venue.capacity}" if venue.capacity else "",
                    ])),
                    entity_type="venue",
                    entity_id=venue.id,
                )
                for venue in venues
            ]),
            _candidate_group("schedules", "可选档期", "schedule", [
                _candidate_item(f"schedule-{schedule}", schedule, {"schedule": schedule})
                for schedule in schedule_values
            ]),
        ]

    numeric_fields = {
        "S15": [
            ("expected_attendance", "常用规模", "expected_attendance", "人"),
            ("available_funds", "可用资金", "available_funds", "元"),
            ("avg_ticket_price", "平均票价", "avg_ticket_price", "元"),
        ],
        "S16": [
            ("artist_fee", "艺人费用", "artist_fee", "元"),
            ("venue_cost", "场馆费用", "venue_cost", "元"),
            ("marketing_cost", "宣发费用", "marketing_cost", "元"),
            ("production_cost", "制作费用", "production_cost", "元"),
        ],
    }
    return [
        _numeric_candidate_group(
            projects,
            group_key,
            group_label,
            field_name,
            unit,
        )
        for group_key, group_label, field_name, unit in numeric_fields.get(screen_id, [])
    ]


def _project_create_screen(
    db: Session,
    context: ScreenRequestContext,
    provider_key: str,
    screen_id: str,
) -> dict:
    draft = db.query(Project).filter(
        Project.tenant_id == context.tenant_id,
        Project.created_by == context.user_id,
        Project.status == 'draft',
    ).order_by(Project.id.desc()).first()
    artists = db.query(Artist).order_by(
        Artist.heat_score.desc(),
        Artist.id.asc(),
    ).all()
    city_rows = db.query(Show.city).filter(Show.city != '').distinct().order_by(Show.city.asc()).all()
    return {
        "screen_id": screen_id,
        "summary": {
            "title": PROJECT_CREATE_TITLES[provider_key],
            "subtitle": "已保存内容会在当前客户空间恢复",
            "highlight": draft.name if draft else None,
        },
        "items": [],
        "options": {
            "draft": serialize_project(draft) if draft else None,
            "candidate_groups": _project_candidate_groups(
                db,
                context.tenant_id,
                screen_id,
            ),
            "artists": [
                {"id": artist.id, "name": artist.name}
                for artist in artists
            ],
            "cities": [city for city, in city_rows],
            "project_types": [
                {"value": "concert", "label": "演唱会"},
                {"value": "festival", "label": "音乐节"},
                {"value": "tour", "label": "巡演"},
            ],
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _project_draft_screen(db: Session, context: ScreenRequestContext) -> dict:
    drafts = db.query(Project).filter(
        Project.tenant_id == context.tenant_id,
        Project.created_by == context.user_id,
        Project.status == 'draft',
    ).order_by(Project.id.desc()).all()
    return {
        "screen_id": "S18",
        "summary": {
            "title": "项目草稿",
            "subtitle": "草稿按客户空间和创建人隔离",
            "highlight": str(len(drafts)),
        },
        "items": [
            {
                "id": f"project-{draft.id}",
                "entity_type": "project",
                "title": draft.name,
                "description": " · ".join(filter(None, [
                    draft.artist_name,
                    draft.city,
                    draft.schedule,
                ])) or None,
                "status": draft.status,
                "context": {"project_id": draft.id},
            }
            for draft in drafts
        ],
        "options": {},
        "context": _screen_context(context),
        "empty_state": {
            "title": "暂无草稿",
            "description": "创建项目时保存的内容会显示在这里",
            "action": {
                "label": "创建项目",
                "target_screen": "S13",
            },
        },
    }


def _finance_input_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else None
    )
    missing_fields = (
        finance_result.get("missing_fields", [])
        if finance_result
        else ["current_version.finance_result"]
    )
    response_context = _screen_context(context)
    response_context["version_id"] = current_version.id if current_version else None
    return {
        "screen_id": "S25",
        "summary": {
            "title": f"{project.name}财务测算",
            "subtitle": "测算结果来自当前项目版本",
            "highlight": finance_result.get("status") if finance_result else "pending_input",
        },
        "items": [],
        "options": {
            "project": serialize_project(project),
            "finance_result": finance_result,
            "missing_fields": missing_fields,
            "finance_cockpit": {
                "scenarios": finance_result.get("scenarios") if finance_result else {},
                "breakeven_attendance": finance_result.get("breakeven_attendance") if finance_result else None,
                "total_cost": finance_result.get("total_cost") if finance_result else None,
                "available_funds": project.available_funds,
                "maximum_funding_gap": (
                    max(finance_result["total_cost"] - project.available_funds, 0)
                    if finance_result and finance_result.get("total_cost") is not None
                    and project.available_funds is not None
                    else None
                ),
                "missing_fields": missing_fields,
            },
        },
        "context": response_context,
        "empty_state": {
            "title": "财务参数待补充",
            "description": "补齐必要参数后才能生成测算结果",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


FINANCE_SCENARIOS = {
    "finance_conservative": ("S28", "conservative", "保守情景"),
    "finance_neutral": ("S29", "neutral", "中性情景"),
    "finance_optimistic": ("S30", "optimistic", "乐观情景"),
}


def _finance_scenario_screen(
    db: Session,
    context: ScreenRequestContext,
    provider_key: str,
) -> dict:
    screen_id, scenario_name, title = FINANCE_SCENARIOS[provider_key]
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else {}
    )
    scenario = (finance_result.get("scenarios") or {}).get(scenario_name)
    missing_fields = finance_result.get("missing_fields") or []
    if not scenario and not missing_fields:
        missing_fields = [f"finance_result.scenarios.{scenario_name}"]
    response_context = _screen_context(context)
    response_context["version_id"] = current_version.id if current_version else None
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{title}",
            "subtitle": "结果来自当前项目版本",
            "highlight": finance_result.get("status") or "pending_input",
        },
        "items": [
            {
                "id": f"{scenario_name}-{key}",
                "entity_type": "finance_metric",
                "title": label,
                "value": str(scenario[key]),
                "context": {"metric": key, "scenario": scenario_name},
            }
            for key, label in (
                ("attendance", "预计人数"),
                ("revenue", "预计收入"),
                ("cost", "总成本"),
                ("profit", "预计利润"),
            )
        ] if scenario else [],
        "options": {
            "scenario_name": scenario_name,
            "scenario": scenario,
            "missing_fields": missing_fields,
        },
        "context": response_context,
        "empty_state": {
            "title": "情景测算参数不完整",
            "description": "补齐财务参数后再查看该情景",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if not scenario else None,
    }


def _ticket_tiers_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    ticket_tiers = project.ticket_tiers or []
    missing_fields = [] if ticket_tiers else ["ticket_tiers"]
    return {
        "screen_id": "S26",
        "summary": {
            "title": f"{project.name}票价结构",
            "subtitle": "票档价格和预计销售占比",
            "highlight": str(len(ticket_tiers)) if ticket_tiers else None,
        },
        "items": [
            {
                "id": f"ticket-tier-{index}",
                "entity_type": "ticket_tier",
                "title": tier.get("name") or f"票档 {index + 1}",
                "description": (
                    f"预计占比 {tier.get('share')}%"
                    if tier.get("share") is not None
                    else None
                ),
                "value": str(tier.get("price")) if tier.get("price") is not None else None,
                "context": {"index": index, "ticket_tier": tier},
            }
            for index, tier in enumerate(ticket_tiers)
        ],
        "options": {
            "ticket_tiers": ticket_tiers,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "票档待补充",
            "description": "添加真实票档后才能展示票价结构",
            "action": {
                "label": "补充票档",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


def _cost_breakdown_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        ("artist_fee", "艺人费用"),
        ("venue_cost", "场馆费用"),
        ("marketing_cost", "宣发费用"),
        ("production_cost", "制作费用"),
    )
    present_costs = [
        (field_name, label, getattr(project, field_name))
        for field_name, label in cost_fields
        if getattr(project, field_name) is not None
    ]
    missing_fields = [
        field_name
        for field_name, _ in cost_fields
        if getattr(project, field_name) is None
    ]
    return {
        "screen_id": "S27",
        "summary": {
            "title": f"{project.name}成本拆分",
            "subtitle": "成本项来自项目已保存参数",
            "highlight": None,
        },
        "items": [
            {
                "id": field_name,
                "entity_type": "cost_item",
                "title": label,
                "value": str(value),
                "context": {"field": field_name},
            }
            for field_name, label, value in present_costs
        ],
        "options": {
            "missing_fields": missing_fields,
            "total_cost": (
                sum(value for _, _, value in present_costs)
                if not missing_fields
                else None
            ),
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "成本参数待补充",
            "description": "缺失成本不会按零计算",
            "action": {
                "label": "补充成本",
                "target_screen": "S16",
            },
        } if missing_fields else None,
    }


def _breakeven_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
    )
    missing_fields = [
        field_name
        for field_name in cost_fields
        if getattr(project, field_name) is None
    ]
    if not project.avg_ticket_price:
        missing_fields.append("avg_ticket_price")
    total_cost = (
        sum(getattr(project, field_name) for field_name in cost_fields)
        if not missing_fields
        else None
    )
    breakeven_attendance = (
        (total_cost + project.avg_ticket_price - 1) // project.avg_ticket_price
        if total_cost is not None
        else None
    )
    return {
        "screen_id": "S31",
        "summary": {
            "title": f"{project.name}保本测算",
            "subtitle": "由真实成本和平均票价计算",
            "highlight": str(breakeven_attendance) if breakeven_attendance is not None else None,
        },
        "items": [{
            "id": "breakeven-attendance",
            "entity_type": "finance_metric",
            "title": "保本人数",
            "value": str(breakeven_attendance),
            "context": {"metric": "breakeven_attendance"},
        }] if breakeven_attendance is not None else [],
        "options": {
            "total_cost": total_cost,
            "avg_ticket_price": project.avg_ticket_price,
            "breakeven_attendance": breakeven_attendance,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "无法计算保本人数",
            "description": "成本或平均票价尚未补齐",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


def _funding_gap_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
    )
    missing_fields = [
        field_name
        for field_name in cost_fields
        if getattr(project, field_name) is None
    ]
    if project.available_funds is None:
        missing_fields.append("available_funds")
    total_cost = (
        sum(getattr(project, field_name) for field_name in cost_fields)
        if not any(field_name in missing_fields for field_name in cost_fields)
        else None
    )
    funding_gap = (
        max(total_cost - project.available_funds, 0)
        if total_cost is not None and project.available_funds is not None
        else None
    )
    return {
        "screen_id": "S33",
        "summary": {
            "title": f"{project.name}资金缺口",
            "subtitle": "由总成本减去可用资金计算",
            "highlight": str(funding_gap) if funding_gap is not None else None,
        },
        "items": [{
            "id": "funding-gap",
            "entity_type": "finance_metric",
            "title": "资金缺口",
            "value": str(funding_gap),
            "context": {"metric": "funding_gap"},
        }] if funding_gap is not None else [],
        "options": {
            "total_cost": total_cost,
            "available_funds": project.available_funds,
            "funding_gap": funding_gap,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "无法计算资金缺口",
            "description": "成本或可用资金尚未补齐",
            "action": {
                "label": "补充参数",
                "target_screen": "S15",
            },
        } if missing_fields else None,
    }


def _finance_sensitivity_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
    )
    rate_fields = {
        "conservative": "conservative_occupancy_rate",
        "neutral": "neutral_occupancy_rate",
        "optimistic": "optimistic_occupancy_rate",
    }
    missing_fields = [
        field_name
        for field_name in cost_fields
        if getattr(project, field_name) is None
    ]
    if project.venue_capacity is None:
        missing_fields.append("venue_capacity")
    for field_name in rate_fields.values():
        if getattr(project, field_name) is None:
            missing_fields.append(field_name)

    ticket_tiers = project.ticket_tiers or []
    valid_tiers = [
        tier
        for tier in ticket_tiers
        if tier.get("price") is not None and tier.get("share") is not None
    ]
    total_share = sum(tier["share"] for tier in valid_tiers)
    if not valid_tiers or total_share <= 0 or len(valid_tiers) != len(ticket_tiers):
        missing_fields.append("ticket_tiers")

    weighted_ticket_price = (
        sum(tier["price"] * tier["share"] for tier in valid_tiers) / total_share
        if "ticket_tiers" not in missing_fields
        else None
    )
    total_cost = (
        sum(getattr(project, field_name) for field_name in cost_fields)
        if not any(field_name in missing_fields for field_name in cost_fields)
        else None
    )
    scenarios = {}
    if not missing_fields:
        for scenario_name, field_name in rate_fields.items():
            occupancy_rate = getattr(project, field_name)
            attendance = round(project.venue_capacity * occupancy_rate / 100)
            revenue = round(attendance * weighted_ticket_price)
            scenarios[scenario_name] = {
                "occupancy_rate": occupancy_rate,
                "attendance": attendance,
                "revenue": revenue,
                "profit": revenue - total_cost,
            }
    return {
        "screen_id": "S32",
        "summary": {
            "title": f"{project.name}敏感性分析",
            "subtitle": "仅调整上座率，票价和成本保持不变",
            "highlight": None,
        },
        "items": [
            {
                "id": f"sensitivity-{scenario_name}",
                "entity_type": "finance_scenario",
                "title": scenario_name,
                "value": str(scenario["profit"]),
                "context": {"scenario": scenario_name, **scenario},
            }
            for scenario_name, scenario in scenarios.items()
        ],
        "options": {
            "venue_capacity": project.venue_capacity,
            "weighted_ticket_price": weighted_ticket_price,
            "total_cost": total_cost,
            "scenarios": scenarios,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "无法生成敏感性分析",
            "description": "容量、票档、成本或上座率尚未补齐",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


def _empty_state(title: str, description: str, target_screen: Optional[str] = None) -> dict:
    return {
        "title": title,
        "description": description,
        "action": (
            {"label": "去处理", "target_screen": target_screen}
            if target_screen
            else None
        ),
    }


def _user_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    return {
        user.id: user.name
        for user in db.query(User).filter(User.id.in_(user_ids)).all()
    }


def _serialize_decision(decision: Decision, names: dict[int, str]) -> dict:
    return {
        "id": decision.id,
        "project_id": decision.project_id,
        "version_id": decision.version_id,
        "decision_type": decision.decision_type,
        "conditions": decision.conditions,
        "decided_by": decision.decided_by,
        "decided_by_name": names.get(decision.decided_by),
        "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
    }


def _decision_bundle(db: Session, project: Project) -> dict:
    current_version = _get_current_version(db, project)
    decisions = db.query(Decision).filter(
        Decision.project_id == project.id,
    ).order_by(Decision.id.desc()).all()
    risks = db.query(Risk).filter(Risk.project_id == project.id).all()
    gates = db.query(Gate).filter(Gate.project_id == project.id).all()
    names = _user_names(
        db,
        {decision.decided_by for decision in decisions if decision.decided_by},
    )
    return {
        "current_version": current_version,
        "decisions": decisions,
        "risks": risks,
        "gates": gates,
        "user_names": names,
    }


def _judgement_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    project = _get_project(db, context)
    bundle = _decision_bundle(db, project)
    latest_decision = bundle["decisions"][0] if bundle["decisions"] else None
    open_risks = [risk for risk in bundle["risks"] if risk.status == "open"]
    blocked_gates = [
        gate for gate in bundle["gates"]
        if gate.status in {"blocked", "pending"}
    ]
    items = [
        {
            "id": f"risk-{risk.id}",
            "entity_type": "risk",
            "title": risk.title,
            "description": risk.mitigation or None,
            "status": risk.status,
            "context": {"project_id": project.id, "risk_id": risk.id, "level": risk.level},
        }
        for risk in open_risks
    ] + [
        {
            "id": f"gate-{gate.id}",
            "entity_type": "gate",
            "title": gate.name,
            "description": gate.required_evidence or None,
            "status": gate.status,
            "context": {"project_id": project.id, "gate_id": gate.id},
        }
        for gate in blocked_gates
    ]
    if latest_decision:
        items.append({
            "id": f"decision-{latest_decision.id}",
            "entity_type": "decision",
            "title": latest_decision.decision_type,
            "description": latest_decision.conditions or None,
            "status": latest_decision.decision_type,
            "context": {
                "project_id": project.id,
                "version_id": latest_decision.version_id,
                "decision_id": latest_decision.id,
            },
        })
    current_version = bundle["current_version"]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'判断说明' if screen_id == 'S35' else '判断摘要'}",
            "subtitle": "基于当前版本、风险、门禁和最近决策",
            "highlight": latest_decision.decision_type if latest_decision else None,
        },
        "items": items,
        "options": {
            "current_version": serialize_version(current_version) if current_version else None,
            "latest_decision": (
                _serialize_decision(latest_decision, bundle["user_names"])
                if latest_decision
                else None
            ),
            "open_risk_count": len(open_risks),
            "blocked_gate_count": len(blocked_gates),
        },
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无判断依据", "当前项目尚无版本、风险、门禁或决策记录")
            if not current_version and not items
            else None
        ),
    }


def _assumption_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    assumptions = db.query(Assumption).filter(
        Assumption.project_id == project.id,
    ).order_by(Assumption.id.desc()).all()
    return {
        "screen_id": "S36",
        "summary": {
            "title": f"{project.name}假设",
            "subtitle": "展示已保存的业务假设和置信度",
            "highlight": str(len(assumptions)),
        },
        "items": [{
            "id": f"assumption-{item.id}",
            "entity_type": "assumption",
            "title": item.title,
            "description": item.content or None,
            "status": item.status,
            "value": str(item.confidence),
            "context": {
                "project_id": project.id,
                "assumption_id": item.id,
                "confidence": item.confidence,
            },
        } for item in assumptions],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无假设", "项目尚未录入业务假设")
            if not assumptions else None
        ),
    }


def _fact_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    facts = db.query(Fact).filter(
        Fact.project_id == project.id,
    ).order_by(Fact.id.desc()).all()
    verifier_names = _user_names(
        db,
        {fact.verified_by for fact in facts if fact.verified_by},
    )
    return {
        "screen_id": "S37",
        "summary": {
            "title": f"{project.name}事实",
            "subtitle": "展示事实内容和人工核验状态",
            "highlight": str(len(facts)),
        },
        "items": [{
            "id": f"fact-{fact.id}",
            "entity_type": "fact",
            "title": fact.title,
            "description": fact.content or None,
            "status": fact.status,
            "context": {
                "project_id": project.id,
                "fact_id": fact.id,
                "source": fact.source,
                "verified_by": fact.verified_by,
                "verified_by_name": verifier_names.get(fact.verified_by),
                "verified_comment": fact.verified_comment,
            },
        } for fact in facts],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无事实", "项目尚未录入事实") if not facts else None,
    }


def _evidence_screen(
    db: Session,
    context: ScreenRequestContext,
    *,
    conflicts_only: bool = False,
) -> dict:
    project = _get_project(db, context)
    evidences = db.query(Evidence).filter(
        Evidence.project_id == project.id,
    ).order_by(Evidence.id.desc()).all()
    if conflicts_only:
        evidences = [
            evidence for evidence in evidences
            if evidence.status == "conflict"
            or bool((evidence.meta or {}).get("conflict_reason"))
        ]
    screen_id = "S39" if conflicts_only else "S38"
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'依据冲突' if conflicts_only else '依据资料'}",
            "subtitle": "仅展示已保存且可追溯的资料",
            "highlight": str(len(evidences)),
        },
        "items": [{
            "id": f"evidence-{evidence.id}",
            "entity_type": "evidence_conflict" if conflicts_only else "evidence",
            "title": evidence.name,
            "description": evidence.source or None,
            "status": evidence.status,
            "context": {
                "project_id": project.id,
                "evidence_id": evidence.id,
                "fact_id": evidence.fact_id,
                "file_url": evidence.file_url,
                "evidence_type": evidence.evidence_type,
                "metadata": evidence.meta or {},
                "conflict_reason": (evidence.meta or {}).get("conflict_reason"),
            },
        } for evidence in evidences],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state(
                "暂无依据冲突" if conflicts_only else "暂无依据资料",
                "当前没有已记录的冲突" if conflicts_only else "上传资料后可在这里查看",
                "S41" if not conflicts_only else None,
            )
            if not evidences else None
        ),
    }


def _evidence_gap_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    gates = db.query(Gate).filter(
        Gate.project_id == project.id,
        Gate.status.in_(("pending", "blocked")),
    ).order_by(Gate.id.desc()).all()
    gaps = [gate for gate in gates if gate.required_evidence]
    return {
        "screen_id": "S40",
        "summary": {
            "title": f"{project.name}依据缺口",
            "subtitle": "来自待处理门禁明确要求的资料",
            "highlight": str(len(gaps)),
        },
        "items": [{
            "id": f"evidence-gap-{gate.id}",
            "entity_type": "evidence_gap",
            "title": gate.required_evidence,
            "description": gate.name,
            "status": gate.status,
            "context": {"project_id": project.id, "gate_id": gate.id},
        } for gate in gaps],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无明确资料缺口", "待处理门禁未要求补充资料")
            if not gaps else None
        ),
    }


def _evidence_upload_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    facts = db.query(Fact).filter(
        Fact.project_id == project.id,
    ).order_by(Fact.id.desc()).all()
    return {
        "screen_id": "S41",
        "summary": {
            "title": f"{project.name}上传依据",
            "subtitle": "可将资料关联到已保存事实",
            "highlight": None,
        },
        "items": [],
        "options": {
            "project": {"id": project.id, "name": project.name},
            "facts": [
                {"id": fact.id, "title": fact.title, "status": fact.status}
                for fact in facts
            ],
            "evidence_types": ["document", "spreadsheet", "image"],
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _document_parse_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    jobs = db.query(DocumentParseJob).filter(
        DocumentParseJob.tenant_id == context.tenant_id,
        DocumentParseJob.project_id == project.id,
    ).order_by(DocumentParseJob.id.desc()).all()
    return {
        "screen_id": "S42",
        "summary": {
            "title": f"{project.name}解析结果",
            "subtitle": "展示真实文档解析任务和候选结果",
            "highlight": str(len(jobs)),
        },
        "items": [{
            "id": f"parse-job-{job.id}",
            "entity_type": "document_parse_job",
            "title": job.file_name,
            "description": job.purpose or None,
            "status": job.status,
            "context": {
                "project_id": project.id,
                "evidence_id": job.evidence_id,
                "parse_job_id": job.id,
                "file_kind": job.file_kind,
                "parse_scope": job.parse_scope,
                "result": job.result or {},
            },
        } for job in jobs],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无解析任务", "上传并解析资料后可在这里复核", "S41")
            if not jobs else None
        ),
    }


def _risk_screen(db: Session, context: ScreenRequestContext, screen_id: str) -> dict:
    project = _get_project(db, context)
    risks = db.query(Risk).filter(Risk.project_id == project.id).all()
    level_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"open": 0, "monitoring": 1, "closed": 2}
    risks.sort(key=lambda item: (
        level_order.get(item.level, 99),
        status_order.get(item.status, 99),
        -item.id,
    ))
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'风险详情' if screen_id == 'S44' else '风险'}",
            "subtitle": "按严重级别和处理状态排序",
            "highlight": str(len([risk for risk in risks if risk.status == "open"])),
        },
        "items": [{
            "id": f"risk-{risk.id}",
            "entity_type": "risk",
            "title": risk.title,
            "description": risk.mitigation or None,
            "status": risk.status,
            "value": risk.level,
            "context": {
                "project_id": project.id,
                "risk_id": risk.id,
                "level": risk.level,
                "mitigation": risk.mitigation,
            },
        } for risk in risks],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无风险", "当前项目没有风险记录") if not risks else None,
    }


def _gate_screen(db: Session, context: ScreenRequestContext, screen_id: str) -> dict:
    project = _get_project(db, context)
    gates = db.query(Gate).filter(Gate.project_id == project.id).all()
    status_order = {"blocked": 0, "pending": 1, "passed": 2, "closed": 3}
    gates.sort(key=lambda item: (status_order.get(item.status, 99), -item.id))
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'门禁详情' if screen_id == 'S46' else '门禁'}",
            "subtitle": "按阻塞和待处理状态优先展示",
            "highlight": str(len([gate for gate in gates if gate.status in {"blocked", "pending"}])),
        },
        "items": [{
            "id": f"gate-{gate.id}",
            "entity_type": "gate",
            "title": gate.name,
            "description": gate.required_evidence or None,
            "status": gate.status,
            "context": {
                "project_id": project.id,
                "gate_id": gate.id,
                "required_evidence": gate.required_evidence,
                "owner_group": gate.owner_group,
            },
        } for gate in gates],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无门禁", "当前项目没有门禁记录") if not gates else None,
    }


def _decision_confirm_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    version = db.query(ProjectVersion).filter(
        ProjectVersion.id == context.version_id,
        ProjectVersion.project_id == project.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Project version not found")
    decision = db.query(Decision).filter(
        Decision.project_id == project.id,
        Decision.version_id == version.id,
    ).order_by(Decision.id.desc()).first()
    names = _user_names(db, {decision.decided_by} if decision and decision.decided_by else set())
    return {
        "screen_id": "S47",
        "summary": {
            "title": f"{project.name}确认决策",
            "subtitle": f"基于版本 {version.version_no}",
            "highlight": decision.decision_type if decision else None,
        },
        "items": [],
        "options": {
            "project": serialize_project(project),
            "version": serialize_version(version),
            "decision": _serialize_decision(decision, names) if decision else None,
            "decision_types": ["advance", "conditional_advance", "pause", "reject"],
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _decision_result_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    decisions = db.query(Decision).filter(
        Decision.project_id == project.id,
    ).order_by(Decision.id.desc()).all()
    names = _user_names(
        db,
        {decision.decided_by for decision in decisions if decision.decided_by},
    )
    items = [{
        "id": f"decision-{decision.id}",
        "entity_type": "decision",
        "title": decision.decision_type,
        "description": decision.conditions or None,
        "status": decision.decision_type,
        "context": {
            **_serialize_decision(decision, names),
            "decision_id": decision.id,
        },
    } for decision in decisions]
    return {
        "screen_id": "S48",
        "summary": {
            "title": f"{project.name}决策结果",
            "subtitle": "按决策时间倒序展示",
            "highlight": decisions[0].decision_type if decisions else None,
        },
        "items": items,
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无决策", "确认决策后可查看结果", "S47") if not items else None,
    }


def _version_compare_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    versions = db.query(ProjectVersion).filter(
        ProjectVersion.project_id == project.id,
    ).order_by(ProjectVersion.version_no.desc()).limit(2).all()
    if len(versions) < 2:
        return {
            "screen_id": "S49",
            "summary": {
                "title": f"{project.name}版本对比",
                "subtitle": "至少需要两个真实版本",
                "highlight": None,
            },
            "items": [],
            "options": {"versions": [serialize_version(version) for version in versions], "changes": {}},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无可对比版本", "保存新版本后可查看字段变化", "S12"),
        }
    current, previous = versions
    before = previous.input_snapshot or {}
    after = current.input_snapshot or {}
    changes = {
        key: {"from": before.get(key), "to": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }
    return {
        "screen_id": "S49",
        "summary": {
            "title": f"{project.name}版本对比",
            "subtitle": f"版本 {previous.version_no} 与版本 {current.version_no}",
            "highlight": str(len(changes)),
        },
        "items": [{
            "id": f"version-change-{key}",
            "entity_type": "version_change",
            "title": key,
            "description": f"{change['from']} -> {change['to']}",
            "context": {"field": key, **change},
        } for key, change in changes.items()],
        "options": {
            "versions": [serialize_version(previous), serialize_version(current)],
            "changes": changes,
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _report_preview_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    reports = db.query(Evidence).filter(
        Evidence.project_id == project.id,
        Evidence.evidence_type == "feasibility_report",
    ).order_by(Evidence.id.desc()).all()
    return {
        "screen_id": "S50",
        "summary": {
            "title": f"{project.name}报告",
            "subtitle": "展示已经生成并入库的报告文件",
            "highlight": str(len(reports)),
        },
        "items": [{
            "id": f"report-{report.id}",
            "entity_type": "report",
            "title": report.name,
            "description": report.source or None,
            "status": report.status,
            "context": {
                "project_id": project.id,
                "version_id": (report.meta or {}).get("version_id"),
                "evidence_id": report.id,
                "file_url": report.file_url,
                "metadata": report.meta or {},
            },
        } for report in reports],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无报告", "生成报告后可在这里预览") if not reports else None,
    }


def _is_active_share(share: ReportShare) -> bool:
    if not share.created_at:
        return False
    created_at = share.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(days=share.expires_in_days or 0) > datetime.now(timezone.utc)


def _report_share_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    shares = db.query(ReportShare).filter(
        ReportShare.project_id == project.id,
    ).order_by(ReportShare.id.desc()).all()
    active_shares = [share for share in shares if _is_active_share(share)]
    return {
        "screen_id": "S51",
        "summary": {
            "title": f"{project.name}报告分享",
            "subtitle": "仅展示尚未过期的分享记录",
            "highlight": str(len(active_shares)),
        },
        "items": [{
            "id": f"report-share-{share.id}",
            "entity_type": "report_share",
            "title": f"分享链接 {share.id}",
            "status": "active",
            "context": {
                "project_id": project.id,
                "version_id": share.version_id,
                "share_id": share.id,
                "token": share.token,
                "expires_in_days": share.expires_in_days,
                "share_url": f"/shared/reports/{share.token}",
            },
        } for share in active_shares],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无有效分享", "创建报告分享后可在这里管理")
            if not active_shares else None
        ),
    }


def _tenant_task_rows(db: Session, tenant_id: int):
    return db.query(Task, Project.name, User.name).join(
        Project,
        Task.project_id == Project.id,
    ).outerjoin(
        User,
        Task.assignee_id == User.id,
    ).filter(
        Project.tenant_id == tenant_id,
    ).order_by(Task.id.desc()).all()


def _task_item(task: Task, project_name: str, assignee_name: Optional[str]) -> dict:
    actionability = (
        ["accept", "reject", "block"]
        if task.status in {"pending", "in_progress"}
        else ["submit"] if task.status == "accepted"
        else []
    )
    return {
        "id": f"task-{task.id}",
        "entity_type": "task",
        "title": task.title,
        "description": task.description or None,
        "status": task.status,
        "context": {
            "task_id": task.id,
            "project_id": task.project_id,
            "project_name": project_name,
            "assignee_id": task.assignee_id,
            "assignee_name": assignee_name,
            "due_date": task.due_date,
            "result": task.result,
            "evidence_ids": task.evidence_ids or [],
            "evidence_count": len(task.evidence_ids or []),
            "rejection_reason": task.rejection_reason or "",
            "actionability": actionability,
            "evidence_required": task.status in {"accepted", "in_progress"},
            "due_label": task.due_date or "未设置期限",
            "owner_label": assignee_name or "待分配",
        },
    }


def _task_list_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    rows = _tenant_task_rows(db, context.tenant_id)
    if screen_id == "S56":
        rows = [
            row for row in rows
            if row[0].status not in {"submitted", "completed"}
        ]
    items = [_task_item(*row) for row in rows]
    selectable_task_ids = [
        task.id for task, _, _ in rows
        if task.status not in {"submitted", "completed"}
    ]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": "批量处理任务" if screen_id == "S56" else "任务列表",
            "subtitle": "任务来自当前客户空间",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {
            "selectable_task_ids": selectable_task_ids,
            "selected_task_ids": [],
        } if screen_id == "S56" else {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无可处理任务", "当前客户空间没有可处理任务")
            if not items else None
        ),
    }


def _task_detail_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    row = db.query(Task, Project.name, User.name).join(
        Project,
        Task.project_id == Project.id,
    ).outerjoin(
        User,
        Task.assignee_id == User.id,
    ).filter(
        Task.id == context.task_id,
        Project.tenant_id == context.tenant_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    task, project_name, assignee_name = row
    return {
        "screen_id": screen_id,
        "summary": {
            "title": task.title,
            "subtitle": project_name,
            "highlight": task.status,
        },
        "items": [_task_item(task, project_name, assignee_name)],
        "options": {
            "allowed_actions": (
                ["submit"] if screen_id == "S57" else ["block"]
            ),
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _analysis_item(job: ProjectAnalysisJob, project_name: str) -> dict:
    return {
        "id": f"analysis-job-{job.id}",
        "entity_type": "project_analysis_job",
        "title": job.purpose or project_name,
        "description": project_name,
        "status": job.status,
        "context": {
            "analysis_job_id": job.id,
            "project_id": job.project_id,
            "version_id": job.version_id,
            "parameters": job.parameters or {},
            "result": job.result or {},
            "error_message": job.error_message,
        },
    }


def _agent_dashboard_screen(db: Session, context: ScreenRequestContext) -> dict:
    rows = [
        row for row in _tenant_task_rows(db, context.tenant_id)
        if row[0].assignee_id == context.user_id
        and row[0].status not in {"submitted", "completed"}
    ]
    items = [_task_item(*row) for row in rows]
    projects = db.query(Project).filter(
        Project.tenant_id == context.tenant_id,
        Project.status != "archived",
    ).order_by(Project.id.desc()).all()
    top_task = items[0] if items else None
    return {
        "screen_id": "S52",
        "summary": {
            "title": "今日工作",
            "subtitle": "展示当前用户尚未完成的任务",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {
            "default_project_id": projects[0].id if projects else None,
            "available_projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "status": project.status,
                }
                for project in projects
            ],
            "work_briefing": {
                "today_change_count": len(items),
                "top_task": (
                    {
                        "task_id": top_task["context"]["task_id"],
                        "title": top_task["title"],
                        "status": top_task["status"],
                        "project_name": top_task["context"]["project_name"],
                    }
                    if top_task else None
                ),
                "active_project_count": len(projects),
            },
        },
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无待办", "当前没有分配给你的未完成任务") if not items else None,
    }


def _agent_plan_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    task_rows = [
        row for row in _tenant_task_rows(db, context.tenant_id)
        if row[0].project_id == project.id
    ]
    jobs = db.query(ProjectAnalysisJob).filter(
        ProjectAnalysisJob.tenant_id == context.tenant_id,
        ProjectAnalysisJob.project_id == project.id,
    ).order_by(ProjectAnalysisJob.id.desc()).all()
    work_plan = db.query(ProjectWorkPlan).filter(
        ProjectWorkPlan.tenant_id == context.tenant_id,
        ProjectWorkPlan.project_id == project.id,
        ProjectWorkPlan.status == "current",
    ).order_by(ProjectWorkPlan.version_no.desc()).first()
    open_alert_count = db.query(AlertEvent).filter(
        AlertEvent.tenant_id == context.tenant_id,
        AlertEvent.project_id == project.id,
        AlertEvent.status != "resolved",
    ).count()
    items = [_task_item(*row) for row in task_rows]
    items.extend(_analysis_item(job, project.name) for job in jobs)
    return {
        "screen_id": "S53",
        "summary": {
            "title": f"{project.name}执行计划",
            "subtitle": "由真实任务和分析任务组成",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {
            "project_work": (
                {
                    "plan_version": work_plan.version_no,
                    "open_alert_count": open_alert_count,
                    "recommendation": (
                        f"当前有 {open_alert_count} 项预警，等待负责人核验后再推进。"
                        if open_alert_count
                        else "当前计划无未关闭预警，仍需由负责人确认财务与审批门禁。"
                    ),
                    "human_gate": (
                        (work_plan.plan_json or {}).get("constraints", {}).get("human_gate")
                        or "财务与审批由负责人确认"
                    ),
                }
                if work_plan else None
            ),
        },
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无执行计划", "创建任务或分析任务后可在这里查看") if not items else None,
    }


def _agent_chat_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    job = db.query(ProjectAnalysisJob).filter(
        ProjectAnalysisJob.tenant_id == context.tenant_id,
        ProjectAnalysisJob.project_id == project.id,
    ).order_by(ProjectAnalysisJob.id.desc()).first()
    return {
        "screen_id": "S54",
        "summary": {
            "title": f"{project.name}项目助手",
            "subtitle": "上下文来自项目当前版本和最近分析",
            "highlight": job.status if job else None,
        },
        "items": [_analysis_item(job, project.name)] if job else [],
        "options": {
            "project": serialize_project(project),
            "current_version": (
                serialize_version(current_version)
                if current_version
                else None
            ),
            "latest_analysis": ({
                "id": job.id,
                "project_id": job.project_id,
                "version_id": job.version_id,
                "purpose": job.purpose,
                "status": job.status,
                "parameters": job.parameters or {},
                "result": job.result or {},
                "error_message": job.error_message,
            } if job else None),
        },
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无分析结果", "先运行项目分析后再开始对话") if not job else None,
    }


def _project_changes_screen(db: Session, context: ScreenRequestContext) -> dict:
    comparison = _version_compare_screen(db, context)
    return {
        **comparison,
        "screen_id": "S59",
        "summary": {
            **comparison["summary"],
            "title": f"{_get_project(db, context).name}关键变化",
            "subtitle": "仅展示相邻两个真实版本中发生变化的输入",
        },
        "empty_state": (
            _empty_state("暂无关键变化", "至少需要两个版本且关键输入发生变化")
            if not comparison["items"] else None
        ),
    }


def _tour_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    plans = db.query(TourPlan).filter(
        TourPlan.tenant_id == context.tenant_id,
    ).order_by(TourPlan.id.desc()).all()
    plan_ids = [plan.id for plan in plans]
    stops = (
        db.query(TourStop)
        .filter(TourStop.tour_plan_id.in_(plan_ids))
        .order_by(TourStop.sequence.asc(), TourStop.id.asc())
        .all()
        if plan_ids else []
    )
    stops_by_plan = {}
    for stop in stops:
        stops_by_plan.setdefault(stop.tour_plan_id, []).append(stop)

    if screen_id == "S61":
        items = [
            {
                "id": f"tour-plan-{plan.id}",
                "entity_type": "tour_plan",
                "title": plan.name,
                "description": f"{len(stops_by_plan.get(plan.id, []))} 个站点",
                "status": plan.status,
                "context": {"tour_plan_id": plan.id},
            }
            for plan in plans
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "巡演计划", "subtitle": "当前客户空间真实巡演", "highlight": str(len(plans))},
            "items": items,
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无巡演计划", "创建巡演计划后可查看路线") if not items else None,
        }

    selected_stops = stops
    if screen_id == "S63":
        project = _get_project(db, context)
        selected_stops = [stop for stop in stops if stop.project_id == project.id]
    items = [
        {
            "id": f"tour-stop-{stop.id}",
            "entity_type": "tour_stop",
            "title": stop.city,
            "description": stop.scheduled_at or None,
            "status": stop.status,
            "value": str(stop.sequence),
            "context": {
                "tour_plan_id": stop.tour_plan_id,
                "tour_stop_id": stop.id,
                "project_id": stop.project_id,
                "venue_id": stop.venue_id,
                "sequence": stop.sequence,
                "scheduled_at": stop.scheduled_at,
            },
        }
        for stop in selected_stops
    ]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": "巡演站点" if screen_id == "S63" else "巡演路线",
            "subtitle": "按站点顺序展示",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无巡演站点", "为巡演计划添加真实站点") if not items else None,
    }


def _actual_payload(actual: ProjectActual) -> dict:
    return {
        "id": actual.id,
        "project_id": actual.project_id,
        "actual_attendance": actual.actual_attendance,
        "actual_revenue": actual.actual_revenue,
        "actual_cost": actual.actual_cost,
        "actual_profit": actual.actual_profit,
        "status": actual.status,
        "notes": actual.notes,
        "settled_at": actual.settled_at.isoformat() if actual.settled_at else None,
    }


def _project_review_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    project = _get_project(db, context)
    if screen_id == "S64":
        snapshot = db.query(TicketingSnapshot).filter(
            TicketingSnapshot.project_id == project.id,
        ).order_by(
            TicketingSnapshot.captured_at.desc(),
            TicketingSnapshot.id.desc(),
        ).first()
        payload = ({
            "id": snapshot.id,
            "project_id": snapshot.project_id,
            "captured_at": snapshot.captured_at.isoformat(),
            "sold_count": snapshot.sold_count,
            "gross_revenue": snapshot.gross_revenue,
            "source": snapshot.source,
        } if snapshot else None)
        current_version = _get_current_version(db, project)
        finance_result = (
            current_version.finance_result
            if current_version and isinstance(current_version.finance_result, dict)
            else {}
        )
        forecast = (finance_result.get("scenarios") or {}).get("neutral")
        return {
            "screen_id": screen_id,
            "summary": {
                "title": f"{project.name}售票进度",
                "subtitle": "最新售票快照",
                "highlight": str(snapshot.sold_count) if snapshot else None,
            },
            "items": ([{
                "id": f"ticketing-snapshot-{snapshot.id}",
                "entity_type": "ticketing_snapshot",
                "title": f"已售 {snapshot.sold_count}",
                "description": snapshot.captured_at.isoformat(),
                "value": str(snapshot.gross_revenue) if snapshot.gross_revenue is not None else None,
                "context": payload,
            }] if snapshot else []),
            "options": {
                "snapshot": payload,
                "ticketing_loop": {
                    "forecast_attendance": forecast.get("attendance") if forecast else None,
                    "current_sold_count": snapshot.sold_count if snapshot else None,
                    "gross_revenue": snapshot.gross_revenue if snapshot else None,
                    "attendance_variance": (
                        snapshot.sold_count - forecast["attendance"]
                        if snapshot and forecast and forecast.get("attendance") is not None
                        else None
                    ),
                    "source": snapshot.source if snapshot else None,
                },
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无售票快照", "同步售票数据后可查看进度") if not snapshot else None,
        }

    actual = db.query(ProjectActual).filter(
        ProjectActual.project_id == project.id,
    ).first()
    actual_data = _actual_payload(actual) if actual else None
    if screen_id == "S65":
        items = [
            {
                "id": f"actual-{field_name}",
                "entity_type": "project_actual",
                "title": title,
                "value": str(value),
                "context": {"field": field_name, "project_actual_id": actual.id},
            }
            for field_name, title, value in (
                ("actual_attendance", "实际到场", actual.actual_attendance if actual else None),
                ("actual_revenue", "实际收入", actual.actual_revenue if actual else None),
                ("actual_cost", "实际成本", actual.actual_cost if actual else None),
                ("actual_profit", "实际利润", actual.actual_profit if actual else None),
            )
            if value is not None
        ]
        return {
            "screen_id": screen_id,
            "summary": {
                "title": f"{project.name}实际结果",
                "subtitle": actual.notes if actual else None,
                "highlight": actual.status if actual else None,
            },
            "items": items,
            "options": {
                "actual": actual_data,
                "actuals_summary": {
                    "actual_attendance": actual.actual_attendance if actual else None,
                    "actual_revenue": actual.actual_revenue if actual else None,
                    "actual_cost": actual.actual_cost if actual else None,
                    "actual_profit": actual.actual_profit if actual else None,
                    "status": actual.status if actual else None,
                    "notes": actual.notes if actual else None,
                },
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无实际结果", "完成结算后录入实际结果") if not actual else None,
        }

    current_version = _get_current_version(db, project)
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else {}
    )
    forecast = (finance_result.get("scenarios") or {}).get("neutral")
    variance = None
    if actual and forecast:
        actual_values = {
            "attendance": actual.actual_attendance,
            "revenue": actual.actual_revenue,
            "cost": actual.actual_cost,
            "profit": actual.actual_profit,
        }
        if all(actual_values[key] is not None and forecast.get(key) is not None for key in actual_values):
            variance = {
                key: actual_values[key] - forecast[key]
                for key in actual_values
            }
    items = [
        {
            "id": f"variance-{key}",
            "entity_type": "project_variance",
            "title": label,
            "value": str(value),
            "context": {
                "metric": key,
                "forecast": forecast[key],
                "actual": actual_data[f"actual_{key}"],
            },
        }
        for key, label in (
            ("attendance", "到场差异"),
            ("revenue", "收入差异"),
            ("cost", "成本差异"),
            ("profit", "利润差异"),
        )
        for value in ([variance[key]] if variance else [])
    ]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}项目复盘",
            "subtitle": "中性预测与实际结果对比",
            "highlight": actual.status if actual else None,
        },
        "items": items,
        "options": {
            "forecast": forecast,
            "actual": actual_data,
            "variance": variance,
            "calibration_loop": {
                "forecast_profit": forecast.get("profit") if forecast else None,
                "actual_profit": actual.actual_profit if actual else None,
                "forecast_attendance": forecast.get("attendance") if forecast else None,
                "actual_attendance": actual.actual_attendance if actual else None,
                "profit_variance": variance.get("profit") if variance else None,
                "notes": actual.notes if actual else None,
            },
        },
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无实际结果", "录入实际结果后才能计算预测差异")
            if not actual else
            _empty_state("暂无可比预测", "当前版本缺少中性情景测算")
            if not forecast else
            _empty_state("实际结果不完整", "补齐实际到场、收入、成本和利润")
            if not variance else None
        ),
    }


def _privacy_payload(consent: PrivacyConsent) -> dict:
    return {
        "id": consent.id,
        "scope": consent.scope,
        "granted": bool(consent.granted),
        "policy_version": consent.policy_version,
        "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
        "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
    }


def _auth_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S01":
        return {
            "screen_id": screen_id,
            "summary": {"title": "登录", "subtitle": "选择可用登录方式", "highlight": None},
            "items": [],
            "options": {"login_methods": ["wechat", "web"]},
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S02":
        rows = db.query(TenantMember, Tenant).join(
            Tenant,
            Tenant.id == TenantMember.tenant_id,
        ).filter(
            TenantMember.user_id == context.user_id,
            Tenant.status == "active",
        ).order_by(Tenant.id.asc()).all()
        items = [
            {
                "id": f"tenant-{tenant.id}",
                "entity_type": "tenant",
                "title": tenant.name,
                "status": tenant.status,
                "value": member.role,
                "context": {
                    "tenant_id": tenant.id,
                    "role": member.role,
                    "is_current": tenant.id == context.tenant_id,
                },
            }
            for member, tenant in rows
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "选择客户空间", "subtitle": "仅显示当前用户已加入的空间", "highlight": str(len(items))},
            "items": items,
            "options": {"current_tenant_id": context.tenant_id},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无可用空间", "请联系管理员添加成员关系") if not items else None,
        }

    consents = db.query(PrivacyConsent).filter(
        PrivacyConsent.tenant_id == context.tenant_id,
        PrivacyConsent.user_id == context.user_id,
    ).order_by(PrivacyConsent.scope.asc()).all()
    items = [
        {
            "id": f"privacy-consent-{consent.id}",
            "entity_type": "privacy_consent",
            "title": consent.scope,
            "status": "granted" if consent.granted else "revoked",
            "value": consent.policy_version or None,
            "context": _privacy_payload(consent),
        }
        for consent in consents
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": "隐私授权", "subtitle": "当前用户已保存的授权范围", "highlight": str(sum(bool(item.granted) for item in consents))},
        "items": items,
        "options": {"privacy_consents": [_privacy_payload(consent) for consent in consents]},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无隐私授权记录", "授权后将在这里展示") if not items else None,
    }


def _account_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S67":
        user = db.query(User).filter(User.id == context.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        unread_count = db.query(Notification).filter(
            Notification.tenant_id == context.tenant_id,
            Notification.user_id == context.user_id,
            Notification.status == "unread",
        ).count()
        return {
            "screen_id": screen_id,
            "summary": {"title": user.name, "subtitle": user.account or user.phone or None, "highlight": str(unread_count)},
            "items": [],
            "options": {"user": serialize_user(user), "unread_notification_count": unread_count},
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S68":
        rows = db.query(TenantMember, User).join(
            User,
            User.id == TenantMember.user_id,
        ).filter(
            TenantMember.tenant_id == context.tenant_id,
        ).order_by(User.name.asc(), User.id.asc()).all()
        items = [
            {
                "id": f"tenant-member-{member.id}",
                "entity_type": "tenant_member",
                "title": user.name,
                "description": user.account or user.phone or None,
                "status": user.status,
                "value": member.role,
                "context": {
                    "tenant_member_id": member.id,
                    "user_id": user.id,
                    "role": member.role,
                },
            }
            for member, user in rows
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "团队成员", "subtitle": "当前客户空间成员", "highlight": str(len(items))},
            "items": items,
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无团队成员", "邀请成员加入当前客户空间") if not items else None,
        }

    if screen_id == "S69":
        notifications = db.query(Notification).filter(
            Notification.tenant_id == context.tenant_id,
            Notification.user_id == context.user_id,
        ).order_by(Notification.created_at.desc(), Notification.id.desc()).all()
        items = [
            {
                "id": f"notification-{notification.id}",
                "entity_type": "notification",
                "title": notification.title,
                "description": notification.content or None,
                "status": notification.status,
                "value": notification.notification_type,
                "context": {
                    "notification_id": notification.id,
                    **(notification.context or {}),
                },
            }
            for notification in notifications
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "通知", "subtitle": "当前用户可见消息", "highlight": str(sum(item.status == "unread" for item in notifications))},
            "items": items,
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无通知", "新通知会显示在这里") if not items else None,
        }

    setting = db.query(UserSetting).filter(
        UserSetting.tenant_id == context.tenant_id,
        UserSetting.user_id == context.user_id,
    ).first()
    setting_payload = ({
        "id": setting.id,
        "locale": setting.locale,
        "theme": setting.theme,
        "notification_preferences": setting.notification_preferences or {},
    } if setting else None)
    if screen_id == "S70":
        return {
            "screen_id": screen_id,
            "summary": {"title": "用户设置", "subtitle": "当前客户空间内的个人设置", "highlight": setting.theme if setting else None},
            "items": [],
            "options": {"setting": setting_payload},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无用户设置", "保存设置后将在这里展示") if not setting else None,
        }

    if screen_id == "S71":
        consents = db.query(PrivacyConsent).filter(
            PrivacyConsent.tenant_id == context.tenant_id,
            PrivacyConsent.user_id == context.user_id,
        ).order_by(PrivacyConsent.scope.asc()).all()
        permissions = db.query(AgentPermission).filter(
            AgentPermission.tenant_id == context.tenant_id,
            AgentPermission.user_id == context.user_id,
        ).order_by(AgentPermission.capability.asc()).all()
        return {
            "screen_id": screen_id,
            "summary": {"title": "数据权限", "subtitle": "隐私授权与工作能力", "highlight": str(len(consents) + len(permissions))},
            "items": [],
            "options": {
                "privacy_consents": [_privacy_payload(consent) for consent in consents],
                "agent_permissions": [
                    {"capability": permission.capability, "enabled": bool(permission.enabled)}
                    for permission in permissions
                ],
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无数据权限记录", "完成授权后将在这里展示") if not consents and not permissions else None,
        }

    invitations = db.query(MemberInvitation).filter(
        MemberInvitation.tenant_id == context.tenant_id,
    ).order_by(MemberInvitation.created_at.desc(), MemberInvitation.id.desc()).all()
    items = [
        {
            "id": f"member-invitation-{invitation.id}",
            "entity_type": "member_invitation",
            "title": invitation.invitee,
            "status": invitation.status,
            "value": invitation.role,
            "context": {
                "invitation_id": invitation.id,
                "invited_by": invitation.invited_by,
                "expires_at": invitation.expires_at.isoformat(),
            },
        }
        for invitation in invitations
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": "成员邀请", "subtitle": "当前客户空间邀请记录", "highlight": str(len(items))},
        "items": items,
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无邀请记录", "邀请成员后可在这里查看状态") if not items else None,
    }


def _settings_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S82":
        wechat_configured = bool(
            os.environ.get("WECHAT_MINIAPP_APPID")
            and os.environ.get("WECHAT_MINIAPP_SECRET")
        )
        storage_provider = os.environ.get("OSS_PROVIDER", "local-placeholder").strip().lower()
        storage_configured = (
            bool(os.environ.get("MINIO_ACCESS_KEY") and os.environ.get("MINIO_SECRET_KEY"))
            if storage_provider in {"minio", "local-placeholder"} else
            bool(storage_provider)
        )
        connections = {
            "wechat": {"configured": wechat_configured},
            "object_storage": {
                "provider": storage_provider,
                "configured": storage_configured,
            },
        }
        return {
            "screen_id": screen_id,
            "summary": {"title": "服务连接", "subtitle": "仅展示配置状态", "highlight": str(sum(value["configured"] for value in connections.values()))},
            "items": [],
            "options": {"connections": connections},
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S83":
        setting = db.query(UserSetting).filter(
            UserSetting.tenant_id == context.tenant_id,
            UserSetting.user_id == context.user_id,
        ).first()
        preferences = setting.notification_preferences or {} if setting else {}
        return {
            "screen_id": screen_id,
            "summary": {"title": "通知偏好", "subtitle": "当前用户已保存设置", "highlight": str(len(preferences))},
            "items": [],
            "options": {"notification_preferences": preferences},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无通知偏好", "保存偏好后将在这里展示") if not setting else None,
        }

    consents = db.query(PrivacyConsent).filter(
        PrivacyConsent.tenant_id == context.tenant_id,
        PrivacyConsent.user_id == context.user_id,
    ).order_by(PrivacyConsent.scope.asc()).all()
    items = [
        {
            "id": f"privacy-record-{consent.id}",
            "entity_type": "privacy_consent",
            "title": consent.scope,
            "status": "granted" if consent.granted else "revoked",
            "value": consent.policy_version or None,
            "context": _privacy_payload(consent),
        }
        for consent in consents
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": "隐私记录", "subtitle": "当前用户授权历史", "highlight": str(len(items))},
        "items": items,
        "options": {"privacy_consents": [_privacy_payload(consent) for consent in consents]},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无隐私记录", "授权或撤回后将在这里展示") if not items else None,
    }


def _agent_permissions_screen(db: Session, context: ScreenRequestContext) -> dict:
    permissions = db.query(AgentPermission).filter(
        AgentPermission.tenant_id == context.tenant_id,
        AgentPermission.user_id == context.user_id,
    ).order_by(AgentPermission.capability.asc()).all()
    return {
        "screen_id": "S60",
        "summary": {
            "title": "工作权限",
            "subtitle": "当前用户已保存的工作授权",
            "highlight": str(sum(bool(permission.enabled) for permission in permissions)),
        },
        "items": [
            {
                "id": f"agent-permission-{permission.id}",
                "entity_type": "agent_permission",
                "title": permission.capability,
                "status": "enabled" if permission.enabled else "disabled",
                "context": {
                    "permission_id": permission.id,
                    "capability": permission.capability,
                    "enabled": bool(permission.enabled),
                },
            }
            for permission in permissions
        ],
        "options": {
            "permissions": [
                {"capability": permission.capability, "enabled": bool(permission.enabled)}
                for permission in permissions
            ],
        },
        "context": _screen_context(context),
        "empty_state": _empty_state(
            "暂无工作权限配置",
            "配置独立工作权限后将在这里展示",
        ) if not permissions else None,
    }


def _state_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S73":
        project_list = _project_list_screen(db, context)
        return {
            **project_list,
            "screen_id": screen_id,
            "summary": {
                "title": "项目状态",
                "subtitle": "当前客户空间项目",
                "highlight": project_list["summary"]["highlight"],
            },
            "empty_state": (
                _empty_state("暂无项目", "创建项目后可开始业务判断", "S13")
                if not project_list["items"] else None
            ),
        }

    if screen_id == "S74":
        project = _get_project(db, context)
        analysis_job = db.query(ProjectAnalysisJob).filter(
            ProjectAnalysisJob.tenant_id == context.tenant_id,
            ProjectAnalysisJob.project_id == project.id,
        ).order_by(ProjectAnalysisJob.created_at.desc(), ProjectAnalysisJob.id.desc()).first()
        job_payload = ({
            "id": analysis_job.id,
            "version_id": analysis_job.version_id,
            "purpose": analysis_job.purpose,
            "status": analysis_job.status,
            "error_message": analysis_job.error_message,
        } if analysis_job else None)
        return {
            "screen_id": screen_id,
            "summary": {
                "title": f"{project.name}分析进度",
                "subtitle": "读取最近一次真实分析任务",
                "highlight": analysis_job.status if analysis_job else None,
            },
            "items": [],
            "options": {
                "project": serialize_project(project),
                "analysis_job": job_payload,
                "recovery_target": "S11",
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无分析任务", "发起分析后可查看处理进度", "S11") if not analysis_job else None,
        }

    if screen_id == "S78":
        project = _get_project(db, context)
        requested_version = db.query(ProjectVersion).filter(
            ProjectVersion.id == context.version_id,
            ProjectVersion.project_id == project.id,
        ).first()
        if not requested_version:
            raise HTTPException(status_code=404, detail="Project version not found")
        return {
            "screen_id": screen_id,
            "summary": {
                "title": "项目版本已变化",
                "subtitle": project.name,
                "highlight": str(project.current_version_id) if project.current_version_id else None,
            },
            "items": [],
            "options": {
                "requested_version_id": requested_version.id,
                "current_version_id": project.current_version_id,
                "recovery_target": "S11",
            },
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S80":
        project = _get_project(db, context)
        return {
            "screen_id": screen_id,
            "summary": {
                "title": "确认归档项目",
                "subtitle": project.name,
                "highlight": project.status,
            },
            "items": [],
            "options": {
                "project": serialize_project(project),
                "recovery_target": "S11",
            },
            "context": _screen_context(context),
            "empty_state": None,
        }

    state_metadata = {
        "S75": ("网络请求失败", "检查网络后重试", "retry"),
        "S76": ("上下文不可用", "返回项目列表重新选择", "S10"),
        "S77": ("无访问权限", "返回可访问的项目列表", "S10"),
        "S79": ("输入校验失败", "返回上一页修正输入", "back"),
        "S81": ("登录状态已失效", "重新登录后继续", "S01"),
    }
    title, subtitle, recovery_target = state_metadata[screen_id]
    return {
        "screen_id": screen_id,
        "summary": {"title": title, "subtitle": subtitle, "highlight": None},
        "items": [],
        "options": {"recovery_target": recovery_target},
        "context": _screen_context(context),
        "empty_state": None,
    }


def build_miniapp_screen(
    screen_id: str,
    context: ScreenRequestContext,
    db: Optional[Session] = None,
) -> MiniappScreenData:
    registration = SCREEN_PROVIDERS.get(screen_id)
    if not registration:
        raise HTTPException(status_code=400, detail='Unknown miniapp screen')

    missing_context = [
        name
        for name in registration.required_context
        if getattr(context, name) is None
    ]
    if missing_context:
        raise HTTPException(
            status_code=422,
            detail=f"Missing screen context: {', '.join(sorted(missing_context))}",
        )

    if registration.provider_key in {"auth_login", "tenant_select", "privacy_scope"}:
        if db is None:
            raise RuntimeError('Database session is required for authentication screens')
        return MiniappScreenData.model_validate(_auth_screen(db, context, screen_id))
    if registration.provider_key in {
        "account_home",
        "team_members",
        "notifications",
        "user_settings",
        "data_permissions",
        "member_invite",
    }:
        if db is None:
            raise RuntimeError('Database session is required for account screens')
        return MiniappScreenData.model_validate(_account_screen(db, context, screen_id))
    if registration.provider_key in {
        "developer_connection",
        "notification_preferences",
        "privacy_records",
    }:
        if db is None:
            raise RuntimeError('Database session is required for settings screens')
        return MiniappScreenData.model_validate(_settings_screen(db, context, screen_id))
    if registration.domain == "state":
        if db is None:
            raise RuntimeError('Database session is required for state screens')
        return MiniappScreenData.model_validate(_state_screen(db, context, screen_id))
    if registration.provider_key in {
        "discovery_public",
        "case_list",
        "case_detail",
        "opportunity_detail",
        "discovery_search",
    }:
        if db is None:
            raise RuntimeError('Database session is required for discovery screens')
        return MiniappScreenData.model_validate(_discovery_screen(db, context, screen_id))
    if registration.provider_key == "discovery_dashboard":
        if db is None:
            raise RuntimeError('Database session is required for discovery screens')
        return MiniappScreenData.model_validate(_discovery_dashboard_screen(db, context))
    if registration.provider_key in {
        "artist_candidates",
        "artist_detail",
        "artist_compare",
        "city_compare",
        "schedule_options",
        "venue_options",
    }:
        if db is None:
            raise RuntimeError('Database session is required for portfolio screens')
        return MiniappScreenData.model_validate(_portfolio_screen(db, context, screen_id))
    if registration.provider_key in {"tour_overview", "tour_route", "tour_stop"}:
        if db is None:
            raise RuntimeError('Database session is required for tour screens')
        return MiniappScreenData.model_validate(_tour_screen(db, context, screen_id))
    if registration.provider_key in {"ticketing_progress", "project_actuals", "project_review"}:
        if db is None:
            raise RuntimeError('Database session is required for review screens')
        return MiniappScreenData.model_validate(_project_review_screen(db, context, screen_id))
    if registration.provider_key == 'project_list':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_list_screen(db, context))
    if registration.provider_key == 'project_detail':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_detail_screen(db, context))
    if registration.provider_key == 'project_versions':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_versions_screen(db, context))
    if registration.provider_key in PROJECT_CREATE_TITLES:
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_create_screen(
            db,
            context,
            registration.provider_key,
            screen_id,
        ))
    if registration.provider_key == 'project_draft':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_draft_screen(db, context))
    if registration.provider_key == 'finance_input':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_finance_input_screen(db, context))
    if registration.provider_key == 'ticket_tiers':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_ticket_tiers_screen(db, context))
    if registration.provider_key == 'cost_breakdown':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_cost_breakdown_screen(db, context))
    if registration.provider_key == 'finance_breakeven':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_breakeven_screen(db, context))
    if registration.provider_key == 'finance_funding_gap':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_funding_gap_screen(db, context))
    if registration.provider_key == 'finance_sensitivity':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_finance_sensitivity_screen(db, context))
    if registration.provider_key in FINANCE_SCENARIOS:
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_finance_scenario_screen(
            db,
            context,
            registration.provider_key,
        ))
    if registration.provider_key in {"judgement_summary", "judgement_explanation"}:
        if db is None:
            raise RuntimeError('Database session is required for decision screens')
        return MiniappScreenData.model_validate(_judgement_screen(db, context, screen_id))
    if registration.provider_key == "assumption_list":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_assumption_screen(db, context))
    if registration.provider_key == "fact_list":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_fact_screen(db, context))
    if registration.provider_key == "evidence_detail":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_screen(db, context))
    if registration.provider_key == "evidence_conflicts":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_screen(
            db,
            context,
            conflicts_only=True,
        ))
    if registration.provider_key == "evidence_gaps":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_gap_screen(db, context))
    if registration.provider_key == "evidence_upload_context":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_upload_screen(db, context))
    if registration.provider_key == "document_parse_review":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_document_parse_screen(db, context))
    if registration.provider_key in {"risk_list", "risk_detail"}:
        if db is None:
            raise RuntimeError('Database session is required for risk screens')
        return MiniappScreenData.model_validate(_risk_screen(db, context, screen_id))
    if registration.provider_key in {"gate_list", "gate_detail"}:
        if db is None:
            raise RuntimeError('Database session is required for gate screens')
        return MiniappScreenData.model_validate(_gate_screen(db, context, screen_id))
    if registration.provider_key == "decision_confirm":
        if db is None:
            raise RuntimeError('Database session is required for decision screens')
        return MiniappScreenData.model_validate(_decision_confirm_screen(db, context))
    if registration.provider_key == "decision_result":
        if db is None:
            raise RuntimeError('Database session is required for decision screens')
        return MiniappScreenData.model_validate(_decision_result_screen(db, context))
    if registration.provider_key == "version_compare":
        if db is None:
            raise RuntimeError('Database session is required for version screens')
        return MiniappScreenData.model_validate(_version_compare_screen(db, context))
    if registration.provider_key == "report_preview":
        if db is None:
            raise RuntimeError('Database session is required for report screens')
        return MiniappScreenData.model_validate(_report_preview_screen(db, context))
    if registration.provider_key == "report_share":
        if db is None:
            raise RuntimeError('Database session is required for report screens')
        return MiniappScreenData.model_validate(_report_share_screen(db, context))
    if registration.provider_key in {"task_list", "task_batch"}:
        if db is None:
            raise RuntimeError('Database session is required for task screens')
        return MiniappScreenData.model_validate(_task_list_screen(db, context, screen_id))
    if registration.provider_key in {"task_submit", "task_block"}:
        if db is None:
            raise RuntimeError('Database session is required for task screens')
        return MiniappScreenData.model_validate(_task_detail_screen(db, context, screen_id))
    if registration.provider_key == "agent_dashboard":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_dashboard_screen(db, context))
    if registration.provider_key == "agent_plan":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_plan_screen(db, context))
    if registration.provider_key == "agent_chat":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_chat_screen(db, context))
    if registration.provider_key == "project_changes":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_project_changes_screen(db, context))
    if registration.provider_key == "agent_permissions":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_permissions_screen(db, context))

    raise RuntimeError(
        f"Unhandled miniapp screen provider: {registration.provider_key}",
    )
