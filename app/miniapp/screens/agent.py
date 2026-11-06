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
from .decisioning import _version_compare_screen
from .tasks import _task_item, _tenant_task_rows


def _analysis_item(job: ProjectAnalysisJob, project_name: str) -> dict:
    return {
        "id": f"analysis-job-{job.id}",
        "entity_type": "project_analysis_job",
        "title": job.purpose or project_name,
        "description": project_name,
        "status": job.status,
        "context": {
            "analysis_job_id": job.id,
            "project_id": job.project_id,
            "version_id": job.version_id,
            "parameters": job.parameters or {},
            "result": job.result or {},
            "error_message": job.error_message,
        },
    }


def _agent_dashboard_screen(db: Session, context: ScreenRequestContext) -> dict:
    rows = [
        row for row in _tenant_task_rows(db, context.tenant_id)
        if row[0].assignee_id == context.user_id
        and row[0].status not in {"submitted", "completed"}
    ]
    items = [_task_item(*row) for row in rows]
    projects = db.query(Project).filter(
        Project.tenant_id == context.tenant_id,
        Project.status != "archived",
    ).order_by(Project.id.desc()).all()
    top_task = items[0] if items else None
    return {
        "screen_id": "S52",
        "summary": {
            "title": "今日工作",
            "subtitle": "展示当前用户尚未完成的任务",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {
            "default_project_id": projects[0].id if projects else None,
            "available_projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "status": project.status,
                }
                for project in projects
            ],
            "work_briefing": {
                "today_change_count": len(items),
                "top_task": (
                    {
                        "task_id": top_task["context"]["task_id"],
                        "title": top_task["title"],
                        "status": top_task["status"],
                        "project_name": top_task["context"]["project_name"],
                    }
                    if top_task else None
                ),
                "active_project_count": len(projects),
            },
        },
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无待办", "当前没有分配给你的未完成任务") if not items else None,
    }


def _agent_plan_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    task_rows = [
        row for row in _tenant_task_rows(db, context.tenant_id)
        if row[0].project_id == project.id
    ]
    jobs = db.query(ProjectAnalysisJob).filter(
        ProjectAnalysisJob.tenant_id == context.tenant_id,
        ProjectAnalysisJob.project_id == project.id,
    ).order_by(ProjectAnalysisJob.id.desc()).all()
    work_plan = db.query(ProjectWorkPlan).filter(
        ProjectWorkPlan.tenant_id == context.tenant_id,
        ProjectWorkPlan.project_id == project.id,
        ProjectWorkPlan.status == "current",
    ).order_by(ProjectWorkPlan.version_no.desc()).first()
    open_alert_count = db.query(AlertEvent).filter(
        AlertEvent.tenant_id == context.tenant_id,
        AlertEvent.project_id == project.id,
        AlertEvent.status != "resolved",
    ).count()
    items = [_task_item(*row) for row in task_rows]
    items.extend(_analysis_item(job, project.name) for job in jobs)
    return {
        "screen_id": "S53",
        "summary": {
            "title": f"{project.name}执行计划",
            "subtitle": "由真实任务和分析任务组成",
            "highlight": str(len(items)),
        },
        "items": items,
        "options": {
            "project_work": (
                {
                    "plan_version": work_plan.version_no,
                    "open_alert_count": open_alert_count,
                    "recommendation": (
                        f"当前有 {open_alert_count} 项预警，等待负责人核验后再推进。"
                        if open_alert_count
                        else "当前计划无未关闭预警，仍需由负责人确认财务与审批门禁。"
                    ),
                    "human_gate": (
                        (work_plan.plan_json or {}).get("constraints", {}).get("human_gate")
                        or "财务与审批由负责人确认"
                    ),
                }
                if work_plan else None
            ),
        },
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无执行计划", "创建任务或分析任务后可在这里查看") if not items else None,
    }


def _agent_chat_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    current_version = _get_current_version(db, project)
    job = db.query(ProjectAnalysisJob).filter(
        ProjectAnalysisJob.tenant_id == context.tenant_id,
        ProjectAnalysisJob.project_id == project.id,
    ).order_by(ProjectAnalysisJob.id.desc()).first()
    return {
        "screen_id": "S54",
        "summary": {
            "title": f"{project.name}项目助手",
            "subtitle": "上下文来自项目当前版本和最近分析",
            "highlight": job.status if job else None,
        },
        "items": [_analysis_item(job, project.name)] if job else [],
        "options": {
            "project": serialize_project(project),
            "current_version": (
                serialize_version(current_version)
                if current_version
                else None
            ),
            "latest_analysis": ({
                "id": job.id,
                "project_id": job.project_id,
                "version_id": job.version_id,
                "purpose": job.purpose,
                "status": job.status,
                "parameters": job.parameters or {},
                "result": job.result or {},
                "error_message": job.error_message,
            } if job else None),
        },
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无分析结果", "先运行项目分析后再开始对话") if not job else None,
    }


def _project_changes_screen(db: Session, context: ScreenRequestContext) -> dict:
    comparison = _version_compare_screen(db, context)
    return {
        **comparison,
        "screen_id": "S59",
        "summary": {
            **comparison["summary"],
            "title": f"{_get_project(db, context).name}关键变化",
            "subtitle": "仅展示相邻两个真实版本中发生变化的输入",
        },
        "empty_state": (
            _empty_state("暂无关键变化", "至少需要两个版本且关键输入发生变化")
            if not comparison["items"] else None
        ),
    }


def _agent_permissions_screen(db: Session, context: ScreenRequestContext) -> dict:
    permissions = db.query(AgentPermission).filter(
        AgentPermission.tenant_id == context.tenant_id,
        AgentPermission.user_id == context.user_id,
    ).order_by(AgentPermission.capability.asc()).all()
    return {
        "screen_id": "S60",
        "summary": {
            "title": "工作权限",
            "subtitle": "当前用户已保存的工作授权",
            "highlight": str(sum(bool(permission.enabled) for permission in permissions)),
        },
        "items": [
            {
                "id": f"agent-permission-{permission.id}",
                "entity_type": "agent_permission",
                "title": permission.capability,
                "status": "enabled" if permission.enabled else "disabled",
                "context": {
                    "permission_id": permission.id,
                    "capability": permission.capability,
                    "enabled": bool(permission.enabled),
                },
            }
            for permission in permissions
        ],
        "options": {
            "permissions": [
                {"capability": permission.capability, "enabled": bool(permission.enabled)}
                for permission in permissions
            ],
        },
        "context": _screen_context(context),
        "empty_state": _empty_state(
            "暂无工作权限配置",
            "配置独立工作权限后将在这里展示",
        ) if not permissions else None,
    }
