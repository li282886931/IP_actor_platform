from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MiniappScreenSummary(BaseModel):
    title: str
    subtitle: Optional[str] = None
    highlight: Optional[str] = None


class MiniappScreenItem(BaseModel):
    id: str
    entity_type: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    value: Optional[str] = None
    details: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


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


class ArtistOut(BaseModel):
    id: int
    name: str
    tags: Optional[str]
    heat_score: int
    fan_count: Optional[str]
    risk_level: int
    profile: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ShowOut(BaseModel):
    id: int
    title: str
    artist_id: Optional[int]
    artist_name: Optional[str]
    city: Optional[str]
    date: Optional[str]
    venue: Optional[str]
    price: Optional[str]
    status: Optional[str]
    description: Optional[str]
    poster_url: Optional[str] = ''

    model_config = ConfigDict(from_attributes=True)


class AIGenerateIn(BaseModel):
    type: str
    show_name: Optional[str] = ''
    artist: Optional[str] = ''
    city: Optional[str] = ''
    generation_nonce: Optional[str] = ''


class OrderIn(BaseModel):
    name: str
    phone: str


class WebLoginIn(BaseModel):
    account: str
    password: str
    captcha_id: str
    captcha_code: str
    name: Optional[str] = ''


class WechatLoginIn(BaseModel):
    code: str
    phone_code: str
    name: Optional[str] = ''


class UserCreateIn(BaseModel):
    account: str
    name: str
    phone: Optional[str] = ''
    password: str
    group_code: str


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    group_code: Optional[str] = None
    status: Optional[str] = None


class ProjectIn(BaseModel):
    name: str
    type: Optional[str] = 'concert'
    artist_id: Optional[int] = None
    artist_name: Optional[str] = ''
    city: Optional[str] = ''
    venue_id: Optional[int] = None
    venue: Optional[str] = ''
    source_project_id: Optional[int] = None
    schedule: Optional[str] = ''
    expected_attendance: Optional[int] = None
    avg_ticket_price: Optional[int] = None
    artist_fee: Optional[int] = None
    venue_cost: Optional[int] = None
    marketing_cost: Optional[int] = None
    production_cost: Optional[int] = None
    available_funds: Optional[int] = None
    venue_capacity: Optional[int] = None
    ticket_tiers: list[dict[str, Any]] = Field(default_factory=list)
    conservative_occupancy_rate: Optional[int] = None
    neutral_occupancy_rate: Optional[int] = None
    optimistic_occupancy_rate: Optional[int] = None


class FinanceCalculateIn(BaseModel):
    project_id: int
    expected_attendance: Optional[int] = None
    avg_ticket_price: Optional[int] = None
    artist_fee: Optional[int] = None
    venue_cost: Optional[int] = None
    marketing_cost: Optional[int] = None
    production_cost: Optional[int] = None


class FinanceBreakevenIn(BaseModel):
    project_id: int
    target_profit: Optional[int] = 0
    avg_ticket_price: Optional[int] = None
    artist_fee: Optional[int] = None
    venue_cost: Optional[int] = None
    marketing_cost: Optional[int] = None
    production_cost: Optional[int] = None


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


class AgentChatIn(BaseModel):
    project_id: Optional[int] = None
    message: str


class ReportShareIn(BaseModel):
    version_id: Optional[int] = None
    expires_in_days: Optional[int] = 7


class FeasibilityReportIn(BaseModel):
    version_id: Optional[int] = None
    tax_fee_rate: Optional[float] = 0.15
    sponsorship_income: Optional[int] = 0
    merchandise_income: Optional[int] = 0
    use_ai_copy: Optional[bool] = True


class ExternalDataJobIn(BaseModel):
    project_id: Optional[int] = None
    source_type: str
    provider: Optional[str] = 'mcp'
    query: str
    purpose: Optional[str] = ''
    parameters: Optional[dict] = None


class ProjectAnalysisJobIn(BaseModel):
    version_id: Optional[int] = None
    purpose: Optional[str] = ''
    parameters: Optional[dict] = None
