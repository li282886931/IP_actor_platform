import copy

import pytest

from test_collaboration import collaboration


def budget(**updates):
    return dict(total_cost=400000, full_ticket_gross=1000000, net_ticket_rate=.88,
                sponsorship=50000, subsidy=10000, expected_occupancy=.7,
                artist_fee=250000, permit_received=True, nonrefundable_spend=0,
                stop_loss_amount=100000, artist_misconduct=False, foreign_artist=False,
                foreign_approval=False, public_sale_ratio=.85, presale_ratio=.6, **updates)


def rules():
    return {
        "thresholds": {"comprehensive_breakeven": .5, "stop_loss": .3, "public_sale": .85,
                       "artist_fee": .6, "presale": .5, "large_spend": 100000},
        "dimensions": [], "conditions": [],
    }


def evaluate(inputs=None, config=None):
    from app.services.decision_platform import evaluate_decision
    return evaluate_decision(inputs or budget(), config or rules())


def test_dual_breakeven_uses_net_rate_sponsorship_subsidy():
    result = evaluate()
    assert result["finance"]["pure_breakeven"] == pytest.approx(400000 / 880000)
    assert result["finance"]["comprehensive_breakeven"] == pytest.approx(340000 / 880000)
    assert result["finance"]["predicted_profit"] == 276000
    assert result["score"]["value"] is None
    assert result["score"]["status"] == "pending_configuration"
    assert "艺人费用占比预警" in [x["title"] for x in result["warnings"]]


@pytest.mark.parametrize("field,value,redline", [
    ("total_cost", 510001, "V2"), ("public_sale_ratio", .849, "V5"),
    ("artist_misconduct", True, "V4"),
])
def test_veto_boundaries(field, value, redline):
    data = budget()
    data.update({field: value, "sponsorship": 0, "subsidy": 0, "net_ticket_rate": 1})
    assert redline in evaluate(data)["vetoes"]


def test_stoploss_is_plan_trigger_and_missing_permit_is_not_automatically_a_veto():
    data = budget()
    data.update(permit_received=False, nonrefundable_spend=0, stop_loss_amount=120001)
    result = evaluate(data)
    assert "V1" not in result["vetoes"]
    assert "V3" in result["plan_triggers"]
    data["nonrefundable_spend"] = 100000
    assert "V1" in evaluate(data)["vetoes"]


def test_missing_real_parameters_does_not_emit_synthetic_numbers():
    data = budget()
    data.pop("net_ticket_rate")
    result = evaluate(data)
    assert result["finance"]["status"] == "pending_input"
    assert result["finance"]["pure_breakeven"] is None
    assert "net_ticket_rate" in result["missing_fields"]
    assert result["status"] == "pending_input"


def test_configurable_score_and_if_then_are_replayable():
    config = rules()
    config["dimensions"] = [
        {"key": f"d{i}", "label": f"已核验维度{i}", "category": "income" if i < 6 else "risk",
         "weight": 1, "max_score": 10} for i in range(12)
    ]
    config["conditions"] = [{"key": "cost", "field": "artist_fee_ratio", "op": "gt",
                              "value": .6, "severity": "warning", "message": "优化艺人合同"}]
    data = budget()
    data["scores"] = {f"d{i}": 8 for i in range(12)}
    before = copy.deepcopy((data, config))
    result = evaluate(data, config)
    assert result["score"]["value"] == 96
    assert result["rule_hits"][0]["message"] == "优化艺人合同"
    assert (data, config) == before


def test_incremental_share_excludes_counterfactual_and_unverified_or_unprofitable():
    from app.services.decision_platform import calculate_incremental
    data = dict(avoided_projects=2, potential_loss_per_project=100000,
                baseline_occupancy=.5, optimized_occupancy=.7,
                full_ticket_gross=1000000, net_ticket_rate=.88,
                saved_hours=10, hourly_cost=200, supplier_savings=3000,
                share_rate=.05)
    assert calculate_incremental(data, verified=True, actual_profit=10000)["share_amount"] == 9050
    assert calculate_incremental(data, verified=False, actual_profit=10000)["share_amount"] == 0
    result = calculate_incremental(data, verified=True, actual_profit=-1)
    assert result["share_amount"] == 0
    assert result["potential_avoided_loss"] == 200000
    assert result["operating_increment"] == 181000


