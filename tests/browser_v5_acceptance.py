"""Isolated v5 HTTP/UI acceptance. Test fixtures stay in a process-local database."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/local-verification/v5"
BASE = "http://127.0.0.1:15173"


def serve():
    os.environ["DATABASE_URL"] = "sqlite://"
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    import pytest
    import uvicorn
    from test_collaboration import collaboration
    from test_v5_decision import reviewed_report
    from test_main import app_module
    from app.models import Project, Show
    patch = pytest.MonkeyPatch()
    fixture = collaboration.__wrapped__(patch)
    bundle = next(fixture)
    call, project, report, evidence = reviewed_report(bundle)
    for account in ("brand_user", "g_user", "artist_user", "investor_user"):
        bundle[-1](account)
    with bundle[1]() as db:
        db.get(Project, project).schedule = "2026-12-20"
        db.query(Show).first().date = "2026-12-20"
        db.commit()
    call("put", f"/projects/{project}/actuals", {"request_key": "ui-actual", "actual_attendance": 700,
         "actual_revenue": 800000, "actual_cost": 400000, "evidence_ids": [evidence], "verified": True})
    print("Isolated v5 server ready", flush=True)
    try:
        uvicorn.run(app_module.app, host="127.0.0.1", port=18001, log_level="warning")
    finally:
        fixture.close()
        patch.undo()


def verify():
    from playwright.sync_api import expect, sync_playwright
    routes = {"b_user": ["/operations/decision", "/operations/review", "/calendar"],
              "brand_user": ["/partnership/valuation"], "g_user": ["/city/assets", "/calendar"],
              "investor_user": ["/investment/returns"], "artist_user": ["/performer/community"],
              "c_user": ["/audience/plan"]}
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for account, paths in routes.items():
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE)
            page.wait_for_load_state("networkidle")
            page.get_by_label("账号", exact=True).fill(account)
            page.get_by_label("密码", exact=True).fill("123456")
            page.get_by_label("验证码", exact=True).fill("ABCD")
            page.get_by_role("button", name="登录", exact=True).click()
            expect(page.get_by_role("navigation", name="主导航", exact=True)).to_be_visible()
            for path in paths:
                page.goto(BASE + path)
                page.wait_for_load_state("networkidle")
                expect(page).to_have_url(BASE + path)
                assert not page.locator('[role="alert"]').count(), page.locator('[role="alert"]').all_inner_texts()
                assert "[object Object]" not in page.locator("main").inner_text()
                if path == "/operations/decision":
                    expect(page.get_by_text("风险评分", exact=True)).to_be_visible()
                    expect(page.get_by_text("96 / 120", exact=True)).to_be_visible()
                    for label, value in {"单场容量（人）": "1000", "基准票价（元）": "100",
                        "基准上座率（0–1）": ".5", "票房实收率（0–1）": ".9",
                        "有来源的价格弹性（−10–0）": "-1", "演出场数": "2",
                        "多场共用成本（元）": "10000", "单场成本（元）": "30000",
                        "单场赞助（元）": "5000", "单场补贴（元）": "0", "测算票价（元）": "80"}.items():
                        page.get_by_label(label, exact=True).fill(value)
                    page.get_by_role("button", name="计算敏感性", exact=True).click()
                    expect(page.get_by_text("票价 80 元 · 上座率 62.50% · 综合保本 41.67% · 利润 30,000 元")).to_be_visible()
                if path == "/partnership/valuation":
                    page.get_by_label("记录名称", exact=True).fill("HTTP权益验收")
                    for label, value in {"赞助投入（元）": "50000", "现场曝光（次）": "100000",
                        "传播曝光（次）": "200000", "现场千次曝光价值（元）": "200",
                        "传播千次曝光价值（元）": "100", "其他权益价值（元）": "20000"}.items():
                        page.get_by_label(label, exact=True).fill(value)
                    page.get_by_role("button", name="保存测算记录", exact=True).click()
                    expect(page.get_by_text("HTTP权益验收", exact=True)).to_be_visible()
                    expect(page.get_by_text("20.00%", exact=True)).to_be_visible()
                for width in (1440, 390):
                    page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                    page.evaluate("window.scrollTo(0, 0)")
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (path, width)
                    page.screenshot(path=str(OUTPUT / f"{account}-{paths.index(path)}-{width}.png"), full_page=True)
                    results.append({"account": account, "route": path, "width": width, "status": "passed"})
                page.set_viewport_size({"width": 1440, "height": 1000})
            assert not errors, errors
            context.close()
        browser.close()
    (OUTPUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"V5 acceptance: {len(results)} desktop/mobile route checks passed", flush=True)


if __name__ == "__main__":
    serve() if "--serve" in sys.argv else verify()
