from datetime import datetime
from typing import Annotated, Any, Literal, Optional

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


NonNegativeAmount = Annotated[int, Field(ge=0)]
DeductionRate = Annotated[float, Field(ge=0, lt=1, allow_inf_nan=False)]
OccupancyRate = Annotated[int, Field(ge=0, le=100)]


class ShowCalculationIn(BaseModel):
    project_id: int
    venue_capacity: Optional[Annotated[int, Field(gt=0)]] = None
    expected_attendance: Optional[NonNegativeAmount] = None
    avg_ticket_price: Optional[Annotated[int, Field(gt=0)]] = None
    artist_fee: Optional[NonNegativeAmount] = None
    venue_cost: Optional[NonNegativeAmount] = None
    marketing_cost: Optional[NonNegativeAmount] = None
    production_cost: Optional[NonNegativeAmount] = None
    security_cost: Optional[NonNegativeAmount] = None
    travel_cost: Optional[NonNegativeAmount] = None
    accommodation_cost: Optional[NonNegativeAmount] = None
    insurance_cost: Optional[NonNegativeAmount] = None
    approval_cost: Optional[NonNegativeAmount] = None
    contingency_cost: Optional[NonNegativeAmount] = None
    available_funds: Optional[NonNegativeAmount] = None
    tax_fee_rate: Optional[DeductionRate] = None
    ticketing_fee_rate: Optional[DeductionRate] = None
    sponsorship_income: Optional[NonNegativeAmount] = 0
    merchandise_income: Optional[NonNegativeAmount] = 0
    target_profit: Optional[NonNegativeAmount] = 0
    conservative_occupancy_rate: Optional[OccupancyRate] = 60
    neutral_occupancy_rate: Optional[OccupancyRate] = 80
    optimistic_occupancy_rate: Optional[OccupancyRate] = 95

    @model_validator(mode="after")
    def validate_business_bounds(self):
        if self.venue_capacity is not None and self.expected_attendance is not None:
            if self.expected_attendance > self.venue_capacity:
                raise ValueError("预计人数不得超过场馆容量")
        if (self.tax_fee_rate or 0) + (self.ticketing_fee_rate or 0) >= 1:
            raise ValueError("税费与票务服务费合计必须小于 100%")
        rates = [
            self.conservative_occupancy_rate if self.conservative_occupancy_rate is not None else 60,
            self.neutral_occupancy_rate if self.neutral_occupancy_rate is not None else 80,
            self.optimistic_occupancy_rate if self.optimistic_occupancy_rate is not None else 95,
        ]
        if rates != sorted(rates):
            raise ValueError("情景上座率须满足保守 ≤ 中性 ≤ 乐观")
        return self


class FeasibilityReportIn(BaseModel):
    version_id: Optional[int] = None
    tax_fee_rate: Optional[DeductionRate] = None
    sponsorship_income: Optional[NonNegativeAmount] = 0
    merchandise_income: Optional[NonNegativeAmount] = 0
    use_ai_copy: Optional[bool] = True
