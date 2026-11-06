# App Package Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize all backend implementation files under `app/` into focused packages and split the monolithic routes, miniapp screens, models, schemas, and services without changing behavior.

**Architecture:** Keep FastAPI as a modular monolith. Stable package entry points re-export public symbols while focused submodules own one business responsibility and dependencies flow from routes toward services, models, database, and configuration.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic v2, pytest.

---

## File Map

The approved structure is defined in
`docs/superpowers/specs/2026-11-06-app-package-reorganization-design.md`.
Implementation ownership is:

- `app/config/`, `app/database/`, `app/core/`, `app/infrastructure/`: runtime foundations.
- `app/models/`: SQLAlchemy models grouped by business ownership.
- `app/schemas/`: Pydantic API contracts grouped by endpoint ownership.
- `app/services/`: authentication, finance, serialization, initialization, and intelligence logic.
- `app/integrations/`: WeChat, LLM, object storage, AMap, and QWeather boundaries.
- `app/documents/`, `app/datasets/`: document processing and static market data.
- `app/miniapp/`: entity details and screen-provider modules.
- `app/routes/`: focused FastAPI routers and aggregate router.
- `tests/test_app_structure.py`: package, metadata, startup, and route contract tests.

No task creates a Git commit unless the user separately authorizes commits.

### Task 1: Freeze Structural Contracts

**Files:**
- Create: `tests/test_app_structure.py`
- Read: `app/main.py`
- Read: `app/models.py`
- Read: `app/routes.py`

- [ ] **Step 1: Add the stable import and startup contract test**

```python
import importlib


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


def test_repository_and_package_entrypoints_share_the_application():
    repository_main = importlib.import_module("main")
    package_main = importlib.import_module("app.main")
    assert repository_main.app is package_main.app
```

- [ ] **Step 2: Add route uniqueness and expected-route tests**

Capture the current route signature set before moving code:

```python
from app.main import app


def iter_routes(routes):
    for route in routes:
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            yield from iter_routes(original_router.routes)
        else:
            yield route


EXCLUDED_FRAMEWORK_PATHS = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}


def test_route_registrations_are_unique():
    signatures = [
        (method, route.path)
        for route in iter_routes(app.routes)
        for method in (getattr(route, "methods", None) or set())
        if route.path not in EXCLUDED_FRAMEWORK_PATHS
    ]
    assert len(signatures) == len(set(signatures))
```

Store the literal pre-refactor signature set:

```python
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


def test_route_contract_matches_pre_refactor_snapshot():
    actual = {
        (method, route.path)
        for route in iter_routes(app.routes)
        for method in (getattr(route, "methods", None) or set())
        if route.path not in EXCLUDED_FRAMEWORK_PATHS
    }
    assert actual == EXPECTED_ROUTE_SIGNATURES
```

- [ ] **Step 3: Add model metadata snapshot test**

Capture the current literal table-name set and assert it after importing
`app.models`:

```python
from app.database import Base
import app.models  # noqa: F401


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


def test_all_model_tables_are_registered():
    assert set(Base.metadata.tables) == EXPECTED_TABLE_NAMES
```

- [ ] **Step 4: Run the structural tests and full baseline**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_app_structure.py -q
PYTHONPATH=. .venv/bin/pytest -q
```

Expected: structural tests pass and the full suite reports at least 133 passed.

### Task 2: Move Foundation and Leaf Modules

**Files:**
- Move: `app/config.py` -> `app/config/__init__.py`
- Move: `app/database.py` -> `app/database/__init__.py`
- Move: `app/schema.sql` -> `app/database/schema.sql`
- Move: `app/cache.py` -> `app/infrastructure/cache.py`
- Move: `app/responses.py` -> `app/core/responses.py`
- Move: `app/market_dossier.py` -> `app/datasets/market_dossier.py`
- Move: `app/document_parsers.py` -> `app/documents/parsers.py`
- Move: `app/feasibility_reports.py` -> `app/documents/feasibility.py`
- Move: `app/connectors.py` -> `app/integrations/connectors.py`
- Create: package `__init__.py` files for `core`, `datasets`, `documents`, `infrastructure`, and `integrations`
- Modify: imports under `app/` and `tests/`

- [ ] **Step 1: Add a failing canonical-path import test**

```python
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
```

- [ ] **Step 2: Move files without altering their behavior**

Use `git mv` for tracked files. Add package markers containing only explicit
public exports; do not use wildcard imports.

- [ ] **Step 3: Update imports**

Use these canonical replacements:

```text
.cache -> .infrastructure.cache
.connectors -> .integrations.connectors
.document_parsers -> .documents.parsers
.feasibility_reports -> .documents.feasibility
.market_dossier -> .datasets.market_dossier
.responses -> .core.responses
```

Adjust relative depth for modules inside subpackages.

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_app_structure.py tests/test_main.py -q
```

Expected: all selected tests pass.

