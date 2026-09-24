import hashlib
import math

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from . import database
from .models import (
    Assumption,
    Artist,
    DocumentParseJob,
    Evidence,
    ExternalDataJob,
    Fact,
    Gate,
    OSSUpload,
    Project,
    ProjectVersion,
    ProjectAnalysisJob,
    ReportShare,
    Risk,
    Show,
    Task,
    Tenant,
    TenantMember,
    User,
    UserGroup,
)
from .market_dossier import MARKET_DOSSIER


GROUPS = [
    {"code": "root", "name": "超级管理员", "permissions": ["user:manage"], "role": "B"},
    {"code": "B", "name": "主办方", "permissions": ["project:read", "project:write", "finance:calculate", "decision:write", "task:write"], "role": "B"},
    {"code": "Brand", "name": "品牌方", "permissions": ["project:read"], "role": "Brand"},
    {"code": "G", "name": "政府 / 文旅", "permissions": ["project:read"], "role": "G"},
    {"code": "C", "name": "观众端", "permissions": ["show:read"], "role": "C"},
]

DEFAULT_USERS = [
    {"account": "root", "name": "超级管理员", "group_code": "root"},
    {"account": "b_user", "name": "主办方用户", "group_code": "B"},
    {"account": "brand_user", "name": "品牌方用户", "group_code": "Brand"},
    {"account": "g_user", "name": "政府文旅用户", "group_code": "G"},
    {"account": "c_user", "name": "观众用户", "group_code": "C"},
]

