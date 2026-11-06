from app.core.responses import json_ok
from app.database import get_db
from app.models import AlertEvent
from app.models import Artist
from app.models import Assumption
from app.models import CaseOutcome
from app.models import ConversionAssumption
from app.models import DataAsset
from app.models import DataRecord
from app.models import Decision
from app.models import DecisionSnapshot
from app.models import Evidence
from app.models import Fact
from app.models import ForecastCalibration
from app.models import Gate
from app.models import Project
from app.models import ProjectVersion
from app.models import ProjectWorkEvent
from app.models import ProjectWorkPlan
from app.models import Risk
from app.models import Task
from app.models import User
from app.models import Venue
from app.schemas import CaseOutcomeIn
from app.schemas import ConversionAssumptionIn
from app.schemas import DecisionIn
from app.schemas import GateIn
from app.schemas import ProjectWorkEventIn
from app.schemas import RiskIn
from app.schemas import TaskBatchActionIn
from app.schemas import TaskIn
from app.schemas import TaskSubmitIn
from app.services import get_default_tenant_id
from app.services import get_or_create_default_context
from app.services import serialize_gate
from app.services import serialize_risk
from app.services import serialize_task
from datetime import datetime
from datetime import timezone
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json
import uuid


router = APIRouter()


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
    query = db.query(Task, Project.name, User.name).join(Project, Task.project_id == Project.id).outerjoin(User, Task.assignee_id == User.id).filter(Project.tenant_id == tenant_id)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    tasks = query.order_by(Task.id.desc()).all()
    return json_ok([
        serialize_task(task, project_name=project_name, assignee_name=assignee_name)
        for task, project_name, assignee_name in tasks
    ])

