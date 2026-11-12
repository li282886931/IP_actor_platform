"""Role navigation acceptance against an isolated test database."""
import json
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def serve():
    import pytest
    import uvicorn
    from test_main import app_module, make_test_client
    from app.models import Artist, Gate, Project, ProjectVersion, Risk, User
    from app.services.auth import get_or_create_default_context

    patch = pytest.MonkeyPatch()
    _, sessions = make_test_client(patch)
    with sessions() as db:
        tenant, _ = get_or_create_default_context(db, account="investor_user")
        get_or_create_default_context(db, account="artist_user")
        artist = db.query(Artist).first()
        db.query(User).filter(User.account == "artist_user").one().artist_id = artist.id
        project = Project(tenant_id=tenant.id, artist_id=artist.id, artist_name=artist.name,
                          name="角色验收演出", city="北京", venue="音乐厅", schedule="待定")
        db.add(project)
        db.flush()
        version = ProjectVersion(project_id=project.id, version_no=1, input_snapshot={},
                                 finance_result={"status": "calculated", "roi": 0, "funding_gap": 0,
                                                 "total_cost": 40000, "total_revenue": 40000,
                                                 "net_profit": 0, "available_funds": 40000})
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.add_all([Risk(project_id=project.id, title="合同待核验"),
                    Gate(project_id=project.id, name="资金保障")])
        db.commit()
    try:
        uvicorn.run(app_module.app, host="127.0.0.1", port=8012, log_level="warning")
    finally:
        app_module.app.dependency_overrides.clear()
        patch.undo()


def check_browser():
    from playwright.sync_api import sync_playwright, expect
    from app.services.auth import create_session_token

    output = Path(__file__).resolve().parents[1] / "docs/superpowers/specs"
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        users = context.request.get("http://127.0.0.1:8012/users").json()["data"]
        tenant = context.request.get("http://127.0.0.1:8012/tenants").json()["data"][0]
        for role, account, routes in [
            ("Investor", "investor_user", [("/", "投资评估概览"), ("/investment/projects", "项目评估"),
                                          ("/investment/safeguards", "资金与风险"), ("/artist", "艺人洞察")]),
            ("Artist", "artist_user", [("/", "我的演出工作台"), ("/performer/profile", "我的资料"),
                                      ("/performer/opportunities", "演出机会"), ("/generate", "AI 宣发")]),
        ]:
            user = next(user for user in users if user["account"] == account)
            token = create_session_token(user["id"], tenant["id"])
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            storage = {"starhub-login": "true", "starhub-role": role, "starhub-user": json.dumps(user),
                       "starhub-tenant": json.dumps(tenant), "starhub-token": token}
            page.add_init_script("Object.entries(" + json.dumps(storage) + ").forEach(([key,value]) => localStorage.setItem(key,value))")
            for width, height, viewport in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
                page.set_viewport_size({"width": width, "height": height})
                for route, heading in routes:
                    page.goto(f"http://127.0.0.1:5179{route}")
                    page.wait_for_load_state("networkidle")
                    expect(page.get_by_role("heading", name=heading, exact=True).first).to_be_visible()
                    if role == "Investor" and route != "/artist":
                        page.get_by_text("角色验收演出", exact=True).click()
                        expect(page.get_by_text("合同待核验", exact=True)).to_be_visible()
                    if role == "Artist" and route in ["/", "/performer/opportunities"]:
                        expect(page.get_by_text("角色验收演出", exact=True)).to_be_visible()
                    assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth"), (role, route, viewport)
                    if route == "/":
                        page.screenshot(path=str(output / f"2026-11-12-{role.lower()}-{viewport}.png"), full_page=True)
                    results.append({"role": role, "route": route, "viewport": viewport})
                # Exercise visible navigation, then verify the opposite role route redirects.
                nav = page.get_by_role("navigation", name="主导航" if viewport == "desktop" else "移动端主导航", exact=True)
                nav.locator('a[href="/"]').click()
                expect(page).to_have_url("http://127.0.0.1:5179/")
                foreign = "/performer/profile" if role == "Investor" else "/investment/projects"
                page.goto("http://127.0.0.1:5179" + foreign)
                expect(page).to_have_url("http://127.0.0.1:5179/")
            assert not errors, errors
            page.close()
        context.close()
        browser.close()
    print(json.dumps({"result": "passed", "checks": results}, ensure_ascii=False))


if __name__ == "__main__":
    serve() if "--serve" in sys.argv else check_browser()
