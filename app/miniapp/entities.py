import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import (
    AgentPermission,
    Artist,
    Assumption,
    Decision,
    DocumentParseJob,
    Evidence,
    Fact,
    Gate,
    MemberInvitation,
    Notification,
    PrivacyConsent,
    Project,
    ProjectActual,
    ProjectAnalysisJob,
    ProjectVersion,
    ReportShare,
    Risk,
    Show,
    Task,
    Tenant,
    TenantMember,
    TicketingSnapshot,
    TourPlan,
    TourStop,
    User,
    Venue,
)
from .schemas import MiniappEntityDetail


@dataclass(frozen=True)
class EntityRequestContext:
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None


@dataclass(frozen=True)
class EntityDetailConfig:
    model: type
    title_attr: Optional[str]
    status_attr: Optional[str] = "status"
    scope: str = "project"
    subtitle_attrs: tuple[str, ...] = ()
    media_attr: Optional[str] = None
    long_fields: dict[str, str] = field(default_factory=dict)
    excluded_fields: frozenset[str] = field(default_factory=frozenset)


ENTITY_DETAIL_CONFIGS = {
    "show": EntityDetailConfig(Show, "title", scope="public", subtitle_attrs=("artist_name", "city", "date"), media_attr="poster_url", long_fields={"description": "演出介绍"}),
    "artist": EntityDetailConfig(Artist, "name", status_attr=None, scope="authenticated", subtitle_attrs=("tags",), long_fields={"profile": "艺人画像"}),
    "project": EntityDetailConfig(Project, "name", scope="tenant", subtitle_attrs=("artist_name", "city", "schedule"), long_fields={"ticket_tiers": "票档设置"}),
    "project_version": EntityDetailConfig(ProjectVersion, None, scope="project", long_fields={"input_snapshot": "输入快照", "finance_result": "财务测算"}),
    "fact": EntityDetailConfig(Fact, "title", scope="project", long_fields={"content": "事实内容", "verified_comment": "核验说明"}),
    "assumption": EntityDetailConfig(Assumption, "title", scope="project", long_fields={"content": "假设内容"}),
    "evidence": EntityDetailConfig(Evidence, "name", scope="project", media_attr="file_url", long_fields={"meta": "资料元数据"}),
    "risk": EntityDetailConfig(Risk, "title", scope="project", long_fields={"mitigation": "应对措施"}),
    "gate": EntityDetailConfig(Gate, "name", scope="project", long_fields={"required_evidence": "所需依据"}),
    "decision": EntityDetailConfig(Decision, None, status_attr="decision_type", scope="project", long_fields={"conditions": "决策条件"}),
    "task": EntityDetailConfig(Task, "title", scope="project", long_fields={"description": "任务说明", "result": "提交结果", "rejection_reason": "拒绝原因", "evidence_ids": "关联依据"}),
    "document_parse_job": EntityDetailConfig(DocumentParseJob, "file_name", scope="tenant", subtitle_attrs=("purpose",), long_fields={"parameters": "解析参数", "result": "解析结果"}),
    "project_analysis_job": EntityDetailConfig(ProjectAnalysisJob, "purpose", scope="tenant", long_fields={"parameters": "分析参数", "result": "分析结果", "error_message": "错误信息"}),
    "report_share": EntityDetailConfig(ReportShare, None, status_attr=None, scope="project", excluded_fields=frozenset({"token"})),
    "venue": EntityDetailConfig(Venue, "name", status_attr="fire_safety_status", scope="tenant", subtitle_attrs=("city", "address"), long_fields={"transport_notes": "交通说明"}),
    "tour_plan": EntityDetailConfig(TourPlan, "name", scope="tenant"),
    "tour_stop": EntityDetailConfig(TourStop, "city", scope="tour", subtitle_attrs=("scheduled_at",)),
    "ticketing_snapshot": EntityDetailConfig(TicketingSnapshot, None, status_attr=None, scope="project"),
    "project_actual": EntityDetailConfig(ProjectActual, None, scope="project", long_fields={"notes": "结算说明"}),
    "tenant": EntityDetailConfig(Tenant, "name", scope="membership"),
    "tenant_member": EntityDetailConfig(TenantMember, None, status_attr=None, scope="tenant"),
    "notification": EntityDetailConfig(Notification, "title", scope="user", subtitle_attrs=("notification_type",), long_fields={"content": "通知内容", "context": "关联上下文"}),
    "member_invitation": EntityDetailConfig(MemberInvitation, "invitee", scope="tenant", excluded_fields=frozenset({"token"})),
    "agent_permission": EntityDetailConfig(AgentPermission, "capability", status_attr=None, scope="user"),
    "privacy_consent": EntityDetailConfig(PrivacyConsent, "scope", status_attr=None, scope="user"),
}


