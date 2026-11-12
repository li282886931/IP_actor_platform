import pytest

from test_main import app_module, make_test_client
from test_ai_user_isolation import login
from app.models import Artist, Evidence, Project, ProjectVersion, User


def test_managed_show_list_requires_binding_and_management_grant(collaboration):
    _, sessions, _, project, _, post, get, grant = collaboration
    from app.models import Show, ShowProjectBinding
    with sessions() as db:
        p = db.get(Project, project)
        show = Show(title="已绑定演出", city=p.city, artist_id=p.artist_id)
        db.add(show)
        db.flush()
        db.add(ShowProjectBinding(tenant_id=p.tenant_id, project_id=p.id, show_id=show.id))
        db.commit()
        show_id = show.id
    assert get("b_user").json()["data"]["managed_shows"][0]["id"] == show_id
    assert get("root").json()["data"]["managed_shows"] == []
    grant("root", ["collaborate", "manage"])
    assert get("root").json()["data"]["managed_shows"][0]["project_id"] == project
    grant("brand_user")
    assert get("brand_user").json()["data"]["managed_shows"] == []


def test_collaboration_task_resubmission_keeps_legacy_inbox_consistent(collaboration):
    _, sessions, ids, project, _, post, _, grant = collaboration
    from app.models import Task
    grant("artist_user")
    item = post("b_user", "/items", {"kind": "task", "project_id": project,
                "recipient_id": ids["artist_user"][1]["user"]["id"], "title": "提交资料",
                "payload": {"instructions": "提交实际凭证"}, "request_key": "task-create"}).json()["data"]
    def action(account, name, revision, **kwargs):
        result = post(account, f'/items/{item["id"]}/actions',
                      {"action": name, "revision": revision, "request_key": f"{name}-{revision}", **kwargs})
        assert result.status_code == 200, result.text
        return result.json()["data"]
    shared = action("b_user", "share", 1)
    with sessions() as db:
        assert db.get(Task, shared["task_id"]).status == "pending"
    action("artist_user", "start", 2)
    action("artist_user", "submit", 3, note="已提交")
    action("b_user", "return", 4, note="缺少签字")
    with sessions() as db:
        assert db.get(Task, shared["task_id"]).status == "rejected"
    action("artist_user", "start", 5)
    action("artist_user", "submit", 6, note="已补充签字")
    with sessions() as db:
        task = db.get(Task, shared["task_id"])
        assert task.status == "submitted"
        assert task.rejection_reason == ""
    action("b_user", "approve", 7)


