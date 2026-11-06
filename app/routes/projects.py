from app.core.responses import json_ok
from app.database import get_db
from app.models import Artist
from app.models import Project
from app.models import ProjectVersion
from app.models import Venue
from app.schemas import ProjectIn
from app.services import get_default_tenant_id
from app.services import get_or_create_default_context
from app.services import next_project_version_no
from app.services import project_input_snapshot
from app.services import serialize_project
from app.services import serialize_version
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session


router = APIRouter()


@router.get('/projects')
def list_projects(db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    projects = db.query(Project).filter(Project.tenant_id == tenant_id).order_by(Project.id.desc()).all()
    return json_ok([serialize_project(project) for project in projects])

@router.post('/projects')
def create_project(payload: ProjectIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    if payload.artist_id and not db.query(Artist).filter(Artist.id == payload.artist_id).first():
        raise HTTPException(status_code=404, detail='Artist not found')
    if payload.venue_id and not db.query(Venue).filter(
        Venue.id == payload.venue_id,
        Venue.tenant_id == tenant.id,
    ).first():
        raise HTTPException(status_code=404, detail='Venue not found')
    if payload.source_project_id and not db.query(Project).filter(
        Project.id == payload.source_project_id,
        Project.tenant_id == tenant.id,
    ).first():
        raise HTTPException(status_code=404, detail='Source project not found')
    project = Project(
        tenant_id=tenant.id,
        name=payload.name,
        type=payload.type or 'concert',
        status='draft',
        artist_id=payload.artist_id,
        artist_name=payload.artist_name or '',
        city=payload.city or '',
        venue_id=payload.venue_id,
        venue=payload.venue or '',
        source_project_id=payload.source_project_id,
        schedule=payload.schedule or '',
        expected_attendance=payload.expected_attendance,
        avg_ticket_price=payload.avg_ticket_price,
        artist_fee=payload.artist_fee,
        venue_cost=payload.venue_cost,
        marketing_cost=payload.marketing_cost,
        production_cost=payload.production_cost,
        available_funds=payload.available_funds,
        venue_capacity=payload.venue_capacity,
        ticket_tiers=payload.ticket_tiers,
        conservative_occupancy_rate=payload.conservative_occupancy_rate,
        neutral_occupancy_rate=payload.neutral_occupancy_rate,
        optimistic_occupancy_rate=payload.optimistic_occupancy_rate,
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