### Task 3: Split SQLAlchemy Models

**Files:**
- Delete after migration: `app/models.py`
- Create: `app/models/__init__.py`
- Create: `app/models/commerce.py`
- Create: `app/models/identity.py`
- Create: `app/models/projects.py`
- Create: `app/models/evidence.py`
- Create: `app/models/intelligence.py`
- Create: `app/models/operations.py`
- Test: `tests/test_app_structure.py`
- Test: `tests/test_miniapp_domain_models.py`

- [ ] **Step 1: Strengthen the model identity contract**

For representative models from every target file, assert that package exports
refer to the class registered in SQLAlchemy:

```python
import app.models as models


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
```

- [ ] **Step 2: Move model classes by approved ownership**

Each model file starts with the required SQLAlchemy imports and:

```python
from app.database import Base
```

Keep every class body byte-for-byte equivalent except import formatting. Do
not import one model module from another.

- [ ] **Step 3: Export all models explicitly**

`app/models/__init__.py` imports every model class from its owner module and
defines `__all__` with the same names.

- [ ] **Step 4: Verify metadata and domain behavior**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_app_structure.py tests/test_miniapp_domain_models.py -q
```

Expected: table snapshot and all domain-model tests pass.

### Task 4: Split Pydantic Schemas

**Files:**
- Delete after migration: `app/schemas.py`
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/miniapp.py`
- Create: `app/schemas/auth.py`
- Create: `app/schemas/projects.py`
- Create: `app/schemas/finance.py`
- Create: `app/schemas/decisions.py`
- Create: `app/schemas/intelligence.py`
- Test: `tests/test_app_structure.py`
- Test: `tests/test_miniapp_screens.py`

- [ ] **Step 1: Add schema export coverage**

```python
import app.schemas as schemas


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
```

- [ ] **Step 2: Move schema classes by endpoint ownership**

Keep class definitions and Pydantic v2 validators unchanged. Shared schema
types needed by another file must be imported from their canonical owner.

- [ ] **Step 3: Export all schemas explicitly**

`app/schemas/__init__.py` re-exports every class formerly defined in
`app/schemas.py`; existing `from app.schemas import ...` statements must keep
working.

- [ ] **Step 4: Verify**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_app_structure.py tests/test_miniapp_screens.py -q
```

Expected: all selected tests pass.

### Task 5: Split Services

**Files:**
- Delete after migration: `app/services.py`
- Create: `app/services/__init__.py`
- Create: `app/services/auth.py`
- Create: `app/services/finance.py`
- Create: `app/services/serializers.py`
- Create: `app/services/seeding.py`
- Create: `app/services/intelligence.py`
- Modify: imports under `app/` and tests

- [ ] **Step 1: Add stable service export tests**

```python
import app.services as services


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
```

- [ ] **Step 2: Move authentication and finance functions**

Move request context, token, password, user-role helpers to `auth.py`.
Move financial input snapshots and calculations to `finance.py`.

- [ ] **Step 3: Move serializers and intelligence helpers**

Move all `serialize_*` functions to `serializers.py`. Move connector health and
market-dossier idempotent upsert helpers to `intelligence.py`.

- [ ] **Step 4: Move initialization**

Move seed constants, seed functions, runtime-column checks, `init_db`, and
`next_project_version_no` to `seeding.py`. Import every model through
`app.models` before `Base.metadata.create_all`.

- [ ] **Step 5: Add explicit package exports and verify**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_app_structure.py tests/test_miniapp_domain_models.py tests/test_main.py -q
```

Expected: all selected tests pass.

### Task 6: Split Miniapp Entity and Screen Providers

**Files:**
- Move: `app/miniapp_entity_details.py` -> `app/miniapp/entities.py`
- Delete after migration: `app/miniapp_screens.py`
- Create: `app/miniapp/__init__.py`
- Create: `app/miniapp/screens/__init__.py`
- Create: `app/miniapp/screens/common.py`
- Create: `app/miniapp/screens/registry.py`
- Create: `app/miniapp/screens/discovery.py`
- Create: `app/miniapp/screens/projects.py`
- Create: `app/miniapp/screens/finance.py`
- Create: `app/miniapp/screens/decisioning.py`
- Create: `app/miniapp/screens/tasks.py`
- Create: `app/miniapp/screens/agent.py`
- Create: `app/miniapp/screens/account.py`
- Modify: `tests/test_miniapp_screens.py`

- [ ] **Step 1: Change canonical import tests first**

Replace tests that import old internal modules with:

```python
from app.miniapp.entities import EntityRequestContext, build_miniapp_entity_detail
from app.miniapp.screens import SCREEN_PROVIDERS, ScreenRequestContext, build_miniapp_screen
```

The tests must fail until the new modules exist.

- [ ] **Step 2: Move shared types and helpers**

Put `ScreenRequestContext`, registration dataclasses, empty-state helpers,
display helpers, user-name lookups, and common serializers in `common.py`.