@pytest.fixture
def collaboration(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    identities = {account: login(client, monkeypatch, account) for account in (
        "root", "b_user", "brand_user", "g_user", "c_user", "investor_user", "artist_user",
    )}
    with sessions() as db:
        artist = db.query(Artist).first()
        db.query(User).filter(User.account == "artist_user").one().artist_id = artist.id
        project = Project(name="协作项目", city="北京", artist_id=artist.id,
                          tenant_id=identities["root"][1]["current_tenant"]["id"],
                          created_by=identities["b_user"][1]["user"]["id"])
        db.add(project)
        db.flush()
        version = ProjectVersion(project_id=project.id, version_no=1, input_snapshot={})
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()
        project_id, version_id = project.id, version.id
    def post(account, path, payload):
        return client.post("/collaboration" + path, headers=identities[account][0], json=payload)
    def get(account, path=""):
        return client.get("/collaboration" + path, headers=identities[account][0])
    def grant(account, duties=None):
        return post("root", "/grants", {"project_id": project_id,
                    "user_id": identities[account][1]["user"]["id"],
                    "duties": duties or (["collaborate", "finance"] if account in {"investor_user", "b_user"}
                                        else ["collaborate"]), "request_key": "grant-" + account})
    yield client, sessions, identities, project_id, version_id, post, get, grant
    app_module.app.dependency_overrides.clear()


def test_collaboration_auth_and_grant_revocation(collaboration):
    client, _, ids, project, _, post, get, grant = collaboration
    assert client.get("/collaboration").status_code == 401
    assert post("brand_user", "/grants", {"project_id": project,
                "user_id": ids["brand_user"][1]["user"]["id"], "request_key": "x"}).status_code == 403
    response = grant("brand_user")
    assert response.status_code == 200
    assert get("brand_user").json()["data"]["projects"][0]["id"] == project
    assert post("root", f'/grants/{response.json()["data"]["id"]}/revoke',
                {"revision": 1, "request_key": "revoke"}).status_code == 200
    assert get("brand_user").json()["data"]["projects"] == []


def test_private_drafts_cas_and_idempotency(collaboration):
    _, _, ids, project, _, post, get, grant = collaboration
    grant("brand_user")
    payload = {"kind": "brand_demand", "project_id": project,
               "recipient_id": ids["b_user"][1]["user"]["id"], "title": "合作需求",
               "payload": {"goal": "曝光", "city": "北京", "audience": "本地观众", "resources": "传播资源"},
               "request_key": "draft"}
    response = post("brand_user", "/items", payload)
    assert response.status_code == 200
    item = response.json()["data"]
    assert post("brand_user", "/items", payload).json()["data"]["id"] == item["id"]
    assert get("root").json()["data"]["items"] == []
    assert get("b_user").json()["data"]["items"] == []
    assert post("brand_user", f'/items/{item["id"]}/actions',
                {"action": "share", "revision": 99, "request_key": "bad"}).status_code == 409
    action = {"action": "share", "revision": 1, "request_key": "share"}
    assert post("brand_user", f'/items/{item["id"]}/actions', action).status_code == 200
    assert post("brand_user", f'/items/{item["id"]}/actions', action).status_code == 200
    assert len(get("b_user").json()["data"]["items"]) == 1
    action["action"] = "withdraw"
    assert post("brand_user", f'/items/{item["id"]}/actions', action).status_code == 409


@pytest.mark.parametrize("account,kind,payload", [
    ("b_user", "invitation", {"purpose": "演出合作"}),
    ("g_user", "supplement", {"materials": "消防材料", "due_date": "2026-12-01"}),
    ("investor_user", "investment", {"conditions": "成本核验", "amount": 20000}),
])
def test_shared_role_flow_and_history(collaboration, account, kind, payload):
    _, _, ids, project, version, post, get, grant = collaboration
    target = "artist_user" if kind == "invitation" else "b_user"
    grant(account)
    grant(target)
    item = post(account, "/items", {"kind": kind, "project_id": project, "version_id": version,
                "recipient_id": ids[target][1]["user"]["id"], "title": "协作事项",
                "payload": payload, "request_key": "create"}).json()["data"]
    shared = post(account, f'/items/{item["id"]}/actions',
                  {"action": "share", "revision": 1, "request_key": "share"})
    assert shared.status_code == 200
    replied = post(target, f'/items/{item["id"]}/actions',
                   {"action": "reply", "revision": 2, "note": "已补充资料", "request_key": "reply"})
    assert replied.status_code == 200
    if kind != "invitation":
        accepted = post(account, f'/items/{item["id"]}/actions',
                        {"action": "approve", "revision": 3, "request_key": "approve"})
        assert accepted.status_code == 200
    assert len(get(account, f'/items/{item["id"]}/history').json()["data"]) >= 3


def test_artist_profile_review_keeps_original_and_preferences_private(collaboration):
    _, sessions, ids, _, _, post, get, _ = collaboration
    with sessions() as db:
        original = db.query(Artist).first().name
    item = post("artist_user", "/items", {"kind": "profile_change",
                "recipient_id": ids["root"][1]["user"]["id"], "title": "资料修订",
                "payload": {"name": "核验后的艺人", "tags": "流行"}, "request_key": "profile"}).json()["data"]
    post("artist_user", f'/items/{item["id"]}/actions',
         {"action": "share", "revision": 1, "request_key": "share"})
    with sessions() as db:
        assert db.query(Artist).first().name == original
    assert post("root", f'/items/{item["id"]}/actions',
                {"action": "approve", "revision": 2, "request_key": "approve"}).status_code == 200
    with sessions() as db:
        assert db.query(Artist).first().name == "核验后的艺人"
    assert post("investor_user", "/personal", {"type": "focus", "payload": {"cities": ["北京"]},
                "request_key": "focus"}).status_code == 200
    assert get("investor_user").json()["data"]["focus"] == {"cities": ["北京"]}
    assert get("b_user").json()["data"]["focus"] == {}


def test_evidence_and_reviewer_validation(collaboration):
    _, sessions, ids, project, _, post, _, grant = collaboration
    grant("brand_user")
    with sessions() as db:
        other = Project(name="其他项目", tenant_id=ids["root"][1]["current_tenant"]["id"])
        db.add(other)
        db.flush()
        evidence = Evidence(project_id=other.id, name="证明", evidence_type="document", file_url="proof.pdf")
        db.add(evidence)
        db.commit()
        evidence_id = evidence.id
    response = post("brand_user", "/items", {"kind": "rights", "project_id": project,
                    "recipient_id": ids["b_user"][1]["user"]["id"], "title": "权益",
                    "payload": {"deliverables": "品牌展位", "due_date": "2026-12-01",
                                "acceptance": "照片核验", "evidence_ids": [evidence_id]},
                    "request_key": "invalid"})
    assert response.status_code == 422
    assert post("b_user", "/items", {"kind": "task", "project_id": project,
                "recipient_id": ids["b_user"][1]["user"]["id"], "title": "自验收",
                "payload": {"instructions": "提交证明"}, "request_key": "self"}).status_code == 422


def test_rights_require_two_confirmations_and_reconfirm_after_edit(collaboration):
    _, sessions, ids, project, _, post, _, grant = collaboration
    grant("brand_user")
    payload = {"deliverables": "品牌展位", "due_date": "2026-12-01", "acceptance": "照片核验"}
    item = post("brand_user", "/items", {"kind": "rights", "project_id": project,
                "recipient_id": ids["b_user"][1]["user"]["id"], "title": "展位交付",
                "payload": payload, "request_key": "rights"}).json()["data"]
    def act(user, action, revision, **kwargs):
        return post(user, f'/items/{item["id"]}/actions',
                    {"action": action, "revision": revision, "request_key": f"{action}-{revision}", **kwargs})
    assert act("brand_user", "share", 1).status_code == 200
    assert act("b_user", "deliver", 2, note="提前交付").status_code == 403
    assert act("brand_user", "confirm", 2).status_code == 200
    assert act("b_user", "confirm", 3).json()["data"]["status"] == "confirmed"
    assert act("b_user", "edit", 4, payload={**payload, "deliverables": "两处展位"}).status_code == 200
    assert act("b_user", "deliver", 5, note="照片").status_code == 403
    assert act("b_user", "share", 5).status_code == 200
    assert act("brand_user", "confirm", 6).status_code == 200
    assert act("b_user", "confirm", 7).status_code == 200
    assert act("b_user", "deliver", 8, note="已提交展位照片").status_code == 200
    assert act("b_user", "approve", 9).status_code == 403
    assert act("brand_user", "return", 9).status_code == 422
    assert act("brand_user", "approve", 9).status_code == 422
    with sessions() as db:
        proof = Evidence(project_id=project, name="实际展位照片", evidence_type="image", file_url="proof.jpg")
        db.add(proof); db.commit(); proof_id = proof.id
    assert act("brand_user", "approve", 9, payload={"evidence_ids": [proof_id]}).json()["data"]["status"] == "accepted"


def test_rights_next_handler_tracks_both_confirmations(collaboration):
    _, _, ids, project, _, post, _, grant = collaboration
    grant("brand_user")
    item = post("brand_user", "/items", {"kind": "rights", "project_id": project,
                "recipient_id": ids["b_user"][1]["user"]["id"], "title": "权益确认",
                "payload": {"deliverables": "展位", "due_date": "2026-12-01", "acceptance": "照片"},
                "request_key": "create-next"}).json()["data"]
    assert item["next_user_id"] == ids["brand_user"][1]["user"]["id"]
    shared = post("brand_user", f'/items/{item["id"]}/actions',
                  {"action": "share", "revision": 1, "request_key": "next-share"}).json()["data"]
    assert set(shared["next_user_ids"]) == {ids["b_user"][1]["user"]["id"], ids["brand_user"][1]["user"]["id"]}
    confirmed = post("b_user", f'/items/{item["id"]}/actions',
                    {"action": "confirm", "revision": 2, "request_key": "next-confirm"}).json()["data"]
    assert confirmed["next_user_id"] == ids["brand_user"][1]["user"]["id"]


def test_task_submission_updates_real_task_and_reviewer_returns(collaboration):
    _, sessions, ids, project, _, post, _, grant = collaboration
    from app.models import Task
    grant("artist_user")
    item = post("b_user", "/items", {"kind": "task", "project_id": project,
                "recipient_id": ids["artist_user"][1]["user"]["id"], "title": "提交演出材料",
                "payload": {"instructions": "艺人授权材料"}, "request_key": "task"}).json()["data"]
    for user, action, revision, note in [("b_user", "share", 1, ""),
            ("artist_user", "start", 2, ""), ("artist_user", "submit", 3, "已补交授权"),
            ("b_user", "return", 4, "缺少签名"), ("artist_user", "start", 5, ""),
            ("artist_user", "submit", 6, "已补签"), ("b_user", "approve", 7, "")]:
        assert post(user, f'/items/{item["id"]}/actions', {"action": action, "revision": revision,
                    "note": note, "request_key": f"task-{revision}"}).status_code == 200
    with sessions() as db:
        task = db.query(Task).filter_by(title="提交演出材料").one()
        assert task.status == "accepted" and task.result == "已补签"


def test_homepage_projects_collaboration_reviewer_and_honors_revocation(collaboration):
    client, _, ids, project, _, post, _, grant = collaboration
    permission = grant("artist_user").json()["data"]
    item = post("b_user", "/items", {"kind": "task", "project_id": project,
                "recipient_id": ids["artist_user"][1]["user"]["id"], "title": "首页交接",
                "payload": {"instructions": "提交证明"}, "request_key": "home-task"}).json()["data"]
    for account, action, revision in [("b_user", "share", 1), ("artist_user", "start", 2), ("artist_user", "submit", 3)]:
        response = post(account, f'/items/{item["id"]}/actions',
                        {"action": action, "revision": revision, "note": "实际执行结果", "request_key": f"home-{revision}"})
        assert response.status_code == 200
    overview = client.get("/workspaces/artist", headers=ids["artist_user"][0]).json()["data"]
    task = next(t for t in overview["personal"]["tasks"] if t["title"] == "首页交接")
    assert task["reviewer_name"] == ids["b_user"][1]["user"]["name"]
    assert task["next_user_name"] == task["reviewer_name"]
    assert task["collaboration_item_id"] == item["id"]
    post("root", f'/grants/{permission["id"]}/revoke',
         {"revision": permission["revision"], "request_key": "home-revoke"})
    after = client.get("/workspaces/artist", headers=ids["artist_user"][0]).json()["data"]
    assert "首页交接" not in [t["title"] for t in after["personal"]["tasks"]]


def test_availability_details_private_and_invitation_exposes_only_conflict(collaboration):
    _, _, ids, project, version, post, get, grant = collaboration
    grant("artist_user")
    slot = {"start": "2026-12-01T10:00:00+08:00", "end": "2026-12-01T12:00:00+08:00", "note": "私人安排"}
    assert post("artist_user", "/personal", {"type": "availability", "record_key": "slot",
                "payload": slot, "request_key": "slot"}).status_code == 200
    assert post("artist_user", "/personal", {"type": "availability", "record_key": "bad",
                "payload": {**slot, "end": "2026-11-01T12:00:00"}, "request_key": "bad"}).status_code == 422
    assert get("root").json()["data"]["personal"] == []
    item = post("b_user", "/items", {"kind": "invitation", "project_id": project, "version_id": version,
                "recipient_id": ids["artist_user"][1]["user"]["id"], "title": "邀请",
                "payload": {"purpose": "演出", "start": slot["start"], "end": slot["end"]},
                "request_key": "invite"}).json()["data"]
    assert item["availability_conflict"] is True
    assert "私人安排" not in str(item)


def test_investment_version_change_retains_opinion_and_revoked_grant_blocks_replay(collaboration):
    _, sessions, ids, project, version, post, get, grant = collaboration
    grant_response = grant("investor_user")
    body = {"kind": "investment", "project_id": project, "version_id": version,
            "recipient_id": ids["b_user"][1]["user"]["id"], "title": "投资意见",
            "payload": {"conditions": "核验票务"}, "request_key": "investment"}
    item = post("investor_user", "/items", body).json()["data"]
    with sessions() as db:
        v = ProjectVersion(project_id=project, version_no=2, input_snapshot={})
        db.add(v)
        db.flush()
        db.get(Project, project).current_version_id = v.id
        db.commit()
    current = get("investor_user").json()["data"]["items"][0]
    assert current["version_changed"] and current["version_id"] == version
    assert post("root", f'/grants/{grant_response.json()["data"]["id"]}/revoke',
                {"revision": 1, "request_key": "revoke"}).status_code == 200
    assert post("investor_user", "/items", body).status_code == 403
    assert get("investor_user", f'/items/{item["id"]}/history').status_code == 403


def test_audience_cancel_restore_history_and_confirmed_show_notifications(collaboration):
    client, sessions, ids, project, _, post, get, _ = collaboration
    from app.models import Notification, Order, Show
    with sessions() as db:
        p = db.get(Project, project)
        show = Show(title="已确认演出", city=p.city, artist_id=p.artist_id)
        db.add(show)
        db.flush()
        order = Order(show_id=show.id, name="观众", phone="123", tenant_id=p.tenant_id,
                      user_id=ids["c_user"][1]["user"]["id"])
        db.add(order)
        db.commit()
        show_id, order_id = show.id, order.id
    binding = {"project_id": project, "show_id": show_id, "confirmed": True, "changes": {}, "request_key": "binding"}
    assert post("b_user", "/show-binding", binding).status_code == 403
    assert post("root", "/show-binding", binding).status_code == 200
    assert post("b_user", "/reservations", {"order_id": order_id, "action": "cancel", "request_key": "bad"}).status_code == 403
    assert post("c_user", "/reservations", {"order_id": order_id, "action": "cancel", "request_key": "cancel"}).status_code == 200
    legacy = client.get("/workspaces/audience", headers=ids["c_user"][0]).json()["data"]
    assert next(r for r in legacy["reservations"] if r["id"] == order_id)["status"] == "cancelled"
    update = {**binding, "changes": {"date": "2026-12-02"}, "request_key": "update"}
    assert post("b_user", "/shows/update", update).status_code == 200
    assert get("c_user").json()["data"]["notifications"] == []
    assert post("c_user", "/reservations", {"order_id": order_id, "action": "restore", "request_key": "restore"}).status_code == 200
    update["changes"]["date"] = "2026-12-03"
    update["request_key"] = "update2"
    assert post("b_user", "/shows/update", update).status_code == 200
    assert post("b_user", "/shows/update", update).status_code == 200
    notice = get("c_user").json()["data"]["notifications"][0]
    assert post("c_user", f'/notifications/{notice["id"]}/read', {"request_key": "read"}).status_code == 200
    assert len(get("c_user", f"/reservations/{order_id}/history").json()["data"]) == 2
    with sessions() as db:
        assert db.query(Order).filter_by(show_id=show_id).count() == 1
        assert db.query(Notification).filter_by(user_id=ids["c_user"][1]["user"]["id"]).count() == 1


def test_official_result_requires_source_and_is_manually_reviewed(collaboration):
    _, _, ids, project, _, post, _, grant = collaboration
    grant("g_user")
    body = {"kind": "official_result", "project_id": project,
            "recipient_id": ids["b_user"][1]["user"]["id"], "title": "来源登记",
            "payload": {"result": "材料已收件"}, "request_key": "official"}
    assert post("g_user", "/items", body).status_code == 422
    body["payload"].update(authority="主管部门", reference="真实凭证编号",
                           source_url="https://example.org/record", recorded_at="2026-11-12T12:00:00+08:00")
    item = post("g_user", "/items", body).json()["data"]
    assert post("g_user", f'/items/{item["id"]}/actions',
                {"action": "share", "revision": 1, "request_key": "share"}).status_code == 200
    assert post("b_user", f'/items/{item["id"]}/actions',
                {"action": "approve", "revision": 2, "request_key": "verify"}).json()["data"]["status"] == "accepted"


def test_foreign_space_and_membership_role_do_not_expand_authorization(collaboration):
    client, sessions, ids, project, _, post, get, _ = collaboration
    from app.models import Tenant, TenantMember
    with sessions() as db:
        other = Tenant(name="外部空间", status="active")
        db.add(other)
        db.flush()
        db.add(TenantMember(tenant_id=other.id, user_id=ids["b_user"][1]["user"]["id"], role="admin"))
        db.commit()
        tenant_id = other.id
    headers = {**ids["b_user"][0], "X-Tenant-Id": str(tenant_id)}
    assert client.get("/collaboration", headers=headers).json()["data"]["projects"] == []
    assert client.post("/collaboration/grants", headers=headers, json={
        "project_id": project, "user_id": ids["b_user"][1]["user"]["id"], "request_key": "role",
    }).status_code == 403
    assert client.get("/collaboration", headers={**ids["brand_user"][0], "X-Tenant-Id": str(tenant_id)}).status_code == 403
    assert client.get("/collaboration", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_grant_edits_require_revision_and_financial_role(collaboration):
    _, _, ids, project, _, post, _, grant = collaboration
    grant("brand_user")
    assert post("root", "/grants", {"project_id": project, "user_id": ids["brand_user"][1]["user"]["id"],
                "duties": ["finance"], "request_key": "financial"}).status_code == 422
    assert post("root", "/grants", {"project_id": project, "user_id": ids["brand_user"][1]["user"]["id"],
                "duties": ["collaborate"], "request_key": "overwrite"}).status_code == 409


def test_incident_assignment_requires_real_failed_source(collaboration):
    _, sessions, ids, project, _, post, _, grant = collaboration
    from app.models import ExternalDataJob
    grant("root")
    with sessions() as db:
        job = ExternalDataJob(tenant_id=ids["root"][1]["current_tenant"]["id"],
                              project_id=project, source_type="mcp", query="声量",
                              purpose="声量采集", status="failed")
        db.add(job)
        db.commit()
        job_id = job.id
    item = post("root", "/items", {"kind": "incident", "project_id": project,
            "recipient_id": ids["b_user"][1]["user"]["id"], "title": "采集失败处置",
            "payload": {"source_type": "job", "source_id": job_id, "instructions": "核验连接参数"},
            "request_key": "incident"}).json()["data"]
    for user, action, rev, note in [("root", "share", 1, ""), ("b_user", "start", 2, ""),
            ("b_user", "submit", 3, "已核查参数，需真实重跑"), ("root", "approve", 4, "处置记录验收")]:
        assert post(user, f'/items/{item["id"]}/actions', {"action": action, "revision": rev, "note": note,
                    "request_key": f"incident-{rev}"}).status_code == 200
    with sessions() as db:
        assert db.get(ExternalDataJob, job_id).status == "failed"