DEFAULT_ARTISTS = [
    {"name": "周杰伦", "tags": "流行/华语", "heat_score": 95, "fan_count": "5000万", "risk_level": 0, "profile": {}},
    {"name": "五月天", "tags": "摇滚/台湾", "heat_score": 88, "fan_count": "2000万", "risk_level": 0, "profile": {}},
    {"name": "林俊杰", "tags": "流行/R&B", "heat_score": 82, "fan_count": "1500万", "risk_level": 2, "profile": {}},
    {
        "name": "蔡琴",
        "tags": "华语乐坛/丝绒歌后/成熟客群/资深女艺人市场",
        "heat_score": 78,
        "fan_count": "待补充",
        "risk_level": 2,
        "profile": {
            "age": "约68岁",
            "market_positioning": "华语乐坛“丝绒歌后”，纯音乐演唱会",
            "touring_box_office_reference": "2026《不要告别》巡回演唱会全国多城，票价399-1399元，杭州跨年场；宣布2027年底告别歌坛",
            "differentiation_with_zhao_yazhi": "纯歌手路线，无影视IP加持；客群偏成熟（40+）；无“时尚大秀”基因",
            "cooperation_recommendation": "票房稳定；可作“资深女艺人市场”对标；2026年部分场次有取消",
        },
    },
    {
        "name": "毛阿敏",
        "tags": "内地乐坛/大姐大/实力派唱将/拼盘演唱会",
        "heat_score": 70,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约62岁",
            "market_positioning": "内地乐坛大姐大，实力派唱将",
            "touring_box_office_reference": "近年以拼盘演唱会为主，个人巡演较少",
            "differentiation_with_zhao_yazhi": "唱功顶级但综艺曝光少，社交话题度低于赵雅芝",
            "cooperation_recommendation": "适合做嘉宾",
        },
    },
    {
        "name": "刘晓庆",
        "tags": "传奇影后/话剧女王/争议舆情/反面参照",
        "heat_score": 68,
        "fan_count": "待补充",
        "risk_level": 5,
        "profile": {
            "age": "约75岁",
            "market_positioning": "传奇影后+话剧女王，“永不认输”人设",
            "touring_box_office_reference": "话剧《风华绝代》巡演243场（2012-2026），3小时独角戏3万字台词，成都站谢幕跪地引轰动",
            "differentiation_with_zhao_yazhi": "形象争议大：2026年5月开封万岁山商演戴墨镜、躲太阳、被质疑“耍大牌/捞金”，全网负面舆情；75岁仍拍短剧（9天82集），商业感过重",
            "cooperation_recommendation": "与赵雅芝“优雅松弛”路线反差极大；品牌安全性低，不建议合作，仅作反面参照",
        },
    },
    {
        "name": "林青霞",
        "tags": "华语影坛传奇/东方不败/稀缺公开活动",
        "heat_score": 86,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约71岁",
            "market_positioning": "华语影坛传奇，东方不败",
            "touring_box_office_reference": "极少公开活动，无个人演唱会/大秀计划",
            "differentiation_with_zhao_yazhi": "国民度顶级但已半隐退，商业化可能性极低",
            "cooperation_recommendation": "仅作对标参考，不可替代",
        },
    },
    {
        "name": "汪明荃",
        "tags": "港圈大姐大/TVB/粤语区/怀旧市场",
        "heat_score": 76,
        "fan_count": "待补充",
        "risk_level": 3,
        "profile": {
            "age": "约78岁",
            "market_positioning": "港圈大姐大，TVB活化石",
            "touring_box_office_reference": "近年有演唱会，680元档开票十分钟抢光，VIP三天售完；观众含白发老人+年轻人举灯牌",
            "differentiation_with_zhao_yazhi": "粤语区影响力大，内地号召力弱于赵雅芝；走路需人扶，体力受限",
            "cooperation_recommendation": "地域局限明显，仅粤语区对标",
        },
    },
    {
        "name": "蔡国庆",
        "tags": "内地军旅歌手/祝福歌曲/拼盘演出/嘉宾",
        "heat_score": 63,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约57岁",
            "market_positioning": "内地军旅歌手，“一年有三百六十五个祝福”",
            "touring_box_office_reference": "拼盘演出为主",
            "differentiation_with_zhao_yazhi": "男艺人，客群偏中老年男性，与18-40岁女性定位不符",
            "cooperation_recommendation": "适合做嘉宾",
        },
    },
    {
        "name": "陈慧娴",
        "tags": "港乐天后/千千阙歌/粤港澳/怀旧市场",
        "heat_score": 74,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约65岁",
            "market_positioning": "港乐天后，《千千阙歌》",
            "touring_box_office_reference": "近年巡演，粤港澳号召力强",
            "differentiation_with_zhao_yazhi": "纯歌手路线，时尚属性弱",
            "cooperation_recommendation": "粤语区为主，可对标港乐怀旧市场",
        },
    },
    {
        "name": "潘迎紫",
        "tags": "一代女皇/冻龄女神/内地首秀/同台嘉宾",
        "heat_score": 72,
        "fan_count": "待补充",
        "risk_level": 2,
        "profile": {
            "age": "约76岁",
            "market_positioning": "“一代女皇”，冻龄女神鼻祖",
            "touring_box_office_reference": "2026年4月成都“走进原声带”内地首秀",
            "differentiation_with_zhao_yazhi": "与赵雅芝同属“冻龄”赛道，但影视IP以武则天为主，内地活动极少",
            "cooperation_recommendation": "可作为对打/同台嘉宾",
        },
    },
    {
        "name": "费玉清类",
        "tags": "已封麦/不可用/对标排除",
        "heat_score": 0,
        "fan_count": "不适用",
        "risk_level": 0,
        "profile": {
            "age": "—",
            "market_positioning": "已封麦",
            "touring_box_office_reference": "2019年已正式封麦退出演艺圈",
            "differentiation_with_zhao_yazhi": "不可用",
            "cooperation_recommendation": "—",
        },
    },
]


