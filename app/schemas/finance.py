from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class ShowCalculationIn(BaseModel):
    project_id: int
    venue_capacity: Optional[int] = None
    expected_attendance: Optional[int] = None
    avg_ticket_price: Optional[int] = None
    artist_fee: Optional[int] = None
    venue_cost: Optional[int] = None
    marketing_cost: Optional[int] = None
    production_cost: Optional[int] = None
    security_cost: Optional[int] = None
    travel_cost: Optional[int] = None
    accommodation_cost: Optional[int] = None
    insurance_cost: Optional[int] = None
    approval_cost: Optional[int] = None
    contingency_cost: Optional[int] = None
    tax_fee_rate: Optional[float] = 0
    ticketing_fee_rate: Optional[float] = 0
    sponsorship_income: Optional[int] = 0
    merchandise_income: Optional[int] = 0
    target_profit: Optional[int] = 0
    conservative_occupancy_rate: Optional[int] = 60
    neutral_occupancy_rate: Optional[int] = 80
    optimistic_occupancy_rate: Optional[int] = 95


class FeasibilityReportIn(BaseModel):
    version_id: Optional[int] = None
    tax_fee_rate: Optional[float] = 0.15
    sponsorship_income: Optional[int] = 0
    merchandise_income: Optional[int] = 0
    use_ai_copy: Optional[bool] = True
