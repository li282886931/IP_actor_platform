"""Bounded, read-only API and MCP Streamable HTTP adapters."""
import ipaddress
import json
import os
import re
import socket
import time
from urllib.parse import urlsplit

import requests

from app.integrations.connectors import credential_environment_name
from app.integrations.llm import sanitize_ai_output

MAX_BYTES = 262144


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Invalid HTTP address")
    return f"{parsed.scheme}://{parsed.hostname.lower()}" + (
        f":{parsed.port}" if parsed.port and parsed.port != (443 if parsed.scheme == "https" else 80) else "")


def validate_public_host(url):
    origin(url)
    parsed = urlsplit(url)
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError("Non-public webpage address")


def validate_endpoint(url):
    allowed = {origin(value.strip()) for value in os.environ.get("ANALYSIS_ALLOWED_ORIGINS", "").split(",") if value.strip()}
    if origin(url) not in allowed or urlsplit(url).query or urlsplit(url).fragment:
        raise ValueError("Endpoint is not configured in the allowlist")
    # Local MCP/API services require an explicit operator-controlled allowlist above.


def request_json(method, url, **kwargs):
    """Read JSON or the matching JSON-RPC SSE result without waiting for stream closure."""
    session = requests.Session()
    session.trust_env = False
    response = None
    try:
        response = session.request(method, url, timeout=kwargs.pop("timeout", 10),
                                   allow_redirects=False, stream=True, **kwargs)
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise ValueError("Redirects are not allowed")
        headers = dict(response.headers)
        if response.status_code in {202, 204}:
            return None, headers
        is_sse = "text/event-stream" in response.headers.get("Content-Type", "")
        raw = bytearray()
        buffer = b""
        expected_id = (kwargs.get("json") or {}).get("id")
        started = time.monotonic()
        # SSE may remain open after a small result; do not wait for a full block.
        for chunk in response.iter_content(chunk_size=1 if is_sse else 4096):
            if time.monotonic() - started > 20:
                raise ValueError("Response exceeded time limit")
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise ValueError("Response exceeded size limit")
            if is_sse:
                buffer += chunk
                buffer = buffer.replace(b"\r\n", b"\n")
                while b"\n\n" in buffer:
                    event, buffer = buffer.split(b"\n\n", 1)
                    lines = [line[5:].lstrip() for line in event.split(b"\n") if line.startswith(b"data:")]
                    if not lines:
                        continue
                    message = json.loads(b"\n".join(lines).decode("utf-8"))
                    if isinstance(message, dict) and message.get("id") == expected_id and ("result" in message or "error" in message):
                        return message, headers
        if is_sse:
            raise ValueError("MCP response was incomplete")
        return json.loads(raw.decode("utf-8")), headers
    finally:
        if response is not None:
            response.close()
        session.close()


def redact(value, credential=""):
    if isinstance(value, dict):
        return {k: redact(v, credential) for k, v in value.items()
                if not re.search(r"token|secret|password|authorization|api.?key|credential|cookie", str(k), re.I)}
    if isinstance(value, list):
        return [redact(v, credential) for v in value]
    if isinstance(value, str):
        text = value.replace(credential, "[已隐藏]") if credential else value
        return sanitize_ai_output(text)
    return value


def read_source(source, project, page_url=None):
    config = source.scope_config or {}
    endpoint = config.get("endpoint", "")
    validate_endpoint(endpoint)
    credential = os.environ.get(credential_environment_name(source.credential_ref), "").strip() if source.credential_ref else ""
    if source.credential_ref and not credential:
        raise ValueError("Credential is not configured")
    headers = {"Authorization": f"Bearer {credential}"} if credential else {}
    if source.connector_key == "agent_api":
        query = {}
        values = {"project_id": str(project.id), "city": project.city or "", "artist_name": project.artist_name or ""}
        for key, value in (config.get("query") or {}).items():
            if re.search(r"token|secret|password|key|authorization", key, re.I):
                raise ValueError("Secrets must be supplied through credential_ref")
            text = str(value)
            for name, replacement in values.items():
                text = text.replace("{" + name + "}", replacement)
            query[key] = text
        payload, _ = request_json("GET", endpoint, headers=headers, params=query)
        return redact(payload, credential), endpoint
    if source.connector_key != "mcp_web" or not page_url:
        raise ValueError("MCP webpage URL is required")
    validate_public_host(page_url)
    headers.update({"Accept": "application/json, text/event-stream", "Content-Type": "application/json"})
    started = time.monotonic()
    counter = 0

    def rpc(method, params=None, notification=False):
        nonlocal counter
        remaining = 30 - (time.monotonic() - started)
        if remaining <= 0:
            raise ValueError("MCP request exceeded time limit")
        body = {"jsonrpc": "2.0", "method": method}
        if not notification:
            counter += 1
            body["id"] = counter
        if params is not None:
            body["params"] = params
        reply, response_headers = request_json("POST", endpoint, json=body, headers=headers,
                                              timeout=min(10, remaining))
        session_id = response_headers.get("Mcp-Session-Id") or response_headers.get("mcp-session-id")
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        if notification:
            return {}
        if not isinstance(reply, dict) or reply.get("id") != counter or "error" in reply:
            raise ValueError("MCP protocol request failed")
        return reply.get("result") or {}

    initialized = rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                     "clientInfo": {"name": "starhub-analysis", "version": "1.0"}})
    if initialized.get("protocolVersion") not in {"2025-03-26", "2025-06-18", "2025-11-25"}:
        raise ValueError("MCP protocol version is not supported")
    headers["MCP-Protocol-Version"] = initialized["protocolVersion"]
    rpc("notifications/initialized", notification=True)
    tool_name = config.get("tool")
    tools = rpc("tools/list").get("tools") or []
    tool = next((item for item in tools if item.get("name") == tool_name), None)
    if not tool or (tool.get("annotations") or {}).get("readOnlyHint") is False:
        raise ValueError("Configured read-only MCP tool is unavailable")
    result = rpc("tools/call", {"name": tool_name, "arguments": {config.get("url_argument", "url"): page_url}})
    if result.get("isError"):
        raise ValueError("MCP tool execution failed")
    content = "\n".join(part.get("text", "") for part in result.get("content", []) if part.get("type") == "text")
    if not content:
        raise ValueError("MCP tool returned no text")
    return redact({"text": content}, credential), page_url