def hash_password(password: str):
    return hashlib.sha256(f"ruiyinchang:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str):
    return bool(password_hash) and hash_password(password) == password_hash


def group_role(group_code: str):
    for group in GROUPS:
        if group["code"] == group_code:
            return group["role"]
    return "C"


def can_manage_users(group_code: str):
    return group_code == "root"


def serialize_user(user: User):
    return {
        "id": user.id,
        "account": user.account,
        "name": user.name,
        "phone": user.phone,
        "group_code": user.group_code,
        "role": group_role(user.group_code),
        "status": user.status,
        "can_manage_users": can_manage_users(user.group_code),
    }


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


def project_input_snapshot(project):
    return {
        "name": project.name,
        "type": project.type,
        "artist_name": project.artist_name,
        "city": project.city,
        "venue": project.venue,
        "schedule": project.schedule,
        "expected_attendance": project.expected_attendance,
        "avg_ticket_price": project.avg_ticket_price,
        "artist_fee": project.artist_fee,
        "venue_cost": project.venue_cost,
        "marketing_cost": project.marketing_cost,
        "production_cost": project.production_cost,
    }


def calculate_finance_result(payload):
    attendance = payload.expected_attendance
    ticket_price = payload.avg_ticket_price
    costs = [
        payload.artist_fee,
        payload.venue_cost,
        payload.marketing_cost,
        payload.production_cost,
    ]
    missing = []
    if attendance is None:
        missing.append('expected_attendance')
    if ticket_price is None:
        missing.append('avg_ticket_price')
    for key, value in [
        ('artist_fee', payload.artist_fee),
        ('venue_cost', payload.venue_cost),
        ('marketing_cost', payload.marketing_cost),
        ('production_cost', payload.production_cost),
    ]:
        if value is None:
            missing.append(key)

    if missing:
        return {
            "formula_version": "finance-v1",
            "status": "pending_input",
            "missing_fields": missing,
            "scenarios": {},
            "breakeven_attendance": None,
            "total_cost": None,
        }

    total_cost = sum(costs)
    scenarios = {}
    for key, factor in [('conservative', 0.8), ('neutral', 1), ('optimistic', 1.2)]:
        scenario_attendance = round(attendance * factor)
        revenue = scenario_attendance * ticket_price
        scenarios[key] = {
            "attendance": scenario_attendance,
            "revenue": revenue,
            "cost": total_cost,
            "profit": revenue - total_cost,
        }

    return {
        "formula_version": "finance-v1",
        "status": "calculated",
        "missing_fields": [],
        "scenarios": scenarios,
        "breakeven_attendance": math.ceil(total_cost / ticket_price) if ticket_price else None,
        "total_cost": total_cost,
    }


def calculate_breakeven_result(project, payload):
    ticket_price = payload.avg_ticket_price or project.avg_ticket_price
    cost_values = {
        "artist_fee": payload.artist_fee if payload.artist_fee is not None else project.artist_fee,
        "venue_cost": payload.venue_cost if payload.venue_cost is not None else project.venue_cost,
        "marketing_cost": payload.marketing_cost if payload.marketing_cost is not None else project.marketing_cost,
        "production_cost": payload.production_cost if payload.production_cost is not None else project.production_cost,
    }
    missing = [key for key, value in cost_values.items() if value is None]
    if ticket_price is None:
        missing.append("avg_ticket_price")
    if missing:
        return {
            "formula_version": "breakeven-v1",
            "status": "pending_input",
            "missing_fields": missing,
            "total_cost": None,
            "avg_ticket_price": ticket_price,
            "breakeven_attendance": None,
            "target_profit_attendance": None,
        }
    total_cost = sum(cost_values.values())
    target_profit = payload.target_profit or 0
    return {
        "formula_version": "breakeven-v1",
        "status": "calculated",
        "missing_fields": [],
        "total_cost": total_cost,
        "avg_ticket_price": ticket_price,
        "breakeven_attendance": math.ceil(total_cost / ticket_price) if ticket_price else None,
        "target_profit_attendance": math.ceil((total_cost + target_profit) / ticket_price) if ticket_price else None,
    }


def serialize_project(project):
    return {
        "id": project.id,
        "tenant_id": project.tenant_id,
        "name": project.name,
        "type": project.type,
        "status": project.status,
        "artist_name": project.artist_name,
        "city": project.city,
        "venue": project.venue,
        "schedule": project.schedule,
        "expected_attendance": project.expected_attendance,
        "avg_ticket_price": project.avg_ticket_price,
        "artist_fee": project.artist_fee,
        "venue_cost": project.venue_cost,
        "marketing_cost": project.marketing_cost,
        "production_cost": project.production_cost,
        "current_version_id": project.current_version_id,
    }


def serialize_version(version):
    return {
        "id": version.id,
        "project_id": version.project_id,
        "version_no": version.version_no,
        "input_snapshot": version.input_snapshot,
        "finance_result": version.finance_result,
        "status": version.status,
    }


def serialize_task(task: Task):
    return {
        "id": task.id,
        "project_id": task.project_id,
        "assignee_id": task.assignee_id,
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date,
        "status": task.status,
        "result": task.result,
        "evidence_ids": task.evidence_ids or [],
    }


def serialize_fact(fact: Fact):
    return {
        "id": fact.id,
        "project_id": fact.project_id,
        "title": fact.title,
        "content": fact.content,
        "source": fact.source,
        "status": fact.status,
        "verified_by": fact.verified_by,
        "verified_comment": fact.verified_comment,
    }


def serialize_assumption(assumption: Assumption):
    return {
        "id": assumption.id,
        "project_id": assumption.project_id,
        "title": assumption.title,
        "content": assumption.content,
        "confidence": assumption.confidence,
        "status": assumption.status,
    }


def serialize_evidence(evidence: Evidence):
    return {
        "id": evidence.id,
        "project_id": evidence.project_id,
        "fact_id": evidence.fact_id,
        "name": evidence.name,
        "file_url": evidence.file_url,
        "evidence_type": evidence.evidence_type,
        "source": evidence.source,
        "status": evidence.status,
        "metadata": evidence.meta or {},
        "uploaded_by": evidence.uploaded_by,
    }


def serialize_oss_upload(upload: OSSUpload):
    return {
        "id": upload.id,
        "project_id": upload.project_id,
        "fact_id": upload.fact_id,
        "provider": upload.provider,
        "bucket": upload.bucket,
        "object_key": upload.object_key,
        "file_name": upload.file_name,
        "content_type": upload.content_type,
        "evidence_type": upload.evidence_type,
        "source": upload.source,
        "status": upload.status,
        "file_url": upload.file_url,
        "size": upload.size,
        "checksum": upload.checksum,
        "metadata": upload.meta or {},
    }


def serialize_document_parse_job(job: DocumentParseJob):
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "evidence_id": job.evidence_id,
        "file_name": job.file_name,
        "file_kind": job.file_kind,
        "parse_scope": job.parse_scope,
        "purpose": job.purpose,
        "status": job.status,
        "parameters": job.parameters or {},
        "result": job.result or {},
        "created_by": job.created_by,
    }


