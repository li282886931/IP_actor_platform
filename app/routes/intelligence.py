from app.core.responses import json_ok
from app.database import get_db
from app.integrations import connectors as connector_integration
from app.models import AlertEvent
from app.models import Assumption
from app.models import DataAsset
from app.models import DataRecord
from app.models import DataSource
from app.models import Evidence
from app.models import ExternalDataJob
from app.models import Fact
from app.models import Gate
from app.models import MonitoringRule
from app.models import Notification
from app.models import Project
from app.models import ProjectAnalysisJob
from app.models import ProjectVersion
from app.models import Risk
from app.models import Task
from app.schemas import AgentChatIn
from app.schemas import ExternalDataJobIn
from app.schemas import MonitoringRuleIn
from app.schemas import ProjectAnalysisJobIn
from app.services import connector_health
from app.services import get_default_tenant_id
from app.services import get_or_create_default_context
from app.services import serialize_data_asset
from app.services import serialize_external_data_job
from app.services import serialize_project_analysis_job
from app.services import serialize_task
from datetime import datetime
from datetime import timezone
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Header
from app.services import live_analysis
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import json


router = APIRouter()


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

def _serialize_alert(alert: AlertEvent, task: Task | None = None):
    return {
        "id": alert.id,
        "project_id": alert.project_id,
        "rule_id": alert.rule_id,
        "severity": alert.severity,
        "title": alert.title,
        "summary": alert.summary,
        "status": alert.status,
        "context": alert.context or {},
        "task": serialize_task(task) if task else None,
    }

