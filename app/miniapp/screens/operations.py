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


def _tour_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    plans = db.query(TourPlan).filter(
        TourPlan.tenant_id == context.tenant_id,
    ).order_by(TourPlan.id.desc()).all()
    plan_ids = [plan.id for plan in plans]
    stops = (
        db.query(TourStop)
        .filter(TourStop.tour_plan_id.in_(plan_ids))
        .order_by(TourStop.sequence.asc(), TourStop.id.asc())
        .all()
        if plan_ids else []
    )
    stops_by_plan = {}
    for stop in stops:
        stops_by_plan.setdefault(stop.tour_plan_id, []).append(stop)

    if screen_id == "S61":
        items = [
            {
                "id": f"tour-plan-{plan.id}",
                "entity_type": "tour_plan",
                "title": plan.name,
                "description": f"{len(stops_by_plan.get(plan.id, []))} 个站点",
                "status": plan.status,
                "context": {"tour_plan_id": plan.id},
            }
            for plan in plans
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "巡演计划", "subtitle": "当前客户空间真实巡演", "highlight": str(len(plans))},
            "items": items,
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无巡演计划", "创建巡演计划后可查看路线") if not items else None,
        }

    selected_stops = stops
    if screen_id == "S63":
        project = _get_project(db, context)
        selected_stops = [stop for stop in stops if stop.project_id == project.id]
    items = [
        {
            "id": f"tour-stop-{stop.id}",
            "entity_type": "tour_stop",
            "title": stop.city,
            "description": stop.scheduled_at or None,
            "status": stop.status,
            "value": str(stop.sequence),
            "context": {
                "tour_plan_id": stop.tour_plan_id,
                "tour_stop_id": stop.id,
                "project_id": stop.project_id,
                "venue_id": stop.venue_id,
                "sequence": stop.sequence,
                "scheduled_at": stop.scheduled_at,
            },
        }
        for stop in selected_stops
    ]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": "巡演站点" if screen_id == "S63" else "巡演路线",
            "subtitle": "按站点顺序展示",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无巡演站点", "为巡演计划添加真实站点") if not items else None,
    }


def _actual_payload(actual: ProjectActual) -> dict:
    return {
        "id": actual.id,
        "project_id": actual.project_id,
        "actual_attendance": actual.actual_attendance,
        "actual_revenue": actual.actual_revenue,
        "actual_cost": actual.actual_cost,
        "actual_profit": actual.actual_profit,
        "status": actual.status,
        "notes": actual.notes,
        "settled_at": actual.settled_at.isoformat() if actual.settled_at else None,
    }


