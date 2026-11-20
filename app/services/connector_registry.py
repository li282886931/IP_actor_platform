import hashlib
import json
from datetime import datetime, timezone

from app.datasets.connector_catalog import BUILTIN_CONNECTORS
from app.integrations.connectors import connector_credential_is_configured
from app.models import ConnectorDefinition, DataSource


NON_RUNNABLE = {
    "adapter_required", "contract_required", "runner_required", "disabled",
}
REGISTRATION_STATES = {
    "pending_config", "pending_credentials", "pending_test", "testing", "ready", "active",
    "error", "disabled",
}


def seed_connector_definitions(db):
    catalog_keys = {item["key"] for item in BUILTIN_CONNECTORS}
    existing = {
        item.key: item
        for item in db.query(ConnectorDefinition).filter(
            ConnectorDefinition.builtin == 1,
            ConnectorDefinition.tenant_id.is_(None),
        )
    }
    for metadata in BUILTIN_CONNECTORS:
        definition = existing.get(metadata["key"])
        if definition is None:
            definition = ConnectorDefinition(
                key=metadata["key"],
                builtin=1,
                tenant_id=None,
            )
            db.add(definition)
            existing[metadata["key"]] = definition
        if definition.version is None or definition.version <= metadata["version"]:
            for field, value in metadata.items():
                setattr(definition, field, value)
            definition.enabled = 1
    for key, definition in existing.items():
        if key not in catalog_keys:
            definition.enabled = 0
    db.flush()

    definitions = {item.key: item.id for item in existing.values()}
    for source in db.query(DataSource).filter(DataSource.definition_id.is_(None)):
        definition_id = definitions.get(source.connector_key)
        if definition_id:
            source.definition_id = definition_id
    db.commit()


def public_config_complete(definition, scope_config):
    fields = (definition.config_schema or {}).get("fields") or []
    return all(
        not field.get("required")
        or scope_config.get(field["name"]) not in (None, "", [])
        for field in fields
    )


def registration_credential_status(source, definition):
    if definition.auth_type == "none":
        return "not_required"
    if not (source.credential_ref or "").strip():
        return "missing"
    return (
        "configured"
        if connector_credential_is_configured(
            definition.adapter_key,
            source.credential_ref,
        )
        else "missing"
    )


def configuration_hash(source):
    value = json.dumps(
        {
            "credential_ref": source.credential_ref or "",
            "scope_config": source.scope_config or {},
            "schedule_config": source.schedule_config or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode()).hexdigest()


def state_before_test(definition, source):
    if definition.availability != "available":
        return "pending_config"
    if not public_config_complete(definition, source.scope_config or {}):
        return "pending_config"
    if registration_credential_status(source, definition) == "missing":
        return "pending_credentials"
    return "pending_test"


def begin_test(source, definition):
    state = state_before_test(definition, source)
    if state != "pending_test":
        raise ValueError(state)
    source.status = "testing"


def finish_test(source, *, success, summary):
    source.status = "ready" if success else "error"
    source.last_test_at = datetime.now(timezone.utc)
    source.last_test_result = {
        "ok": bool(success),
        "code": summary["code"],
        "message": summary["message"],
        "capabilities": summary.get("capabilities", []),
        "config_hash": configuration_hash(source),
    }


def activate_registration(source):
    result = source.last_test_result or {}
    if not result.get("ok") or result.get("config_hash") != configuration_hash(source):
        raise ValueError("A current successful connection test is required")
    source.status = "active"
    source.activated_at = datetime.now(timezone.utc)


def disable_registration(source):
    source.status = "disabled"


def registration_status(definition, source):
    if source is None:
        return "unregistered"
    if source.status in {"testing", "ready", "active", "error", "disabled"}:
        return source.status
    return state_before_test(definition, source)