def serialize_project_analysis_job(job: ProjectAnalysisJob):
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "version_id": job.version_id,
        "purpose": job.purpose,
        "status": job.status,
        "parameters": job.parameters or {},
        "result": job.result or {},
        "error_message": job.error_message,
        "requested_by": job.requested_by,
    }


def serialize_gate(gate: Gate):
    return {
        "id": gate.id,
        "project_id": gate.project_id,
        "name": gate.name,
        "status": gate.status,
        "required_evidence": gate.required_evidence,
        "owner_group": gate.owner_group,
    }


def serialize_risk(risk: Risk):
    return {
        "id": risk.id,
        "project_id": risk.project_id,
        "title": risk.title,
        "level": risk.level,
        "mitigation": risk.mitigation,
        "status": risk.status,
    }


def serialize_report_share(share: ReportShare):
    return {
        "id": share.id,
        "project_id": share.project_id,
        "version_id": share.version_id,
        "token": share.token,
        "expires_in_days": share.expires_in_days,
        "share_url": f"/shared/reports/{share.token}",
    }


def serialize_external_data_job(job: ExternalDataJob):
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "source_type": job.source_type,
        "provider": job.provider,
        "query": job.query,
        "purpose": job.purpose,
        "status": job.status,
        "parameters": job.parameters or {},
        "result": job.result or {},
        "error_message": job.error_message,
        "requested_by": job.requested_by,
    }


def _truncate(value: str, length: int):
    text_value = str(value or '')
    return text_value if len(text_value) <= length else text_value[:length]


def _market_dossier_summary(row: dict):
    cells = row["cells"]
    return "；".join(
        f"{key}：{value}"
        for key, value in cells.items()
        if value not in (None, '')
    )


def _market_dossier_title(sheet: dict, row: dict):
    primary_header = sheet["headers"][0]
    primary = row["cells"].get(primary_header) or row["id"]
    return _truncate(f"{sheet['sheet']} - {primary}", 255)


def _market_dossier_source(row: dict):
    return _truncate(f"market-dossier:{row['id']}", 128)


