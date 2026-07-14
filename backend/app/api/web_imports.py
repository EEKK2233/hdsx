from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.api.schemas import WebImportConfirmRequest, WebImportPreviewRequest, WebSearchRequest
from app.db.session import get_db
from app.modules.models import User, WebImportDraft
from app.services.web_imports import WebImportService

router = APIRouter(tags=["web-imports"])


def serialize(draft: WebImportDraft, include_content: bool = True) -> dict:
    value = {
        "id": draft.id, "course_id": draft.course_id, "title": draft.title,
        "source_url": draft.source_url, "resolved_url": draft.resolved_url,
        "source_domain": draft.source_domain, "content_hash": draft.content_hash,
        "status": draft.status, "fetched_at": draft.fetched_at, "expires_at": draft.expires_at,
        "confirmed_document_id": draft.confirmed_document_id, "metadata": draft.metadata_json,
    }
    if include_content:
        value["content"] = draft.content
    return value


@router.post("/courses/{course_id}/web-imports/search")
async def search_web(course_id: int, data: WebSearchRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("teacher", "admin"))):
    return await WebImportService(db, user).search(course_id, data.keyword, data.limit)


@router.post("/courses/{course_id}/web-imports/preview", status_code=201)
async def preview_web(course_id: int, data: WebImportPreviewRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("teacher", "admin"))):
    return serialize(await WebImportService(db, user).create_preview(course_id, data.url))


@router.get("/courses/{course_id}/web-imports")
def list_web_imports(course_id: int, status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles("teacher", "admin"))):
    return [serialize(item) for item in WebImportService(db, user).list_drafts(course_id, status)]


@router.post("/web-imports/{draft_id}/confirm", status_code=201)
async def confirm_web_import(draft_id: int, data: WebImportConfirmRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("teacher", "admin"))):
    draft, document, chunks = await WebImportService(db, user).confirm(draft_id, data.category)
    return {"draft": serialize(draft, False), "document": {"id": document.id, "filename": document.filename, "source_url": document.source_url, "status": document.status, "chunks": chunks}}


@router.delete("/web-imports/{draft_id}", status_code=204)
def reject_web_import(draft_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("teacher", "admin"))):
    WebImportService(db, user).reject(draft_id)
    return Response(status_code=204)
