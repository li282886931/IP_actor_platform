import math

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import database
from .models import Artist, ProjectVersion, Show, Tenant, TenantMember, Task, User, UserGroup


def get_or_create_default_context(db: Session, *, account='operator@ruiyinchang.com', name='运营负责人'):
    tenant = db.query(Tenant).order_by(Tenant.id.asc()).first()
    if not tenant:
        tenant = Tenant(name='锐音场默认空间', status='active')
        db.add(tenant)
        db.flush()

    user = db.query(User).filter(User.account == account).first()
    if not user:
        user = User(account=account, name=name or account, status='active')
        db.add(user)
        db.flush()
    elif name and user.name != name:
        user.name = name

    group = db.query(UserGroup).filter(
        UserGroup.tenant_id == tenant.id,
        UserGroup.name == '管理层组',
    ).first()
    if not group:
        group = UserGroup(
            tenant_id=tenant.id,
            name='管理层组',
            description='默认项目管理与决策权限',
            permission_set=['project:read', 'project:write', 'finance:calculate', 'decision:write', 'task:write'],
            data_scope='all_projects',
        )
        db.add(group)
        db.flush()

    if not user.group_id:
        user.group_id = group.id

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


def init_db():
    database.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    try:
        seed_initial_data(db)
        get_or_create_default_context(db)
    finally:
        db.close()


def next_project_version_no(db: Session, project_id: int):
    return (db.query(func.max(ProjectVersion.version_no)).filter(ProjectVersion.project_id == project_id).scalar() or 0) + 1
