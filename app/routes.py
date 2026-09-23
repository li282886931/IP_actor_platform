import os
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import LLAMA_SERVER_MODEL, LLAMA_SERVER_TIMEOUT_SECONDS, LLAMA_SERVER_URL
from .database import get_db
from .models import (
    AIGeneration,
    Assumption,
    Artist,
    Decision,
    Evidence,
    Fact,
    Gate,
    Order,
    Project,
    ProjectVersion,
    ReportShare,
    Risk,
    Show,
    Task,
    Tenant,
    User,
    UserGroup,
)
from .responses import json_ok
from .schemas import (
    AgentChatIn,
    AIGenerateIn,
    AssumptionIn,
    ArtistOut,
    DecisionIn,
    EvidenceUploadIn,
    FactIn,
    FactVerifyIn,
    FinanceBreakevenIn,
    FinanceCalculateIn,
    GateIn,
    OrderIn,
    ProjectIn,
    ReportShareIn,
    RiskIn,
    ShowOut,
    TaskIn,
    TaskSubmitIn,
    UserCreateIn,
    UserUpdateIn,
    WebLoginIn,
    WechatLoginIn,
)
from .services import (
    GROUPS,
    calculate_breakeven_result,
    calculate_finance_result,
    get_default_tenant_id,
    get_or_create_default_context,
    hash_password,
    next_project_version_no,
    project_input_snapshot,
    serialize_assumption,
    serialize_evidence,
    serialize_fact,
    serialize_gate,
    serialize_project,
    serialize_report_share,
    serialize_risk,
    serialize_task,
    serialize_user,
    serialize_version,
    verify_password,
)


router = APIRouter()


def extract_llama_server_text(data):
    if not isinstance(data, dict):
        return None

    choices = data.get('choices')
    if isinstance(choices, list) and choices:
        first_choice = choices[0] or {}
        message = first_choice.get('message') or {}
        content = message.get('content') or message.get('reasoning_content') or first_choice.get('text')
        if content:
            return content

    content = data.get('content')
    if content:
        return content

    return data.get('response')


@router.post('/auth/web-login')
def web_login(payload: WebLoginIn, db: Session = Depends(get_db)):
    tenant, _ = get_or_create_default_context(db)
    user = db.query(User).filter(User.account == payload.account, User.status == 'active').first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid account or password')
    token = f"dev-token-{user.id}-{tenant.id}"
    return json_ok({
        "token": token,
        "user": serialize_user(user),
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
        "source": "web",
    })


