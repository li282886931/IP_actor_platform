import os
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import LLAMA_SERVER_MODEL, LLAMA_SERVER_TIMEOUT_SECONDS, LLAMA_SERVER_URL, MINIO_BUCKET, MINIO_ENDPOINT, MINIO_SECURE, OSS_PROVIDER
from .database import get_db
from .models import (
    AIGeneration,
    Assumption,
    Artist,
    Decision,
    DocumentParseJob,
    Evidence,
    ExternalDataJob,
    Fact,
    Gate,
    Order,
    OSSUpload,
    Project,
    ProjectAnalysisJob,
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
    DocumentParseJobIn,
    EvidenceUploadIn,
    FactIn,
    FactVerifyIn,
    FinanceBreakevenIn,
    FinanceCalculateIn,
    GateIn,
    OSSUploadCompleteIn,
    OSSUploadInitiateIn,
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
    ExternalDataJobIn,
    ProjectAnalysisJobIn,
)
from .document_parsers import parse_document_evidence, parse_spreadsheet_evidence
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
    serialize_document_parse_job,
    serialize_evidence,
    serialize_fact,
    serialize_gate,
    serialize_external_data_job,
    serialize_oss_upload,
    serialize_project_analysis_job,
    serialize_project,
    serialize_report_share,
    serialize_risk,
    serialize_task,
    serialize_user,
    serialize_version,
    verify_password,
)


router = APIRouter()


def current_oss_provider():
    return os.environ.get('OSS_PROVIDER', OSS_PROVIDER).strip().lower()


def minio_bucket_name():
    return os.environ.get('MINIO_BUCKET', MINIO_BUCKET).strip()


def minio_secure_enabled():
    value = os.environ.get('MINIO_SECURE')
    if value is None:
        return bool(MINIO_SECURE)
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def create_minio_client():
    try:
        from minio import Minio
    except ImportError as exc:
        raise RuntimeError('MinIO SDK is not installed') from exc

    access_key = os.environ.get('MINIO_ACCESS_KEY') or ''
    secret_key = os.environ.get('MINIO_SECRET_KEY') or ''
    if not access_key or not secret_key:
        raise RuntimeError('MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required')

    return Minio(
        os.environ.get('MINIO_ENDPOINT', MINIO_ENDPOINT),
        access_key=access_key,
        secret_key=secret_key,
        secure=minio_secure_enabled(),
    )


def ensure_minio_bucket(client, bucket: str):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def create_upload_target(provider: str, object_key: str, content_type: str):
    if provider != 'minio':
        return {
            "provider": "local-placeholder",
            "bucket": "",
            "upload_url": f"/oss/local-placeholder/{object_key}",
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "expires_in_seconds": 900,
        }

    bucket = minio_bucket_name()
    if not bucket:
        raise HTTPException(status_code=500, detail='MINIO_BUCKET is required')
    try:
        client = create_minio_client()
        ensure_minio_bucket(client, bucket)
        expires = timedelta(seconds=900)
        upload_url = client.presigned_put_object(bucket, object_key, expires=expires)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'MinIO upload URL generation failed: {exc}') from exc

    return {
        "provider": "minio",
        "bucket": bucket,
        "upload_url": upload_url,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
        "expires_in_seconds": 900,
    }


def safe_object_name(file_name: str):
    sanitized = re.sub(r'[^A-Za-z0-9._-]+', '-', file_name.strip()).strip('.-')
    return sanitized or 'upload.bin'


def infer_file_kind(file_name: str):
    suffix = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
    if suffix == 'docx':
        return 'docx'
    if suffix == 'pdf':
        return 'pdf'
    if suffix in {'xlsx', 'xls', 'csv'}:
        return 'spreadsheet'
    if suffix in {'png', 'jpg', 'jpeg', 'webp'}:
        return 'image'
    return 'document'


