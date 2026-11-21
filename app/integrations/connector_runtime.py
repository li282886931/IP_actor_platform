"""Allowlisted, bounded connector connection tests."""
import requests

from app.datasets.connector_catalog import BUILTIN_SKILL_KEYS
from app.integrations import live_reads
from app.integrations.connectors import resolve_connector_credential


SKILL_RUNNER_REGISTRY = {}


def connector_adapter(adapter_key):
    return ADAPTER_REGISTRY.get(adapter_key)


def register_skill_runner(key, runner):
    if key not in BUILTIN_SKILL_KEYS:
        raise ValueError("Unknown skill definition")
    SKILL_RUNNER_REGISTRY[key] = runner


def _skill_runner_key(source, definition):
    return (
        (definition.adapter_key or "").strip()
        if definition is not None
        else ""
    ) or source.connector_key


def execution_block_reason(source, definition, parameters):
    if source.status == "disabled":
        return "Data source is disabled"
    if source.status != "active":
        return "Data source is not active"
    if source.source_kind == "skill":
        if SKILL_RUNNER_REGISTRY.get(_skill_runner_key(source, definition)) is None:
            return "Skill runner is not registered"
        return ""
    if source.connector_key not in {
        "agent_api", "custom_rest_api", "mcp_web", "custom_mcp",
    }:
        return "Connector is not executable"
    auth_type = definition.auth_type if definition is not None else "bearer"
    if auth_type != "none" and not resolve_connector_credential(
        source.connector_key,
        source.credential_ref,
    ):
        return "Connector credential is not configured"
    try:
        live_reads.validate_endpoint((source.scope_config or {}).get("endpoint", ""))
    except (TypeError, ValueError):
        return "Connector endpoint is invalid"
    if source.connector_key in {"mcp_web", "custom_mcp"}:
        page_url = (parameters or {}).get("url", "")
        if not page_url:
            return "MCP URL is required"
        try:
            live_reads.validate_public_host(page_url)
        except (TypeError, ValueError):
            return "MCP URL is invalid"
    return ""


def execute_registration(source, definition, project, parameters):
    if source.source_kind == "skill":
        runner = SKILL_RUNNER_REGISTRY[_skill_runner_key(source, definition)]
        result = runner(
            source=source,
            definition=definition,
            project=project,
            parameters=parameters or {},
            connection_test=False,
        )
        return live_reads.redact(result)
    return live_reads.read_source(
        source,
        project,
        page_url=(parameters or {}).get("url"),
    )[0]


def _result(ok, code, message, capabilities=None):
    return {
        "ok": ok,
        "code": code,
        "message": message,
        "capabilities": capabilities or [],
    }


def _file_connection(source, definition, credential):
    return _result(True, "connected", "连接测试通过", definition.capabilities)


def _vendor_get(url, credential, params, success):
    try:
        payload, _ = live_reads.request_json(
            "GET",
            url,
            params={**params, "key": credential},
            timeout=10,
        )
        if not isinstance(payload, dict) or not success(payload):
            return _result(False, "provider_rejected", "供应商拒绝连接测试")
    except (requests.RequestException, ValueError, TypeError):
        return _result(False, "connection_failed", "连接测试失败")
    return _result(True, "connected", "连接测试通过", ["read"])


def _amap_connection(source, definition, credential):
    return _vendor_get(
        "https://restapi.amap.com/v5/place/text",
        credential,
        {"keywords": "场馆", "city": "北京", "page_size": 1},
        lambda payload: payload.get("status") == "1",
    )


def _qweather_connection(source, definition, credential):
    return _vendor_get(
        "https://devapi.qweather.com/v7/weather/3d",
        credential,
        {"location": "101010100"},
        lambda payload: payload.get("code") == "200",
    )


