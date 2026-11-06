from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(64), default='concert')
    status = Column(String(64), default='draft')
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=True)
    artist_name = Column(String(255), default='')
    city = Column(String(128), default='')
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=True)
    venue = Column(String(255), default='')
    source_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    schedule = Column(String(64), default='')
    expected_attendance = Column(Integer, nullable=True)
    avg_ticket_price = Column(Integer, nullable=True)
    artist_fee = Column(Integer, nullable=True)
    venue_cost = Column(Integer, nullable=True)
    marketing_cost = Column(Integer, nullable=True)
    production_cost = Column(Integer, nullable=True)
    available_funds = Column(Integer, nullable=True)
    venue_capacity = Column(Integer, nullable=True)
    ticket_tiers = Column(JSON, nullable=True)
    conservative_occupancy_rate = Column(Integer, nullable=True)
    neutral_occupancy_rate = Column(Integer, nullable=True)
    optimistic_occupancy_rate = Column(Integer, nullable=True)
    current_version_id = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class ProjectVersion(Base):
    __tablename__ = 'project_versions'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    version_no = Column(Integer, nullable=False)
    input_snapshot = Column(JSON, nullable=False)
    finance_result = Column(JSON, nullable=True)
    status = Column(String(64), default='draft')
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Decision(Base):
    __tablename__ = 'decisions'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    version_id = Column(Integer, ForeignKey('project_versions.id'), nullable=False)
    decision_type = Column(String(64), nullable=False)
    conditions = Column(Text, default='')
    decided_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    decided_at = Column(DateTime, server_default=func.current_timestamp())


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    due_date = Column(String(64), default='')
    status = Column(String(64), default='pending')
    result = Column(Text, default='')
    evidence_ids = Column(JSON, default=list)
    rejection_reason = Column(Text, default='')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Gate(Base):
    __tablename__ = 'gates'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(64), default='pending')
    required_evidence = Column(Text, default='')
    owner_group = Column(String(64), default='')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Risk(Base):
    __tablename__ = 'risks'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(255), nullable=False)
    level = Column(String(64), default='medium')
    mitigation = Column(Text, default='')
    status = Column(String(64), default='open')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class DecisionSnapshot(Base):
    __tablename__ = 'decision_snapshots'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project_version_id = Column(Integer, ForeignKey('project_versions.id'), nullable=True)
    snapshot_type = Column(String(64), default='work_event')
    input_lineage = Column(JSON, default=dict)
    finance_result = Column(JSON, default=dict)
    risk_summary = Column(JSON, default=dict)
    alert_summary = Column(JSON, default=dict)
    recommendation = Column(Text, default='')
    created_by_type = Column(String(64), default='system')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ProjectWorkPlan(Base):
    __tablename__ = 'project_work_plans'
    __table_args__ = (
        UniqueConstraint('project_id', 'version_no', name='uq_project_work_plans_project_version'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    version_no = Column(Integer, nullable=False)
    status = Column(String(64), default='current')
    plan_json = Column(JSON, default=dict)
    decision_snapshot_id = Column(Integer, ForeignKey('decision_snapshots.id'), nullable=True)
    created_from_event_id = Column(Integer, ForeignKey('project_work_events.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ProjectWorkEvent(Base):
    __tablename__ = 'project_work_events'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uq_project_work_events_tenant_idempotency'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    event_type = Column(String(64), nullable=False)
    business_key = Column(String(255), nullable=False)
    payload = Column(JSON, default=dict)
    source_asset_id = Column(Integer, ForeignKey('data_assets.id'), nullable=True)
    alert_event_id = Column(Integer, ForeignKey('alert_events.id'), nullable=True)
    decision_snapshot_id = Column(Integer, ForeignKey('decision_snapshots.id'), nullable=True)
    status = Column(String(64), default='queued')
    processed_at = Column(DateTime, nullable=True)
    idempotency_key = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ProjectDraft(Base):
    __tablename__ = 'project_drafts'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', 'draft_key', name='uq_project_drafts_tenant_user_key'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    draft_key = Column(String(128), nullable=False, default='default')
    payload = Column(JSON, default=dict)
    current_step = Column(Integer, default=1)
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
