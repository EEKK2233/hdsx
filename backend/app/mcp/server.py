from typing import Any
import json

from app.core.exceptions import AppError
from app.tools.contracts import ToolContext
from app.tools.registry import get_tool_registry


class InternalMCPServer:
    """面向站内管理员的 MCP JSON-RPC 子集，仅暴露注册工具。"""

    async def handle(self, payload: dict[str, Any], context: ToolContext) -> dict:
        request_id, method = payload.get("id"), payload.get("method")
        try:
            if method == "initialize":
                requested = (payload.get("params") or {}).get("protocolVersion")
                supported = ("2025-11-25", "2025-06-18")
                version = requested if requested in supported else supported[0]
                result = {"protocolVersion":version,"serverInfo":{"name":"ai-education-agent","title":"AI 教育智能体安全工具网关","version":"1.0.0"},"capabilities":{"tools":{"listChanged":False}},"instructions":"仅调用当前账号有权访问课程的只读工具。"}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools":[{"name": item.name, "description": item.description, "inputSchema": item.input_schema} for item in get_tool_registry().list()]}
            elif method == "tools/call":
                params = payload.get("params") or {}
                try:
                    value = await get_tool_registry().call(params.get("name", ""), context, params.get("arguments") or {})
                    result = {"content":[{"type":"text","text":json.dumps(value, ensure_ascii=False, default=str)}],"structuredContent":{"result":value},"isError":False}
                except AppError as exc:
                    if exc.code == "TOOL_NOT_ALLOWED":
                        raise
                    result = {"content":[{"type":"text","text":exc.message}],"structuredContent":{"error":{"code":exc.code,"details":exc.details}},"isError":True}
            else:
                return {"jsonrpc":"2.0","id":request_id,"error":{"code":-32601,"message":"不支持的 MCP 方法"}}
            return {"jsonrpc":"2.0","id":request_id,"result":result}
        except Exception as exc:
            return {"jsonrpc":"2.0","id":request_id,"error":{"code":-32000,"message":str(exc)}}