def _readonly_api_connection(source, definition, credential):
    endpoint = (source.scope_config or {}).get("endpoint", "")
    try:
        live_reads.validate_endpoint(endpoint)
    except (TypeError, ValueError):
        return _result(False, "endpoint_rejected", "服务地址未通过安全校验")
    headers = {"Authorization": f"Bearer {credential}"} if credential else {}
    try:
        live_reads.request_json("GET", endpoint, headers=headers)
    except (requests.RequestException, ValueError, TypeError):
        return _result(False, "connection_failed", "连接测试失败")
    return _result(True, "connected", "连接测试通过", definition.capabilities)


def _readonly_mcp_connection(source, definition, credential):
    config = source.scope_config or {}
    endpoint = config.get("endpoint", "")
    try:
        live_reads.validate_endpoint(endpoint)
    except (TypeError, ValueError):
        return _result(False, "endpoint_rejected", "服务地址未通过安全校验")
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if credential:
        headers["Authorization"] = f"Bearer {credential}"
    counter = 0

    def rpc(method, params=None, notification=False):
        nonlocal counter
        body = {"jsonrpc": "2.0", "method": method}
        if not notification:
            counter += 1
            body["id"] = counter
        if params is not None:
            body["params"] = params
        reply, response_headers = live_reads.request_json(
            "POST",
            endpoint,
            json=body,
            headers=headers,
            timeout=10,
        )
        session_id = (
            response_headers.get("Mcp-Session-Id")
            or response_headers.get("mcp-session-id")
        )
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        if notification:
            return {}
        if not isinstance(reply, dict) or reply.get("id") != counter or "error" in reply:
            raise ValueError("MCP protocol request failed")
        return reply.get("result") or {}

    try:
        initialized = rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "connector-registry", "version": "1.0"},
            },
        )
        if initialized.get("protocolVersion") not in {
            "2025-03-26", "2025-06-18", "2025-11-25",
        }:
            return _result(False, "protocol_rejected", "MCP 协议版本不受支持")
        headers["MCP-Protocol-Version"] = initialized["protocolVersion"]
        rpc("notifications/initialized", notification=True)
        tools = rpc("tools/list").get("tools") or []
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return _result(False, "connection_failed", "连接测试失败")
    tool = next((item for item in tools if item.get("name") == config.get("tool")), None)
    if not tool:
        return _result(False, "tool_missing", "配置的 MCP 工具不存在")
    if (tool.get("annotations") or {}).get("readOnlyHint") is False:
        return _result(False, "tool_not_readonly", "MCP 工具不是只读工具")
    return _result(True, "connected", "连接测试通过", definition.capabilities)


ADAPTER_REGISTRY = {
    "amap": _amap_connection,
    "qweather": _qweather_connection,
    "agent_api": _readonly_api_connection,
    "mcp_web": _readonly_mcp_connection,
    "organizer_files": _file_connection,
    "spreadsheet_evidence": _file_connection,
    "custom_rest_api": _readonly_api_connection,
    "custom_mcp": _readonly_mcp_connection,
}


def test_registration(source, definition):
    if definition.availability in {
        "adapter_required", "contract_required", "disabled",
    }:
        return _result(False, "definition_unavailable", "连接器当前不可测试")
    if getattr(definition, "source_kind", "") == "skill":
        runner = SKILL_RUNNER_REGISTRY.get(definition.adapter_key)
        if runner is None:
            return _result(False, "runner_missing", "服务器尚未注册执行器")
        try:
            runner(source=source, definition=definition, connection_test=True)
        except Exception:
            return _result(False, "runner_failed", "执行器连接测试失败")
        return _result(
            True,
            "connected",
            "连接测试通过",
            definition.capabilities,
        )
    credential = ""
    if definition.auth_type != "none":
        credential = resolve_connector_credential(
            definition.adapter_key,
            source.credential_ref,
        )
        if not credential:
            return _result(False, "credential_missing", "鉴权尚未配置")
    adapter = connector_adapter(definition.adapter_key)
    if adapter is None:
        return _result(False, "adapter_missing", "连接器适配器尚未实现")
    return adapter(source, definition, credential)
