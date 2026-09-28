# Miniapp Screen API Matrix

All screens read through `GET /miniapp/screens/{screen_id}`. Write operations remain separate domain APIs. `401`, `403`, `409`, and `422` are handled by the shared client; `404` is returned for missing or cross-tenant entities.

| Screen | Provider | Required context | Read entities | Write API | Empty state | Error state | Tests |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | `auth_login` | none | login capabilities | `/auth/wechat-login` | not applicable | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S02 | `tenant_select` | user | TenantMember, Tenant | `/tenants/switch` | no joined tenant | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S03 | `privacy_scope` | tenant, user | PrivacyConsent | privacy domain API | no consent | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S04 | `discovery_public` | none | Show | none | no show | shared network | `test_discovery_screens_use_real_shows_and_empty_business_sources` |
| S05 | `discovery_dashboard` | tenant, user | Project | none | no project | shared auth/network | `test_project_list_screen_returns_empty_state_without_fabricated_items` |
| S06 | `case_list` | none | completed Show | none | no real case | shared network | `test_discovery_screens_use_real_shows_and_empty_business_sources` |
| S07 | `case_detail` | none | completed Show | none | no real case | shared network | `test_discovery_screens_use_real_shows_and_empty_business_sources` |
| S08 | `opportunity_detail` | none | opportunity Show | none | no real opportunity | shared network | `test_discovery_screens_use_real_shows_and_empty_business_sources` |
| S09 | `discovery_search` | none, keyword optional | Show | none | no matching show | shared network | `test_discovery_screens_use_real_shows_and_empty_business_sources` |
| S10 | `project_list` | tenant | Project | none | no project | shared auth/network | `test_project_list_screen_returns_only_current_tenant_projects_and_active_count` |
| S11 | `project_detail` | tenant, project | Project, ProjectVersion | project APIs | not applicable | 404 / shared | `test_project_detail_uses_requested_project_and_rejects_cross_tenant_access` |
| S12 | `project_versions` | tenant, project | ProjectVersion | project APIs | no version | 404 / shared | `test_project_version_screen_orders_versions_and_marks_current` |
| S13 | `project_create_basic` | tenant, user | Project, Artist, Show | project draft API | no draft allowed | shared auth/network | `test_project_creation_screens_return_saved_draft_and_real_options` |
| S14 | `project_create_schedule` | tenant, user | Project, Artist, Show | project draft API | no draft allowed | shared auth/network | `test_project_creation_screens_return_saved_draft_and_real_options` |
| S15 | `project_create_scale` | tenant, user | Project, Artist, Show | project draft API | no draft allowed | shared auth/network | `test_project_creation_screens_return_saved_draft_and_real_options` |
| S16 | `project_create_costs` | tenant, user | Project, Artist, Show | project draft API | no draft allowed | shared auth/network | `test_project_creation_screens_return_saved_draft_and_real_options` |
| S17 | `project_create_review` | tenant, user | Project, Artist, Show | `POST /projects` | no draft allowed | shared auth/network | `test_project_creation_persists_selected_entity_ids` |
| S18 | `project_draft` | tenant, user | Project | project draft API | no draft | shared auth/network | `test_project_draft_screen_is_scoped_to_current_user_and_tenant` |
| S19 | `artist_candidates` | tenant | Project, Artist | none | no candidate | shared auth/network | `test_artist_candidate_and_detail_screens_return_real_artist_fields` |
| S20 | `artist_detail` | artist | Artist | project API | not applicable | 404 / shared | `test_artist_candidate_and_detail_screens_return_real_artist_fields` |
| S21 | `artist_compare` | tenant, project | Project, Artist | project API | no artist | 404 / shared | `test_artist_candidate_and_detail_screens_return_real_artist_fields` |
| S22 | `city_compare` | tenant, project | Project, Venue | project API | no city | 404 / shared | `test_city_and_venue_screens_are_tenant_scoped_and_show_verified_fields` |
| S23 | `schedule_options` | tenant, project | Project | project API | no schedule | 404 / shared | `test_city_and_venue_screens_are_tenant_scoped_and_show_verified_fields` |
| S24 | `venue_options` | tenant, project | Project, Venue | project API | no venue | 404 / shared | `test_city_and_venue_screens_are_tenant_scoped_and_show_verified_fields` |
| S25 | `finance_input` | tenant, project | Project, ProjectVersion | `/finance/calculate` | missing inputs | 404 / shared | `test_finance_input_screen_returns_saved_inputs_and_missing_fields` |
| S26 | `ticket_tiers` | tenant, project | Project | project API | no ticket tiers | 404 / shared | `test_ticket_tiers_screen_uses_saved_tiers_without_defaults` |
| S27 | `cost_breakdown` | tenant, project | Project, ProjectVersion | project API | missing costs | 404 / shared | `test_cost_breakdown_screen_uses_saved_costs` |
| S28 | `finance_conservative` | tenant, project | ProjectVersion | none | missing scenario | 404 / shared | `test_finance_scenario_screens_use_saved_version_results` |
| S29 | `finance_neutral` | tenant, project | ProjectVersion | none | missing scenario | 404 / shared | `test_finance_scenario_screens_use_saved_version_results` |
| S30 | `finance_optimistic` | tenant, project | ProjectVersion | none | missing scenario | 404 / shared | `test_finance_scenario_screens_use_saved_version_results` |
| S31 | `finance_breakeven` | tenant, project | Project | `/finance/breakeven` | missing inputs | 404 / shared | `test_breakeven_screen_uses_real_project_parameters` |
| S32 | `finance_sensitivity` | tenant, project | Project, ProjectVersion | none | missing scenario | 404 / shared | `test_finance_sensitivity_recalculates_only_occupancy` |
| S33 | `finance_funding_gap` | tenant, project | Project | none | missing inputs | 404 / shared | `test_funding_gap_screen_uses_available_funds` |
| S34 | `judgement_summary` | tenant, project | ProjectVersion, Gate, Risk, Decision | none | no decision data | 404 / shared | `test_judgement_screens_aggregate_current_version_gates_risks_and_decision` |
| S35 | `judgement_explanation` | tenant, project | ProjectVersion, Gate, Risk, Decision | none | no decision data | 404 / shared | `test_judgement_screens_aggregate_current_version_gates_risks_and_decision` |
| S36 | `assumption_list` | tenant, project | Assumption | assumption API | no assumption | 404 / shared | `test_evidence_domain_screens_return_real_records_and_context` |
| S37 | `fact_list` | tenant, project | Fact | fact API | no fact | 404 / shared | `test_evidence_domain_screens_return_real_records_and_context` |
| S38 | `evidence_detail` | tenant, project | Evidence | evidence API | no evidence | 404 / shared | `test_evidence_domain_screens_return_real_records_and_context` |
| S39 | `evidence_conflicts` | tenant, project | Evidence | evidence API | no conflict | 404 / shared | `test_evidence_conflict_screen_only_returns_conflicts` |
| S40 | `evidence_gaps` | tenant, project | Gate, Evidence | evidence API | no gap | 404 / shared | `test_evidence_gap_and_upload_screens_use_real_project_state` |
| S41 | `evidence_upload_context` | tenant, project | Project, Evidence | evidence upload APIs | no evidence allowed | 404 / shared | `test_evidence_gap_and_upload_screens_use_real_project_state` |
| S42 | `document_parse_review` | tenant, project | DocumentParseJob | parse job APIs | no parse job | 404 / shared | `test_document_parse_screen_uses_latest_real_job` |
| S43 | `risk_list` | tenant, project | Risk | risk API | no risk | 404 / shared | `test_risk_and_gate_screens_sort_real_records` |
| S44 | `risk_detail` | tenant, project | Risk | risk API | no risk | 404 / shared | `test_risk_and_gate_screens_sort_real_records` |
| S45 | `gate_list` | tenant, project | Gate | gate API | no gate | 404 / shared | `test_risk_and_gate_screens_sort_real_records` |
| S46 | `gate_detail` | tenant, project | Gate | gate API | no gate | 404 / shared | `test_risk_and_gate_screens_sort_real_records` |
| S47 | `decision_confirm` | tenant, project, version | Decision, User | decision API | no prior decision allowed | 404 / shared | `test_decision_screens_use_named_owner_and_real_latest_decision` |
| S48 | `decision_result` | tenant, project | Decision, User | none | no decision | 404 / shared | `test_decision_screens_use_named_owner_and_real_latest_decision` |
| S49 | `version_compare` | tenant, project | ProjectVersion | project API | fewer than two versions | 404 / shared | `test_version_compare_screen_uses_two_latest_real_versions` |
| S50 | `report_preview` | tenant, project | Evidence, Fact, Risk, Gate, Decision | report API | no report evidence | 404 / shared | `test_report_screens_use_real_evidence_and_active_shares` |
| S51 | `report_share` | tenant, project | ReportShare | report share API | no active share | 404 / shared | `test_report_screens_use_real_evidence_and_active_shares` |
| S52 | `agent_dashboard` | tenant, user | Task, Project | none | no assigned task | shared auth/network | `test_agent_screens_aggregate_current_user_tasks_and_analysis_jobs` |
| S53 | `agent_plan` | tenant, project | Task, ProjectAnalysisJob | task API | no plan item | 404 / shared | `test_agent_screens_aggregate_current_user_tasks_and_analysis_jobs` |
| S54 | `agent_chat` | tenant, project | ProjectAnalysisJob | agent APIs | no analysis | 404 / shared | `test_agent_screens_aggregate_current_user_tasks_and_analysis_jobs` |
| S55 | `task_list` | tenant | Task, Project, User | task APIs | no task | shared auth/network | `test_task_list_screens_are_tenant_scoped_and_include_project_details` |
| S56 | `task_batch` | tenant | Task, Project, User | `/tasks/actions/batch` | no actionable task | shared auth/network | `test_task_list_screens_are_tenant_scoped_and_include_project_details` |
| S57 | `task_submit` | tenant, task | Task, Project, User | task submit API | not applicable | 404 / shared | `test_task_detail_screens_require_tenant_owned_task` |
| S58 | `task_block` | tenant, task | Task, Project, User | task block API | not applicable | 404 / shared | `test_task_detail_screens_require_tenant_owned_task` |
| S59 | `project_changes` | tenant, project | ProjectVersion | none | no changes | 404 / shared | `test_agent_change_screen_only_reports_real_version_changes` |
| S60 | `agent_permissions` | tenant, user | AgentPermission | agent permission API | no permission | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S61 | `tour_overview` | tenant | TourPlan, TourStop | tour API | no tour | shared auth/network | `test_tour_and_review_screens_use_ordered_stops_latest_snapshot_and_actuals` |
| S62 | `tour_route` | tenant | TourPlan, TourStop | tour API | no stop | shared auth/network | `test_tour_and_review_screens_use_ordered_stops_latest_snapshot_and_actuals` |
| S63 | `tour_stop` | tenant, project | TourPlan, TourStop, Project | project API | no project stop | 404 / shared | `test_tour_and_review_screens_use_ordered_stops_latest_snapshot_and_actuals` |
| S64 | `ticketing_progress` | tenant, project | TicketingSnapshot | ticketing API | no snapshot | 404 / shared | `test_tour_and_review_screens_use_ordered_stops_latest_snapshot_and_actuals` |
| S65 | `project_actuals` | tenant, project | ProjectActual | actuals API | no actuals | 404 / shared | `test_tour_and_review_screens_use_ordered_stops_latest_snapshot_and_actuals` |
| S66 | `project_review` | tenant, project | ProjectActual, ProjectVersion | review API | no comparable actuals | 404 / shared | `test_project_review_does_not_invent_variance_without_actuals` |
| S67 | `account_home` | tenant, user | User, Notification | none | not applicable | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S68 | `team_members` | tenant | TenantMember, User | member API | no member | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S69 | `notifications` | tenant, user | Notification | notification API | no notification | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S70 | `user_settings` | tenant, user | UserSetting | setting API | no setting | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S71 | `data_permissions` | tenant, user | PrivacyConsent, AgentPermission | permission APIs | no permission | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S72 | `member_invite` | tenant, user | MemberInvitation | invitation API | no invitation | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S73 | `project_empty` | tenant | Project | none | no project | shared auth/network | `test_project_empty_state_only_applies_when_current_tenant_has_no_projects` |
| S74 | `analysis_processing` | tenant, project | Project, ProjectAnalysisJob | analysis API | no analysis job | 404 / shared | `test_processing_version_and_archive_states_validate_real_project_context` |
| S75 | `network_failure` | user | state metadata | retry read | not applicable | shared auth/network | `test_recoverable_state_screens_have_explicit_targets_without_business_items` |
| S76 | `context_unavailable` | user | state metadata | none | not applicable | shared auth/network | `test_recoverable_state_screens_have_explicit_targets_without_business_items` |
| S77 | `permission_denied` | user | state metadata | none | not applicable | shared auth/network | `test_recoverable_state_screens_have_explicit_targets_without_business_items` |
| S78 | `version_changed` | tenant, project, version | Project, ProjectVersion | none | not applicable | 404 / shared | `test_processing_version_and_archive_states_validate_real_project_context` |
| S79 | `validation_error` | user | state metadata | retry write | not applicable | shared auth/network | `test_recoverable_state_screens_have_explicit_targets_without_business_items` |
| S80 | `archive_confirmation` | tenant, project | Project | archive project API | not applicable | 404 / shared | `test_processing_version_and_archive_states_validate_real_project_context` |
| S81 | `auth_expired` | user | state metadata | `/auth/wechat-login` | not applicable | shared auth/network | `test_recoverable_state_screens_have_explicit_targets_without_business_items` |
| S82 | `developer_connection` | user | environment status | save local API base | not applicable | shared auth/network | `test_developer_connection_screen_exposes_status_without_secret_values` |
| S83 | `notification_preferences` | tenant, user | UserSetting | setting API | no preferences | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
| S84 | `privacy_records` | tenant, user | PrivacyConsent | privacy domain API | no privacy record | shared auth/network | `test_account_collaboration_and_privacy_screens_read_scoped_saved_state` |
