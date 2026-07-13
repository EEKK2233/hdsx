from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError


class MCPHttpClient:
    """受主机白名单限制的 JSON-RPC MCP HTTP 客户端。默认禁用远端调用。"""

    def __init__(self, endpoint: str):
        settings = get_settings()
        host = urlparse(endpoint).hostname or ""
        allowed = {item.strip() for item in settings.mcp_allowed_hosts.split(",") if item.strip()}
        if not settings.mcp_remote_enabled or host not in allowed:
            raise AppError("MCP_REMOTE_DISABLED", "远端 MCP 未启用或主机不在白名单", 403)
        self.endpoint = endpoint
        self.protocol_version = "2025-11-25"

    async def request(self, method: str, params: dict | None = None) -> dict:
        payload = {"jsonrpc":"2.0","id":"edu-agent","method":method,"params":params or {}}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                headers = {} if method == "initialize" else {"MCP-Protocol-Version": self.protocol_version}
                response = await client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError("MCP_REMOTE_UNAVAILABLE", f"远端 MCP 调用失败：{exc}", 503) from exc
        if "error" in data:
            raise AppError("MCP_REMOTE_ERROR", str(data["error"].get("message", "MCP 调用失败")), 502)
        return data.get("result", {})
