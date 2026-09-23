import os
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import AIGeneration, Artist, Decision, Order, Project, ProjectVersion, Show, Task, Tenant
from .responses import json_ok
from .schemas import AIGenerateIn, ArtistOut, DecisionIn, FinanceCalculateIn, OrderIn, ProjectIn, ShowOut, TaskIn, WebLoginIn
from .services import (
    calculate_finance_result,
    get_default_tenant_id,
    get_or_create_default_context,
    next_project_version_no,
    project_input_snapshot,
    serialize_project,
    serialize_task,
    serialize_version,
)


router = APIRouter()


@router.post('/auth/web-login')
def web_login(payload: WebLoginIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db, account=payload.account, name=payload.name or payload.account)
    token = f"dev-token-{user.id}-{tenant.id}"
    return json_ok({
        "token": token,
        "user": {"id": user.id, "account": user.account, "name": user.name, "status": user.status},
        "current_tenant": {"id": tenant.id, "name": tenant.name, "status": tenant.status},
        "source": "web",
    })


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
    prompt = f"""
    你是演出行业营销专家。请为以下演出生成{payload.type}：
    演出：{payload.show_name}，艺人：{payload.artist}，城市：{payload.city}
    要求：年轻化、有传播力、带emoji、不超过150字。
    """.strip()

    api_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('DASHSCOPE_API_TOKEN')
    result_text = None

    if api_key:
        try:
            resp = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "qwen-turbo", "input": {"messages": [{"role": "user", "content": prompt}]}},
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
            result_text = f"🎵 {payload.show_name} · {payload.artist} · {payload.city} —— 不容错过的现场，立即抢票！🔥"
        elif payload.type == 'video_script':
            result_text = f"短视频脚本：开场s1 展示{payload.artist}，过渡s2 展示现场，结尾s3 呼吁到场。"
        else:
            result_text = f"生成：{payload.type} for {payload.show_name} by {payload.artist} in {payload.city}"

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
