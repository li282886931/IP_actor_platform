"""Authenticated v5 decision and operating workflows shared by Web and miniapp."""
from datetime import datetime, timedelta
import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import ValidationError
from sqlalchemy import func

from app.core.responses import json_ok
from app.database import get_db
from app.models import (Artist, CityProfile, DecisionReport, DecisionRuleVersion, Evidence, Gate,
                        OperatingRecord, Project, ProjectActual, ProjectVersion, Risk, Show, User)
from app.schemas.decision_platform import (
    ActualsIn, CalibrateIn, CityIn, RECORD_MODELS, RecordIn, ReportIn, ReviewIn, RuleIn, ScenarioIn, StageIn, STAGES,
)
from app.schemas.collaboration import RequestIn
from app.services.decision_catalog import builtin_catalog
from app.services.auth import resolve_request_context
from app.services.collaboration import history, mutate, project_access, serialize
from app.services.decision_platform import DEFAULT_CONFIG, calculate_record, calculate_scenarios, evaluate_decision

router = APIRouter()
ROLES = {
    "brand_match": {"B", "Brand"}, "city_fit": {"B", "G"}, "artist_benchmark": {"B", "Artist"},
    "incremental": {"B"}, "sponsorship": {"B", "Brand"}, "investment": {"Investor"},
    "asset": {"G"}, "impact": {"G"}, "artist_post": {"Artist"}, "artist_metrics": {"Artist"},
    "wishlist": {"C"}, "checkin": {"C"}, "comment": {"C", "Artist"},
}
FINANCE_KINDS = {"incremental", "investment"}
AUXILIARY_KINDS = {"brand_match", "city_fit", "artist_benchmark"}
RULE_READ_ROLES = {"B", "Investor", "Brand", "G", "Artist"}


def context(db=Depends(get_db), authorization: str = Header(default=""), x_tenant_id: str = Header(default="")):
    return resolve_request_context(db, authorization=authorization, tenant_header=x_tenant_id)


def require_role(ctx, roles):
    if ctx.user.group_code not in roles:
        raise HTTPException(403, "当前角色无此操作权限")


