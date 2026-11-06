from app.core.responses import json_ok
from app.database import get_db
from app.documents.feasibility import build_feasibility_calculation
from app.documents.feasibility import build_feasibility_report_docx
from app.integrations import object_storage as storage_integration
from app.models import Assumption
from app.models import Evidence
from app.models import ExternalDataJob
from app.models import Fact
from app.models import Order
from app.models import Project
from app.models import ProjectVersion
from app.models import ReportShare
from app.models import Risk
from app.models import Show
from app.models import Task
from app.schemas import FeasibilityReportIn
from app.schemas import ReportShareIn
from app.schemas import ShowOut
from app.services import get_default_tenant_id
from app.services import get_or_create_default_context
from app.services import serialize_evidence
from app.services import serialize_order
from app.services import serialize_report_share
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid


router = APIRouter()


def current_version_by_project(db: Session, project_ids: list[int]):
    if not project_ids:
        return {}
    versions = db.query(ProjectVersion).filter(ProjectVersion.project_id.in_(project_ids)).all()
    by_project = {}
    for version in versions:
        current = by_project.get(version.project_id)
        if not current or version.version_no > current.version_no:
            by_project[version.project_id] = version
    return by_project

def neutral_profit_from_version(version: Optional[ProjectVersion]):
    if not version or not isinstance(version.finance_result, dict):
        return 0
    neutral = (version.finance_result.get('scenarios') or {}).get('neutral') or {}
    return neutral.get('profit') or 0

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

