from types import SimpleNamespace

from app.api import router as router_module


class FakeDB:
    def __init__(self, document, chunks):
        self.document = document
        self.chunks = chunks

    def get(self, model, document_id):
        return self.document if self.document.id == document_id else None

    def scalars(self, statement):
        return self.chunks


def test_document_preview_reassembles_chunks_and_marks_markdown(monkeypatch):
    monkeypatch.setattr(router_module, "visible_course", lambda *args: None)
    document = SimpleNamespace(id=7, course_id=3, status="ready", filename="chapter.md", mime_type="text/markdown", category="textbook", source_url=None)
    chunks = [SimpleNamespace(content="# 标题"), SimpleNamespace(content="正文内容")]
    result = router_module.preview_document(3, 7, FakeDB(document, chunks), SimpleNamespace(id=1))
    assert result["format"] == "markdown"
    assert result["content"] == "# 标题\n\n正文内容"
    assert result["chunks"] == 2
    assert result["truncated"] is False


def test_document_preview_removes_splitter_overlap(monkeypatch):
    monkeypatch.setattr(router_module, "visible_course", lambda *args: None)
    document = SimpleNamespace(id=8, course_id=3, status="ready", filename="note.txt", mime_type="text/plain", category="textbook", source_url=None)
    repeated = "这是需要去重的重叠内容一共超过二十个字符。"
    chunks = [SimpleNamespace(content="第一段。" + repeated), SimpleNamespace(content=repeated + "第二段。")]
    result = router_module.preview_document(3, 8, FakeDB(document, chunks), SimpleNamespace(id=1))
    assert result["content"].count(repeated) == 1
    assert result["format"] == "text"