@router.post('/auth/wechat-login')
def wechat_login(payload: WechatLoginIn, db: Session = Depends(get_db)):
    tenant, _ = get_or_create_default_context(db)
    group_code = payload.group_code or 'C'
    if group_code not in {group["code"] for group in GROUPS}:
        raise HTTPException(status_code=400, detail='Invalid user group')
    openid = f"local-wx-{payload.code}"
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(
            openid=openid,
            account=f"wx_{payload.code}",
            name=payload.name or '微信用户',
            phone=payload.phone or '',
            group_code=group_code,
            status='active',
        )
        group = db.query(UserGroup).filter(UserGroup.tenant_id == tenant.id, UserGroup.name == group_code).first()
        if group:
            user.group_id = group.id
        db.add(user)
    else:
        user.name = payload.name or user.name
        user.phone = payload.phone or user.phone
        user.group_code = group_code or user.group_code
        user.status = 'active'
    db.commit()
    db.refresh(user)
    return json_ok({
        "token": f"dev-token-{user.id}-{tenant.id}",
        "user": serialize_user(user),
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
        "source": "wechat",
    })


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
def create_user(payload: UserCreateIn, db: Session = Depends(get_db)):
    tenant, _ = get_or_create_default_context(db)
    if payload.group_code not in {group["code"] for group in GROUPS}:
        raise HTTPException(status_code=400, detail='Invalid user group')
    existing = db.query(User).filter(User.account == payload.account).first()
    if existing:
        raise HTTPException(status_code=409, detail='User already exists')
    user = User(
        account=payload.account,
        name=payload.name,
        password_hash=hash_password(payload.password),
        group_code=payload.group_code,
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
def update_user(user_id: int, payload: UserUpdateIn, db: Session = Depends(get_db)):
    tenant, _ = get_or_create_default_context(db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    if payload.group_code is not None:
        if payload.group_code not in {group["code"] for group in GROUPS}:
            raise HTTPException(status_code=400, detail='Invalid user group')
        group = db.query(UserGroup).filter(UserGroup.tenant_id == tenant.id, UserGroup.name == payload.group_code).first()
        if group:
            user.group_id = group.id
        user.group_code = payload.group_code
    if payload.name is not None:
        user.name = payload.name
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
    db.delete(user)
    db.commit()
    return json_ok({"deleted": True})


@router.get('/tenants')
def list_tenants(db: Session = Depends(get_db)):
    get_or_create_default_context(db)
    tenants = db.query(Tenant).order_by(Tenant.id.asc()).all()
    return json_ok([{"id": tenant.id, "name": tenant.name, "status": tenant.status} for tenant in tenants])


@router.post('/tenants/switch')
def switch_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail='Tenant not found')
    return json_ok({
        "token": f"dev-token-tenant-{tenant.id}",
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
    })


@router.get('/projects')
def list_projects(db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    projects = db.query(Project).filter(Project.tenant_id == tenant_id).order_by(Project.id.desc()).all()
    return json_ok([serialize_project(project) for project in projects])


@router.post('/projects')
def create_project(payload: ProjectIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = Project(
        tenant_id=tenant.id,
        name=payload.name,
        type=payload.type or 'concert',
        status='draft',
        artist_name=payload.artist_name or '',
        city=payload.city or '',
        venue=payload.venue or '',
        schedule=payload.schedule or '',
        expected_attendance=payload.expected_attendance,
        avg_ticket_price=payload.avg_ticket_price,
        artist_fee=payload.artist_fee,
        venue_cost=payload.venue_cost,
        marketing_cost=payload.marketing_cost,
        production_cost=payload.production_cost,
        created_by=user.id,
    )
    db.add(project)
    db.flush()

    version = ProjectVersion(
        project_id=project.id,
        version_no=1,
        input_snapshot=project_input_snapshot(project),
        finance_result=None,
        status='draft',
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    project.current_version_id = version.id
    db.commit()
    db.refresh(project)
    return json_ok(serialize_project(project))


@router.get('/projects/{project_id}')
def get_project(project_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    current_version = None
    if project.current_version_id:
        current_version = db.query(ProjectVersion).filter(ProjectVersion.id == project.current_version_id).first()
    data = serialize_project(project)
    data["current_version"] = serialize_version(current_version) if current_version else None
    return json_ok(data)


@router.get('/projects/{project_id}/versions')
def list_project_versions(project_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    versions = db.query(ProjectVersion).filter(ProjectVersion.project_id == project_id).order_by(ProjectVersion.version_no.asc()).all()
    return json_ok([serialize_version(version) for version in versions])


@router.post('/projects/{project_id}/versions')
def create_project_version(project_id: int, payload: ProjectIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    version = ProjectVersion(
        project_id=project.id,
        version_no=next_project_version_no(db, project.id),
        input_snapshot=project_input_snapshot(project),
        finance_result=None,
        status='draft',
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    project.current_version_id = version.id
    db.commit()
    db.refresh(version)
    return json_ok(serialize_version(version))


@router.post('/finance/calculate')
def finance_calculate(payload: FinanceCalculateIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    for field, value in payload.model_dump(exclude={'project_id'}).items():
        if value is not None:
            setattr(project, field, value)

    result = calculate_finance_result(FinanceCalculateIn(project_id=project.id, **{
        "expected_attendance": project.expected_attendance,
        "avg_ticket_price": project.avg_ticket_price,
        "artist_fee": project.artist_fee,
        "venue_cost": project.venue_cost,
        "marketing_cost": project.marketing_cost,
        "production_cost": project.production_cost,
    }))
    version = ProjectVersion(
        project_id=project.id,
        version_no=next_project_version_no(db, project.id),
        input_snapshot=project_input_snapshot(project),
        finance_result=result,
        status=result["status"],
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    project.current_version_id = version.id
    if result["status"] == "calculated":
        project.status = "calculated"
    db.commit()
    result["version_id"] = version.id
    result["project_status"] = project.status
    return json_ok(result)


@router.post('/finance/breakeven')
def finance_breakeven(payload: FinanceBreakevenIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    result = calculate_breakeven_result(project, payload)
    result["project_id"] = project.id
    return json_ok(result)


@router.post('/decisions')
def create_decision(payload: DecisionIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    version = db.query(ProjectVersion).filter(
        ProjectVersion.id == payload.version_id,
        ProjectVersion.project_id == project.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail='Project version not found')

    decision = Decision(
        project_id=project.id,
        version_id=version.id,
        decision_type=payload.decision_type,
        conditions=payload.conditions or '',
        decided_by=user.id,
    )
    project.status = 'pending_confirmation' if payload.decision_type == 'advance' else payload.decision_type
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return json_ok({
        "id": decision.id,
        "project_id": decision.project_id,
        "version_id": decision.version_id,
        "decision_type": decision.decision_type,
        "conditions": decision.conditions,
        "project_status": project.status,
    })


@router.get('/tasks')
def list_tasks(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Task).join(Project, Task.project_id == Project.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    tasks = query.order_by(Task.id.desc()).all()
    return json_ok([serialize_task(task) for task in tasks])


@router.post('/tasks')
def create_task(payload: TaskIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    task = Task(
        project_id=project.id,
        assignee_id=payload.assignee_id,
        title=payload.title,
        description=payload.description or '',
        due_date=payload.due_date or '',
        status='pending',
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return json_ok(serialize_task(task))


@router.post('/tasks/{task_id}/submit')
def submit_task(task_id: int, payload: TaskSubmitIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    task = db.query(Task).join(Project, Task.project_id == Project.id).filter(
        Task.id == task_id,
        Project.tenant_id == tenant_id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    evidence_ids = payload.evidence_ids or []
    if evidence_ids:
        existing_count = db.query(Evidence).filter(
            Evidence.project_id == task.project_id,
            Evidence.id.in_(evidence_ids),
        ).count()
        if existing_count != len(set(evidence_ids)):
            raise HTTPException(status_code=404, detail='Evidence not found')
    task.result = payload.result
    task.evidence_ids = evidence_ids
    task.status = 'submitted'
    db.commit()
    db.refresh(task)
    return json_ok(serialize_task(task))


@router.get('/facts')
def list_facts(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Fact).join(Project, Fact.project_id == Project.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Fact.project_id == project_id)
    facts = query.order_by(Fact.id.desc()).all()
    return json_ok([serialize_fact(fact) for fact in facts])


@router.post('/facts')
def create_fact(payload: FactIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    fact = Fact(
        project_id=project.id,
        title=payload.title,
        content=payload.content or '',
        source=payload.source or '',
        status='pending',
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return json_ok(serialize_fact(fact))


@router.post('/facts/{fact_id}/verify')
def verify_fact(fact_id: int, payload: FactVerifyIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    if payload.status not in {'verified', 'rejected', 'needs_review'}:
        raise HTTPException(status_code=400, detail='Invalid fact status')
    fact = db.query(Fact).join(Project, Fact.project_id == Project.id).filter(
        Fact.id == fact_id,
        Project.tenant_id == tenant.id,
    ).first()
    if not fact:
        raise HTTPException(status_code=404, detail='Fact not found')
    fact.status = payload.status
    fact.verified_by = user.id
    fact.verified_comment = payload.comment or ''
    fact.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fact)
    return json_ok(serialize_fact(fact))


@router.get('/assumptions')
def list_assumptions(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Assumption).join(Project, Assumption.project_id == Project.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Assumption.project_id == project_id)
    assumptions = query.order_by(Assumption.id.desc()).all()
    return json_ok([serialize_assumption(assumption) for assumption in assumptions])


@router.post('/assumptions')
def create_assumption(payload: AssumptionIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    assumption = Assumption(
        project_id=project.id,
        title=payload.title,
        content=payload.content or '',
        confidence=payload.confidence if payload.confidence is not None else 50,
        status='active',
        created_by=user.id,
    )
    db.add(assumption)
    db.commit()
    db.refresh(assumption)
    return json_ok(serialize_assumption(assumption))


@router.post('/evidences/upload')
def upload_evidence(payload: EvidenceUploadIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    if payload.fact_id:
        fact = db.query(Fact).filter(Fact.id == payload.fact_id, Fact.project_id == project.id).first()
        if not fact:
            raise HTTPException(status_code=404, detail='Fact not found')
    evidence = Evidence(
        project_id=project.id,
        fact_id=payload.fact_id,
        name=payload.name,
        file_url=payload.file_url,
        evidence_type=payload.evidence_type or 'document',
        source=payload.source or '',
        status='uploaded',
        meta=payload.metadata or {},
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return json_ok(serialize_evidence(evidence))


@router.get('/evidences')
def list_evidences(project_id: Optional[int] = None, fact_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Evidence).join(Project, Evidence.project_id == Project.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Evidence.project_id == project_id)
    if fact_id:
        query = query.filter(Evidence.fact_id == fact_id)
    evidences = query.order_by(Evidence.id.desc()).all()
    return json_ok([serialize_evidence(evidence) for evidence in evidences])


@router.get('/gates')
def list_gates(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Gate).join(Project, Gate.project_id == Project.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Gate.project_id == project_id)
    gates = query.order_by(Gate.id.desc()).all()
    return json_ok([serialize_gate(gate) for gate in gates])


@router.post('/gates')
def create_gate(payload: GateIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    gate = Gate(
        project_id=project.id,
        name=payload.name,
        status=payload.status or 'pending',
        required_evidence=payload.required_evidence or '',
        owner_group=payload.owner_group or '',
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return json_ok(serialize_gate(gate))


@router.get('/risks')
def list_risks(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Risk).join(Project, Risk.project_id == Project.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Risk.project_id == project_id)
    risks = query.order_by(Risk.id.desc()).all()
    return json_ok([serialize_risk(risk) for risk in risks])


@router.post('/risks')
def create_risk(payload: RiskIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    risk = Risk(
        project_id=project.id,
        title=payload.title,
        level=payload.level or 'medium',
        mitigation=payload.mitigation or '',
        status=payload.status or 'open',
    )
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return json_ok(serialize_risk(risk))


@router.post('/agent/chat')
def agent_chat(payload: AgentChatIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = None
    if payload.project_id:
        project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
        if not project:
            raise HTTPException(status_code=404, detail='Project not found')
    if project:
        risks = db.query(Risk).filter(Risk.project_id == project.id).all()
        gates = db.query(Gate).filter(Gate.project_id == project.id).all()
        answer = (
            f"{project.name} 当前状态为 {project.status}。"
            f"建议优先推进 {gates[0].name if gates else '项目关卡确认'}，"
            f"同时关注 {risks[0].title if risks else '成本、审批和履约风险'}。"
        )
    else:
        answer = "请先选择项目，我可以基于项目版本、财务测算、事实证据和风险给出下一步建议。"
    return json_ok({"answer": answer, "message": payload.message, "project_id": payload.project_id})


@router.get('/cases/search')
def search_cases(q: Optional[str] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(Project).filter(Project.tenant_id == tenant_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Project.name.like(like)) |
            (Project.artist_name.like(like)) |
            (Project.city.like(like)) |
            (Project.venue.like(like))
        )
    projects = query.order_by(Project.id.desc()).limit(20).all()
    return json_ok([
        {
            "project_id": project.id,
            "name": project.name,
            "artist_name": project.artist_name,
            "city": project.city,
            "venue": project.venue,
            "status": project.status,
            "current_version_id": project.current_version_id,
        }
        for project in projects
    ])


@router.post('/reports/{project_id}/share')
def share_report(project_id: int, payload: ReportShareIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    version_id = payload.version_id or project.current_version_id
    if version_id:
        version = db.query(ProjectVersion).filter(ProjectVersion.id == version_id, ProjectVersion.project_id == project.id).first()
        if not version:
            raise HTTPException(status_code=404, detail='Project version not found')
    share = ReportShare(
        project_id=project.id,
        version_id=version_id,
        token=uuid.uuid4().hex,
        expires_in_days=payload.expires_in_days or 7,
        created_by=user.id,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return json_ok(serialize_report_share(share))


@router.get('/artists')
def list_artists(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Artist)
    if q:
        like = f"%{q}%"
        query = query.filter(Artist.name.like(like))
    artists = query.order_by(Artist.heat_score.desc()).all()
    return json_ok([ArtistOut.model_validate(a).model_dump() for a in artists])


@router.get('/artists/{artist_id}')
def get_artist(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail='Artist not found')
    artist_dict = ArtistOut.model_validate(artist).model_dump()
    heat_score = getattr(artist, 'heat_score', 0) or 0
    if heat_score >= 90:
        cities = ['北京', '上海', '广州']
    elif heat_score >= 80:
        cities = ['北京', '上海']
    elif heat_score >= 60:
        cities = ['省会城市', '一线/新一线']
    else:
        cities = ['本地城市']
    return json_ok({"artist": artist_dict, "city_suggestions": cities})


@router.post('/ai/generate')
def ai_generate(payload: AIGenerateIn, db: Session = Depends(get_db)):
    content_type_name = '短视频脚本' if payload.type == 'video_script' else '海报文案'
    generation_nonce = payload.generation_nonce or uuid.uuid4().hex
    generation_seed = random.randint(1, 2_147_483_647)
    prompt = f"""
    你是资深演出行业营销策划和票务转化专家。请为以下演出生成一份可直接用于运营投放的完整宣发方案。

    本次创作批次：{generation_nonce}
    内容类型：{content_type_name}
    演出名称：{payload.show_name}
    艺人：{payload.artist}
    城市：{payload.city}

    输出要求：
    1. 使用中文，语气专业、有现场感、有转化力。
    2. 内容要丰富，不要只输出一句口号。
    3. 必须包含以下小标题：传播定位、核心文案、社交平台短文案、短视频脚本、投放建议。
    4. 海报文案要包含主标题、副标题、卖点 bullet、行动号召。
    5. 短视频脚本要包含 3-5 个镜头、画面、口播/字幕、节奏提示。
    6. 避免空泛形容词，尽量围绕艺人、城市、现场体验和购票转化展开。
    7. 本次必须重新创作，不要复用上一次生成的句式、标题和行动号召；允许在传播角度、开场钩子、短视频节奏和投放建议上做变化。
    """.strip()

    result_text = None
    llama_server_url = os.environ.get('LLAMA_SERVER_URL', LLAMA_SERVER_URL)
    llama_server_model = os.environ.get('LLAMA_SERVER_MODEL', LLAMA_SERVER_MODEL)

    if llama_server_url:
        try:
            resp = requests.post(
                llama_server_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": llama_server_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.95,
                    "top_p": 0.92,
                    "presence_penalty": 0.6,
                    "frequency_penalty": 0.35,
                    "seed": generation_seed,
                    "max_tokens": 1200,
                },
                timeout=LLAMA_SERVER_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            result_text = extract_llama_server_text(resp.json())
        except Exception as exc:
            print('Local llama_server error:', exc)

    api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('DASHSCOPE_API_TOKEN')

    if not result_text and api_key:
        try:
            resp = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "qwen-turbo",
                    "input": {"messages": [{"role": "user", "content": prompt}]},
                    "parameters": {"temperature": 0.95, "top_p": 0.92, "max_tokens": 1200},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data.get('output', {}).get('text') if isinstance(data, dict) else None
            if not result_text:
                result_text = data.get('data', [{}])[0].get('content', '') if isinstance(data, dict) else None
        except Exception as exc:
            print('AI API error:', exc)
            result_text = None

    if not result_text:
        if payload.type == 'poster':
            result_text = f"""
传播定位
面向{payload.city or '目标城市'}核心乐迷与高频演出消费人群，突出{payload.artist or '艺人'}到场带来的稀缺现场体验，将{payload.show_name or '本场演出'}包装为城市级音乐事件。

核心文案
主标题：{payload.artist or '实力唱将'}登陆{payload.city or '城市'}，把熟悉旋律唱成这一晚的共同记忆
副标题：{payload.show_name or '年度现场'}正式开启，经典作品、沉浸舞美与万人合唱一次集结。
卖点：
- 代表作品现场演绎，覆盖歌迷高期待曲目
- 城市限定氛围，适合社交平台打卡传播
- 适合好友、情侣、家庭共同参与的高情绪价值现场
行动号召：锁定开票时间，提前预约提醒，抢占更佳观演位置。

社交平台短文案
这一晚，把耳机里的歌带到现场。{payload.artist or 'TA'}来到{payload.city or '你的城市'}，和你一起完成一次真正属于现场的合唱。

短视频脚本
镜头1：城市地标快切，字幕“{payload.city or '这座城市'}今晚有一场重要相遇”
镜头2：歌迷入场、灯牌亮起，字幕“熟悉的旋律，终于在现场响起”
镜头3：舞台灯光与人群合唱，口播“{payload.artist or '艺人'}的歌，不只适合听，也适合和万人一起唱”
镜头4：票务信息露出，字幕“立即预约，不错过开票提醒”

投放建议
优先投放给本地演出兴趣、音乐综艺兴趣、艺人粉丝和近 30 天票务浏览用户；开票前强化预约，开票当天强化倒计时和余票紧迫感。
            """.strip()
        elif payload.type == 'video_script':
            result_text = f"""
传播定位
以“城市相遇 + 现场合唱”为核心，把{payload.show_name or '演出'}塑造成{payload.city or '本地'}用户近期最值得预约的线下娱乐选择。

核心文案
主标题：{payload.artist or '艺人'}来了，下一次大合唱就在{payload.city or '这座城市'}
副标题：从耳机到现场，把熟悉旋律变成真实相遇。
行动号召：立即预约开票提醒，锁定现场席位。

社交平台短文案
别只在歌单里循环了。{payload.artist or '艺人'}来到{payload.city or '你的城市'}，这一次把副歌交给全场一起唱。

短视频脚本
镜头1｜0-3s：城市夜景与场馆外观快切；字幕“{payload.city or '这座城市'}，准备好了吗？”
镜头2｜3-8s：歌迷检票、灯牌、周边细节；口播“那些陪你通勤、熬夜、长大的歌，要在现场响起了。”
镜头3｜8-15s：舞台灯光、人群挥手、合唱氛围；字幕“{payload.artist or '艺人'} · {payload.show_name or '专属现场'}”
镜头4｜15-22s：票务页和预约按钮；口播“现在预约开票提醒，别把遗憾留到下一轮巡演。”
镜头5｜22-25s：演出信息定格；字幕“立即预约｜一起去现场”

投放建议
短视频首 3 秒必须露出城市和艺人名；达人素材侧重“我为什么一定要去现场”；信息流素材侧重开票时间、场馆和预约按钮。
            """.strip()
        else:
            result_text = f"""
传播定位
围绕{payload.artist or '艺人'}、{payload.show_name or '演出'}与{payload.city or '城市'}建立明确传播主题，服务预约、转化与二次扩散。

核心文案
{payload.show_name or '本场演出'}即将在{payload.city or '目标城市'}开启，用现场声浪连接真实情绪与城市夜晚。

社交平台短文案
把期待留给现场，把位置提前锁定。{payload.artist or '艺人'}与你在{payload.city or '这座城市'}见。

短视频脚本
镜头1：城市与场馆建立期待
镜头2：艺人代表元素引发识别
镜头3：现场氛围和购票信息完成转化

投放建议
按照预约期、开票期、临演期分层投放，分别强化关注、抢票和到场决策。
            """.strip()

    try:
        generation = AIGeneration(type=payload.type, prompt=prompt, result=result_text)
        db.add(generation)
        db.commit()
    except Exception as exc:
        print('Failed to save AI generation:', exc)

    return json_ok({"result": result_text})


@router.get('/shows')
def list_shows(city: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Show)
    if city:
        query = query.filter(Show.city == city)
    shows = query.order_by(Show.id.desc()).all()
    return json_ok([ShowOut.model_validate(show).model_dump() for show in shows])


@router.get('/shows/{show_id}')
def get_show(show_id: int, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail='Show not found')
    return json_ok(ShowOut.model_validate(show).model_dump())


@router.post('/shows/{show_id}/order')
def order_show(show_id: int, payload: OrderIn, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail='Show not found')
    order = Order(show_id=show_id, name=payload.name, phone=payload.phone)
    db.add(order)
    db.commit()
    return json_ok({"order_id": order.id, "status": "ok"})


@router.get('/ping')
def ping():
    return {'ok': True}
