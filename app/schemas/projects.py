from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.decisions import AgentReadIn


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


class ProjectWorkEventIn(BaseModel):
    event_type: str
    business_key: str
    payload: Optional[dict] = None
    source_asset_id: Optional[int] = None
    alert_event_id: Optional[int] = None
    idempotency_key: str


class ProjectAnalysisJobIn(BaseModel):
    version_id: Optional[int] = None
    purpose: Optional[str] = ''
    parameters: Optional[dict] = None
    reads: list[AgentReadIn] = Field(default_factory=list, max_length=4)
