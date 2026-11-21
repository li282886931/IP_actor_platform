import copy

import pytest
from pydantic import ValidationError

from test_collaboration import collaboration
from test_v5_decision import api, budget, rules


def catalog():
    from app.services.decision_catalog import builtin_catalog
    return builtin_catalog()


def automatic_inputs():
    return dict(**budget(), cost_overrun_ratio=0, weather_risk=.1, reputation_risk=.1,
                demand_verified=True, ticket_price=200, willingness_price=220, audience_match_ratio=.8,
                comparable_artist_fee=250000, fan_growth_ratio=.1, supplier_quotes_verified=True,
                available_funds=500000, sponsorship_verified=True, subsidy_verified=True,
                contracted_sponsorship=50000, days_until_show=80, application_submitted=True,
                foreign_approval_verified=True, copyright_authorized=True, safety_verified=True,
                insurance_verified=True, schedule_conflict=False, scoring_mode="auto", source="项目凭证")


def test_catalog_is_complete_typed_and_independent():
    from app.schemas.decision_platform import RuleConfig
    item = catalog()
    config = RuleConfig.model_validate(item["config"]).model_dump(mode="json")
    assert len(config["dimensions"]) == 12
    assert len(config["conditions"]) == 32
    assert len(config["risk_categories"]) == 12
    assert set(config["auxiliary_models"]) == {"brand_match", "city_fit", "artist_benchmark"}
    assert all(d["metric"] and d["source"] for d in config["dimensions"])
    assert all(c["source"] and c["risk_category"] for c in config["conditions"])
    item["config"]["dimensions"][0]["weight"] = 99
    assert catalog()["config"]["dimensions"][0]["weight"] == 1


def test_auto_scores_use_raw_metrics_no_manual_override_and_no_partial_total():
    from app.services.decision_platform import evaluate_decision
    data, config = automatic_inputs(), catalog()["config"]
    result = evaluate_decision(data, config)
    assert result["score"]["status"] == "calculated"
    assert result["score"]["dimensions"][0]["score"] == 7
    assert result["score"]["dimensions"][6]["score"] == 3.75
    assert result["score"]["dimensions"][0]["raw_value"] == .7
    assert result["score"]["value"] == 79.45
    assert result["score"]["value"] == pytest.approx(sum(d["contribution"] for d in result["score"]["dimensions"]), abs=.005)
    data["weather_risk"] = None
    missing = evaluate_decision(data, config)
    assert missing["score"]["value"] is None
    assert "weather_risk" in missing["score"]["missing"]
    assert len(missing["score"]["dimensions"]) == 12
    data["scores"] = {"ticket_demand": 10}
    with pytest.raises(ValueError, match="自动评分"):
        evaluate_decision(data, config)


@pytest.mark.parametrize("index", range(32))
def test_every_rule_hits_clears_and_missing_is_unresolved(index):
    from app.services.decision_platform import evaluate_conditions
    config = catalog()["config"]
    rule = config["conditions"][index]
    metrics = {}
    ops = {"lt": (-1, 1), "lte": (0, 1), "gt": (1, -1), "gte": (0, -1), "eq": (0, 1)}
    for gate in rule.get("applies_when", []):
        threshold = config["thresholds"].get(gate.get("threshold_ref"), gate.get("value", 0))
        metrics[gate["field"]] = threshold + ops[gate["op"]][0]
    threshold = config["thresholds"].get(rule.get("threshold_ref"), rule.get("value", 0))
    if rule.get("compare_field"):
        metrics[rule["compare_field"]] = threshold = .5
    metrics[rule["field"]] = threshold + ops[rule["op"]][0]
    hit = evaluate_conditions(metrics, config["thresholds"], [rule])
    assert hit["checks"][0]["status"] == "hit", (rule, hit)
    metrics[rule["field"]] = threshold + ops[rule["op"]][1]
    assert evaluate_conditions(metrics, config["thresholds"], [rule])["checks"][0]["status"] == "clear"
    metrics[rule["field"]] = None
    assert evaluate_conditions(metrics, config["thresholds"], [rule])["unresolved"]


def test_applicability_unknown_is_not_false_and_threshold_refs_follow_version():
    from app.services.decision_platform import evaluate_conditions
    config = catalog()["config"]
    conditional = config["conditions"][16]
    assert evaluate_conditions({"sponsorship": 0}, config["thresholds"], [conditional])["checks"][0]["status"] == "skipped"
    assert evaluate_conditions({}, config["thresholds"], [conditional])["checks"][0]["status"] == "unresolved"
    presale = config["conditions"][4]
    config["thresholds"]["presale"] = .2
    assert evaluate_conditions({"presale_ratio": .3}, config["thresholds"], [presale])["hits"] == []


