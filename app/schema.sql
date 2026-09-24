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
	artist_name VARCHAR(255),
	city VARCHAR(128),
	venue VARCHAR(255),
	schedule VARCHAR(64),
	expected_attendance INTEGER,
	avg_ticket_price INTEGER,
	artist_fee INTEGER,
	venue_cost INTEGER,
	marketing_cost INTEGER,
	production_cost INTEGER,
	current_version_id INTEGER,
	created_by INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
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

SET FOREIGN_KEY_CHECKS = 1;