@router.post('/tasks')
def create_task(payload: TaskIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    assignee = None
    if payload.assignee_id is not None:
        assignee = db.query(User).filter(User.id == payload.assignee_id, User.status == 'active').first()
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
    return json_ok(serialize_task(task, project_name=project.name, assignee_name=assignee.name if assignee else None))

@router.post('/tasks/{task_id}/accept')
def accept_task(task_id: int, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    task_row = db.query(Task, Project.name).join(Project, Task.project_id == Project.id).filter(
        Task.id == task_id,
        Project.tenant_id == tenant.id,
    ).first()
    if not task_row:
        raise HTTPException(status_code=404, detail='Task not found')
    task, project_name = task_row
    if task.status in {'submitted', 'completed'}:
        raise HTTPException(status_code=409, detail='Task has already been submitted')
    if task.assignee_id is None:
        task.assignee_id = user.id
    task.status = 'in_progress'
    task.rejection_reason = ''
    db.commit()
    db.refresh(task)
    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    return json_ok(serialize_task(
        task,
        project_name=project_name,
        assignee_name=assignee.name if assignee else None,
    ))

@router.post('/tasks/actions/batch')
def batch_task_action(payload: TaskBatchActionIn, db: Session = Depends(get_db)):
    task_ids = list(dict.fromkeys(payload.task_ids))
    if not task_ids:
        raise HTTPException(status_code=400, detail='Select at least one task')

    tenant, user = get_or_create_default_context(db)
    task_rows = db.query(Task, Project.name).join(Project, Task.project_id == Project.id).filter(
        Task.id.in_(task_ids),
        Project.tenant_id == tenant.id,
    ).all()
    if len(task_rows) != len(task_ids):
        raise HTTPException(status_code=404, detail='Task not found')

    blocked_tasks = [task for task, _ in task_rows if task.status in {'submitted', 'completed'}]
    if blocked_tasks:
        raise HTTPException(status_code=409, detail='Submitted or completed tasks cannot be changed')

    reason = (payload.reason or '').strip()
    if payload.action == 'reject' and not reason:
        raise HTTPException(status_code=400, detail='Rejection reason is required')

    project_names = {}
    for task, project_name in task_rows:
        project_names[task.id] = project_name
        if payload.action == 'accept':
            task.assignee_id = user.id
            task.status = 'in_progress'
            task.rejection_reason = ''
        else:
            task.assignee_id = None
            task.status = 'pending'
            task.rejection_reason = reason

    db.commit()
    tasks_by_id = {task.id: task for task, _ in task_rows}
    serialized_tasks = []
    for task_id in task_ids:
        task = tasks_by_id[task_id]
        db.refresh(task)
        serialized_tasks.append(serialize_task(
            task,
            project_name=project_names[task.id],
            assignee_name=user.name if payload.action == 'accept' else None,
        ))
    return json_ok({
        "action": payload.action,
        "updated_count": len(serialized_tasks),
        "tasks": serialized_tasks,
    })

@router.post('/tasks/{task_id}/submit')
def submit_task(task_id: int, payload: TaskSubmitIn, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    task_row = db.query(Task, Project.name, User.name).join(Project, Task.project_id == Project.id).outerjoin(User, Task.assignee_id == User.id).filter(
        Task.id == task_id,
        Project.tenant_id == tenant_id,
    ).first()
    if not task_row:
        raise HTTPException(status_code=404, detail='Task not found')
    task, project_name, assignee_name = task_row
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
    return json_ok(serialize_task(task, project_name=project_name, assignee_name=assignee_name))

def _serialize_decision_snapshot(snapshot: DecisionSnapshot):
    return {
        "id": snapshot.id,
        "project_id": snapshot.project_id,
        "project_version_id": snapshot.project_version_id,
        "snapshot_type": snapshot.snapshot_type,
        "input_lineage": snapshot.input_lineage or {},
        "finance_result": snapshot.finance_result or {},
        "risk_summary": snapshot.risk_summary or {},
        "alert_summary": snapshot.alert_summary or {},
        "recommendation": snapshot.recommendation,
        "created_by_type": snapshot.created_by_type,
    }

def _serialize_project_work_plan(plan: ProjectWorkPlan | None):
    if not plan:
        return None
    return {
        "id": plan.id,
        "project_id": plan.project_id,
        "version_no": plan.version_no,
        "status": plan.status,
        "plan_json": plan.plan_json or {},
        "decision_snapshot_id": plan.decision_snapshot_id,
        "created_from_event_id": plan.created_from_event_id,
    }

def _serialize_project_work_event(event: ProjectWorkEvent):
    return {
        "id": event.id,
        "project_id": event.project_id,
        "event_type": event.event_type,
        "business_key": event.business_key,
        "payload": event.payload or {},
        "source_asset_id": event.source_asset_id,
        "alert_event_id": event.alert_event_id,
        "decision_snapshot_id": event.decision_snapshot_id,
        "status": event.status,
        "idempotency_key": event.idempotency_key,
    }

def _build_decision_snapshot(db: Session, tenant_id: int, project: Project, snapshot_type: str):
    records = db.query(DataRecord).join(DataAsset, DataRecord.asset_id == DataAsset.id).filter(
        DataRecord.tenant_id == tenant_id,
        DataAsset.project_id == project.id,
    ).order_by(DataRecord.id.asc()).all()
    evidences = db.query(Evidence).filter(Evidence.project_id == project.id).order_by(Evidence.id.asc()).all()
    facts = db.query(Fact).filter(
        Fact.project_id == project.id,
        Fact.status == 'verified',
    ).order_by(Fact.id.asc()).all()
    assumptions = db.query(Assumption).filter(
        Assumption.project_id == project.id,
        Assumption.status == 'active',
    ).order_by(Assumption.id.asc()).all()
    risks = db.query(Risk).filter(
        Risk.project_id == project.id,
        Risk.status != 'resolved',
    ).order_by(Risk.id.asc()).all()
    alerts = db.query(AlertEvent).filter(
        AlertEvent.tenant_id == tenant_id,
        AlertEvent.project_id == project.id,
        AlertEvent.status != 'resolved',
    ).order_by(AlertEvent.id.asc()).all()
    version = db.query(ProjectVersion).filter(
        ProjectVersion.id == project.current_version_id,
        ProjectVersion.project_id == project.id,
    ).first()
    finance_result = version.finance_result if version and version.finance_result else {}
    input_lineage = {
        "data_record_ids": [record.id for record in records],
        "evidence_ids": [evidence.id for evidence in evidences],
        "fact_ids": [fact.id for fact in facts],
        "assumption_ids": [assumption.id for assumption in assumptions],
    }
    risk_summary = {
        "open_count": len(risks),
        "risk_ids": [risk.id for risk in risks],
    }
    alert_summary = {
        "open_count": len(alerts),
        "alert_ids": [alert.id for alert in alerts],
        "severities": sorted({alert.severity for alert in alerts}),
    }
    if alert_summary["open_count"] or risk_summary["open_count"]:
        recommendation = "存在未关闭预警或风险，等待具名负责人核验后再推进。"
    elif not records:
        recommendation = "补充可追溯资料后重新评估；系统不会替代人工审批。"
    else:
        recommendation = "当前输入已更新，请由负责人确认后按既定财务和审批门禁推进。"
    snapshot = DecisionSnapshot(
        tenant_id=tenant_id,
        project_id=project.id,
        project_version_id=version.id if version else None,
        snapshot_type=snapshot_type,
        input_lineage=input_lineage,
        finance_result=finance_result,
        risk_summary=risk_summary,
        alert_summary=alert_summary,
        recommendation=recommendation,
        created_by_type='system',
    )
    db.add(snapshot)
    db.flush()
    return snapshot

def _snapshot_material_signature(snapshot: DecisionSnapshot):
    return json.dumps(
        {
            "input_lineage": snapshot.input_lineage or {},
            "finance_result": snapshot.finance_result or {},
            "risk_summary": snapshot.risk_summary or {},
            "alert_summary": snapshot.alert_summary or {},
            "recommendation": snapshot.recommendation,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )

def _refresh_project_work_plan(
    db: Session,
    tenant_id: int,
    project: Project,
    event: ProjectWorkEvent,
    snapshot: DecisionSnapshot,
):
    previous_snapshot = db.query(DecisionSnapshot).filter(
        DecisionSnapshot.tenant_id == tenant_id,
        DecisionSnapshot.project_id == project.id,
        DecisionSnapshot.id != snapshot.id,
    ).order_by(DecisionSnapshot.id.desc()).first()
    current_plan = db.query(ProjectWorkPlan).filter(
        ProjectWorkPlan.tenant_id == tenant_id,
        ProjectWorkPlan.project_id == project.id,
        ProjectWorkPlan.status == 'current',
    ).order_by(ProjectWorkPlan.version_no.desc()).first()
    material_change = (
        previous_snapshot is None
        or _snapshot_material_signature(previous_snapshot) != _snapshot_material_signature(snapshot)
    )
    if not material_change:
        return current_plan, False
    if current_plan:
        current_plan.status = 'superseded'
    version_no = (current_plan.version_no if current_plan else 0) + 1
    plan = ProjectWorkPlan(
        tenant_id=tenant_id,
        project_id=project.id,
        version_no=version_no,
        status='current',
        decision_snapshot_id=snapshot.id,
        created_from_event_id=event.id,
        plan_json={
            "goal": f"推进{project.name}的可审计决策",
            "constraints": {
                "open_alert_count": (snapshot.alert_summary or {}).get("open_count", 0),
                "open_risk_count": (snapshot.risk_summary or {}).get("open_count", 0),
                "human_gate": "财务公式、审批门槛和资金拨付必须由具名负责人确认",
            },
            "predefined_task_types": ["verify_ticketing", "verify_evidence", "review_risk"],
            "dependencies": ["证据核验", "人工审批"],
            "escalation_policy": "未关闭预警或风险时阻塞推进并通知负责人",
        },
    )
    db.add(plan)
    db.flush()
    return plan, True

@router.post('/projects/{project_id}/work-events')
def create_project_work_event(
    project_id: int,
    payload: ProjectWorkEventIn,
    db: Session = Depends(get_db),
):
    tenant, _ = get_or_create_default_context(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    idempotency_key = payload.idempotency_key.strip()
    existing = db.query(ProjectWorkEvent).filter(
        ProjectWorkEvent.tenant_id == tenant.id,
        ProjectWorkEvent.idempotency_key == idempotency_key,
    ).first()
    if existing:
        snapshot = db.query(DecisionSnapshot).filter(DecisionSnapshot.id == existing.decision_snapshot_id).first()
        plan = db.query(ProjectWorkPlan).filter(
            ProjectWorkPlan.tenant_id == tenant.id,
            ProjectWorkPlan.project_id == project.id,
            ProjectWorkPlan.status == 'current',
        ).order_by(ProjectWorkPlan.version_no.desc()).first()
        return json_ok({
            "created": False,
            "work_plan_created": False,
            "event": _serialize_project_work_event(existing),
            "decision_snapshot": _serialize_decision_snapshot(snapshot) if snapshot else None,
            "work_plan": _serialize_project_work_plan(plan),
        })
    event = ProjectWorkEvent(
        tenant_id=tenant.id,
        project_id=project.id,
        event_type=payload.event_type.strip().lower(),
        business_key=payload.business_key.strip(),
        payload=payload.payload or {},
        source_asset_id=payload.source_asset_id,
        alert_event_id=payload.alert_event_id,
        idempotency_key=idempotency_key,
        status='processing',
    )
    db.add(event)
    db.flush()
    snapshot = _build_decision_snapshot(db, tenant.id, project, event.event_type)
    plan, work_plan_created = _refresh_project_work_plan(db, tenant.id, project, event, snapshot)
    event.decision_snapshot_id = snapshot.id
    event.status = 'processed'
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    db.refresh(snapshot)
    if plan:
        db.refresh(plan)
    return json_ok({
        "created": True,
        "work_plan_created": work_plan_created,
        "event": _serialize_project_work_event(event),
        "decision_snapshot": _serialize_decision_snapshot(snapshot),
        "work_plan": _serialize_project_work_plan(plan),
    })

@router.get('/projects/{project_id}/work-plan')
def get_project_work_plan(project_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    plan = db.query(ProjectWorkPlan).filter(
        ProjectWorkPlan.tenant_id == tenant_id,
        ProjectWorkPlan.project_id == project_id,
        ProjectWorkPlan.status == 'current',
    ).order_by(ProjectWorkPlan.version_no.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail='Project work plan not found')
    return json_ok(_serialize_project_work_plan(plan))

@router.post('/projects/{project_id}/work-plan/refresh')
def refresh_project_work_plan(project_id: int, db: Session = Depends(get_db)):
    return create_project_work_event(
        project_id,
        ProjectWorkEventIn(
            event_type='manual_refresh',
            business_key='manual-refresh',
            idempotency_key=f"manual-refresh:{project_id}:{uuid.uuid4()}",
        ),
        db,
    )

@router.get('/projects/{project_id}/decision-snapshots')
def list_decision_snapshots(project_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    snapshots = db.query(DecisionSnapshot).filter(
        DecisionSnapshot.tenant_id == tenant_id,
        DecisionSnapshot.project_id == project_id,
    ).order_by(DecisionSnapshot.id.desc()).all()
    return json_ok([_serialize_decision_snapshot(snapshot) for snapshot in snapshots])

def _serialize_conversion_assumption(assumption: ConversionAssumption):
    return {
        "id": assumption.id,
        "scope_type": assumption.scope_type,
        "scope_id": assumption.scope_id,
        "funnel_stage_from": assumption.funnel_stage_from,
        "funnel_stage_to": assumption.funnel_stage_to,
        "rate": assumption.rate,
        "segment": assumption.segment or {},
        "evidence_ids": assumption.evidence_ids or [],
        "confidence": assumption.confidence,
        "status": assumption.status,
        "effective_from": assumption.effective_from.isoformat() if assumption.effective_from else None,
        "effective_until": assumption.effective_until.isoformat() if assumption.effective_until else None,
        "version_no": assumption.version_no,
    }

def _serialize_case_outcome(case: CaseOutcome):
    return {
        "id": case.id,
        "title": case.title,
        "artist_id": case.artist_id,
        "city": case.city,
        "venue_id": case.venue_id,
        "outcome_label": case.outcome_label,
        "scenario": case.scenario or {},
        "revenue": case.revenue,
        "cost": case.cost,
        "profit": case.profit,
        "occupancy_rate": case.occupancy_rate,
        "failure_reason": case.failure_reason or '',
        "evidence_ids": case.evidence_ids or [],
    }

def _serialize_forecast_calibration(calibration: ForecastCalibration):
    return {
        "id": calibration.id,
        "project_id": calibration.project_id,
        "conversion_assumption_id": calibration.conversion_assumption_id,
        "forecast_metric": calibration.forecast_metric,
        "forecast_value": calibration.forecast_value,
        "actual_value": calibration.actual_value,
        "error_value": calibration.error_value,
        "segment": calibration.segment or {},
        "status": calibration.status,
        "candidate_rate": calibration.candidate_rate,
    }

def _active_conversion_assumption(db: Session, tenant_id: int, project_id: int):
    now = datetime.utcnow()
    candidates = db.query(ConversionAssumption).filter(
        ConversionAssumption.tenant_id == tenant_id,
        ConversionAssumption.status == 'active',
        (
            ((ConversionAssumption.scope_type == 'project') & (ConversionAssumption.scope_id == str(project_id)))
            | ((ConversionAssumption.scope_type == 'tenant') & (ConversionAssumption.scope_id == str(tenant_id)))
        ),
    ).order_by(ConversionAssumption.version_no.desc(), ConversionAssumption.id.desc()).all()
    for assumption in candidates:
        if assumption.effective_from and assumption.effective_from > now:
            continue
        if assumption.effective_until and assumption.effective_until <= now:
            continue
        return assumption
    return None

@router.post('/conversion-assumptions')
def create_conversion_assumption(payload: ConversionAssumptionIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    if not 0 < payload.rate <= 1:
        raise HTTPException(status_code=422, detail='Conversion rate must be between 0 and 1')
    if payload.status == 'active' and not payload.evidence_ids:
        raise HTTPException(status_code=422, detail='Active conversion assumption requires evidence')
    latest = db.query(ConversionAssumption).filter(
        ConversionAssumption.tenant_id == tenant.id,
        ConversionAssumption.scope_type == payload.scope_type.strip().lower(),
        ConversionAssumption.scope_id == payload.scope_id.strip(),
        ConversionAssumption.funnel_stage_from == payload.funnel_stage_from.strip().lower(),
        ConversionAssumption.funnel_stage_to == payload.funnel_stage_to.strip().lower(),
    ).order_by(ConversionAssumption.version_no.desc()).first()
    assumption = ConversionAssumption(
        tenant_id=tenant.id,
        scope_type=payload.scope_type.strip().lower(),
        scope_id=payload.scope_id.strip(),
        funnel_stage_from=payload.funnel_stage_from.strip().lower(),
        funnel_stage_to=payload.funnel_stage_to.strip().lower(),
        rate=payload.rate,
        segment=payload.segment or {},
        evidence_ids=payload.evidence_ids,
        confidence=payload.confidence if payload.confidence is not None else 50,
        status=payload.status,
        effective_from=payload.effective_from,
        effective_until=payload.effective_until,
        version_no=(latest.version_no if latest else 0) + 1,
        created_by=user.id,
    )
    db.add(assumption)
    db.commit()
    db.refresh(assumption)
    return json_ok(_serialize_conversion_assumption(assumption))

@router.get('/conversion-assumptions')
def list_conversion_assumptions(
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    tenant_id = get_default_tenant_id(db)
    query = db.query(ConversionAssumption).filter(ConversionAssumption.tenant_id == tenant_id)
    if scope_type:
        query = query.filter(ConversionAssumption.scope_type == scope_type)
    if scope_id:
        query = query.filter(ConversionAssumption.scope_id == scope_id)
    assumptions = query.order_by(ConversionAssumption.id.desc()).all()
    return json_ok([_serialize_conversion_assumption(assumption) for assumption in assumptions])

@router.post('/case-outcomes')
def create_case_outcome(payload: CaseOutcomeIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    if payload.artist_id and not db.query(Artist).filter(Artist.id == payload.artist_id).first():
        raise HTTPException(status_code=404, detail='Artist not found')
    if payload.venue_id and not db.query(Venue).filter(
        Venue.id == payload.venue_id,
        Venue.tenant_id == tenant.id,
    ).first():
        raise HTTPException(status_code=404, detail='Venue not found')
    case = CaseOutcome(
        tenant_id=tenant.id,
        title=payload.title.strip(),
        artist_id=payload.artist_id,
        city=payload.city or (payload.scenario or {}).get('city', ''),
        venue_id=payload.venue_id,
        outcome_label=payload.outcome_label,
        scenario=payload.scenario or {},
        revenue=payload.revenue,
        cost=payload.cost,
        profit=payload.profit,
        occupancy_rate=payload.occupancy_rate,
        failure_reason=payload.failure_reason or '',
        evidence_ids=payload.evidence_ids,
        created_by=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return json_ok(_serialize_case_outcome(case))

@router.get('/case-outcomes')
def list_case_outcomes(
    artist_id: Optional[int] = None,
    city: Optional[str] = None,
    venue_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    tenant_id = get_default_tenant_id(db)
    query = db.query(CaseOutcome).filter(CaseOutcome.tenant_id == tenant_id)
    if artist_id:
        query = query.filter(CaseOutcome.artist_id == artist_id)
    if city:
        query = query.filter(CaseOutcome.city == city)
    if venue_id:
        query = query.filter(CaseOutcome.venue_id == venue_id)
    return json_ok([_serialize_case_outcome(case) for case in query.order_by(CaseOutcome.id.desc()).all()])

@router.get('/projects/{project_id}/calibration')
def get_project_calibration(project_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    assumption = _active_conversion_assumption(db, tenant_id, project.id)
    if not assumption:
        return json_ok({
            "status": "needs_assumption",
            "conversion_assumption": None,
            "candidate": None,
            "message": "缺少有来源且在有效期内的转化参数，不能使用默认常数计算。",
        })
    candidate = db.query(ForecastCalibration).filter(
        ForecastCalibration.tenant_id == tenant_id,
        ForecastCalibration.project_id == project.id,
        ForecastCalibration.status == 'candidate',
    ).order_by(ForecastCalibration.id.desc()).first()
    return json_ok({
        "status": "pending_approval" if candidate else "ready",
        "conversion_assumption": _serialize_conversion_assumption(assumption),
        "candidate": _serialize_forecast_calibration(candidate) if candidate else None,
    })

@router.post('/calibration-candidates/{calibration_id}/approve')
def approve_calibration_candidate(calibration_id: int, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    calibration = db.query(ForecastCalibration).filter(
        ForecastCalibration.id == calibration_id,
        ForecastCalibration.tenant_id == tenant.id,
        ForecastCalibration.status == 'candidate',
    ).first()
    if not calibration:
        raise HTTPException(status_code=404, detail='Calibration candidate not found')
    source = db.query(ConversionAssumption).filter(
        ConversionAssumption.id == calibration.conversion_assumption_id,
        ConversionAssumption.tenant_id == tenant.id,
    ).first()
    if not source or not isinstance(calibration.candidate_rate, (int, float)):
        raise HTTPException(status_code=422, detail='Calibration candidate has no approvable conversion parameter')
    source.status = 'superseded'
    source.effective_until = datetime.now(timezone.utc)
    assumption = ConversionAssumption(
        tenant_id=tenant.id,
        scope_type=source.scope_type,
        scope_id=source.scope_id,
        funnel_stage_from=source.funnel_stage_from,
        funnel_stage_to=source.funnel_stage_to,
        rate=calibration.candidate_rate,
        segment=source.segment or {},
        evidence_ids=source.evidence_ids or [],
        confidence=source.confidence,
        status='active',
        effective_from=datetime.now(timezone.utc),
        version_no=source.version_no + 1,
        created_by=user.id,
    )
    calibration.status = 'approved'
    calibration.approved_by = user.id
    calibration.approved_at = datetime.now(timezone.utc)
    db.add(assumption)
    db.commit()
    db.refresh(calibration)
    db.refresh(assumption)
    return json_ok({
        "candidate": _serialize_forecast_calibration(calibration),
        "conversion_assumption": _serialize_conversion_assumption(assumption),
    })

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
