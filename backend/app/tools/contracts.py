from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.models import User


@dataclass(slots=True)
class ToolContext:
    db: Session
    user: User
    trace_id: str


ToolHandler = Callable[[ToolContext, dict[str, Any]], Awaitable[Any]]


class ToolDefinition(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str
    input_schema: dict
    read_only: bool = True

