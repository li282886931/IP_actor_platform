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


def _serialize_decision(decision: Decision, names: dict[int, str]) -> dict:
    return {
        "id": decision.id,
        "project_id": decision.project_id,
        "version_id": decision.version_id,
        "decision_type": decision.decision_type,
        "conditions": decision.conditions,
        "decided_by": decision.decided_by,
        "decided_by_name": names.get(decision.decided_by),
        "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
    }


def _decision_bundle(db: Session, project: Project) -> dict:
    current_version = _get_current_version(db, project)
    decisions = db.query(Decision).filter(
        Decision.project_id == project.id,
    ).order_by(Decision.id.desc()).all()
    risks = db.query(Risk).filter(Risk.project_id == project.id).all()
    gates = db.query(Gate).filter(Gate.project_id == project.id).all()
    names = _user_names(
        db,
        {decision.decided_by for decision in decisions if decision.decided_by},
    )
    return {
        "current_version": current_version,
        "decisions": decisions,
        "risks": risks,
        "gates": gates,
        "user_names": names,
    }


def _judgement_screen(
    db: Session,
    context: ScreenRequestContext,
    screen_id: str,
) -> dict:
    project = _get_project(db, context)
    bundle = _decision_bundle(db, project)
    latest_decision = bundle["decisions"][0] if bundle["decisions"] else None
    open_risks = [risk for risk in bundle["risks"] if risk.status == "open"]
    blocked_gates = [
        gate for gate in bundle["gates"]
        if gate.status in {"blocked", "pending"}
    ]
    items = [
        {
            "id": f"risk-{risk.id}",
            "entity_type": "risk",
            "title": risk.title,
            "description": risk.mitigation or None,
            "status": risk.status,
            "context": {"project_id": project.id, "risk_id": risk.id, "level": risk.level},
        }
        for risk in open_risks
    ] + [
        {
            "id": f"gate-{gate.id}",
            "entity_type": "gate",
            "title": gate.name,
            "description": gate.required_evidence or None,
            "status": gate.status,
            "context": {"project_id": project.id, "gate_id": gate.id},
        }
        for gate in blocked_gates
    ]
    if latest_decision:
        items.append({
            "id": f"decision-{latest_decision.id}",
            "entity_type": "decision",
            "title": latest_decision.decision_type,
            "description": latest_decision.conditions or None,
            "status": latest_decision.decision_type,
            "context": {
                "project_id": project.id,
                "version_id": latest_decision.version_id,
                "decision_id": latest_decision.id,
            },
        })
    current_version = bundle["current_version"]
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'判断说明' if screen_id == 'S35' else '判断摘要'}",
            "subtitle": "基于当前版本、风险、门禁和最近决策",
            "highlight": latest_decision.decision_type if latest_decision else None,
        },
        "items": items,
        "options": {
            "current_version": serialize_version(current_version) if current_version else None,
            "latest_decision": (
                _serialize_decision(latest_decision, bundle["user_names"])
                if latest_decision
                else None
            ),
            "open_risk_count": len(open_risks),
            "blocked_gate_count": len(blocked_gates),
        },
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无判断依据", "当前项目尚无版本、风险、门禁或决策记录")
            if not current_version and not items
            else None
        ),
    }


def _assumption_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    assumptions = db.query(Assumption).filter(
        Assumption.project_id == project.id,
    ).order_by(Assumption.id.desc()).all()
    return {
        "screen_id": "S36",
        "summary": {
            "title": f"{project.name}假设",
            "subtitle": "展示已保存的业务假设和置信度",
            "highlight": str(len(assumptions)),
        },
        "items": [{
            "id": f"assumption-{item.id}",
            "entity_type": "assumption",
            "title": item.title,
            "description": item.content or None,
            "status": item.status,
            "value": str(item.confidence),
            "context": {
                "project_id": project.id,
                "assumption_id": item.id,
                "confidence": item.confidence,
            },
        } for item in assumptions],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无假设", "项目尚未录入业务假设")
            if not assumptions else None
        ),
    }


