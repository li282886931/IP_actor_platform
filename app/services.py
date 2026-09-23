import hashlib
import math

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from . import database
from .models import (
    Assumption,
    Artist,
    Evidence,
    Fact,
    Gate,
    ProjectVersion,
    ReportShare,
    Risk,
    Show,
    Task,
    Tenant,
    TenantMember,
    User,
    UserGroup,
)


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


def seed_initial_data(db: Session):
    if db.query(Artist).count() > 0 or db.query(Show).count() > 0:
        return

    a1 = Artist(name='周杰伦', tags='流行/华语', heat_score=95, fan_count='5000万', risk_level=0)
    a2 = Artist(name='五月天', tags='摇滚/台湾', heat_score=88, fan_count='2000万', risk_level=0)
    a3 = Artist(name='林俊杰', tags='流行/R&B', heat_score=82, fan_count='1500万', risk_level=2)
    db.add_all([a1, a2, a3])
    db.commit()

    s1 = Show(title='周杰伦·北京演唱会', artist_id=a1.id, artist_name=a1.name, city='北京', date='2026-09-10', venue='鸟巢', price='380-1280', status='on_sale', description='周杰伦个人巡回演唱会 — 北京站')
    s2 = Show(title='五月天·上海演唱会', artist_id=a2.id, artist_name=a2.name, city='上海', date='2026-12-31', venue='梅赛德斯-奔驰文化中心', price='480-1280', status='on_sale', description='五月天跨年演唱会 — 上海站')
    s3 = Show(title='林俊杰小巨蛋特别场', artist_id=a3.id, artist_name=a3.name, city='台北', date='2026-10-05', venue='台北小巨蛋', price='420-980', status='on_sale', description='林俊杰抒情特别场')
    db.add_all([s1, s2, s3])
    db.commit()


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