def test_strict_bindings_and_legacy_replay():
    from app.schemas.decision_platform import RuleConfig, DecisionInputs
    from app.services.decision_platform import evaluate_decision
    config = catalog()["config"]
    for field, value in [("floor", 1), ("metric", "fabricated_metric")]:
        bad = copy.deepcopy(config)
        bad["dimensions"][0][field] = value
        with pytest.raises(ValidationError):
            RuleConfig.model_validate(bad)
    with pytest.raises(ValidationError):
        DecisionInputs.model_validate({"scoring_mode": "auto", "scores": {"x": 1}})
    legacy = evaluate_decision(budget(), rules())
    assert legacy["formula_version"] == "decision-v5-1"
    assert "rule_checks" not in legacy
    assert "raw_value" not in str(legacy["score"])


def test_catalog_install_authorization_dedup_and_auto_report(collaboration):
    call, _, project, _ = api(collaboration)
    assert call("get", "/decision/catalog").status_code == 200
    body = {"request_key": "install"}
    installed = call("post", "/decision/catalog/install", body)
    assert installed.status_code == 200, installed.text
    rule = installed.json()["data"]
    assert rule["status"] == "pending"
    assert call("post", "/decision/catalog/install", {"request_key": "second"}).json()["data"]["id"] == rule["id"]
    assert call("post", "/decision/catalog/install", body, account="brand_user").status_code == 403
    inputs = automatic_inputs()
    report_body = {"request_key": "auto", "rule_version_id": rule["id"], "inputs": inputs}
    report = call("post", f"/projects/{project}/report", report_body)
    assert report.status_code == 200, report.text
    row = report.json()["data"]
    assert row["result"]["score"]["status"] == "calculated"
    assert call("get", f'/decision/reports/{row["id"]}/replay').json()["data"]["matches"]
    inputs["scores"] = {"ticket_demand": 10}
    report_body["request_key"] = "override"
    assert call("post", f"/projects/{project}/report", report_body).status_code == 422


@pytest.mark.parametrize("kind,account", [("brand_match", "brand_user"), ("city_fit", "g_user"),
                                        ("artist_benchmark", "artist_user")])
def test_aux_models_snapshot_permissions_and_verification(collaboration, kind, account):
    from app.models import Evidence
    call, sessions, project, grant = api(collaboration)
    grant(account)
    rule = call("post", "/decision/catalog/install", {"request_key": "install"}).json()["data"]
    model = rule["config"]["auxiliary_models"][kind]
    metrics = {c["key"]: .8 for c in model["criteria"]}
    payload = {"metrics": metrics, "rule_version_id": rule["id"], "source": "项目匹配凭证"}
    body = {"request_key": "score", "record_key": "score", "kind": kind, "project_id": project,
            "title": "匹配评分", "payload": payload}
    saved = call("post", "/decision/records", body, account=account)
    assert saved.status_code == 200, saved.text
    row = saved.json()["data"]
    assert row["result"]["value"] == 80
    assert row["payload"]["model_snapshot"] == model
    if kind == "artist_benchmark":
        assert row["payload"]["artist_id"]
    assert call("get", "/decision/workspace", account=account).json()["data"]["rules"]
    assert call("get", "/decision/workspace").json()["data"]["records"] == []
    with sessions() as db:
        evidence = Evidence(project_id=project, name="已核验证明", status="verified", file_url="oss://test/proof")
        db.add(evidence)
        db.commit()
        proof_id = evidence.id
    review = {"request_key": "review", "evidence_ids": [proof_id], "note": "核验完成"}
    assert call("post", f'/decision/records/{row["id"]}/verify', review, account=account).status_code == 409
    verified = call("post", "/decision/rules", {"request_key": "verified", "name": "人工核验规则",
                "config": rule["config"], "source": "已核验参考", "reviewed": True}).json()["data"]
    payload["rule_version_id"] = verified["id"]
    body.update(request_key="update", revision=row["revision"])
    updated = call("post", "/decision/records", body, account=account)
    assert updated.status_code == 200, updated.text
    review["request_key"] = "review2"
    checked = call("post", f'/decision/records/{row["id"]}/verify', review, account=account)
    assert checked.status_code == 200, checked.text
    assert checked.json()["data"]["result"]["verification_status"] == "verified"
    assert call("post", "/decision/records", {**body, "request_key": "forbidden"}, account="c_user").status_code == 403


def test_normalization_weight_direction_and_clamp():
    from app.services.scoring import score_model
    criteria = [
        {"key": "a", "metric": "a", "label": "A", "method": "linear_high", "floor": 0, "ceiling": 1, "max_score": 10, "weight": 3},
        {"key": "b", "metric": "b", "label": "B", "method": "linear_low", "floor": 0, "ceiling": 1, "max_score": 10, "weight": 1},
    ]
    result = score_model({"a": 2, "b": .5}, criteria, 100)
    assert result["value"] == 87.5
    assert result["dimensions"][0]["raw_value"] == 2
    assert score_model({"a": .8}, criteria, 100)["value"] is None