def _fact_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    facts = db.query(Fact).filter(
        Fact.project_id == project.id,
    ).order_by(Fact.id.desc()).all()
    verifier_names = _user_names(
        db,
        {fact.verified_by for fact in facts if fact.verified_by},
    )
    return {
        "screen_id": "S37",
        "summary": {
            "title": f"{project.name}事实",
            "subtitle": "展示事实内容和人工核验状态",
            "highlight": str(len(facts)),
        },
        "items": [{
            "id": f"fact-{fact.id}",
            "entity_type": "fact",
            "title": fact.title,
            "description": fact.content or None,
            "status": fact.status,
            "context": {
                "project_id": project.id,
                "fact_id": fact.id,
                "source": fact.source,
                "verified_by": fact.verified_by,
                "verified_by_name": verifier_names.get(fact.verified_by),
                "verified_comment": fact.verified_comment,
            },
        } for fact in facts],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无事实", "项目尚未录入事实") if not facts else None,
    }


def _evidence_screen(
    db: Session,
    context: ScreenRequestContext,
    *,
    conflicts_only: bool = False,
) -> dict:
    project = _get_project(db, context)
    evidences = db.query(Evidence).filter(
        Evidence.project_id == project.id,
    ).order_by(Evidence.id.desc()).all()
    if conflicts_only:
        evidences = [
            evidence for evidence in evidences
            if evidence.status == "conflict"
            or bool((evidence.meta or {}).get("conflict_reason"))
        ]
    screen_id = "S39" if conflicts_only else "S38"
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'依据冲突' if conflicts_only else '依据资料'}",
            "subtitle": "仅展示已保存且可追溯的资料",
            "highlight": str(len(evidences)),
        },
        "items": [{
            "id": f"evidence-{evidence.id}",
            "entity_type": "evidence_conflict" if conflicts_only else "evidence",
            "title": evidence.name,
            "description": evidence.source or None,
            "status": evidence.status,
            "context": {
                "project_id": project.id,
                "evidence_id": evidence.id,
                "fact_id": evidence.fact_id,
                "file_url": evidence.file_url,
                "evidence_type": evidence.evidence_type,
                "metadata": evidence.meta or {},
                "conflict_reason": (evidence.meta or {}).get("conflict_reason"),
            },
        } for evidence in evidences],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state(
                "暂无依据冲突" if conflicts_only else "暂无依据资料",
                "当前没有已记录的冲突" if conflicts_only else "上传资料后可在这里查看",
                "S41" if not conflicts_only else None,
            )
            if not evidences else None
        ),
    }


def _evidence_gap_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    gates = db.query(Gate).filter(
        Gate.project_id == project.id,
        Gate.status.in_(("pending", "blocked")),
    ).order_by(Gate.id.desc()).all()
    gaps = [gate for gate in gates if gate.required_evidence]
    return {
        "screen_id": "S40",
        "summary": {
            "title": f"{project.name}依据缺口",
            "subtitle": "来自待处理门禁明确要求的资料",
            "highlight": str(len(gaps)),
        },
        "items": [{
            "id": f"evidence-gap-{gate.id}",
            "entity_type": "evidence_gap",
            "title": gate.required_evidence,
            "description": gate.name,
            "status": gate.status,
            "context": {"project_id": project.id, "gate_id": gate.id},
        } for gate in gaps],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无明确资料缺口", "待处理门禁未要求补充资料")
            if not gaps else None
        ),
    }