def test_dated_irr_and_sponsorship_use_real_inputs():
    from app.services.decision_platform import calculate_investment, calculate_sponsorship
    cashflows = [{"date": "2025-01-01", "amount": -10000}, {"date": "2026-01-01", "amount": 11000}]
    assert calculate_investment({"cashflows": cashflows})["irr"] == pytest.approx(.1, abs=.0001)
    assert calculate_investment({"cashflows": [{"date": "2026-01-01", "amount": 1}]})["irr"] is None
    value = calculate_sponsorship(dict(investment=50000, onsite_exposures=100000, media_exposures=200000,
                                     onsite_cpm=200, media_cpm=100, rights_value=20000))
    assert value["total_value"] == 60000
    assert value["roi"] == .2


def api(collaboration):
    client, sessions, ids, project, _, _, _, grant = collaboration
    def call(method, path, body=None, account="b_user"):
        return getattr(client, method)(path, headers=ids[account][0], **({"json": body} if body is not None else {}))
    return call, sessions, project, grant


def test_report_auth_idempotency_replay_and_actuals(collaboration):
    call, sessions, project, grant = api(collaboration)
    assert call("get", f"/projects/{project}/report", account="investor_user").status_code == 403
    assert grant("investor_user").status_code == 200
    config = call("post", "/decision/rules", {"request_key": "rules", "name": "v5待回测",
                  "config": rules(), "source": "说明书p11", "reviewed": False})
    assert config.status_code == 200, config.text
    rule_id = config.json()["data"]["id"]
    body = {"request_key": "report", "rule_version_id": rule_id, "inputs": budget()}
    report = call("post", f"/projects/{project}/report", body)
    assert report.status_code == 200, report.text
    report = report.json()["data"]
    assert report["verification_status"] == "pending"
    assert call("post", f"/projects/{project}/report", body).json()["data"]["id"] == report["id"]
    assert call("get", f'/decision/reports/{report["id"]}/replay').json()["data"]["matches"] is True
    actual = call("put", f"/projects/{project}/actuals", {
        "request_key": "actuals", "actual_attendance": 700, "actual_revenue": 800000,
        "actual_cost": 400000, "notes": "结算数据"})
    assert actual.status_code == 200, actual.text
    assert actual.json()["data"]["actual_profit"] == 400000
    result = call("post", f'/reports/{report["id"]}/calibrate', {
        "request_key": "calibrate", "attribution": "实收票房偏差", "config": rules()})
    assert result.status_code == 200, result.text
    assert result.json()["data"]["rule"]["status"] == "pending"
    assert call("get", f'/decision/reports/{report["id"]}/replay').json()["data"]["matches"] is True


def test_unverified_report_cannot_advance_and_records_are_account_scoped(collaboration):
    call, _, project, _ = api(collaboration)
    stage = call("post", f"/decision/projects/{project}/stage", {
        "request_key": "stage", "stage": "approval", "report_id": 1, "evidence_ids": []})
    assert stage.status_code in (404, 409)
    wish = {"request_key": "wish", "kind": "wishlist", "record_key": "2026", "title": "年度清单",
            "payload": {"year": 2026, "show_ids": [], "note": "想看现场"}}
    result = call("post", "/decision/records", wish, account="c_user")
    assert result.status_code == 200, result.text
    assert call("get", "/decision/workspace", account="b_user").json()["data"]["records"] == []
    assert len(call("get", "/decision/workspace", account="c_user").json()["data"]["records"]) == 1


def test_invalid_rule_dimensions_and_negative_cash_amount_rejected(collaboration):
    call, _, project, _ = api(collaboration)
    bad = rules()
    bad["dimensions"] = [{"key": "one", "label": "一项", "category": "income", "weight": 1, "max_score": 10}]
    assert call("post", "/decision/rules", {"request_key": "invalid-rule", "name": "规则", "config": bad,
                "source": "实际依据"}).status_code == 422
    assert call("put", f"/projects/{project}/actuals", {
        "request_key": "negative", "actual_cost": -1}).status_code == 422