def test_custom_comparison_and_applicability_without_catalog_marker():
    from test_v5_decision import complete_rules
    from app.services.decision_platform import evaluate_decision
    config = complete_rules()
    config["conditions"][0].update(field="expected_occupancy", compare_field="comprehensive_breakeven", op="lt",
                                   applies_when=[{"field": "presale_ratio", "op": "lt", "value": .9}])
    data = budget()
    data.update(expected_occupancy=.1, scores={f"d{i}": 8 for i in range(12)}, source="测试凭证")
    result = evaluate_decision(data, config)
    assert result["rule_checks"][0]["status"] == "hit"
    data["presale_ratio"] = 1
    assert evaluate_decision(data, config)["rule_checks"][0]["status"] == "skipped"


def test_auto_report_verification_stage_and_rule_veto(collaboration):
    from app.models import Evidence
    call, sessions, project, _ = api(collaboration)
    with sessions() as db:
        proof = Evidence(project_id=project, name="真实参数核验", file_url="oss://test/proof", status="verified")
        db.add(proof)
        db.commit()
        evidence_id = proof.id
    config = catalog()["config"]
    config["thresholds"]["large_spend"] = 100000
    rule = call("post", "/decision/rules", {"request_key": "reviewed", "name": "已核验规则",
        "config": config, "source": "项目核验材料", "reviewed": True}).json()["data"]
    inputs = {**automatic_inputs(), "evidence_ids": [evidence_id]}
    row = call("post", f"/projects/{project}/report", {"request_key": "complete-auto",
        "rule_version_id": rule["id"], "inputs": inputs}).json()["data"]
    assert row["result"]["configuration_gaps"] == []
    assert row["result"]["unresolved_rules"] == []
    assert row["result"]["status"] == "ready_for_review"
    review = {"request_key": "verify-auto", "evidence_ids": [evidence_id], "note": "全部指标与模型核验"}
    assert call("post", f'/decision/reports/{row["id"]}/verify', review).status_code == 200
    assert call("post", f"/decision/projects/{project}/stage", {"request_key": "advance-auto",
        "stage": "approval", "report_id": row["id"], "evidence_ids": [evidence_id]}).status_code == 200
    inputs["copyright_authorized"] = False
    vetoed = call("post", f"/projects/{project}/report", {"request_key": "copyright",
        "rule_version_id": rule["id"], "inputs": inputs}).json()["data"]
    assert "R24" in vetoed["result"]["vetoes"]
    review["request_key"] = "verify-veto"
    assert call("post", f'/decision/reports/{vetoed["id"]}/verify', review).status_code == 200
    assert call("post", f"/decision/projects/{project}/stage", {"request_key": "stop-veto",
        "stage": "sponsorship", "report_id": vetoed["id"], "evidence_ids": [evidence_id]}).status_code == 409


def test_aux_input_validation_missing_items_and_all_proofs(collaboration):
    from app.models import Evidence
    call, sessions, project, grant = api(collaboration)
    grant("brand_user")
    rule = call("post", "/decision/rules", {"request_key": "verified", "name": "核验规则",
        "config": catalog()["config"], "source": "参数依据", "reviewed": True}).json()["data"]
    with sessions() as db:
        rows = [Evidence(project_id=project, name="核验材料", file_url="oss://test/p", status=s)
                for s in ("verified", "pending")]
        db.add_all(rows)
        db.commit()
        verified_id, pending_id = [r.id for r in rows]
    metrics = {c["key"]: .8 for c in rule["config"]["auxiliary_models"]["brand_match"]["criteria"]}
    body = {"kind": "brand_match", "record_key": "brand", "title": "匹配评分", "project_id": project,
            "request_key": "brand", "payload": {"rule_version_id": rule["id"], "metrics": metrics,
                                              "source": "样本", "evidence_ids": [pending_id]}}
    saved = call("post", "/decision/records", body, account="brand_user").json()["data"]
    review = {"request_key": "verify", "evidence_ids": [verified_id], "note": "新增核验"}
    assert call("post", f'/decision/records/{saved["id"]}/verify', review, account="brand_user").status_code == 422
    body.update(request_key="missing", revision=saved["revision"])
    body["payload"]["metrics"] = {"target_coverage": .8}
    missing = call("post", "/decision/records", body, account="brand_user").json()["data"]
    assert missing["result"]["value"] is None
    assert len(missing["result"]["missing"]) == 5
    body.update(request_key="bad", revision=missing["revision"])
    body["payload"]["metrics"] = {"target_coverage": 1.01}
    assert call("post", "/decision/records", body, account="brand_user").status_code == 422
    body["payload"]["metrics"] = {"imaginary": .8}
    assert call("post", "/decision/records", body, account="brand_user").status_code == 422
    body["payload"]["model_snapshot"] = rule["config"]["auxiliary_models"]["brand_match"]
    assert call("post", "/decision/records", body, account="brand_user").status_code == 422
