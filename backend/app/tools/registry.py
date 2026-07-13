import inspect
from functools import lru_cache
from typing import Any

from app.core.exceptions import AppError
from app.tools.contracts import ToolContext, ToolDefinition, ToolHandler
from app.tools.knowledge import get_course_context, get_document_context, search_course_knowledge
from app.tools.assignment import get_assignment_rubric
from app.tools.analytics import get_student_mastery_summary


class ToolRegistry:
    def __init__(self):
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"重复 Tool：{definition.name}")
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def list(self) -> list[ToolDefinition]:
        return sorted(self._definitions.values(), key=lambda item: item.name)

    def get(self, name: str) -> ToolDefinition:
        if name not in self._definitions:
            raise AppError("TOOL_NOT_ALLOWED", f"工具未注册或不在白名单：{name}", 403)
        return self._definitions[name]

    async def call(self, name: str, context: ToolContext, arguments: dict[str, Any]) -> Any:
        definition = self.get(name)
        required = definition.input_schema.get("required", [])
        missing = [key for key in required if key not in arguments]
        if missing:
            raise AppError("TOOL_ARGUMENT_INVALID", f"工具 {name} 缺少参数：{missing}", 422)
        result = self._handlers[name](context, arguments)
        return await result if inspect.isawaitable(result) else result


@lru_cache
def get_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="search_course_knowledge", description="混合检索当前用户有权访问的课程知识库", input_schema={"type":"object","properties":{"course_id":{"type":"integer"},"query":{"type":"string"},"top_k":{"type":"integer"}},"required":["course_id","query"]}), search_course_knowledge)
    registry.register(ToolDefinition(name="get_course_context", description="读取当前课程的代表性证据片段", input_schema={"type":"object","properties":{"course_id":{"type":"integer"},"top_k":{"type":"integer"}},"required":["course_id"]}), get_course_context)
    registry.register(ToolDefinition(name="get_document_context", description="读取教师明确选择的一个或多个课程文件片段", input_schema={"type":"object","properties":{"course_id":{"type":"integer"},"document_ids":{"type":"array","items":{"type":"integer"}}},"required":["course_id","document_ids"]}), get_document_context)
    registry.register(ToolDefinition(name="get_assignment_rubric", description="读取有权课程作业的题目、标准答案和评分点", input_schema={"type":"object","properties":{"assignment_id":{"type":"integer"}},"required":["assignment_id"]}), get_assignment_rubric)
    registry.register(ToolDefinition(name="get_student_mastery_summary", description="读取权限范围内学生的课程掌握度摘要", input_schema={"type":"object","properties":{"course_id":{"type":"integer"},"student_id":{"type":"integer"}},"required":["course_id","student_id"]}), get_student_mastery_summary)
    return registry
