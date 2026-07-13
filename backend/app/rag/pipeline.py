from app.integrations.reranker import BGEReranker
from app.rag.retrieval.deduplicator import deduplicate
from app.rag.retrieval.filters import positive_evidence
from app.rag.retrieval.fusion import rrf_fusion
from app.rag.types import RetrievedChunk


class RetrievalPipeline:
    """融合、去重、重排和证据过滤的可测试流水线。"""

    def rank(self, query: str, result_lists: list[list[RetrievedChunk]], top_k: int) -> list[RetrievedChunk]:
        candidates = deduplicate(rrf_fusion(result_lists))
        if not candidates:
            return []
        rerank_candidates = candidates[:30]
        scores = BGEReranker().score(query, [item.content for item in rerank_candidates])
        for item, score in zip(rerank_candidates, scores, strict=True):
            item.rerank_score = score
        rerank_candidates.sort(key=lambda item: item.rerank_score if item.rerank_score is not None else item.score, reverse=True)
        return positive_evidence(rerank_candidates)[:top_k]

