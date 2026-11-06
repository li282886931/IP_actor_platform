from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas import MiniappScreenData

from .account import _account_screen, _auth_screen, _settings_screen, _state_screen
from .agent import _agent_chat_screen, _agent_dashboard_screen, _agent_permissions_screen, _agent_plan_screen, _project_changes_screen
from .common import ScreenRegistration, ScreenRequestContext
from .decisioning import (_assumption_screen, _decision_confirm_screen, _decision_result_screen, _document_parse_screen, _evidence_gap_screen, _evidence_screen, _evidence_upload_screen, _fact_screen, _gate_screen, _judgement_screen, _report_preview_screen, _report_share_screen, _risk_screen, _version_compare_screen)
from .discovery import _discovery_dashboard_screen, _discovery_screen, _portfolio_screen
from .finance import (FINANCE_SCENARIOS, _breakeven_screen, _cost_breakdown_screen, _finance_input_screen, _finance_scenario_screen, _finance_sensitivity_screen, _funding_gap_screen, _ticket_tiers_screen)
from .operations import _project_review_screen, _tour_screen
from .projects import (PROJECT_CREATE_TITLES, _project_create_screen, _project_detail_screen, _project_draft_screen, _project_list_screen, _project_versions_screen)
from .tasks import _task_detail_screen, _task_list_screen


def _registration(
    screen_id: str,
    provider_key: str,
    domain: str,
    *required_context: str,
) -> ScreenRegistration:
    return ScreenRegistration(
        screen_id=screen_id,
        provider_key=provider_key,
        domain=domain,
        required_context=frozenset(required_context),
    )


