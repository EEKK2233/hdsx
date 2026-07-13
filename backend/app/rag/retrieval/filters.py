from app.rag.types import RetrievedChunk


def positive_evidence(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """丢弃重排器明确判定为负相关的片段，未启用重排器时保留融合结果。"""
    return [item for item in chunks if item.rerank_score is None or item.rerank_score > 0]

