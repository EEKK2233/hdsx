from app.rag.types import RetrievedChunk


def build_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    return [{"chunk_id": item.chunk_id, "document_id": item.document_id, "filename": item.filename, "chunk_index": item.chunk_index, "source_url": item.source_url} for item in chunks]
