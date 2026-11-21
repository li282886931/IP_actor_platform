"""Versioned decision inputs and role-owned operating records."""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class DecisionRuleVersion(Base):
    __tablename__ = "decision_rule_versions"
    __table_args__ = (UniqueConstraint("tenant_id", "version_no", name="uq_decision_rule_version"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=False)
    source = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    parent_id = Column(Integer, ForeignKey("decision_rule_versions.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class DecisionReport(Base):
    __tablename__ = "decision_reports"
    __table_args__ = (UniqueConstraint("project_id", "fingerprint", name="uq_decision_report_inputs"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project_version_id = Column(Integer, ForeignKey("project_versions.id"), nullable=True)
    rule_version_id = Column(Integer, ForeignKey("decision_rule_versions.id"), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    inputs = Column(JSON, nullable=False)
    rule_snapshot = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    verification_status = Column(String(32), nullable=False, default="pending")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class OperatingRecord(Base):
    __tablename__ = "operating_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "owner_id", "kind", "record_key", name="uq_operating_record_owner"),
    )
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    kind = Column(String(32), nullable=False)
    record_key = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, default=dict)
    status = Column(String(32), nullable=False, default="pending")
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    __mapper_args__ = {"version_id_col": revision}


class CityProfile(Base):
    __tablename__ = "city_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_city_profile_name"),)
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(128), nullable=False)
    profile = Column(JSON, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": revision}
