import json

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.datasets.connector_catalog import BUILTIN_CONNECTORS
from app.models import ConnectorDefinition, DataSource, Tenant
from app.services.connector_registry import seed_connector_definitions


EXPECTED_KEYS = {
    "agent_api", "mcp_web", "organizer_files", "spreadsheet_evidence",
    "custom_rest_api", "custom_mcp", "custom_skill",
    "amap", "baidu_maps", "tencent_lbs", "venue_official_api",
    "city_culture_tourism_api", "city_transport_api", "hotel_market_api",
    "qweather", "qweather_warning", "cma_weather", "venue_iot",
    "artist_agency_api", "weibo_open", "douyin_open", "xiaohongshu_business",
    "bilibili_open", "wechat_index", "baidu_index", "qq_music_business",
    "netease_music_business", "kugou_kuwo_business", "sentiment_mcp",
    "ticketing_api", "damai_business", "maoyan_business", "showstart_business",
    "ticket_refund_api", "ticket_entry_api", "audience_crm",
    "brand_crm", "sponsor_rights_api", "ad_exposure_api", "commerce_sales_api",
    "finance_erp", "invoice_api", "payment_settlement_api", "bank_supervision_api",
    "government_approval_api", "public_security_api", "fire_safety_api",
    "copyright_registry_api", "esign_contract_api", "entry_flow_api",
    "security_incident_api", "market_research_skill", "ip_research_skill",
    "audience_profile_skill", "city_analysis_skill", "content_strategy_skill",
    "hook_analyzer_skill", "risk_classification_skill", "case_retrieval_skill",
    "report_synthesis_skill", "review_calibration_skill",
}


def connector_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_connector_definition_and_registration_columns_exist():
    db = connector_session()
    try:
        columns = {
            column["name"]
            for column in inspect(db.bind).get_columns("connector_definitions")
        }
        assert {
            "id", "key", "name", "source_kind", "domain", "description", "builtin",
            "tenant_id", "auth_type", "config_schema", "capabilities", "adapter_key",
            "availability", "human_verification_required", "version", "enabled",
            "created_at", "updated_at",
        } <= columns
        source_columns = {
            column["name"]
            for column in inspect(db.bind).get_columns("data_sources")
        }
        assert {
            "definition_id", "last_test_at", "last_test_result", "activated_at",
        } <= source_columns
        assert ConnectorDefinition.__tablename__ == "connector_definitions"
    finally:
        db.close()


def test_builtin_catalog_is_complete_and_safe():
    assert {item["key"] for item in BUILTIN_CONNECTORS} == EXPECTED_KEYS
    assert len(BUILTIN_CONNECTORS) == len(EXPECTED_KEYS) == 61
    assert all(item["source_kind"] in {"api", "mcp", "skill", "file"}
               for item in BUILTIN_CONNECTORS)
    assert all(item["availability"] in {
        "available", "adapter_required", "contract_required", "runner_required",
    } for item in BUILTIN_CONNECTORS)
    assert all("secret" not in json.dumps(item).lower() for item in BUILTIN_CONNECTORS)


def test_seed_is_idempotent_and_backfills_legacy_sources_without_overwriting():
    db = connector_session()
    try:
        tenant = Tenant(name="目录测试空间", status="active")
        db.add(tenant)
        db.flush()
        source = DataSource(
            tenant_id=tenant.id,
            name="自定义高德",
            source_kind="api",
            connector_key="amap",
            status="disabled",
            credential_ref="AMAP_PROD",
            scope_config={"project_ids": [9]},
        )
        db.add(source)
        db.commit()

        seed_connector_definitions(db)
        first_count = db.query(ConnectorDefinition).filter(
            ConnectorDefinition.builtin == 1,
        ).count()
        db.refresh(source)
        definition_id = source.definition_id
        seed_connector_definitions(db)
        db.refresh(source)

        assert first_count == 61
        assert db.query(ConnectorDefinition).filter(
            ConnectorDefinition.builtin == 1,
        ).count() == 61
        assert source.definition_id == definition_id
        assert source.credential_ref == "AMAP_PROD"
        assert source.scope_config == {"project_ids": [9]}
        assert source.status == "disabled"
    finally:
        db.close()
