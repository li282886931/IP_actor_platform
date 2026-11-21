from datetime import date
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.collaboration import Proof, RequestIn, StrictModel
from app.services.decision_catalog import METRIC_LABELS

Amount = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Rate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Number = Annotated[float, Field(allow_inf_nan=False)]
Key = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")]
STAGES = ("initiation", "approval", "sponsorship", "ticketing", "execution", "review")


class Thresholds(StrictModel):
    comprehensive_breakeven: Rate = .5
    stop_loss: Rate = .3
    public_sale: Rate = .85
    artist_fee: Rate = .6
    presale: Rate = .5
    large_spend: Amount | None = None
    application_days: int = Field(default=60, ge=0)
    permit_days: int = Field(default=14, ge=0)


class Criterion(StrictModel):
    key: Key
    label: str = Field(min_length=1, max_length=128)
    weight: float = Field(gt=0, allow_inf_nan=False)
    max_score: float = Field(gt=0, allow_inf_nan=False)
    metric: Key | None = None
    method: Literal["manual", "linear_high", "linear_low"] = "manual"
    floor: Number = 0
    ceiling: Number = 1
    source: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def binding(self):
        if self.ceiling <= self.floor:
            raise ValueError("归一上界须大于下界")
        if self.method != "manual" and not self.metric:
            raise ValueError("自动维度须绑定真实指标")
        return self


class ScoreDimension(Criterion):
    category: Literal["income", "risk"]

    @model_validator(mode="after")
    def supported_metric(self):
        if self.metric and self.metric not in METRIC_LABELS:
            raise ValueError("未知决策指标")
        return self


class Predicate(StrictModel):
    field: Key
    op: Literal["gt", "gte", "lt", "lte", "eq"]
    value: Number = 0
    threshold_ref: Literal["comprehensive_breakeven", "stop_loss", "public_sale", "artist_fee", "presale",
                           "large_spend", "application_days", "permit_days"] | None = None

    @model_validator(mode="after")
    def supported_field(self):
        if self.field not in METRIC_LABELS:
            raise ValueError("未知规则指标")
        return self


class Condition(Predicate):
    key: Key
    compare_field: Key | None = None
    applies_when: list[Predicate] = Field(default_factory=list, max_length=10)
    severity: Literal["warning", "veto", "plan"]
    message: str = Field(min_length=1, max_length=1000)
    source: str = Field(default="", max_length=5000)
    risk_category: Key | None = None

    @model_validator(mode="after")
    def comparison(self):
        if self.compare_field and (self.compare_field not in METRIC_LABELS or self.threshold_ref):
            raise ValueError("对比指标须受支持，且不得同时指定阈值引用")
        return self


class RiskCategory(StrictModel):
    key: Key
    label: str = Field(min_length=1)
    verification: str = Field(min_length=1)
    action: str = Field(min_length=1)


class AuxiliaryModel(StrictModel):
    label: str = Field(min_length=1)
    max_total: Literal[100] = 100
    criteria: list[Criterion] = Field(min_length=1, max_length=12)
    source: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def automatic(self):
        if any(c.method == "manual" or c.metric != c.key for c in self.criteria):
            raise ValueError("辅助模型须按同名指标自动归一")
        if len({c.key for c in self.criteria}) != len(self.criteria):
            raise ValueError("辅助指标不得重复")
        return self


class RuleConfig(StrictModel):
    catalog_version: str | None = None
    thresholds: Thresholds = Field(default_factory=Thresholds)
    dimensions: list[ScoreDimension] = Field(default_factory=list, max_length=12)
    conditions: list[Condition] = Field(default_factory=list, max_length=32)
    risk_categories: list[RiskCategory] = Field(default_factory=list, max_length=12)
    auxiliary_models: dict[Literal["brand_match", "city_fit", "artist_benchmark"], AuxiliaryModel] = Field(default_factory=dict)

    @model_validator(mode="after")
    def complete_dimensions(self):
        if self.dimensions and (len(self.dimensions) != 12 or
                                sum(d.category == "income" for d in self.dimensions) != 6):
            raise ValueError("评分卡须为12维，收入6维、成本风险6维；未配置时请保持空列表")
        for rows in (self.dimensions, self.conditions, self.risk_categories):
            if len({d.key for d in rows}) != len(rows):
                raise ValueError("配置项键名不得重复")
        if any(c.risk_category and c.risk_category not in {r.key for r in self.risk_categories} for c in self.conditions):
            raise ValueError("规则风险分类不存在")
        return self


