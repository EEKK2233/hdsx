from app.rag.types import RetrievedChunk


class ContextBuilder:
    def build(self, chunks: list[RetrievedChunk], max_chars: int = 24000) -> str:
        sections, used = [], 0
        for index, chunk in enumerate(chunks, start=1):
            section = f"[资料{index}|chunk_id={chunk.chunk_id}|{chunk.filename}]\n{chunk.content}"
            if sections and used + len(section) > max_chars:
                break
            sections.append(section)
            used += len(section)
        return "\n\n".join(sections)

