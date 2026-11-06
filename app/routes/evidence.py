from app.core.responses import json_ok
from app.database import get_db
from app.documents.parsers import parse_document_evidence
from app.documents.parsers import parse_spreadsheet_evidence
from app.integrations import connectors as connector_integration
from app.integrations import object_storage as storage_integration
from app.models import Assumption
from app.models import DataAsset
from app.models import DataQualityIssue
from app.models import DataRecord
from app.models import DataSource
from app.models import DocumentParseJob
from app.models import Evidence
from app.models import Fact
from app.models import Gate
from app.models import OSSUpload
from app.models import Project
from app.models import ProjectVersion
from app.models import Risk
from app.schemas import AssumptionIn
from app.schemas import DataAssetIn
from app.schemas import DataSourceIn
from app.schemas import DocumentParseJobIn
from app.schemas import EvidenceUploadIn
from app.schemas import FactIn
from app.schemas import FactVerifyIn
from app.schemas import OSSUploadCompleteIn
from app.schemas import OSSUploadInitiateIn
from app.services import connector_health
from app.services import get_default_tenant_id
from app.services import get_or_create_default_context
from app.services import project_input_snapshot
from app.services import serialize_assumption
from app.services import serialize_data_asset
from app.services import serialize_data_record
from app.services import serialize_data_source
from app.services import serialize_document_parse_job
from app.services import serialize_evidence
from app.services import serialize_fact
from app.services import serialize_oss_upload
from app.services import serialize_project
from datetime import datetime
from datetime import timezone
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import uuid


router = APIRouter()


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

    file_name = storage_integration.safe_object_name(payload.file_name)
    object_key = f"projects/{project.id}/{uuid.uuid4().hex}/{file_name}"
    upload_target = storage_integration.create_upload_target(
        storage_integration.current_oss_provider(),
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
            storage_integration.create_minio_client().stat_object(upload.bucket, upload.object_key)
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

@router.post('/data-sources')
def create_data_source(payload: DataSourceIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    existing = db.query(DataSource).filter(
        DataSource.tenant_id == tenant.id,
        DataSource.name == payload.name.strip(),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail='Data source name already exists')
    source = DataSource(
        tenant_id=tenant.id,
        name=payload.name.strip(),
        source_kind=payload.source_kind.strip().lower(),
        connector_key=payload.connector_key.strip().lower(),
        status=payload.status,
        credential_ref=(payload.credential_ref or '').strip(),
        schedule_config=payload.schedule_config or {},
        scope_config=payload.scope_config or {},
        created_by=user.id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return json_ok(serialize_data_source(source))

@router.get('/data-sources')
def list_data_sources(db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    sources = db.query(DataSource).filter(DataSource.tenant_id == tenant_id).order_by(DataSource.id.desc()).all()
    return json_ok([serialize_data_source(source) for source in sources])

@router.post('/data-sources/{source_id}/health-check')
def health_check_data_source(source_id: int, db: Session = Depends(get_db)):
    tenant_id = get_default_tenant_id(db)
    source = db.query(DataSource).filter(DataSource.id == source_id, DataSource.tenant_id == tenant_id).first()
    if not source:
        raise HTTPException(status_code=404, detail='Data source not found')
    can_fetch, reason = connector_health(source)
    if (
        can_fetch
        and connector_integration.is_managed_connector(source.connector_key)
        and not connector_integration.connector_credential_is_configured(source.connector_key, source.credential_ref)
    ):
        can_fetch = False
        reason = 'Connector credential is not configured'
    return json_ok({
        "data_source_id": source.id,
        "connector_key": source.connector_key,
        "status": source.status,
        "can_fetch": can_fetch,
        "reason": reason,
    })

@router.post('/data-assets')
def create_data_asset(payload: DataAssetIn, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    source = db.query(DataSource).filter(
        DataSource.id == payload.data_source_id,
        DataSource.tenant_id == tenant.id,
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail='Data source not found')
    if payload.project_id:
        project = db.query(Project).filter(Project.id == payload.project_id, Project.tenant_id == tenant.id).first()
        if not project:
            raise HTTPException(status_code=404, detail='Project not found')
    asset = DataAsset(
        tenant_id=tenant.id,
        project_id=payload.project_id,
        data_source_id=source.id,
        asset_type=payload.asset_type.strip().lower(),
        source_uri=(payload.source_uri or '').strip(),
        content_hash=(payload.content_hash or '').strip(),
        visibility=payload.visibility,
        raw_payload_ref=(payload.raw_payload_ref or '').strip(),
        created_by=user.id,
    )
    db.add(asset)
    db.flush()
    records = [
        DataRecord(
            tenant_id=tenant.id,
            asset_id=asset.id,
            entity_type=record.entity_type.strip().lower(),
            entity_id=record.entity_id,
            metric_key=record.metric_key.strip().lower(),
            value_json=record.value_json,
            unit=record.unit or '',
            confidence=record.confidence,
            record_status=record.record_status,
            lineage=record.lineage or {},
        )
        for record in payload.records
    ]
    db.add_all(records)
    db.commit()
    db.refresh(asset)
    return json_ok(serialize_data_asset(asset, records))

@router.get('/data-assets')
def list_data_assets(
    project_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    tenant_id = get_default_tenant_id(db)
    query = db.query(DataAsset).filter(DataAsset.tenant_id == tenant_id)
    if project_id:
        query = query.filter(DataAsset.project_id == project_id)
    if asset_type:
        query = query.filter(DataAsset.asset_type == asset_type)
    if status:
        query = query.filter(DataAsset.status == status)
    assets = query.order_by(DataAsset.id.desc()).all()
    return json_ok([serialize_data_asset(asset) for asset in assets])

@router.get('/data-records')
def list_data_records(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    metric_key: Optional[str] = None,
    db: Session = Depends(get_db),
):
    tenant_id = get_default_tenant_id(db)
    query = db.query(DataRecord).filter(DataRecord.tenant_id == tenant_id)
    if entity_type:
        query = query.filter(DataRecord.entity_type == entity_type)
    if entity_id:
        query = query.filter(DataRecord.entity_id == entity_id)
    if metric_key:
        query = query.filter(DataRecord.metric_key == metric_key)
    records = query.order_by(DataRecord.id.desc()).all()
    return json_ok([serialize_data_record(record) for record in records])

@router.post('/data-quality-issues/{issue_id}/resolve')
def resolve_data_quality_issue(issue_id: int, db: Session = Depends(get_db)):
    tenant, user = get_or_create_default_context(db)
    issue = db.query(DataQualityIssue).filter(
        DataQualityIssue.id == issue_id,
        DataQualityIssue.tenant_id == tenant.id,
    ).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Data quality issue not found')
    if issue.status != 'resolved':
        issue.status = 'resolved'
        issue.resolved_by = user.id
        issue.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(issue)
    return json_ok({
        "id": issue.id,
        "status": issue.status,
        "resolved_by": issue.resolved_by,
        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
    })
