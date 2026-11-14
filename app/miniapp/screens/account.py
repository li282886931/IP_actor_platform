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
from .projects import _project_list_screen


def _privacy_payload(consent: PrivacyConsent) -> dict:
    return {
        "id": consent.id,
        "scope": consent.scope,
        "granted": bool(consent.granted),
        "policy_version": consent.policy_version,
        "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
        "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
    }


def _auth_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S01":
        return {
            "screen_id": screen_id,
            "summary": {"title": "登录", "subtitle": "选择可用登录方式", "highlight": None},
            "items": [],
            "options": {"login_methods": ["wechat", "web"]},
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S02":
        rows = db.query(TenantMember, Tenant).join(
            Tenant,
            Tenant.id == TenantMember.tenant_id,
        ).filter(
            TenantMember.user_id == context.user_id,
            Tenant.status == "active",
        ).order_by(Tenant.id.asc()).all()
        items = [
            {
                "id": f"tenant-{tenant.id}",
                "entity_type": "tenant",
                "title": tenant.name,
                "status": tenant.status,
                "value": member.role,
                "context": {
                    "tenant_id": tenant.id,
                    "role": member.role,
                    "is_current": tenant.id == context.tenant_id,
                },
            }
            for member, tenant in rows
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "选择客户空间", "subtitle": "仅显示当前用户已加入的空间", "highlight": str(len(items))},
            "items": items,
            "options": {"current_tenant_id": context.tenant_id},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无可用空间", "请联系管理员添加成员关系") if not items else None,
        }

    consents = db.query(PrivacyConsent).filter(
        PrivacyConsent.tenant_id == context.tenant_id,
        PrivacyConsent.user_id == context.user_id,
    ).order_by(PrivacyConsent.scope.asc()).all()
    items = [
        {
            "id": f"privacy-consent-{consent.id}",
            "entity_type": "privacy_consent",
            "title": consent.scope,
            "status": "granted" if consent.granted else "revoked",
            "value": consent.policy_version or None,
            "context": _privacy_payload(consent),
        }
        for consent in consents
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": "隐私授权", "subtitle": "当前用户已保存的授权范围", "highlight": str(sum(bool(item.granted) for item in consents))},
        "items": items,
        "options": {"privacy_consents": [_privacy_payload(consent) for consent in consents]},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无隐私授权记录", "授权后将在这里展示") if not items else None,
    }


