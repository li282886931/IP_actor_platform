from typing import Optional

from app.models import Assumption, DataAsset, DataRecord, DataSource, DocumentParseJob, Evidence, ExternalDataJob, Fact, Gate, Order, OSSUpload, ProjectAnalysisJob, ReportShare, Risk, Task, User
from app.services.auth import can_manage_users, group_role


def serialize_user(user: User):
    return {
        "id": user.id,
        "account": user.account,
        "name": user.name,
        "phone": user.phone,
        "group_code": user.group_code,
        "role": group_role(user.group_code),
        "status": user.status,
        "can_manage_users": can_manage_users(user.group_code),
    }


def serialize_order(order: Order, show_title: str = ''):
    return {
        "id": order.id,
        "show_id": order.show_id,
        "show_title": show_title,
        "name": order.name,
        "phone": order.phone,
    }


def serialize_project(project):
    return {
        "id": project.id,
        "tenant_id": project.tenant_id,
        "name": project.name,
        "type": project.type,
        "status": project.status,
        "artist_id": project.artist_id,
        "artist_name": project.artist_name,
        "city": project.city,
        "venue_id": project.venue_id,
        "venue": project.venue,
        "source_project_id": project.source_project_id,
        "schedule": project.schedule,
        "expected_attendance": project.expected_attendance,
        "avg_ticket_price": project.avg_ticket_price,
        "artist_fee": project.artist_fee,
        "venue_cost": project.venue_cost,
        "marketing_cost": project.marketing_cost,
        "production_cost": project.production_cost,
        "available_funds": project.available_funds,
        "venue_capacity": project.venue_capacity,
        "ticket_tiers": project.ticket_tiers or [],
        "conservative_occupancy_rate": project.conservative_occupancy_rate,
        "neutral_occupancy_rate": project.neutral_occupancy_rate,
        "optimistic_occupancy_rate": project.optimistic_occupancy_rate,
        "current_version_id": project.current_version_id,
    }


def serialize_version(version):
    return {
        "id": version.id,
        "project_id": version.project_id,
        "version_no": version.version_no,
        "input_snapshot": version.input_snapshot,
        "finance_result": version.finance_result,
        "status": version.status,
    }


def serialize_task(task: Task, *, project_name: Optional[str] = None, assignee_name: Optional[str] = None):
    return {
        "id": task.id,
        "project_id": task.project_id,
        "project_name": project_name,
        "assignee_id": task.assignee_id,
        "assignee_name": assignee_name,
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date,
        "status": task.status,
        "result": task.result,
        "evidence_ids": task.evidence_ids or [],
        "evidence_count": len(task.evidence_ids or []),
        "rejection_reason": task.rejection_reason or '',
    }


def serialize_fact(fact: Fact):
    return {
        "id": fact.id,
        "project_id": fact.project_id,
        "title": fact.title,
        "content": fact.content,
        "source": fact.source,
        "status": fact.status,
        "verified_by": fact.verified_by,
        "verified_comment": fact.verified_comment,
    }


def serialize_assumption(assumption: Assumption):
    return {
        "id": assumption.id,
        "project_id": assumption.project_id,
        "title": assumption.title,
        "content": assumption.content,
        "confidence": assumption.confidence,
        "status": assumption.status,
    }


def serialize_evidence(evidence: Evidence):
    return {
        "id": evidence.id,
        "project_id": evidence.project_id,
        "fact_id": evidence.fact_id,
        "name": evidence.name,
        "file_url": evidence.file_url,
        "evidence_type": evidence.evidence_type,
        "source": evidence.source,
        "status": evidence.status,
        "metadata": evidence.meta or {},
        "uploaded_by": evidence.uploaded_by,
    }


def serialize_oss_upload(upload: OSSUpload):
    return {
        "id": upload.id,
        "project_id": upload.project_id,
        "fact_id": upload.fact_id,
        "provider": upload.provider,
        "bucket": upload.bucket,
        "object_key": upload.object_key,
        "file_name": upload.file_name,
        "content_type": upload.content_type,
        "evidence_type": upload.evidence_type,
        "source": upload.source,
        "status": upload.status,
        "file_url": upload.file_url,
        "size": upload.size,
        "checksum": upload.checksum,
        "metadata": upload.meta or {},
    }


def serialize_document_parse_job(job: DocumentParseJob):
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "evidence_id": job.evidence_id,
        "file_name": job.file_name,
        "file_kind": job.file_kind,
        "parse_scope": job.parse_scope,
        "purpose": job.purpose,
        "status": job.status,
        "parameters": job.parameters or {},
        "result": job.result or {},
        "created_by": job.created_by,
    }


def serialize_project_analysis_job(job: ProjectAnalysisJob):
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "version_id": job.version_id,
        "purpose": job.purpose,
        "status": job.status,
        "parameters": job.parameters or {},
        "result": job.result or {},
        "error_message": job.error_message,
        "requested_by": job.requested_by,
    }


def serialize_gate(gate: Gate):
    return {
        "id": gate.id,
        "project_id": gate.project_id,
        "name": gate.name,
        "status": gate.status,
        "required_evidence": gate.required_evidence,
        "owner_group": gate.owner_group,
    }


def serialize_risk(risk: Risk):
    return {
        "id": risk.id,
        "project_id": risk.project_id,
        "title": risk.title,
        "level": risk.level,
        "mitigation": risk.mitigation,
        "status": risk.status,
    }


def serialize_report_share(share: ReportShare):
    return {
        "id": share.id,
        "project_id": share.project_id,
        "version_id": share.version_id,
        "token": share.token,
        "expires_in_days": share.expires_in_days,
        "share_url": f"/shared/reports/{share.token}",
    }


def serialize_external_data_job(job: ExternalDataJob):
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "project_id": job.project_id,
        "source_type": job.source_type,
        "provider": job.provider,
        "query": job.query,
        "purpose": job.purpose,
        "status": job.status,
        "parameters": job.parameters or {},
        "result": job.result or {},
        "error_message": job.error_message,
        "requested_by": job.requested_by,
    }


def serialize_data_source(source: DataSource):
    return {
        "id": source.id,
        "tenant_id": source.tenant_id,
        "name": source.name,
        "source_kind": source.source_kind,
        "connector_key": source.connector_key,
        "status": source.status,
        "credential_ref": source.credential_ref or '',
        "schedule_config": source.schedule_config or {},
        "scope_config": source.scope_config or {},
    }


def serialize_data_record(record: DataRecord):
    return {
        "id": record.id,
        "asset_id": record.asset_id,
        "entity_type": record.entity_type,
        "entity_id": record.entity_id,
        "metric_key": record.metric_key,
        "value_json": record.value_json,
        "unit": record.unit or '',
        "confidence": record.confidence,
        "record_status": record.record_status,
        "lineage": record.lineage or {},
    }


def serialize_data_asset(asset: DataAsset, records: list[DataRecord] | None = None):
    return {
        "id": asset.id,
        "tenant_id": asset.tenant_id,
        "project_id": asset.project_id,
        "data_source_id": asset.data_source_id,
        "asset_type": asset.asset_type,
        "source_uri": asset.source_uri or '',
        "content_hash": asset.content_hash or '',
        "visibility": asset.visibility,
        "status": asset.status,
        "raw_payload_ref": asset.raw_payload_ref or '',
        "records": [serialize_data_record(record) for record in records or []],
    }
