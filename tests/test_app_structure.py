import importlib

import app.models  # noqa: F401
import app.models as models
import app.schemas as schemas
import app.services as services
from app.database import Base
from app.main import app


EXCLUDED_FRAMEWORK_PATHS = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}

EXPECTED_ROUTE_SIGNATURES = {
    ("DELETE", "/users/{user_id}"),
    ("GET", "/alerts"),
    ("GET", "/analytics/dashboard"),
    ("GET", "/artists"),
    ("GET", "/artists/{artist_id}"),
    ("GET", "/assumptions"),
    ("GET", "/auth/captcha"),
    ("GET", "/case-outcomes"),
    ("GET", "/cases/search"),
    ("GET", "/conversion-assumptions"),
    ("GET", "/data-assets"),
    ("GET", "/data-records"),
    ("GET", "/data-sources"),
    ("GET", "/evidences"),
    ("GET", "/external-data/jobs"),
    ("GET", "/external-data/jobs/{job_id}"),
    ("GET", "/facts"),
    ("GET", "/gates"),
    ("GET", "/miniapp/entities/{entity_type}/{entity_id}"),
    ("GET", "/miniapp/screens/{screen_id}"),
    ("GET", "/miniapp/search"),
    ("GET", "/monitoring-rules"),
    ("GET", "/ping"),
    ("GET", "/projects"),
    ("GET", "/projects/{project_id}"),
    ("GET", "/projects/{project_id}/analysis-jobs/{job_id}"),
    ("GET", "/projects/{project_id}/calibration"),
    ("GET", "/projects/{project_id}/decision-snapshots"),
    ("GET", "/projects/{project_id}/versions"),
    ("GET", "/projects/{project_id}/work-plan"),
    ("GET", "/reports/files/{evidence_id}"),
    ("GET", "/risks"),
    ("GET", "/shows"),
    ("GET", "/shows/recommendations"),
    ("GET", "/shows/{show_id}"),
    ("GET", "/tasks"),
    ("GET", "/tenants"),
    ("GET", "/ticketing/summary"),
    ("GET", "/user-groups"),
    ("GET", "/users"),
    ("PATCH", "/users/{user_id}"),
    ("POST", "/agent/chat"),
    ("POST", "/ai/generate"),
    ("POST", "/ai/generate/stream"),
    ("POST", "/alerts/{alert_id}/acknowledge"),
    ("POST", "/alerts/{alert_id}/resolve"),
    ("POST", "/assumptions"),
    ("POST", "/auth/web-login"),
    ("POST", "/auth/wechat-login"),
    ("POST", "/calibration-candidates/{calibration_id}/approve"),
    ("POST", "/case-outcomes"),
    ("POST", "/conversion-assumptions"),
    ("POST", "/data-assets"),
    ("POST", "/data-quality-issues/{issue_id}/resolve"),
    ("POST", "/data-sources"),
    ("POST", "/data-sources/{source_id}/health-check"),
    ("POST", "/decisions"),
    ("POST", "/document-parse-jobs/{job_id}/confirm-projects"),
    ("POST", "/document-parse-jobs/{job_id}/run"),
    ("POST", "/evidences/upload"),
    ("POST", "/evidences/{evidence_id}/parse-jobs"),
    ("POST", "/external-data/jobs"),
    ("POST", "/external-data/jobs/{job_id}/run"),
    ("POST", "/facts"),
    ("POST", "/facts/{fact_id}/verify"),
    ("POST", "/finance/breakeven"),
    ("POST", "/finance/calculate"),
    ("POST", "/finance/show-calculation"),
    ("POST", "/gates"),
    ("POST", "/monitoring-rules"),
    ("POST", "/monitoring-rules/{rule_id}/evaluate"),
    ("POST", "/oss/uploads/initiate"),
    ("POST", "/oss/uploads/{upload_id}/complete"),
    ("POST", "/projects"),
    ("POST", "/projects/{project_id}/analysis-jobs"),
    ("POST", "/projects/{project_id}/feasibility-report"),
    ("POST", "/projects/{project_id}/versions"),
    ("POST", "/projects/{project_id}/work-events"),
    ("POST", "/projects/{project_id}/work-plan/refresh"),
    ("POST", "/reports/{project_id}/share"),
    ("POST", "/risks"),
    ("POST", "/shows/{show_id}/order"),
    ("POST", "/tasks"),
    ("POST", "/tasks/actions/batch"),
    ("POST", "/tasks/{task_id}/accept"),
    ("POST", "/tasks/{task_id}/submit"),
    ("POST", "/tenants/switch"),
    ("POST", "/users"),
}

