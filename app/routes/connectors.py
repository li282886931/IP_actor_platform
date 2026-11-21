from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.responses import json_ok
from app.database import get_db
from app.integrations.connector_runtime import test_registration
from app.models import ConnectorDefinition, DataSource
from app.schemas import (
    ConnectorRegistrationIn,
    ConnectorRegistrationUpdateIn,
    CustomConnectorDefinitionIn,
    CustomConnectorDefinitionUpdateIn,
)
from app.schemas.connectors import validate_public_connector_config
from app.services.auth import RequestContext, resolve_request_context
from app.services.connector_registry import (
    activate_registration,
    begin_test,
    disable_registration,
    finish_test,
    registration_credential_status,
    registration_status,
    state_before_test,
)


router = APIRouter()


def connector_context(
    authorization: Optional[str] = Header(default=None),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    db: Session = Depends(get_db),
):
    return resolve_request_context(
        db,
        authorization=authorization or "",
        tenant_header=x_tenant_id,
    )


def require_connector_admin(context: RequestContext):
    if context.user.group_code != "root":
        raise HTTPException(403, "仅平台管理员可管理数据连接器")


def _definition_for_tenant(db, tenant_id, *, key=None, definition_id=None):
    query = db.query(ConnectorDefinition).filter(
        ConnectorDefinition.enabled == 1,
        (
            (ConnectorDefinition.builtin == 1)
            | (ConnectorDefinition.tenant_id == tenant_id)
        ),
    )
    if key is not None:
        query = query.filter(ConnectorDefinition.key == key)
    if definition_id is not None:
        query = query.filter(ConnectorDefinition.id == definition_id)
    return query.order_by(ConnectorDefinition.builtin.asc()).first()


def _public_test_result(result):
    return {
        key: value
        for key, value in (result or {}).items()
        if key in {"ok", "code", "message", "capabilities"}
    }


def _serialize_registration(source, definition):
    return {
        "id": source.id,
        "tenant_id": source.tenant_id,
        "definition_id": source.definition_id,
        "name": source.name,
        "source_kind": source.source_kind,
        "connector_key": source.connector_key,
        "status": registration_status(definition, source),
        "credential_ref": source.credential_ref or "",
        "credential_status": registration_credential_status(source, definition),
        "scope_config": source.scope_config or {},
        "schedule_config": source.schedule_config or {},
        "last_test_at": source.last_test_at.isoformat() if source.last_test_at else None,
        "last_test_result": _public_test_result(source.last_test_result),
        "activated_at": source.activated_at.isoformat() if source.activated_at else None,
    }


def _serialize_definition(definition, registration=None):
    return {
        "id": definition.id,
        "key": definition.key,
        "name": definition.name,
        "source_kind": definition.source_kind,
        "domain": definition.domain,
        "description": definition.description or "",
        "builtin": bool(definition.builtin),
        "tenant_id": definition.tenant_id,
        "auth_type": definition.auth_type,
        "config_schema": definition.config_schema or {},
        "capabilities": definition.capabilities or [],
        "adapter_key": definition.adapter_key or "",
        "availability": definition.availability,
        "human_verification_required": bool(
            definition.human_verification_required
        ),
        "version": definition.version,
        "enabled": bool(definition.enabled),
        "registration": (
            _serialize_registration(registration, definition)
            if registration else None
        ),
    }


