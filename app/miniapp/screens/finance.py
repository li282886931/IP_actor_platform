import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Artist, AgentPermission, AlertEvent, Assumption, Decision, DocumentParseJob,
    Evidence, Fact, Gate, Project, ProjectActual, ProjectAnalysisJob,
    ProjectWorkPlan, ProjectVersion, MemberInvitation, Notification,
    PrivacyConsent, ReportShare, Risk, Show, Task, TicketingSnapshot, Tenant,
    TenantMember, TourPlan, TourStop, User, UserSetting, Venue,
)
from app.schemas import MiniappScreenData
from app.services import serialize_project, serialize_user, serialize_version
from .common import (
    ScreenRequestContext, _empty_state, _get_current_version, _get_project,
    _screen_context, _user_names,
)


def _finance_input_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else None
    )
    missing_fields = (
        finance_result.get("missing_fields", [])
        if finance_result
        else ["current_version.finance_result"]
    )
    response_context = _screen_context(context)
    response_context["version_id"] = current_version.id if current_version else None
    neutral = (finance_result.get("scenarios") or {}).get("neutral") if finance_result else None
    return {
        "screen_id": "S25",
        "summary": {
            "title": f"{project.name}财务测算",
            "subtitle": "测算结果来自当前项目版本",
            "highlight": finance_result.get("status") if finance_result else "pending_input",
        },
        "items": [],
        "options": {
            "project": serialize_project(project),
            "finance_result": finance_result,
            "missing_fields": missing_fields,
            "finance_cockpit": {
                "scenarios": finance_result.get("scenarios") if finance_result else {},
                "neutral_profit": (
                    finance_result.get("net_profit")
                    if finance_result and finance_result.get("net_profit") is not None
                    else neutral.get("profit") if neutral else None
                ),
                "breakeven_attendance": finance_result.get("breakeven_attendance") if finance_result else None,
                "total_cost": finance_result.get("total_cost") if finance_result else None,
                "available_funds": project.available_funds,
                "maximum_funding_gap": (
                    finance_result.get("funding_gap")
                    if finance_result and finance_result.get("funding_gap") is not None
                    else max(finance_result["total_cost"] - project.available_funds, 0)
                    if finance_result and finance_result.get("total_cost") is not None and project.available_funds is not None
                    else None
                ),
                "status": finance_result.get("status") if finance_result else "pending_input",
                "combination": {
                    "建议最低票价": finance_result.get("recommended_min_ticket_price") if finance_result else None,
                    "目标利润票价": finance_result.get("recommended_target_ticket_price") if finance_result else None,
                    "利润率": finance_result.get("profit_margin") if finance_result else None,
                    "非票收入": finance_result.get("non_ticket_income") if finance_result else None,
                },
                "missing_fields": missing_fields,
            },
        },
        "context": response_context,
        "empty_state": {
            "title": "财务参数待补充",
            "description": "补齐必要参数后才能生成测算结果",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


FINANCE_SCENARIOS = {
    "finance_conservative": ("S28", "conservative", "保守情景"),
    "finance_neutral": ("S29", "neutral", "中性情景"),
    "finance_optimistic": ("S30", "optimistic", "乐观情景"),
}


def _finance_scenario_screen(
    db: Session,
    context: ScreenRequestContext,
    provider_key: str,
) -> dict:
    screen_id, scenario_name, title = FINANCE_SCENARIOS[provider_key]
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else {}
    )
    scenario = (finance_result.get("scenarios") or {}).get(scenario_name)
    missing_fields = finance_result.get("missing_fields") or []
    if not scenario and not missing_fields:
        missing_fields = [f"finance_result.scenarios.{scenario_name}"]
    response_context = _screen_context(context)
    response_context["version_id"] = current_version.id if current_version else None
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{title}",
            "subtitle": "结果来自当前项目版本",
            "highlight": finance_result.get("status") or "pending_input",
        },
        "items": [
            {
                "id": f"{scenario_name}-{key}",
                "entity_type": "finance_metric",
                "title": label,
                "value": str(scenario[key]),
                "context": {"metric": key, "scenario": scenario_name},
            }
            for key, label in (
                ("attendance", "预计人数"),
                ("revenue", "预计收入"),
                ("cost", "总成本"),
                ("profit", "预计利润"),
            )
        ] if scenario else [],
        "options": {
            "scenario_name": scenario_name,
            "scenario": scenario,
            "missing_fields": missing_fields,
        },
        "context": response_context,
        "empty_state": {
            "title": "情景测算参数不完整",
            "description": "补齐财务参数后再查看该情景",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if not scenario else None,
    }


