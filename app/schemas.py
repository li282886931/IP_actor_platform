from typing import Optional

from pydantic import BaseModel, ConfigDict


class ArtistOut(BaseModel):
    id: int
    name: str
    tags: Optional[str]
    heat_score: int
    fan_count: Optional[str]
    risk_level: int

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

    model_config = ConfigDict(from_attributes=True)


class AIGenerateIn(BaseModel):
    type: str
    show_name: Optional[str] = ''
    artist: Optional[str] = ''
    city: Optional[str] = ''


class OrderIn(BaseModel):
    name: str
    phone: str


class WebLoginIn(BaseModel):
    account: str
    name: Optional[str] = ''


class ProjectIn(BaseModel):
    name: str
    type: Optional[str] = 'concert'
    artist_name: Optional[str] = ''
    city: Optional[str] = ''
    venue: Optional[str] = ''
    schedule: Optional[str] = ''
    expected_attendance: Optional[int] = None
    avg_ticket_price: Optional[int] = None
    artist_fee: Optional[int] = None
    venue_cost: Optional[int] = None
    marketing_cost: Optional[int] = None
    production_cost: Optional[int] = None


class FinanceCalculateIn(BaseModel):
    project_id: int
    expected_attendance: Optional[int] = None
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
