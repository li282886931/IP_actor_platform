"""Role collaboration with explicit project grants and private account records."""
from datetime import datetime, timezone
import hashlib
import json

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.models import (
    Artist, CollaborationHistory, CollaborationItem, CollaborationReceipt, DataAsset, DataQualityIssue,
    Evidence, ExternalDataJob, Notification, Order, PersonalRecord, Project, ProjectGrant,
    ProjectVersion, Risk, Show, ShowProjectBinding, Task, TenantMember, User,
)
from app.schemas.collaboration import Availability, Favorite, Focus, PAYLOAD_MODELS


CREATORS = {"invitation": {"B"}, "brand_demand": {"Brand"}, "rights": {"B", "Brand"},
            "supplement": {"G"}, "official_result": {"G"}, "impact": {"G"},
            "investment": {"Investor"}, "profile_change": {"Artist"}, "incident": {"root"},
            "task": {"B", "root"}}
TARGETS = {"invitation": {"Brand", "Investor", "Artist"}, "brand_demand": {"B"},
           "rights": {"B", "Brand"}, "supplement": {"B"}, "official_result": {"B", "root"},
           "impact": {"B", "root"}, "investment": {"B"}, "profile_change": {"root"},
           "incident": {"B", "root"}, "task": {"B", "Brand", "G", "Investor", "Artist", "root"}}


def fail(code, message):
    raise HTTPException(code, detail=message)


