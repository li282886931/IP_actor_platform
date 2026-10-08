import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import app.schemas as schemas
import app.database as database
import app.models as models
import app.services as services
import main as app_module
import importlib
import importlib.util
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient


def make_screen_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    services.init_db()
    return session_factory


def make_screen_client(monkeypatch):
    session_factory = make_screen_session(monkeypatch)
    monkeypatch.setattr(app_module, "engine", database.engine)
    monkeypatch.setattr(app_module, "SessionLocal", session_factory)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_db
    return TestClient(app_module.app), session_factory


def test_miniapp_screen_data_contract_preserves_optional_values():
    assert hasattr(schemas, "MiniappScreenData")

    payload = {
        "screen_id": "S10",
        "summary": {
            "title": "我的项目",
            "subtitle": "快速查看判断、待办和版本变化",
            "highlight": None,
        },
        "items": [],
        "options": {},
        "context": {
            "tenant_id": 1,
            "user_id": 2,
            "project_id": None,
            "version_id": None,
            "task_id": None,
            "artist_id": None,
        },
        "empty_state": {
            "title": "暂无项目",
            "description": "创建项目后可在这里查看判断与待办",
            "action": {
                "label": "创建项目",
                "target_screen": "S13",
            },
        },
    }

    data = schemas.MiniappScreenData.model_validate(payload).model_dump()

    assert data["screen_id"] == "S10"
    assert data["summary"]["highlight"] is None
    assert data["context"]["project_id"] is None
    assert data["items"] == []
    assert data["options"] == {}


def test_miniapp_screen_item_contract_preserves_optional_detail_reference():
    payload = {
        "screen_id": "S04",
        "summary": {"title": "发现演出"},
        "items": [{
            "id": "show-3",
            "entity_type": "show",
            "title": "真实演出",
            "context": {"show_id": 3},
            "detail_ref": {"entity_type": "show", "entity_id": 3},
        }],
    }

    data = schemas.MiniappScreenData.model_validate(payload).model_dump()

    assert data["items"][0]["detail_ref"] == {
        "entity_type": "show",
        "entity_id": 3,
    }


def test_miniapp_screen_item_infers_detail_reference_only_for_persisted_entities():
    data = schemas.MiniappScreenData.model_validate({
        "screen_id": "S25",
        "summary": {"title": "详情引用"},
        "items": [
            {
                "id": "task-9",
                "entity_type": "task",
                "title": "真实任务",
                "context": {"task_id": 9},
            },
            {
                "id": "finance-profit",
                "entity_type": "finance_metric",
                "title": "预计利润",
                "context": {"metric": "profit"},
            },
        ],
    }).model_dump()

    assert data["items"][0]["detail_ref"] == {
        "entity_type": "task",
        "entity_id": 9,
    }
    assert data["items"][1]["detail_ref"] is None


def test_miniapp_entity_detail_contract_preserves_structured_sections():
    payload = {
        "entity_type": "show",
        "entity_id": 3,
        "title": "真实演出",
        "subtitle": "艺人 · 城市",
        "status": "on_sale",
        "media_url": "https://assets.example.com/show.jpg",
        "fields": [
            {"key": "date", "label": "演出日期", "value": "2026-10-05"},
        ],
        "sections": [
            {"key": "description", "title": "演出介绍", "content": "完整介绍"},
        ],
        "related_items": [
            {
                "title": "关联艺人",
                "subtitle": "艺人资料",
                "detail_ref": {"entity_type": "artist", "entity_id": 2},
            },
        ],
        "actions": [],
    }

    data = schemas.MiniappEntityDetail.model_validate(payload).model_dump()

    assert data["entity_id"] == 3
    assert data["fields"][0]["label"] == "演出日期"
    assert data["related_items"][0]["detail_ref"]["entity_type"] == "artist"


def test_entity_detail_registry_covers_all_persisted_list_entity_types():
    module = importlib.import_module("app.miniapp_entity_details")

    assert set(module.ENTITY_DETAIL_CONFIGS) == {
        "show",
        "artist",
        "project",
        "project_version",
        "fact",
        "assumption",
        "evidence",
        "risk",
        "gate",
        "decision",
        "task",
        "document_parse_job",
        "project_analysis_job",
        "report_share",
        "venue",
        "tour_plan",
        "tour_stop",
        "ticketing_snapshot",
        "project_actual",
        "tenant",
        "tenant_member",
        "notification",
        "member_invitation",
        "agent_permission",
        "privacy_consent",
    }


def test_miniapp_screen_data_rejects_unknown_screen_id():
    with pytest.raises(ValidationError):
        schemas.MiniappScreenData.model_validate({
            "screen_id": "S85",
            "summary": {"title": "Invalid"},
        })


def test_screen_provider_registry_explicitly_covers_all_84_screens():
    assert importlib.util.find_spec("app.miniapp_screens") is not None
    module = importlib.import_module("app.miniapp_screens")

    expected_ids = {f"S{index:02d}" for index in range(1, 85)}
    assert set(module.SCREEN_PROVIDERS) == expected_ids
    for screen_id, registration in module.SCREEN_PROVIDERS.items():
        assert registration.provider_key
        assert registration.domain
        assert isinstance(registration.required_context, frozenset)
        assert registration.screen_id == screen_id


def test_registered_screen_providers_cannot_fall_back_to_generic_empty_data():
    module = importlib.import_module("app.miniapp_screens")
    source = inspect.getsource(module.build_miniapp_screen)

    assert "暂无可用数据" not in source
    assert "Unhandled miniapp screen provider" in source


def test_screen_api_matrix_covers_registry_with_required_columns():
    module = importlib.import_module("app.miniapp_screens")
    matrix_path = Path(__file__).parents[1] / "docs" / "miniapp-screen-api-matrix.md"
    content = matrix_path.read_text(encoding="utf-8")
    rows = {
        line.split("|")[1].strip(): [cell.strip() for cell in line.split("|")[1:-1]]
        for line in content.splitlines()
        if line.startswith("| S") and not line.startswith("| Screen")
    }

    assert set(rows) == set(module.SCREEN_PROVIDERS)
    assert "| Screen | Provider | Required context | Read entities | Write API | Empty state | Error state | Tests |" in content
    for screen_id, registration in module.SCREEN_PROVIDERS.items():
        row = rows[screen_id]
        assert row[1] == f"`{registration.provider_key}`"
        assert row[2] != ""
        assert row[3] != ""
        assert row[4] != ""
        assert row[5] != ""
        assert row[6] != ""
        assert row[7] != ""


