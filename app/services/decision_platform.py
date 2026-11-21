"""Deterministic finance and rule evaluation. No inferred market facts or AI scores."""
from datetime import date
import operator


DEFAULT_CONFIG = {
    "thresholds": {"comprehensive_breakeven": .5, "stop_loss": .3, "public_sale": .85,
                   "artist_fee": .6, "presale": .5, "large_spend": None,
                   "application_days": 60, "permit_days": 14},
    "dimensions": [], "conditions": [],
}


def calculate_scenarios(data):
    required = ("capacity", "base_price", "base_occupancy", "net_ticket_rate", "price_elasticity",
                "show_count", "shared_cost", "cost_per_show", "sponsorship_per_show", "subsidy_per_show")
    missing = [key for key in required if data.get(key) is None]
    scenarios = []
    if not missing:
        count = data["show_count"]
        cost = data["shared_cost"] + data["cost_per_show"] * count
        other = (data["sponsorship_per_show"] + data["subsidy_per_show"]) * count
        for price in data.get("prices", []):
            occupancy = min(1., max(0., data["base_occupancy"] *
                                   (price / data["base_price"]) ** data["price_elasticity"]))
            gross = data["capacity"] * price * count
            net = gross * data["net_ticket_rate"]
            scenarios.append({"price": price, "occupancy": occupancy,
                              "net_ticket_income": round(net * occupancy, 2), "total_cost": cost,
                              "profit": round(net * occupancy + other - cost, 2),
                              "comprehensive_breakeven": max(cost - other, 0) / net})
    cancellation = (max(0, data["cancellation_nonrefundable"] - data["insurance_recovery"])
                    if all(data.get(k) is not None for k in ("cancellation_nonrefundable", "insurance_recovery")) else None)
    overrun = ((data["cost_actual"] - data["cost_budget"]) / data["cost_budget"]
               if data.get("cost_budget") and data.get("cost_actual") is not None else None)
    return {"scenarios": scenarios, "missing_fields": missing, "cancellation_loss": cancellation,
            "cost_overrun_ratio": overrun,
            "formula": "上座率=基准上座率×(票价/基准票价)^弹性，限制在0–100%；总成本=共用成本+单场成本×场次",
            "notice": "弹性和上座率为有来源的假设，测算需回测核验；取消损失仅按不可退支出与可确认保险回款计算"}


