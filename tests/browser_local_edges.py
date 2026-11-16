"""Supplemental real-UI checks using the isolated local verification fixtures."""
import json
import sys
import time

from browser_local_verification import BASE, OUTPUT, expect, login, sync_playwright


def verify():
    results = ([r for r in json.loads((OUTPUT / "supplemental.json").read_text()) if r["status"] == "passed"]
               if "--resume" in sys.argv else [])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        contexts, pages = [], {}
        for account in ("b_user", "brand_user", "g_user", "investor_user", "artist_user", "c_user"):
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            contexts.append(context)
            page = context.new_page()
            login(page, account)
            pages[account] = page

        def go(account, route="/collaboration"):
            page = pages[account]
            page.goto(BASE + route)
            page.wait_for_load_state("networkidle")
            return page

        def record(name):
            results.append({"workflow": name, "status": "passed"})
            (OUTPUT / "supplemental.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)

        def item(page, title):
            page.get_by_role("button", name="全部事项", exact=True).click()
            return page.locator("article.collab-item").filter(has=page.get_by_text(title, exact=True))

        try:
            if not results:
                page = go("brand_user")
                row = item(page, "本地测试·品牌合作邀请")
                row.get_by_label("处理说明 · 本地测试·品牌合作邀请").fill("本地测试：已核对合作目标")
                row.get_by_role("button", name="提交回复", exact=True).click()
                expect(row.locator(".status-badge")).to_have_text("待确认")
                page = go("b_user")
                row = item(page, "本地测试·品牌合作邀请")
                row.get_by_role("button", name="确认验收", exact=True).click()
                expect(row.locator(".status-badge")).to_have_text("已验收")
                row.locator(".collab-history summary").click()
                expect(row.locator(".collab-history article")).to_have_count(4)
                record("合作邀请回复确认及操作历史")

                page = go("brand_user")
                title = f"本地测试·品牌需求{int(time.time())}"
                page.get_by_label("事项类型").select_option("brand_demand")
                page.get_by_label("事项标题").fill(title)
                page.get_by_label("授权项目").select_option("2")
                page.get_by_label("处理人").select_option("2")
                page.get_by_label("合作目标").select_option("曝光")
                page.get_by_label("目标城市").fill("杭州")
                page.get_by_label("目标受众").fill("本地测试音乐爱好者")
                page.get_by_label("可提供资源").fill("本地测试传播素材")
                page.get_by_role("button", name="保存草稿", exact=True).click()
                expect(page.get_by_role("status")).to_contain_text("草稿已保存")
                assert not item(go("b_user"), title).count()
                row = item(go("brand_user"), title)
                row.get_by_role("button", name="发送事项", exact=True).click()
                expect(row.locator(".status-badge")).to_have_text("待处理")
                page = go("b_user")
                row = item(page, title)
                row.get_by_label(f"处理说明 · {title}").fill("本地测试：已收到品牌需求")
                row.get_by_role("button", name="提交回复", exact=True).click()
                expect(row.locator(".status-badge")).to_have_text("待确认")
                record("品牌需求创建、私有草稿、发送及主办方回复")

            page = go("b_user")
            page.get_by_label("已绑定演出").select_option("4")
            page.get_by_label("变更字段").select_option("description")
            page.get_by_label("确认后的新内容").fill(f"本地测试：演出说明已更新，核验批次{int(time.time())}")
            expect(page.get_by_role("button", name="发布变化并通知")).to_be_disabled()
            page.get_by_role("checkbox", name="我已核验此变化，可以通知已登记观众").check()
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/collaboration/shows/update")) as response:
                page.get_by_role("button", name="发布变化并通知").click()
            assert response.value.ok
            page = go("c_user")
            notice_title = "演出信息已更新 · 本地测试·林澄杭州音乐现场"
            expect(page.get_by_text(notice_title, exact=True)).to_be_visible()
            notification = page.locator(".workspace-compact-row").filter(has=page.get_by_text(notice_title, exact=True))
            expect(notification).to_contain_text("演出说明：")
            notification.get_by_role("button", name="标记已读", exact=True).click()
            expect(notification.get_by_text("已读", exact=True)).to_be_visible()
            record("确认演出变化后通知已登记观众及标记已读")

            page = go("c_user", "/show/4")
            page.get_by_label("姓名", exact=True).fill("本地测试观众")
            page.get_by_label("手机号", exact=True).fill("13800000000")
            page.get_by_role("button", name="立即预约", exact=True).click()
            expect(page.locator(".inline-message")).to_contain_text("预约登记成功")
            page = go("c_user", "/audience/reservations")
            expect(page.get_by_text("本地测试·林澄杭州音乐现场", exact=True)).to_be_visible()
            record("演出详情预约登记及我的预约查询")

            page = go("artist_user")
            title = f"本地测试·资料修订{int(time.time())}"
            page.get_by_label("事项标题").fill(title)
            page.get_by_label("处理人").select_option("1")
            page.get_by_label("艺人介绍").fill("本地测试资料修订，审批前保持原资料")
            page.get_by_role("button", name="保存草稿", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("草稿已保存")
            row = item(page, title)
            row.get_by_role("button", name="发送事项", exact=True).click()
            expect(row.locator(".status-badge")).to_have_text("待处理")
            record("艺人资料修订申请保存发送（等待审核）")

            page = go("b_user", "/projects/2")
            page.locator("#project-finance").scroll_into_view_if_needed()
            page.screenshot(path=str(OUTPUT / "project-finance-desktop.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            page.screenshot(path=str(OUTPUT / "project-finance-mobile.png"))
            page = go("brand_user", "/generate")
            page.screenshot(path=str(OUTPUT / "generation-desktop.png"), full_page=True)
            record("财务桌面与窄屏截图")
        except Exception as error:
            results.append({"workflow": "当前补充流程", "status": "failed", "error": str(error)})
            (OUTPUT / "supplemental.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()


if __name__ == "__main__":
    verify()