def test_request_context_resolves_user_and_tenant_from_login_token(monkeypatch):
    session_factory = make_screen_session(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        token = f"dev-token-{user.id}-{tenant.id}"

        context = services.resolve_request_context(
            db,
            authorization=f"Bearer {token}",
            tenant_header=str(tenant.id),
        )

        assert context.user.id == user.id
        assert context.tenant.id == tenant.id
    finally:
        db.close()


@pytest.mark.parametrize("authorization", ["", "Bearer invalid", "Basic dev-token-1-1"])
def test_request_context_rejects_missing_or_invalid_token(monkeypatch, authorization):
    session_factory = make_screen_session(monkeypatch)
    db = session_factory()
    try:
        with pytest.raises(HTTPException) as error:
            services.resolve_request_context(db, authorization=authorization)

        assert error.value.status_code == 401
    finally:
        db.close()


def test_miniapp_screen_route_returns_wrapped_authenticated_context(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S10",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-Id": str(tenant.id),
            },
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["screen_id"] == "S10"
    assert body["data"]["context"]["tenant_id"] == tenant.id
    assert body["data"]["context"]["user_id"] == user.id


def test_miniapp_screen_route_rejects_unknown_screen_before_auth(monkeypatch):
    client, _ = make_screen_client(monkeypatch)
    try:
        response = client.get("/miniapp/screens/S85")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 400


def test_tenant_switch_preserves_current_user_in_returned_token(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        current_tenant, user = services.get_or_create_default_context(db)
        second_tenant = models.Tenant(name="第二客户空间", status="active")
        db.add(second_tenant)
        db.flush()
        db.add(models.TenantMember(
            tenant_id=second_tenant.id,
            user_id=user.id,
            role="admin",
        ))
        db.commit()
        second_tenant_id = second_tenant.id
        token = f"dev-token-{user.id}-{current_tenant.id}"
    finally:
        db.close()

    try:
        response = client.post(
            f"/tenants/switch?tenant_id={second_tenant_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["token"] == f"dev-token-{user.id}-{second_tenant_id}"


def test_project_screen_requires_project_context(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S11",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "project_id" in response.json()["detail"]


def test_public_discovery_screen_allows_anonymous_access(monkeypatch):
    client, _ = make_screen_client(monkeypatch)
    try:
        response = client.get("/miniapp/screens/S04")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["context"]["user_id"] is None


def test_public_show_detail_returns_complete_database_fields(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        artist = models.Artist(name="详情艺人", tags="现场")
        db.add(artist)
        db.flush()
        show = models.Show(
            title="详情演出",
            artist_id=artist.id,
            artist_name=artist.name,
            city="南京",
            date="2026-12-01",
            venue="南京体育中心",
            price="380-1280",
            status="on_sale",
            description="数据库中的完整演出介绍",
            poster_url="https://assets.example.com/detail.jpg",
        )
        db.add(show)
        db.commit()
        show_id = show.id
        artist_id = artist.id
    finally:
        db.close()

    try:
        response = client.get(f"/miniapp/entities/show/{show_id}")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["title"] == "详情演出"
    assert detail["status"] == "on_sale"
    assert detail["media_url"] == "https://assets.example.com/detail.jpg"
    assert {field["label"]: field["value"] for field in detail["fields"]} == {
        "艺人": "详情艺人",
        "城市": "南京",
        "日期": "2026-12-01",
        "场馆": "南京体育中心",
        "票价": "380-1280",
    }
    assert detail["sections"][0]["content"] == "数据库中的完整演出介绍"
    assert detail["related_items"][0]["detail_ref"] == {
        "entity_type": "artist",
        "entity_id": artist_id,
    }


def test_project_entity_details_are_tenant_scoped_and_hide_share_tokens(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="详情项目",
            status="pending_confirmation",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=2,
            input_snapshot={"city": "南京"},
            finance_result={"status": "calculated"},
            created_by=user.id,
        )
        fact = models.Fact(
            project_id=project.id,
            title="详情事实",
            content="事实完整内容",
            source="manual",
        )
        assumption = models.Assumption(
            project_id=project.id,
            title="详情假设",
            content="假设完整内容",
            confidence=70,
            created_by=user.id,
        )
        db.add_all([version, fact, assumption])
        db.flush()
        project.current_version_id = version.id
        evidence = models.Evidence(
            project_id=project.id,
            fact_id=fact.id,
            name="详情依据",
            file_url="https://assets.example.com/evidence.pdf",
            source="upload",
            uploaded_by=user.id,
        )
        risk = models.Risk(
            project_id=project.id,
            title="详情风险",
            level="high",
            mitigation="风险应对措施",
        )
        gate = models.Gate(
            project_id=project.id,
            name="详情门禁",
            required_evidence="审批文件",
        )
        decision = models.Decision(
            project_id=project.id,
            version_id=version.id,
            decision_type="conditional_advance",
            conditions="完成审批",
            decided_by=user.id,
        )
        task = models.Task(
            project_id=project.id,
            title="详情任务",
            description="任务完整说明",
        )
        db.add_all([evidence, risk, gate, decision, task])
        db.flush()
        parse_job = models.DocumentParseJob(
            tenant_id=tenant.id,
            project_id=project.id,
            evidence_id=evidence.id,
            file_name="evidence.pdf",
            purpose="project_evidence",
            created_by=user.id,
        )
        analysis_job = models.ProjectAnalysisJob(
            tenant_id=tenant.id,
            project_id=project.id,
            version_id=version.id,
            purpose="项目分析",
            requested_by=user.id,
        )
        share = models.ReportShare(
            project_id=project.id,
            version_id=version.id,
            token="must-not-leak",
            created_by=user.id,
        )
        db.add_all([parse_job, analysis_job, share])
        db.commit()
        entity_ids = {
            "project": project.id,
            "project_version": version.id,
            "fact": fact.id,
            "assumption": assumption.id,
            "evidence": evidence.id,
            "risk": risk.id,
            "gate": gate.id,
            "decision": decision.id,
            "task": task.id,
            "document_parse_job": parse_job.id,
            "project_analysis_job": analysis_job.id,
            "report_share": share.id,
        }
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        details = {}
        for entity_type, entity_id in entity_ids.items():
            response = client.get(
                f"/miniapp/entities/{entity_type}/{entity_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200, entity_type
            details[entity_type] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert details["project"]["title"] == "详情项目"
    assert details["project_version"]["title"] == "项目版本 V2"
    assert details["task"]["sections"][0]["content"] == "任务完整说明"
    assert "must-not-leak" not in str(details["report_share"])


def test_tenant_and_user_entity_details_enforce_scope(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        member = models.User(account="detail-member", name="详情成员", status="active")
        db.add(member)
        db.flush()
        membership = models.TenantMember(
            tenant_id=tenant.id,
            user_id=member.id,
            role="editor",
        )
        venue = models.Venue(
            tenant_id=tenant.id,
            name="详情场馆",
            city="南京",
            capacity=12000,
            quote=800000,
        )
        plan = models.TourPlan(
            tenant_id=tenant.id,
            name="详情巡演",
            created_by=user.id,
        )
        project = models.Project(
            tenant_id=tenant.id,
            name="详情复盘项目",
            created_by=user.id,
        )
        notification = models.Notification(
            tenant_id=tenant.id,
            user_id=user.id,
            business_key="detail-notice",
            title="详情通知",
            content="通知完整内容",
        )
        invitation = models.MemberInvitation(
            tenant_id=tenant.id,
            invitee="detail@example.com",
            token="invitation-secret",
            invited_by=user.id,
            expires_at=datetime(2026, 10, 8),
        )
        permission = models.AgentPermission(
            tenant_id=tenant.id,
            user_id=user.id,
            capability="project_analysis",
            enabled=1,
        )
        consent = models.PrivacyConsent(
            tenant_id=tenant.id,
            user_id=user.id,
            scope="profile",
            granted=1,
        )
        db.add_all([
            membership,
            venue,
            plan,
            project,
            notification,
            invitation,
            permission,
            consent,
        ])
        db.flush()
        stop = models.TourStop(
            tour_plan_id=plan.id,
            project_id=project.id,
            venue_id=venue.id,
            city="南京",
            sequence=1,
        )
        snapshot = models.TicketingSnapshot(
            project_id=project.id,
            captured_at=datetime(2026, 9, 28, 12, 0),
            sold_count=5000,
            source="ticketing",
        )
        actual = models.ProjectActual(
            project_id=project.id,
            actual_attendance=4800,
            status="settled",
        )
        db.add_all([stop, snapshot, actual])
        db.commit()
        entity_ids = {
            "tenant": tenant.id,
            "tenant_member": membership.id,
            "venue": venue.id,
            "tour_plan": plan.id,
            "tour_stop": stop.id,
            "ticketing_snapshot": snapshot.id,
            "project_actual": actual.id,
            "notification": notification.id,
            "member_invitation": invitation.id,
            "agent_permission": permission.id,
            "privacy_consent": consent.id,
        }
        artist_id = db.query(models.Artist.id).first()[0]
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        for entity_type, entity_id in entity_ids.items():
            response = client.get(
                f"/miniapp/entities/{entity_type}/{entity_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200, entity_type
            assert "invitation-secret" not in response.text
        assert client.get(f"/miniapp/entities/artist/{artist_id}").status_code == 401
    finally:
        app_module.app.dependency_overrides.clear()


def test_entity_detail_hides_other_tenant_and_other_user_records(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        other_tenant = models.Tenant(name="详情隔离租户", status="active")
        other_user = models.User(account="detail-outsider", name="详情外部用户", status="active")
        db.add_all([other_tenant, other_user])
        db.flush()
        hidden_project = models.Project(tenant_id=other_tenant.id, name="隐藏详情项目")
        hidden_venue = models.Venue(tenant_id=other_tenant.id, name="隐藏详情场馆", city="上海")
        hidden_notification = models.Notification(
            tenant_id=tenant.id,
            user_id=other_user.id,
            business_key="hidden-detail-notice",
            title="隐藏详情通知",
        )
        db.add_all([hidden_project, hidden_venue, hidden_notification])
        db.commit()
        hidden_ids = {
            "project": hidden_project.id,
            "venue": hidden_venue.id,
            "notification": hidden_notification.id,
        }
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        for entity_type, entity_id in hidden_ids.items():
            response = client.get(
                f"/miniapp/entities/{entity_type}/{entity_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 404, entity_type
    finally:
        app_module.app.dependency_overrides.clear()


def test_request_context_rejects_tenant_without_membership(monkeypatch):
    session_factory = make_screen_session(monkeypatch)
    db = session_factory()
    try:
        current_tenant, user = services.get_or_create_default_context(db)
        other_tenant = models.Tenant(name="无权限空间", status="active")
        db.add(other_tenant)
        db.commit()

        with pytest.raises(HTTPException) as error:
            services.resolve_request_context(
                db,
                authorization=f"Bearer dev-token-{user.id}-{current_tenant.id}",
                tenant_header=str(other_tenant.id),
            )

        assert error.value.status_code == 403
    finally:
        db.close()


def test_project_list_screen_returns_only_current_tenant_projects_and_active_count(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).delete()
        other_tenant = models.Tenant(name="其他客户空间", status="active")
        db.add(other_tenant)
        db.flush()
        current_projects = [
            models.Project(
                tenant_id=tenant.id,
                name="当前租户草稿",
                status="draft",
                created_by=user.id,
            ),
            models.Project(
                tenant_id=tenant.id,
                name="当前租户已归档",
                status="archived",
                created_by=user.id,
            ),
        ]
        db.add_all([
            *current_projects,
            models.Project(
                tenant_id=other_tenant.id,
                name="其他租户项目",
                status="calculated",
                created_by=user.id,
            ),
        ])
        db.commit()
        expected_project_ids = [project.id for project in reversed(current_projects)]
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S10",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["context"]["project_id"] for item in data["items"]] == expected_project_ids
    assert [item["title"] for item in data["items"]] == ["当前租户已归档", "当前租户草稿"]
    assert data["summary"]["highlight"] == "1"


def test_project_detail_screen_returns_real_project_and_current_version(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="华东巡演上海站",
            status="calculated",
            artist_name="测试艺人",
            city="上海",
            venue="测试场馆",
            schedule="2027-05-01",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=3,
            input_snapshot={"city": "上海"},
            finance_result={"status": "calculated"},
            status="calculated",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()
        project_id = project.id
        version_id = version.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S11?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["summary"]["title"] == "华东巡演上海站"
    assert data["items"][0]["context"]["project_id"] == project_id
    assert data["options"]["project"]["venue"] == "测试场馆"
    assert data["options"]["current_version"]["id"] == version_id
    assert data["context"]["version_id"] == version_id


def test_project_versions_screen_orders_versions_and_marks_current(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="版本测试项目",
            status="draft",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        versions = [
            models.ProjectVersion(
                project_id=project.id,
                version_no=number,
                input_snapshot={"version": number},
                status="draft",
                created_by=user.id,
            )
            for number in (2, 1, 3)
        ]
        db.add_all(versions)
        db.flush()
        current_version = next(version for version in versions if version.version_no == 2)
        project.current_version_id = current_version.id
        db.commit()
        project_id = project.id
        current_version_id = current_version.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S12?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["value"] for item in data["items"]] == ["1", "2", "3"]
    assert [item["context"]["is_current"] for item in data["items"]] == [False, True, False]
    assert data["options"]["current_version_id"] == current_version_id


@pytest.mark.parametrize("screen_id", ["S13", "S14", "S15", "S16", "S17"])
def test_project_create_screens_restore_current_user_draft_and_real_artist_options(
    monkeypatch,
    screen_id,
):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        other_user = models.User(
            account="other-draft-owner",
            name="其他草稿用户",
            status="active",
        )
        artist = models.Artist(name="真实候选艺人", heat_score=77)
        db.add_all([other_user, artist])
        db.flush()
        own_draft = models.Project(
            tenant_id=tenant.id,
            name="我的最近草稿",
            status="draft",
            artist_name=artist.name,
            city="南京",
            created_by=user.id,
        )
        db.add_all([
            own_draft,
            models.Project(
                tenant_id=tenant.id,
                name="他人的草稿",
                status="draft",
                created_by=other_user.id,
            ),
        ])
        db.commit()
        draft_id = own_draft.id
        artist_id = artist.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/{screen_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    options = response.json()["data"]["options"]
    assert options["draft"]["id"] == draft_id
    assert {"id": artist_id, "name": "真实候选艺人"} in options["artists"]


@pytest.mark.parametrize("screen_id", ["S13", "S14", "S15", "S16"])
def test_project_create_screens_offer_scoped_database_candidates(monkeypatch, screen_id):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        other_tenant = models.Tenant(name="其他候选租户", status="active")
        artist = models.Artist(name="候选艺人", heat_score=92)
        db.add_all([other_tenant, artist])
        db.flush()
        venue = models.Venue(
            tenant_id=tenant.id,
            name="真实候选场馆",
            city="南京",
            capacity=12000,
        )
        foreign_venue = models.Venue(
            tenant_id=other_tenant.id,
            name="其他租户场馆",
            city="上海",
            capacity=9000,
        )
        project = models.Project(
            tenant_id=tenant.id,
            name="真实历史项目",
            type="concert",
            artist_id=artist.id,
            artist_name=artist.name,
            city="南京",
            venue_id=venue.id,
            venue=venue.name,
            schedule="2026-11-01",
            expected_attendance=10000,
            available_funds=5000000,
            avg_ticket_price=680,
            artist_fee=2000000,
            venue_cost=600000,
            marketing_cost=300000,
            production_cost=800000,
            created_by=user.id,
        )
        foreign_project = models.Project(
            tenant_id=other_tenant.id,
            name="其他租户项目",
            city="上海",
            venue=foreign_venue.name,
        )
        db.add_all([venue, foreign_venue])
        db.flush()
        project.venue_id = venue.id
        db.add_all([project, foreign_project])
        db.commit()
        artist_id = artist.id
        venue_id = venue.id
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/{screen_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    groups = response.json()["data"]["options"]["candidate_groups"]
    expected_group_keys = {
        "S13": {"projects", "artists", "project_types"},
        "S14": {"cities", "venues", "schedules"},
        "S15": {"expected_attendance", "available_funds", "avg_ticket_price"},
        "S16": {"artist_fee", "venue_cost", "marketing_cost", "production_cost"},
    }
    assert {group["key"] for group in groups} == expected_group_keys[screen_id]
    candidates = {
        item["key"]: item
        for group in groups
        for item in group["items"]
    }
    assert "其他租户项目" not in str(groups)
    assert "其他租户场馆" not in str(groups)
    if screen_id == "S13":
        assert candidates["project-%s" % project_id]["entity_id"] == project_id
        assert candidates["artist-%s" % artist_id]["patch"] == {
            "artist_id": artist_id,
            "artist_name": "候选艺人",
        }
    if screen_id == "S14":
        assert candidates["venue-%s" % venue_id]["patch"] == {
            "venue_id": venue_id,
            "venue": "真实候选场馆",
            "city": "南京",
            "venue_capacity": 12000,
        }
    if screen_id == "S15":
        assert candidates["expected_attendance-10000"]["patch"] == {
            "expected_attendance": 10000,
        }
    if screen_id == "S16":
        assert candidates["artist_fee-2000000"]["patch"] == {"artist_fee": 2000000}


def test_project_draft_screen_returns_only_current_users_tenant_drafts(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).delete()
        other_user = models.User(
            account="other-s18-owner",
            name="其他用户",
            status="active",
        )
        db.add(other_user)
        db.flush()
        own_drafts = [
            models.Project(
                tenant_id=tenant.id,
                name="草稿一",
                status="draft",
                created_by=user.id,
            ),
            models.Project(
                tenant_id=tenant.id,
                name="草稿二",
                status="draft",
                created_by=user.id,
            ),
        ]
        db.add_all([
            *own_drafts,
            models.Project(
                tenant_id=tenant.id,
                name="其他用户草稿",
                status="draft",
                created_by=other_user.id,
            ),
            models.Project(
                tenant_id=tenant.id,
                name="已测算项目",
                status="calculated",
                created_by=user.id,
            ),
        ])
        db.commit()
        expected_ids = [project.id for project in reversed(own_drafts)]
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S18",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["context"]["project_id"] for item in data["items"]] == expected_ids


def test_project_list_screen_returns_create_action_when_tenant_has_no_projects(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).filter(models.Project.tenant_id == tenant.id).delete()
        db.commit()
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S10",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["empty_state"]["action"] == {
        "label": "创建项目",
        "target_screen": "S13",
    }


def test_project_detail_screen_hides_cross_tenant_project(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        other_tenant = models.Tenant(name="详情隔离空间", status="active")
        db.add(other_tenant)
        db.flush()
        project = models.Project(
            tenant_id=other_tenant.id,
            name="不可见项目",
            status="draft",
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S11?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_project_create_persists_extended_finance_inputs(monkeypatch):
    client, _ = make_screen_client(monkeypatch)
    try:
        response = client.post(
            "/projects",
            json={
                "name": "完整财务参数项目",
                "available_funds": 6000000,
                "venue_capacity": 12000,
                "ticket_tiers": [
                    {"name": "看台", "price": 480, "share": 70},
                    {"name": "内场", "price": 980, "share": 30},
                ],
                "conservative_occupancy_rate": 60,
                "neutral_occupancy_rate": 80,
                "optimistic_occupancy_rate": 95,
            },
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    project = response.json()["data"]
    assert project["available_funds"] == 6000000
    assert project["venue_capacity"] == 12000
    assert project["ticket_tiers"][1]["price"] == 980
    assert project["conservative_occupancy_rate"] == 60
    assert project["neutral_occupancy_rate"] == 80
    assert project["optimistic_occupancy_rate"] == 95


def test_finance_input_screen_reads_saved_current_version_result(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="真实财务项目",
            status="calculated",
            expected_attendance=10000,
            avg_ticket_price=600,
            artist_fee=1000000,
            venue_cost=500000,
            marketing_cost=300000,
            production_cost=700000,
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        finance_result = {
            "formula_version": "finance-v1",
            "status": "calculated",
            "missing_fields": [],
            "total_cost": 2500000,
            "breakeven_attendance": 4167,
            "scenarios": {
                "conservative": {"attendance": 8000, "revenue": 4800000, "cost": 2500000, "profit": 2300000},
                "neutral": {"attendance": 10000, "revenue": 6000000, "cost": 2500000, "profit": 3500000},
                "optimistic": {"attendance": 12000, "revenue": 7200000, "cost": 2500000, "profit": 4700000},
            },
        }
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=2,
            input_snapshot={},
            finance_result=finance_result,
            status="calculated",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()
        project_id = project.id
        version_id = version.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S25?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["options"]["finance_result"] == finance_result
    assert data["context"]["version_id"] == version_id
    assert data["summary"]["highlight"] == "calculated"


def test_finance_scenario_screens_select_saved_scenario_without_recalculation(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="三情景项目",
            status="calculated",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        scenarios = {
            "conservative": {"attendance": 5000, "revenue": 2600000, "cost": 2000000, "profit": 600000},
            "neutral": {"attendance": 7000, "revenue": 3900000, "cost": 2000000, "profit": 1900000},
            "optimistic": {"attendance": 9000, "revenue": 5400000, "cost": 2000000, "profit": 3400000},
        }
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=1,
            input_snapshot={},
            finance_result={
                "status": "calculated",
                "missing_fields": [],
                "total_cost": 2000000,
                "scenarios": scenarios,
            },
            status="calculated",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    responses = {}
    try:
        for screen_id, scenario_name in (
            ("S28", "conservative"),
            ("S29", "neutral"),
            ("S30", "optimistic"),
        ):
            response = client.get(
                f"/miniapp/screens/{screen_id}?project_id={project_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            responses[scenario_name] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    for scenario_name, expected in scenarios.items():
        assert responses[scenario_name]["options"]["scenario"] == expected
        assert responses[scenario_name]["options"]["scenario_name"] == scenario_name


@pytest.mark.parametrize(
    ("ticket_tiers", "expected_values", "expected_missing"),
    [
        (
            [
                {"name": "看台", "price": 380, "share": 65},
                {"name": "内场", "price": 880, "share": 35},
            ],
            ["380", "880"],
            [],
        ),
        ([], [], ["ticket_tiers"]),
    ],
)
def test_ticket_tier_screen_uses_saved_tiers_or_reports_missing(
    monkeypatch,
    ticket_tiers,
    expected_values,
    expected_missing,
):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="票档项目",
            status="draft",
            ticket_tiers=ticket_tiers,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S26?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["value"] for item in data["items"]] == expected_values
    assert data["options"]["missing_fields"] == expected_missing


def test_cost_breakdown_screen_lists_real_costs_and_missing_fields(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="成本拆分项目",
            status="draft",
            artist_fee=1200000,
            venue_cost=500000,
            marketing_cost=None,
            production_cost=800000,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S27?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["context"]["field"] for item in data["items"]] == [
        "artist_fee",
        "venue_cost",
        "production_cost",
    ]
    assert [item["value"] for item in data["items"]] == ["1200000", "500000", "800000"]
    assert data["options"]["missing_fields"] == ["marketing_cost"]
    assert data["options"]["total_cost"] is None


@pytest.mark.parametrize(
    ("marketing_cost", "expected_breakeven", "expected_missing"),
    [
        (300000, 4167, []),
        (None, None, ["marketing_cost"]),
    ],
)
def test_breakeven_screen_calculates_only_with_complete_real_inputs(
    monkeypatch,
    marketing_cost,
    expected_breakeven,
    expected_missing,
):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="保本项目",
            status="draft",
            avg_ticket_price=600,
            artist_fee=1000000,
            venue_cost=500000,
            marketing_cost=marketing_cost,
            production_cost=700000,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S31?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    options = response.json()["data"]["options"]
    assert options["breakeven_attendance"] == expected_breakeven
    assert options["missing_fields"] == expected_missing


@pytest.mark.parametrize(
    ("available_funds", "expected_gap", "expected_missing"),
    [
        (1800000, 700000, []),
        (3000000, 0, []),
        (None, None, ["available_funds"]),
    ],
)
def test_funding_gap_screen_uses_real_costs_and_available_funds(
    monkeypatch,
    available_funds,
    expected_gap,
    expected_missing,
):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="资金缺口项目",
            status="draft",
            artist_fee=1000000,
            venue_cost=500000,
            marketing_cost=300000,
            production_cost=700000,
            available_funds=available_funds,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S33?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    options = response.json()["data"]["options"]
    assert options["funding_gap"] == expected_gap
    assert options["missing_fields"] == expected_missing


def test_finance_sensitivity_changes_only_saved_occupancy_rates(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="敏感性项目",
            status="draft",
            venue_capacity=10000,
            ticket_tiers=[
                {"name": "普通", "price": 400, "share": 75},
                {"name": "高价", "price": 800, "share": 25},
            ],
            conservative_occupancy_rate=60,
            neutral_occupancy_rate=80,
            optimistic_occupancy_rate=100,
            artist_fee=1200000,
            venue_cost=600000,
            marketing_cost=400000,
            production_cost=800000,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S32?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    options = response.json()["data"]["options"]
    assert options["weighted_ticket_price"] == 500
    assert options["total_cost"] == 3000000
    assert options["scenarios"] == {
        "conservative": {
            "occupancy_rate": 60,
            "attendance": 6000,
            "revenue": 3000000,
            "profit": 0,
        },
        "neutral": {
            "occupancy_rate": 80,
            "attendance": 8000,
            "revenue": 4000000,
            "profit": 1000000,
        },
        "optimistic": {
            "occupancy_rate": 100,
            "attendance": 10000,
            "revenue": 5000000,
            "profit": 2000000,
        },
    }


def test_judgement_screens_aggregate_current_version_risks_gates_and_latest_decision(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="判断聚合项目",
            status="pending_confirmation",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=2,
            input_snapshot={"city": "上海"},
            finance_result={"status": "calculated"},
            status="calculated",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.add_all([
            models.Risk(
                project_id=project.id,
                title="审批周期风险",
                level="high",
                mitigation="提前提交材料",
                status="open",
            ),
            models.Gate(
                project_id=project.id,
                name="场地审批",
                status="blocked",
                required_evidence="场地批文",
                owner_group="B",
            ),
            models.Decision(
                project_id=project.id,
                version_id=version.id,
                decision_type="conditional_advance",
                conditions="批文通过后推进",
                decided_by=user.id,
            ),
        ])
        db.commit()
        project_id = project.id
        version_id = version.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        responses = [
            client.get(
                f"/miniapp/screens/{screen_id}?project_id={project_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            for screen_id in ("S34", "S35")
        ]
    finally:
        app_module.app.dependency_overrides.clear()

    for response in responses:
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["options"]["current_version"]["id"] == version_id
        assert data["options"]["latest_decision"]["decision_type"] == "conditional_advance"
        assert data["options"]["latest_decision"]["decided_by_name"] == user.name
        assert data["options"]["open_risk_count"] == 1
        assert data["options"]["blocked_gate_count"] == 1
        assert {item["entity_type"] for item in data["items"]} >= {"risk", "gate", "decision"}


def test_evidence_screens_return_saved_records_conflicts_gaps_and_parse_results(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="依据聚合项目",
            status="draft",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        fact = models.Fact(
            project_id=project.id,
            title="场馆容量",
            content="可容纳一万人",
            source="场馆函件",
            status="needs_review",
        )
        assumption = models.Assumption(
            project_id=project.id,
            title="售票率假设",
            content="预计售票率 80%",
            confidence=70,
            status="active",
            created_by=user.id,
        )
        db.add_all([fact, assumption])
        db.flush()
        evidence = models.Evidence(
            project_id=project.id,
            fact_id=fact.id,
            name="场馆资料.pdf",
            file_url="oss://bucket/venue.pdf",
            evidence_type="document",
            source="场馆方",
            status="conflict",
            meta={"conflict_reason": "容量口径与合同不一致"},
            uploaded_by=user.id,
        )
        db.add(evidence)
        db.flush()
        parse_job = models.DocumentParseJob(
            tenant_id=tenant.id,
            project_id=project.id,
            evidence_id=evidence.id,
            file_name=evidence.name,
            file_kind="document",
            status="completed",
            result={"candidate_facts": [{"title": "容量候选"}]},
            created_by=user.id,
        )
        gate = models.Gate(
            project_id=project.id,
            name="补齐合同",
            status="pending",
            required_evidence="正式场馆合同",
            owner_group="B",
        )
        db.add_all([parse_job, gate])
        db.commit()
        project_id = project.id
        assumption_id = assumption.id
        fact_id = fact.id
        evidence_id = evidence.id
        parse_job_id = parse_job.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        data_by_screen = {}
        for screen_id in ("S36", "S37", "S38", "S39", "S40", "S41", "S42"):
            response = client.get(
                f"/miniapp/screens/{screen_id}?project_id={project_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data_by_screen[screen_id] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert data_by_screen["S36"]["items"][0]["context"]["assumption_id"] == assumption_id
    assert data_by_screen["S37"]["items"][0]["context"]["fact_id"] == fact_id
    assert data_by_screen["S38"]["items"][0]["context"]["evidence_id"] == evidence_id
    assert data_by_screen["S39"]["items"][0]["context"]["conflict_reason"] == "容量口径与合同不一致"
    assert data_by_screen["S40"]["items"][0]["title"] == "正式场馆合同"
    assert data_by_screen["S41"]["options"]["facts"][0]["id"] == fact_id
    assert data_by_screen["S42"]["items"][0]["context"]["parse_job_id"] == parse_job_id
    assert data_by_screen["S42"]["items"][0]["context"]["result"]["candidate_facts"][0]["title"] == "容量候选"


def test_risk_and_gate_screens_sort_real_records_by_priority(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="风险门禁项目",
            status="draft",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        db.add_all([
            models.Risk(project_id=project.id, title="低风险", level="low", status="closed"),
            models.Risk(project_id=project.id, title="高风险", level="high", status="open"),
            models.Risk(project_id=project.id, title="中风险", level="medium", status="open"),
            models.Gate(project_id=project.id, name="已通过", status="passed"),
            models.Gate(project_id=project.id, name="待处理", status="pending"),
            models.Gate(project_id=project.id, name="被阻塞", status="blocked"),
        ])
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        responses = {
            screen_id: client.get(
                f"/miniapp/screens/{screen_id}?project_id={project_id}",
                headers={"Authorization": f"Bearer {token}"},
            ).json()["data"]
            for screen_id in ("S43", "S44", "S45", "S46")
        }
    finally:
        app_module.app.dependency_overrides.clear()

    assert [item["title"] for item in responses["S43"]["items"]] == ["高风险", "中风险", "低风险"]
    assert responses["S44"]["items"][0]["context"]["risk_id"]
    assert [item["title"] for item in responses["S45"]["items"]] == ["被阻塞", "待处理", "已通过"]
    assert responses["S46"]["items"][0]["context"]["gate_id"]


def test_decision_version_and_report_screens_use_real_records_only(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="决策报告项目",
            status="calculated",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        versions = [
            models.ProjectVersion(
                project_id=project.id,
                version_no=number,
                input_snapshot={"city": city, "artist_fee": fee},
                finance_result={"status": "calculated", "profit": profit},
                status="calculated",
                created_by=user.id,
            )
            for number, city, fee, profit in [
                (1, "北京", 100, 20),
                (2, "上海", 120, 30),
            ]
        ]
        db.add_all(versions)
        db.flush()
        project.current_version_id = versions[1].id
        decision = models.Decision(
            project_id=project.id,
            version_id=versions[1].id,
            decision_type="advance",
            conditions="按第二版执行",
            decided_by=user.id,
        )
        report = models.Evidence(
            project_id=project.id,
            name="可行性报告.docx",
            file_url="oss://bucket/report.docx",
            evidence_type="feasibility_report",
            source="system",
            status="uploaded",
            meta={"version_id": versions[1].id},
            uploaded_by=user.id,
        )
        valid_share = models.ReportShare(
            project_id=project.id,
            version_id=versions[1].id,
            token="valid-share",
            expires_in_days=7,
            created_by=user.id,
            created_at=datetime.now(timezone.utc),
        )
        expired_share = models.ReportShare(
            project_id=project.id,
            version_id=versions[0].id,
            token="expired-share",
            expires_in_days=1,
            created_by=user.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        db.add_all([decision, report, valid_share, expired_share])
        db.commit()
        project_id = project.id
        current_version_id = versions[1].id
        decision_id = decision.id
        report_id = report.id
        user_name = user.name
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        data_by_screen = {}
        queries = {
            "S47": f"project_id={project_id}&version_id={current_version_id}",
            "S48": f"project_id={project_id}",
            "S49": f"project_id={project_id}",
            "S50": f"project_id={project_id}",
            "S51": f"project_id={project_id}",
        }
        for screen_id, query in queries.items():
            response = client.get(
                f"/miniapp/screens/{screen_id}?{query}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data_by_screen[screen_id] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert data_by_screen["S47"]["options"]["version"]["id"] == current_version_id
    assert data_by_screen["S48"]["items"][0]["context"]["decision_id"] == decision_id
    assert data_by_screen["S48"]["items"][0]["context"]["decided_by_name"] == user_name
    assert data_by_screen["S49"]["options"]["changes"]["city"] == {"from": "北京", "to": "上海"}
    assert data_by_screen["S49"]["options"]["changes"]["artist_fee"] == {"from": 100, "to": 120}
    assert data_by_screen["S50"]["items"][0]["context"]["evidence_id"] == report_id
    assert [item["context"]["token"] for item in data_by_screen["S51"]["items"]] == ["valid-share"]


def test_version_compare_requires_two_real_versions(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="单版本项目",
            status="draft",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=1,
            input_snapshot={"city": "北京"},
            status="draft",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S49?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["empty_state"]["title"] == "暂无可对比版本"


def test_task_screens_are_tenant_scoped_and_include_operational_fields(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="当前租户项目",
            created_by=user.id,
        )
        other_tenant = models.Tenant(name="其他任务租户", status="active")
        db.add_all([project, other_tenant])
        db.flush()
        other_project = models.Project(
            tenant_id=other_tenant.id,
            name="不可见项目",
            created_by=user.id,
        )
        db.add(other_project)
        db.flush()
        task = models.Task(
            project_id=project.id,
            assignee_id=user.id,
            title="核验场馆材料",
            due_date="2026-09-28",
            status="in_progress",
            evidence_ids=[11, 12],
            rejection_reason="",
        )
        rejected_task = models.Task(
            project_id=project.id,
            title="补充预算",
            status="pending",
            rejection_reason="档期冲突",
        )
        hidden_task = models.Task(
            project_id=other_project.id,
            title="其他租户任务",
            status="pending",
        )
        db.add_all([task, rejected_task, hidden_task])
        db.commit()
        project_id = project.id
        task_id = task.id
        token = f"dev-token-{user.id}-{tenant.id}"
        user_name = user.name
    finally:
        db.close()

    try:
        data_by_screen = {}
        queries = {
            "S55": "",
            "S56": "",
            "S57": f"?task_id={task_id}",
            "S58": f"?task_id={task_id}",
        }
        for screen_id, query in queries.items():
            response = client.get(
                f"/miniapp/screens/{screen_id}{query}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data_by_screen[screen_id] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert {item["title"] for item in data_by_screen["S55"]["items"]} == {"核验场馆材料", "补充预算"}
    task_item = next(item for item in data_by_screen["S55"]["items"] if item["context"]["task_id"] == task_id)
    assert task_item["context"]["project_id"] == project_id
    assert task_item["context"]["project_name"] == "当前租户项目"
    assert task_item["context"]["assignee_name"] == user_name
    assert task_item["context"]["due_date"] == "2026-09-28"
    assert task_item["context"]["evidence_count"] == 2
    assert data_by_screen["S56"]["options"]["selected_task_ids"] == []
    assert set(data_by_screen["S56"]["options"]["selectable_task_ids"]) == {
        item["context"]["task_id"] for item in data_by_screen["S56"]["items"]
    }
    assert data_by_screen["S57"]["items"][0]["context"]["task_id"] == task_id
    assert data_by_screen["S58"]["items"][0]["context"]["task_id"] == task_id


def test_task_detail_rejects_cross_tenant_task(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        other_tenant = models.Tenant(name="隔离任务租户", status="active")
        db.add(other_tenant)
        db.flush()
        other_project = models.Project(
            tenant_id=other_tenant.id,
            name="隔离项目",
            created_by=user.id,
        )
        db.add(other_project)
        db.flush()
        task = models.Task(project_id=other_project.id, title="不可见任务")
        db.add(task)
        db.commit()
        task_id = task.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S57?task_id={task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 404


def test_agent_screens_aggregate_current_user_tasks_and_analysis_jobs(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="Agent 聚合项目",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=1,
            input_snapshot={"city": "北京"},
            status="draft",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        task = models.Task(
            project_id=project.id,
            assignee_id=user.id,
            title="今日复核",
            due_date="2026-09-28",
            status="in_progress",
        )
        other_task = models.Task(
            project_id=project.id,
            title="未分配任务",
            status="pending",
        )
        analysis = models.ProjectAnalysisJob(
            tenant_id=tenant.id,
            project_id=project.id,
            version_id=version.id,
            purpose="项目判断",
            status="completed",
            result={"recommendation": "conditional_advance"},
            requested_by=user.id,
        )
        db.add_all([task, other_task, analysis])
        db.commit()
        project_id = project.id
        task_id = task.id
        analysis_id = analysis.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        data_by_screen = {}
        for screen_id in ("S52", "S53", "S54", "S60"):
            query = f"?project_id={project_id}" if screen_id in {"S53", "S54"} else ""
            response = client.get(
                f"/miniapp/screens/{screen_id}{query}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data_by_screen[screen_id] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert [item["context"]["task_id"] for item in data_by_screen["S52"]["items"]] == [task_id]
    assert {item["entity_type"] for item in data_by_screen["S53"]["items"]} == {
        "task",
        "project_analysis_job",
    }
    assert data_by_screen["S54"]["options"]["latest_analysis"]["id"] == analysis_id
    assert data_by_screen["S54"]["options"]["latest_analysis"]["result"]["recommendation"] == "conditional_advance"
    assert data_by_screen["S52"]["options"]["work_briefing"]["today_change_count"] == 1
    assert data_by_screen["S52"]["options"]["work_briefing"]["top_task"]["task_id"] == task_id
    task_item = next(
        item for item in data_by_screen["S53"]["items"]
        if item["context"].get("task_id") == task_id
    )
    assert task_item["context"]["actionability"] == ["accept", "reject", "block"]
    assert task_item["context"]["evidence_required"] is True
    assert data_by_screen["S60"]["items"] == []
    assert data_by_screen["S60"]["summary"]["title"] == "工作权限"
    assert data_by_screen["S60"]["summary"]["subtitle"] == "当前用户已保存的工作授权"
    assert data_by_screen["S60"]["empty_state"]["title"] == "暂无工作权限配置"


def test_agent_dashboard_returns_latest_tenant_project_as_default_context(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).delete()
        active_projects = [
            models.Project(
                tenant_id=tenant.id,
                name=name,
                status="pending_confirmation",
                created_by=user.id,
            )
            for name in ("较早项目", "最新项目")
        ]
        archived_project = models.Project(
            tenant_id=tenant.id,
            name="已归档项目",
            status="archived",
            created_by=user.id,
        )
        other_tenant = models.Tenant(name="其他 Agent 客户空间", status="active")
        db.add_all([*active_projects, archived_project, other_tenant])
        db.flush()
        db.add(models.Project(
            tenant_id=other_tenant.id,
            name="其他租户最新项目",
            status="pending_confirmation",
            created_by=user.id,
        ))
        db.commit()
        expected_project_id = active_projects[-1].id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S52",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    options = response.json()["data"]["options"]
    assert options["default_project_id"] == expected_project_id
    assert [project["name"] for project in options["available_projects"]] == [
        "最新项目",
        "较早项目",
    ]


def test_agent_dashboard_has_no_default_project_when_tenant_has_no_projects(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).filter(models.Project.tenant_id == tenant.id).delete()
        db.commit()
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S52",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["options"]["default_project_id"] is None
    assert response.json()["data"]["options"]["available_projects"] == []


def test_agent_change_screen_only_reports_real_version_changes(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="版本变化项目",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        versions = [
            models.ProjectVersion(
                project_id=project.id,
                version_no=number,
                input_snapshot=snapshot,
                status="draft",
                created_by=user.id,
            )
            for number, snapshot in [
                (1, {"city": "北京", "artist_fee": 100}),
                (2, {"city": "北京", "artist_fee": 130}),
            ]
        ]
        db.add_all(versions)
        db.flush()
        project.current_version_id = versions[1].id
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S59?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["title"] for item in data["items"]] == ["artist_fee"]
    assert data["items"][0]["context"] == {
        "field": "artist_fee",
        "from": 100,
        "to": 130,
    }


def test_miniapp_entity_search_normalizes_keyword_and_returns_real_ids(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="南京音乐节",
            artist_name="周杰伦",
            city="南京",
            venue="南京体育中心",
            created_by=user.id,
        )
        venue = models.Venue(
            tenant_id=tenant.id,
            name="南京体育中心",
            city="南京",
            capacity=12000,
            source="manual",
        )
        member = models.User(account="nanjing_owner", name="南京负责人", status="active")
        db.add_all([project, venue, member])
        db.flush()
        db.add(models.TenantMember(tenant_id=tenant.id, user_id=member.id, role="member"))

        other_tenant = models.Tenant(name="其他客户", status="active")
        db.add(other_tenant)
        db.flush()
        db.add_all([
            models.Project(tenant_id=other_tenant.id, name="南京隐藏项目"),
            models.Venue(tenant_id=other_tenant.id, name="南京隐藏场馆", city="南京", source="manual"),
        ])
        db.commit()
        token = f"dev-token-{user.id}-{tenant.id}"
        project_id = project.id
        venue_id = venue.id
        member_id = member.id
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/search?q=%20南京%20",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    groups = response.json()["data"]["groups"]
    by_type = {group["entity_type"]: group["items"] for group in groups}
    assert {item["entity_id"] for item in by_type["project"]} == {project_id}
    assert {item["entity_id"] for item in by_type["venue"]} == {venue_id}
    assert {item["entity_id"] for item in by_type["member"]} == {member_id}
    assert by_type["city"][0]["entity_id"] == "city:南京"
    assert all("隐藏" not in item["label"] for group in groups for item in group["items"])


def test_miniapp_entity_search_rejects_blank_keyword(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/search?q=%20%20",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 422


def test_project_creation_persists_selected_entity_ids(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, _ = services.get_or_create_default_context(db)
        artist = models.Artist(name="选择艺人")
        venue = models.Venue(tenant_id=tenant.id, name="选择场馆", city="南京", source="manual")
        source_project = models.Project(tenant_id=tenant.id, name="来源项目")
        db.add_all([artist, venue, source_project])
        db.commit()
        artist_id = artist.id
        venue_id = venue.id
        source_project_id = source_project.id
    finally:
        db.close()

    try:
        response = client.post(
            "/projects",
            json={
                "name": "使用真实选择的新项目",
                "artist_id": artist_id,
                "artist_name": "选择艺人",
                "venue_id": venue_id,
                "venue": "选择场馆",
                "city": "南京",
                "source_project_id": source_project_id,
            },
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["artist_id"] == artist_id
    assert data["venue_id"] == venue_id
    assert data["source_project_id"] == source_project_id


def test_discovery_screens_use_real_shows_and_empty_business_sources(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        db.query(models.Show).delete()
        db.query(models.Project).delete()
        artist = models.Artist(
            name="真实发现艺人",
            tags="流行,现场",
            heat_score=91,
            fan_count="120万",
        )
        db.add(artist)
        db.flush()
        show = models.Show(
            title="真实发现演出",
            artist_id=artist.id,
            artist_name=artist.name,
            city="杭州",
            date="2026-11-08",
            venue="杭州奥体中心",
            price="480-1280",
            status="on_sale",
            description="来自演出领域表",
            poster_url="https://assets.example.com/show.jpg",
        )
        db.add(show)
        db.commit()
        show_id = show.id
        artist_id = artist.id
    finally:
        db.close()

    try:
        discovery = client.get("/miniapp/screens/S04")
        cases = client.get("/miniapp/screens/S06")
        opportunity = client.get("/miniapp/screens/S08")
    finally:
        app_module.app.dependency_overrides.clear()

    assert discovery.status_code == 200
    discovery_data = discovery.json()["data"]
    assert [item["context"]["show_id"] for item in discovery_data["items"]] == [show_id]
    assert discovery_data["items"][0]["context"]["artist_id"] == artist_id
    assert discovery_data["items"][0]["context"]["poster_url"] == "https://assets.example.com/show.jpg"
    assert discovery_data["options"]["quick_start"]["target_screen"] == "S13"
    assert discovery_data["options"]["value_evidence"] == [{
        "title": "真实发现演出",
        "metric": "480-1280",
        "source_label": "当前机会",
        "context": {"show_id": show_id},
    }]
    assert cases.json()["data"]["items"] == []
    assert cases.json()["data"]["empty_state"]["title"] == "暂无真实案例"
    assert opportunity.json()["data"]["items"] == []
    assert opportunity.json()["data"]["empty_state"]["title"] == "暂无真实机会"


def test_artist_candidate_and_detail_screens_return_real_artist_fields(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).delete()
        artist = models.Artist(
            name="候选艺人",
            tags="摇滚,乐队",
            heat_score=87,
            fan_count="86万",
            risk_level=2,
            profile={"agency": "真实经纪公司", "availability": "2026-Q4"},
        )
        db.add(artist)
        db.flush()
        db.add(models.Project(
            tenant_id=tenant.id,
            name="候选组合项目",
            artist_id=artist.id,
            artist_name=artist.name,
            created_by=user.id,
        ))
        db.commit()
        artist_id = artist.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        candidates = client.get(
            "/miniapp/screens/S19",
            headers={"Authorization": f"Bearer {token}"},
        )
        detail = client.get(
            f"/miniapp/screens/S20?artist_id={artist_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert candidates.status_code == 200
    candidate = next(
        item for item in candidates.json()["data"]["items"]
        if item["context"]["artist_id"] == artist_id
    )
    assert candidate["title"] == "候选艺人"
    assert candidate["value"] == "87"
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["options"]["artist"]["profile"]["agency"] == "真实经纪公司"
    assert detail_data["items"][0]["context"]["risk_level"] == 2


def test_city_and_venue_screens_are_tenant_scoped_and_show_verified_fields(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Venue).delete()
        project = models.Project(
            tenant_id=tenant.id,
            name="场馆组合项目",
            city="成都",
            created_by=user.id,
        )
        venue = models.Venue(
            tenant_id=tenant.id,
            name="成都金融城演艺中心",
            city="成都",
            capacity=12000,
            quote=860000,
            fire_safety_status="verified",
            transport_notes="地铁直达",
            source="manual",
        )
        other_tenant = models.Tenant(name="场馆隔离租户", status="active")
        db.add_all([project, venue, other_tenant])
        db.flush()
        hidden_venue = models.Venue(
            tenant_id=other_tenant.id,
            name="不可见场馆",
            city="成都",
            capacity=99999,
            quote=1,
            source="manual",
        )
        db.add(hidden_venue)
        db.commit()
        project_id = project.id
        venue_id = venue.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        city_response = client.get(
            f"/miniapp/screens/S22?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        venue_response = client.get(
            f"/miniapp/screens/S24?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert city_response.status_code == 200
    city_items = city_response.json()["data"]["items"]
    assert [item["title"] for item in city_items] == ["成都"]
    assert city_items[0]["context"]["venue_count"] == 1
    assert venue_response.status_code == 200
    venue_items = venue_response.json()["data"]["items"]
    assert [item["context"]["venue_id"] for item in venue_items] == [venue_id]
    assert venue_items[0]["context"]["capacity"] == 12000
    assert venue_items[0]["context"]["quote"] == 860000
    assert venue_items[0]["context"]["fire_safety_status"] == "verified"
    assert all(item["title"] != "不可见场馆" for item in venue_items)


def test_tour_and_review_screens_use_ordered_stops_latest_snapshot_and_actuals(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="巡演成都站",
            city="成都",
            expected_attendance=10000,
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=1,
            input_snapshot={"city": "成都"},
            finance_result={
                "status": "calculated",
                "scenarios": {
                    "neutral": {
                        "attendance": 10000,
                        "revenue": 6000000,
                        "cost": 4200000,
                        "profit": 1800000,
                    },
                },
            },
            created_by=user.id,
        )
        plan = models.TourPlan(
            tenant_id=tenant.id,
            name="真实巡演",
            status="active",
            created_by=user.id,
        )
        db.add_all([version, plan])
        db.flush()
        project.current_version_id = version.id
        db.add_all([
            models.TourStop(
                tour_plan_id=plan.id,
                project_id=project.id,
                city="成都",
                sequence=2,
                scheduled_at="2026-12-08",
                status="confirmed",
            ),
            models.TourStop(
                tour_plan_id=plan.id,
                city="重庆",
                sequence=1,
                scheduled_at="2026-12-01",
                status="planned",
            ),
            models.TicketingSnapshot(
                project_id=project.id,
                captured_at=datetime(2026, 9, 20, 10, 0),
                sold_count=3200,
                gross_revenue=1900000,
                source="ticketing",
            ),
            models.TicketingSnapshot(
                project_id=project.id,
                captured_at=datetime(2026, 9, 28, 10, 0),
                sold_count=5800,
                gross_revenue=3500000,
                source="ticketing",
            ),
            models.ProjectActual(
                project_id=project.id,
                actual_attendance=9200,
                actual_revenue=5700000,
                actual_cost=4300000,
                actual_profit=1400000,
                status="settled",
                notes="已完成结算",
            ),
        ])
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        responses = {}
        for screen_id in ("S61", "S62", "S63", "S64", "S65", "S66"):
            query = f"?project_id={project_id}" if screen_id in {"S63", "S64", "S65", "S66"} else ""
            response = client.get(
                f"/miniapp/screens/{screen_id}{query}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            responses[screen_id] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert responses["S61"]["items"][0]["title"] == "真实巡演"
    assert [item["context"]["sequence"] for item in responses["S62"]["items"]] == [1, 2]
    assert responses["S63"]["items"][0]["context"]["project_id"] == project_id
    assert responses["S64"]["options"]["snapshot"]["sold_count"] == 5800
    assert responses["S64"]["options"]["snapshot"]["gross_revenue"] == 3500000
    assert responses["S64"]["options"]["ticketing_loop"]["current_sold_count"] == 5800
    assert responses["S65"]["options"]["actual"]["actual_profit"] == 1400000
    assert responses["S65"]["options"]["actuals_summary"]["actual_profit"] == 1400000
    assert responses["S66"]["options"]["variance"] == {
        "attendance": -800,
        "revenue": -300000,
        "cost": 100000,
        "profit": -400000,
    }
    assert responses["S66"]["options"]["calibration_loop"]["forecast_profit"] == 1800000
    assert responses["S66"]["options"]["calibration_loop"]["actual_profit"] == 1400000


def test_project_review_does_not_invent_variance_without_actuals(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="待复盘项目",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=1,
            input_snapshot={},
            finance_result={
                "status": "calculated",
                "scenarios": {
                    "neutral": {
                        "attendance": 6000,
                        "revenue": 3000000,
                        "cost": 2100000,
                        "profit": 900000,
                    },
                },
            },
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()
        project_id = project.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            f"/miniapp/screens/S66?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["options"]["variance"] is None
    assert data["items"] == []
    assert data["empty_state"]["title"] == "暂无实际结果"


def test_account_collaboration_and_privacy_screens_read_scoped_saved_state(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        member = models.User(
            account="account_member",
            name="协作成员",
            phone="13800000001",
            group_code="C",
            status="active",
        )
        outsider = models.User(
            account="account_outsider",
            name="外部用户",
            phone="13800000002",
            status="active",
        )
        db.add_all([member, outsider])
        db.flush()
        db.add_all([
            models.TenantMember(tenant_id=tenant.id, user_id=member.id, role="editor"),
            models.Notification(
                tenant_id=tenant.id,
                user_id=user.id,
                business_key="current-user-notice",
                notification_type="task",
                title="当前用户通知",
                content="请处理任务",
                status="unread",
            ),
            models.Notification(
                tenant_id=tenant.id,
                user_id=member.id,
                business_key="other-user-notice",
                title="其他用户通知",
            ),
            models.UserSetting(
                tenant_id=tenant.id,
                user_id=user.id,
                locale="zh-CN",
                theme="light",
                notification_preferences={"task": True, "system": False},
            ),
            models.PrivacyConsent(
                tenant_id=tenant.id,
                user_id=user.id,
                scope="profile",
                granted=1,
                policy_version="2026-09",
                granted_at=datetime(2026, 9, 28, 9, 0),
            ),
            models.MemberInvitation(
                tenant_id=tenant.id,
                invitee="new.member@example.com",
                role="member",
                token="secret-invitation-token",
                status="pending",
                invited_by=user.id,
                expires_at=datetime(2026, 10, 5, 9, 0),
            ),
            models.AgentPermission(
                tenant_id=tenant.id,
                user_id=user.id,
                capability="project_analysis",
                enabled=1,
            ),
        ])
        db.commit()
        member_id = member.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        responses = {}
        for screen_id in ("S01", "S02", "S03", "S60", "S67", "S68", "S69", "S70", "S71", "S72", "S83", "S84"):
            response = client.get(
                f"/miniapp/screens/{screen_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            responses[screen_id] = response.json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert responses["S01"]["options"]["login_methods"] == ["wechat", "web"]
    assert responses["S02"]["items"][0]["context"]["tenant_id"] == tenant.id
    assert responses["S03"]["items"][0]["context"]["scope"] == "profile"
    assert responses["S60"]["items"][0]["context"]["capability"] == "project_analysis"
    assert responses["S71"]["summary"]["subtitle"] == "隐私授权与工作能力"
    assert responses["S67"]["options"]["user"]["id"] == user.id
    assert {item["context"]["user_id"] for item in responses["S68"]["items"]} == {
        user.id,
        member_id,
    }
    assert [item["title"] for item in responses["S69"]["items"]] == ["当前用户通知"]
    assert responses["S70"]["options"]["setting"]["theme"] == "light"
    assert responses["S71"]["options"]["privacy_consents"][0]["scope"] == "profile"
    assert responses["S72"]["items"][0]["title"] == "new.member@example.com"
    assert "secret-invitation-token" not in str(responses["S72"])
    assert responses["S83"]["options"]["notification_preferences"] == {
        "task": True,
        "system": False,
    }
    assert responses["S84"]["items"][0]["context"]["policy_version"] == "2026-09"


def test_developer_connection_screen_exposes_status_without_secret_values(monkeypatch):
    monkeypatch.setenv("WECHAT_MINIAPP_APPID", "wx-public-id")
    monkeypatch.setenv("WECHAT_MINIAPP_SECRET", "wechat-secret-value")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio-access-value")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio-secret-value")
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        response = client.get(
            "/miniapp/screens/S82",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["options"]["connections"]["wechat"]["configured"] is True
    assert data["options"]["connections"]["object_storage"]["configured"] is True
    serialized = str(data)
    assert "wechat-secret-value" not in serialized
    assert "minio-access-value" not in serialized
    assert "minio-secret-value" not in serialized


def test_project_empty_state_only_applies_when_current_tenant_has_no_projects(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        db.query(models.Project).filter(models.Project.tenant_id == tenant.id).delete()
        db.commit()
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        empty_response = client.get(
            "/miniapp/screens/S73",
            headers={"Authorization": f"Bearer {token}"},
        )
        db = session_factory()
        db.add(models.Project(
            tenant_id=tenant.id,
            name="已存在项目",
            created_by=user.id,
        ))
        db.commit()
        db.close()
        populated_response = client.get(
            "/miniapp/screens/S73",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert empty_response.status_code == 200
    assert empty_response.json()["data"]["items"] == []
    assert empty_response.json()["data"]["empty_state"]["title"] == "暂无项目"
    populated_data = populated_response.json()["data"]
    assert [item["title"] for item in populated_data["items"]] == ["已存在项目"]
    assert populated_data["empty_state"] is None


def test_processing_version_and_archive_states_validate_real_project_context(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="状态页项目",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        versions = [
            models.ProjectVersion(
                project_id=project.id,
                version_no=number,
                input_snapshot={"version": number},
                status="draft",
                created_by=user.id,
            )
            for number in (1, 2)
        ]
        db.add_all(versions)
        db.flush()
        project.current_version_id = versions[1].id
        job = models.ProjectAnalysisJob(
            tenant_id=tenant.id,
            project_id=project.id,
            version_id=versions[1].id,
            purpose="项目分析",
            status="running",
            requested_by=user.id,
        )
        db.add(job)
        db.commit()
        project_id = project.id
        old_version_id = versions[0].id
        current_version_id = versions[1].id
        job_id = job.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        processing = client.get(
            f"/miniapp/screens/S74?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        changed = client.get(
            f"/miniapp/screens/S78?project_id={project_id}&version_id={old_version_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        archive = client.get(
            f"/miniapp/screens/S80?project_id={project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        missing = client.get(
            "/miniapp/screens/S74?project_id=999999",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app_module.app.dependency_overrides.clear()

    assert processing.status_code == 200
    assert processing.json()["data"]["options"]["analysis_job"]["id"] == job_id
    assert changed.json()["data"]["options"]["requested_version_id"] == old_version_id
    assert changed.json()["data"]["options"]["current_version_id"] == current_version_id
    assert archive.json()["data"]["options"]["project"]["id"] == project_id
    assert missing.status_code == 404


def test_recoverable_state_screens_have_explicit_targets_without_business_items(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    expected_targets = {
        "S75": "retry",
        "S76": "S10",
        "S77": "S10",
        "S79": "back",
        "S81": "S01",
    }
    try:
        for screen_id, target in expected_targets.items():
            response = client.get(
                f"/miniapp/screens/{screen_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["items"] == []
            assert data["options"]["recovery_target"] == target
    finally:
        app_module.app.dependency_overrides.clear()


def test_cross_tenant_entities_are_hidden_across_project_task_evidence_version_notification_and_tour(monkeypatch):
    client, session_factory = make_screen_client(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        own_project = models.Project(tenant_id=tenant.id, name="当前租户项目", created_by=user.id)
        other_tenant = models.Tenant(name="隔离客户空间", status="active")
        db.add_all([own_project, other_tenant])
        db.flush()
        other_project = models.Project(
            tenant_id=other_tenant.id,
            name="不可见项目",
            created_by=user.id,
        )
        db.add(other_project)
        db.flush()
        hidden_version = models.ProjectVersion(
            project_id=other_project.id,
            version_no=1,
            input_snapshot={"secret": True},
            created_by=user.id,
        )
        hidden_evidence = models.Evidence(
            project_id=other_project.id,
            name="不可见证据",
            file_url="https://assets.example.com/hidden.pdf",
            source="private",
            status="verified",
        )
        hidden_task = models.Task(
            project_id=other_project.id,
            title="不可见任务",
            status="pending",
        )
        hidden_notification = models.Notification(
            tenant_id=other_tenant.id,
            user_id=user.id,
            business_key="hidden-notification",
            title="不可见通知",
        )
        hidden_plan = models.TourPlan(
            tenant_id=other_tenant.id,
            name="不可见巡演",
            created_by=user.id,
        )
        db.add_all([
            hidden_version,
            hidden_evidence,
            hidden_task,
            hidden_notification,
            hidden_plan,
        ])
        db.commit()
        own_project_id = own_project.id
        other_project_id = other_project.id
        hidden_task_id = hidden_task.id
        token = f"dev-token-{user.id}-{tenant.id}"
    finally:
        db.close()

    try:
        project_response = client.get(
            f"/miniapp/screens/S11?project_id={other_project_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        task_response = client.get(
            f"/miniapp/screens/S57?task_id={hidden_task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        versions = client.get(
            f"/miniapp/screens/S12?project_id={own_project_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["data"]
        evidence = client.get(
            f"/miniapp/screens/S38?project_id={own_project_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["data"]
        notifications = client.get(
            "/miniapp/screens/S69",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["data"]
        tours = client.get(
            "/miniapp/screens/S61",
            headers={"Authorization": f"Bearer {token}"},
        ).json()["data"]
    finally:
        app_module.app.dependency_overrides.clear()

    assert project_response.status_code == 404
    assert task_response.status_code == 404
    assert all(item["title"] != "不可见项目" for item in versions["items"])
    assert all(item["title"] != "不可见证据" for item in evidence["items"])
    assert all(item["title"] != "不可见通知" for item in notifications["items"])
    assert all(item["title"] != "不可见巡演" for item in tours["items"])


def test_core_screen_providers_stay_within_query_budgets(monkeypatch):
    session_factory = make_screen_session(monkeypatch)
    db = session_factory()
    try:
        tenant, user = services.get_or_create_default_context(db)
        project = models.Project(
            tenant_id=tenant.id,
            name="查询预算项目",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        version = models.ProjectVersion(
            project_id=project.id,
            version_no=1,
            input_snapshot={},
            status="draft",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        project.current_version_id = version.id
        db.commit()

        from app.miniapp_screens import ScreenRequestContext, build_miniapp_screen

        context = ScreenRequestContext(
            tenant_id=tenant.id,
            user_id=user.id,
            project_id=project.id,
        )
        query_count = 0

        def count_query(*_args):
            nonlocal query_count
            query_count += 1

        event.listen(database.engine, "before_cursor_execute", count_query)
        try:
            budgets = {
                "S10": 1,
                "S34": 6,
                "S52": 2,
                "S61": 2,
                "S67": 2,
            }
            for screen_id, budget in budgets.items():
                query_count = 0
                build_miniapp_screen(screen_id, context, db)
                assert query_count <= budget, f"{screen_id} used {query_count} queries, budget is {budget}"
        finally:
            event.remove(database.engine, "before_cursor_execute", count_query)
    finally:
        db.close()
