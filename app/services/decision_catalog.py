"""Reviewable platform proposals; never inferred external facts or calibrated standards."""
from copy import deepcopy

CATALOG_VERSION = "v5-proposal-1"
PROPOSAL = "平台建议，等权及线性区间须人工核验和回测"
METRIC_LABELS = dict([
    ("pure_breakeven", "纯票房保本率"), ("comprehensive_breakeven", "综合保本率"),
    ("artist_fee_ratio", "艺人费用比例"), ("stop_loss_ratio", "止损比例"),
    ("public_sale_ratio", "公售比例"), ("presale_ratio", "预售比例"),
    ("predicted_profit", "预测利润"), ("expected_occupancy", "预计上座率"),
    ("cost_overrun_ratio", "成本超支比例"), ("weather_risk", "天气风险值"),
    ("reputation_risk", "舆情风险值"), ("schedule_conflict", "档期冲突"),
    ("net_ticket_rate", "净票房率"), ("sponsorship_coverage", "赞助覆盖率"),
    ("subsidy_coverage", "补贴覆盖率"), ("profit_margin", "盈利缓冲比例"),
    ("permit_received", "批文已收到"), ("occupancy_buffer", "上座安全余量"),
    ("demand_verified", "购票需求已核验"), ("price_willingness_ratio", "定价/意愿价"),
    ("audience_match_ratio", "受众匹配比例"), ("artist_quote_ratio", "报价/可比报价"),
    ("fan_growth_ratio", "粉丝增长比例"), ("supplier_quotes_verified", "供应商报价已核验"),
    ("funding_coverage", "资金覆盖率"), ("sponsorship", "已落实赞助"),
    ("subsidy", "已落实补贴"), ("sponsorship_verified", "赞助已核验"),
    ("subsidy_verified", "补贴已核验"), ("sponsor_received_ratio", "赞助实收比例"),
    ("contracted_sponsorship", "约定赞助金额"), ("funding_gap", "资金缺口"),
    ("days_until_show", "距演出天数"), ("application_submitted", "报批已提交"),
    ("foreign_artist", "涉外艺人"), ("foreign_approval", "涉外审批已收到"),
    ("foreign_approval_verified", "涉外证明已核验"), ("copyright_authorized", "版权授权完成"),
    ("safety_verified", "现场安全已核验"), ("insurance_verified", "保险已核验"),
    ("artist_misconduct", "存在劣迹风险"),
])


def dimension(key, label, metric, category="income", method="linear_high"):
    return dict(key=key, label=label, metric=metric, category=category, method=method,
                floor=0, ceiling=1, weight=1, max_score=10, source=PROPOSAL)


def predicate(field, op="eq", value=1, threshold_ref=None):
    return dict(field=field, op=op, value=value, threshold_ref=threshold_ref)