EXPECTED_TABLE_NAMES = {
    "agent_permissions",
    "ai_generations",
    "alert_events",
    "artists",
    "assumptions",
    "case_outcomes",
    "conversion_assumptions",
    "data_assets",
    "data_quality_issues",
    "data_records",
    "data_sources",
    "decision_snapshots",
    "decisions",
    "document_parse_jobs",
    "evidences",
    "external_data_jobs",
    "facts",
    "forecast_calibrations",
    "gates",
    "member_invitations",
    "monitoring_rules",
    "notifications",
    "orders",
    "oss_uploads",
    "privacy_consents",
    "project_actuals",
    "project_analysis_jobs",
    "project_drafts",
    "project_versions",
    "project_work_events",
    "project_work_plans",
    "projects",
    "report_shares",
    "risks",
    "shows",
    "tasks",
    "tenant_members",
    "tenants",
    "ticketing_snapshots",
    "tour_plans",
    "tour_stops",
    "user_groups",
    "user_settings",
    "users",
    "venues",
}


def iter_routes(routes):
    for route in routes:
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            yield from iter_routes(original_router.routes)
        else:
            yield route


def route_signatures():
    return [
        (method, route.path)
        for route in iter_routes(app.routes)
        for method in (getattr(route, "methods", None) or set())
        if route.path not in EXCLUDED_FRAMEWORK_PATHS
    ]


def test_stable_backend_packages_are_importable():
    for name in (
        "app.config",
        "app.database",
        "app.models",
        "app.schemas",
        "app.services",
        "app.routes",
        "app.main",
    ):
        assert importlib.import_module(name) is not None


def test_leaf_modules_use_canonical_package_paths():
    modules = (
        "app.core.responses",
        "app.datasets.market_dossier",
        "app.documents.parsers",
        "app.documents.feasibility",
        "app.infrastructure.cache",
        "app.integrations.connectors",
    )
    for name in modules:
        assert importlib.import_module(name) is not None


def test_repository_and_package_entrypoints_share_the_application():
    repository_main = importlib.import_module("main")
    package_main = importlib.import_module("app.main")
    assert repository_main.app is package_main.app


def test_route_registrations_are_unique():
    signatures = route_signatures()
    assert len(signatures) == len(set(signatures))


def test_route_contract_matches_pre_refactor_snapshot():
    assert set(route_signatures()) == EXPECTED_ROUTE_SIGNATURES


def test_all_model_tables_are_registered():
    assert set(Base.metadata.tables) == EXPECTED_TABLE_NAMES


def test_model_package_exports_registered_classes():
    for model in (
        models.Artist,
        models.User,
        models.Project,
        models.Evidence,
        models.DataAsset,
        models.Venue,
    ):
        assert Base.metadata.tables[model.__tablename__] is model.__table__


def test_representative_models_have_focused_module_owners():
    assert models.Artist.__module__ == "app.models.commerce"
    assert models.User.__module__ == "app.models.identity"
    assert models.Project.__module__ == "app.models.projects"
    assert models.Evidence.__module__ == "app.models.evidence"
    assert models.DataAsset.__module__ == "app.models.intelligence"
    assert models.Venue.__module__ == "app.models.operations"


def test_schema_package_keeps_public_contracts():
    expected = {
        "MiniappScreenData",
        "MiniappEntityDetail",
        "WebLoginIn",
        "ProjectIn",
        "FinanceCalculateIn",
        "DecisionIn",
        "DataAssetIn",
    }
    assert expected <= set(dir(schemas))


def test_representative_schemas_have_focused_module_owners():
    assert schemas.MiniappScreenData.__module__ == "app.schemas.miniapp"
    assert schemas.WebLoginIn.__module__ == "app.schemas.auth"
    assert schemas.ProjectIn.__module__ == "app.schemas.projects"
    assert schemas.FinanceCalculateIn.__module__ == "app.schemas.finance"
    assert schemas.DecisionIn.__module__ == "app.schemas.decisions"
    assert schemas.DataAssetIn.__module__ == "app.schemas.intelligence"


def test_service_package_keeps_public_exports():
    for name in (
        "resolve_request_context",
        "create_session_token",
        "calculate_finance_result",
        "serialize_project",
        "seed_initial_data",
        "init_db",
    ):
        assert callable(getattr(services, name))


def test_representative_services_have_focused_module_owners():
    assert services.resolve_request_context.__module__ == "app.services.auth"
    assert services.calculate_finance_result.__module__ == "app.services.finance"
    assert services.serialize_project.__module__ == "app.services.serializers"
    assert services.connector_health.__module__ == "app.services.intelligence"
    assert services.init_db.__module__ == "app.services.seeding"
