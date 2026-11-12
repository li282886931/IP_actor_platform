"""Authenticated, read-only role workspaces scoped to the selected membership."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.responses import json_ok
from app.database import get_db
from app.models import Artist, Evidence, Gate, Project, ProjectVersion, Risk
from app.services.auth import resolve_request_context
from app.services.serializers import serialize_project, serialize_version

router = APIRouter(prefix="/workspaces")


def workspace_context(db, authorization, tenant_id, role):
    context = resolve_request_context(db, authorization=authorization or '', tenant_header=tenant_id)
    if context.user.group_code not in (role, 'root'):
        raise HTTPException(status_code=403, detail='Workspace access denied')
    return context


@router.get("/investor")
def investor_workspace(
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    context = workspace_context(db, authorization, x_tenant_id, 'Investor')
    projects = db.query(Project).filter(Project.tenant_id == context.tenant.id).order_by(Project.id.desc()).all()
    ids = [p.id for p in projects]
    versions = {v.id: v for v in db.query(ProjectVersion).filter(ProjectVersion.project_id.in_(ids)).all()} if ids else {}
    risks, gates, evidence = {}, {}, {}
    if ids:
        for row in db.query(Risk).filter(Risk.project_id.in_(ids)).order_by(Risk.id).all():
            risks.setdefault(row.project_id, []).append({
                "id": row.id, "title": row.title, "level": row.level,
                "mitigation": row.mitigation, "status": row.status,
            })
        for row in db.query(Gate).filter(Gate.project_id.in_(ids)).order_by(Gate.id).all():
            gates.setdefault(row.project_id, []).append({
                "id": row.id, "name": row.name, "status": row.status,
                "required_evidence": row.required_evidence, "owner_group": row.owner_group,
            })
        for row in db.query(Evidence).filter(Evidence.project_id.in_(ids)).all():
            counts = evidence.setdefault(row.project_id, {"total": 0, "pending": 0})
            counts["total"] += 1
            counts["pending"] += int(row.status != 'verified')
    result = []
    for project in projects:
        version = versions.get(project.current_version_id)
        if version and version.project_id != project.id:
            version = None
        result.append({
            **serialize_project(project), "version": serialize_version(version) if version else None,
            "risks": risks.get(project.id, []), "gates": gates.get(project.id, []),
            "evidence": evidence.get(project.id, {"total": 0, "pending": 0}),
        })
    return json_ok({"tenant_id": context.tenant.id, "projects": result})


@router.get("/artist")
def artist_workspace(
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    context = workspace_context(db, authorization, x_tenant_id, 'Artist')
    artist = db.get(Artist, context.user.artist_id) if context.user.artist_id else None
    projects = db.query(Project).filter(
        Project.tenant_id == context.tenant.id, Project.artist_id == artist.id,
    ).order_by(Project.id.desc()).all() if artist else []
    return json_ok({
        "tenant_id": context.tenant.id,
        "artist": {
            "id": artist.id, "name": artist.name, "tags": artist.tags,
            "fan_count": artist.fan_count, "heat_score": artist.heat_score,
            "profile": artist.profile or {}, "verification_status": "pending",
        } if artist else None,
        "projects": [{
            "id": p.id, "name": p.name, "city": p.city, "venue": p.venue,
            "schedule": p.schedule, "status": p.status, "artist_id": p.artist_id,
            "artist_name": p.artist_name,
        } for p in projects],
    })
