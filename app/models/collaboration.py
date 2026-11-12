from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from app.database import Base


class ProjectGrant(Base):
    __tablename__ = "project_grants"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_grant_user"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_code = Column(String(64), nullable=False)
    duties = Column(JSON, default=list)
    status = Column(String(32), default="active")
    revision = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": revision}


class CollaborationItem(Base):
    __tablename__ = "collaboration_items"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    version_id = Column(Integer, ForeignKey("project_versions.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String(64), nullable=False, default="draft")
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    __mapper_args__ = {"version_id_col": revision}


class CollaborationHistory(Base):
    __tablename__ = "collaboration_history"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_type = Column(String(64), nullable=False)
    subject_id = Column(Integer, nullable=False)
    action = Column(String(64), nullable=False)
    before = Column(JSON, default=dict)
    after = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class CollaborationReceipt(Base):
    __tablename__ = "collaboration_receipts"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "request_key", name="uq_collaboration_request"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_key = Column(String(128), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    result = Column(JSON, nullable=False)


class PersonalRecord(Base):
    __tablename__ = "personal_records"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "type", "record_key", name="uq_personal_record"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(32), nullable=False)
    record_key = Column(String(128), nullable=False)
    payload = Column(JSON, default=dict)
    revision = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": revision}


class ShowProjectBinding(Base):
    __tablename__ = "show_project_bindings"
    __table_args__ = (UniqueConstraint("show_id", name="uq_bound_show"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