def test_city_assets_social_stream_and_privacy(collaboration):
    call, _, project, grant = api(collaboration)
    city = call("post", "/cities", {"request_key": "city", "name": "北京", "source": "统计来源",
                                    "population": 100000, "genres": ["流行"]}, account="g_user")
    assert city.status_code == 200, city.text
    assert call("get", "/cities", account="g_user").json()["data"][0]["name"] == "北京"
    post = call("post", "/decision/records", {"request_key": "post", "kind": "artist_post",
                "title": "新作品", "record_key": "work", "payload": {"content": "新作品已发布", "post_type": "work"}},
                account="artist_user")
    assert post.status_code == 200, post.text
    post_id = post.json()["data"]["id"]
    comment = call("post", "/decision/records", {"request_key": "comment", "kind": "comment",
                  "title": "作品评论", "record_key": "one", "payload": {"post_id": post_id, "content": "期待现场"}},
                  account="c_user")
    assert comment.status_code == 200, comment.text
    stream = call("get", "/decision/workspace", account="c_user").json()["data"]["stream"]
    assert stream[0]["comments"][0]["payload"]["content"] == "期待现场"
    assert "owner_id" not in stream[0]
    grant("g_user")
    result = call("post", "/decision/records", {"request_key": "impact", "kind": "impact",
                  "project_id": project, "record_key": "impact", "title": "消费带动",
                  "payload": {"city": "上海", "period": "2026年"}}, account="g_user")
    assert result.status_code == 422


def test_record_revision_evidence_and_missing_metrics(collaboration):
    call, _, project, grant = api(collaboration)
    grant("brand_user")
    body = {"request_key": "sponsor", "kind": "sponsorship", "project_id": project,
            "record_key": "sponsor", "title": "权益测算", "payload": {"investment": 1000}}
    row = call("post", "/decision/records", body, account="brand_user")
    assert row.status_code == 200, row.text
    row = row.json()["data"]
    assert row["result"]["roi"] is None
    body["request_key"] = "stale"
    body["revision"] = row["revision"] + 1
    assert call("post", "/decision/records", body, account="brand_user").status_code == 409
    assert call("post", f'/decision/records/{row["id"]}/verify', {
        "request_key": "verify", "evidence_ids": [99999], "note": "核验"}, account="brand_user").status_code == 422


def complete_rules():
    config = rules()
    config["dimensions"] = [
        {"key": f"d{i}", "label": f"测试维度{i}", "category": "income" if i < 6 else "risk",
         "weight": 1, "max_score": 10} for i in range(12)]
    config["conditions"] = [
        {"key": f"c{i}", "field": "expected_occupancy", "op": "lt", "value": .1,
         "severity": "warning", "message": "测试规则"} for i in range(32)]
    return config


def reviewed_report(collaboration):
    call, sessions, project, _ = api(collaboration)
    from app.models import Evidence
    with sessions() as db:
        row = Evidence(project_id=project, name="核验凭证", file_url="oss://test/proof", status="verified")
        db.add(row)
        db.commit()
        evidence_id = row.id
    rule = call("post", "/decision/rules", {"request_key": "complete-rule", "name": "核验配置",
                "source": "测试凭证", "reviewed": True, "config": complete_rules()}).json()["data"]
    inputs = budget()
    inputs.update(scores={f"d{i}": 8 for i in range(12)}, evidence_ids=[evidence_id])
    report = call("post", f"/projects/{project}/report", {"request_key": "complete-report",
                  "rule_version_id": rule["id"], "inputs": inputs}).json()["data"]
    response = call("post", f'/decision/reports/{report["id"]}/verify', {
        "request_key": "report-verify", "evidence_ids": [evidence_id], "note": "核验完成"})
    assert response.status_code == 200, response.text
    return call, project, report, evidence_id


def test_stage_sequence_retry_and_settlement_gate(collaboration):
    call, project, report, evidence = reviewed_report(collaboration)
    for stage in ("approval", "sponsorship", "ticketing", "execution"):
        body = {"request_key": f"stage-{stage}", "stage": stage,
                "report_id": report["id"], "evidence_ids": [evidence]}
        response = call("post", f"/decision/projects/{project}/stage", body)
        assert response.status_code == 200, response.text
        assert call("post", f"/decision/projects/{project}/stage", body).json() == response.json()
    body = {"request_key": "stage-review", "stage": "review",
            "report_id": report["id"], "evidence_ids": [evidence]}
    assert call("post", f"/decision/projects/{project}/stage", body).status_code == 409
    assert call("put", f"/projects/{project}/actuals", {"request_key": "settle",
        "actual_attendance": 700, "actual_revenue": 800000, "actual_cost": 400000,
        "verified": True, "evidence_ids": [evidence]}).status_code == 200
    assert call("post", f"/decision/projects/{project}/stage", body).status_code == 200