_REGISTRATIONS = [
    _registration('S01', 'auth_login', 'auth'),
    _registration('S02', 'tenant_select', 'auth', 'user_id'),
    _registration('S03', 'privacy_scope', 'auth', 'tenant_id', 'user_id'),
    _registration('S04', 'discovery_public', 'discovery'),
    _registration('S05', 'discovery_dashboard', 'discovery', 'tenant_id', 'user_id'),
    _registration('S06', 'case_list', 'discovery'),
    _registration('S07', 'case_detail', 'discovery'),
    _registration('S08', 'opportunity_detail', 'discovery'),
    _registration('S09', 'discovery_search', 'discovery'),
    _registration('S10', 'project_list', 'project', 'tenant_id'),
    _registration('S11', 'project_detail', 'project', 'tenant_id', 'project_id'),
    _registration('S12', 'project_versions', 'project', 'tenant_id', 'project_id'),
    _registration('S13', 'project_create_basic', 'project', 'tenant_id', 'user_id'),
    _registration('S14', 'project_create_schedule', 'project', 'tenant_id', 'user_id'),
    _registration('S15', 'project_create_scale', 'project', 'tenant_id', 'user_id'),
    _registration('S16', 'project_create_costs', 'project', 'tenant_id', 'user_id'),
    _registration('S17', 'project_create_review', 'project', 'tenant_id', 'user_id'),
    _registration('S18', 'project_draft', 'project', 'tenant_id', 'user_id'),
    _registration('S19', 'artist_candidates', 'portfolio', 'tenant_id'),
    _registration('S20', 'artist_detail', 'portfolio', 'artist_id'),
    _registration('S21', 'artist_compare', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S22', 'city_compare', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S23', 'schedule_options', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S24', 'venue_options', 'portfolio', 'tenant_id', 'project_id'),
    _registration('S25', 'finance_input', 'finance', 'tenant_id', 'project_id'),
    _registration('S26', 'ticket_tiers', 'finance', 'tenant_id', 'project_id'),
    _registration('S27', 'cost_breakdown', 'finance', 'tenant_id', 'project_id'),
    _registration('S28', 'finance_conservative', 'finance', 'tenant_id', 'project_id'),
    _registration('S29', 'finance_neutral', 'finance', 'tenant_id', 'project_id'),
    _registration('S30', 'finance_optimistic', 'finance', 'tenant_id', 'project_id'),
    _registration('S31', 'finance_breakeven', 'finance', 'tenant_id', 'project_id'),
    _registration('S32', 'finance_sensitivity', 'finance', 'tenant_id', 'project_id'),
    _registration('S33', 'finance_funding_gap', 'finance', 'tenant_id', 'project_id'),
    _registration('S34', 'judgement_summary', 'decision', 'tenant_id', 'project_id'),
    _registration('S35', 'judgement_explanation', 'decision', 'tenant_id', 'project_id'),
    _registration('S36', 'assumption_list', 'evidence', 'tenant_id', 'project_id'),
    _registration('S37', 'fact_list', 'evidence', 'tenant_id', 'project_id'),
    _registration('S38', 'evidence_detail', 'evidence', 'tenant_id', 'project_id'),
    _registration('S39', 'evidence_conflicts', 'evidence', 'tenant_id', 'project_id'),
    _registration('S40', 'evidence_gaps', 'evidence', 'tenant_id', 'project_id'),
    _registration('S41', 'evidence_upload_context', 'evidence', 'tenant_id', 'project_id'),
    _registration('S42', 'document_parse_review', 'evidence', 'tenant_id', 'project_id'),
    _registration('S43', 'risk_list', 'risk', 'tenant_id', 'project_id'),
    _registration('S44', 'risk_detail', 'risk', 'tenant_id', 'project_id'),
    _registration('S45', 'gate_list', 'gate', 'tenant_id', 'project_id'),
    _registration('S46', 'gate_detail', 'gate', 'tenant_id', 'project_id'),
    _registration('S47', 'decision_confirm', 'decision', 'tenant_id', 'project_id', 'version_id'),
    _registration('S48', 'decision_result', 'decision', 'tenant_id', 'project_id'),
    _registration('S49', 'version_compare', 'version', 'tenant_id', 'project_id'),
    _registration('S50', 'report_preview', 'report', 'tenant_id', 'project_id'),
    _registration('S51', 'report_share', 'report', 'tenant_id', 'project_id'),
    _registration('S52', 'agent_dashboard', 'agent', 'tenant_id', 'user_id'),
    _registration('S53', 'agent_plan', 'agent', 'tenant_id', 'project_id'),
    _registration('S54', 'agent_chat', 'agent', 'tenant_id', 'project_id'),
    _registration('S55', 'task_list', 'task', 'tenant_id'),
    _registration('S56', 'task_batch', 'task', 'tenant_id'),
    _registration('S57', 'task_submit', 'task', 'tenant_id', 'task_id'),
    _registration('S58', 'task_block', 'task', 'tenant_id', 'task_id'),
    _registration('S59', 'project_changes', 'agent', 'tenant_id', 'project_id'),
    _registration('S60', 'agent_permissions', 'agent', 'tenant_id', 'user_id'),
    _registration('S61', 'tour_overview', 'tour', 'tenant_id'),
    _registration('S62', 'tour_route', 'tour', 'tenant_id'),
    _registration('S63', 'tour_stop', 'tour', 'tenant_id', 'project_id'),
    _registration('S64', 'ticketing_progress', 'review', 'tenant_id', 'project_id'),
    _registration('S65', 'project_actuals', 'review', 'tenant_id', 'project_id'),
    _registration('S66', 'project_review', 'review', 'tenant_id', 'project_id'),
    _registration('S67', 'account_home', 'account', 'tenant_id', 'user_id'),
    _registration('S68', 'team_members', 'account', 'tenant_id'),
    _registration('S69', 'notifications', 'account', 'tenant_id', 'user_id'),
    _registration('S70', 'user_settings', 'account', 'tenant_id', 'user_id'),
    _registration('S71', 'data_permissions', 'account', 'tenant_id', 'user_id'),
    _registration('S72', 'member_invite', 'account', 'tenant_id', 'user_id'),
    _registration('S73', 'project_empty', 'state', 'tenant_id'),
    _registration('S74', 'analysis_processing', 'state', 'tenant_id', 'project_id'),
    _registration('S75', 'network_failure', 'state', 'user_id'),
    _registration('S76', 'context_unavailable', 'state', 'user_id'),
    _registration('S77', 'permission_denied', 'state', 'user_id'),
    _registration('S78', 'version_changed', 'state', 'tenant_id', 'project_id', 'version_id'),
    _registration('S79', 'validation_error', 'state', 'user_id'),
    _registration('S80', 'archive_confirmation', 'state', 'tenant_id', 'project_id'),
    _registration('S81', 'auth_expired', 'state', 'user_id'),
    _registration('S82', 'developer_connection', 'settings', 'user_id'),
    _registration('S83', 'notification_preferences', 'settings', 'tenant_id', 'user_id'),
    _registration('S84', 'privacy_records', 'settings', 'tenant_id', 'user_id'),
]


SCREEN_PROVIDERS = {
    registration.screen_id: registration
    for registration in _REGISTRATIONS
}


def build_miniapp_screen(
    screen_id: str,
    context: ScreenRequestContext,
    db: Optional[Session] = None,
) -> MiniappScreenData:
    registration = SCREEN_PROVIDERS.get(screen_id)
    if not registration:
        raise HTTPException(status_code=400, detail='Unknown miniapp screen')

    missing_context = [
        name
        for name in registration.required_context
        if getattr(context, name) is None
    ]
    if missing_context:
        raise HTTPException(
            status_code=422,
            detail=f"Missing screen context: {', '.join(sorted(missing_context))}",
        )

    if registration.provider_key in {"auth_login", "tenant_select", "privacy_scope"}:
        if db is None:
            raise RuntimeError('Database session is required for authentication screens')
        return MiniappScreenData.model_validate(_auth_screen(db, context, screen_id))
    if registration.provider_key in {
        "account_home",
        "team_members",
        "notifications",
        "user_settings",
        "data_permissions",
        "member_invite",
    }:
        if db is None:
            raise RuntimeError('Database session is required for account screens')
        return MiniappScreenData.model_validate(_account_screen(db, context, screen_id))
    if registration.provider_key in {
        "developer_connection",
        "notification_preferences",
        "privacy_records",
    }:
        if db is None:
            raise RuntimeError('Database session is required for settings screens')
        return MiniappScreenData.model_validate(_settings_screen(db, context, screen_id))
    if registration.domain == "state":
        if db is None:
            raise RuntimeError('Database session is required for state screens')
        return MiniappScreenData.model_validate(_state_screen(db, context, screen_id))
    if registration.provider_key in {
        "discovery_public",
        "case_list",
        "case_detail",
        "opportunity_detail",
        "discovery_search",
    }:
        if db is None:
            raise RuntimeError('Database session is required for discovery screens')
        return MiniappScreenData.model_validate(_discovery_screen(db, context, screen_id))
    if registration.provider_key == "discovery_dashboard":
        if db is None:
            raise RuntimeError('Database session is required for discovery screens')
        return MiniappScreenData.model_validate(_discovery_dashboard_screen(db, context))
    if registration.provider_key in {
        "artist_candidates",
        "artist_detail",
        "artist_compare",
        "city_compare",
        "schedule_options",
        "venue_options",
    }:
        if db is None:
            raise RuntimeError('Database session is required for portfolio screens')
        return MiniappScreenData.model_validate(_portfolio_screen(db, context, screen_id))
    if registration.provider_key in {"tour_overview", "tour_route", "tour_stop"}:
        if db is None:
            raise RuntimeError('Database session is required for tour screens')
        return MiniappScreenData.model_validate(_tour_screen(db, context, screen_id))
    if registration.provider_key in {"ticketing_progress", "project_actuals", "project_review"}:
        if db is None:
            raise RuntimeError('Database session is required for review screens')
        return MiniappScreenData.model_validate(_project_review_screen(db, context, screen_id))
    if registration.provider_key == 'project_list':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_list_screen(db, context))
    if registration.provider_key == 'project_detail':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_detail_screen(db, context))
    if registration.provider_key == 'project_versions':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_versions_screen(db, context))
    if registration.provider_key in PROJECT_CREATE_TITLES:
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_create_screen(
            db,
            context,
            registration.provider_key,
            screen_id,
        ))
    if registration.provider_key == 'project_draft':
        if db is None:
            raise RuntimeError('Database session is required for project screens')
        return MiniappScreenData.model_validate(_project_draft_screen(db, context))
    if registration.provider_key == 'finance_input':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_finance_input_screen(db, context))
    if registration.provider_key == 'ticket_tiers':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_ticket_tiers_screen(db, context))
    if registration.provider_key == 'cost_breakdown':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_cost_breakdown_screen(db, context))
    if registration.provider_key == 'finance_breakeven':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_breakeven_screen(db, context))
    if registration.provider_key == 'finance_funding_gap':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_funding_gap_screen(db, context))
    if registration.provider_key == 'finance_sensitivity':
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_finance_sensitivity_screen(db, context))
    if registration.provider_key in FINANCE_SCENARIOS:
        if db is None:
            raise RuntimeError('Database session is required for finance screens')
        return MiniappScreenData.model_validate(_finance_scenario_screen(
            db,
            context,
            registration.provider_key,
        ))
    if registration.provider_key in {"judgement_summary", "judgement_explanation"}:
        if db is None:
            raise RuntimeError('Database session is required for decision screens')
        return MiniappScreenData.model_validate(_judgement_screen(db, context, screen_id))
    if registration.provider_key == "assumption_list":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_assumption_screen(db, context))
    if registration.provider_key == "fact_list":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_fact_screen(db, context))
    if registration.provider_key == "evidence_detail":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_screen(db, context))
    if registration.provider_key == "evidence_conflicts":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_screen(
            db,
            context,
            conflicts_only=True,
        ))
    if registration.provider_key == "evidence_gaps":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_gap_screen(db, context))
    if registration.provider_key == "evidence_upload_context":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_evidence_upload_screen(db, context))
    if registration.provider_key == "document_parse_review":
        if db is None:
            raise RuntimeError('Database session is required for evidence screens')
        return MiniappScreenData.model_validate(_document_parse_screen(db, context))
    if registration.provider_key in {"risk_list", "risk_detail"}:
        if db is None:
            raise RuntimeError('Database session is required for risk screens')
        return MiniappScreenData.model_validate(_risk_screen(db, context, screen_id))
    if registration.provider_key in {"gate_list", "gate_detail"}:
        if db is None:
            raise RuntimeError('Database session is required for gate screens')
        return MiniappScreenData.model_validate(_gate_screen(db, context, screen_id))
    if registration.provider_key == "decision_confirm":
        if db is None:
            raise RuntimeError('Database session is required for decision screens')
        return MiniappScreenData.model_validate(_decision_confirm_screen(db, context))
    if registration.provider_key == "decision_result":
        if db is None:
            raise RuntimeError('Database session is required for decision screens')
        return MiniappScreenData.model_validate(_decision_result_screen(db, context))
    if registration.provider_key == "version_compare":
        if db is None:
            raise RuntimeError('Database session is required for version screens')
        return MiniappScreenData.model_validate(_version_compare_screen(db, context))
    if registration.provider_key == "report_preview":
        if db is None:
            raise RuntimeError('Database session is required for report screens')
        return MiniappScreenData.model_validate(_report_preview_screen(db, context))
    if registration.provider_key == "report_share":
        if db is None:
            raise RuntimeError('Database session is required for report screens')
        return MiniappScreenData.model_validate(_report_share_screen(db, context))
    if registration.provider_key in {"task_list", "task_batch"}:
        if db is None:
            raise RuntimeError('Database session is required for task screens')
        return MiniappScreenData.model_validate(_task_list_screen(db, context, screen_id))
    if registration.provider_key in {"task_submit", "task_block"}:
        if db is None:
            raise RuntimeError('Database session is required for task screens')
        return MiniappScreenData.model_validate(_task_detail_screen(db, context, screen_id))
    if registration.provider_key == "agent_dashboard":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_dashboard_screen(db, context))
    if registration.provider_key == "agent_plan":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_plan_screen(db, context))
    if registration.provider_key == "agent_chat":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_chat_screen(db, context))
    if registration.provider_key == "project_changes":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_project_changes_screen(db, context))
    if registration.provider_key == "agent_permissions":
        if db is None:
            raise RuntimeError('Database session is required for agent screens')
        return MiniappScreenData.model_validate(_agent_permissions_screen(db, context))

    raise RuntimeError(
        f"Unhandled miniapp screen provider: {registration.provider_key}",
    )
