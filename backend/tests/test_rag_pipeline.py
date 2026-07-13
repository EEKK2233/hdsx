from app.rag.context_builder import ContextBuilder
from app.rag.retrieval.deduplicator import deduplicate
from app.rag.types import RetrievedChunk


def make_chunk(chunk_id: int, document_id: int = 1, index: int = 0):
    return RetrievedChunk(chunk_id, document_id, f"正文{chunk_id}", "教材.txt", index, "textbook")


def test_deduplicator_uses_document_and_chunk_index():
    assert [item.chunk_id for item in deduplicate([make_chunk(1), make_chunk(2), make_chunk(3, index=1)])] == [1, 3]


def test_context_builder_contains_traceable_source():
    context = ContextBuilder().build([make_chunk(7)])
    assert "资料1" in context and "chunk_id=7" in context and "教材.txt" in context