FIELD_LABELS = {
    "type": "项目类型",
    "artist_name": "艺人",
    "city": "城市",
    "date": "日期",
    "venue": "场馆",
    "price": "票价",
    "tags": "标签",
    "heat_score": "热度",
    "fan_count": "粉丝规模",
    "risk_level": "风险等级",
    "schedule": "计划时间",
    "expected_attendance": "预计人数",
    "avg_ticket_price": "平均票价",
    "artist_fee": "艺人费用",
    "venue_cost": "场馆费用",
    "marketing_cost": "宣发费用",
    "production_cost": "制作费用",
    "available_funds": "可用资金",
    "venue_capacity": "场馆容量",
    "version_no": "版本号",
    "confidence": "置信度",
    "source": "数据来源",
    "evidence_type": "资料类型",
    "level": "风险等级",
    "owner_group": "负责用户组",
    "due_date": "截止日期",
    "file_kind": "文件类型",
    "parse_scope": "解析范围",
    "expires_in_days": "有效天数",
    "address": "地址",
    "capacity": "容量",
    "quote": "报价",
    "sequence": "站点顺序",
    "scheduled_at": "计划时间",
    "sold_count": "已售数量",
    "gross_revenue": "票房收入",
    "actual_attendance": "实际到场",
    "actual_revenue": "实际收入",
    "actual_cost": "实际成本",
    "actual_profit": "实际利润",
    "role": "角色",
    "notification_type": "通知类型",
    "invitee": "邀请对象",
    "capability": "能力",
    "enabled": "是否启用",
    "scope": "授权范围",
    "granted": "是否授权",
    "policy_version": "政策版本",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "decided_at": "决定时间",
    "verified_at": "核验时间",
    "captured_at": "采集时间",
    "settled_at": "结算时间",
    "expires_at": "失效时间",
    "read_at": "阅读时间",
}


IDENTIFIER_FIELDS = {
    "id",
    "tenant_id",
    "user_id",
    "project_id",
    "version_id",
    "artist_id",
    "venue_id",
    "source_project_id",
    "fact_id",
    "evidence_id",
    "assignee_id",
    "verified_by",
    "uploaded_by",
    "created_by",
    "requested_by",
    "decided_by",
    "invited_by",
    "tour_plan_id",
}


def _field(key: str, label: str, value) -> Optional[dict]:
    if value is None or value == "":
        return None
    return {"key": key, "label": label, "value": str(value)}