def serialize(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def jsonable(value):
    return json.loads(json.dumps(value, default=lambda v: v.isoformat()))


def member(db, ctx, user_id):
    user = db.query(User).join(TenantMember, TenantMember.user_id == User.id).filter(
        TenantMember.tenant_id == ctx.tenant.id, User.id == user_id, User.status == "active",
    ).first()
    if not user:
        fail(403, "处理人必须是当前空间的有效成员")
    return user


def project_access(db, ctx, project_id, user=None, duty="collaborate"):
    user = user or ctx.user
    project = db.query(Project).filter(Project.id == project_id, Project.tenant_id == ctx.tenant.id).first()
    if not project:
        fail(404, "项目不存在")
    if user.group_code == "B" and project.created_by == user.id:
        return project
    grant = db.query(ProjectGrant).filter_by(
        tenant_id=ctx.tenant.id, project_id=project_id, user_id=user.id, status="active",
        group_code=user.group_code,
    ).first()
    if not grant or duty not in grant.duties:
        fail(403, "请管理员配置有效的项目职责授权")
    if user.group_code == "Artist" and (not user.artist_id or project.artist_id != user.artist_id):
        fail(403, "项目与本人艺人身份不匹配")
    return project


def history(db, ctx, subject_type, row_id, action, before, after):
    event = CollaborationHistory(tenant_id=ctx.tenant.id, actor_id=ctx.user.id,
                               subject_type=subject_type, subject_id=row_id, action=action,
                               before=jsonable(before), after=jsonable(after))
    db.add(event)
    return event


def notify(db, ctx, user_id, key, title, content="", item_id=None):
    if user_id == ctx.user.id:
        return
    if not db.query(Notification).filter_by(tenant_id=ctx.tenant.id, user_id=user_id, business_key=key).first():
        db.add(Notification(tenant_id=ctx.tenant.id, user_id=user_id, business_key=key,
                            notification_type="collaboration", title=title, content=content,
                            context={"item_id": item_id, "route": "/collaboration"}))


def item_access(db, ctx, item_id):
    row = db.query(CollaborationItem).filter_by(id=item_id, tenant_id=ctx.tenant.id).first()
    if not row or ctx.user.id not in (row.owner_id, row.recipient_id):
        fail(404, "协作事项不存在")
    if row.status == "draft" and row.owner_id != ctx.user.id:
        fail(404, "协作事项不存在")
    if row.project_id:
        project_access(db, ctx, row.project_id, duty="finance" if row.kind == "investment" else "collaborate")
    return row


def validate_payload(db, ctx, kind, payload, project_id, owner=None):
    try:
        parsed = PAYLOAD_MODELS[kind].model_validate(payload).model_dump(mode="json", exclude_none=True)
    except ValidationError as error:
        fail(422, str(error))
    for evidence_id in parsed.get("evidence_ids", []):
        evidence = db.query(Evidence).filter_by(id=evidence_id, project_id=project_id).first()
        if not project_id or not evidence:
            fail(422, "证明材料必须属于当前项目")
    if kind in {"official_result", "impact"}:
        if datetime.fromisoformat(parsed["recorded_at"].replace("Z", "+00:00")).tzinfo is None:
            fail(422, "来源登记时间必须含时区")
        if kind == "impact":
            project = project_access(db, ctx, project_id, owner)
            if parsed["region"] != project.city:
                fail(422, "成效地域必须与授权项目城市一致")
    if kind == "incident":
        model = ExternalDataJob if parsed["source_type"] == "job" else DataQualityIssue
        source = db.query(model).filter_by(id=parsed["source_id"], tenant_id=ctx.tenant.id).first()
        if not source or (getattr(source, "project_id", None) and source.project_id != project_id):
            fail(422, "异常来源与空间或项目不一致")
        if parsed["source_type"] == "job" and source.status != "failed":
            fail(422, "只能分派失败的采集任务")
        if parsed["source_type"] == "quality":
            asset = db.get(DataAsset, source.asset_id) if source.asset_id else None
            if source.status != "open" or not asset or asset.project_id != project_id:
                fail(422, "质量异常须为当前项目未解决的数据问题")
    return parsed


def grant_project(db, ctx, body):
    if ctx.user.group_code != "root":
        fail(403, "仅管理员可配置项目授权")
    project = db.query(Project).filter_by(id=body.project_id, tenant_id=ctx.tenant.id).first()
    if not project:
        fail(404, "项目不存在")
    target = member(db, ctx, body.user_id)
    if target.group_code == "C":
        fail(422, "观众不参与内部项目授权")
    if "manage" in body.duties and target.group_code not in {"B", "root"}:
        fail(422, "项目管理职责限主办方或管理员")
    if "finance" in body.duties and target.group_code not in {"Investor", "B", "root"}:
        fail(422, "财务职责限资方、主办方或管理员")
    row = db.query(ProjectGrant).filter_by(project_id=body.project_id, user_id=body.user_id).first()
    if row and row.revision != body.revision:
        fail(409, "授权已存在或已变化，请刷新后修改")
    before = serialize(row) if row else {}
    if not row:
        row = ProjectGrant(tenant_id=ctx.tenant.id, project_id=body.project_id,
                           user_id=body.user_id, group_code=target.group_code)
        db.add(row)
    row.status, row.duties, row.group_code = "active", body.duties, target.group_code
    db.flush()
    history(db, ctx, "grant", row.id, "grant", before, serialize(row))
    return serialize(row)


def revoke_grant(db, ctx, grant_id, body):
    if ctx.user.group_code != "root":
        fail(403, "仅管理员可撤销授权")
    row = db.query(ProjectGrant).filter_by(id=grant_id, tenant_id=ctx.tenant.id).first()
    if not row:
        fail(404, "授权不存在")
    if row.revision != body.revision:
        fail(409, "授权已变化，请刷新")
    before = serialize(row)
    row.status = "revoked"
    db.flush()
    history(db, ctx, "grant", row.id, "revoke", before, serialize(row))
    return serialize(row)


def create_item(db, ctx, body):
    if ctx.user.group_code not in CREATORS[body.kind]:
        fail(403, "当前角色不能发起该事项")
    target = member(db, ctx, body.recipient_id)
    if target.id == ctx.user.id or target.group_code not in TARGETS[body.kind]:
        fail(422, "请指定适合的其他处理人")
    if body.kind == "rights" and {target.group_code, ctx.user.group_code} != {"B", "Brand"}:
        fail(422, "权益须由品牌方和主办方共同确认")
    if body.kind != "profile_change":
        if not body.project_id:
            fail(422, "请选择授权项目")
        duty = "finance" if body.kind == "investment" else "collaborate"
        project_access(db, ctx, body.project_id, duty=duty)
        project_access(db, ctx, body.project_id, target, duty=duty)
    elif not ctx.user.artist_id:
        fail(422, "请先绑定艺人身份")
    elif body.project_id or body.version_id:
        fail(422, "艺人资料修改不绑定项目")
    if body.version_id:
        if not db.query(ProjectVersion).filter_by(id=body.version_id, project_id=body.project_id).first():
            fail(422, "测算版本必须属于当前项目")
    if body.kind in {"investment", "invitation"} and not body.version_id:
        fail(422, "请明确引用项目版本")
    if body.kind == "invitation" and body.version_id != db.get(Project, body.project_id).current_version_id:
        fail(409, "邀请必须引用项目当前版本")
    payload = validate_payload(db, ctx, body.kind, body.payload, body.project_id)
    if body.kind == "profile_change":
        payload = {"changes": payload, "artist_id": ctx.user.artist_id,
                   "base": jsonable(serialize(db.get(Artist, ctx.user.artist_id)))}
    row = CollaborationItem(tenant_id=ctx.tenant.id, project_id=body.project_id,
                            version_id=body.version_id, owner_id=ctx.user.id,
                            recipient_id=body.recipient_id, title=body.title, kind=body.kind,
                            payload=payload, status="draft")
    db.add(row)
    db.flush()
    history(db, ctx, "item", row.id, "create", {}, serialize(row))
    return item_out(db, ctx, row)


def actions_for(row, user_id):
    owner = user_id == row.owner_id
    if row.status == "draft":
        return ["edit", "share"] if owner else []
    if row.status in {"withdrawn", "accepted", "declined", "disputed"}:
        return []
    if row.kind == "rights":
        if row.status == "shared":
            confirm = [] if user_id in row.payload.get("confirmations", []) else ["confirm"]
            return confirm + (["edit", "withdraw"] if owner else ["dispute"])
        if row.status in {"confirmed", "needs_more"}:
            return ["deliver", "edit"] if row.payload.get("delivery_user_id") == user_id else []
        if row.status == "submitted":
            return ["approve", "return", "dispute"] if row.payload.get("brand_user_id") == user_id else []
    if row.kind in {"task", "incident"}:
        if row.status in {"shared", "needs_more"}:
            return ["start"] if not owner else ["withdraw"]
        if row.status == "in_progress":
            return ["submit"] if not owner else ["withdraw"]
        if row.status == "submitted":
            return ["approve", "return"] if owner else []
    if row.status in {"shared", "needs_more"}:
        return ["withdraw", "edit"] if owner else (
            ["approve", "return"] if row.kind in {"profile_change", "official_result", "impact"}
            else ["reply", "decline"])
    if row.status == "replied":
        return ["approve", "return"] if owner else []
    return []


def item_out(db, ctx, row):
    result = serialize(row)
    result["actions"] = actions_for(row, ctx.user.id)
    result["owner_name"] = db.get(User, row.owner_id).name
    result["recipient_name"] = db.get(User, row.recipient_id).name
    result["version_changed"] = bool(row.version_id and db.get(Project, row.project_id).current_version_id != row.version_id)
    result["next_user_id"] = (row.owner_id if row.status in {"draft", "replied", "submitted"} else row.recipient_id)
    if row.kind == "rights" and row.status != "draft":
        if row.status == "shared":
            result["next_user_ids"] = [uid for uid in (row.owner_id, row.recipient_id)
                                       if uid not in row.payload.get("confirmations", [])]
            result["next_user_id"] = next(iter(result["next_user_ids"]), None)
        else:
            result["next_user_id"] = row.payload.get(
                "brand_user_id" if row.status == "submitted" else "delivery_user_id", row.recipient_id)
    if row.status in {"accepted", "declined", "withdrawn", "disputed"}:
        result["next_user_id"], result["next_user_ids"] = None, []
    if row.kind == "invitation" and row.payload.get("start"):
        target = db.get(User, row.recipient_id)
        if target.group_code == "Artist":
            start = datetime.fromisoformat(row.payload["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(row.payload["end"].replace("Z", "+00:00"))
            slots = db.query(PersonalRecord).filter_by(tenant_id=ctx.tenant.id, user_id=target.id, type="availability").all()
            result["availability_conflict"] = any(
                datetime.fromisoformat(slot.payload["start"].replace("Z", "+00:00")) < end and
                datetime.fromisoformat(slot.payload["end"].replace("Z", "+00:00")) > start for slot in slots)
    return result


def act_item(db, ctx, item_id, body):
    row = item_access(db, ctx, item_id)
    if row.revision != body.revision:
        fail(409, "事项已被修改，请刷新后操作")
    if body.action not in actions_for(row, ctx.user.id):
        fail(403, "当前状态不能执行此操作")
    if body.action in {"return", "dispute", "decline"} and not body.note:
        fail(422, "请填写退回、争议或拒绝原因")
    if body.action in {"reply", "deliver", "submit"} and not body.note:
        fail(422, "请填写实际处理结果")
    target = member(db, ctx, row.recipient_id)
    owner = member(db, ctx, row.owner_id)
    if row.project_id:
        duty = "finance" if row.kind == "investment" else "collaborate"
        project_access(db, ctx, row.project_id, target, duty=duty)
        project_access(db, ctx, row.project_id, owner, duty=duty)
    before = serialize(row)
    payload = dict(row.payload)
    action = body.action
    if action == "edit":
        if body.payload is None:
            fail(422, "请填写修改内容")
        fresh = validate_payload(db, ctx, row.kind, body.payload, row.project_id, owner)
        if row.kind == "profile_change":
            fresh = {**payload, "changes": fresh}
        if row.kind == "rights" and ctx.user.id != row.owner_id:
            row.owner_id, row.recipient_id = row.recipient_id, row.owner_id
        row.payload, row.status = fresh, "draft"
    elif action == "share":
        if row.kind == "rights":
            payload["delivery_user_id"] = owner.id if owner.group_code == "B" else target.id
            payload["brand_user_id"] = owner.id if owner.group_code == "Brand" else target.id
            payload["confirmations"] = []
        if row.kind in {"task", "incident"} and not row.task_id:
            task = Task(project_id=row.project_id, assignee_id=target.id, title=row.title,
                        description=payload["instructions"], due_date=payload.get("due_date", ""))
            db.add(task)
            db.flush()
            row.task_id = task.id
        if row.task_id:
            task = db.get(Task, row.task_id)
            task.title, task.description = row.title, payload["instructions"]
            task.due_date, task.status = payload.get("due_date", ""), "pending"
        row.status = "shared"
    elif action == "confirm":
        confirmations = list(payload.get("confirmations", []))
        if ctx.user.id in confirmations:
            fail(409, "本版本已确认")
        confirmations.append(ctx.user.id)
        payload["confirmations"] = confirmations
        row.status = "confirmed" if len(confirmations) == 2 else "shared"
    else:
        row.status = {"withdraw": "withdrawn", "reply": "replied", "decline": "declined",
                      "approve": "accepted", "return": "needs_more", "dispute": "disputed",
                      "start": "in_progress", "submit": "submitted", "deliver": "submitted"}[action]
        if body.payload is not None:
            if set(body.payload) - {"evidence_ids"}:
                fail(422, "此动作只能补交证明材料，修改条款请使用编辑")
            evidence_ids = body.payload.get("evidence_ids", [])
            if not isinstance(evidence_ids, list) or any(not isinstance(v, int) for v in evidence_ids):
                fail(422, "证明材料编号格式错误")
            for eid in evidence_ids:
                if not row.project_id or not db.query(Evidence).filter_by(id=eid, project_id=row.project_id).first():
                    fail(422, "证明材料必须属于当前项目")
            payload["evidence_ids"] = evidence_ids
        if action == "approve" and row.kind == "rights" and not payload.get("evidence_ids"):
            fail(422, "权益验收须补齐当前项目的实际交付证明材料")
        if action == "approve" and row.kind == "profile_change":
            artist = db.query(Artist).filter_by(id=payload["artist_id"]).with_for_update().one()
            if owner.artist_id != artist.id:
                fail(409, "艺人绑定已变化")
            if jsonable(serialize(artist)) != payload["base"]:
                fail(409, "原资料已变化，请重新提交申请")
            for key, value in payload["changes"].items():
                setattr(artist, key, value)
        if action == "approve" and row.kind == "incident":
            model = ExternalDataJob if payload["source_type"] == "job" else DataQualityIssue
            source = db.get(model, payload["source_id"])
            if payload["source_type"] == "quality":
                source.status = "resolved"
                source.resolved_by = ctx.user.id
                source.resolved_at = datetime.utcnow()
            # Failed jobs stay failed until a real connector rerun succeeds.
        if body.note:
            payload["last_note"] = body.note
            payload["last_actor_id"] = ctx.user.id
        if action in {"reply", "submit", "deliver", "approve"}:
            payload.pop("rejection_reason", None)
        if action in {"return", "dispute", "decline"}:
            payload["rejection_reason"] = body.note
        if row.task_id:
            task = db.get(Task, row.task_id)
            task.status = {"needs_more": "rejected", "withdrawn": "cancelled",
                           "declined": "cancelled"}.get(row.status, row.status)
            if action == "submit":
                task.result, task.evidence_ids = body.note, payload.get("evidence_ids", [])
                task.rejection_reason = ""
            if action == "return":
                task.rejection_reason = body.note
    if action != "edit":
        row.payload = payload
    db.flush()
    history(db, ctx, "item", row.id, action, before, serialize(row))
    if action != "edit":
        other = row.recipient_id if ctx.user.id == row.owner_id else row.owner_id
        notify(db, ctx, other, f"collaboration:{row.id}:{row.revision}", row.title,
               body.note or f"事项状态：{row.status}", row.id)
    return item_out(db, ctx, row)


def personal(db, ctx, body):
    if body.type == "availability" and (ctx.user.group_code != "Artist" or not ctx.user.artist_id):
        fail(403, "仅已绑定艺人可维护本人档期")
    if body.type == "favorite" and ctx.user.group_code != "C":
        fail(403, "关注收藏仅供观众使用")
    try:
        payload = {} if body.remove else {
            "focus": Focus, "favorite": Favorite, "availability": Availability,
        }[body.type].model_validate(body.payload).model_dump(mode="json", exclude_unset=True)
    except ValidationError as error:
        fail(422, str(error))
    key = body.record_key
    if body.type == "focus":
        key = "default"
    if body.type == "favorite" and not body.remove:
        target = payload["target_type"]
        if target in {"artist", "show"}:
            try:
                model = Artist if target == "artist" else Show
                exists = db.get(model, int(payload["target_id"]))
            except ValueError:
                exists = None
            if not exists:
                fail(422, "关注对象不存在")
        key = target + ":" + payload["target_id"]
    row = db.query(PersonalRecord).filter_by(tenant_id=ctx.tenant.id, user_id=ctx.user.id,
                                             type=body.type, record_key=key).first()
    before = serialize(row) if row else {}
    if row and (body.revision is None or row.revision != body.revision):
        fail(409, "个人设置已变化，请刷新后操作")
    if body.remove:
        if row:
            history(db, ctx, "personal", row.id, "remove", before, {})
            db.delete(row)
        return {"removed": True}
    if not row:
        row = PersonalRecord(tenant_id=ctx.tenant.id, user_id=ctx.user.id, type=body.type, record_key=key)
        db.add(row)
    row.payload = payload
    db.flush()
    history(db, ctx, "personal", row.id, "save", before, serialize(row))
    return serialize(row)


def reservation(db, ctx, body):
    if ctx.user.group_code != "C":
        fail(403, "仅观众可修改本人预约")
    row = db.query(Order).filter_by(id=body.order_id, tenant_id=ctx.tenant.id,
                                    user_id=ctx.user.id).with_for_update().first()
    if not row:
        fail(404, "预约不存在")
    before = serialize(row)
    expected = "registered" if body.action == "cancel" else "cancelled"
    if row.status != expected:
        fail(409, "预约状态已变化")
    row.status = "cancelled" if body.action == "cancel" else "registered"
    db.flush()
    history(db, ctx, "reservation", row.id, body.action, before, serialize(row))
    return serialize(row)


def show_update(db, ctx, body):
    if not body.confirmed:
        fail(422, "仅已确认演出变化可发布")
    if set(body.changes) - {"date", "venue", "status", "price", "description"} or not body.changes:
        fail(422, "可修改时间、场馆、票价、状态和说明")
    if "status" in body.changes and body.changes["status"] not in {"on_sale", "scheduled", "cancelled", "ended"}:
        fail(422, "演出状态无效")
    project_access(db, ctx, body.project_id, duty="manage")
    show = db.query(Show).filter_by(id=body.show_id).with_for_update().first()
    if not show:
        fail(404, "演出不存在")
    binding = db.query(ShowProjectBinding).filter_by(show_id=show.id).first()
    if not binding or binding.tenant_id != ctx.tenant.id or binding.project_id != body.project_id:
        fail(403, "演出须先由管理员绑定本空间项目")
    before = serialize(show)
    changes = {k: v for k, v in body.changes.items() if getattr(show, k) != v}
    for key, value in changes.items():
        setattr(show, key, value)
    if changes:
        event = history(db, ctx, "show", show.id, "publish", before, serialize(show))
        db.flush()
        event_id = event.id
        for order in db.query(Order).filter_by(show_id=show.id, tenant_id=ctx.tenant.id, status="registered").all():
            if order.user_id:
                notify(db, ctx, order.user_id, f"show:{show.id}:{event_id}", "演出信息已更新",
                       "；".join(f"{k}：{v}" for k, v in changes.items()))
    return serialize(show)


def overview(db, ctx):
    projects = []
    for project in db.query(Project).filter_by(tenant_id=ctx.tenant.id).all():
        if ctx.user.group_code == "root":
            projects.append({"id": project.id, "name": project.name, "city": project.city,
                             "current_version_id": project.current_version_id})
            continue
        try:
            project_access(db, ctx, project.id)
        except HTTPException:
            continue
        data = {"id": project.id, "name": project.name, "city": project.city,
                "current_version_id": project.current_version_id}
        levels = {risk.level for risk in db.query(Risk).filter_by(project_id=project.id).all()
                  if risk.status not in {"resolved", "closed"}}
        data["risk_level"] = next((level for level in ("high", "medium", "low") if level in levels), None)
        if ctx.user.group_code in {"Investor", "B"}:
            try:
                project_access(db, ctx, project.id, duty="finance")
                data["versions"] = [serialize(v) for v in db.query(ProjectVersion).filter_by(project_id=project.id).all()]
            except HTTPException:
                pass
        projects.append(data)
    items = []
    for row in db.query(CollaborationItem).filter(
        CollaborationItem.tenant_id == ctx.tenant.id,
        or_(CollaborationItem.owner_id == ctx.user.id, CollaborationItem.recipient_id == ctx.user.id),
    ).order_by(CollaborationItem.id.desc()).all():
        try:
            item_access(db, ctx, row.id)
        except HTTPException:
            continue
        items.append(item_out(db, ctx, row))
    records = db.query(PersonalRecord).filter_by(tenant_id=ctx.tenant.id, user_id=ctx.user.id).all()
    grants = db.query(ProjectGrant).filter_by(tenant_id=ctx.tenant.id).all() if ctx.user.group_code == "root" else []
    visible_users = set([ctx.user.id])
    if ctx.user.group_code == "root":
        visible_users.update(uid for uid, in db.query(TenantMember.user_id).filter_by(tenant_id=ctx.tenant.id))
    else:
        for p in projects:
            visible_users.update(g.user_id for g in db.query(ProjectGrant).filter_by(project_id=p["id"], status="active"))
            visible_users.add(db.get(Project, p["id"]).created_by)
        # Profile-change review can select a same-space administrator.
        if ctx.user.group_code == "Artist":
            visible_users.update(u.id for u in db.query(User).join(TenantMember).filter(
                TenantMember.tenant_id == ctx.tenant.id, User.group_code == "root"))
    result = {
        "projects": projects, "items": items, "grants": [serialize(g) for g in grants],
        "members": [{"id": u.id, "name": u.name, "group_code": u.group_code, "artist_id": u.artist_id}
                    for u in db.query(User).filter(User.id.in_(visible_users), User.status == "active").all()],
        "focus": next((r.payload for r in records if r.type == "focus"), {}),
        "personal": [serialize(r) for r in records],
        "reservations": [serialize(o) for o in db.query(Order).filter_by(tenant_id=ctx.tenant.id, user_id=ctx.user.id)],
        "notifications": [serialize(n) for n in db.query(Notification).filter_by(
            tenant_id=ctx.tenant.id, user_id=ctx.user.id).order_by(Notification.id.desc()).limit(100)],
        "role": ctx.user.group_code,
        "managed_shows": [],
    }
    if ctx.user.group_code in {"B", "root"}:
        for binding in db.query(ShowProjectBinding).filter_by(tenant_id=ctx.tenant.id):
            try:
                project_access(db, ctx, binding.project_id, duty="manage")
            except HTTPException:
                continue
            show = db.get(Show, binding.show_id)
            if show:
                result["managed_shows"].append({"id": show.id, "title": show.title,
                                               "project_id": binding.project_id})
    if ctx.user.group_code == "C":
        result["shows"] = [{"id": s.id, "title": s.title, "city": s.city, "date": s.date} for s in db.query(Show)]
        result["artists"] = [{"id": a.id, "name": a.name} for a in db.query(Artist)]
    if ctx.user.group_code == "root":
        result["audit"] = [serialize(h) for h in db.query(CollaborationHistory).filter(
            CollaborationHistory.tenant_id == ctx.tenant.id,
            CollaborationHistory.subject_type.in_(["grant", "binding", "show_binding"]),
        ).order_by(CollaborationHistory.id.desc()).limit(100)]
        result["shows"] = [{"id": s.id, "title": s.title} for s in db.query(Show)]
        result["artists"] = [{"id": a.id, "name": a.name} for a in db.query(Artist)]
        result["incidents"] = (
            [{"source_type": "job", "source_id": j.id, "project_id": j.project_id}
             for j in db.query(ExternalDataJob).filter_by(tenant_id=ctx.tenant.id, status="failed")] +
            [{"source_type": "quality", "source_id": q.id, "project_id": getattr(q, "project_id", None)}
             for q in db.query(DataQualityIssue).filter_by(tenant_id=ctx.tenant.id, status="open")])
    return result


def mutate(db, ctx, route, body, operation):
    """Atomically store business effects and the retry receipt."""
    fingerprint = hashlib.sha256(json.dumps(
        {"route": route, "body": body.model_dump(mode="json")}, sort_keys=True).encode()).hexdigest()
    receipt = db.query(CollaborationReceipt).filter_by(
        tenant_id=ctx.tenant.id, user_id=ctx.user.id, request_key=body.request_key).first()
    if receipt:
        if receipt.fingerprint != fingerprint:
            fail(409, "重复请求键与原请求内容不一致")
        if route.startswith("items/") or route == "items":
            item_access(db, ctx, receipt.result["id"])
        return receipt.result
    try:
        result = jsonable(operation())
        db.add(CollaborationReceipt(tenant_id=ctx.tenant.id, user_id=ctx.user.id,
                                   request_key=body.request_key, fingerprint=fingerprint, result=result))
        db.commit()
        return result
    except (StaleDataError, IntegrityError):
        db.rollback()
        fail(409, "数据已变化或请求正在处理，请刷新后重试")
    except Exception:
        db.rollback()
        raise
