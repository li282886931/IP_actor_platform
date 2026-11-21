"""Real-UI acceptance for the explicitly isolated local verification server.

Run with LOCAL_VERIFY_PASSWORD set; never targets production by default.
"""
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:5173"
OUTPUT = Path(__file__).resolve().parents[1] / "docs/local-verification"
ROUTES = {
    "root": ["/users"],
    "b_user": ["/", "/collaboration", "/operations/projects", "/operations/tasks", "/artist", "/generate", "/preferences"],
    "brand_user": ["/", "/collaboration", "/partnership/opportunities", "/partnership/evidence", "/artist", "/generate", "/preferences"],
    "g_user": ["/", "/collaboration", "/city/projects", "/city/review", "/city/impact", "/generate", "/preferences"],
    "c_user": ["/", "/collaboration", "/audience/discover", "/audience/reservations", "/artist", "/preferences"],
    "investor_user": ["/", "/collaboration", "/investment/projects", "/investment/safeguards", "/artist", "/preferences"],
    "artist_user": ["/", "/collaboration", "/performer/profile", "/performer/opportunities", "/generate", "/preferences"],
}


def login(page, account):
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    page.get_by_label("账号", exact=True).fill(account)
    page.get_by_label("密码", exact=True).fill(os.environ["LOCAL_VERIFY_PASSWORD"])
    expect(page.get_by_role("img", name="登录验证码")).to_be_visible()
    page.get_by_label("验证码", exact=True).fill("2468")
    page.get_by_role("button", name="登录", exact=True).click()
    expect(page.get_by_role("navigation", name="主导航", exact=True)).to_be_visible()
    page.wait_for_load_state("networkidle")


