from app.rag.types import RetrievedChunk


def rrf_fusion(result_lists: list[list[RetrievedChunk]], k: int = 60) -> list[RetrievedChunk]:
    merged: dict[int, RetrievedChunk] = {}
    scores: dict[int, float] = {}
    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            merged[item.chunk_id] = item
            scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1.0 / (k + rank)
    for chunk_id, item in merged.items():
        item.score = scores[chunk_id]
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)

