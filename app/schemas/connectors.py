from typing import Literal
import re

from pydantic import BaseModel, Field, field_validator


AuthType = Literal[
    "none", "api_key", "bearer", "oauth2", "basic", "signature",
    "vendor_contract",
]


def _validate_public_config_schema(value):
    fields = (value or {}).get("fields") or []
    if not isinstance(fields, list):
        raise ValueError("config_schema.fields must be a list")
    for field in fields:
        if not isinstance(field, dict):
            raise ValueError("config schema field must be an object")
        name = str(field.get("name") or "")
        field_type = str(field.get("type") or "")
        if re.search(
            r"token|secret|password|authorization|api.?key|cookie|credential",
            f"{name} {field_type}",
            re.I,
        ):
            raise ValueError("真实鉴权字段必须使用 credential_ref")
    return value


def validate_public_connector_config(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(
                r"token|secret|password|authorization|api.?key|cookie|credential",
                str(key),
                re.I,
            ):
                raise ValueError("鉴权信息必须使用 credential_ref")
            validate_public_connector_config(item)
    elif isinstance(value, list):
        for item in value:
            validate_public_connector_config(item)
    return value


class CustomConnectorDefinitionIn(BaseModel):
    key: str = Field(min_length=3, max_length=128, pattern=r"^[a-z][a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    source_kind: Literal["api", "mcp", "skill"]
    domain: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=2000)
    auth_type: AuthType
    config_schema: dict = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)

    _public_config_only = field_validator("config_schema")(
        _validate_public_config_schema
    )


class CustomConnectorDefinitionUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    auth_type: AuthType | None = None
    config_schema: dict | None = None
    capabilities: list[str] | None = None
    enabled: bool | None = None

    _public_config_only = field_validator("config_schema")(
        _validate_public_config_schema
    )


class ConnectorRegistrationIn(BaseModel):
    definition_key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    credential_ref: str = Field(
        default="",
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]*$",
    )
    scope_config: dict = Field(default_factory=dict)
    schedule_config: dict = Field(default_factory=dict)


class ConnectorRegistrationUpdateIn(BaseModel):
    credential_ref: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]*$",
    )
    scope_config: dict | None = None
    schedule_config: dict | None = None