- [ ] **Step 3: Move providers by workflow**

Move complete provider functions and their private constants to the approved
workflow modules. A provider file may import `common.py`, models, schemas, and
services, but must not import `registry.py`.

- [ ] **Step 4: Build the registry**

`registry.py` imports provider functions, defines `SCREEN_PROVIDERS`, validates
unknown IDs, and delegates `build_miniapp_screen`. `screens/__init__.py`
explicitly exports the three public miniapp screen symbols.

- [ ] **Step 5: Verify every miniapp contract**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_miniapp_screens.py -q
```

Expected: every existing miniapp test passes.

### Task 7: Extract External Integrations from Routes

**Files:**
- Create: `app/integrations/wechat.py`
- Create: `app/integrations/llm.py`
- Create: `app/integrations/object_storage.py`
- Modify: `tests/test_main.py`
- Modify later route owners under `app/routes/`

- [ ] **Step 1: Retarget monkeypatch-based tests**

Tests must patch provider clients at canonical owner modules:

```python
import app.integrations.connectors as connector_integration
import app.integrations.llm as llm_integration
import app.integrations.object_storage as storage_integration
import app.integrations.wechat as wechat_integration
```

- [ ] **Step 2: Move provider-specific helpers**

Move functions without changing signatures, environment lookups, timeout
values, UTF-8 handling, output cleaning, or storage paths.

- [ ] **Step 3: Verify focused provider behavior**

Run the captcha, WeChat, MinIO, connector, AI generation, and SSE tests from
`tests/test_main.py`.

Expected: all focused tests pass.

### Task 8: Split and Aggregate FastAPI Routes

**Files:**
- Delete after migration: `app/routes.py`
- Create: `app/routes/__init__.py`
- Create: `app/routes/auth.py`
- Create: `app/routes/miniapp.py`
- Create: `app/routes/users.py`
- Create: `app/routes/projects.py`
- Create: `app/routes/finance.py`
- Create: `app/routes/decisioning.py`
- Create: `app/routes/evidence.py`
- Create: `app/routes/intelligence.py`
- Create: `app/routes/reports.py`
- Create: `app/routes/ai.py`
- Create: `app/routes/shows.py`
- Create: `app/routes/health.py`
- Modify: `app/main.py`
- Modify: repository `main.py`

- [ ] **Step 1: Move endpoints with their route-local helpers**

Each module defines:

```python
from fastapi import APIRouter

router = APIRouter()
```

Move each decorated endpoint to exactly one owner module. Import shared
business behavior from services, documents, miniapp, or integrations rather
than from another route module.

- [ ] **Step 2: Aggregate routers exactly once**

`app/routes/__init__.py` creates one aggregate router:

```python
from fastapi import APIRouter
from . import ai, auth, decisioning, evidence, finance, health, intelligence
from . import miniapp, projects, reports, shows, users

router = APIRouter()
for child in (
    miniapp.router,
    auth.router,
    users.router,
    projects.router,
    finance.router,
    decisioning.router,
    evidence.router,
    intelligence.router,
    reports.router,
    ai.router,
    shows.router,
    health.router,
):
    router.include_router(child)
```

Explicitly re-export endpoint functions imported by repository `main.py`.

- [ ] **Step 3: Verify route parity before broader tests**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_app_structure.py -q
```

Expected: exact pre-refactor method/path set, no duplicates, and both
application entry points import successfully.

- [ ] **Step 4: Run all API tests**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_main.py -q
```

Expected: all API tests pass.

### Task 9: Documentation, Cleanup, and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `.gitignore` only if generated caches are not already ignored
- Verify: all files under `app/`

- [ ] **Step 1: Update the README**

Replace the flat backend tree with the new package structure and document:

```text
Routes: app/routes/
Business services: app/services/
External providers: app/integrations/
Miniapp screen providers: app/miniapp/screens/
Models: app/models/
Schemas: app/schemas/
Startup: python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 2: Scan for stale internal imports and flat files**

Run:

```bash
rg -n "app\.(miniapp_screens|miniapp_entity_details|document_parsers|feasibility_reports|connectors|cache|market_dossier|responses)" . --glob '*.py'
find app -maxdepth 1 -type f -print | sort
```

Expected: no stale internal imports; root contains only `app/__init__.py` and
`app/main.py`.

- [ ] **Step 3: Run the complete verification suite**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python -m compileall app
PYTHONPATH=. .venv/bin/python -c "from app.main import app; assert app.openapi()"
git diff --check
```

Expected: at least 133 tests pass, compilation succeeds, OpenAPI generation
succeeds, and Git reports no whitespace errors.

- [ ] **Step 4: Review final diff**

Confirm no API paths, model table names, response contracts, or runtime
configuration values changed. Confirm no `.pyc`, `__pycache__`, local
database, credentials, or environment files are included.
