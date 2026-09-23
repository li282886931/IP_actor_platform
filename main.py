from app.database import SQLALCHEMY_DATABASE_URL, Base, SessionLocal, create_engine_kwargs, engine, get_db, resolve_database_url
from app.main import app
from app.models import (
    AIGeneration,
    Artist,
    Decision,
    Order,
    Project,
    ProjectVersion,
    Show,
    Task,
    Tenant,
    TenantMember,
    User,
    UserGroup,
)
from app.routes import (
    ai_generate,
    create_decision,
    create_project,
    create_project_version,
    create_task,
    finance_calculate,
    get_artist,
    get_project,
    get_show,
    list_artists,
    list_project_versions,
    list_projects,
    list_shows,
    list_tasks,
    list_tenants,
    order_show,
    ping,
    switch_tenant,
    web_login,
)
from app.schemas import AIGenerateIn, ArtistOut, DecisionIn, FinanceCalculateIn, OrderIn, ProjectIn, ShowOut, TaskIn, WebLoginIn
from app.services import (
    calculate_finance_result,
    get_default_tenant_id,
    get_or_create_default_context,
    init_db,
    project_input_snapshot,
    seed_initial_data,
    serialize_project,
    serialize_task,
    serialize_version,
)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False)
