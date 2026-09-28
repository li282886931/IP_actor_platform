from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .database import Base


class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    tags = Column(String(255), default='')
    heat_score = Column(Integer, default=0)
    fan_count = Column(String(64), default='0')
    risk_level = Column(Integer, default=0)
    profile = Column(JSON, default=dict)


class Show(Base):
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=True)
    artist_name = Column(String(255), default='')
    city = Column(String(128), default='')
    date = Column(String(64), default='')
    venue = Column(String(255), default='')
    price = Column(String(64), default='')
    status = Column(String(64), default='on_sale')
    description = Column(Text, default='')
    poster_url = Column(Text, default='')
    artist = relationship('Artist')


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey('shows.id'))
    name = Column(String(255))
    phone = Column(String(64))


class AIGeneration(Base):
    __tablename__ = 'ai_generations'

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(64), nullable=False)
    prompt = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Tenant(Base):
    __tablename__ = 'tenants'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(64), default='active')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class UserGroup(Base):
    __tablename__ = 'user_groups'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default='')
    permission_set = Column(JSON, default=list)
    data_scope = Column(String(64), default='all_projects')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(128), nullable=True, unique=True)
    unionid = Column(String(128), nullable=True, unique=True)
    account = Column(String(255), nullable=True, unique=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(128), default='')
    phone = Column(String(64), default='')
    group_id = Column(Integer, ForeignKey('user_groups.id'), nullable=True)
    group_code = Column(String(64), default='B')
    status = Column(String(64), default='active')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class TenantMember(Base):
    __tablename__ = 'tenant_members'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(64), default='admin')
    created_at = Column(DateTime, server_default=func.current_timestamp())


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


class Fact(Base):
    __tablename__ = 'facts'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, default='')
    source = Column(String(128), default='')
    status = Column(String(64), default='pending')
    verified_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    verified_comment = Column(Text, default='')
    created_at = Column(DateTime, server_default=func.current_timestamp())
    verified_at = Column(DateTime, nullable=True)


class Assumption(Base):
    __tablename__ = 'assumptions'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, default='')
    confidence = Column(Integer, default=50)
    status = Column(String(64), default='active')
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Evidence(Base):
    __tablename__ = 'evidences'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    fact_id = Column(Integer, ForeignKey('facts.id'), nullable=True)
    name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    evidence_type = Column(String(64), default='document')
    source = Column(String(128), default='')
    status = Column(String(64), default='uploaded')
    meta = Column(JSON, default=dict)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class OSSUpload(Base):
    __tablename__ = 'oss_uploads'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    fact_id = Column(Integer, ForeignKey('facts.id'), nullable=True)
    provider = Column(String(64), default='local-placeholder')
    bucket = Column(String(255), default='')
    object_key = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(128), default='application/octet-stream')
    evidence_type = Column(String(64), default='document')
    source = Column(String(128), default='')
    status = Column(String(64), default='pending')
    file_url = Column(Text, default='')
    size = Column(Integer, nullable=True)
    checksum = Column(String(255), default='')
    meta = Column(JSON, default=dict)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    completed_at = Column(DateTime, nullable=True)


class DocumentParseJob(Base):
    __tablename__ = 'document_parse_jobs'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    evidence_id = Column(Integer, ForeignKey('evidences.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_kind = Column(String(64), default='document')
    parse_scope = Column(String(64), default='single_project')
    purpose = Column(String(128), default='')
    status = Column(String(64), default='queued')
    parameters = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class ProjectAnalysisJob(Base):
    __tablename__ = 'project_analysis_jobs'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    version_id = Column(Integer, ForeignKey('project_versions.id'), nullable=True)
    purpose = Column(String(128), default='')
    status = Column(String(64), default='queued')
    parameters = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error_message = Column(Text, default='')
    requested_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


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


class ReportShare(Base):
    __tablename__ = 'report_shares'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    version_id = Column(Integer, ForeignKey('project_versions.id'), nullable=True)
    token = Column(String(128), nullable=False, unique=True)
    expires_in_days = Column(Integer, default=7)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())


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


class Venue(Base):
    __tablename__ = 'venues'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'city', 'name', name='uq_venues_tenant_city_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    city = Column(String(128), nullable=False)
    address = Column(String(512), default='')
    capacity = Column(Integer, nullable=True)
    quote = Column(Integer, nullable=True)
    fire_safety_status = Column(String(64), default='unverified')
    transport_notes = Column(Text, default='')
    source = Column(String(128), default='')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class TourPlan(Base):
    __tablename__ = 'tour_plans'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tour_plans_tenant_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(64), default='draft')
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class TourStop(Base):
    __tablename__ = 'tour_stops'
    __table_args__ = (
        UniqueConstraint('tour_plan_id', 'sequence', name='uq_tour_stops_plan_sequence'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tour_plan_id = Column(Integer, ForeignKey('tour_plans.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=True)
    city = Column(String(128), nullable=False)
    sequence = Column(Integer, nullable=False)
    scheduled_at = Column(String(64), default='')
    status = Column(String(64), default='planned')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Notification(Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', 'business_key', name='uq_notifications_recipient_key'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    business_key = Column(String(255), nullable=False)
    notification_type = Column(String(64), default='system')
    title = Column(String(255), nullable=False)
    content = Column(Text, default='')
    status = Column(String(64), default='unread')
    context = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    read_at = Column(DateTime, nullable=True)


class ProjectActual(Base):
    __tablename__ = 'project_actuals'
    __table_args__ = (
        UniqueConstraint('project_id', name='uq_project_actuals_project'),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    actual_attendance = Column(Integer, nullable=True)
    actual_revenue = Column(Integer, nullable=True)
    actual_cost = Column(Integer, nullable=True)
    actual_profit = Column(Integer, nullable=True)
    status = Column(String(64), default='pending')
    notes = Column(Text, default='')
    settled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class TicketingSnapshot(Base):
    __tablename__ = 'ticketing_snapshots'
    __table_args__ = (
        UniqueConstraint('project_id', 'captured_at', 'source', name='uq_ticketing_snapshots_project_time_source'),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    captured_at = Column(DateTime, nullable=False)
    sold_count = Column(Integer, nullable=False)
    gross_revenue = Column(Integer, nullable=True)
    source = Column(String(128), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class UserSetting(Base):
    __tablename__ = 'user_settings'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', name='uq_user_settings_tenant_user'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    locale = Column(String(32), default='zh-CN')
    theme = Column(String(32), default='system')
    notification_preferences = Column(JSON, default=dict)
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class PrivacyConsent(Base):
    __tablename__ = 'privacy_consents'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', 'scope', name='uq_privacy_consents_tenant_user_scope'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    scope = Column(String(128), nullable=False)
    granted = Column(Integer, default=0)
    policy_version = Column(String(64), default='')
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class MemberInvitation(Base):
    __tablename__ = 'member_invitations'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'invitee', 'status', name='uq_member_invitations_active_invitee'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    invitee = Column(String(255), nullable=False)
    role = Column(String(64), default='member')
    token = Column(String(128), nullable=False, unique=True)
    status = Column(String(64), default='pending')
    invited_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class AgentPermission(Base):
    __tablename__ = 'agent_permissions'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', 'capability', name='uq_agent_permissions_tenant_user_capability'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    capability = Column(String(128), nullable=False)
    enabled = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


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
