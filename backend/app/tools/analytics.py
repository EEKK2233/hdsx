from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.models import CourseMember, KnowledgePoint, MasterySnapshot
from app.tools.contracts import ToolContext
from app.tools.knowledge import _ensure_course_access


async def get_student_mastery_summary(context: ToolContext, arguments: dict) -> dict:
    course_id, student_id = int(arguments["course_id"]), int(arguments["student_id"])
    _ensure_course_access(context, course_id)
    if context.user.role == "student" and context.user.id != student_id:
        raise AppError("STUDENT_DATA_DENIED", "学生只能读取本人学情", 403)
    if context.user.role != "admin" and not context.db.scalar(
        select(CourseMember.id).where(CourseMember.course_id == course_id, CourseMember.student_id == student_id, CourseMember.status == "active")
    ):
        raise AppError("STUDENT_DATA_DENIED", "该学生不是当前课程的正式成员", 403)
    rows = context.db.execute(
        select(MasterySnapshot, KnowledgePoint).join(KnowledgePoint, KnowledgePoint.id == MasterySnapshot.knowledge_point_id)
        .where(MasterySnapshot.student_id == student_id, KnowledgePoint.course_id == course_id)
        .order_by(MasterySnapshot.updated_at.desc())
    ).all()
    latest: dict[int, tuple] = {}
    for snapshot, point in rows:
        latest.setdefault(point.id, (snapshot, point))
    values = [{"knowledge_point_id": point.id, "name": point.name, "score": snapshot.score, "level": snapshot.level} for snapshot, point in latest.values()]
    return {"student_id": student_id, "course_id": course_id, "average": round(sum(item["score"] for item in values) / len(values), 3) if values else 0, "items": values}