def _evaluate_legacy(inputs, config):
    required = ["total_cost", "full_ticket_gross", "net_ticket_rate", "sponsorship", "subsidy",
                "expected_occupancy", "artist_fee", "permit_received", "nonrefundable_spend",
                "stop_loss_amount", "artist_misconduct", "foreign_artist", "public_sale_ratio", "presale_ratio"]
    if inputs.get("foreign_artist") is True:
        required.append("foreign_approval")
    missing = [key for key in required if inputs.get(key) is None]
    finance_fields = ["total_cost", "full_ticket_gross", "net_ticket_rate", "sponsorship", "subsidy", "expected_occupancy"]
    finance = {"status": "pending_input", "pure_breakeven": None, "comprehensive_breakeven": None,
               "predicted_profit": None, "net_full_ticket_gross": None}
    if all(inputs.get(k) is not None for k in finance_fields):
        net_full = inputs["full_ticket_gross"] * inputs["net_ticket_rate"]
        finance = {"status": "calculated", "net_full_ticket_gross": net_full,
                   "pure_breakeven": inputs["total_cost"] / net_full,
                   "comprehensive_breakeven": max(inputs["total_cost"] - inputs["sponsorship"] - inputs["subsidy"], 0) / net_full,
                   "predicted_profit": round(net_full * inputs["expected_occupancy"] + inputs["sponsorship"] +
                                             inputs["subsidy"] - inputs["total_cost"], 2)}
    thresholds = config["thresholds"]
    vetoes, plans, warnings, unresolved = [], [], [], []
    cost = inputs.get("total_cost")
    metrics = {**inputs, **finance}
    metrics["artist_fee_ratio"] = inputs["artist_fee"] / cost if cost and inputs.get("artist_fee") is not None else None
    metrics["stop_loss_ratio"] = inputs["stop_loss_amount"] / cost if cost and inputs.get("stop_loss_amount") is not None else None
    if inputs.get("permit_received") is False and inputs.get("nonrefundable_spend") is not None:
        if thresholds.get("large_spend") is None:
            unresolved.append("large_spend")
        elif inputs["nonrefundable_spend"] > 0 and inputs["nonrefundable_spend"] >= thresholds["large_spend"]:
            vetoes.append("V1")
    if finance["comprehensive_breakeven"] is not None and finance["comprehensive_breakeven"] > thresholds["comprehensive_breakeven"]:
        vetoes.append("V2")
    if metrics["stop_loss_ratio"] is not None and metrics["stop_loss_ratio"] > thresholds["stop_loss"]:
        plans.append("V3")
    if inputs.get("artist_misconduct") is True or (inputs.get("foreign_artist") is True and inputs.get("foreign_approval") is False):
        vetoes.append("V4")
    if inputs.get("public_sale_ratio") is not None and inputs["public_sale_ratio"] < thresholds["public_sale"]:
        vetoes.append("V5")
    for field, threshold, title in [
        ("artist_fee_ratio", "artist_fee", "艺人费用占比预警"), ("presale_ratio", "presale", "预售不足预警"),
    ]:
        value = metrics.get(field)
        if value is not None and (value > thresholds[threshold] if field == "artist_fee_ratio" else value < thresholds[threshold]):
            warnings.append({"key": field, "title": title, "value": value, "threshold": thresholds[threshold]})
    dimensions = config.get("dimensions") or []
    scores = inputs.get("scores") or {}
    missing_scores = [d["key"] for d in dimensions if scores.get(d["key"]) is None]
    score = {"status": "pending_configuration" if not dimensions else "pending_input",
             "value": None, "max": 120, "missing": missing_scores, "dimensions": []}
    if dimensions and not missing_scores:
        total_weight = sum(d["weight"] for d in dimensions)
        contributions = [{"key": d["key"], "label": d["label"], "category": d["category"],
                          "score": scores[d["key"]], "max_score": d["max_score"],
                          "contribution": scores[d["key"]] / d["max_score"] * d["weight"] / total_weight * 120}
                         for d in dimensions]
        score.update(status="calculated", value=round(sum(d["contribution"] for d in contributions), 2), dimensions=contributions)
    hits = []
    operations = {"gt": operator.gt, "gte": operator.ge, "lt": operator.lt, "lte": operator.le, "eq": operator.eq}
    for rule in config.get("conditions") or []:
        value = metrics.get(rule["field"])
        if value is None:
            unresolved.append(rule["field"])
        elif operations[rule["op"]](value, rule["value"]):
            hits.append({**rule, "observed_value": value})
            if rule["severity"] == "veto":
                vetoes.append(rule["key"])
            elif rule["severity"] == "plan":
                plans.append(rule["key"])
    configuration_gaps = (["dimensions"] if not dimensions else []) + (["conditions"] if len(config.get("conditions", [])) < 32 else [])
    status = "vetoed" if vetoes else "pending_input" if missing or missing_scores else "pending_configuration" if unresolved or configuration_gaps else "requires_plan" if plans else "ready_for_review"
    return {"formula_version": "decision-v5-1", "status": status, "finance": finance, "score": score,
            "missing_fields": missing, "configuration_gaps": configuration_gaps,
            "unresolved_rules": sorted(set(unresolved)), "vetoes": vetoes, "plan_triggers": plans,
            "warnings": warnings, "rule_hits": hits,
            "metrics": {k: metrics.get(k) for k in ("artist_fee_ratio", "stop_loss_ratio", "public_sale_ratio", "presale_ratio")}}


def evaluate_conditions(metrics, thresholds, conditions):
    operations = {"gt": operator.gt, "gte": operator.ge, "lt": operator.lt, "lte": operator.le, "eq": operator.eq}
    hits, checks, unresolved = [], [], []

    def compare(item):
        value = metrics.get(item["field"])
        ref = item.get("compare_field") or item.get("threshold_ref")
        threshold = (metrics.get(item["compare_field"]) if item.get("compare_field") else
                     thresholds.get(item["threshold_ref"]) if item.get("threshold_ref") else item["value"])
        missing = ([item["field"]] if value is None else []) + ([ref] if threshold is None and ref else [])
        return (None if missing else operations[item["op"]](value, threshold)), value, threshold, missing

    for rule in conditions:
        gates = [compare(p) for p in rule.get("applies_when", [])]
        status, value, threshold, missing = "skipped", None, None, []
        if not any(g[0] is False for g in gates):
            gate_missing = [key for gate in gates for key in gate[3]]
            if gate_missing:
                status, missing = "unresolved", gate_missing
            else:
                triggered, value, threshold, missing = compare(rule)
                status = "unresolved" if triggered is None else "hit" if triggered else "clear"
        check = {**rule, "status": status, "observed_value": value, "resolved_threshold": threshold,
                 "missing_fields": missing}
        checks.append(check)
        if status == "hit":
            hits.append(check)
        if status == "unresolved":
            unresolved.extend(missing)
    return dict(hits=hits, checks=checks, unresolved=sorted(set(unresolved)))


