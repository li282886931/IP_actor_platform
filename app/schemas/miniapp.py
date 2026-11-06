from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MiniappScreenSummary(BaseModel):
    title: str
    subtitle: Optional[str] = None
    highlight: Optional[str] = None


class MiniappEntityRef(BaseModel):
    entity_type: str
    entity_id: int


class MiniappEntityField(BaseModel):
    key: str
    label: str
    value: str


class MiniappEntitySection(BaseModel):
    key: str
    title: str
    content: str


class MiniappEntityRelatedItem(BaseModel):
    title: str
    subtitle: Optional[str] = None
    detail_ref: MiniappEntityRef


class MiniappEntityAction(BaseModel):
    label: str
    target_screen: Optional[str] = None


class MiniappEntityDetail(BaseModel):
    entity_type: str
    entity_id: int
    title: str
    subtitle: Optional[str] = None
    status: Optional[str] = None
    media_url: Optional[str] = None
    fields: list[MiniappEntityField] = Field(default_factory=list)
    sections: list[MiniappEntitySection] = Field(default_factory=list)
    related_items: list[MiniappEntityRelatedItem] = Field(default_factory=list)
    actions: list[MiniappEntityAction] = Field(default_factory=list)


class MiniappScreenItem(BaseModel):
    id: str
    entity_type: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    value: Optional[str] = None
    details: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    detail_ref: Optional[MiniappEntityRef] = None

    @model_validator(mode='after')
    def infer_detail_reference(self):
        if self.detail_ref is not None:
            return self
        context_keys = {
            "show": "show_id",
            "artist": "artist_id",
            "project": "project_id",
            "project_version": "version_id",
            "fact": "fact_id",
            "assumption": "assumption_id",
            "evidence": "evidence_id",
            "risk": "risk_id",
            "gate": "gate_id",
            "decision": "decision_id",
            "task": "task_id",
            "document_parse_job": "parse_job_id",
            "project_analysis_job": "analysis_job_id",
            "report_share": "share_id",
            "venue": "venue_id",
            "tour_plan": "tour_plan_id",
            "tour_stop": "tour_stop_id",
            "ticketing_snapshot": "id",
            "project_actual": "project_actual_id",
            "tenant": "tenant_id",
            "tenant_member": "tenant_member_id",
            "notification": "notification_id",
            "member_invitation": "invitation_id",
            "agent_permission": "permission_id",
            "privacy_consent": "id",
        }
        context_key = context_keys.get(self.entity_type)
        entity_id = self.context.get(context_key) if context_key else None
        if isinstance(entity_id, int) and entity_id > 0:
            self.detail_ref = MiniappEntityRef(
                entity_type=self.entity_type,
                entity_id=entity_id,
            )
        return self


class MiniappScreenAction(BaseModel):
    label: str
    target_screen: Optional[str] = None


class MiniappEmptyState(BaseModel):
    title: str
    description: Optional[str] = None
    action: Optional[MiniappScreenAction] = None


class MiniappScreenContext(BaseModel):
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    version_id: Optional[int] = None
    task_id: Optional[int] = None
    artist_id: Optional[int] = None


class MiniappScreenData(BaseModel):
    screen_id: str
    summary: MiniappScreenSummary
    items: list[MiniappScreenItem] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    context: MiniappScreenContext = Field(default_factory=MiniappScreenContext)
    empty_state: Optional[MiniappEmptyState] = None

    @field_validator('screen_id')
    @classmethod
    def validate_screen_id(cls, value: str):
        if value not in {f"S{index:02d}" for index in range(1, 85)}:
            raise ValueError('screen_id must be between S01 and S84')
        return value