def _ticket_tiers_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    ticket_tiers = project.ticket_tiers or []
    missing_fields = [] if ticket_tiers else ["ticket_tiers"]
    return {
        "screen_id": "S26",
        "summary": {
            "title": f"{project.name}票价结构",
            "subtitle": "票档价格和预计销售占比",
            "highlight": str(len(ticket_tiers)) if ticket_tiers else None,
        },
        "items": [
            {
                "id": f"ticket-tier-{index}",
                "entity_type": "ticket_tier",
                "title": tier.get("name") or f"票档 {index + 1}",
                "description": (
                    f"预计占比 {tier.get('share')}%"
                    if tier.get("share") is not None
                    else None
                ),
                "value": str(tier.get("price")) if tier.get("price") is not None else None,
                "context": {"index": index, "ticket_tier": tier},
            }
            for index, tier in enumerate(ticket_tiers)
        ],
        "options": {
            "ticket_tiers": ticket_tiers,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "票档待补充",
            "description": "添加真实票档后才能展示票价结构",
            "action": {
                "label": "补充票档",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


def _cost_breakdown_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        ("artist_fee", "艺人费用"),
        ("venue_cost", "场馆费用"),
        ("marketing_cost", "宣发费用"),
        ("production_cost", "制作费用"),
    )
    present_costs = [
        (field_name, label, getattr(project, field_name))
        for field_name, label in cost_fields
        if getattr(project, field_name) is not None
    ]
    missing_fields = [
        field_name
        for field_name, _ in cost_fields
        if getattr(project, field_name) is None
    ]
    return {
        "screen_id": "S27",
        "summary": {
            "title": f"{project.name}成本拆分",
            "subtitle": "成本项来自项目已保存参数",
            "highlight": None,
        },
        "items": [
            {
                "id": field_name,
                "entity_type": "cost_item",
                "title": label,
                "value": str(value),
                "context": {"field": field_name},
            }
            for field_name, label, value in present_costs
        ],
        "options": {
            "missing_fields": missing_fields,
            "total_cost": (
                sum(value for _, _, value in present_costs)
                if not missing_fields
                else None
            ),
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "成本参数待补充",
            "description": "缺失成本不会按零计算",
            "action": {
                "label": "补充成本",
                "target_screen": "S16",
            },
        } if missing_fields else None,
    }


def _breakeven_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
    )
    missing_fields = [
        field_name
        for field_name in cost_fields
        if getattr(project, field_name) is None
    ]
    if not project.avg_ticket_price:
        missing_fields.append("avg_ticket_price")
    total_cost = (
        sum(getattr(project, field_name) for field_name in cost_fields)
        if not missing_fields
        else None
    )
    breakeven_attendance = (
        (total_cost + project.avg_ticket_price - 1) // project.avg_ticket_price
        if total_cost is not None
        else None
    )
    return {
        "screen_id": "S31",
        "summary": {
            "title": f"{project.name}保本测算",
            "subtitle": "由真实成本和平均票价计算",
            "highlight": str(breakeven_attendance) if breakeven_attendance is not None else None,
        },
        "items": [{
            "id": "breakeven-attendance",
            "entity_type": "finance_metric",
            "title": "保本人数",
            "value": str(breakeven_attendance),
            "context": {"metric": "breakeven_attendance"},
        }] if breakeven_attendance is not None else [],
        "options": {
            "total_cost": total_cost,
            "avg_ticket_price": project.avg_ticket_price,
            "breakeven_attendance": breakeven_attendance,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "无法计算保本人数",
            "description": "成本或平均票价尚未补齐",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }


def _funding_gap_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
    )
    missing_fields = [
        field_name
        for field_name in cost_fields
        if getattr(project, field_name) is None
    ]
    if project.available_funds is None:
        missing_fields.append("available_funds")
    total_cost = (
        sum(getattr(project, field_name) for field_name in cost_fields)
        if not any(field_name in missing_fields for field_name in cost_fields)
        else None
    )
    funding_gap = (
        max(total_cost - project.available_funds, 0)
        if total_cost is not None and project.available_funds is not None
        else None
    )
    return {
        "screen_id": "S33",
        "summary": {
            "title": f"{project.name}资金缺口",
            "subtitle": "由总成本减去可用资金计算",
            "highlight": str(funding_gap) if funding_gap is not None else None,
        },
        "items": [{
            "id": "funding-gap",
            "entity_type": "finance_metric",
            "title": "资金缺口",
            "value": str(funding_gap),
            "context": {"metric": "funding_gap"},
        }] if funding_gap is not None else [],
        "options": {
            "total_cost": total_cost,
            "available_funds": project.available_funds,
            "funding_gap": funding_gap,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "无法计算资金缺口",
            "description": "成本或可用资金尚未补齐",
            "action": {
                "label": "补充参数",
                "target_screen": "S15",
            },
        } if missing_fields else None,
    }


def _finance_sensitivity_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    cost_fields = (
        "artist_fee",
        "venue_cost",
        "marketing_cost",
        "production_cost",
    )
    rate_fields = {
        "conservative": "conservative_occupancy_rate",
        "neutral": "neutral_occupancy_rate",
        "optimistic": "optimistic_occupancy_rate",
    }
    missing_fields = [
        field_name
        for field_name in cost_fields
        if getattr(project, field_name) is None
    ]
    if project.venue_capacity is None:
        missing_fields.append("venue_capacity")
    for field_name in rate_fields.values():
        if getattr(project, field_name) is None:
            missing_fields.append(field_name)

    ticket_tiers = project.ticket_tiers or []
    valid_tiers = [
        tier
        for tier in ticket_tiers
        if tier.get("price") is not None and tier.get("share") is not None
    ]
    total_share = sum(tier["share"] for tier in valid_tiers)
    if not valid_tiers or total_share <= 0 or len(valid_tiers) != len(ticket_tiers):
        missing_fields.append("ticket_tiers")

    weighted_ticket_price = (
        sum(tier["price"] * tier["share"] for tier in valid_tiers) / total_share
        if "ticket_tiers" not in missing_fields
        else None
    )
    total_cost = (
        sum(getattr(project, field_name) for field_name in cost_fields)
        if not any(field_name in missing_fields for field_name in cost_fields)
        else None
    )
    scenarios = {}
    if not missing_fields:
        for scenario_name, field_name in rate_fields.items():
            occupancy_rate = getattr(project, field_name)
            attendance = round(project.venue_capacity * occupancy_rate / 100)
            revenue = round(attendance * weighted_ticket_price)
            scenarios[scenario_name] = {
                "occupancy_rate": occupancy_rate,
                "attendance": attendance,
                "revenue": revenue,
                "profit": revenue - total_cost,
            }
    return {
        "screen_id": "S32",
        "summary": {
            "title": f"{project.name}敏感性分析",
            "subtitle": "仅调整上座率，票价和成本保持不变",
            "highlight": None,
        },
        "items": [
            {
                "id": f"sensitivity-{scenario_name}",
                "entity_type": "finance_scenario",
                "title": scenario_name,
                "value": str(scenario["profit"]),
                "context": {"scenario": scenario_name, **scenario},
            }
            for scenario_name, scenario in scenarios.items()
        ],
        "options": {
            "venue_capacity": project.venue_capacity,
            "weighted_ticket_price": weighted_ticket_price,
            "total_cost": total_cost,
            "scenarios": scenarios,
            "missing_fields": missing_fields,
        },
        "context": _screen_context(context),
        "empty_state": {
            "title": "无法生成敏感性分析",
            "description": "容量、票档、成本或上座率尚未补齐",
            "action": {
                "label": "补充参数",
                "target_screen": "S25",
            },
        } if missing_fields else None,
    }
