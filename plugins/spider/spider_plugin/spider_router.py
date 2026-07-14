"""
spider_router.py — 爬虫 FastAPI 路由插件
========================================
本项目与前端的 Bridge 层。

设计思路：以「路由插件」形式挂载到主项目，不修改任何既有源码。

总负责人接入（只需改 main.py 加 2 行）：
    from app.spider_plugin.spider_router import spider_router
    app.include_router(spider_router, prefix=settings.api_prefix)

爬虫引擎（spider_fetcher.py）无项目依赖，可独立测试。
"""

import hashlib
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_roles
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.db.session import get_db
from app.modules.models import Course, CourseManager, Document, Status, User
from app.rag.service import KnowledgeService

from .spider_fetcher import TextCourseFetcher

logger = logging.getLogger(__name__)
router = APIRouter(tags=["spider"])

# ==================== 请求/响应 Schema ====================


class SpiderSearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200, description="搜索主题")
    max_results: int = Field(default=15, ge=1, le=30)


class SpiderSearchItem(BaseModel):
    title: str
    url: str
    platform: str


class SpiderSearchResponse(BaseModel):
    topic: str
    total: int
    results: list[SpiderSearchItem]


class SpiderFetchRequest(BaseModel):
    url: str = Field(min_length=5, max_length=2000, description="文章链接")


class SpiderFetchResponse(BaseModel):
    title: str
    url: str
    text: str
    platform: str
    length: int


class SpiderIngestRequest(BaseModel):
    course_id: int = Field(..., description="目标课程 ID")
    url: str = Field(min_length=5, max_length=2000, description="文章链接")
    topic: str = Field(
        default="", max_length=200,
        description="主题标签（用于文件名）",
    )
    category: str = Field(default="web", max_length=80)


class SpiderIngestResponse(BaseModel):
    document_id: int
    filename: str
    course_id: int
    chunks: int
    status: str  # ready|duplicate|processing
    message: str = ""


# ==================== 权限辅助 ====================


def _check_course_access(db: Session, course_id: int, user: User) -> Course:
    """校验当前用户对该课程的管理权限，复用项目已有的鉴权逻辑。"""
    course = db.get(Course, course_id)
    if not course:
        raise NotFoundError("课程")
    if user.role == "teacher":
        is_manager = db.scalar(
            select(CourseManager.id).where(
                CourseManager.course_id == course_id,
                CourseManager.user_id == user.id,
            )
        )
        if not is_manager:
            raise PermissionDeniedError("只有课程负责人可以执行此操作")
    return course


# ==================== 路由 ====================


@router.post("/spider/search", response_model=SpiderSearchResponse)
def spider_search(
    data: SpiderSearchRequest,
    _user: User = Depends(require_roles("teacher", "admin")),
):
    """
    搜索网络学习资料。
    通过 Bing 在 CSDN、博客园、掘金、知乎专栏等文本平台中搜索指定主题的资料。
    """
    try:
        fetcher = TextCourseFetcher()
        results = fetcher.search(data.topic, data.max_results)
        return SpiderSearchResponse(
            topic=data.topic,
            total=len(results),
            results=[
                SpiderSearchItem(title=r.title, url=r.url, platform=r.platform)
                for r in results
            ],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("spider/search 搜索异常")
        raise HTTPException(status_code=500, detail=f"搜索异常: {e}")


@router.post("/spider/fetch", response_model=SpiderFetchResponse)
def spider_fetch(
    data: SpiderFetchRequest,
    _user: User = Depends(require_roles("teacher", "admin")),
):
    """
    抓取指定 URL 的正文内容。
    仅返回文本预览，不写入数据库。教师可先预览再决定是否入库。
    """
    try:
        fetcher = TextCourseFetcher()
        article = fetcher.fetch(data.url)
        return SpiderFetchResponse(
            title=article.title,
            url=article.url,
            text=article.text[:50000],  # 限制预览长度
            platform=article.platform,
            length=len(article.text),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("spider/fetch 抓取异常")
        raise HTTPException(status_code=500, detail=f"抓取异常: {e}")


@router.post("/spider/ingest", response_model=SpiderIngestResponse)
async def spider_ingest(
    data: SpiderIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("teacher", "admin")),
):
    """
    抓取 URL 并直接入库到指定课程的知识库。

    等价于「在线下载 → 内容去重 → 递归分块 → Ollama 向量化 → 写入 Milvus」

    入库后的文档会出现在课程知识库列表中，与手动上传的文件完全等价，
    可以被备课、答疑、作业材料生成等所有功能复用。
    """
    # ---- 1. 校验课程管理权限 ----
    _check_course_access(db, data.course_id, user)

    # ---- 2. 抓取网页 ----
    try:
        fetcher = TextCourseFetcher()
        article = fetcher.fetch(data.url)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if len(article.text) < 50:
        raise HTTPException(
            status_code=422,
            detail="正文过短（可能需 JS 渲染或登录），请检查链接是否可访问",
        )

    # ---- 3. 构造文件名与内容哈希 ----
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", article.title)[:60] or f"web_{data.course_id}"
    filename = f"{safe_name}.md"
    content_hash = hashlib.sha256(article.text.encode()).hexdigest()

    # ---- 4. 查重：同一课程下内容相同的文件不再重复入库 ----
    existing = db.scalar(
        select(Document).where(
            Document.course_id == data.course_id,
            Document.file_hash == content_hash,
        )
    )
    if existing:
        return SpiderIngestResponse(
            document_id=existing.id,
            filename=existing.filename,
            course_id=data.course_id,
            chunks=0,
            status="duplicate",
            message=f"内容与现有文件《{existing.filename}》相同，已跳过",
        )

    # ---- 5. 创建 Document 记录（复用项目的数据模型） ----
    document = Document(
        course_id=data.course_id,
        uploader_id=user.id,
        filename=filename,
        source_path=data.url,
        category=data.category,
        mime_type="text/html",
        file_hash=content_hash,
        dedup_key=content_hash,
        status=Status.processing,
    )
    db.add(document)
    db.flush()

    # ---- 6. 递归分块 + 写入 MySQL（复用 KnowledgeService.ingest_text） ----
    try:
        service = KnowledgeService(db)
        chunk_count = service.ingest_text(document, article.text)
        db.flush()
    except Exception as e:
        db.rollback()
        logger.exception("分块失败")
        raise HTTPException(status_code=500, detail=f"文本分块失败: {e}")

    # ---- 7. 向量化：Ollama Embedding → Milvus（复用 index_document_vectors） ----
    try:
        await service.index_document_vectors(document)
    except Exception as e:
        # 向量化失败时标记为 processing，关键词检索仍可用
        document.status = Status.processing
        document.error_message = f"向量化失败: {e}"
        db.commit()
        logger.warning(f"向量化失败，文档 {document.id} 标记为 processing: {e}")
        return SpiderIngestResponse(
            document_id=document.id,
            filename=filename,
            course_id=data.course_id,
            chunks=chunk_count,
            status="processing",
            message=f"文本已入库但向量化未完成（{e}），关键词检索仍可用",
        )

    # ---- 8. 完成 ----
    document.status = Status.ready
    db.commit()
    db.refresh(document)

    return SpiderIngestResponse(
        document_id=document.id,
        filename=filename,
        course_id=data.course_id,
        chunks=chunk_count,
        status="ready",
        message=f"成功从网络抓取并入库，共 {chunk_count} 个分块",
    )
