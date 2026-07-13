from app.rag.types import RetrievedChunk


def deduplicate(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[tuple[int, int]] = set()
    output = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.chunk_index)
        if key not in seen:
            seen.add(key)
            output.append(chunk)
    return output