def _display_value(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def _require_entity_scope(
    db: Session,
    entity,
    config: EntityDetailConfig,
    context: EntityRequestContext,
) -> None:
    if config.scope == "public":
        return
    if context.user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if config.scope == "authenticated":
        return
    if config.scope == "tenant":
        if getattr(entity, "tenant_id", None) != context.tenant_id:
            raise HTTPException(status_code=404, detail="Entity not found")
        return
    if config.scope == "project":
        project = db.query(Project).filter(
            Project.id == entity.project_id,
            Project.tenant_id == context.tenant_id,
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Entity not found")
        return
    if config.scope == "tour":
        plan = db.query(TourPlan).filter(
            TourPlan.id == entity.tour_plan_id,
            TourPlan.tenant_id == context.tenant_id,
        ).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Entity not found")
        return
    if config.scope == "user":
        if (
            getattr(entity, "tenant_id", None) != context.tenant_id
            or getattr(entity, "user_id", None) != context.user_id
        ):
            raise HTTPException(status_code=404, detail="Entity not found")
        return
    if config.scope == "membership":
        membership = db.query(TenantMember).filter(
            TenantMember.tenant_id == entity.id,
            TenantMember.user_id == context.user_id,
        ).first()
        if not membership:
            raise HTTPException(status_code=404, detail="Entity not found")


def _entity_title(db: Session, entity_type: str, entity, config: EntityDetailConfig) -> str:
    if entity_type == "project_version":
        return f"项目版本 V{entity.version_no}"
    if entity_type == "decision":
        return f"项目决策 #{entity.id}"
    if entity_type == "report_share":
        return f"报告分享 #{entity.id}"
    if entity_type == "ticketing_snapshot":
        return f"售票快照 #{entity.id}"
    if entity_type == "project_actual":
        return f"项目实际结果 #{entity.id}"
    if entity_type == "tenant_member":
        user = db.query(User).filter(User.id == entity.user_id).first()
        return user.name if user else f"团队成员 #{entity.id}"
    value = getattr(entity, config.title_attr, None) if config.title_attr else None
    return str(value or f"{entity_type} #{entity.id}")


def _related_items(db: Session, entity_type: str, entity) -> list[dict]:
    related = []
    project_id = getattr(entity, "project_id", None)
    if project_id and entity_type != "project":
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            related.append({
                "title": project.name,
                "subtitle": "关联项目",
                "detail_ref": {"entity_type": "project", "entity_id": project.id},
            })
    if entity_type == "project":
        if entity.artist_id:
            artist = db.query(Artist).filter(Artist.id == entity.artist_id).first()
            if artist:
                related.append({
                    "title": artist.name,
                    "subtitle": "关联艺人",
                    "detail_ref": {"entity_type": "artist", "entity_id": artist.id},
                })
        if entity.venue_id:
            venue = db.query(Venue).filter(Venue.id == entity.venue_id).first()
            if venue:
                related.append({
                    "title": venue.name,
                    "subtitle": "关联场馆",
                    "detail_ref": {"entity_type": "venue", "entity_id": venue.id},
                })
    if entity_type == "tour_stop":
        plan = db.query(TourPlan).filter(TourPlan.id == entity.tour_plan_id).first()
        if plan:
            related.insert(0, {
                "title": plan.name,
                "subtitle": "所属巡演",
                "detail_ref": {"entity_type": "tour_plan", "entity_id": plan.id},
            })
    return related


def _generic_detail(
    db: Session,
    entity_type: str,
    entity_id: int,
    context: EntityRequestContext,
) -> dict:
    config = ENTITY_DETAIL_CONFIGS[entity_type]
    entity = db.query(config.model).filter(config.model.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    _require_entity_scope(db, entity, config, context)

    fields = []
    sections = []
    skipped = (
        IDENTIFIER_FIELDS
        | config.excluded_fields
        | set(config.long_fields)
        | {config.title_attr, config.status_attr, config.media_attr}
    )
    for column in entity.__table__.columns:
        key = column.name
        value = getattr(entity, key)
        if key in skipped or value is None or value == "":
            continue
        fields.append({
            "key": key,
            "label": FIELD_LABELS.get(key, key.replace("_", " ")),
            "value": _display_value(value),
        })
    for key, title in config.long_fields.items():
        value = getattr(entity, key, None)
        if value is None or value == "" or value == {} or value == []:
            continue
        sections.append({
            "key": key,
            "title": title,
            "content": _display_value(value),
        })
    if entity_type == "tenant_member":
        user = db.query(User).filter(User.id == entity.user_id).first()
        if user:
            fields[:0] = [
                {"key": "account", "label": "账号", "value": user.account or ""},
                {"key": "phone", "label": "手机号", "value": user.phone or ""},
            ]
            fields = [item for item in fields if item["value"]]
    subtitle = " · ".join(
        str(getattr(entity, key))
        for key in config.subtitle_attrs
        if getattr(entity, key, None)
    ) or None
    status = getattr(entity, config.status_attr, None) if config.status_attr else None
    media_url = getattr(entity, config.media_attr, None) if config.media_attr else None
    return {
        "entity_type": entity_type,
        "entity_id": entity.id,
        "title": _entity_title(db, entity_type, entity, config),
        "subtitle": subtitle,
        "status": str(status) if status is not None else None,
        "media_url": str(media_url) if media_url else None,
        "fields": fields,
        "sections": sections,
        "related_items": _related_items(db, entity_type, entity),
        "actions": [],
    }


def _show_detail(db: Session, entity_id: int) -> dict:
    show = db.query(Show).filter(Show.id == entity_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    fields = [
        _field("artist_name", "艺人", show.artist_name),
        _field("city", "城市", show.city),
        _field("date", "日期", show.date),
        _field("venue", "场馆", show.venue),
        _field("price", "票价", show.price),
    ]
    related_items = []
    if show.artist_id:
        artist = db.query(Artist).filter(Artist.id == show.artist_id).first()
        if artist:
            related_items.append({
                "title": artist.name,
                "subtitle": "关联艺人",
                "detail_ref": {
                    "entity_type": "artist",
                    "entity_id": artist.id,
                },
            })
    return {
        "entity_type": "show",
        "entity_id": show.id,
        "title": show.title,
        "subtitle": " · ".join(filter(None, [show.artist_name, show.city, show.date])) or None,
        "status": show.status,
        "media_url": show.poster_url or None,
        "fields": [item for item in fields if item],
        "sections": ([{
            "key": "description",
            "title": "演出介绍",
            "content": show.description,
        }] if show.description else []),
        "related_items": related_items,
        "actions": [],
    }


def build_miniapp_entity_detail(
    entity_type: str,
    entity_id: int,
    context: EntityRequestContext,
    db: Session,
) -> MiniappEntityDetail:
    if entity_type == "show":
        return MiniappEntityDetail.model_validate(_show_detail(db, entity_id))
    if entity_type not in ENTITY_DETAIL_CONFIGS:
        raise HTTPException(status_code=400, detail="Unsupported entity detail type")
    return MiniappEntityDetail.model_validate(
        _generic_detail(db, entity_type, entity_id, context),
    )
