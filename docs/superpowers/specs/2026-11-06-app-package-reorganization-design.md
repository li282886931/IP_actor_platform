# App Package Reorganization Design

## Goal

Reorganize the flat `app/` backend package into focused subpackages and split
the largest modules by business responsibility without changing externally
observable behavior.

The refactor must preserve:

- FastAPI paths, methods, request bodies, response envelopes, and status codes.
- The `uvicorn main:app` startup command.
- Database table names, columns, constraints, initialization, and seed behavior.
- Miniapp screen and entity-detail payload contracts.
- SSE UTF-8 decoding and AI output sanitization.
- Idempotent persistence and existing tenant isolation rules.

The current verification baseline is 130 passing backend tests:

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

## Scope

This is a structural refactor of all backend modules under `app/`. It includes
splitting `routes.py`, `miniapp_screens.py`, `services.py`, `models.py`, and
`schemas.py`, moving smaller modules into responsibility-based directories,
updating imports and tests, and documenting the new layout.

It does not introduce new product behavior, API versions, database migrations,
repositories, dependency-injection frameworks, or exception hierarchies.

## Target Structure

`app/__init__.py` remains the package marker and `app/main.py` remains the
FastAPI composition root. All other implementation files move into focused
packages.

```text
app/
├── __init__.py
├── main.py
├── config/
│   └── __init__.py
├── database/
│   ├── __init__.py
│   └── schema.sql
├── models/
│   ├── __init__.py
│   ├── commerce.py
│   ├── identity.py
│   ├── projects.py
│   ├── evidence.py
│   ├── intelligence.py
│   └── operations.py
├── schemas/
│   ├── __init__.py
│   ├── miniapp.py
│   ├── auth.py
│   ├── projects.py
│   ├── finance.py
│   ├── decisions.py
│   └── intelligence.py
├── services/
│   ├── __init__.py
│   ├── auth.py
│   ├── finance.py
│   ├── serializers.py
│   ├── seeding.py
│   └── intelligence.py
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── miniapp.py
│   ├── users.py
│   ├── projects.py
│   ├── finance.py
│   ├── decisioning.py
│   ├── evidence.py
│   ├── intelligence.py
│   ├── reports.py
│   ├── ai.py
│   ├── shows.py
│   └── health.py
├── miniapp/
│   ├── __init__.py
│   ├── entities.py
│   └── screens/
│       ├── __init__.py
│       ├── common.py
│       ├── registry.py
│       ├── discovery.py
│       ├── projects.py
│       ├── finance.py
│       ├── decisioning.py
│       ├── tasks.py
│       ├── agent.py
│       └── account.py
├── documents/
│   ├── __init__.py
│   ├── parsers.py
│   └── feasibility.py
├── integrations/
│   ├── __init__.py
│   ├── connectors.py
│   ├── llm.py
│   ├── object_storage.py
│   └── wechat.py
├── infrastructure/
│   ├── __init__.py
│   └── cache.py
├── datasets/
│   ├── __init__.py
│   └── market_dossier.py
└── core/
    ├── __init__.py
    └── responses.py
```

The implementation may add narrowly named files within these packages when a
listed file would otherwise retain multiple unrelated responsibilities. It
must not collapse the design back into generic `utils.py` or `helpers.py`
modules.

## Compatibility Boundaries

The following import paths remain stable through package-level re-exports:

- `app.config`
- `app.database`
- `app.models`
- `app.schemas`
- `app.services`
- `app.routes`
- `app.main`

The repository-level `main.py` remains a compatibility entry point and may
continue importing public models, schemas, services, and endpoint functions
from those stable package paths.

The internal paths `app.miniapp_screens`, `app.miniapp_entity_details`,
`app.document_parsers`, `app.feasibility_reports`, `app.connectors`,
`app.cache`, `app.market_dossier`, and `app.responses` are replaced by their
new canonical package paths. Repository tests and internal imports must use
the new paths; no empty compatibility files are retained for them.

## Dependency Direction

Dependencies must follow this direction:

```text
main
  -> routes
     -> services / miniapp / documents / integrations
        -> models / schemas / database
           -> config

infrastructure / datasets / core
  -> config or no app dependency
```

Additional rules:

- Route modules may not import other route modules.
- Route modules own HTTP parsing, authentication context, transaction
  boundaries, and response conversion, but not external-provider algorithms.
- Service modules may not import `app.routes`.
- Model modules may import `Base` from `app.database` but may not import
  schemas, services, routes, or other model modules.
- Cross-model foreign keys continue to use table-name strings. SQLAlchemy
  relationships continue to use class-name strings.
- `app.models.__init__` imports every model before database initialization so
  `Base.metadata` contains the complete schema.
- `app.schemas.__init__` and `app.services.__init__` expose stable public names;
  internal code imports focused submodules where practical.

## Route Composition

Each file under `app/routes/` owns one `APIRouter`. `app/routes/__init__.py`
creates the aggregate router and includes every subrouter exactly once.

