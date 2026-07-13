from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.models import Assignment, Question
from app.tools.contracts import ToolContext
from app.tools.knowledge import _ensure_course_access


async def get_assignment_rubric(context: ToolContext, arguments: dict) -> list[dict]:
    assignment = context.db.get(Assignment, int(arguments["assignment_id"]))
    if not assignment:
        raise AppError("ASSIGNMENT_NOT_FOUND", "作业不存在", 404)
    _ensure_course_access(context, assignment.course_id)
    questions = context.db.scalars(select(Question).where(Question.assignment_id == assignment.id).order_by(Question.sort_order))
    return [{"question_id": item.id, "question_type": item.question_type, "stem": item.stem, "standard_answer": item.standard_answer, "rubric": item.rubric_json, "max_score": float(item.max_score)} for item in questions]
