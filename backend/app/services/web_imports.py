import hashlib
import re
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.integrations.web import WebArticleCrawler
from app.modules.models import CourseManager, Document, Status, User, WebImportDraft
from app.rag.service import KnowledgeService


class WebImportService:
    def __init__(self, db: Session, user: User):
        self.db, self.user, self.settings = db, user, get_settings()

    def ensure_manager(self, course_id: int) -> None:
        if self.user.role == "admin":
            return
        if self.user.role != "teacher" or not self.db.scalar(select(CourseManager.id).where(CourseManager.course_id == course_id, CourseManager.user_id == self.user.id)):
            raise AppError("COURSE_ACCESS_DENIED", "只有课程负责人可以抓取并确认网页资料", 403)

    async def search(self, course_id: int, keyword: str, limit: int) -> list[dict]:
        self.ensure_manager(course_id)
        return await WebArticleCrawler().search(keyword, limit)

    async def create_preview(self, course_id: int, url: str) -> WebImportDraft:
        self.ensure_manager(course_id)
        article = await WebArticleCrawler().fetch(url)
        digest = hashlib.sha256(article.text.encode("utf-8")).hexdigest()
        existing = self.db.scalar(select(Document).where(Document.course_id == course_id, Document.file_hash == digest))
        if existing:
            raise AppError("DUPLICATE_DOCUMENT", f"网页正文已存在于知识库《{existing.filename}》", 409, {"document_id": existing.id})
        draft = WebImportDraft(
            course_id=course_id, creator_id=self.user.id, source_url=article.source_url,
            resolved_url=article.resolved_url, source_domain=urlparse(article.resolved_url).hostname or "",
            title=article.title, content=article.text, content_hash=digest,
            expires_at=datetime.utcnow() + timedelta(hours=self.settings.web_import_expire_hours),
            metadata_json={"content_type": article.content_type, "character_count": len(article.text), "confirmation_required": True},
        )
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def list_drafts(self, course_id: int, status: str | None = None) -> list[WebImportDraft]:
        self.ensure_manager(course_id)
        now = datetime.utcnow()
        expired = list(self.db.scalars(select(WebImportDraft).where(WebImportDraft.course_id == course_id, WebImportDraft.status == "pending", WebImportDraft.expires_at <= now)))
        for item in expired:
            item.status = "expired"
        if expired:
            self.db.commit()
        stmt = select(WebImportDraft).where(WebImportDraft.course_id == course_id)
        if status:
            stmt = stmt.where(WebImportDraft.status == status)
        return list(self.db.scalars(stmt.order_by(WebImportDraft.created_at.desc()).limit(100)))

    async def confirm(self, draft_id: int, category: str = "web_reference") -> tuple[WebImportDraft, Document, int]:
        draft = self.db.get(WebImportDraft, draft_id)
        if not draft:
            raise AppError("WEB_DRAFT_NOT_FOUND", "网页抓取草稿不存在", 404)
        self.ensure_manager(draft.course_id)
        if draft.status != "pending" or draft.expires_at <= datetime.utcnow():
            raise AppError("WEB_DRAFT_NOT_PENDING", "该网页草稿已处理或过期，请重新抓取", 409)
        duplicate = self.db.scalar(select(Document).where(Document.course_id == draft.course_id, Document.file_hash == draft.content_hash))
        if duplicate:
            raise AppError("DUPLICATE_DOCUMENT", f"网页正文已存在于知识库《{duplicate.filename}》", 409, {"document_id": duplicate.id})
        safe = re.sub(r'[\\/*?:"<>|]', "_", draft.title).strip(" .")[:100] or "网页学习资料"
        filename = f"{safe}.md"
        markdown = f"# {draft.title}\n\n> 来源：{draft.resolved_url}\n> 抓取时间：{draft.fetched_at.isoformat()}\n\n---\n\n{draft.content}\n"
        target_dir = self.settings.storage_root / "uploads" / str(draft.course_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid.uuid4().hex}_{filename}"
        document = None
        try:
            target.write_text(markdown, encoding="utf-8")
            document = Document(
                course_id=draft.course_id, uploader_id=self.user.id, filename=filename,
                source_path=str(target.resolve()), source_url=draft.resolved_url, category=category,
                mime_type="text/markdown", file_hash=draft.content_hash, dedup_key=draft.content_hash,
            )
            self.db.add(document)
            self.db.flush()
            service = KnowledgeService(self.db)
            count = service.ingest_text(document, markdown)
            self.db.flush()
            await service.index_document_vectors(document)
            document.status = Status.ready
            draft.status = "confirmed"
            draft.confirmed_document_id = document.id
            self.db.commit()
            self.db.refresh(document)
            self.db.refresh(draft)
            return draft, document, count
        except IntegrityError as exc:
            self.db.rollback()
            target.unlink(missing_ok=True)
            raise AppError("DUPLICATE_DOCUMENT", "相同网页内容已被其他请求确认入库", 409) from exc
        except Exception:
            self.db.rollback()
            target.unlink(missing_ok=True)
            raise

    def delete_draft(self, draft_id: int) -> None:
        draft = self.db.get(WebImportDraft, draft_id)
        if not draft:
            raise AppError("WEB_DRAFT_NOT_FOUND", "网页抓取草稿不存在", 404)
        self.ensure_manager(draft.course_id)
        self.db.delete(draft)
        self.db.commit()