@router.post('/projects/{project_id}/feasibility-report')
def generate_feasibility_report(project_id: int, payload: FeasibilityReportIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    version_id = payload.version_id or project.current_version_id
    version = None
    if version_id:
        version = db.query(ProjectVersion).filter(
            ProjectVersion.id == version_id,
            ProjectVersion.project_id == project.id,
        ).first()
        if not version:
            raise HTTPException(status_code=404, detail='Project version not found')

    calculation = build_feasibility_calculation(project, payload)
    if calculation["status"] != "calculated":
        raise HTTPException(status_code=400, detail=calculation)

    facts = db.query(Fact).filter(Fact.project_id == project.id).order_by(Fact.id.desc()).all()
    risks = db.query(Risk).filter(Risk.project_id == project.id).order_by(Risk.id.desc()).all()
    assumptions = db.query(Assumption).filter(Assumption.project_id == project.id).order_by(Assumption.id.desc()).all()
    copy_mode = 'ai_assisted_template' if payload.use_ai_copy else 'deterministic_template'
    report_bytes = build_feasibility_report_docx(
        project,
        calculation,
        facts,
        risks,
        assumptions,
        copy_mode=copy_mode,
    )

    file_name = f"project-{project.id}-feasibility-report.docx"
    object_key = f"projects/{project.id}/reports/{uuid.uuid4().hex}/{file_name}"
    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    stored = storage_integration.store_generated_report(storage_integration.current_oss_provider(), object_key, report_bytes, content_type)
    metadata = {
        "object_key": stored["object_key"],
        "provider": stored["provider"],
        "bucket": stored["bucket"],
        "size": stored["size"],
        "local_path": stored["local_path"],
        "content_type": content_type,
        "version_id": version.id if version else None,
        "copy_mode": copy_mode,
        "calculation_result": calculation,
    }
    evidence = Evidence(
        project_id=project.id,
        fact_id=None,
        name=file_name,
        file_url=stored["file_url"],
        evidence_type='feasibility_report',
        source='system',
        status='uploaded',
        meta=metadata,
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    download_url = f"/reports/files/{evidence.id}" if stored["provider"] == "local-placeholder" else stored["file_url"]
    return json_ok({
        "project_id": project.id,
        "version_id": version.id if version else None,
        "file_name": file_name,
        "file_url": stored["file_url"],
        "download_url": download_url,
        "calculation_result": calculation,
        "evidence": serialize_evidence(evidence),
    })

@router.get('/reports/files/{evidence_id}')
def download_report_file(evidence_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    evidence = db.query(Evidence).join(Project, Evidence.project_id == Project.id).filter(
        Evidence.id == evidence_id,
        Project.tenant_id == tenant_id,
        Evidence.evidence_type == 'feasibility_report',
    ).first()
    if not evidence:
        raise HTTPException(status_code=404, detail='Report file not found')
    local_path = (evidence.meta or {}).get("local_path")
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail='Local report file not found')
    return FileResponse(
        local_path,
        media_type=(evidence.meta or {}).get("content_type") or 'application/octet-stream',
        filename=evidence.name,
    )

@router.get('/analytics/dashboard')
def dashboard_analytics(db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    projects = db.query(Project).filter(Project.tenant_id == tenant_id).all()
    project_ids = [project.id for project in projects]
    versions_by_project = current_version_by_project(db, project_ids)
    neutral_profit_total = sum(
        neutral_profit_from_version(versions_by_project.get(project.id))
        for project in projects
    )
    active_projects = sum(1 for project in projects if project.status != 'archived')
    calculated_projects = sum(1 for project in projects if project.status == 'calculated')
    pending_confirmation_projects = sum(1 for project in projects if project.status == 'pending_confirmation')
    pending_tasks = db.query(Task).filter(Task.project_id.in_(project_ids), Task.status == 'pending').count() if project_ids else 0
    reservations = db.query(Order).count()
    on_sale_shows = db.query(Show).filter(Show.status == 'on_sale').count()
    evidence_count = db.query(Evidence).filter(Evidence.project_id.in_(project_ids)).count() if project_ids else 0
    external_jobs = db.query(ExternalDataJob).filter(ExternalDataJob.tenant_id == tenant_id).count()

    summary = {
        "active_projects": active_projects,
        "calculated_projects": calculated_projects,
        "pending_confirmation_projects": pending_confirmation_projects,
        "pending_tasks": pending_tasks,
        "reservations": reservations,
        "on_sale_shows": on_sale_shows,
        "neutral_profit_total": neutral_profit_total,
        "evidence_count": evidence_count,
        "external_jobs": external_jobs,
    }
    metrics = [
        {"key": "active_projects", "label": "进行中项目", "value": active_projects, "unit": "个"},
        {"key": "neutral_profit_total", "label": "中性利润合计", "value": neutral_profit_total, "unit": "元"},
        {"key": "reservations", "label": "预约人数", "value": reservations, "unit": "人"},
        {"key": "pending_tasks", "label": "待处理任务", "value": pending_tasks, "unit": "项"},
        {"key": "on_sale_shows", "label": "售票中演出", "value": on_sale_shows, "unit": "场"},
        {"key": "evidence_count", "label": "证据资料", "value": evidence_count, "unit": "条"},
    ]
    return json_ok({"summary": summary, "metrics": metrics})

@router.get('/ticketing/summary')
def ticketing_summary(db: Session = Depends(get_db)):
    shows = db.query(Show).order_by(Show.id.desc()).all()
    reservation_counts = dict(
        db.query(Order.show_id, func.count(Order.id))
        .group_by(Order.show_id)
        .all()
    )
    show_titles = {show.id: show.title for show in shows}
    show_rows = [
        {
            **ShowOut.model_validate(show).model_dump(),
            "reservation_count": reservation_counts.get(show.id, 0),
        }
        for show in shows
    ]
    show_rows.sort(key=lambda item: (item["reservation_count"], item["id"]), reverse=True)
    orders = db.query(Order).order_by(Order.id.desc()).limit(50).all()
    summary = {
        "total_shows": len(shows),
        "on_sale_shows": sum(1 for show in shows if show.status == 'on_sale'),
        "reservation_count": sum(reservation_counts.values()),
    }
    return json_ok({
        "summary": summary,
        "shows": show_rows,
        "orders": [serialize_order(order, show_titles.get(order.show_id, '')) for order in orders],
    })
