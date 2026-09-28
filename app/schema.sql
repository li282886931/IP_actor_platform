-- Ruiyinchang backend schema generated from app.models SQLAlchemy metadata.
-- Target dialect: MySQL 8 / InnoDB / utf8mb4.
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE ai_generations (
	id INTEGER NOT NULL AUTO_INCREMENT,
	type VARCHAR(64) NOT NULL,
	prompt TEXT NOT NULL,
	result TEXT NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_ai_generations_id ON ai_generations (id);

CREATE TABLE artists (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255),
	tags VARCHAR(255),
	heat_score INTEGER,
	fan_count VARCHAR(64),
	risk_level INTEGER,
	profile JSON,
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_artists_name ON artists (name);
CREATE INDEX ix_artists_id ON artists (id);

CREATE TABLE tenants (
	id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(255) NOT NULL,
	status VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_tenants_id ON tenants (id);

CREATE TABLE shows (
	id INTEGER NOT NULL AUTO_INCREMENT,
	title VARCHAR(255),
	artist_id INTEGER,
	artist_name VARCHAR(255),
	city VARCHAR(128),
	date VARCHAR(64),
	venue VARCHAR(255),
	price VARCHAR(64),
	status VARCHAR(64),
	description TEXT,
	poster_url TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(artist_id) REFERENCES artists (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_shows_title ON shows (title);
CREATE INDEX ix_shows_id ON shows (id);

CREATE TABLE user_groups (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	description TEXT,
	permission_set JSON,
	data_scope VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_user_groups_id ON user_groups (id);

CREATE TABLE orders (
	id INTEGER NOT NULL AUTO_INCREMENT,
	show_id INTEGER,
	name VARCHAR(255),
	phone VARCHAR(64),
	PRIMARY KEY (id),
	FOREIGN KEY(show_id) REFERENCES shows (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_orders_id ON orders (id);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT,
	openid VARCHAR(128),
	unionid VARCHAR(128),
	account VARCHAR(255),
	name VARCHAR(255) NOT NULL,
	password_hash VARCHAR(128),
	phone VARCHAR(64),
	group_id INTEGER,
	group_code VARCHAR(64),
	status VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE (openid),
	UNIQUE (unionid),
	UNIQUE (account),
	FOREIGN KEY(group_id) REFERENCES user_groups (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_users_id ON users (id);

CREATE TABLE projects (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	type VARCHAR(64),
	status VARCHAR(64),
	artist_id INTEGER,
	artist_name VARCHAR(255),
	city VARCHAR(128),
	venue_id INTEGER,
	venue VARCHAR(255),
	source_project_id INTEGER,
	schedule VARCHAR(64),
	expected_attendance INTEGER,
	avg_ticket_price INTEGER,
	artist_fee INTEGER,
	venue_cost INTEGER,
	marketing_cost INTEGER,
	production_cost INTEGER,
	available_funds INTEGER,
	venue_capacity INTEGER,
	ticket_tiers JSON,
	conservative_occupancy_rate INTEGER,
	neutral_occupancy_rate INTEGER,
	optimistic_occupancy_rate INTEGER,
	current_version_id INTEGER,
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(artist_id) REFERENCES artists (id),
	FOREIGN KEY(venue_id) REFERENCES venues (id),
	FOREIGN KEY(source_project_id) REFERENCES projects (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_projects_id ON projects (id);

CREATE TABLE tenant_members (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	`role` VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_tenant_members_id ON tenant_members (id);

CREATE TABLE assumptions (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	title VARCHAR(255) NOT NULL,
	content TEXT,
	confidence INTEGER,
	status VARCHAR(64),
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_assumptions_id ON assumptions (id);

CREATE TABLE external_data_jobs (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	project_id INTEGER,
	source_type VARCHAR(64) NOT NULL,
	provider VARCHAR(64),
	query TEXT NOT NULL,
	purpose VARCHAR(128),
	status VARCHAR(64),
	parameters JSON,
	result JSON,
	error_message TEXT,
	requested_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	started_at DATETIME,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(requested_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_external_data_jobs_id ON external_data_jobs (id);

CREATE TABLE facts (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	title VARCHAR(255) NOT NULL,
	content TEXT,
	source VARCHAR(128),
	status VARCHAR(64),
	verified_by INTEGER,
	verified_comment TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	verified_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(verified_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_facts_id ON facts (id);

CREATE TABLE gates (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	status VARCHAR(64),
	required_evidence TEXT,
	owner_group VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_gates_id ON gates (id);

CREATE TABLE project_versions (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	version_no INTEGER NOT NULL,
	input_snapshot JSON NOT NULL,
	finance_result JSON,
	status VARCHAR(64),
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_project_versions_id ON project_versions (id);

CREATE TABLE risks (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	title VARCHAR(255) NOT NULL,
	level VARCHAR(64),
	mitigation TEXT,
	status VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_risks_id ON risks (id);

CREATE TABLE tasks (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	assignee_id INTEGER,
	title VARCHAR(255) NOT NULL,
	description TEXT,
	due_date VARCHAR(64),
	status VARCHAR(64),
	result TEXT,
	evidence_ids JSON,
	rejection_reason TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(assignee_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_tasks_id ON tasks (id);

CREATE TABLE decisions (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	version_id INTEGER NOT NULL,
	decision_type VARCHAR(64) NOT NULL,
	conditions TEXT,
	decided_by INTEGER,
	decided_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(version_id) REFERENCES project_versions (id),
	FOREIGN KEY(decided_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_decisions_id ON decisions (id);

CREATE TABLE evidences (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	fact_id INTEGER,
	name VARCHAR(255) NOT NULL,
	file_url TEXT NOT NULL,
	evidence_type VARCHAR(64),
	source VARCHAR(128),
	status VARCHAR(64),
	meta JSON,
	uploaded_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(fact_id) REFERENCES facts (id),
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_evidences_id ON evidences (id);

CREATE TABLE oss_uploads (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	fact_id INTEGER,
	provider VARCHAR(64),
	bucket VARCHAR(255),
	object_key VARCHAR(512) NOT NULL,
	file_name VARCHAR(255) NOT NULL,
	content_type VARCHAR(128),
	evidence_type VARCHAR(64),
	source VARCHAR(128),
	status VARCHAR(64),
	file_url TEXT,
	size INTEGER,
	checksum VARCHAR(255),
	meta JSON,
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(fact_id) REFERENCES facts (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_oss_uploads_id ON oss_uploads (id);

CREATE TABLE project_analysis_jobs (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	project_id INTEGER NOT NULL,
	version_id INTEGER,
	purpose VARCHAR(128),
	status VARCHAR(64),
	parameters JSON,
	result JSON,
	error_message TEXT,
	requested_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	started_at DATETIME,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(version_id) REFERENCES project_versions (id),
	FOREIGN KEY(requested_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_project_analysis_jobs_id ON project_analysis_jobs (id);

CREATE TABLE report_shares (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	version_id INTEGER,
	token VARCHAR(128) NOT NULL,
	expires_in_days INTEGER,
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(version_id) REFERENCES project_versions (id),
	UNIQUE (token),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_report_shares_id ON report_shares (id);

CREATE TABLE document_parse_jobs (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	project_id INTEGER NOT NULL,
	evidence_id INTEGER NOT NULL,
	file_name VARCHAR(255) NOT NULL,
	file_kind VARCHAR(64),
	parse_scope VARCHAR(64),
	purpose VARCHAR(128),
	status VARCHAR(64),
	parameters JSON,
	result JSON,
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	started_at DATETIME,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(evidence_id) REFERENCES evidences (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_document_parse_jobs_id ON document_parse_jobs (id);

CREATE TABLE venues (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	city VARCHAR(128) NOT NULL,
	address VARCHAR(512),
	capacity INTEGER,
	quote INTEGER,
	fire_safety_status VARCHAR(64),
	transport_notes TEXT,
	source VARCHAR(128),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_venues_tenant_city_name UNIQUE (tenant_id, city, name),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_venues_id ON venues (id);

CREATE TABLE tour_plans (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	status VARCHAR(64),
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_tour_plans_tenant_name UNIQUE (tenant_id, name),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_tour_plans_id ON tour_plans (id);

CREATE TABLE tour_stops (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tour_plan_id INTEGER NOT NULL,
	project_id INTEGER,
	venue_id INTEGER,
	city VARCHAR(128) NOT NULL,
	sequence INTEGER NOT NULL,
	scheduled_at VARCHAR(64),
	status VARCHAR(64),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_tour_stops_plan_sequence UNIQUE (tour_plan_id, sequence),
	FOREIGN KEY(tour_plan_id) REFERENCES tour_plans (id),
	FOREIGN KEY(project_id) REFERENCES projects (id),
	FOREIGN KEY(venue_id) REFERENCES venues (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_tour_stops_id ON tour_stops (id);

CREATE TABLE notifications (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	business_key VARCHAR(255) NOT NULL,
	notification_type VARCHAR(64),
	title VARCHAR(255) NOT NULL,
	content TEXT,
	status VARCHAR(64),
	context JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	read_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_notifications_recipient_key UNIQUE (tenant_id, user_id, business_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_notifications_id ON notifications (id);

CREATE TABLE project_actuals (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	actual_attendance INTEGER,
	actual_revenue INTEGER,
	actual_cost INTEGER,
	actual_profit INTEGER,
	status VARCHAR(64),
	notes TEXT,
	settled_at DATETIME,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_project_actuals_project UNIQUE (project_id),
	FOREIGN KEY(project_id) REFERENCES projects (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_project_actuals_id ON project_actuals (id);

CREATE TABLE ticketing_snapshots (
	id INTEGER NOT NULL AUTO_INCREMENT,
	project_id INTEGER NOT NULL,
	captured_at DATETIME NOT NULL,
	sold_count INTEGER NOT NULL,
	gross_revenue INTEGER,
	source VARCHAR(128) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_ticketing_snapshots_project_time_source UNIQUE (project_id, captured_at, source),
	FOREIGN KEY(project_id) REFERENCES projects (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_ticketing_snapshots_id ON ticketing_snapshots (id);

CREATE TABLE user_settings (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	locale VARCHAR(32),
	theme VARCHAR(32),
	notification_preferences JSON,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_user_settings_tenant_user UNIQUE (tenant_id, user_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_user_settings_id ON user_settings (id);

CREATE TABLE privacy_consents (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	scope VARCHAR(128) NOT NULL,
	granted INTEGER,
	policy_version VARCHAR(64),
	granted_at DATETIME,
	revoked_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_privacy_consents_tenant_user_scope UNIQUE (tenant_id, user_id, scope),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_privacy_consents_id ON privacy_consents (id);

CREATE TABLE member_invitations (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	invitee VARCHAR(255) NOT NULL,
	`role` VARCHAR(64),
	token VARCHAR(128) NOT NULL,
	status VARCHAR(64),
	invited_by INTEGER,
	expires_at DATETIME NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_member_invitations_active_invitee UNIQUE (tenant_id, invitee, status),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	UNIQUE (token),
	FOREIGN KEY(invited_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_member_invitations_id ON member_invitations (id);

CREATE TABLE agent_permissions (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	capability VARCHAR(128) NOT NULL,
	enabled INTEGER,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_agent_permissions_tenant_user_capability UNIQUE (tenant_id, user_id, capability),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_agent_permissions_id ON agent_permissions (id);

CREATE TABLE project_drafts (
	id INTEGER NOT NULL AUTO_INCREMENT,
	tenant_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	draft_key VARCHAR(128) NOT NULL,
	payload JSON,
	current_step INTEGER,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	CONSTRAINT uq_project_drafts_tenant_user_key UNIQUE (tenant_id, user_id, draft_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE INDEX ix_project_drafts_id ON project_drafts (id);

SET FOREIGN_KEY_CHECKS = 1;
