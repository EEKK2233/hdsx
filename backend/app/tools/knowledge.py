from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.models import CourseManager, CourseMember, Document, DocumentChunk
from app.rag.service import KnowledgeService
from app.tools.contracts import ToolContext


def _ensure_course_access(context: ToolContext, course_id: int) -> None:
    user = context.user
    if user.role == "admin":
        return
    if user.role == "teacher":
        allowed = context.db.scalar(select(CourseManager.id).where(CourseManager.course_id == course_id, CourseManager.user_id == user.id))
    elif user.role == "student":
        allowed = context.db.scalar(select(CourseMember.id).where(CourseMember.course_id == course_id, CourseMember.student_id == user.id, CourseMember.status == "active"))
    else:
        allowed = None
    if not allowed:
        raise AppError("COURSE_ACCESS_DENIED", "无权调用该课程的知识工具", 403)


async def search_course_knowledge(context: ToolContext, arguments: dict) -> list[dict]:
    course_id, query = int(arguments["course_id"]), str(arguments["query"]).strip()
    _ensure_course_access(context, course_id)
    chunks = await KnowledgeService(context.db).hybrid_search(course_id, query, min(int(arguments.get("top_k", 8)), 20))
    return [{"chunk_id": c.chunk_id, "document_id": c.document_id, "filename": c.filename, "content": c.content, "score": c.rerank_score if c.rerank_score is not None else c.score} for c in chunks]


async def get_course_context(context: ToolContext, arguments: dict) -> list[dict]:
    course_id = int(arguments["course_id"])
    _ensure_course_access(context, course_id)
    chunks = KnowledgeService(context.db).course_context(course_id, min(int(arguments.get("top_k", 8)), 20))
    return [{"chunk_id": c.chunk_id, "document_id": c.document_id, "filename": c.filename, "content": c.content} for c in chunks]


async def get_document_context(context: ToolContext, arguments: dict) -> list[dict]:
    course_id = int(arguments["course_id"])
    _ensure_course_access(context, course_id)
    document_ids = [int(value) for value in arguments.get("document_ids", [])]
    if not document_ids:
        raise AppError("DOCUMENT_REQUIRED", "至少选择一份参考资料", 422)
    rows = context.db.execute(
        select(DocumentChunk, Document).join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.course_id == course_id, Document.id.in_(document_ids), Document.status == "ready")
        .order_by(Document.id, DocumentChunk.chunk_index).limit(80)
    ).all()
    found = {document.id for _, document in rows}
    if found != set(document_ids):
        raise AppError("DOCUMENT_ACCESS_DENIED", "部分资料不存在、未就绪或不属于当前课程", 403)
    return [{"chunk_id": chunk.id, "document_id": document.id, "filename": document.filename, "content": chunk.content} for chunk, document in rows]

