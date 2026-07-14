import asyncio
from types import SimpleNamespace
from app.agents.structured import GradingOutput, ParentReportOutput, validate_or_fallback
from app.services import agents


def test_contract_fallback_is_always_valid():
    value = validate_or_fallback(
        "不是 JSON", GradingOutput,
        lambda: GradingOutput(score=1, confidence=.2, feedback="待教师复核"),
    )
    assert value.model_dump() == {"score": 1.0, "confidence": .2, "feedback": "待教师复核", "evidence": []}


def test_grading_invalid_model_output_uses_deterministic_fallback(monkeypatch):
    async def fake_run(*args, **kwargs):
        return SimpleNamespace(content="score: 五分，格式坏了")
    monkeypatch.setattr(agents.GradingAgent, "run", fake_run)
    question = SimpleNamespace(standard_answer="监督学习需要标签数据", rubric_json=[], max_score=10)
    result = asyncio.run(agents.grade_subjective(question, "需要标签数据", "监督学习资料"))
    assert 0 <= result["score"] <= 10
    assert 0 <= result["confidence"] <= 1
    assert result["feedback"]


def test_assignment_invalid_model_output_returns_requested_valid_items(monkeypatch):
    async def fake_run(*args, **kwargs):
        return SimpleNamespace(content="{broken")
    monkeypatch.setattr(agents.AssignmentAgent, "run", fake_run)
    request = SimpleNamespace(chapter_or_topic="线性回归", example_count=1, exercise_count=2, thinking_count=1, extension_count=0)
    document = SimpleNamespace(id=1, filename="教材.md")
    chunk = SimpleNamespace(document_id=1, content="线性回归通过最小化均方误差拟合参数。")
    items = asyncio.run(agents.generate_assignment_materials([document], [chunk], request))
    assert len(items) == 4
    assert all(item["stem"] and item["standard_answer"] for item in items)


def test_report_invalid_model_output_is_parent_friendly(monkeypatch):
    async def fake_run(*args, **kwargs):
        return SimpleNamespace(content="完全不符合格式")
    monkeypatch.setattr(agents.ReportAgent, "run", fake_run)
    result = asyncio.run(agents.generate_parent_report({"average_mastery": .72, "weak_points": [1, 2]}))
    validated = ParentReportOutput.model_validate(result)
    assert "72%" in validated.overview
    assert validated.action_plan
