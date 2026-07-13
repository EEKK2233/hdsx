import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.db.session import get_db
from app.mcp.server import InternalMCPServer
from app.modules.models import User
from app.prompts.registry import get_prompt_registry
from app.skills.registry import get_skill_registry
from app.tools.contracts import ToolContext
from app.tools.registry import get_tool_registry

router = APIRouter(tags=["agent-capabilities"])


@router.get("/agent-capabilities")
def list_capabilities(_: User = Depends(require_roles("admin"))):
    prompts = get_prompt_registry().list()
    skills = get_skill_registry().list()
    tools = get_tool_registry().list()
    return {
        "skills": [{"name": x.name, "version": x.version, "description": x.description, "prompt": x.prompt, "allowed_tools": x.allowed_tools, "input_schema": x.input_schema, "output_schema": x.output_schema} for x in skills],
        "prompts": [{"name": x.name, "version": x.version, "description": x.description, "output_mode": x.output_mode, "variables": x.variables} for x in prompts],
        "tools": [x.model_dump() for x in tools],
        "mcp": {"enabled": True, "protocol_versions": ["2025-11-25", "2025-06-18"], "transport": "authenticated-json-rpc", "methods": ["initialize", "ping", "tools/list", "tools/call"], "remote_default": "disabled"},
    }


@router.post("/mcp")
async def internal_mcp(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    context = ToolContext(db=db, user=user, trace_id=uuid.uuid4().hex)
    return await InternalMCPServer().handle(payload, context)
