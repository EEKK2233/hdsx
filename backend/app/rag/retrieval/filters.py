from app.rag.types import RetrievedChunk


def positive_evidence(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """丢弃重排器明确判定为负相关的片段，未启用重排器时保留融合结果。"""
    return [item for item in chunks if item.rerank_score is None or item.rerank_score > 0]


def diverse_evidence(chunks: list[RetrievedChunk], per_document: int = 3) -> list[RetrievedChunk]:
    """过滤过短片段，并限制单一文件占满结果列表。"""
    counts: dict[int, int] = {}
    selected: list[RetrievedChunk] = []
    for item in chunks:
        if len(item.content.strip()) < 20 or counts.get(item.document_id, 0) >= per_document:
            continue
        selected.append(item)
        counts[item.document_id] = counts.get(item.document_id, 0) + 1
    return selected
