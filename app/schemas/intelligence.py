from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExternalDataJobIn(BaseModel):
    project_id: Optional[int] = None
    source_type: str
    provider: Optional[str] = 'mcp'
    query: str
    purpose: Optional[str] = ''
    parameters: Optional[dict] = None


class DataSourceIn(BaseModel):
    name: str
    source_kind: str
    connector_key: str
    status: Literal['configured', 'disabled', 'active', 'error'] = 'configured'
    credential_ref: Optional[str] = ''
    schedule_config: Optional[dict] = None
    scope_config: Optional[dict] = None


class DataRecordIn(BaseModel):
    entity_type: str
    entity_id: str
    metric_key: str
    value_json: Any
    unit: Optional[str] = ''
    confidence: Optional[int] = None
    record_status: Literal['observed', 'estimated', 'assumed', 'verified', 'conflicted'] = 'observed'
    lineage: Optional[dict] = None


class DataAssetIn(BaseModel):
    project_id: Optional[int] = None
    data_source_id: int
    asset_type: str
    source_uri: Optional[str] = ''
    content_hash: Optional[str] = ''
    visibility: Literal['tenant', 'project', 'restricted'] = 'project'
    raw_payload_ref: Optional[str] = ''
    records: list[DataRecordIn] = Field(default_factory=list)


class MonitoringRuleIn(BaseModel):
    name: str
    rule_type: str
    condition_json: dict
    severity_policy: Literal['reminder', 'important', 'urgent'] = 'reminder'
    notification_policy: Optional[dict] = None
    enabled: bool = True


class ConversionAssumptionIn(BaseModel):
    scope_type: str
    scope_id: str
    funnel_stage_from: str
    funnel_stage_to: str
    rate: float
    segment: Optional[dict] = None
    evidence_ids: list[int] = Field(default_factory=list)
    confidence: Optional[int] = 50
    status: Literal['draft', 'active'] = 'draft'
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class CaseOutcomeIn(BaseModel):
    title: str
    artist_id: Optional[int] = None
    city: Optional[str] = ''
    venue_id: Optional[int] = None
    outcome_label: Literal['success', 'failure', 'mixed']
    scenario: Optional[dict] = None
    revenue: Optional[int] = None
    cost: Optional[int] = None
    profit: Optional[int] = None
    occupancy_rate: Optional[float] = None
    failure_reason: Optional[str] = ''
    evidence_ids: list[int] = Field(default_factory=list)
