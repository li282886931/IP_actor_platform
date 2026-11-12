from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DecisionIn(BaseModel):
    project_id: int
    version_id: int
    decision_type: str
    conditions: Optional[str] = ''


class TaskIn(BaseModel):
    project_id: int
    assignee_id: Optional[int] = None
    title: str
    description: Optional[str] = ''
    due_date: Optional[str] = ''


class TaskSubmitIn(BaseModel):
    result: str
    evidence_ids: Optional[list[int]] = None


class TaskBatchActionIn(BaseModel):
    task_ids: list[int]
    action: Literal['accept', 'reject']
    reason: Optional[str] = ''


class FactIn(BaseModel):
    project_id: int
    title: str
    content: Optional[str] = ''
    source: Optional[str] = ''


class FactVerifyIn(BaseModel):
    status: str
    comment: Optional[str] = ''


class AssumptionIn(BaseModel):
    project_id: int
    title: str
    content: Optional[str] = ''
    confidence: Optional[int] = 50


class EvidenceUploadIn(BaseModel):
    project_id: int
    fact_id: Optional[int] = None
    name: str
    file_url: str
    evidence_type: Optional[str] = 'document'
    source: Optional[str] = ''
    metadata: Optional[dict] = None


class OSSUploadInitiateIn(BaseModel):
    project_id: int
    fact_id: Optional[int] = None
    file_name: str
    content_type: Optional[str] = 'application/octet-stream'
    evidence_type: Optional[str] = 'document'
    source: Optional[str] = ''
    metadata: Optional[dict] = None


class OSSUploadCompleteIn(BaseModel):
    file_url: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = ''
    fact_id: Optional[int] = None
    metadata: Optional[dict] = None


class DocumentParseJobIn(BaseModel):
    parse_scope: Optional[str] = None
    purpose: Optional[str] = ''
    parameters: Optional[dict] = None


class GateIn(BaseModel):
    project_id: int
    name: str
    status: Optional[str] = 'pending'
    required_evidence: Optional[str] = ''
    owner_group: Optional[str] = ''


class RiskIn(BaseModel):
    project_id: int
    title: str
    level: Optional[str] = 'medium'
    mitigation: Optional[str] = ''
    status: Optional[str] = 'open'


class AgentReadIn(BaseModel):
    source_id: int = Field(gt=0)
    url: Optional[str] = Field(default=None, max_length=2048)


class AgentChatIn(BaseModel):
    project_id: Optional[int] = None
    message: str
    reads: list[AgentReadIn] = Field(default_factory=list, max_length=4)
    use_ai: bool = False


class ReportShareIn(BaseModel):
    version_id: Optional[int] = None
    expires_in_days: Optional[int] = 7