def evaluate_decision(inputs, config):
    # Stored pre-catalog reports keep both the original computation and exact result shape.
    extended_conditions = any(c.get("compare_field") or c.get("threshold_ref") or c.get("applies_when")
                              for c in config.get("conditions", []))
    if not config.get("catalog_version") and not extended_conditions and inputs.get("scoring_mode") != "auto":
        return _evaluate_legacy(inputs, config)
    from app.services.scoring import score_model
    from app.services.decision_catalog import METRIC_LABELS
    automatic = inputs.get("scoring_mode") == "auto"
    if automatic and inputs.get("scores"):
        raise ValueError("自动评分不接受人工得分覆盖")
    dimensions = config.get("dimensions") or []
    if automatic and any(d.get("method", "manual") == "manual" for d in dimensions):
        raise ValueError("自动评分须使用绑定真实指标的评分维度")
    result = _evaluate_legacy(inputs, {**config, "conditions": []})
    metrics = {**inputs, **result["finance"], **result["metrics"]}
    cost = inputs.get("total_cost")

    def ratio(numerator, denominator):
        return numerator / denominator if numerator is not None and denominator else None

    metrics.update(
        sponsorship_coverage=ratio(inputs.get("sponsorship"), cost),
        subsidy_coverage=ratio(inputs.get("subsidy"), cost),
        profit_margin=ratio(result["finance"]["predicted_profit"], cost),
        occupancy_buffer=(inputs["expected_occupancy"] - result["finance"]["comprehensive_breakeven"]
                          if inputs.get("expected_occupancy") is not None and result["finance"]["comprehensive_breakeven"] is not None else None),
        price_willingness_ratio=ratio(inputs.get("ticket_price"), inputs.get("willingness_price")),
        artist_quote_ratio=ratio(inputs.get("artist_fee"), inputs.get("comparable_artist_fee")),
        funding_coverage=ratio(inputs.get("available_funds"), cost),
        sponsor_received_ratio=ratio(inputs.get("sponsorship"), inputs.get("contracted_sponsorship")),
        funding_gap=(cost - inputs["available_funds"] if cost is not None and inputs.get("available_funds") is not None else None),
    )
    if automatic:
        result["score"] = score_model(metrics, dimensions, 120)
    checks = evaluate_conditions(metrics, config["thresholds"], config.get("conditions") or [])
    result["rule_hits"], result["rule_checks"] = checks["hits"], checks["checks"]
    result["unresolved_rules"] = sorted(set(result["unresolved_rules"] + checks["unresolved"]))
    for hit in checks["hits"]:
        if hit["severity"] == "veto":
            result["vetoes"].append(hit["key"])
        elif hit["severity"] == "plan":
            result["plan_triggers"].append(hit["key"])
    result["configuration_gaps"] = (["dimensions"] if not dimensions else []) + (["conditions"] if len(config.get("conditions", [])) < 32 else [])
    if not inputs.get("source", "").strip():
        result["missing_fields"].append("source")
    result["status"] = ("vetoed" if result["vetoes"] else "pending_input"
                        if result["missing_fields"] or result["score"]["status"] == "pending_input" else "pending_configuration"
                        if result["unresolved_rules"] or result["configuration_gaps"] or result["score"]["status"] != "calculated"
                        else "requires_plan" if result["plan_triggers"] else "ready_for_review")
    result.update(formula_version="decision-v5-2", metrics={k: metrics.get(k) for k in METRIC_LABELS},
                  catalog_version=config.get("catalog_version"), scoring_mode="auto" if automatic else "manual")
    return result


def calculate_incremental(data, *, verified=False, actual_profit=None):
    earned_fields = ("baseline_occupancy", "optimized_occupancy", "full_ticket_gross", "net_ticket_rate")
    earned = ((data["optimized_occupancy"] - data["baseline_occupancy"]) * data["full_ticket_gross"] * data["net_ticket_rate"]
              if all(data.get(k) is not None for k in earned_fields) else None)
    efficient = (data["saved_hours"] * data["hourly_cost"] + data["supplier_savings"]
                 if all(data.get(k) is not None for k in ("saved_hours", "hourly_cost", "supplier_savings")) else None)
    operating = round(earned + efficient, 2) if earned is not None and efficient is not None else None
    return {"potential_avoided_loss": data.get("avoided_projects", 0) * data["potential_loss_per_project"]
            if data.get("potential_loss_per_project") is not None else None,
            "earned_increment": round(earned, 2) if earned is not None else None, "efficiency_increment": efficient,
            "operating_increment": operating,
            "realized_increment": operating if verified and actual_profit is not None else None,
            "share_amount": round(max(operating, 0) * data["share_rate"], 2)
            if verified and actual_profit is not None and actual_profit > 0 and operating is not None and data.get("share_rate") is not None else 0,
            "verification_status": "verified" if verified else "pending",
            "counterfactual_notice": "避坑为反事实估计，不计入已实现收益或分成"}


