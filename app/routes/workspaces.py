"""Authenticated, read-only role workspaces scoped to the selected membership."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.responses import json_ok
from app.database import get_db
from app.models import Artist, DataQualityIssue, DataSource, Evidence, ExternalDataJob, Gate, Order, Project, ProjectVersion, Risk, Show, TenantMember, User, Venue
from app.services.auth import resolve_request_context
from app.services.serializers import serialize_project, serialize_version
from app.services.workspaces import personal_summary, project_reviews
from app.routes.shows import serialize_show

router = APIRouter(prefix="/workspaces")


def workspace_context(db, authorization, tenant_id, role):
    context = resolve_request_context(db, authorization=authorization or '', tenant_header=tenant_id)
    if context.user.group_code == 'root' or context.user.group_code != role:
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
    return json_ok({"tenant_id": context.tenant.id, "projects": result, "personal": personal_summary(db, context)})


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
        "personal": personal_summary(db, context),
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


@router.get("/admin")
def admin_workspace(authorization: Optional[str] = Header(default=None),
                    x_tenant_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    context = workspace_context(db, authorization, x_tenant_id, 'root')
    tid = context.tenant.id
    members = db.query(User).join(TenantMember, TenantMember.user_id == User.id).filter(TenantMember.tenant_id == tid).all()
    sources = db.query(DataSource).filter(DataSource.tenant_id == tid).order_by(DataSource.id.desc()).all()
    jobs = db.query(ExternalDataJob).filter(ExternalDataJob.tenant_id == tid).order_by(ExternalDataJob.id.desc()).all()
    return json_ok({
        "tenant_id": tid, "personal": personal_summary(db, context),
        "summary": {"users": len(members), "disabled_users": sum(u.status != 'active' for u in members),
                    "projects": db.query(Project).filter(Project.tenant_id == tid).count(),
                    "sources": len(sources), "quality_issues": db.query(DataQualityIssue).filter(
                        DataQualityIssue.tenant_id == tid, DataQualityIssue.status != 'resolved').count()},
        "sources": [{"id": s.id, "name": s.name, "source_kind": s.source_kind, "status": s.status} for s in sources],
        "jobs": [{"id": j.id, "purpose": j.purpose, "provider": j.provider, "status": j.status} for j in jobs],
    })


@router.get("/business")
def business_workspace(authorization: Optional[str] = Header(default=None),
                       x_tenant_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    context = workspace_context(db, authorization, x_tenant_id, 'B')
    return json_ok({"tenant_id": context.tenant.id, "projects": project_reviews(db, context.tenant.id),
                    "personal": personal_summary(db, context)})


@router.get("/brand")
def brand_workspace(authorization: Optional[str] = Header(default=None),
                    x_tenant_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    context = workspace_context(db, authorization, x_tenant_id, 'Brand')
    projects = project_reviews(db, context.tenant.id)
    artist_ids = {p["artist_id"] for p in projects if p["artist_id"]}
    artists = db.query(Artist).filter(Artist.id.in_(artist_ids)).all() if artist_ids else []
    return json_ok({"tenant_id": context.tenant.id, "projects": projects, "personal": personal_summary(db, context),
                    "artists": [{"id": a.id, "name": a.name, "tags": a.tags} for a in artists]})


@router.get("/government")
def government_workspace(authorization: Optional[str] = Header(default=None),
                         x_tenant_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    context = workspace_context(db, authorization, x_tenant_id, 'G')
    venues = db.query(Venue).filter(Venue.tenant_id == context.tenant.id).all()
    return json_ok({"tenant_id": context.tenant.id, "projects": project_reviews(db, context.tenant.id),
                    "personal": personal_summary(db, context),
                    "venues": [{"id": v.id, "name": v.name, "city": v.city, "capacity": v.capacity,
                                "fire_safety_status": v.fire_safety_status, "source": v.source} for v in venues]})


@router.get("/audience")
def audience_workspace(authorization: Optional[str] = Header(default=None),
                       x_tenant_id: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    context = workspace_context(db, authorization, x_tenant_id, 'C')
    orders = db.query(Order).filter(Order.tenant_id == context.tenant.id, Order.user_id == context.user.id).order_by(Order.id.desc()).all()
    shows = db.query(Show).order_by(Show.id.desc()).all()
    by_id = {s.id: s for s in shows}
    return json_ok({"tenant_id": context.tenant.id, "personal": personal_summary(db, context),
                    "shows": [serialize_show(s, db) for s in shows],
                    "reservations": [{"id": o.id, "show_id": o.show_id, "status": o.status,
                                      "show": serialize_show(by_id[o.show_id], db) if o.show_id in by_id else None} for o in orders]})