def _upsert_market_dossier_evidence(db: Session, project: Project, sheet: dict, row: dict):
    file_url = f"market-dossier://zhao-yazhi/{row['id']}"
    evidence = db.query(Evidence).filter(
        Evidence.project_id == project.id,
        Evidence.file_url == file_url,
    ).first()
    if not evidence:
        evidence = Evidence(project_id=project.id, file_url=file_url)
        db.add(evidence)
    evidence.name = _market_dossier_title(sheet, row)
    evidence.evidence_type = 'market_dossier'
    evidence.source = _market_dossier_source(row)
    evidence.status = 'needs_review'
    evidence.meta = {
        "artist_name": "赵雅芝",
        "sheet": sheet["sheet"],
        "row_id": row["id"],
        "headers": sheet["headers"],
        "cells": row["cells"],
        "system_target": row["system_target"],
        "handling": row["handling"],
        "record_type": row["record_type"],
        "capture_plan": row["capture_plan"],
        "requires_human_verification": True,
    }
    return evidence


def _upsert_market_dossier_fact(db: Session, project: Project, sheet: dict, row: dict):
    source = _market_dossier_source(row)
    fact = db.query(Fact).filter(Fact.project_id == project.id, Fact.source == source).first()
    if not fact:
        fact = Fact(project_id=project.id, source=source)
        db.add(fact)
    fact.title = _market_dossier_title(sheet, row)
    fact.content = _market_dossier_summary(row)
    fact.status = 'pending'
    return fact


def _upsert_market_dossier_assumption(db: Session, project: Project, sheet: dict, row: dict):
    title = _market_dossier_title(sheet, row)
    assumption = db.query(Assumption).filter(
        Assumption.project_id == project.id,
        Assumption.title == title,
    ).first()
    if not assumption:
        assumption = Assumption(project_id=project.id, title=title)
        db.add(assumption)
    assumption.content = _market_dossier_summary(row)
    assumption.confidence = 70
    assumption.status = 'active'
    return assumption


def _upsert_market_dossier_risk(db: Session, project: Project, sheet: dict, row: dict):
    title = _market_dossier_title(sheet, row)
    risk = db.query(Risk).filter(Risk.project_id == project.id, Risk.title == title).first()
    if not risk:
        risk = Risk(project_id=project.id, title=title)
        db.add(risk)
    cells = row["cells"]
    risk.level = 'high' if any(keyword in _market_dossier_summary(row) for keyword in ['负面', '风险', '争议', '不可用']) else 'medium'
    risk.mitigation = cells.get('合作/对标建议') or cells.get('大秀可落地方案建议') or _market_dossier_summary(row)
    risk.status = 'open'
    return risk


def _upsert_market_dossier_external_job(db: Session, tenant: Tenant, user: User, project: Project, row: dict):
    plan = row["capture_plan"]
    job = db.query(ExternalDataJob).filter(
        ExternalDataJob.tenant_id == tenant.id,
        ExternalDataJob.project_id == project.id,
        ExternalDataJob.purpose == plan["purpose"],
        ExternalDataJob.query == plan["query"],
    ).first()
    if not job:
        job = ExternalDataJob(
            tenant_id=tenant.id,
            project_id=project.id,
            purpose=plan["purpose"],
            query=plan["query"],
            requested_by=user.id,
        )
        db.add(job)
    job.source_type = plan["source_type"]
    job.provider = plan["provider"]
    job.status = job.status or 'queued'
    job.parameters = {
        "artist_name": "赵雅芝",
        "dossier_row_id": row["id"],
        "system_target": row["system_target"],
        "requires_human_verification": True,
    }
    job.result = job.result or {}
    return job