def calculate_sponsorship(data):
    exposure = (data["onsite_exposures"] * data["onsite_cpm"] / 1000 + data["media_exposures"] * data["media_cpm"] / 1000
                if all(data.get(k) is not None for k in ("onsite_exposures", "onsite_cpm", "media_exposures", "media_cpm")) else None)
    total = exposure + data["rights_value"] if exposure is not None and data.get("rights_value") is not None else None
    return {"exposure_value": exposure, "total_value": total,
            "roi": (total - data["investment"]) / data["investment"] if total is not None and data.get("investment") else None,
            "sales_roi": (data["actual_sales_profit"] - data["investment"]) / data["investment"]
            if data.get("actual_sales_profit") is not None and data.get("investment") else None,
            "valuation_notice": "曝光等价价值与实际销售收益分别核验，不能混同"}


def calculate_investment(data):
    flows = data.get("cashflows") or []
    irr, reason = None, "需同时包含投入和回款"
    if flows and any(x["amount"] < 0 for x in flows) and any(x["amount"] > 0 for x in flows):
        ordered = sorted(flows, key=lambda x: x["date"])
        base = date.fromisoformat(str(ordered[0]["date"]))
        times = [((date.fromisoformat(str(x["date"])) - base).days / 365, x["amount"]) for x in ordered]
        # Conventional single investment then receipts admits a unique root.
        changes = sum((a["amount"] < 0) != (b["amount"] < 0) for a, b in zip(ordered, ordered[1:]) if a["amount"] and b["amount"])
        if changes == 1 and ordered[0]["amount"] < 0 and any(t > 0 for t, _ in times):
            def npv(rate):
                return sum(amount / (1 + rate) ** years for years, amount in times)
            low, high = -.9999, 1.
            while npv(high) > 0 and high < 1e6:
                high *= 2
            if npv(low) >= 0 and npv(high) <= 0:
                for _ in range(120):
                    mid = (low + high) / 2
                    if npv(mid) > 0:
                        low = mid
                    else:
                        high = mid
                irr, reason = (low + high) / 2, ""
            else:
                reason = "给定现金流无可求解的年化回报率"
        else:
            reason = "现金流存在多次正负转换或缺少期间，IRR可能不唯一"
    return {"irr": irr, "irr_note": reason, "net_cashflow": sum(x["amount"] for x in flows) if flows else None,
            "custody_notice": "资金监管仅登记第三方凭证，平台不划转本金"}


def calculate_record(kind, data, *, verified=False, actual_profit=None):
    if kind in {"brand_match", "city_fit", "artist_benchmark"}:
        from app.services.scoring import score_model
        model = data["model_snapshot"]
        result = score_model(data["metrics"], model["criteria"], model["max_total"])
        return {**result, "model": kind, "model_label": model["label"], "source": data["source"],
                "rule_version_id": data["rule_version_id"], "catalog_version": data.get("catalog_version"),
                "verification_status": "verified" if verified else "pending",
                "notice": "有来源输入的适配评分；须人工核验，不代表外部认证或保票承诺"}
    if kind == "incremental":
        return calculate_incremental(data, verified=verified, actual_profit=actual_profit)
    if kind == "sponsorship":
        return calculate_sponsorship(data)
    if kind == "investment":
        return calculate_investment(data)
    if kind == "asset":
        profit = data["operating_income"] - data["operating_cost"] - data["activation_cost"] if all(
            data.get(k) is not None for k in ("operating_income", "operating_cost", "activation_cost")) else None
        return {"activation_profit": profit, "activation_roi": profit / data["activation_cost"]
                if profit is not None and data.get("activation_cost") else None}
    if kind == "impact":
        return {"consumption_impact": data["visitor_spend"] * data["consumption_coefficient"]
                if data.get("visitor_spend") is not None and data.get("consumption_coefficient") is not None and data.get("coefficient_source") else None,
                "subsidy_leverage": data["attributable_revenue"] / data["subsidy"]
                if data.get("attributable_revenue") is not None and data.get("subsidy") else None}
    return {}
