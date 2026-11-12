from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


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
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=True)
    status = Column(String(64), default='active')
    created_at = Column(DateTime, server_default=func.current_timestamp())


class TenantMember(Base):
    __tablename__ = 'tenant_members'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(String(64), default='admin')
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
