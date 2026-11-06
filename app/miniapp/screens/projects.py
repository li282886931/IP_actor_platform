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