@router.post("/decision/projects/{project_id}/scenarios")
def scenarios(project_id: int, body: ScenarioIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B", "Investor"})
    project_access(db, ctx, project_id, duty="finance")
    return json_ok(calculate_scenarios(body.model_dump(mode="json")))


def proof(db, project_id, ids, *, verified=False, required=False):
    if required and not ids:
        raise HTTPException(422, "请提供已核验的项目证明材料")
    for evidence_id in ids:
        row = db.query(Evidence).filter_by(id=evidence_id, project_id=project_id).first()
        if not row or (verified and row.status != "verified"):
            raise HTTPException(422, "证明材料须属于当前项目并完成核验")


def get_rule(db, ctx, rule_id):
    rule = db.query(DecisionRuleVersion).filter_by(id=rule_id, tenant_id=ctx.tenant.id).first()
    if not rule:
        raise HTTPException(404, "规则版本不存在")
    return rule


def report_access(db, ctx, report_id, *, manage=False):
    report = db.query(DecisionReport).filter_by(id=report_id, tenant_id=ctx.tenant.id).first()
    if not report:
        raise HTTPException(404, "报告不存在")
    project_access(db, ctx, report.project_id, duty="manage" if manage else "finance")
    return report


def new_rule(db, ctx, name, config, source, reviewed=False, parent_id=None):
    if parent_id:
        get_rule(db, ctx, parent_id)
    row = DecisionRuleVersion(tenant_id=ctx.tenant.id,
                              version_no=(db.query(func.max(DecisionRuleVersion.version_no)).filter_by(
                                  tenant_id=ctx.tenant.id).scalar() or 0) + 1,
                              name=name, config=config, source=source, parent_id=parent_id,
                              status="verified" if reviewed else "pending", created_by=ctx.user.id)
    db.add(row)
    db.flush()
    history(db, ctx, "decision_rule", row.id, "create", {}, serialize(row))
    return serialize(row)


@router.get("/decision/rules")
def list_rules(db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, RULE_READ_ROLES)
    return json_ok([serialize(r) for r in db.query(DecisionRuleVersion).filter_by(
        tenant_id=ctx.tenant.id).order_by(DecisionRuleVersion.version_no.desc())])


@router.get("/decision/catalog")
def catalog(db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, RULE_READ_ROLES)
    return json_ok(builtin_catalog())


@router.post("/decision/catalog/install")
def install_catalog(body: RequestIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    from app.schemas.decision_platform import RuleConfig
    catalog = builtin_catalog()
    config = RuleConfig.model_validate(catalog["config"]).model_dump(mode="json")
    def operation():
        for row in db.query(DecisionRuleVersion).filter_by(tenant_id=ctx.tenant.id):
            if row.config == config:
                return serialize(row)
        return new_rule(db, ctx, catalog["name"], config, catalog["source"])
    return json_ok(mutate(db, ctx, "v5/catalog/install", body, operation))


@router.post("/decision/rules")
def create_rule(body: RuleIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    return json_ok(mutate(db, ctx, "v5/rules", body, lambda: new_rule(
        db, ctx, body.name, body.config.model_dump(mode="json"), body.source, body.reviewed, body.parent_id)))


@router.post("/projects/{project_id}/report")
def create_report(project_id: int, body: ReportIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    project = project_access(db, ctx, project_id, duty="manage")
    rule = get_rule(db, ctx, body.rule_version_id)
    inputs = body.inputs.model_dump(mode="json")
    proof(db, project.id, inputs["evidence_ids"])
    version_id = body.project_version_id or project.current_version_id
    if version_id and not db.query(ProjectVersion).filter_by(id=version_id, project_id=project.id).first():
        raise HTTPException(422, "测算版本不属于当前项目")
    for dimension in rule.config.get("dimensions", []):
        if inputs["scores"].get(dimension["key"], 0) > dimension["max_score"]:
            raise HTTPException(422, "评分不得超过配置维度上限")
    if set(inputs["scores"]) - {d["key"] for d in rule.config.get("dimensions", [])}:
        raise HTTPException(422, "评分包含未配置的维度")
    try:
        result = evaluate_decision(inputs, rule.config)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    def operation():
        fingerprint = hashlib.sha256(json.dumps(
            [inputs, rule.id, version_id], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        row = db.query(DecisionReport).filter_by(project_id=project.id, fingerprint=fingerprint).first()
        if not row:
            row = DecisionReport(tenant_id=ctx.tenant.id, project_id=project.id, project_version_id=version_id,
                                 rule_version_id=rule.id, fingerprint=fingerprint, inputs=inputs,
                                 rule_snapshot=rule.config, result=result,
                                 created_by=ctx.user.id)
            db.add(row)
            db.flush()
            history(db, ctx, "decision_report", row.id, "create", {}, serialize(row))
        return serialize(row)
    return json_ok(mutate(db, ctx, f"v5/projects/{project_id}/report", body, operation))


@router.get("/projects/{project_id}/report")
def latest_report(project_id: int, db=Depends(get_db), ctx=Depends(context)):
    project_access(db, ctx, project_id, duty="finance")
    row = db.query(DecisionReport).filter_by(project_id=project_id).order_by(DecisionReport.id.desc()).first()
    return json_ok(serialize(row) if row else None)


@router.get("/decision/reports/{report_id}/replay")
def replay_report(report_id: int, db=Depends(get_db), ctx=Depends(context)):
    row = report_access(db, ctx, report_id)
    result = evaluate_decision(row.inputs, row.rule_snapshot)
    return json_ok({"matches": result == row.result, "result": result, "rule_version_id": row.rule_version_id})


@router.post("/decision/reports/{report_id}/verify")
def verify_report(report_id: int, body: ReviewIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    row = report_access(db, ctx, report_id, manage=True)
    proof(db, row.project_id, list(set(body.evidence_ids + row.inputs.get("evidence_ids", []))), verified=True, required=True)
    rule = get_rule(db, ctx, row.rule_version_id)
    if rule.status != "verified" or row.result["missing_fields"] or row.result["unresolved_rules"] or row.result["configuration_gaps"] or row.result["score"]["status"] != "calculated":
        raise HTTPException(409, "规则或输入未完整核验，请先补齐配置与评分")
    def operation():
        before = serialize(row)
        row.verification_status = "verified"
        db.flush()
        history(db, ctx, "decision_report", row.id, "verify", before, {**serialize(row), "note": body.note, "evidence_ids": body.evidence_ids})
        return serialize(row)
    return json_ok(mutate(db, ctx, f"v5/reports/{report_id}/verify", body, operation))


@router.put("/projects/{project_id}/actuals")
def put_actuals(project_id: int, body: ActualsIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    project_access(db, ctx, project_id, duty="manage")
    proof(db, project_id, body.evidence_ids, verified=body.verified, required=body.verified)
    def operation():
        row = db.query(ProjectActual).filter_by(project_id=project_id).first()
        before = serialize(row) if row else {}
        if not row:
            row = ProjectActual(project_id=project_id)
            db.add(row)
        for key in ("actual_attendance", "actual_revenue", "actual_cost", "notes"):
            setattr(row, key, getattr(body, key))
        row.actual_profit = body.actual_revenue - body.actual_cost if body.actual_revenue is not None and body.actual_cost is not None else None
        if body.verified and (row.actual_profit is None or row.actual_attendance is None):
            raise HTTPException(422, "核验前请补齐实际人数、实收收入和成本")
        row.status = "verified" if body.verified else "pending"
        db.flush()
        history(db, ctx, "project_actual", row.id, "save", before,
                {**serialize(row), "evidence_ids": body.evidence_ids})
        # Revalidate incremental records whenever actual settlement changes.
        for record in db.query(OperatingRecord).filter_by(project_id=project_id, kind="incremental"):
            record.result = calculate_record(record.kind, record.payload, verified=record.status == "verified" and row.status == "verified",
                                             actual_profit=row.actual_profit if row.status == "verified" else None)
        return serialize(row)
    return json_ok(mutate(db, ctx, f"v5/projects/{project_id}/actuals", body, operation))


@router.post("/reports/{report_id}/calibrate")
def calibrate(report_id: int, body: CalibrateIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    row = report_access(db, ctx, report_id, manage=True)
    actual = db.query(ProjectActual).filter_by(project_id=row.project_id).first()
    if not actual or actual.actual_profit is None:
        raise HTTPException(409, "请先录入实际收入和成本")
    def operation():
        rule = new_rule(db, ctx, f"报告{row.id}复盘校准", body.config.model_dump(mode="json"),
                        body.attribution, parent_id=row.rule_version_id)
        comparison = {"predicted_profit": row.result["finance"]["predicted_profit"], "actual_profit": actual.actual_profit,
                      "profit_deviation": actual.actual_profit - row.result["finance"]["predicted_profit"]
                      if row.result["finance"]["predicted_profit"] is not None else None,
                      "actual_status": actual.status, "attribution": body.attribution}
        history(db, ctx, "decision_report", row.id, "calibrate", {}, {"rule": rule, "comparison": comparison})
        return {"rule": rule, "comparison": comparison}
    return json_ok(mutate(db, ctx, f"v5/reports/{report_id}/calibrate", body, operation))


@router.post("/decision/projects/{project_id}/stage")
def advance_stage(project_id: int, body: StageIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B"})
    project = project_access(db, ctx, project_id, duty="manage")
    row = report_access(db, ctx, body.report_id, manage=True)
    if row.project_id != project_id:
        raise HTTPException(422, "报告与项目不一致")
    def operation():
        current_report = db.query(DecisionReport).filter_by(project_id=project_id).order_by(DecisionReport.id.desc()).first()
        active_rule = db.query(DecisionRuleVersion).filter_by(
            tenant_id=ctx.tenant.id, status="verified").order_by(DecisionRuleVersion.version_no.desc()).first()
        if (current_report.id != row.id or row.project_version_id != project.current_version_id
                or not active_rule or row.rule_version_id != active_rule.id):
            raise HTTPException(409, "请使用当前项目版本及生效规则的最新报告")
        if row.verification_status != "verified" or row.result["vetoes"]:
            raise HTTPException(409, "报告未核验或存在一票否决，禁止推进")
        if row.result["plan_triggers"] and not body.stop_loss_plan:
            raise HTTPException(409, "请先登记止损预案")
        current = db.query(Gate).filter_by(project_id=project_id, name="v5六阶段").with_for_update().first()
        current_stage = current.status if current else STAGES[0]
        if current_stage not in STAGES or STAGES.index(body.stage) != STAGES.index(current_stage) + 1:
            raise HTTPException(409, "阶段必须按立项、报批、招商、票务、执行、复盘依次推进")
        proof(db, project_id, body.evidence_ids, verified=True, required=True)
        if body.stage in {"sponsorship", "ticketing", "execution"} and row.inputs.get("permit_received") is not True:
            raise HTTPException(409, "未收到批文，禁止进入该阶段")
        if body.stage == "review" and not db.query(ProjectActual).filter_by(project_id=project_id, status="verified").first():
            raise HTTPException(409, "复盘前请完成实际结算核验")
        before = serialize(current) if current else {"status": "initiation"}
        gate = current or Gate(project_id=project_id, name="v5六阶段", owner_group="B")
        gate.status = body.stage
        gate.required_evidence = json.dumps({"report_id": row.id, "evidence_ids": body.evidence_ids,
                                            "stop_loss_plan": body.stop_loss_plan}, ensure_ascii=False)
        db.add(gate)
        db.flush()
        history(db, ctx, "decision_stage", gate.id, "advance", before, serialize(gate))
        return serialize(gate)
    # Authorization precedes receipt lookup; state checks only run for new mutations.
    return json_ok(mutate(db, ctx, f"v5/projects/{project_id}/stage", body, operation))


def record_access(db, ctx, row_id):
    row = db.query(OperatingRecord).filter_by(id=row_id, tenant_id=ctx.tenant.id, owner_id=ctx.user.id).first()
    if not row:
        raise HTTPException(404, "经营记录不存在")
    if row.project_id:
        project_access(db, ctx, row.project_id, duty="finance" if row.kind in FINANCE_KINDS else "collaborate")
    return row


@router.post("/decision/records")
def save_record(body: RecordIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, ROLES[body.kind])
    try:
        data = RECORD_MODELS[body.kind].model_validate(body.payload).model_dump(mode="json")
    except ValidationError as error:
        raise HTTPException(422, str(error)) from error
    if body.kind in {"incremental", "sponsorship", "investment", "impact"} | AUXILIARY_KINDS and not body.project_id:
        raise HTTPException(422, "此类记录必须关联授权项目")
    project = project_access(db, ctx, body.project_id, duty="finance" if body.kind in FINANCE_KINDS else "collaborate") if body.project_id else None
    proof(db, body.project_id, data.get("evidence_ids", []))
    if body.kind in AUXILIARY_KINDS:
        rule = get_rule(db, ctx, data["rule_version_id"])
        model = rule.config.get("auxiliary_models", {}).get(body.kind)
        if not model:
            raise HTTPException(422, "此规则版本未配置所选辅助模型")
        known = {c["key"] for c in model["criteria"]}
        if set(data["metrics"]) - known:
            raise HTTPException(422, "评分包含未配置的指标")
        if body.kind != "artist_benchmark" and any(v > 1 for v in data["metrics"].values()):
            raise HTTPException(422, "品牌和城市指标须为0–1比例")
        if not data["source"].strip():
            raise HTTPException(422, "请填写指标来源与参考基准")
        data.update(model_snapshot=model, catalog_version=rule.config.get("catalog_version"))
    if body.kind == "impact" and data["city"] != project.city:
        raise HTTPException(422, "成效城市必须与项目一致")
    if body.kind in {"artist_post", "artist_metrics", "artist_benchmark"}:
        artist_id = ctx.user.artist_id if ctx.user.group_code == "Artist" else project.artist_id
        if not artist_id or not db.get(Artist, artist_id):
            raise HTTPException(409, "请先绑定本人艺人资料")
        if ctx.user.group_code == "Artist" and project and project.artist_id != artist_id:
            raise HTTPException(422, "艺人对标须关联本人艺人的授权项目")
        data["artist_id"] = artist_id
    if body.kind == "wishlist":
        for show_id in data["show_ids"]:
            if not db.get(Show, show_id):
                raise HTTPException(422, "年度计划包含不存在的演出")
    if body.kind == "checkin" and not db.get(Show, data["show_id"]):
        raise HTTPException(422, "演出不存在")
    if body.kind == "comment":
        post = db.query(OperatingRecord).filter_by(id=data["post_id"], tenant_id=ctx.tenant.id, kind="artist_post").first()
        if not post:
            raise HTTPException(422, "动态不存在")
    if body.kind == "asset" and data.get("venue_id"):
        from app.models import Venue
        if not db.query(Venue).filter_by(id=data["venue_id"], tenant_id=ctx.tenant.id, city=data["city"]).first():
            raise HTTPException(422, "场馆必须属于当前空间及城市")
    def operation():
        row = db.query(OperatingRecord).filter_by(tenant_id=ctx.tenant.id, owner_id=ctx.user.id,
                    kind=body.kind, record_key=body.record_key).first()
        before = serialize(row) if row else {}
        if row:
            record_access(db, ctx, row.id)
            if body.revision != row.revision or row.project_id != body.project_id:
                raise HTTPException(409, "记录版本已变化或项目不可更换，请刷新")
        else:
            row = OperatingRecord(tenant_id=ctx.tenant.id, owner_id=ctx.user.id, kind=body.kind,
                                  record_key=body.record_key, project_id=body.project_id)
            db.add(row)
        row.title, row.payload, row.status = body.title, data, "pending"
        row.result = calculate_record(body.kind, data)
        db.flush()
        history(db, ctx, "operating_record", row.id, "save", before, serialize(row))
        return serialize(row)
    return json_ok(mutate(db, ctx, "v5/records", body, operation))


@router.post("/decision/records/{row_id}/verify")
def verify_record(row_id: int, body: ReviewIn, db=Depends(get_db), ctx=Depends(context)):
    row = record_access(db, ctx, row_id)
    if row.kind not in {"incremental", "sponsorship", "investment", "asset", "impact", "artist_metrics"} | AUXILIARY_KINDS:
        raise HTTPException(422, "此类记录无需经营核验")
    proof(db, row.project_id, list(set(body.evidence_ids + row.payload.get("evidence_ids", []))), verified=True, required=True)
    if row.kind in AUXILIARY_KINDS:
        rule = get_rule(db, ctx, row.payload["rule_version_id"])
        if rule.status != "verified" or row.result["status"] != "calculated":
            raise HTTPException(409, "请先核验模型版本并补齐全部指标")
    actual = db.query(ProjectActual).filter_by(project_id=row.project_id, status="verified").first() if row.project_id else None
    if row.kind == "incremental" and not actual:
        raise HTTPException(409, "增量核验前请完成实际结算核验")
    def operation():
        before = serialize(row)
        row.status = "verified"
        row.result = calculate_record(row.kind, row.payload, verified=True, actual_profit=actual.actual_profit if actual else None)
        db.flush()
        history(db, ctx, "operating_record", row.id, "verify", before,
                {**serialize(row), "note": body.note, "evidence_ids": body.evidence_ids})
        return serialize(row)
    return json_ok(mutate(db, ctx, f"v5/records/{row_id}/verify", body, operation))


@router.get("/cities")
def list_cities(db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B", "G", "Brand", "Investor"})
    return json_ok([serialize(row) for row in db.query(CityProfile).filter_by(tenant_id=ctx.tenant.id)])


@router.post("/cities")
def save_city(body: CityIn, db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"G", "B"})
    def operation():
        row = db.query(CityProfile).filter_by(tenant_id=ctx.tenant.id, name=body.name).first()
        before = serialize(row) if row else {}
        if row and row.revision != body.revision:
            raise HTTPException(409, "城市资料已变化，请刷新")
        if not row:
            row = CityProfile(tenant_id=ctx.tenant.id, name=body.name, created_by=ctx.user.id)
            db.add(row)
        row.profile = body.model_dump(exclude={"request_key", "revision", "name"})
        db.flush()
        history(db, ctx, "city_profile", row.id, "save", before, serialize(row))
        return serialize(row)
    return json_ok(mutate(db, ctx, "v5/cities", body, operation))


@router.get("/decision/workspace")
def workspace(db=Depends(get_db), ctx=Depends(context)):
    require_role(ctx, {"B", "Brand", "G", "Investor", "Artist", "C"})
    projects = []
    for project in db.query(Project).filter_by(tenant_id=ctx.tenant.id).order_by(Project.id.desc()):
        try:
            project_access(db, ctx, project.id)
        except HTTPException:
            continue
        row = {"id": project.id, "name": project.name, "city": project.city, "schedule": project.schedule,
               "venue": project.venue, "artist_id": project.artist_id, "artist_name": project.artist_name}
        gate = db.query(Gate).filter_by(project_id=project.id, name="v5六阶段").first()
        row["stage"] = gate.status if gate else "initiation"
        row["risks"] = [serialize(r) for r in db.query(Risk).filter_by(project_id=project.id)]
        row["evidences"] = [dict(id=e.id, name=e.name, status=e.status) for e in db.query(Evidence).filter_by(project_id=project.id)]
        try:
            project_access(db, ctx, project.id, duty="finance")
            reports = db.query(DecisionReport).filter_by(project_id=project.id).order_by(DecisionReport.id.desc()).all()
            row["reports"] = [serialize(r) for r in reports]
            actual = db.query(ProjectActual).filter_by(project_id=project.id).first()
            row["actuals"] = serialize(actual) if actual else None
        except HTTPException:
            row["reports"], row["actuals"] = [], None
        projects.append(row)
    records = []
    for record in db.query(OperatingRecord).filter_by(tenant_id=ctx.tenant.id, owner_id=ctx.user.id).order_by(OperatingRecord.id.desc()):
        try:
            record_access(db, ctx, record.id)
            records.append(serialize(record))
        except HTTPException:
            continue
    stream = []
    posts = db.query(OperatingRecord).filter_by(tenant_id=ctx.tenant.id, kind="artist_post").order_by(OperatingRecord.id.desc()).all()
    for post in posts:
        artist = db.get(Artist, post.payload.get("artist_id"))
        if not artist:
            continue
        comments = db.query(OperatingRecord).filter_by(tenant_id=ctx.tenant.id, kind="comment").all()
        stream.append({"id": post.id, "title": post.title, "artist_id": artist.id, "artist_name": artist.name,
                       "payload": post.payload, "created_at": post.created_at,
                       "comments": [{"id": c.id, "title": c.title, "payload": c.payload} for c in comments
                                    if c.payload.get("post_id") == post.id]})
    dates = []
    for project in projects:
        try:
            day = datetime.fromisoformat(project["schedule"][:10]).date()
        except (ValueError, TypeError):
            continue
        thresholds = DEFAULT_CONFIG["thresholds"]
        latest = (project.get("reports") or [None])[0]
        if latest:
            thresholds = latest["rule_snapshot"]["thresholds"]
        dates.append({"project_id": project["id"], "title": project["name"], "date": day.isoformat(),
                      "application_due": (day - timedelta(days=thresholds.get("application_days", 60))).isoformat(),
                      "permit_due": (day - timedelta(days=thresholds.get("permit_days", 14))).isoformat(),
                      "stage": project["stage"], "source": "项目登记日期"})
    reminders, growth, matches = [], [], []
    for record in records:
        if record["kind"] == "wishlist":
            for show_id in set(record["payload"]["show_ids"]):
                show = db.get(Show, show_id)
                try:
                    day = datetime.fromisoformat(show.date[:10]).date()
                except (ValueError, TypeError, AttributeError):
                    continue
                days = (day - datetime.now().date()).days
                if 0 <= days <= 30 and day.year == record["payload"]["year"]:
                    reminders.append({"show_id": show.id, "title": show.title, "date": day.isoformat(),
                                      "days_remaining": days, "notice": "站内提醒；票务以官方渠道为准"})
        if record["kind"] == "asset":
            matches.append({"record_id": record["id"], "title": record["title"],
                            "projects": [{"id": p["id"], "name": p["name"]} for p in projects
                                         if p["city"] == record["payload"]["city"]],
                            "basis": "同城市的授权项目，容量、档期与品类仍需人工确认"})
    metrics = [r for r in records if r["kind"] == "artist_metrics" and r["status"] == "verified"]
    for city in sorted({r["payload"]["city"] for r in metrics}):
        rows = sorted([r for r in metrics if r["payload"]["city"] == city],
                      key=lambda r: (r["payload"]["observed_at"], r["id"]))
        previous, latest = rows[-2]["payload"] if len(rows) > 1 else {}, rows[-1]["payload"]
        growth.append({"city": city, "date": latest["observed_at"], "fan_count": latest["fan_count"],
                       "fan_growth": latest["fan_count"] - previous["fan_count"]
                       if latest["fan_count"] is not None and previous.get("fan_count") is not None else None,
                       "heat": latest["heat"], "monetization": sum(latest[k] for k in
                       ("artist_fee", "sponsorship", "merchandise", "live_income"))
                       if all(latest[k] is not None for k in ("artist_fee", "sponsorship", "merchandise", "live_income")) else None,
                       "points": [{"date": r["payload"]["observed_at"], "fan_count": r["payload"]["fan_count"],
                                   "heat": r["payload"]["heat"]} for r in rows]})
    checkins = [{"id": r.id, "title": r.title, "payload": r.payload}
                for r in db.query(OperatingRecord).filter_by(tenant_id=ctx.tenant.id, kind="checkin")
                if r.payload.get("public") is True]
    return json_ok({"role": ctx.user.group_code, "projects": projects, "records": records,
                    "reminders": reminders, "growth": growth, "asset_matches": matches, "checkins": checkins,
                    "rules": [serialize(r) for r in db.query(DecisionRuleVersion).filter_by(tenant_id=ctx.tenant.id).order_by(DecisionRuleVersion.id.desc())]
                    if ctx.user.group_code in RULE_READ_ROLES else [],
                    "catalog": builtin_catalog() if ctx.user.group_code in RULE_READ_ROLES else None,
                    "default_config": DEFAULT_CONFIG, "stream": stream, "calendar": dates,
                    "cities": [serialize(c) for c in db.query(CityProfile).filter_by(tenant_id=ctx.tenant.id)]
                    if ctx.user.group_code in {"G", "B"} else [],
                    "shows": [{"id": s.id, "title": s.title, "city": s.city, "date": s.date}
                              for s in db.query(Show)] if ctx.user.group_code == "C" else [],
                    "source_status": {"weather": "待配置真实天气来源", "reputation": "待配置舆情来源",
                                      "permit": "以人工核验批文为准", "ticketing": "以票务快照与实际登记为准"}})