def project_payload_from_candidate(candidate: dict):
    allowed = {
        'name',
        'type',
        'artist_name',
        'city',
        'venue',
        'schedule',
        'expected_attendance',
        'avg_ticket_price',
        'artist_fee',
        'venue_cost',
        'marketing_cost',
        'production_cost',
    }
    data = {key: candidate.get(key) for key in allowed if key in candidate}
    data['name'] = data.get('name') or f"{candidate.get('artist_name') or '未命名项目'}-{candidate.get('city') or '待定城市'}"
    data['type'] = data.get('type') or 'concert'
    return data


def extract_llama_server_text(data):
    if not isinstance(data, dict):
        return None

    choices = data.get('choices')
    if isinstance(choices, list) and choices:
        first_choice = choices[0] or {}
        message = first_choice.get('message') or {}
        content = message.get('content') or first_choice.get('text')
        if content:
            return content

    content = data.get('content')
    if content:
        return content

    return data.get('response')


def create_records_from_parse_result(db: Session, job: DocumentParseJob, result: dict):
    created = {"facts": [], "assumptions": [], "risks": [], "gates": []}

    for item in result.get('candidate_facts') or []:
        fact = Fact(
            project_id=job.project_id,
            title=item.get('title') or f"{job.file_name} 解析候选事实",
            content=item.get('content') or '',
            source=item.get('source') or job.file_kind,
            status='pending',
        )
        db.add(fact)
        db.flush()
        created["facts"].append(fact.id)

    for item in result.get('candidate_assumptions') or []:
        assumption = Assumption(
            project_id=job.project_id,
            title=item.get('title') or '资料解析假设',
            content=item.get('content') or '',
            confidence=item.get('confidence') or 50,
            status='active',
            created_by=job.created_by,
        )
        db.add(assumption)
        db.flush()
        created["assumptions"].append(assumption.id)

    for item in result.get('candidate_risks') or []:
        risk = Risk(
            project_id=job.project_id,
            title=item.get('title') or '资料解析风险',
            level=item.get('level') or 'medium',
            mitigation=item.get('mitigation') or '由负责人复核资料后处理。',
            status='open',
        )
        db.add(risk)
        db.flush()
        created["risks"].append(risk.id)

    for item in result.get('candidate_gates') or []:
        gate = Gate(
            project_id=job.project_id,
            name=item.get('name') or '资料人工核验',
            status=item.get('status') or 'pending',
            required_evidence=item.get('required_evidence') or job.file_name,
            owner_group=item.get('owner_group') or 'B',
        )
        db.add(gate)
        db.flush()
        created["gates"].append(gate.id)

    return created


def build_project_analysis_result(db: Session, project: Project, version: ProjectVersion):
    facts = db.query(Fact).filter(Fact.project_id == project.id).all()
    assumptions = db.query(Assumption).filter(Assumption.project_id == project.id).all()
    risks = db.query(Risk).filter(Risk.project_id == project.id).all()
    gates = db.query(Gate).filter(Gate.project_id == project.id).all()
    evidences = db.query(Evidence).filter(Evidence.project_id == project.id).all()
    external_jobs = db.query(ExternalDataJob).filter(ExternalDataJob.project_id == project.id).all()
    finance_result = version.finance_result or {}
    neutral_profit = ((finance_result.get('scenarios') or {}).get('neutral') or {}).get('profit')

    open_risks = [risk for risk in risks if risk.status == 'open']
    pending_gates = [gate for gate in gates if gate.status in {'pending', 'blocked'}]
    pending_facts = [fact for fact in facts if fact.status != 'verified']

    if any(gate.status == 'blocked' for gate in gates) or (neutral_profit is not None and neutral_profit < 0):
        recommendation = 'pause'
    elif open_risks or pending_gates or pending_facts:
        recommendation = 'conditional_advance'
    else:
        recommendation = 'advance'

    human_review_questions = []
    if pending_facts:
        human_review_questions.append('请核验解析生成的候选事实是否与原始资料一致。')
    if pending_gates:
        human_review_questions.append('请确认审批、授权、付款或场地方资料是否已经补齐。')
    if open_risks:
        human_review_questions.append('请确认开放风险的缓释措施和责任人。')
    if not human_review_questions:
        human_review_questions.append('请负责人复核分析结论后再形成最终决策。')

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "city": project.city,
            "artist_name": project.artist_name,
        },
        "version_id": version.id,
        "inputs": {
            "facts": {
                "total": len(facts),
                "verified": len([fact for fact in facts if fact.status == 'verified']),
                "pending": len(pending_facts),
            },
            "assumptions": {
                "total": len(assumptions),
                "active": len([item for item in assumptions if item.status == 'active']),
            },
            "risks": {
                "total": len(risks),
                "open": len(open_risks),
            },
            "gates": {
                "total": len(gates),
                "pending": len(pending_gates),
            },
            "evidences": len(evidences),
            "external_data_jobs": {
                "total": len(external_jobs),
                "completed": len([job for job in external_jobs if job.status == 'completed']),
            },
            "finance_status": finance_result.get('status') or 'missing',
            "neutral_profit": neutral_profit,
        },
        "analysis_summary": "已汇总项目版本、财务测算、证据、事实、假设、风险、门禁和外部采集任务，结论仅作为负责人核验前的候选判断。",
        "risk_explanations": [
            {"title": risk.title, "level": risk.level, "mitigation": risk.mitigation}
            for risk in open_risks[:10]
        ],
        "missing_materials": [
            gate.required_evidence or gate.name
            for gate in pending_gates
        ],
        "human_review_questions": human_review_questions,
        "recommendation": recommendation,
        "requires_human_verification": True,
    }


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


