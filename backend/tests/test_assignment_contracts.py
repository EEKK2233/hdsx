from app.api.router import _answer_tokens, normalized_question_options
from app.api.schemas import AssignmentMaterialGenerate, QASessionUpdate
from app.services.agents import _load_model_json


def test_model_json_accepts_code_fence_and_embedded_text():
    assert _load_model_json('```json\n{"items": []}\n```') == {"items": []}
    assert _load_model_json('生成结果如下：[{"stem":"题目"}]。') == [{"stem": "题目"}]


def test_multiple_choice_answer_is_order_independent():
    assert _answer_tokens(["B", "A"]) == _answer_tokens("A,B")
    assert _answer_tokens("A，B") != _answer_tokens("A")


def test_true_false_options_are_always_available():
    assert normalized_question_options("true_false", None) == [
        {"key": "true", "content": "正确"},
        {"key": "false", "content": "错误"},
    ]


def test_assignment_material_accepts_multiple_documents():
    request = AssignmentMaterialGenerate(document_ids=[3, 5], chapter_or_topic="第一章")
    assert request.document_ids == [3, 5]


def test_qa_session_title_can_be_renamed():
    assert QASessionUpdate(title="  第一章复习  ").title.strip() == "第一章复习"
