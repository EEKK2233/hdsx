from typing import Any, Literal

from pydantic import BaseModel, Field


class InvocationMeta(BaseModel):
    trace_id: str
    capability: str
    version: str
    duration_ms: int = 0
    tools_used: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    status: Literal["success", "insufficient_evidence", "failed"]
    content: Any = None
    citations: list[dict] = Field(default_factory=list)
    meta: InvocationMeta


class CapabilitySummary(BaseModel):
    name: str
    version: str
    description: str

