"""Isolated HTTP acceptance for the complete catalog and actual scoring workflows."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("/tmp/ip_actor_v5_rule_models")
BASE = "http://127.0.0.1:15173"


def serve():
    os.environ["DATABASE_URL"] = "sqlite://"
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    import pytest
    import uvicorn
    from test_collaboration import collaboration
    from test_main import app_module
    from app.models import Evidence
    patch = pytest.MonkeyPatch()
    fixture = collaboration.__wrapped__(patch)
    bundle = next(fixture)
    for account in ("brand_user", "g_user", "artist_user", "investor_user"):
        bundle[-1](account)
    with bundle[1]() as db:
        evidence = Evidence(project_id=bundle[3], name="隔离验收凭证", file_url="oss://test/proof", status="verified")
        db.add(evidence)
        db.commit()
        evidence_id = evidence.id
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "fixture.json").write_text(json.dumps({"evidence_id": evidence_id}))
    try:
        uvicorn.run(app_module.app, host="127.0.0.1", port=18001, log_level="warning")
    finally:
        fixture.close()
        patch.undo()


def verify():
    from playwright.sync_api import expect, sync_playwright
    proof_id = json.loads((OUTPUT / "fixture.json").read_text())["evidence_id"]
    results, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def login(account, route):
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE)
            page.wait_for_load_state("networkidle")
            page.get_by_label("账号", exact=True).fill(account)
            page.get_by_label("密码", exact=True).fill("123456")
            page.get_by_label("验证码", exact=True).fill("ABCD")
            page.get_by_role("button", name="登录", exact=True).click()
            expect(page.get_by_role("navigation", name="主导航", exact=True)).to_be_visible()
            page.goto(BASE + route)
            page.wait_for_load_state("networkidle")
            return context, page

        def capture(page, name):
            assert not page.locator('[role="alert"]').count(), page.locator('[role="alert"]').all_inner_texts()
            assert "[object Object]" not in page.locator("main").inner_text()
            for width in (1440, 390):
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                page.evaluate("window.scrollTo(0, 0)")
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (name, width)
                page.screenshot(path=str(OUTPUT / f"{name}-{width}.png"), full_page=True)
                results.append({"flow": name, "width": width, "status": "passed"})

        context, page = login("b_user", "/operations/decision")
        page.get_by_text("规则版本与评分配置", exact=True).click()
        page.get_by_role("button", name="安装待核验规则包", exact=True).click()
        expect(page.get_by_label("使用规则版本")).to_contain_text("v5完整规则与评分建议包")
        page.get_by_role("button", name="载入完整建议包", exact=True).click()
        editor = page.locator(".decision-rule-editor")
        editor.get_by_text("指标绑定、权重与归一参数", exact=True).first.click()
        page.get_by_label("维度1上界", exact=True).fill("2")
        page.get_by_label("新版本名称", exact=True).fill("完整模型隔离验收")
        page.get_by_label("规则来源与回测依据", exact=True).fill("隔离测试参数，非生产核验")
        editor.get_by_role("checkbox").check()
        page.get_by_role("button", name="保存新规则版本", exact=True).click()
        expect(page.get_by_label("使用规则版本")).to_contain_text("完整模型隔离验收")
        rule_select = page.get_by_label("使用规则版本", exact=True)
        rule_id = rule_select.locator("option").nth(1).get_attribute("value")
        rule_select.select_option(rule_id)
        expect(page.get_by_label("评分方式")).to_have_value("auto")
        fields = {
            "总成本（元）": "400000", "满场票房（元）": "1000000", "净票房率（0–1）": ".88",
            "已落实赞助（元）": "50000", "已落实补贴（元）": "10000", "预计上座率（0–1）": ".7",
            "艺人费用（元）": "250000", "不可退支出（元）": "0", "止损金额（元）": "100000",
            "公售比例（0–1）": ".85", "预售比例（0–1）": ".6", "成本超支比例（实际/预算−1）": "0",
            "有来源的天气风险值（0–1）": ".1", "有来源的舆情风险值（0–1）": ".1",
            "参数来源说明": "隔离测试材料", "证明材料编号（逗号分隔）": str(proof_id),
        }
        for label, value in fields.items():
            page.get_by_label(label, exact=True).fill(value)
        for label, value in {"批文已收到": "true", "存在劣迹风险": "false",
                             "涉及涉外艺人": "false", "涉外审批已收到": "false", "已确认档期冲突": "false"}.items():
            page.get_by_label(label, exact=True).select_option(value)
        page.get_by_text("完整规则参数：需求、报价、资金与合规", exact=True).click()
        for label, value in {"项目定价（元）": "200", "有来源购票意愿价（元）": "220",
            "受众匹配比例（0–1）": ".8", "可比艺人报价（元）": "250000", "已观测粉丝增长比例": ".1",
            "可用资金（元）": "500000", "约定赞助（元）": "50000", "距演出天数（可为负）": "80"}.items():
            page.get_by_label(label, exact=True).fill(value)
        for label in ("购票需求已核验", "供应商报价已核验", "赞助凭证已核验", "补贴凭证已核验",
                      "报批已提交", "涉外审批证明已核验", "版权授权已完成", "现场安全已核验", "保险已核验"):
            page.get_by_label(label, exact=True).select_option("true")
        page.get_by_role("button", name="生成并保存报告", exact=True).click()
        expect(page.locator(".decision-report-summary dd").filter(has_text="75.95 / 120")).to_be_visible()
        page.get_by_text("规则命中与评分依据", exact=True).click()
        expect(page.get_by_text("分项原值、归一公式与贡献", exact=True)).to_be_visible()
        page.get_by_text("分项原值、归一公式与贡献", exact=True).click()
        expect(page.locator(".decision-score-row")).to_have_count(12)
        capture(page, "decision")
        context.close()

        for account, route, kind, title in [
            ("brand_user", "/partnership/valuation", "brand_match", "品牌匹配验收"),
            ("g_user", "/city/assets", "city_fit", "城市适配验收"),
            ("artist_user", "/performer/community", "artist_benchmark", "艺人对标验收"),
        ]:
            context, page = login(account, route)
            if account == "artist_user":
                selector = page.get_by_label("成长凭证关联项目", exact=True)
                selector.select_option(selector.locator("option").nth(1).get_attribute("value"))
            page.get_by_label("记录类型", exact=True).select_option(kind)
            page.get_by_label("记录名称", exact=True).fill(title)
            page.get_by_label("辅助评分规则版本", exact=True).select_option(rule_id)
            page.get_by_label("指标来源与参考基准", exact=True).fill("隔离样本与参考基准")
            metric_inputs = page.locator("form").filter(has=page.get_by_label("记录名称", exact=True)).locator('input[type="number"]')
            for metric in metric_inputs.all():
                metric.fill(".8")
            page.get_by_label("证明材料编号（逗号分隔）", exact=True).fill(str(proof_id))
            page.get_by_role("button", name="保存测算记录", exact=True).click()
            expect(page.get_by_text(title, exact=True)).to_be_visible()
            expect(page.get_by_text("80 / 100", exact=True)).to_be_visible()
            page.get_by_text("分项原值、归一公式与贡献", exact=True).click()
            capture(page, kind)
            context.close()
        browser.close()
    assert not errors, errors
    (OUTPUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"Complete rule/model acceptance: {len(results)} desktop/mobile flows passed", flush=True)


if __name__ == "__main__":
    serve() if "--serve" in sys.argv else verify()
