import pytest

from test_main import app_module, make_test_client
from test_ai_user_isolation import login
from app.models import Project, ProjectVersion, Tenant, TenantMember


@pytest.fixture
def writer_client(monkeypatch):
    client, sessions = make_test_client(monkeypatch)
    headers, identity = login(client, monkeypatch, "b_user")
    try:
        yield client, sessions, headers, identity
    finally:
        app_module.app.dependency_overrides.clear()


def test_created_project_belongs_to_logged_in_creator_and_is_collaboratable(writer_client):
    client, sessions, headers, identity = writer_client
    response = client.post("/projects", headers=headers, json={"name": "主办方新建项目"})
    assert response.status_code == 200
    project_id = response.json()["data"]["id"]
    with sessions() as db:
        project = db.get(Project, project_id)
        assert project.created_by == identity["user"]["id"]
        assert db.get(ProjectVersion, project.current_version_id).created_by == identity["user"]["id"]
    projects = client.get("/collaboration", headers=headers).json()["data"]["projects"]
    assert project_id in [project["id"] for project in projects]


@pytest.mark.parametrize("route", ["version", "calculate", "show-calculation"])
def test_project_versions_record_actual_writer(writer_client, monkeypatch, route):
    client, sessions, _, identity = writer_client
    project_id = client.post("/projects", json={"name": "已有项目"}).json()["data"]["id"]
    headers, identity = login(client, monkeypatch, "b_user")
    endpoint, payload = (
        (f"/projects/{project_id}/versions", {"name": "修订项目"})
        if route == "version"
        else ("/finance/" + route, {"project_id": project_id})
    )
    assert client.post(endpoint, headers=headers, json=payload).status_code == 200
    with sessions() as db:
        project = db.get(Project, project_id)
        assert db.get(ProjectVersion, project.current_version_id).created_by == identity["user"]["id"]


def test_writer_uses_authorized_tenant_and_rejects_invalid_session(writer_client):
    client, sessions, headers, identity = writer_client
    with sessions() as db:
        tenant = Tenant(name="第二授权空间", status="active")
        db.add(tenant)
        db.flush()
        tenant_id = tenant.id
        db.add(TenantMember(tenant_id=tenant_id, user_id=identity["user"]["id"], role="member"))
        db.commit()
    scoped = {**headers, "X-Tenant-Id": str(tenant_id)}
    response = client.post("/projects", headers=scoped, json={"name": "第二空间项目"})
    assert response.status_code == 200
    project_id = response.json()["data"]["id"]
    with sessions() as db:
        assert db.get(Project, project_id).tenant_id == tenant_id
    assert client.post("/finance/calculate", headers=scoped, json={"project_id": project_id}).status_code == 200
    assert client.post("/finance/calculate", headers=headers, json={"project_id": project_id}).status_code == 404
    assert client.post("/projects", headers={"Authorization": "Bearer forged"}, json={"name": "非法会话"}).status_code == 401
    assert client.post("/projects", headers={"X-Tenant-Id": str(tenant_id)}, json={"name": "缺少会话"}).status_code == 401