def _evidence_upload_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    facts = db.query(Fact).filter(
        Fact.project_id == project.id,
    ).order_by(Fact.id.desc()).all()
    return {
        "screen_id": "S41",
        "summary": {
            "title": f"{project.name}上传依据",
            "subtitle": "可将资料关联到已保存事实",
            "highlight": None,
        },
        "items": [],
        "options": {
            "project": {"id": project.id, "name": project.name},
            "facts": [
                {"id": fact.id, "title": fact.title, "status": fact.status}
                for fact in facts
            ],
            "evidence_types": ["document", "spreadsheet", "image"],
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _document_parse_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    jobs = db.query(DocumentParseJob).filter(
        DocumentParseJob.tenant_id == context.tenant_id,
        DocumentParseJob.project_id == project.id,
    ).order_by(DocumentParseJob.id.desc()).all()
    return {
        "screen_id": "S42",
        "summary": {
            "title": f"{project.name}解析结果",
            "subtitle": "展示真实文档解析任务和候选结果",
            "highlight": str(len(jobs)),
        },
        "items": [{
            "id": f"parse-job-{job.id}",
            "entity_type": "document_parse_job",
            "title": job.file_name,
            "description": job.purpose or None,
            "status": job.status,
            "context": {
                "project_id": project.id,
                "evidence_id": job.evidence_id,
                "parse_job_id": job.id,
                "file_kind": job.file_kind,
                "parse_scope": job.parse_scope,
                "result": job.result or {},
            },
        } for job in jobs],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无解析任务", "上传并解析资料后可在这里复核", "S41")
            if not jobs else None
        ),
    }


def _risk_screen(db: Session, context: ScreenRequestContext, screen_id: str) -> dict:
    project = _get_project(db, context)
    risks = db.query(Risk).filter(Risk.project_id == project.id).all()
    level_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {"open": 0, "monitoring": 1, "closed": 2}
    risks.sort(key=lambda item: (
        level_order.get(item.level, 99),
        status_order.get(item.status, 99),
        -item.id,
    ))
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'风险详情' if screen_id == 'S44' else '风险'}",
            "subtitle": "按严重级别和处理状态排序",
            "highlight": str(len([risk for risk in risks if risk.status == "open"])),
        },
        "items": [{
            "id": f"risk-{risk.id}",
            "entity_type": "risk",
            "title": risk.title,
            "description": risk.mitigation or None,
            "status": risk.status,
            "value": risk.level,
            "context": {
                "project_id": project.id,
                "risk_id": risk.id,
                "level": risk.level,
                "mitigation": risk.mitigation,
            },
        } for risk in risks],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无风险", "当前项目没有风险记录") if not risks else None,
    }


def _gate_screen(db: Session, context: ScreenRequestContext, screen_id: str) -> dict:
    project = _get_project(db, context)
    gates = db.query(Gate).filter(Gate.project_id == project.id).all()
    status_order = {"blocked": 0, "pending": 1, "passed": 2, "closed": 3}
    gates.sort(key=lambda item: (status_order.get(item.status, 99), -item.id))
    return {
        "screen_id": screen_id,
        "summary": {
            "title": f"{project.name}{'门禁详情' if screen_id == 'S46' else '门禁'}",
            "subtitle": "按阻塞和待处理状态优先展示",
            "highlight": str(len([gate for gate in gates if gate.status in {"blocked", "pending"}])),
        },
        "items": [{
            "id": f"gate-{gate.id}",
            "entity_type": "gate",
            "title": gate.name,
            "description": gate.required_evidence or None,
            "status": gate.status,
            "context": {
                "project_id": project.id,
                "gate_id": gate.id,
                "required_evidence": gate.required_evidence,
                "owner_group": gate.owner_group,
            },
        } for gate in gates],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无门禁", "当前项目没有门禁记录") if not gates else None,
    }


