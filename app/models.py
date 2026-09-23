from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, func
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
    artist_name = Column(String(255), default='')
    city = Column(String(128), default='')
    venue = Column(String(255), default='')
    schedule = Column(String(64), default='')
    expected_attendance = Column(Integer, nullable=True)
    avg_ticket_price = Column(Integer, nullable=True)
    artist_fee = Column(Integer, nullable=True)
    venue_cost = Column(Integer, nullable=True)
    marketing_cost = Column(Integer, nullable=True)
    production_cost = Column(Integer, nullable=True)
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