@router.post('/oss/uploads/initiate')
def initiate_oss_upload(payload: OSSUploadInitiateIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    if payload.fact_id:
        fact = db.query(Fact).filter(Fact.id == payload.fact_id, Fact.project_id == project.id).first()
        if not fact:
            raise HTTPException(status_code=404, detail='Fact not found')

    file_name = safe_object_name(payload.file_name)
    object_key = f"projects/{project.id}/{uuid.uuid4().hex}/{file_name}"
    upload_target = create_upload_target(
        current_oss_provider(),
        object_key,
        payload.content_type or 'application/octet-stream',
    )
    upload = OSSUpload(
        project_id=project.id,
        fact_id=payload.fact_id,
        provider=upload_target["provider"],
        bucket=upload_target["bucket"],
        object_key=object_key,
        file_name=file_name,
        content_type=payload.content_type or 'application/octet-stream',
        evidence_type=payload.evidence_type or 'document',
        source=payload.source or '',
        status='pending',
        meta=payload.metadata or {},
        created_by=user.id,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return json_ok({
        **serialize_oss_upload(upload),
        "upload_url": upload_target["upload_url"],
        "method": upload_target["method"],
        "headers": upload_target["headers"],
        "expires_in_seconds": upload_target["expires_in_seconds"],
    })


@router.post('/oss/uploads/{upload_id}/complete')
def complete_oss_upload(upload_id: int, payload: OSSUploadCompleteIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    upload = db.query(OSSUpload).join(Project, OSSUpload.project_id == Project.id).filter(
        OSSUpload.id == upload_id,
        Project.tenant_id == tenant.id,
    ).first()
    if not upload:
        raise HTTPException(status_code=404, detail='OSS upload not found')
    if upload.status == 'completed':
        raise HTTPException(status_code=400, detail='OSS upload already completed')
    fact_id = payload.fact_id if payload.fact_id is not None else upload.fact_id
    if fact_id:
        fact = db.query(Fact).filter(Fact.id == fact_id, Fact.project_id == upload.project_id).first()
        if not fact:
            raise HTTPException(status_code=404, detail='Fact not found')

    if upload.provider == 'minio':
        try:
            create_minio_client().stat_object(upload.bucket, upload.object_key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f'MinIO object verification failed: {exc}') from exc

    file_url = payload.file_url or (
        f"minio://{upload.bucket}/{upload.object_key}"
        if upload.provider == 'minio'
        else f"oss://local-placeholder/{upload.object_key}"
    )
    upload.fact_id = fact_id
    upload.file_url = file_url
    upload.size = payload.size
    upload.checksum = payload.checksum or ''
    upload.status = 'completed'
    upload.completed_at = datetime.now(timezone.utc)
    upload_meta = {
        **(upload.meta or {}),
        **(payload.metadata or {}),
        "object_key": upload.object_key,
        "provider": upload.provider,
        "size": payload.size,
        "checksum": payload.checksum or '',
    }
    upload.meta = upload_meta
    evidence = Evidence(
        project_id=upload.project_id,
        fact_id=fact_id,
        name=upload.file_name,
        file_url=file_url,
        evidence_type=upload.evidence_type,
        source=upload.source or upload.provider,
        status='uploaded',
        meta=upload_meta,
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(upload)
    db.refresh(evidence)
    return json_ok({
        "upload": serialize_oss_upload(upload),
        "evidence": serialize_evidence(evidence),
    })


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


@router.post('/evidences/{evidence_id}/parse-jobs')
def create_document_parse_job(evidence_id: int, payload: DocumentParseJobIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    evidence = db.query(Evidence).join(Project, Evidence.project_id == Project.id).filter(
        Evidence.id == evidence_id,
        Project.tenant_id == tenant.id,
    ).first()
    if not evidence:
        raise HTTPException(status_code=404, detail='Evidence not found')
    file_kind = infer_file_kind(evidence.name or evidence.file_url)
    parse_scope = payload.parse_scope or ('batch_projects' if file_kind == 'spreadsheet' else 'single_project')
    if parse_scope not in {'single_project', 'batch_projects'}:
        raise HTTPException(status_code=400, detail='Invalid parse scope')
    job = DocumentParseJob(
        tenant_id=tenant.id,
        project_id=evidence.project_id,
        evidence_id=evidence.id,
        file_name=evidence.name,
        file_kind=file_kind,
        parse_scope=parse_scope,
        purpose=payload.purpose or '',
        status='queued',
        parameters=payload.parameters or {},
        result={},
        created_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return json_ok(serialize_document_parse_job(job))


@router.post('/document-parse-jobs/{job_id}/run')
def run_document_parse_job(job_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    job = db.query(DocumentParseJob).filter(
        DocumentParseJob.id == job_id,
        DocumentParseJob.tenant_id == tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail='Document parse job not found')
    evidence = db.query(Evidence).filter(Evidence.id == job.evidence_id, Evidence.project_id == job.project_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail='Evidence not found')
    if job.status == 'completed':
        return json_ok(serialize_document_parse_job(job))

    job.status = 'running'
    job.started_at = datetime.now(timezone.utc)
    if job.parse_scope == 'batch_projects':
        result = parse_spreadsheet_evidence(evidence)
    else:
        result = parse_document_evidence(evidence, job.file_kind)
        result["created_records"] = create_records_from_parse_result(db, job, result)
    job.result = result
    job.status = 'completed'
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return json_ok(serialize_document_parse_job(job))


@router.post('/document-parse-jobs/{job_id}/confirm-projects')
def confirm_document_parse_job_projects(job_id: int, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    job = db.query(DocumentParseJob).filter(
        DocumentParseJob.id == job_id,
        DocumentParseJob.tenant_id == tenant.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail='Document parse job not found')
    if job.status != 'completed':
        raise HTTPException(status_code=400, detail='Document parse job is not completed')
    candidates = (job.result or {}).get('candidate_projects') or []
    if not candidates:
        raise HTTPException(status_code=400, detail='No candidate projects to confirm')

    created_projects = []
    for candidate in candidates:
        project_data = project_payload_from_candidate(candidate)
        project = Project(
            tenant_id=tenant.id,
            name=project_data['name'],
            type=project_data.get('type') or 'concert',
            status='draft',
            artist_name=project_data.get('artist_name') or '',
            city=project_data.get('city') or '',
            venue=project_data.get('venue') or '',
            schedule=project_data.get('schedule') or '',
            expected_attendance=project_data.get('expected_attendance'),
            avg_ticket_price=project_data.get('avg_ticket_price'),
            artist_fee=project_data.get('artist_fee'),
            venue_cost=project_data.get('venue_cost'),
            marketing_cost=project_data.get('marketing_cost'),
            production_cost=project_data.get('production_cost'),
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
        created_projects.append(project)

    job.result = {**(job.result or {}), "confirmed_project_ids": [project.id for project in created_projects]}
    db.commit()
    for project in created_projects:
        db.refresh(project)
    return json_ok({"projects": [serialize_project(project) for project in created_projects]})


@router.post('/external-data/jobs')
def create_external_data_job(payload: ExternalDataJobIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    if payload.project_id:
        project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
        if not project:
            raise HTTPException(status_code=404, detail='Project not found')
    source_type = payload.source_type.strip().lower()
    if source_type not in {'web', 'api', 'skill', 'mcp'}:
        raise HTTPException(status_code=400, detail='Invalid external data source type')
    job = ExternalDataJob(
        tenant_id=tenant.id,
        project_id=payload.project_id,
        source_type=source_type,
        provider=(payload.provider or 'mcp').strip().lower(),
        query=payload.query.strip(),
        purpose=payload.purpose or '',
        status='queued',
        parameters=payload.parameters or {},
        result={},
        requested_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return json_ok(serialize_external_data_job(job))


@router.get('/external-data/jobs')
def list_external_data_jobs(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    query = db.query(ExternalDataJob).filter(ExternalDataJob.tenant_id == tenant_id)
    if project_id:
        query = query.filter(ExternalDataJob.project_id == project_id)
    jobs = query.order_by(ExternalDataJob.id.desc()).all()
    return json_ok([serialize_external_data_job(job) for job in jobs])


@router.get('/external-data/jobs/{job_id}')
def get_external_data_job(job_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    job = db.query(ExternalDataJob).filter(ExternalDataJob.id == job_id, ExternalDataJob.tenant_id == tenant_id).first()
    if not job:
        raise HTTPException(status_code=404, detail='External data job not found')
    return json_ok(serialize_external_data_job(job))


@router.post('/external-data/jobs/{job_id}/run')
def run_external_data_job(job_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    job = db.query(ExternalDataJob).filter(ExternalDataJob.id == job_id, ExternalDataJob.tenant_id == tenant_id).first()
    if not job:
        raise HTTPException(status_code=404, detail='External data job not found')
    if job.status == 'completed':
        return json_ok(serialize_external_data_job(job))
    job.status = 'running'
    job.started_at = datetime.now(timezone.utc)
    job.result = {
        "summary": f"已预留通过 {job.provider} 获取 {job.source_type} 数据的异步采集流程。",
        "query": job.query,
        "source_type": job.source_type,
        "provider": job.provider,
        "purpose": job.purpose,
        "items": [],
        "requires_human_verification": True,
        "note": "当前为后端预留实现；接入真实 Skill、MCP 或第三方 API 后写入可追溯来源、采集时间和置信度。",
    }
    job.status = 'completed'
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return json_ok(serialize_external_data_job(job))


@router.post('/projects/{project_id}/analysis-jobs')
def create_project_analysis_job(project_id: int, payload: ProjectAnalysisJobIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    version_id = payload.version_id or project.current_version_id
    version = db.query(ProjectVersion).filter(
        ProjectVersion.id == version_id,
        ProjectVersion.project_id == project.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail='Project version not found')

    job = ProjectAnalysisJob(
        tenant_id=tenant.id,
        project_id=project.id,
        version_id=version.id,
        purpose=payload.purpose or '',
        status='running',
        parameters=payload.parameters or {},
        result={},
        requested_by=user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    job.result = build_project_analysis_result(db, project, version)
    job.status = 'completed'
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return json_ok(serialize_project_analysis_job(job))


@router.get('/projects/{project_id}/analysis-jobs/{job_id}')
def get_project_analysis_job(project_id: int, job_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    job = db.query(ProjectAnalysisJob).filter(
        ProjectAnalysisJob.id == job_id,
        ProjectAnalysisJob.project_id == project_id,
        ProjectAnalysisJob.tenant_id == tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail='Project analysis job not found')
    return json_ok(serialize_project_analysis_job(job))


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
    prompt = f"""/no_think
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
    8. 禁止编造用户未提供的日期、场馆、票价、技术参数、效果提升比例或销售成绩；必要时使用“待确认”或提出补充建议。
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
                    "chat_template_kwargs": {"enable_thinking": False},
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
