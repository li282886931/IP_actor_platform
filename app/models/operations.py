from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


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
