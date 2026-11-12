from app.core.responses import json_ok
from app.database import get_db
from app.models import Project
from app.models import ProjectVersion
from app.schemas import FinanceBreakevenIn
from app.schemas import FinanceCalculateIn
from app.schemas import ShowCalculationIn
from app.services import calculate_breakeven_result
from app.services import calculate_finance_result
from app.services import calculate_show_result
from app.services import get_default_tenant_id
from app.services import get_or_create_default_context
from app.services import next_project_version_no
from app.services import project_input_snapshot
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError


router = APIRouter()


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

@router.post('/finance/show-calculation')
def finance_show_calculation(payload: ShowCalculationIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')

    resolved = payload.model_dump()
    for field, value in resolved.items():
        if value is None and hasattr(project, field):
            resolved[field] = getattr(project, field)
    try:
        payload = ShowCalculationIn.model_validate(resolved)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=[
            {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]) from error

    for field, value in payload.model_dump(exclude={'project_id'}).items():
        if hasattr(project, field) and value is not None:
            setattr(project, field, value)

    result = calculate_show_result(project, payload)
    snapshot = {
        **project_input_snapshot(project),
        "show_calculation": payload.model_dump(exclude={"project_id"}),
    }
    current_version = db.query(ProjectVersion).filter(
        ProjectVersion.id == project.current_version_id,
        ProjectVersion.project_id == project.id,
    ).first()
    if current_version and current_version.input_snapshot == snapshot and current_version.finance_result == result:
        return json_ok({
            **result,
            "version_id": current_version.id,
            "project_id": project.id,
            "project_status": project.status,
        })

    version = ProjectVersion(
        project_id=project.id,
        version_no=next_project_version_no(db, project.id),
        input_snapshot=snapshot,
        finance_result=result,
        status=result["status"],
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    project.current_version_id = version.id
    if result["status"] == "calculated":
        project.status = "calculated"
    elif project.status in {"draft", "calculated", "pending_input"}:
        project.status = "pending_input"
    db.commit()
    result["version_id"] = version.id
    result["project_id"] = project.id
    result["project_status"] = project.status
    return json_ok(result)
