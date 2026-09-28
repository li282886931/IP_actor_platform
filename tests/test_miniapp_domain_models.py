import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
import app.models as models
import app.services as services


DOMAIN_MODELS = {
    models.Venue: {"tenant_id", "name", "city", "capacity", "quote"},
    models.TourPlan: {"tenant_id", "name", "status", "created_by"},
    models.TourStop: {"tour_plan_id", "project_id", "venue_id", "sequence"},
    models.Notification: {"tenant_id", "user_id", "business_key", "read_at"},
    models.ProjectActual: {"project_id", "actual_attendance", "actual_revenue", "actual_cost"},
    models.TicketingSnapshot: {"project_id", "captured_at", "sold_count", "gross_revenue"},
    models.UserSetting: {"tenant_id", "user_id", "notification_preferences"},
    models.PrivacyConsent: {"tenant_id", "user_id", "scope", "granted"},
    models.MemberInvitation: {"tenant_id", "invitee", "token", "status"},
    models.AgentPermission: {"tenant_id", "user_id", "capability", "enabled"},
    models.ProjectDraft: {"tenant_id", "user_id", "draft_key", "payload", "current_step"},
}


def make_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    return engine, session_factory


def test_remaining_miniapp_models_have_required_ownership_and_business_fields():
    for model, required_columns in DOMAIN_MODELS.items():
        assert required_columns <= set(model.__table__.columns.keys())


def test_remaining_miniapp_tables_define_business_unique_constraints():
    for model in DOMAIN_MODELS:
        unique_constraints = [
            constraint
            for constraint in model.__table__.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        ]
        assert unique_constraints, f"{model.__tablename__} must define a business unique key"


def test_init_db_creates_domain_tables_and_seeds_reference_data_idempotently(monkeypatch):
    engine, session_factory = make_session(monkeypatch)

    services.init_db()
    services.init_db()

    inspector = inspect(engine)
    assert set(model.__tablename__ for model in DOMAIN_MODELS) <= set(inspector.get_table_names())

    db = session_factory()
    try:
        venues = db.query(models.Venue).order_by(models.Venue.name.asc()).all()
        assert {(venue.city, venue.name) for venue in venues} == {
            ("北京", "鸟巢"),
            ("上海", "梅赛德斯-奔驰文化中心"),
            ("台北", "台北小巨蛋"),
        }
        assert db.query(models.TourPlan).count() == 0
        assert db.query(models.Notification).count() == 0
        assert db.query(models.ProjectActual).count() == 0
        assert db.query(models.TicketingSnapshot).count() == 0
        assert db.query(models.MemberInvitation).count() == 0
    finally:
        db.close()