def seed_market_dossier_data(db: Session):
    tenant, user = get_or_create_default_context(db)
    row_count = sum(len(sheet["rows"]) for sheet in MARKET_DOSSIER)

    artist = db.query(Artist).filter(Artist.name == "赵雅芝").first()
    if not artist:
        artist = Artist(name="赵雅芝")
        db.add(artist)
    artist.tags = "港星黄金时代/白素贞/东方赫本/冻龄女神/国风高定"
    artist.heat_score = 86
    artist.fan_count = "多平台待核验"
    artist.risk_level = 1
    artist.profile = {
        **(artist.profile or {}),
        "market_positioning": "经典影视 IP 与东方女性美学结合的大秀型艺人",
        "market_dossier": {
            "source": "赵雅芝市场分析 Excel 资料包",
            "sheet_count": len(MARKET_DOSSIER),
            "row_count": row_count,
            "sheets": MARKET_DOSSIER,
            "requires_human_verification": True,
        },
    }

    project = db.query(Project).filter(
        Project.tenant_id == tenant.id,
        Project.name == "赵雅芝大秀市场分析",
    ).first()
    if not project:
        project = Project(
            tenant_id=tenant.id,
            name="赵雅芝大秀市场分析",
            type='concert',
            created_by=user.id,
        )
        db.add(project)
        db.flush()
    project.artist_name = "赵雅芝"
    project.city = project.city or "待定"
    project.venue = project.venue or "待定"
    project.schedule = project.schedule or "待定"
    project.status = project.status or 'draft'

    for sheet in MARKET_DOSSIER:
        for row in sheet["rows"]:
            _upsert_market_dossier_evidence(db, project, sheet, row)
            if row["record_type"] == 'fact':
                _upsert_market_dossier_fact(db, project, sheet, row)
            elif row["record_type"] == 'assumption':
                _upsert_market_dossier_assumption(db, project, sheet, row)
            elif row["record_type"] == 'risk':
                _upsert_market_dossier_risk(db, project, sheet, row)
            if row["handling"] == 'external_capture':
                _upsert_market_dossier_external_job(db, tenant, user, project, row)

    db.commit()


def seed_initial_data(db: Session):
    artists_by_name = {artist.name: artist for artist in db.query(Artist).all()}
    for item in DEFAULT_ARTISTS:
        artist = artists_by_name.get(item["name"])
        if not artist:
            artist = Artist(name=item["name"])
            db.add(artist)
        artist.tags = item["tags"]
        artist.heat_score = item["heat_score"]
        artist.fan_count = item["fan_count"]
        artist.risk_level = item["risk_level"]
        artist.profile = item["profile"]
    db.commit()

    if db.query(Show).count() == 0:
        artists_by_name = {artist.name: artist for artist in db.query(Artist).all()}
        a1 = artists_by_name['周杰伦']
        a2 = artists_by_name['五月天']
        a3 = artists_by_name['林俊杰']
        s1 = Show(title='周杰伦·北京演唱会', artist_id=a1.id, artist_name=a1.name, city='北京', date='2026-09-10', venue='鸟巢', price='380-1280', status='on_sale', description='周杰伦个人巡回演唱会 — 北京站')
        s2 = Show(title='五月天·上海演唱会', artist_id=a2.id, artist_name=a2.name, city='上海', date='2026-12-31', venue='梅赛德斯-奔驰文化中心', price='480-1280', status='on_sale', description='五月天跨年演唱会 — 上海站')
        s3 = Show(title='林俊杰小巨蛋特别场', artist_id=a3.id, artist_name=a3.name, city='台北', date='2026-10-05', venue='台北小巨蛋', price='420-980', status='on_sale', description='林俊杰抒情特别场')
        db.add_all([s1, s2, s3])
        db.commit()

    seed_market_dossier_data(db)


def ensure_runtime_columns():
    inspector = inspect(database.engine)
    if not inspector.has_table('users'):
        return

    user_columns = {column['name'] for column in inspector.get_columns('users')}
    statements = []
    if 'password_hash' not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) DEFAULT ''")
    if 'group_code' not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN group_code VARCHAR(64) DEFAULT 'B'")

    if inspector.has_table('artists'):
        artist_columns = {column['name'] for column in inspector.get_columns('artists')}
        if 'profile' not in artist_columns:
            statements.append("ALTER TABLE artists ADD COLUMN profile JSON")

    if inspector.has_table('tasks'):
        task_columns = {column['name'] for column in inspector.get_columns('tasks')}
        if 'evidence_ids' not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN evidence_ids JSON")

    if not statements:
        return

    with database.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def init_db():
    database.Base.metadata.create_all(bind=database.engine)
    ensure_runtime_columns()
    db = database.SessionLocal()
    try:
        seed_initial_data(db)
        get_or_create_default_context(db)
    finally:
        db.close()


def next_project_version_no(db: Session, project_id: int):
    return (db.query(func.max(ProjectVersion.version_no)).filter(ProjectVersion.project_id == project_id).scalar() or 0) + 1