def _project_review_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    project = _get_project(db, context)
    if screen_id == "S64":
        snapshot = db.query(TicketingSnapshot).filter(
            TicketingSnapshot.project_id == project.id,
        ).order_by(
            TicketingSnapshot.captured_at.desc(),
            TicketingSnapshot.id.desc(),
        ).first()
        payload = ({
            "id": snapshot.id,
            "project_id": snapshot.project_id,
            "captured_at": snapshot.captured_at.isoformat(),
            "sold_count": snapshot.sold_count,
            "gross_revenue": snapshot.gross_revenue,
            "source": snapshot.source,
        } if snapshot else None)
        current_version = _get_current_version(db, project)
        finance_result = (
            current_version.finance_result
            if current_version and isinstance(current_version.finance_result, dict)
            else {}
        )
        forecast = (finance_result.get("scenarios") or {}).get("neutral")
        return {
            "screen_id": screen_id,
            "summary": {
                "title": f"{project.name}售票进度",
                "subtitle": "最新售票快照",
                "highlight": str(snapshot.sold_count) if snapshot else None,
            },
            "items": ([{
                "id": f"ticketing-snapshot-{snapshot.id}",
                "entity_type": "ticketing_snapshot",
                "title": f"已售 {snapshot.sold_count}",
                "description": snapshot.captured_at.isoformat(),
                "value": str(snapshot.gross_revenue) if snapshot.gross_revenue is not None else None,
                "context": payload,
            }] if snapshot else []),
            "options": {
                "snapshot": payload,
                "ticketing_loop": {
                    "forecast_attendance": forecast.get("attendance") if forecast else None,
                    "current_sold_count": snapshot.sold_count if snapshot else None,
                    "gross_revenue": snapshot.gross_revenue if snapshot else None,
                    "attendance_variance": (
                        snapshot.sold_count - forecast["attendance"]
                        if snapshot and forecast and forecast.get("attendance") is not None
                        else None
                    ),
                    "source": snapshot.source if snapshot else None,
                },
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无售票快照", "同步售票数据后可查看进度") if not snapshot else None,
        }

    actual = db.query(ProjectActual).filter(
        ProjectActual.project_id == project.id,
    ).first()
    actual_data = _actual_payload(actual) if actual else None
    if screen_id == "S65":
        items = [
            {
                "id": f"actual-{field_name}",
                "entity_type": "project_actual",
                "title": title,
                "value": str(value),
                "context": {"field": field_name, "project_actual_id": actual.id},
            }
            for field_name, title, value in (
                ("actual_attendance", "实际到场", actual.actual_attendance if actual else None),
                ("actual_revenue", "实际收入", actual.actual_revenue if actual else None),
                ("actual_cost", "实际成本", actual.actual_cost if actual else None),
                ("actual_profit", "实际利润", actual.actual_profit if actual else None),
            )
            if value is not None
        ]
        return {
            "screen_id": screen_id,
            "summary": {
                "title": f"{project.name}实际结果",
                "subtitle": actual.notes if actual else None,
                "highlight": actual.status if actual else None,
            },
            "items": items,
            "options": {
                "actual": actual_data,
                "actuals_summary": {
                    "actual_attendance": actual.actual_attendance if actual else None,
                    "actual_revenue": actual.actual_revenue if actual else None,
                    "actual_cost": actual.actual_cost if actual else None,
                    "actual_profit": actual.actual_profit if actual else None,
                    "status": actual.status if actual else None,
                    "notes": actual.notes if actual else None,
                },
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无实际结果", "完成结算后录入实际结果") if not actual else None,
        }

    current_version = _get_current_version(db, project)
    finance_result = (
        current_version.finance_result
        if current_version and isinstance(current_version.finance_result, dict)
        else {}
    )
    forecast = (finance_result.get("scenarios") or {}).get("neutral")
    variance = None
    if actual and forecast:
        actual_values = {
            "attendance": actual.actual_attendance,
            "revenue": actual.actual_revenue,
            "cost": actual.actual_cost,
            "profit": actual.actual_profit,
        }
        if all(actual_values[key] is not None and forecast.get(key) is not None for key in actual_values):
            variance = {
                key: actual_values[key] - forecast[key]
                for key in actual_values
            }
    items = [
        {
            "id": f"variance-{key}",
            "entity_type": "project_variance",
            "title": label,
            "value": str(value),
            "context": {
                "metric": key,
                "forecast": forecast[key],
                "actual": actual_data[f"actual_{key}"],
            },
        }
        for key, label in (
            ("attendance", "到场差异"),
            ("revenue", "收入差异"),
            ("cost", "成本差异"),
            ("profit", "利润差异"),
        )
        for value in ([variance[key]] if variance else [])
    ]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}项目复盘",
            "subtitle": "中性预测与实际结果对比",
            "highlight": actual.status if actual else None,
        },
        "items": items,
        "options": {
            "forecast": forecast,
            "actual": actual_data,
            "variance": variance,
            "calibration_loop": {
                "forecast_profit": forecast.get("profit") if forecast else None,
                "actual_profit": actual.actual_profit if actual else None,
                "forecast_attendance": forecast.get("attendance") if forecast else None,
                "actual_attendance": actual.actual_attendance if actual else None,
                "profit_variance": variance.get("profit") if variance else None,
                "notes": actual.notes if actual else None,
            },
        },
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无实际结果", "录入实际结果后才能计算预测差异")
            if not actual else
            _empty_state("暂无可比预测", "当前版本缺少中性情景测算")
            if not forecast else
            _empty_state("实际结果不完整", "补齐实际到场、收入、成本和利润")
            if not variance else None
        ),
    }