class RuleIn(RequestIn):
    name: str = Field(min_length=1, max_length=255)
    source: str = Field(min_length=1, max_length=5000)
    config: RuleConfig
    reviewed: bool = False
    parent_id: int | None = None


class DecisionInputs(Proof):
    scoring_mode: Literal["manual", "auto"] = "manual"
    total_cost: Amount | None = None
    full_ticket_gross: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    net_ticket_rate: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] | None = None
    sponsorship: Amount | None = None
    subsidy: Amount | None = None
    expected_occupancy: Rate | None = None
    artist_fee: Amount | None = None
    permit_received: bool | None = None
    nonrefundable_spend: Amount | None = None
    stop_loss_amount: Amount | None = None
    artist_misconduct: bool | None = None
    foreign_artist: bool | None = None
    foreign_approval: bool | None = None
    public_sale_ratio: Rate | None = None
    presale_ratio: Rate | None = None
    cost_overrun_ratio: Number | None = None
    weather_risk: Rate | None = None
    reputation_risk: Rate | None = None
    schedule_conflict: bool | None = None
    demand_verified: bool | None = None
    ticket_price: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    willingness_price: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    audience_match_ratio: Rate | None = None
    comparable_artist_fee: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    fan_growth_ratio: Annotated[float, Field(ge=-1, allow_inf_nan=False)] | None = None
    supplier_quotes_verified: bool | None = None
    available_funds: Amount | None = None
    sponsorship_verified: bool | None = None
    subsidy_verified: bool | None = None
    contracted_sponsorship: Amount | None = None
    days_until_show: int | None = None
    application_submitted: bool | None = None
    foreign_approval_verified: bool | None = None
    copyright_authorized: bool | None = None
    safety_verified: bool | None = None
    insurance_verified: bool | None = None
    scores: dict[str, Amount] = Field(default_factory=dict)
    source: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def bounds(self):
        if self.scoring_mode == "auto" and self.scores:
            raise ValueError("自动评分不接受人工得分覆盖")
        if self.artist_fee is not None and self.total_cost is not None and self.artist_fee > self.total_cost:
            raise ValueError("艺人费用不得大于总成本")
        if self.nonrefundable_spend is not None and self.total_cost is not None and self.nonrefundable_spend > self.total_cost:
            raise ValueError("不可退支出不得大于总成本")
        return self


class ReportIn(RequestIn):
    rule_version_id: int
    project_version_id: int | None = None
    inputs: DecisionInputs


class ReviewIn(RequestIn):
    evidence_ids: list[int] = Field(min_length=1)
    note: str = Field(min_length=1, max_length=5000)


class ActualsIn(RequestIn):
    actual_attendance: int | None = Field(default=None, ge=0)
    actual_revenue: int | None = Field(default=None, ge=0)
    actual_cost: int | None = Field(default=None, ge=0)
    notes: str = Field(default="", max_length=5000)
    evidence_ids: list[int] = Field(default_factory=list)
    verified: bool = False


class CalibrateIn(RequestIn):
    attribution: str = Field(min_length=1, max_length=5000)
    config: RuleConfig


class StageIn(RequestIn):
    stage: Literal["approval", "sponsorship", "ticketing", "execution", "review"]
    report_id: int
    evidence_ids: list[int] = Field(default_factory=list)
    stop_loss_plan: str = Field(default="", max_length=5000)


class Incremental(Proof):
    avoided_projects: int = Field(default=0, ge=0)
    potential_loss_per_project: Amount | None = None
    baseline_occupancy: Rate | None = None
    optimized_occupancy: Rate | None = None
    full_ticket_gross: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    net_ticket_rate: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] | None = None
    saved_hours: Amount | None = None
    hourly_cost: Amount | None = None
    supplier_savings: Amount | None = None
    share_rate: Rate | None = None
    attribution: str = ""


class Sponsorship(Proof):
    investment: Amount | None = None
    onsite_exposures: Amount | None = None
    media_exposures: Amount | None = None
    onsite_cpm: Amount | None = None
    media_cpm: Amount | None = None
    rights_value: Amount | None = None
    actual_sales_profit: Amount | None = None
    target_audience: str = ""
    audience_age: str = ""
    audience_city: str = ""
    purchasing_power: str = ""
    interests: str = ""
    deliverables: str = ""


class Cashflow(StrictModel):
    date: date
    amount: Number