def builtin_catalog():
    from app.services.decision_platform import DEFAULT_CONFIG
    dimensions = [
        dimension("ticket_demand", "票房需求", "expected_occupancy"),
        dimension("presale_certainty", "预售确定性", "presale_ratio"),
        dimension("ticket_efficiency", "票房实收效率", "net_ticket_rate"),
        dimension("sponsor_support", "赞助支撑", "sponsorship_coverage"),
        dimension("subsidy_support", "补贴支撑", "subsidy_coverage"),
        dimension("profit_buffer", "盈利缓冲", "profit_margin"),
        *[dimension(k, label, metric, "risk", method) for k, label, metric, method in [
            ("artist_fee_safety", "艺人费用安全", "artist_fee_ratio", "linear_low"),
            ("stop_loss_safety", "止损安全", "stop_loss_ratio", "linear_low"),
            ("cost_discipline", "成本纪律", "cost_overrun_ratio", "linear_low"),
            ("permit_readiness", "批文准备", "permit_received", "linear_high"),
            ("weather_resilience", "天气韧性", "weather_risk", "linear_low"),
            ("reputation_safety", "舆情安全", "reputation_risk", "linear_low"),
        ]],
    ]
    categories = [
        ("demand", "需求票房", "购票样本、预售与保本口径", "补需求核验和保守情景"),
        ("pricing", "票价", "意愿价样本、定价和弹性来源", "调整定价或验证弹性"),
        ("artist_fee", "艺人费用", "正式报价与可比报价", "比价与合同分担"),
        ("artist_appeal", "艺人号召力", "粉丝增长与受众来源", "复核触达和购票转化"),
        ("procurement", "成本采购", "供应商报价与预算", "预算偏差和成本止损"),
        ("funding", "资金", "可用资金与到账证明", "登记缺口和补足计划"),
        ("sponsorship", "赞助补贴", "合同、批复与实收", "核验落实及到账缺口"),
        ("permit", "审批许可", "报批回执、批文及涉外证明", "倒排时限与停止支出"),
        ("copyright", "版权", "真实授权证明", "授权完成前暂停推进"),
        ("safety", "安全保险", "安全方案、保险及证明", "安全核验和不可抗力预案"),
        ("weather", "天气不可抗力", "有来源的天气风险量化", "不可抗力预案"),
        ("reputation", "舆情档期", "舆情来源、档期和劣迹证明", "舆情预案及合规核验"),
    ]
    conditions = []
    def add(field, op, value, severity, message, category, source="平台建议，待回测",
            compare_field=None, threshold_ref=None, applies_when=None):
        conditions.append(dict(key=f"R{len(conditions)+1:02}", field=field, op=op, value=value,
                               severity=severity, message=message, risk_category=category, source=source,
                               compare_field=compare_field, threshold_ref=threshold_ref,
                               applies_when=applies_when or []))
    derived, document = "真实参数比较推导，输入须核验", "产品说明书v5明确约束"
    add("expected_occupancy", "lt", 0, "plan", "预计上座不足保本，登记止损或补收入预案", "demand", derived, "comprehensive_breakeven")
    add("pure_breakeven", "gt", 1, "warning", "票房不能单独覆盖成本", "demand", derived)
    add("comprehensive_breakeven", "gt", .4, "warning", "安全余量收紧", "demand", "平台建议，参考文档30–40%区间，待回测")
    add("occupancy_buffer", "lt", .1, "plan", "补保守情景预案", "demand")
    add("presale_ratio", "lt", .5, "warning", "预售不足，需求预警", "demand", document, threshold_ref="presale")
    add("presale_ratio", "lt", 0, "plan", "登记预售止损预案", "demand", derived, "comprehensive_breakeven")
    add("demand_verified", "eq", 0, "warning", "补购票样本与转化凭证", "demand")
    add("price_willingness_ratio", "gt", 1, "warning", "调整定价或验证弹性", "pricing", derived)
    add("audience_match_ratio", "lt", .6, "warning", "优化定位与触达", "artist_appeal")
    add("artist_fee_ratio", "gt", .6, "warning", "优化艺人合同分担", "artist_fee", document, threshold_ref="artist_fee")
    add("artist_quote_ratio", "gt", 1.1, "warning", "补比价与溢价说明", "artist_fee")
    add("fan_growth_ratio", "lt", 0, "warning", "复核艺人号召力", "artist_appeal", derived)
    add("cost_overrun_ratio", "gt", .1, "plan", "登记成本止损预案", "procurement")
    add("cost_overrun_ratio", "gt", 0, "warning", "预算偏差预警", "procurement", derived)
    add("supplier_quotes_verified", "eq", 0, "warning", "补实际报价凭证", "procurement")
    add("funding_coverage", "lt", 1, "plan", "登记资金保障预案", "funding", derived)
    add("sponsorship_verified", "eq", 0, "warning", "补赞助合同与到账证明", "sponsorship", applies_when=[predicate("sponsorship", "gt", 0)])
    add("subsidy_verified", "eq", 0, "warning", "补补贴批复与到账证明", "sponsorship", applies_when=[predicate("subsidy", "gt", 0)])
    add("sponsor_received_ratio", "lt", 1, "warning", "赞助到账缺口预警", "sponsorship", derived, applies_when=[predicate("contracted_sponsorship", "gt", 0)])
    add("funding_gap", "gt", 0, "plan", "登记资金缺口与补足计划", "funding", derived)
    add("application_submitted", "eq", 0, "warning", "报批时限预警", "permit", document,
        applies_when=[predicate("days_until_show", "lt", 60, "application_days")])
    add("permit_received", "eq", 0, "plan", "登记批文止损预案", "permit", document,
        applies_when=[predicate("days_until_show", "lt", 14, "permit_days")])
    add("foreign_approval_verified", "eq", 0, "warning", "补涉外证明核验", "permit",
        applies_when=[predicate("foreign_artist"), predicate("foreign_approval")])
    add("copyright_authorized", "eq", 0, "veto", "版权授权未完成，暂停推进", "copyright", "平台建议硬门槛，须人工核验")
    add("safety_verified", "eq", 0, "veto", "现场安全未核验，暂停推进", "safety", "平台建议硬门槛，须人工核验")
    add("insurance_verified", "eq", 0, "plan", "登记保险与不可抗力预案", "safety")
    add("weather_risk", "gte", .7, "plan", "登记天气不可抗力预案", "weather")
    add("reputation_risk", "gte", .7, "plan", "登记舆情预案", "reputation")
    add("schedule_conflict", "eq", 1, "plan", "登记阵容与档期预案", "reputation", derived)
    add("artist_misconduct", "eq", 1, "veto", "劣迹风险否决并留档", "reputation", document)
    add("public_sale_ratio", "lt", .85, "warning", "公售比例不足，渠道整改并保留V5否决", "demand", document, threshold_ref="public_sale")
    add("stop_loss_ratio", "gt", .3, "plan", "登记止损预案", "funding", document, threshold_ref="stop_loss")
    auxiliary = {}
    for key, label, pairs in [
        ("brand_match", "品牌匹配", [("target_coverage", "目标受众覆盖"), ("city_match", "城市匹配"),
         ("age_match", "年龄匹配"), ("purchasing_match", "消费力匹配"), ("interest_overlap", "兴趣重合"), ("rights_delivery", "权益可交付")]),
        ("city_fit", "城市资产适配", [("culture_fit", "本地文化契合"), ("capacity_coverage", "容量覆盖"),
         ("schedule_available", "档期可用"), ("consumption_fit", "消费带动契合"), ("funding_certainty", "资金确定性"), ("environment_compliance", "环保合规")]),
        ("artist_benchmark", "艺人对标", [("fan_growth", "相对基准粉丝增长"), ("city_heat", "相对基准城市热度"),
         ("ticket_conversion", "相对基准购票转化"), ("monetization", "相对基准变现效率"), ("delivery", "相对基准履约表现")]),
    ]:
        criteria = [dict(key=k, metric=k, label=l, method="linear_high", floor=0, ceiling=1,
                         weight=1, max_score=10, source=PROPOSAL) for k, l in pairs]
        auxiliary[key] = dict(label=label, max_total=100, criteria=criteria, source=PROPOSAL)
    config = deepcopy(DEFAULT_CONFIG)
    config.update(catalog_version=CATALOG_VERSION, dimensions=dimensions, conditions=conditions,
                  risk_categories=[dict(key=k, label=l, verification=v, action=a) for k, l, v, a in categories],
                  auxiliary_models=auxiliary)
    return dict(version=CATALOG_VERSION, name="v5完整规则与评分建议包", source=PROPOSAL,
                notice="32条为文档约束、参数推导及平台建议；默认待核验，分数不能覆盖红线。",
                metrics=deepcopy(METRIC_LABELS), config=config)