def navigation():
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for account, routes in ROUTES.items():
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors, failed = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: failed.append(f"{response.status} {response.url}")
                    if response.status >= 400 and "127.0.0.1:8000" in response.url else None)
            try:
                login(page, account)
                for route in routes:
                    page.get_by_role("navigation", name="主导航", exact=True).locator(f'a[href="{route}"]').click()
                    expect(page).to_have_url(BASE + route)
                    page.wait_for_load_state("networkidle")
                    expect(page.locator("main")).to_be_visible()
                    assert "[object Object]" not in page.locator("main").inner_text()
                    assert not page.locator('[role="alert"]').count(), page.locator('[role="alert"]').all_inner_texts()
                    for width in (1440, 390):
                        page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (account, route, width)
                        results.append({"account": account, "route": route, "width": width, "status": "passed"})
                    page.set_viewport_size({"width": 1440, "height": 1000})
                page.goto(BASE + ("/operations/projects" if account == "root" else "/users"))
                expect(page).to_have_url(BASE + ("/users" if account == "root" else "/"))
                page.wait_for_load_state("networkidle")
                assert not errors, errors
                assert not failed, failed
                page.screenshot(path=str(OUTPUT / f"{account}-desktop.png"), full_page=True)
                print(json.dumps({"account": account, "pages": len(routes), "status": "passed"}, ensure_ascii=False), flush=True)
            except Exception as error:
                page.screenshot(path=str(OUTPUT / f"{account}-failure.png"), full_page=True)
                results.append({"account": account, "status": "failed", "error": str(error), "page_errors": errors, "http_errors": failed})
                print(json.dumps(results[-1], ensure_ascii=False), flush=True)
            finally:
                (OUTPUT / "navigation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
                context.close()
        browser.close()
    assert all(row["status"] == "passed" for row in results), "See navigation.json"


def workflows():
    results = ([r for r in json.loads((OUTPUT / "workflows.json").read_text()) if r["status"] == "passed"]
               if "--resume" in sys.argv else [])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        pages = {}
        contexts = []
        for account in ("b_user", "brand_user", "g_user", "investor_user", "artist_user", "c_user", "b_other", "c_other"):
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            contexts.append(context)
            pages[account] = context.new_page()
            login(pages[account], account)

        def go(account, route):
            page = pages[account]
            page.goto(BASE + route)
            page.wait_for_load_state("networkidle")
            return page

        def checkpoint(name):
            results.append({"workflow": name, "status": "passed"})
            (OUTPUT / "workflows.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)

        def act(account, title, button, status, proof=False):
            page = go(account, "/collaboration")
            page.get_by_role("button", name="全部事项", exact=True).click()
            row = page.locator("article.collab-item").filter(has=page.get_by_text(title, exact=True))
            expect(row).to_be_visible()
            note = row.get_by_label(f"处理说明 · {title}", exact=True)
            if note.count():
                note.fill("本地测试：材料已经核对，仅验证流程")
            if proof:
                row.get_by_label(f"补交证明材料编号 · {title}", exact=True).fill("109")
            row.get_by_role("button", name=button, exact=True).click()
            expect(row.locator(".status-badge")).to_have_text(status)
            assert not page.locator('[role="alert"]').count()
            page.wait_for_load_state("networkidle")

        try:
            if not results:
                page = go("b_user", "/")
                page.get_by_role("button", name="新建项目", exact=True).click()
                expect(page.get_by_label("项目名称", exact=True)).to_be_focused()
                title = f"本地测试·归属修复验收{int(time.time())}"
                page.get_by_label("项目名称", exact=True).fill(title)
                page.get_by_label("艺人", exact=True).fill("本地测试·林澄")
                page.get_by_label("城市", exact=True).fill("杭州")
                page.get_by_label("场馆", exact=True).fill("本地测试·星河音乐厅")
                with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/projects")) as response:
                    page.locator(".project-create-form button").click()
                assert response.value.ok
                new_id = response.value.json()["data"]["id"]
                page = go("b_user", "/collaboration")
                expect(page.get_by_label("授权项目").locator(f'option[value="{new_id}"]')).to_have_text(title + " · 杭州")
                page = go("b_other", "/collaboration")
                assert not page.get_by_label("授权项目").locator(f'option[value="{new_id}"]').count()
                checkpoint("新建项目入口、作者归属及协作可见性")

                page = go("b_user", "/projects/2")
                slider = page.get_by_role("slider", name="上座率调节 / %")
                slider.fill("80")
                expect(page.get_by_label("预计人数 / 人", exact=True)).to_have_value("1600")
                page.get_by_role("button", name="保存并计算", exact=True).click()
                expect(page.locator(".finance-results")).to_contain_text("¥")
                page.reload()
                expect(page.get_by_label("预计人数 / 人", exact=True)).to_have_value("1600")
                page.get_by_role("button", name="政府", exact=True).click()
                expect(page.get_by_text("当地可用场馆、审批与安全条件")).to_be_visible()
                page.get_by_role("button", name="资方", exact=True).click()
                expect(page.get_by_text("资金监管、合同保障与分期付款节点")).to_be_visible()
                page.get_by_role("button", name="生成可行性报告", exact=True).click()
                expect(page.get_by_text("报告已生成，可下载核验")).to_be_visible(timeout=30000)
                with page.expect_download() as download:
                    page.locator("a[download]").click()
                download.value.save_as(OUTPUT / "local-feasibility-report.docx")
                assert (OUTPUT / "local-feasibility-report.docx").stat().st_size > 1000
                checkpoint("滑块测算、保存刷新、角色说明及报告下载")

                page = go("b_user", "/projects/2")
                page.get_by_label("本地测试·场馆只读API", exact=True).check()
                page.get_by_label("本地测试·公开网页MCP", exact=True).check()
                page.get_by_label("网页地址 · 本地测试·公开网页MCP").fill("https://93.184.216.34/show")
                page.get_by_label("向智能体提问").fill("核验场馆容量及演出授权，给出下一步建议")
                page.get_by_role("button", name="询问智能体", exact=True).click()
                expect(page.locator(".live-reading")).to_have_count(2)
                expect(page.locator(".live-analysis-result")).to_contain_text("容量：2000")
                assert page.locator(".live-reading").filter(has_text="待人工核验").count() == 2
                assert "读取失败" not in page.locator(".live-analysis-result").inner_text()
                checkpoint("Agent API 与 MCP 网页读取、入库及人工核验提示")

            if "--remaining" not in sys.argv:
                for account in ("b_user", "brand_user", "g_user", "artist_user"):
                    page = go(account, "/generate")
                    page.get_by_label("演出名称", exact=True).fill(f"本地测试·{account}宣发验收")
                    page.get_by_label("艺人", exact=True).fill("本地测试·林澄")
                    page.get_by_label("城市", exact=True).fill("杭州")
                    with page.expect_response(lambda r: r.request.method == "POST" and "/ai/generate/stream" in r.url) as response:
                        page.get_by_role("button", name="一键生成", exact=True).click()
                    assert response.value.ok
                    expect(page.locator(".generated-copy")).to_contain_text("执行建议", timeout=30000)
                    assert "<think>" not in page.locator(".generated-copy").inner_text()
                    assert page.locator(".generated-copy h2").count()
                    page.reload()
                    expect(page.locator(".generated-copy")).to_contain_text("执行建议")
                page = go("b_other", "/generate")
                assert not page.locator(".generated-copy").count()
                checkpoint("四角色 AI SSE、Markdown 渲染、刷新保存及账号隔离")

                act("artist_user", "本地测试·艺人履约资料", "开始执行", "执行中")
                act("artist_user", "本地测试·艺人履约资料", "提交结果", "待验收", proof=True)
                act("b_user", "本地测试·艺人履约资料", "退回补充", "需补充")
                act("artist_user", "本地测试·艺人履约资料", "开始执行", "执行中")
                act("artist_user", "本地测试·艺人履约资料", "提交结果", "待验收", proof=True)
                act("b_user", "本地测试·艺人履约资料", "确认验收", "已验收")
                checkpoint("艺人任务执行、退回补充、重提及验收")
                act("b_user", "本地测试·安全补件", "提交回复", "待确认", proof=True)
                act("g_user", "本地测试·安全补件", "确认验收", "已验收")
                act("b_user", "本地测试·资金投资意见", "提交回复", "待确认")
                act("investor_user", "本地测试·资金投资意见", "确认验收", "已验收")
                checkpoint("政府安全补件及资方意见双向处理")
                act("b_user", "本地测试·品牌权益确认", "确认权益", "待处理")
                act("brand_user", "本地测试·品牌权益确认", "确认权益", "双方已确认")
                act("b_user", "本地测试·品牌权益确认", "提交交付", "待验收", proof=True)
                act("brand_user", "本地测试·品牌权益确认", "确认验收", "已验收", proof=True)
                checkpoint("品牌权益双方确认、证明交付及验收")

                page = go("investor_user", "/collaboration")
                page.get_by_label("对照项目").select_option("2")
                options = page.get_by_label("版本一").locator("option").evaluate_all("(nodes) => nodes.map(n=>n.value).filter(Boolean)")
                page.get_by_label("版本一").select_option(options[0])
                page.get_by_label("版本二").select_option(options[-1])
                expect(page.get_by_text("回报率", exact=True)).to_have_count(2)
                checkpoint("资方历史与当前测算版本对照")

            page = go("artist_user", "/preferences")
            page.get_by_label("关注城市").fill("杭州,上海")
            page.get_by_role("button", name="保存关注设置").click()
            expect(page.get_by_role("status")).to_contain_text("关注设置已保存")
            page.get_by_label("档期开始时间").fill("2026-12-19T10:00")
            page.get_by_label("档期结束时间").fill("2026-12-21T18:00")
            page.get_by_label("档期个人备注").fill("本地测试私有档期")
            page.get_by_role("button", name="登记档期").click()
            expect(page.get_by_text("本地测试私有档期", exact=True)).to_be_visible()
            page.reload()
            expect(page.get_by_label("关注城市")).to_have_value("杭州，上海")
            page = go("b_other", "/preferences")
            expect(page.get_by_label("关注城市")).to_have_value("")
            assert "本地测试私有档期" not in page.locator("main").inner_text()
            checkpoint("关注设置与艺人档期保存、刷新及隐私隔离")

            page = go("c_user", "/collaboration")
            page.get_by_label("收藏对象").select_option("4")
            page.get_by_role("button", name="添加收藏").click()
            expect(page.get_by_role("button", name="取消收藏")).to_have_count(1)
            page.get_by_role("button", name="取消登记").click()
            expect(page.get_by_role("button", name="恢复登记")).to_be_visible()
            page.reload()
            expect(page.get_by_role("button", name="恢复登记")).to_be_visible()
            page.get_by_role("button", name="恢复登记").click()
            expect(page.get_by_role("button", name="取消登记")).to_be_visible()
            page = go("c_other", "/collaboration")
            assert not page.get_by_role("button", name="取消收藏").count()
            assert page.locator("article.collab-item").count() == 1
            checkpoint("观众收藏、预约取消恢复、刷新及账号隔离")

            for account in ROUTES:
                if account == "root":
                    continue
                page = go(account, "/")
                page.screenshot(path=str(OUTPUT / f"{account}-desktop.png"), full_page=True)
            checkpoint("各角色桌面视觉截图")
        except Exception as error:
            results.append({"workflow": "当前流程", "status": "failed", "error": str(error)})
            for account, page in pages.items():
                page.screenshot(path=str(OUTPUT / f"flow-{account}.png"), full_page=True)
            (OUTPUT / "workflows.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()


if __name__ == "__main__":
    workflows() if "--flows" in sys.argv else navigation()