class Investment(Proof):
    cashflows: list[Cashflow] = Field(default_factory=list, max_length=300)
    invested_amount: Amount | None = None
    supervised_balance: Amount | None = None
    stop_loss_amount: Amount | None = None
    exit_plan: str = ""
    due_diligence: str = ""
    custody_reference: str = ""
    profit_share: Rate | None = None


class Asset(Proof):
    city: str = Field(min_length=1)
    venue_id: int | None = None
    category: Literal["venue", "scenic", "stadium"] = "venue"
    capacity: int | None = Field(default=None, gt=0)
    idle_days: int | None = Field(default=None, ge=0)
    activation_cost: Amount | None = None
    operating_income: Amount | None = None
    operating_cost: Amount | None = None
    suitable_genres: list[str] = Field(default_factory=list)
    operating_plan: str = ""


class Impact(Proof):
    city: str = Field(min_length=1)
    period: str = Field(min_length=1)
    subsidy: Amount | None = None
    visitor_spend: Amount | None = None
    consumption_coefficient: Amount | None = None
    coefficient_source: str = ""
    attributable_revenue: Amount | None = None


class ArtistPost(StrictModel):
    content: str = Field(min_length=1, max_length=5000)
    post_type: Literal["update", "work", "live", "support"] = "update"
    scheduled_at: date | None = None
    link: str = ""


class ArtistMetrics(Proof):
    observed_at: date
    city: str = Field(min_length=1)
    fan_count: int | None = Field(default=None, ge=0)
    heat: Amount | None = None
    ticket_gross: Amount | None = None
    artist_fee: Amount | None = None
    sponsorship: Amount | None = None
    merchandise: Amount | None = None
    live_income: Amount | None = None


class Wishlist(StrictModel):
    year: int = Field(ge=2020, le=2100)
    show_ids: list[int] = Field(default_factory=list, max_length=100)
    note: str = Field(default="", max_length=2000)


class Checkin(StrictModel):
    show_id: int
    attended_at: date
    content: str = Field(min_length=1, max_length=2000)
    public: bool = False


class Comment(StrictModel):
    post_id: int
    content: str = Field(min_length=1, max_length=2000)


class RecordIn(RequestIn):
    kind: Literal["incremental", "sponsorship", "investment", "asset", "impact", "artist_post",
                  "artist_metrics", "wishlist", "checkin", "comment", "brand_match", "city_fit", "artist_benchmark"]
    record_key: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    project_id: int | None = None
    revision: int | None = Field(default=None, ge=1)
    payload: dict


class AuxiliaryInputs(Proof):
    rule_version_id: int = Field(gt=0)
    metrics: dict[Key, Amount] = Field(default_factory=dict)
    source: str = Field(min_length=1, max_length=5000)


RECORD_MODELS = {"brand_match": AuxiliaryInputs, "city_fit": AuxiliaryInputs, "artist_benchmark": AuxiliaryInputs,
                 "incremental": Incremental, "sponsorship": Sponsorship, "investment": Investment,
                 "asset": Asset, "impact": Impact, "artist_post": ArtistPost, "artist_metrics": ArtistMetrics,
                 "wishlist": Wishlist, "checkin": Checkin, "comment": Comment}


class CityIn(RequestIn):
    name: str = Field(min_length=1, max_length=128)
    population: int | None = Field(default=None, ge=0)
    annual_shows: int | None = Field(default=None, ge=0)
    market_revenue: Amount | None = None
    genres: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1, max_length=5000)
    revision: int | None = Field(default=None, ge=1)


class ScenarioIn(StrictModel):
    capacity: int | None = Field(default=None, gt=0)
    base_price: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    base_occupancy: Rate | None = None
    net_ticket_rate: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] | None = None
    price_elasticity: Annotated[float, Field(ge=-10, le=0, allow_inf_nan=False)] | None = None
    prices: list[Annotated[float, Field(gt=0, allow_inf_nan=False)]] = Field(default_factory=list, max_length=100)
    show_count: int | None = Field(default=None, ge=1, le=1000)
    shared_cost: Amount | None = None
    cost_per_show: Amount | None = None
    sponsorship_per_show: Amount | None = None
    subsidy_per_show: Amount | None = None
    cancellation_nonrefundable: Amount | None = None
    insurance_recovery: Amount | None = None
    cost_actual: Amount | None = None
    cost_budget: Amount | None = None
    source: str = Field(default="", max_length=5000)
