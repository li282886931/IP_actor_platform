"""Browser acceptance against an isolated in-memory database, never production."""
import json
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"


def serve():
    import pytest
    import uvicorn
    from test_main import make_test_client, app_module

    patch = pytest.MonkeyPatch()
    make_test_client(patch)
    try:
        uvicorn.run(app_module.app, host="127.0.0.1", port=8011, log_level="warning")
    finally:
        app_module.app.dependency_overrides.clear()
        patch.undo()


def check_browser():
    from playwright.sync_api import sync_playwright, expect

    project_root = Path(__file__).resolve().parents[1]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = context.request.post("http://127.0.0.1:8011/projects", data={
            "name": "会议迭代验收项目", "city": "北京",
            "venue_capacity": 1000, "expected_attendance": 800, "avg_ticket_price": 100,
            "artist_fee": 20000, "venue_cost": 10000, "marketing_cost": 5000,
            "production_cost": 5000, "available_funds": 30000,
        })
        assert response.ok
        project_id = response.json()["data"]["id"]
        page.add_init_script("""
          localStorage.setItem('starhub-login', 'true');
          localStorage.setItem('starhub-role', 'B');
          localStorage.setItem('starhub-user', JSON.stringify({account:'验收用户', role:'B', group_code:'B'}));
        """)
        page.goto(f"http://127.0.0.1:5179/projects/{project_id}")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("heading", name="演出决策测算")).to_be_visible()
        expect(page.get_by_label("税费率 / %")).to_have_value("")
        page.get_by_role("button", name="保存并计算", exact=True).click()
        expect(page.locator(".project-finance [role=status]")).to_contain_text("税费率")
        for label in ["安保费用", "交通费用", "住宿费用", "保险费用", "审批费用", "预备费用"]:
            page.get_by_label(f"{label} / 元", exact=True).fill("0")
        page.get_by_label("税费率 / %", exact=True).fill("6")
        page.get_by_label("票务服务费率 / %", exact=True).fill("4")
        page.get_by_role("button", name="保存并计算", exact=True).click()
        expect(page.locator(".finance-results")).to_contain_text("¥72,000")
        expect(page.locator(".finance-results")).to_contain_text("80.00%")
        expect(page.locator(".finance-results")).to_contain_text("¥10,000")
        page.reload()
        expect(page.get_by_label("税费率 / %")).to_have_value("6")
        expect(page.get_by_label("安保费用 / 元")).to_have_value("0")
        page.get_by_role("button", name="政府", exact=True).click()
        expect(page.get_by_text("当地可用场馆、审批与安全条件")).to_be_visible()
        page.get_by_role("button", name="资方", exact=True).click()
        expect(page.get_by_text("资金监管、合同保障与分期付款节点")).to_be_visible()
        page.get_by_role("button", name="生成可行性报告", exact=True).click()
        expect(page.get_by_text("报告已生成，可下载核验")).to_be_visible()
        report = page.locator("a[download]")
        assert report.get_attribute("href").startswith("http://127.0.0.1:8011/")
        assert context.request.get(report.get_attribute("href")).ok
        results = []
        for width, height, name in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
            page.set_viewport_size({"width": width, "height": height})
            page.locator("#project-finance").scroll_into_view_if_needed()
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            assert not overflow, f"{name} horizontal overflow"
            screenshot = project_root / "docs/superpowers/specs" / f"2026-11-12-meeting-{name}.png"
            page.screenshot(path=str(screenshot))
            results.append({"viewport": name, "horizontal_overflow": overflow, "screenshot": str(screenshot)})
        assert errors == [], errors
        print(json.dumps({"browser": "passed", "save_reload_report": "passed", "views": results}, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    serve() if "--serve" in sys.argv else check_browser()
