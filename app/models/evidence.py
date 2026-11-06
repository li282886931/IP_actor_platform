from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


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


class ReportShare(Base):
    __tablename__ = 'report_shares'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    version_id = Column(Integer, ForeignKey('project_versions.id'), nullable=True)
    token = Column(String(128), nullable=False, unique=True)
    expires_in_days = Column(Integer, default=7)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=func.current_timestamp())
