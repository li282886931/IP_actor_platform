from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RequestIn(StrictModel):
    request_key: str = Field(min_length=1, max_length=128)


class GrantIn(RequestIn):
    project_id: int
    user_id: int
    duties: list[Literal["collaborate", "finance", "manage"]] = Field(default_factory=lambda: ["collaborate"])
    revision: int | None = Field(default=None, ge=1)


class ActionIn(RequestIn):
    revision: int = Field(ge=1)
    action: Literal["share", "edit", "withdraw", "reply", "decline", "confirm", "deliver",
                    "approve", "return", "dispute", "start", "submit"] = "withdraw"
    note: str = Field(default="", max_length=5000)
    payload: dict | None = None


class ItemIn(RequestIn):
    kind: Literal["invitation", "brand_demand", "rights", "supplement", "official_result",
                  "impact", "investment", "profile_change", "incident", "task"]
    title: str = Field(min_length=1, max_length=255)
    project_id: int | None = None
    version_id: int | None = None
    recipient_id: int
    payload: dict


class Proof(StrictModel):
    evidence_ids: list[int] = Field(default_factory=list, max_length=100)


class Invitation(Proof):
    purpose: str = Field(min_length=1)
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def check_interval(self):
        if self.start is not None or self.end is not None:
            validate_interval(self.start, self.end)
        return self


class BrandDemand(Proof):
    goal: Literal["曝光", "互动", "转化"]
    city: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    resources: str = Field(min_length=1)
    budget: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class Rights(Proof):
    deliverables: str = Field(min_length=1)
    due_date: str = Field(min_length=1)
    acceptance: str = Field(min_length=1)
    amount: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class Supplement(Proof):
    materials: str = Field(min_length=1)
    due_date: str = Field(min_length=1)


class OfficialResult(Proof):
    authority: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    recorded_at: datetime
    result: str = Field(min_length=1)

    @field_validator("source_url")
    @classmethod
    def source_is_http(cls, value):
        if not value.startswith(("https://", "http://")):
            raise ValueError("来源必须为 HTTP/HTTPS 地址")
        return value


class Impact(OfficialResult):
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)
    region: str = Field(min_length=1)
    period: str = Field(min_length=1)


class Investment(Proof):
    conditions: str = Field(min_length=1)
    amount: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class ProfileChange(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tags: str | None = Field(default=None, max_length=255)
    profile: dict | None = None

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("请填写修改内容")
        return self


class Incident(Proof):
    source_type: Literal["job", "quality"]
    source_id: int
    instructions: str = Field(min_length=1)


class TaskPayload(Proof):
    instructions: str = Field(min_length=1)
    due_date: str = ""


PAYLOAD_MODELS = {"invitation": Invitation, "brand_demand": BrandDemand, "rights": Rights,
                  "supplement": Supplement, "official_result": OfficialResult, "impact": Impact,
                  "investment": Investment, "profile_change": ProfileChange,
                  "incident": Incident, "task": TaskPayload}


def validate_interval(start, end):
    if not start or not end or start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("起止时间必须含时区，结束须晚于开始")


class Availability(StrictModel):
    start: datetime
    end: datetime
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def check_interval(self):
        validate_interval(self.start, self.end)
        return self


class Focus(StrictModel):
    cities: list[str] = Field(default_factory=list, max_length=30)
    goals: list[Literal["曝光", "互动", "转化"]] = Field(default_factory=list)
    risk_levels: list[Literal["low", "medium", "high"]] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list, max_length=30)


class Favorite(StrictModel):
    target_type: Literal["artist", "city", "show"]
    target_id: str = Field(min_length=1, max_length=128)


class PersonalIn(RequestIn):
    type: Literal["focus", "favorite", "availability"]
    record_key: str = Field(default="default", min_length=1, max_length=128)
    revision: int | None = Field(default=None, ge=1)
    remove: bool = False
    payload: dict = Field(default_factory=dict)


class ReservationIn(RequestIn):
    order_id: int
    action: Literal["cancel", "restore"]


class ShowUpdateIn(RequestIn):
    project_id: int
    show_id: int
    confirmed: bool
    changes: dict[str, str]


class BindingIn(RequestIn):
    user_id: int
    artist_id: int
