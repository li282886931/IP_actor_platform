import re

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship, validates

from app.database import Base


def _public_connector_config(value):
    if isinstance(value, dict):
        return {
            key: _public_connector_config(item)
            for key, item in value.items()
            if not re.search(
                r"token|secret|password|authorization|api.?key|cookie|credential",
                str(key),
                re.I,
            )
        }
    if isinstance(value, list):
        return [_public_connector_config(item) for item in value]
    return value


class ConnectorDefinition(Base):
    __tablename__ = 'connector_definitions'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'key', name='uq_connector_definitions_tenant_key'),
    )

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    source_kind = Column(String(32), nullable=False)
    domain = Column(String(64), nullable=False)
    description = Column(Text, default='')
    builtin = Column(Integer, default=0, nullable=False)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=True)
    auth_type = Column(String(32), default='none', nullable=False)
    config_schema = Column(JSON, default=dict)
    capabilities = Column(JSON, default=list)
    adapter_key = Column(String(128), default='')
    availability = Column(String(32), default='adapter_required', nullable=False)
    human_verification_required = Column(Integer, default=1, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    enabled = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class ExternalDataJob(Base):
    __tablename__ = 'external_data_jobs'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    source_type = Column(String(64), nullable=False)
    provider = Column(String(64), default='mcp')
    query = Column(Text, nullable=False)
    purpose = Column(String(128), default='')
    status = Column(String(64), default='queued')
    parameters = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error_message = Column(Text, default='')
    requested_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class DataSource(Base):
    __tablename__ = 'data_sources'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_data_sources_tenant_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    source_kind = Column(String(64), nullable=False)
    connector_key = Column(String(64), nullable=False)
    definition_id = Column(Integer, ForeignKey('connector_definitions.id'), nullable=True)
    status = Column(String(64), default='configured')
    credential_ref = Column(String(512), default='')
    schedule_config = Column(JSON, default=dict)
    scope_config = Column(JSON, default=dict)
    last_test_at = Column(DateTime, nullable=True)
    last_test_result = Column(JSON, default=dict)
    activated_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    @validates('scope_config', 'schedule_config')
    def sanitize_public_config(self, key, value):
        return _public_connector_config(value or {})


class DataAsset(Base):
    __tablename__ = 'data_assets'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
    asset_type = Column(String(64), nullable=False)
    source_uri = Column(Text, default='')
    content_hash = Column(String(255), default='')
    captured_at = Column(DateTime, server_default=func.current_timestamp())
    effective_until = Column(DateTime, nullable=True)
    visibility = Column(String(64), default='project')
    status = Column(String(64), default='received')
    raw_payload_ref = Column(Text, default='')
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class DataRecord(Base):
    __tablename__ = 'data_records'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('data_assets.id'), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(128), nullable=False)
    metric_key = Column(String(128), nullable=False)
    value_json = Column(JSON, default=dict)
    unit = Column(String(64), default='')
    observed_at = Column(DateTime, nullable=True)
    confidence = Column(Integer, nullable=True)
    record_status = Column(String(64), default='observed')
    lineage = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class DataQualityIssue(Base):
    __tablename__ = 'data_quality_issues'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('data_assets.id'), nullable=True)
    record_id = Column(Integer, ForeignKey('data_records.id'), nullable=True)
    issue_type = Column(String(64), nullable=False)
    severity = Column(String(64), default='medium')
    details = Column(JSON, default=dict)
    status = Column(String(64), default='open')
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class MonitoringRule(Base):
    __tablename__ = 'monitoring_rules'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    rule_type = Column(String(64), nullable=False)
    condition_json = Column(JSON, default=dict)
    severity_policy = Column(String(64), default='reminder')
    notification_policy = Column(JSON, default=dict)
    enabled = Column(Integer, default=1)
    version = Column(Integer, default=1)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class AlertEvent(Base):
    __tablename__ = 'alert_events'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'dedupe_key', name='uq_alert_events_tenant_dedupe_key'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    rule_id = Column(Integer, ForeignKey('monitoring_rules.id'), nullable=False)
    business_key = Column(String(255), nullable=False)
    severity = Column(String(64), default='reminder')
    title = Column(String(255), nullable=False)
    summary = Column(Text, default='')
    context = Column(JSON, default=dict)
    status = Column(String(64), default='open')
    source_record_ids = Column(JSON, default=list)
    dedupe_key = Column(String(255), nullable=False)
    triggered_at = Column(DateTime, server_default=func.current_timestamp())
    resolved_at = Column(DateTime, nullable=True)


class ConversionAssumption(Base):
    __tablename__ = 'conversion_assumptions'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    scope_type = Column(String(64), nullable=False)
    scope_id = Column(String(128), nullable=False)
    funnel_stage_from = Column(String(64), nullable=False)
    funnel_stage_to = Column(String(64), nullable=False)
    rate = Column(JSON, nullable=False)
    segment = Column(JSON, default=dict)
    evidence_ids = Column(JSON, default=list)
    confidence = Column(Integer, default=50)
    status = Column(String(64), default='draft')
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    version_no = Column(Integer, default=1)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class CaseOutcome(Base):
    __tablename__ = 'case_outcomes'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    title = Column(String(255), nullable=False)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=True)
    city = Column(String(128), default='')
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=True)
    outcome_label = Column(String(64), nullable=False)
    scenario = Column(JSON, default=dict)
    revenue = Column(Integer, nullable=True)
    cost = Column(Integer, nullable=True)
    profit = Column(Integer, nullable=True)
    occupancy_rate = Column(JSON, nullable=True)
    failure_reason = Column(Text, default='')
    evidence_ids = Column(JSON, default=list)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ForecastCalibration(Base):
    __tablename__ = 'forecast_calibrations'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    conversion_assumption_id = Column(Integer, ForeignKey('conversion_assumptions.id'), nullable=True)
    forecast_metric = Column(String(128), nullable=False)
    forecast_value = Column(JSON, nullable=True)
    actual_value = Column(JSON, nullable=True)
    error_value = Column(JSON, nullable=True)
    segment = Column(JSON, default=dict)
    status = Column(String(64), default='candidate')
    candidate_rate = Column(JSON, nullable=True)
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