@router.get("/connector-definitions")
def list_connector_definitions(
    source_kind: Optional[str] = None,
    domain: Optional[str] = None,
    availability: Optional[str] = None,
    registration_status_filter: Optional[str] = Query(
        default=None,
        alias="registration_status",
    ),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    query = db.query(ConnectorDefinition).filter(
        ConnectorDefinition.enabled == 1,
        (
            (ConnectorDefinition.builtin == 1)
            | (ConnectorDefinition.tenant_id == context.tenant.id)
        ),
    )
    if source_kind:
        query = query.filter(ConnectorDefinition.source_kind == source_kind)
    if domain:
        query = query.filter(ConnectorDefinition.domain == domain)
    if availability:
        query = query.filter(ConnectorDefinition.availability == availability)
    registrations = {
        source.definition_id: source
        for source in db.query(DataSource).filter(
            DataSource.tenant_id == context.tenant.id,
            DataSource.definition_id.is_not(None),
        )
    }
    result = [
        _serialize_definition(item, registrations.get(item.id))
        for item in query.order_by(ConnectorDefinition.id).all()
    ]
    if registration_status_filter:
        result = [
            item for item in result
            if (
                (item["registration"] or {}).get("status", "unregistered")
                == registration_status_filter
            )
        ]
    return json_ok(result)


@router.post("/connector-definitions/custom")
def create_custom_connector_definition(
    payload: CustomConnectorDefinitionIn,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    values = CustomConnectorDefinitionIn.model_validate(
        payload.model_dump()
    ).model_dump()
    conflict = db.query(ConnectorDefinition).filter(
        ConnectorDefinition.key == values["key"],
        (
            (ConnectorDefinition.builtin == 1)
            | (ConnectorDefinition.tenant_id == context.tenant.id)
        ),
    ).first()
    if conflict:
        raise HTTPException(409, "连接器 key 已存在")
    source_kind = values.pop("source_kind")
    definition = ConnectorDefinition(
        **values,
        source_kind=source_kind,
        builtin=0,
        tenant_id=context.tenant.id,
        adapter_key={
            "api": "custom_rest_api",
            "mcp": "custom_mcp",
            "skill": "custom_skill",
        }[source_kind],
        availability="runner_required" if source_kind == "skill" else "available",
        human_verification_required=1,
        version=1,
        enabled=1,
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return json_ok(_serialize_definition(definition))


@router.patch("/connector-definitions/{definition_id}")
def update_custom_connector_definition(
    definition_id: int,
    payload: CustomConnectorDefinitionUpdateIn,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    definition = db.query(ConnectorDefinition).filter(
        ConnectorDefinition.id == definition_id,
    ).first()
    if not definition:
        raise HTTPException(404, "连接器定义不存在")
    if definition.builtin or definition.tenant_id != context.tenant.id:
        raise HTTPException(403, "内置或其他空间的连接器定义不可修改")
    values = CustomConnectorDefinitionUpdateIn.model_validate(
        payload.model_dump()
    ).model_dump(exclude_none=True)
    for key, value in values.items():
        setattr(definition, key, int(value) if key == "enabled" else value)
    definition.version += 1
    db.commit()
    db.refresh(definition)
    return json_ok(_serialize_definition(definition))


@router.post("/data-sources/register")
def register_data_source(
    payload: ConnectorRegistrationIn,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    values = ConnectorRegistrationIn.model_validate(
        payload.model_dump()
    ).model_dump()
    try:
        validate_public_connector_config(values["scope_config"])
        validate_public_connector_config(values["schedule_config"])
    except ValueError:
        raise HTTPException(422, "公开配置不得包含鉴权信息，请使用 credential_ref")
    definition = _definition_for_tenant(
        db,
        context.tenant.id,
        key=values.pop("definition_key"),
    )
    if not definition:
        raise HTTPException(404, "连接器定义不存在")
    name = values["name"].strip()
    existing = db.query(DataSource).filter(
        DataSource.tenant_id == context.tenant.id,
        DataSource.name == name,
    ).first()
    if existing:
        if existing.definition_id != definition.id:
            raise HTTPException(409, "数据源名称已被其他连接器使用")
        return json_ok(_serialize_registration(existing, definition))
    source = DataSource(
        tenant_id=context.tenant.id,
        definition_id=definition.id,
        name=name,
        source_kind=definition.source_kind,
        connector_key=definition.key,
        credential_ref=values["credential_ref"].strip(),
        scope_config=values["scope_config"],
        schedule_config=values["schedule_config"],
        created_by=context.user.id,
    )
    source.status = state_before_test(definition, source)
    db.add(source)
    db.commit()
    db.refresh(source)
    return json_ok(_serialize_registration(source, definition))


def _owned_source(db, context, source_id):
    source = db.query(DataSource).filter(
        DataSource.id == source_id,
        DataSource.tenant_id == context.tenant.id,
    ).first()
    if not source:
        raise HTTPException(404, "数据源不存在")
    definition = _definition_for_tenant(
        db,
        context.tenant.id,
        definition_id=source.definition_id,
    )
    if not definition:
        raise HTTPException(409, "数据源尚未关联可用连接器定义")
    return source, definition


@router.get("/data-sources/{source_id}")
def get_data_source(
    source_id: int,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    source, definition = _owned_source(db, context, source_id)
    return json_ok(_serialize_registration(source, definition))


@router.patch("/data-sources/{source_id}")
def update_data_source(
    source_id: int,
    payload: ConnectorRegistrationUpdateIn,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    source, definition = _owned_source(db, context, source_id)
    values = ConnectorRegistrationUpdateIn.model_validate(
        payload.model_dump()
    ).model_dump(exclude_none=True)
    try:
        validate_public_connector_config(values.get("scope_config", {}))
        validate_public_connector_config(values.get("schedule_config", {}))
    except ValueError:
        raise HTTPException(422, "公开配置不得包含鉴权信息，请使用 credential_ref")
    for key, value in values.items():
        setattr(source, key, value.strip() if key == "credential_ref" else value)
    source.status = state_before_test(definition, source)
    db.commit()
    db.refresh(source)
    return json_ok(_serialize_registration(source, definition))


@router.post("/data-sources/{source_id}/test")
def test_data_source(
    source_id: int,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    source, definition = _owned_source(db, context, source_id)
    try:
        begin_test(source, definition)
    except ValueError as error:
        raise HTTPException(409, f"连接器尚不可测试：{error}")
    result = test_registration(source, definition)
    finish_test(source, success=result["ok"], summary=result)
    db.commit()
    db.refresh(source)
    return json_ok(_serialize_registration(source, definition))


@router.post("/data-sources/{source_id}/activate")
def activate_data_source(
    source_id: int,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    source, definition = _owned_source(db, context, source_id)
    if definition.availability != "available":
        raise HTTPException(409, "连接器定义当前不可启用")
    try:
        activate_registration(source)
    except ValueError as error:
        raise HTTPException(409, str(error))
    db.commit()
    db.refresh(source)
    return json_ok(_serialize_registration(source, definition))


@router.post("/data-sources/{source_id}/disable")
def disable_data_source(
    source_id: int,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    source, definition = _owned_source(db, context, source_id)
    disable_registration(source)
    db.commit()
    db.refresh(source)
    return json_ok(_serialize_registration(source, definition))


@router.get("/data-sources/{source_id}/credential-status")
def data_source_credential_status(
    source_id: int,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(connector_context),
):
    require_connector_admin(context)
    source, definition = _owned_source(db, context, source_id)
    status = registration_credential_status(source, definition)
    return json_ok({"status": "configured" if status == "not_required" else status})