def _account_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S67":
        user = db.query(User).filter(User.id == context.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        unread_count = db.query(Notification).filter(
            Notification.tenant_id == context.tenant_id,
            Notification.user_id == context.user_id,
            Notification.status == "unread",
        ).count()
        return {
            "screen_id": screen_id,
            "summary": {"title": user.name, "subtitle": user.account or user.phone or None, "highlight": str(unread_count)},
            "items": [],
            "options": {"user": serialize_user(user), "unread_notification_count": unread_count},
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S68":
        rows = db.query(TenantMember, User).join(
            User,
            User.id == TenantMember.user_id,
        ).filter(
            TenantMember.tenant_id == context.tenant_id,
        ).order_by(User.name.asc(), User.id.asc()).all()
        items = [
            {
                "id": f"tenant-member-{member.id}",
                "entity_type": "tenant_member",
                "title": user.name,
                "description": user.account or user.phone or None,
                "status": user.status,
                "value": member.role,
                "context": {
                    "tenant_member_id": member.id,
                    "user_id": user.id,
                    "role": member.role,
                },
            }
            for member, user in rows
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "团队成员", "subtitle": "当前客户空间成员", "highlight": str(len(items))},
            "items": items,
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无团队成员", "邀请成员加入当前客户空间") if not items else None,
        }

    if screen_id == "S69":
        notifications = db.query(Notification).filter(
            Notification.tenant_id == context.tenant_id,
            Notification.user_id == context.user_id,
        ).order_by(Notification.created_at.desc(), Notification.id.desc()).all()
        items = [
            {
                "id": f"notification-{notification.id}",
                "entity_type": "notification",
                "title": notification.title,
                "description": notification.content or None,
                "status": notification.status,
                "value": notification.notification_type,
                "context": {
                    "notification_id": notification.id,
                    **(notification.context or {}),
                },
            }
            for notification in notifications
        ]
        return {
            "screen_id": screen_id,
            "summary": {"title": "通知", "subtitle": "当前用户可见消息", "highlight": str(sum(item.status == "unread" for item in notifications))},
            "items": items,
            "options": {},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无通知", "新通知会显示在这里") if not items else None,
        }

    setting = db.query(UserSetting).filter(
        UserSetting.tenant_id == context.tenant_id,
        UserSetting.user_id == context.user_id,
    ).first()
    setting_payload = ({
        "id": setting.id,
        "locale": setting.locale,
        "theme": setting.theme,
        "notification_preferences": setting.notification_preferences or {},
    } if setting else None)
    if screen_id == "S70":
        return {
            "screen_id": screen_id,
            "summary": {"title": "用户设置", "subtitle": "当前客户空间内的个人设置", "highlight": setting.theme if setting else None},
            "items": [],
            "options": {"setting": setting_payload},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无用户设置", "保存设置后将在这里展示") if not setting else None,
        }

    if screen_id == "S71":
        consents = db.query(PrivacyConsent).filter(
            PrivacyConsent.tenant_id == context.tenant_id,
            PrivacyConsent.user_id == context.user_id,
        ).order_by(PrivacyConsent.scope.asc()).all()
        permissions = db.query(AgentPermission).filter(
            AgentPermission.tenant_id == context.tenant_id,
            AgentPermission.user_id == context.user_id,
        ).order_by(AgentPermission.capability.asc()).all()
        return {
            "screen_id": screen_id,
            "summary": {"title": "数据权限", "subtitle": "隐私授权与工作能力", "highlight": str(len(consents) + len(permissions))},
            "items": [],
            "options": {
                "privacy_consents": [_privacy_payload(consent) for consent in consents],
                "agent_permissions": [
                    {"capability": permission.capability, "enabled": bool(permission.enabled)}
                    for permission in permissions
                ],
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无数据权限记录", "完成授权后将在这里展示") if not consents and not permissions else None,
        }

    invitations = db.query(MemberInvitation).filter(
        MemberInvitation.tenant_id == context.tenant_id,
    ).order_by(MemberInvitation.created_at.desc(), MemberInvitation.id.desc()).all()
    items = [
        {
            "id": f"member-invitation-{invitation.id}",
            "entity_type": "member_invitation",
            "title": invitation.invitee,
            "status": invitation.status,
            "value": invitation.role,
            "context": {
                "invitation_id": invitation.id,
                "invited_by": invitation.invited_by,
                "expires_at": invitation.expires_at.isoformat(),
            },
        }
        for invitation in invitations
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": "成员邀请", "subtitle": "当前客户空间邀请记录", "highlight": str(len(items))},
        "items": items,
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无邀请记录", "邀请成员后可在这里查看状态") if not items else None,
    }


def _settings_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S82":
        wechat_configured = bool(
            os.environ.get("WECHAT_MINIAPP_APPID")
            and os.environ.get("WECHAT_MINIAPP_SECRET")
        )
        storage_provider = os.environ.get("OSS_PROVIDER", "local-placeholder").strip().lower()
        if storage_provider == "aliyun-oss":
            from app.integrations.object_storage import load_aliyun_oss_config
            creds = load_aliyun_oss_config()
            storage_configured = bool(creds["endpoint"] and creds["access_key_id"] and creds["access_key_secret"])
        elif storage_provider in {"minio", "local-placeholder"}:
            storage_configured = bool(os.environ.get("MINIO_ACCESS_KEY") and os.environ.get("MINIO_SECRET_KEY"))
        else:
            storage_configured = bool(storage_provider)
        connections = {
            "wechat": {"configured": wechat_configured},
            "object_storage": {
                "provider": storage_provider,
                "configured": storage_configured,
            },
        }
        return {
            "screen_id": screen_id,
            "summary": {"title": "服务连接", "subtitle": "仅展示配置状态", "highlight": str(sum(value["configured"] for value in connections.values()))},
            "items": [],
            "options": {"connections": connections},
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S83":
        setting = db.query(UserSetting).filter(
            UserSetting.tenant_id == context.tenant_id,
            UserSetting.user_id == context.user_id,
        ).first()
        preferences = setting.notification_preferences or {} if setting else {}
        return {
            "screen_id": screen_id,
            "summary": {"title": "通知偏好", "subtitle": "当前用户已保存设置", "highlight": str(len(preferences))},
            "items": [],
            "options": {"notification_preferences": preferences},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无通知偏好", "保存偏好后将在这里展示") if not setting else None,
        }

    consents = db.query(PrivacyConsent).filter(
        PrivacyConsent.tenant_id == context.tenant_id,
        PrivacyConsent.user_id == context.user_id,
    ).order_by(PrivacyConsent.scope.asc()).all()
    items = [
        {
            "id": f"privacy-record-{consent.id}",
            "entity_type": "privacy_consent",
            "title": consent.scope,
            "status": "granted" if consent.granted else "revoked",
            "value": consent.policy_version or None,
            "context": _privacy_payload(consent),
        }
        for consent in consents
    ]
    return {
        "screen_id": screen_id,
        "summary": {"title": "隐私记录", "subtitle": "当前用户授权历史", "highlight": str(len(items))},
        "items": items,
        "options": {"privacy_consents": [_privacy_payload(consent) for consent in consents]},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无隐私记录", "授权或撤回后将在这里展示") if not items else None,
    }


def _state_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    if screen_id == "S73":
        project_list = _project_list_screen(db, context)
        return {
            **project_list,
            "screen_id": screen_id,
            "summary": {
                "title": "项目状态",
                "subtitle": "当前客户空间项目",
                "highlight": project_list["summary"]["highlight"],
            },
            "empty_state": (
                _empty_state("暂无项目", "创建项目后可开始业务判断", "S13")
                if not project_list["items"] else None
            ),
        }

    if screen_id == "S74":
        project = _get_project(db, context)
        analysis_job = db.query(ProjectAnalysisJob).filter(
            ProjectAnalysisJob.tenant_id == context.tenant_id,
            ProjectAnalysisJob.project_id == project.id,
        ).order_by(ProjectAnalysisJob.created_at.desc(), ProjectAnalysisJob.id.desc()).first()
        job_payload = ({
            "id": analysis_job.id,
            "version_id": analysis_job.version_id,
            "purpose": analysis_job.purpose,
            "status": analysis_job.status,
            "error_message": analysis_job.error_message,
        } if analysis_job else None)
        return {
            "screen_id": screen_id,
            "summary": {
                "title": f"{project.name}分析进度",
                "subtitle": "读取最近一次真实分析任务",
                "highlight": analysis_job.status if analysis_job else None,
            },
            "items": [],
            "options": {
                "project": serialize_project(project),
                "analysis_job": job_payload,
                "recovery_target": "S11",
            },
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无分析任务", "发起分析后可查看处理进度", "S11") if not analysis_job else None,
        }

    if screen_id == "S78":
        project = _get_project(db, context)
        requested_version = db.query(ProjectVersion).filter(
            ProjectVersion.id == context.version_id,
            ProjectVersion.project_id == project.id,
        ).first()
        if not requested_version:
            raise HTTPException(status_code=404, detail="Project version not found")
        return {
            "screen_id": screen_id,
            "summary": {
                "title": "项目版本已变化",
                "subtitle": project.name,
                "highlight": str(project.current_version_id) if project.current_version_id else None,
            },
            "items": [],
            "options": {
                "requested_version_id": requested_version.id,
                "current_version_id": project.current_version_id,
                "recovery_target": "S11",
            },
            "context": _screen_context(context),
            "empty_state": None,
        }

    if screen_id == "S80":
        project = _get_project(db, context)
        return {
            "screen_id": screen_id,
            "summary": {
                "title": "确认归档项目",
                "subtitle": project.name,
                "highlight": project.status,
            },
            "items": [],
            "options": {
                "project": serialize_project(project),
                "recovery_target": "S11",
            },
            "context": _screen_context(context),
            "empty_state": None,
        }

    state_metadata = {
        "S75": ("网络请求失败", "检查网络后重试", "retry"),
        "S76": ("上下文不可用", "返回项目列表重新选择", "S10"),
        "S77": ("无访问权限", "返回可访问的项目列表", "S10"),
        "S79": ("输入校验失败", "返回上一页修正输入", "back"),
        "S81": ("登录状态已失效", "重新登录后继续", "S01"),
    }
    title, subtitle, recovery_target = state_metadata[screen_id]
    return {
        "screen_id": screen_id,
        "summary": {"title": title, "subtitle": subtitle, "highlight": None},
        "items": [],
        "options": {"recovery_target": recovery_target},
        "context": _screen_context(context),
        "empty_state": None,
    }