def _decision_confirm_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    version = db.query(ProjectVersion).filter(
        ProjectVersion.id == context.version_id,
        ProjectVersion.project_id == project.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Project version not found")
    decision = db.query(Decision).filter(
        Decision.project_id == project.id,
        Decision.version_id == version.id,
    ).order_by(Decision.id.desc()).first()
    names = _user_names(db, {decision.decided_by} if decision and decision.decided_by else set())
    return {
        "screen_id": "S47",
        "summary": {
            "title": f"{project.name}确认决策",
            "subtitle": f"基于版本 {version.version_no}",
            "highlight": decision.decision_type if decision else None,
        },
        "items": [],
        "options": {
            "project": serialize_project(project),
            "version": serialize_version(version),
            "decision": _serialize_decision(decision, names) if decision else None,
            "decision_types": ["advance", "conditional_advance", "pause", "reject"],
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _decision_result_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    decisions = db.query(Decision).filter(
        Decision.project_id == project.id,
    ).order_by(Decision.id.desc()).all()
    names = _user_names(
        db,
        {decision.decided_by for decision in decisions if decision.decided_by},
    )
    items = [{
        "id": f"decision-{decision.id}",
        "entity_type": "decision",
        "title": decision.decision_type,
        "description": decision.conditions or None,
        "status": decision.decision_type,
        "context": {
            **_serialize_decision(decision, names),
            "decision_id": decision.id,
        },
    } for decision in decisions]
    return {
        "screen_id": "S48",
        "summary": {
            "title": f"{project.name}决策结果",
            "subtitle": "按决策时间倒序展示",
            "highlight": decisions[0].decision_type if decisions else None,
        },
        "items": items,
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无决策", "确认决策后可查看结果", "S47") if not items else None,
    }


def _version_compare_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    versions = db.query(ProjectVersion).filter(
        ProjectVersion.project_id == project.id,
    ).order_by(ProjectVersion.version_no.desc()).limit(2).all()
    if len(versions) < 2:
        return {
            "screen_id": "S49",
            "summary": {
                "title": f"{project.name}版本对比",
                "subtitle": "至少需要两个真实版本",
                "highlight": None,
            },
            "items": [],
            "options": {"versions": [serialize_version(version) for version in versions], "changes": {}},
            "context": _screen_context(context),
            "empty_state": _empty_state("暂无可对比版本", "保存新版本后可查看字段变化", "S12"),
        }
    current, previous = versions
    before = previous.input_snapshot or {}
    after = current.input_snapshot or {}
    changes = {
        key: {"from": before.get(key), "to": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }
    return {
        "screen_id": "S49",
        "summary": {
            "title": f"{project.name}版本对比",
            "subtitle": f"版本 {previous.version_no} 与版本 {current.version_no}",
            "highlight": str(len(changes)),
        },
        "items": [{
            "id": f"version-change-{key}",
            "entity_type": "version_change",
            "title": key,
            "description": f"{change['from']} -> {change['to']}",
            "context": {"field": key, **change},
        } for key, change in changes.items()],
        "options": {
            "versions": [serialize_version(previous), serialize_version(current)],
            "changes": changes,
        },
        "context": _screen_context(context),
        "empty_state": None,
    }


def _report_preview_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    reports = db.query(Evidence).filter(
        Evidence.project_id == project.id,
        Evidence.evidence_type == "feasibility_report",
    ).order_by(Evidence.id.desc()).all()
    return {
        "screen_id": "S50",
        "summary": {
            "title": f"{project.name}报告",
            "subtitle": "展示已经生成并入库的报告文件",
            "highlight": str(len(reports)),
        },
        "items": [{
            "id": f"report-{report.id}",
            "entity_type": "report",
            "title": report.name,
            "description": report.source or None,
            "status": report.status,
            "context": {
                "project_id": project.id,
                "version_id": (report.meta or {}).get("version_id"),
                "evidence_id": report.id,
                "file_url": report.file_url,
                "metadata": report.meta or {},
            },
        } for report in reports],
        "options": {},
        "context": _screen_context(context),
        "empty_state": _empty_state("暂无报告", "生成报告后可在这里预览") if not reports else None,
    }


def _is_active_share(share: ReportShare) -> bool:
    if not share.created_at:
        return False
    created_at = share.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(days=share.expires_in_days or 0) > datetime.now(timezone.utc)


def _report_share_screen(db: Session, context: ScreenRequestContext) -> dict:
    project = _get_project(db, context)
    shares = db.query(ReportShare).filter(
        ReportShare.project_id == project.id,
    ).order_by(ReportShare.id.desc()).all()
    active_shares = [share for share in shares if _is_active_share(share)]
    return {
        "screen_id": "S51",
        "summary": {
            "title": f"{project.name}报告分享",
            "subtitle": "仅展示尚未过期的分享记录",
            "highlight": str(len(active_shares)),
        },
        "items": [{
            "id": f"report-share-{share.id}",
            "entity_type": "report_share",
            "title": f"分享链接 {share.id}",
            "status": "active",
            "context": {
                "project_id": project.id,
                "version_id": share.version_id,
                "share_id": share.id,
                "token": share.token,
                "expires_in_days": share.expires_in_days,
                "share_url": f"/shared/reports/{share.token}",
            },
        } for share in active_shares],
        "options": {},
        "context": _screen_context(context),
        "empty_state": (
            _empty_state("暂无有效分享", "创建报告分享后可在这里管理")
            if not active_shares else None
        ),
    }