@router.post('/monitoring-rules')
def create_monitoring_rule(payload: MonitoringRuleIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    rule = MonitoringRule(
        tenant_id=tenant.id,
        name=payload.name.strip(),
        rule_type=payload.rule_type.strip().lower(),
        condition_json=payload.condition_json,
        severity_policy=payload.severity_policy,
        notification_policy=payload.notification_policy or {},
        enabled=1 if payload.enabled else 0,
        created_by=user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return json_ok({
        "id": rule.id,
        "name": rule.name,
        "rule_type": rule.rule_type,
        "condition_json": rule.condition_json,
        "severity_policy": rule.severity_policy,
        "enabled": bool(rule.enabled),
        "version": rule.version,
    })

@router.get('/monitoring-rules')
def list_monitoring_rules(db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    rules = db.query(MonitoringRule).filter(MonitoringRule.tenant_id == tenant_id).order_by(MonitoringRule.id.desc()).all()
    return json_ok([
        {
            "id": rule.id,
            "name": rule.name,
            "rule_type": rule.rule_type,
            "condition_json": rule.condition_json or {},
            "severity_policy": rule.severity_policy,
            "enabled": bool(rule.enabled),
            "version": rule.version,
        }
        for rule in rules
    ])

@router.post('/monitoring-rules/{rule_id}/evaluate')
def evaluate_monitoring_rule(rule_id: int, project_id: int, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    rule = db.query(MonitoringRule).filter(
        MonitoringRule.id == rule_id,
        MonitoringRule.tenant_id == tenant.id,
        MonitoringRule.enabled == 1,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail='Monitoring rule not found')
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == tenant.id).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    condition = rule.condition_json or {}
    metric_key = (condition.get('metric_key') or '').strip().lower()
    operator = condition.get('operator')
    threshold = condition.get('threshold')
    record = db.query(DataRecord).join(DataAsset, DataRecord.asset_id == DataAsset.id).filter(
        DataRecord.tenant_id == tenant.id,
        DataAsset.project_id == project.id,
        DataRecord.metric_key == metric_key,
    ).order_by(DataRecord.id.desc()).first()
    if not record:
        return json_ok({"created": False, "reason": "No matching data record"})
    value = (record.value_json or {}).get('value')
    if not isinstance(value, (int, float)) or operator != 'gt' or not isinstance(threshold, (int, float)) or value <= threshold:
        return json_ok({"created": False, "reason": "Rule condition not met"})
    dedupe_key = f"rule:{rule.id}:project:{project.id}:record:{record.id}"
    alert = db.query(AlertEvent).filter(
        AlertEvent.tenant_id == tenant.id,
        AlertEvent.dedupe_key == dedupe_key,
    ).first()
    if alert:
        task = db.query(Task).filter(Task.project_id == project.id, Task.title == '核验售票数据').first()
        return json_ok({"created": False, "alert": _serialize_alert(alert, task)})
    alert = AlertEvent(
        tenant_id=tenant.id,
        project_id=project.id,
        rule_id=rule.id,
        business_key=dedupe_key,
        severity=rule.severity_policy,
        title=rule.name,
        summary=f"{metric_key} 当前值 {value} 超过阈值 {threshold}",
        context={"metric_key": metric_key, "value": value, "threshold": threshold},
        source_record_ids=[record.id],
        dedupe_key=dedupe_key,
    )
    db.add(alert)
    db.flush()
    notification = Notification(
        tenant_id=tenant.id,
        user_id=user.id,
        business_key=f"alert:{alert.id}",
        notification_type='alert',
        title=alert.title,
        content=alert.summary,
        context={"alert_id": alert.id},
    )
    task = None
    if condition.get('task_type') == 'verify_ticketing':
        task = Task(
            project_id=project.id,
            assignee_id=user.id,
            title='核验售票数据',
            description=alert.summary,
        )
        db.add(task)
    db.add(notification)
    db.commit()
    db.refresh(alert)
    if task:
        db.refresh(task)
    return json_ok({"created": True, "alert": _serialize_alert(alert, task)})

@router.get('/alerts')
def list_alerts(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    tenant_id = get_default_tenant_id(db)
    query = db.query(AlertEvent).filter(AlertEvent.tenant_id == tenant_id)
    if project_id:
        query = query.filter(AlertEvent.project_id == project_id)
    if status:
        query = query.filter(AlertEvent.status == status)
    if severity:
        query = query.filter(AlertEvent.severity == severity)
    return json_ok([_serialize_alert(alert) for alert in query.order_by(AlertEvent.id.desc()).all()])

def _update_alert_status(alert_id: int, status: str, db: Session):
    tenant_id = get_default_tenant_id(db)
    alert = db.query(AlertEvent).filter(
        AlertEvent.id == alert_id,
        AlertEvent.tenant_id == tenant_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    if alert.status != 'resolved':
        alert.status = status
        if status == 'resolved':
            alert.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)
    data = _serialize_alert(alert)
    data["resolved_at"] = alert.resolved_at.isoformat() if alert.resolved_at else None
    return json_ok(data)

@router.post('/alerts/{alert_id}/acknowledge')
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    return _update_alert_status(alert_id, 'acknowledged', db)

@router.post('/alerts/{alert_id}/resolve')
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    return _update_alert_status(alert_id, 'resolved', db)

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
    data_source_id = (job.parameters or {}).get('data_source_id')
    source = None
    if data_source_id:
        source = db.query(DataSource).filter(
            DataSource.id == data_source_id,
            DataSource.tenant_id == tenant_id,
        ).first()
        if not source:
            raise HTTPException(status_code=404, detail='Data source not found')
        can_fetch, reason = connector_health(source)
        if not can_fetch:
            job.status = 'blocked'
            job.error_message = reason
            job.result = {
                "data_source_id": source.id,
                "connector_key": source.connector_key,
                "reason": reason,
                "network_called": False,
            }
            db.commit()
            db.refresh(job)
            return json_ok(serialize_external_data_job(job))
        if (
            connector_integration.is_managed_connector(source.connector_key)
            and not connector_integration.connector_credential_is_configured(source.connector_key, source.credential_ref)
        ):
            job.status = 'blocked'
            job.error_message = 'Connector credential is not configured'
            job.result = {
                "data_source_id": source.id,
                "connector_key": source.connector_key,
                "reason": job.error_message,
                "network_called": False,
            }
            db.commit()
            db.refresh(job)
            return json_ok(serialize_external_data_job(job))
    job.status = 'running'
    job.started_at = datetime.now(timezone.utc)
    if source and source.connector_key in {'amap', 'qweather'}:
        try:
            credential = connector_integration.resolve_connector_credential(source.connector_key, source.credential_ref)
            if source.connector_key == 'amap':
                connector_payload = connector_integration.fetch_amap_venue_search(
                    credential,
                    job.parameters or {},
                    connector_integration.requests.get,
                )
            else:
                connector_payload = connector_integration.fetch_qweather_daily_forecast(
                    credential,
                    job.parameters or {},
                    connector_integration.requests.get,
                )
        except (connector_integration.requests.RequestException, ValueError):
            job.status = 'failed'
            job.error_message = 'Connector request failed'
            job.result = {
                "data_source_id": source.id,
                "connector_key": source.connector_key,
                "network_called": True,
            }
            db.commit()
            db.refresh(job)
            return json_ok(serialize_external_data_job(job))
        raw_payload = connector_payload.pop("raw_payload")
        asset = DataAsset(
            tenant_id=tenant_id,
            project_id=job.project_id,
            data_source_id=source.id,
            asset_type=connector_payload["asset_type"],
            source_uri=connector_payload["source_uri"],
            content_hash=hashlib.sha256(
                json.dumps(raw_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            visibility='project',
            status='parsed',
            raw_payload_ref=f"connector://{source.connector_key}/jobs/{job.id}",
            created_by=job.requested_by,
        )
        db.add(asset)
        db.flush()
        records = [
            DataRecord(
                tenant_id=tenant_id,
                asset_id=asset.id,
                entity_type=item["entity_type"],
                entity_id=item["entity_id"],
                metric_key=item["metric_key"],
                value_json=item["value_json"],
                confidence=item["confidence"],
                record_status='observed',
                lineage={
                    "connector_key": source.connector_key,
                    "operation": connector_payload["operation"],
                    "source_id": source.id,
                },
            )
            for item in connector_payload["records"]
        ]
        db.add_all(records)
        db.flush()
        job.result = {
            "data_source_id": source.id,
            "connector_key": source.connector_key,
            "network_called": True,
            "asset": serialize_data_asset(asset, records),
            "item_count": len(records),
            "requires_human_verification": True,
        }
        job.status = 'completed'
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return json_ok(serialize_external_data_job(job))
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
def create_project_analysis_job(project_id: int, payload: ProjectAnalysisJobIn, db: Session = Depends(get_db),
                                authorization: Optional[str] = Header(default=None),
                                x_tenant_id: Optional[str] = Header(default=None)):
    readings = []
    if payload.reads:
        context, project = live_analysis.context_for_project(db, authorization, x_tenant_id, project_id)
        tenant, user = context.tenant, context.user
    else:
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
    if payload.reads:
        readings = live_analysis.collect(db, context, project, payload.reads)

    job = ProjectAnalysisJob(
        tenant_id=tenant.id,
        project_id=project.id,
        version_id=version.id,
        purpose=payload.purpose or '',
        status='running',
        parameters={**(payload.parameters or {}), "reads": [item.model_dump() for item in payload.reads]},
        result={},
        requested_by=user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()
    job.result = build_project_analysis_result(db, project, version)
    if payload.reads:
        job.result = {**job.result, "live_readings": readings,
                      "human_review_questions": [*job.result["human_review_questions"],
                          "请核验实时网页／API 来源的适用范围、读取时间与原始内容；失败来源需补充。"]}
    job.status = 'completed'
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return json_ok(serialize_project_analysis_job(job))

@router.get('/projects/{project_id}/analysis-jobs/{job_id}')
def get_project_analysis_job(project_id: int, job_id: int, db: Session = Depends(get_db),
                             authorization: Optional[str] = Header(default=None),
                             x_tenant_id: Optional[str] = Header(default=None)):
    if authorization:
        from app.services.auth import resolve_request_context
        tenant_id = resolve_request_context(db, authorization=authorization, tenant_header=x_tenant_id).tenant.id
    else:
        tenant_id = get_default_tenant_id(db)
    job = db.query(ProjectAnalysisJob).filter(
        ProjectAnalysisJob.id == job_id,
        ProjectAnalysisJob.project_id == project_id,
        ProjectAnalysisJob.tenant_id == tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail='Project analysis job not found')
    if (job.parameters or {}).get("reads"):
        live_analysis.context_for_project(db, authorization, x_tenant_id, project_id)
    return json_ok(serialize_project_analysis_job(job))

@router.post('/agent/chat')
def agent_chat(payload: AgentChatIn, db: Session = Depends(get_db),
               authorization: Optional[str] = Header(default=None),
               x_tenant_id: Optional[str] = Header(default=None)):
    live_context = None
    if payload.reads or payload.use_ai:
        live_context, _ = live_analysis.context_for_project(db, authorization, x_tenant_id, payload.project_id)
        tenant_id = live_context.tenant.id
    else:
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
    readings = live_analysis.collect(db, live_context, project, payload.reads) if payload.reads else []
    if readings:
        answer += "\n\n实时读取依据（待人工核验）：\n" + "\n".join(
            f"[{i + 1}] {item['source_name']}：{item.get('excerpt') if item['status'] == 'completed' else item['error']}"
            for i, item in enumerate(readings))
        answer += "\n\n请核验来源、统计口径与适用日期，读取内容不自动更新财务参数或通过审批。"
    mode, warning = "rules", ""
    if payload.use_ai:
        answer, mode, warning = live_analysis.synthesize(project, payload.message, readings, answer)
    return json_ok({"answer": answer, "message": payload.message, "project_id": payload.project_id,
                    "readings": readings, "answer_mode": mode, "warning": warning,
                    "requires_human_verification": True})


@router.get('/agent/sources')
def agent_sources(project_id: int, db: Session = Depends(get_db),
                  authorization: Optional[str] = Header(default=None),
                  x_tenant_id: Optional[str] = Header(default=None)):
    context, project = live_analysis.context_for_project(db, authorization, x_tenant_id, project_id)
    return json_ok(live_analysis.catalog(db, context, project))

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