It also re-exports endpoint functions currently imported by the repository
root `main.py`. This is compatibility for existing Python callers, not a
reason for route modules to communicate through the aggregate package.

The refactor must capture the pre-migration `(HTTP method, path)` set and assert
that the post-migration set is identical. Duplicate registrations are failures
even if FastAPI starts successfully.

## Service and Integration Extraction

Logic currently embedded in `routes.py` moves according to ownership:

- Captcha, password hashing, session tokens, and request context: auth service.
- WeChat code exchange and phone lookup: WeChat integration.
- LLM request parsing, streaming helpers, and output sanitization: LLM
  integration, with generation orchestration remaining in the AI route or a
  focused service.
- MinIO and local report storage: object-storage integration.
- AMap and QWeather calls: connector integration.
- Financial calculations: finance service.
- Serialization: serializer service files grouped by business area if one
  file becomes too large.
- Seed and runtime-column initialization: seeding service.
- Document parsing and DOCX generation: documents package.

Provider clients remain injectable or monkeypatchable in tests at their
canonical module locations.

## Model and Schema Grouping

Models are grouped by ownership while preserving original class objects and
table metadata:

- `commerce.py`: artists, shows, orders, and AI generation records.
- `identity.py`: tenants, groups, users, memberships, settings, privacy,
  invitations, and agent permissions.
- `projects.py`: projects, versions, drafts, decisions, tasks, gates, risks,
  work plans, work events, and snapshots.
- `evidence.py`: facts, assumptions, evidence, uploads, parse jobs, reports,
  and analysis jobs.
- `intelligence.py`: external jobs, data sources, assets, records, quality,
  monitoring, alerts, conversion assumptions, outcomes, and calibration.
- `operations.py`: venues, tours, notifications, actuals, and ticketing
  snapshots.

Schemas follow API ownership rather than mirroring model files. Every existing
schema remains importable from `app.schemas`.

## Miniapp Screen Decomposition

`app.miniapp.screens.registry` owns screen registration, public lookup, and
`build_miniapp_screen`. Screen provider implementations are grouped by user
workflow:

- Discovery and portfolio.
- Project creation, drafts, details, and versions.
- Finance scenarios and calculations.
- Facts, assumptions, evidence, risks, gates, decisions, and reports.
- Tasks and task details.
- Agent planning, chat, changes, and permissions.
- Authentication, account, settings, privacy, and general state screens.

Shared request context, empty states, display formatting, and lookup helpers
live in `common.py`. Feature modules must not import the registry to avoid
cycles. The registry imports providers after shared types are defined.

## Error Handling and Transactions

Existing `HTTPException` status codes and details remain unchanged. The
refactor does not add a global exception wrapper.

Each route preserves its existing commit, rollback, refresh, and idempotency
behavior. Moving a function is not permission to widen a transaction or move
an external network call inside a transaction. Existing response envelopes
continue to use `{"code": 0, "data": ...}` where currently defined.

## Migration Sequence

1. Add structural contract tests for import compatibility, route parity,
   model metadata, and application startup.
2. Move configuration, database, core, infrastructure, datasets, documents,
   and integrations.
3. Split models and schemas while keeping package-level exports stable.
4. Split services and verify initialization, authentication, finance,
   serialization, and seeding behavior.
5. Split miniapp entity details and screen providers.
6. Split routes and assemble the aggregate router.
7. Update repository imports, tests, and README structure documentation.
8. Remove obsolete flat modules and scan for stale imports.

Each stage must leave the backend importable and must run its focused tests
before the next stage.

## Testing

New tests must cover:

- Stable imports from `app.config`, `app.database`, `app.models`,
  `app.schemas`, `app.services`, and `app.routes`.
- Complete SQLAlchemy table registration after importing `app.models`.
- Exact route method/path parity and absence of duplicate registrations.
- Miniapp provider registration and all existing screen/entity contracts.
- Application import through both `app.main:app` and repository `main:app`.

Existing tests may be split into business-focused files, but assertions and
coverage may not be removed. Tests that monkeypatch implementation details
must target the new canonical owner module.

Final verification:

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python -m compileall app
PYTHONPATH=. .venv/bin/python -c "from app.main import app; assert app.openapi()"
git diff --check
```

The final test count must be at least the 130-test baseline, with all tests
passing.

## Documentation

Update the README directory tree and backend development notes. Document the
canonical locations for routes, service logic, integrations, miniapp screen
providers, models, and schemas. Keep the public startup command unchanged.

## Success Criteria

- No substantive implementation module remains flat under `app/`; only
  `__init__.py` and `main.py` remain at the package root.
- The two largest modules, `routes.py` and `miniapp_screens.py`, no longer
  exist as monolithic files.
- Stable import paths and startup commands continue to work.
- API routes, database metadata, miniapp payloads, and externally observable
  behavior are unchanged.
- The full backend suite passes with at least 130 tests.
- No stale imports, duplicate route registrations, circular imports, or
  generated cache files are committed.
