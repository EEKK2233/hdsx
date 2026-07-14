import hashlib
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.milvus import MilvusIndex
from app.integrations.ollama import OllamaClient
from app.modules.models import Document, DocumentChunk, Status
from app.rag.splitter import RecursiveTextSplitter
from app.rag.types import RagAnswer, RetrievedChunk
from app.agents.tutor import TutorAgent
from app.rag.citation import build_citations
from app.rag.context_builder import ContextBuilder
from app.rag.pipeline import RetrievalPipeline
from app.rag.retrieval.fusion import rrf_fusion
from app.services.web_supplement import WebSupplementService


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def ingest_text(self, document: Document, content: str) -> int:
        splitter = RecursiveTextSplitter(
            self.settings.rag_chunk_size, self.settings.rag_chunk_overlap
        )
        chunks = splitter.split(
            content,
            {
                "source": document.source_url or document.source_path,
                "filename": document.filename,
                "category": document.category,
                "course_id": document.course_id,
            },
        )
        for chunk in chunks:
            self.db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    content_hash=hashlib.sha256(chunk.content.encode()).hexdigest(),
                    metadata_json=chunk.metadata,
                )
            )
        return len(chunks)

    async def index_document_vectors(self, document: Document) -> int:
        chunks = list(self.db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document.id)))
        if not chunks:
            return 0
        embeddings = await OllamaClient().embed([chunk.content for chunk in chunks])
        if any(len(vector) != 768 for vector in embeddings):
            raise ValueError("embeddinggemma 向量维度不是预期的 768")
        MilvusIndex().upsert([
            {
                "chunk_id": chunk.id, "course_id": document.course_id,
                "document_id": document.id, "category": document.category,
                "content_hash": chunk.content_hash, "embedding": vector,
            }
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ])
        for chunk in chunks:
            chunk.milvus_id = str(chunk.id)
        return len(chunks)

    def keyword_search(self, course_id: int, query: str, top_k: int = 20) -> list[RetrievedChunk]:
        # BOOLEAN MODE 对中文分词能力有限，首版同时提供 LIKE 兜底；检索适配层可替换为 ES。
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.course_id == course_id, Document.status == Status.ready, DocumentChunk.content.contains(query))
            .limit(top_k)
        )
        rows = self.db.execute(stmt).all()
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                content=chunk.content,
                filename=doc.filename,
                chunk_index=chunk.chunk_index,
                category=doc.category,
                score=1.0 / (index + 1),
                source_url=doc.source_url,
            )
            for index, (chunk, doc) in enumerate(rows)
        ]

    def course_context(self, course_id: int, top_k: int = 20) -> list[RetrievedChunk]:
        """Return representative ready chunks when a lesson topic is not a literal text match."""
        rows = self.db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.course_id == course_id, Document.status == "ready")
            .order_by(Document.id.desc(), DocumentChunk.chunk_index)
            .limit(top_k)
        ).all()
        return [
            RetrievedChunk(
                chunk_id=chunk.id, document_id=doc.id, content=chunk.content,
                filename=doc.filename, chunk_index=chunk.chunk_index,
                category=doc.category, score=1.0 / (index + 1),
                source_url=doc.source_url,
            )
            for index, (chunk, doc) in enumerate(rows)
        ]

    async def vector_search(self, course_id: int, query: str, top_k: int = 20) -> list[RetrievedChunk]:
        embedding = (await OllamaClient().embed([query]))[0]
        hits = MilvusIndex().search(embedding, course_id, top_k)
        if not hits:
            return []
        score_map = dict(hits)
        rows = self.db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.id.in_(score_map), Document.status == Status.ready)
        ).all()
        values = [
            RetrievedChunk(
                chunk_id=chunk.id, document_id=doc.id, content=chunk.content,
                filename=doc.filename, chunk_index=chunk.chunk_index, category=doc.category,
                score=score_map[chunk.id],
                source_url=doc.source_url,
            ) for chunk, doc in rows
        ]
        return sorted(values, key=lambda item: item.score, reverse=True)

    @staticmethod
    def rrf_fusion(result_lists: list[list[RetrievedChunk]], k: int = 60) -> list[RetrievedChunk]:
        return rrf_fusion(result_lists, k)

    async def hybrid_search(self, course_id: int, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or self.settings.rag_rerank_top_k
        keyword = self.keyword_search(course_id, query, self.settings.rag_keyword_top_k)
        try:
            vector = await self.vector_search(course_id, query, self.settings.rag_vector_top_k)
        except Exception:
            # 关键词检索仍可提供有依据结果；向量故障由健康检查暴露。
            vector = []
        return RetrievalPipeline().rank(query, [vector, keyword], top_k)

    async def answer(self, course_id: int, query: str) -> RagAnswer:
        trace_id = uuid.uuid4().hex
        chunks = await self.hybrid_search(course_id, query, self.settings.rag_rerank_top_k)
        web = await WebSupplementService().collect(query) if len(chunks) < 2 else None
        if not chunks and not (web and web.context):
            return RagAnswer(
                answer="当前课程知识库中没有找到足够依据，请补充资料或转交教师。",
                insufficient_evidence=True,
                trace_id=trace_id,
            )
        context_parts = [ContextBuilder().build(chunks)] if chunks else []
        tools_used = ["search_course_knowledge"]
        citations = build_citations(chunks)
        if web and web.context:
            context_parts.append(web.context)
            citations.extend(web.citations)
            tools_used.append("search_web_knowledge")
        result = await TutorAgent().run(
            {"query": query, "context": "\n\n".join(context_parts)}, tools_used=tools_used,
        )
        confidence = 0.75 if chunks and not web else (0.68 if chunks else 0.58)
        return RagAnswer(answer=str(result.content), citations=citations, confidence=confidence, trace_id=result.meta.trace_id)