def test_new_rule_invalidates_stage_report_without_rewriting_history(collaboration):
    call, project, report, evidence = reviewed_report(collaboration)
    call("post", "/decision/rules", {"request_key": "new-rule", "name": "新配置", "source": "新核验",
         "reviewed": True, "config": complete_rules()})
    assert call("post", f"/decision/projects/{project}/stage", {
        "request_key": "old-report-stage", "stage": "approval", "report_id": report["id"],
        "evidence_ids": [evidence]}).status_code == 409
    assert call("get", f'/decision/reports/{report["id"]}/replay').json()["data"]["matches"]


def test_real_pricing_elasticity_multishow_and_force_majeure():
    from app.services.decision_platform import calculate_scenarios
    result = calculate_scenarios({
        "capacity": 1000, "base_price": 100, "base_occupancy": .5, "net_ticket_rate": .9,
        "price_elasticity": -1, "prices": [80, 100, 120], "show_count": 2,
        "shared_cost": 10000, "cost_per_show": 30000, "sponsorship_per_show": 5000,
        "subsidy_per_show": 0, "cancellation_nonrefundable": 20000, "insurance_recovery": 5000,
        "cost_actual": 80000, "cost_budget": 70000,
    })
    assert result["scenarios"][0]["occupancy"] == pytest.approx(.625)
    assert result["scenarios"][0]["profit"] == pytest.approx(30000)
    assert result["cancellation_loss"] == 15000
    assert result["cost_overrun_ratio"] == pytest.approx(10000 / 70000)
    missing = calculate_scenarios({"capacity": 1000, "prices": [100]})
    assert missing["scenarios"] == []
    assert "price_elasticity" in missing["missing_fields"]


def test_scenarios_require_finance_grant_and_validate_real_bounds(collaboration):
    call, _, project, grant = api(collaboration)
    path = f"/decision/projects/{project}/scenarios"
    assert call("post", path, {"prices": [100]}, account="investor_user").status_code == 403
    grant("investor_user")
    assert call("post", path, {"prices": [100]}, account="investor_user").json()["data"]["scenarios"] == []
    assert call("post", path, {"prices": [0]}).status_code == 422
    assert call("post", path, {"price_elasticity": 1}).status_code == 422


def test_workspace_builds_private_reminders_public_checkins_and_verified_growth(collaboration):
    call, sessions, project, grant = api(collaboration)
    from app.models import OperatingRecord, Show
    from datetime import date, timedelta
    grant("artist_user")
    with sessions() as db:
        show = db.query(Show).first()
        show.date = (date.today() + timedelta(days=5)).isoformat()
        db.commit()
        show_id = show.id
    for key, public in (("private", False), ("public", True)):
        response = call("post", "/decision/records", {"request_key": key, "kind": "checkin",
            "record_key": key, "title": key, "payload": {"show_id": show_id,
             "attended_at": "2026-01-01", "content": key, "public": public}}, account="c_user")
        assert response.status_code == 200, response.text
    call("post", "/decision/records", {"request_key": "remind", "kind": "wishlist", "record_key": "remind",
        "title": "本年计划", "payload": {"year": date.today().year, "show_ids": [show_id]}}, account="c_user")
    audience = call("get", "/decision/workspace", account="c_user").json()["data"]
    assert audience["reminders"][0]["show_id"] == show_id
    other = call("get", "/decision/workspace", account="b_user").json()["data"]
    assert other["reminders"] == []
    assert [r["payload"]["content"] for r in other["checkins"]] == ["public"]
    for day, fans in (("2026-01-01", 100), ("2026-02-01", 120)):
        row = call("post", "/decision/records", {"request_key": day, "kind": "artist_metrics",
            "project_id": project, "title": day, "record_key": day,
            "payload": {"observed_at": day, "city": "北京", "fan_count": fans}}, account="artist_user").json()["data"]
        with sessions() as db:
            db.get(OperatingRecord, row["id"]).status = "verified"
            db.commit()
    artist = call("get", "/decision/workspace", account="artist_user").json()["data"]
    assert artist["growth"][0]["fan_growth"] == 20
    assert other.get("growth", []) == []


def test_miniapp_reads_same_report_and_respects_finance_grants(collaboration):
    call, project, report, _ = reviewed_report(collaboration)
    payload = call("get", f"/miniapp/screens/S34?project_id={project}").json()["data"]
    assert payload["options"]["decision_v5"]["report_id"] == report["id"]
    assert payload["options"]["decision_v5"]["items"][0]["value"] == "45.45%"
    hidden = call("get", f"/miniapp/screens/S34?project_id={project}", account="brand_user")
    assert hidden.status_code == 200
    assert "decision_v5" not in hidden.json()["data"]["options"]
