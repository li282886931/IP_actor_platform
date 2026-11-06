from fastapi import APIRouter

from . import ai, auth, decisioning, evidence, finance, health, intelligence, miniapp, projects, reports, shows, users
from .ai import ai_generate, ai_generate_stream
from .auth import issue_auth_captcha, web_login, wechat_login
from .decisioning import (
    accept_task,
    approve_calibration_candidate,
    batch_task_action,
    create_case_outcome,
    create_conversion_assumption,
    create_decision,
    create_gate,
    create_project_work_event,
    create_risk,
    create_task,
    get_project_calibration,
    get_project_work_plan,
    list_case_outcomes,
    list_conversion_assumptions,
    list_decision_snapshots,
    list_gates,
    list_risks,
    list_tasks,
    refresh_project_work_plan,
    submit_task,
)
from .evidence import (
    complete_oss_upload,
    confirm_document_parse_job_projects,
    create_assumption,
    create_data_asset,
    create_data_source,
    create_document_parse_job,
    create_fact,
    health_check_data_source,
    initiate_oss_upload,
    list_assumptions,
    list_data_assets,
    list_data_records,
    list_data_sources,
    list_evidences,
    list_facts,
    resolve_data_quality_issue,
    run_document_parse_job,
    upload_evidence,
    verify_fact,
)
from .finance import finance_breakeven, finance_calculate, finance_show_calculation
from .health import ping
from .intelligence import (
    acknowledge_alert,
    agent_chat,
    create_external_data_job,
    create_monitoring_rule,
    create_project_analysis_job,
    evaluate_monitoring_rule,
    get_external_data_job,
    get_project_analysis_job,
    list_alerts,
    list_external_data_jobs,
    list_monitoring_rules,
    resolve_alert,
    run_external_data_job,
    search_cases,
)
from .miniapp import get_miniapp_entity_detail, get_miniapp_screen, search_miniapp_entities
from .projects import create_project, create_project_version, get_project, list_project_versions, list_projects
from .reports import dashboard_analytics, download_report_file, generate_feasibility_report, share_report, ticketing_summary
from .shows import get_artist, get_show, list_artists, list_shows, order_show, recommend_shows
from .users import create_user, delete_user, list_tenants, list_user_groups, list_users, switch_tenant, update_user

router = APIRouter()
for child_router in (
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
    router.include_router(child_router)
