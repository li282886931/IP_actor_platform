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


def _tenant_task_rows(db: Session, tenant_id: int):
    return db.query(Task, Project.name, User.name).join(
        Project,
        Task.project_id == Project.id,
    ).outerjoin(
        User,
        Task.assignee_id == User.id,
    ).filter(
        Project.tenant_id == tenant_id,
    ).order_by(Task.id.desc()).all()


def _task_item(task: Task, project_name: str, assignee_name: Optional[str]) -> dict:
    actionability = (
        ["accept", "reject", "block"]
        if task.status in {"pending", "in_progress"}
        else ["submit"] if task.status == "accepted"
        else []
    )
    return {
        "id": f"task-{task.id}",
        "entity_type": "task",
        "title": task.title,
        "description": task.description or None,
        "status": task.status,
        "context": {
            "task_id": task.id,
            "project_id": task.project_id,
            "project_name": project_name,
            "assignee_id": task.assignee_id,
            "assignee_name": assignee_name,
            "due_date": task.due_date,
            "result": task.result,
            "evidence_ids": task.evidence_ids or [],
            "evidence_count": len(task.evidence_ids or []),
            "rejection_reason": task.rejection_reason or "",
            "actionability": actionability,
            "evidence_required": task.status in {"accepted", "in_progress"},
            "due_label": task.due_date or "未设置期限",
            "owner_label": assignee_name or "待分配",
        },
    }


def _task_list_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    rows = _tenant_task_rows(db, context.tenant_id)
    if screen_id == "S56":
        rows = [
            row for row in rows
            if row[0].status not in {"submitted", "completed"}
        ]
    items = [_task_item(*row) for row in rows]
    selectable_task_ids = [
        task.id for task, _, _ in rows
        if task.status not in {"submitted", "completed"}
    ]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": "批量处理任务" if screen_id == "S56" else "任务列表",
            "subtitle": "任务来自当前客户空间",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {
            "selectable_task_ids": selectable_task_ids,
            "selected_task_ids": [],
        } if screen_id == "S56" else {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无可处理任务", "当前客户空间没有可处理任务")
            if not items else None
        ),
    }


def _task_detail_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    row = db.query(Task, Project.name, User.name).join(
        Project,
        Task.project_id == Project.id,
    ).outerjoin(
        User,
        Task.assignee_id == User.id,
    ).filter(
        Task.id == context.task_id,
        Project.tenant_id == context.tenant_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    task, project_name, assignee_name = row
    return {
        "screen_id": screen_id,
        "summary": {
            "title": task.title,
            "subtitle": project_name,
            "highlight": task.status,
        },
        "items": [_task_item(task, project_name, assignee_name)],
        "options": {
            "allowed_actions": (
                ["submit"] if screen_id == "S57" else ["block"]
            ),
        },
        "context": _screen_context(context),
        "empty_state": None,
    }
