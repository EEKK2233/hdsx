from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.analytics import build_course_learning_analysis


def test_analysis_counts_completed_missing_and_qa():
    assignments = [
        SimpleNamespace(id=1, title="作业一", total_score=100, due_at=datetime.utcnow()-timedelta(days=1)),
        SimpleNamespace(id=2, title="作业二", total_score=100, due_at=datetime.utcnow()-timedelta(hours=1)),
    ]
    submissions = [SimpleNamespace(assignment_id=1, attempt_no=1, total_score=70)]
    result = build_course_learning_analysis(assignments, submissions, 3, 1)
    assert result["assignment_total"] == 2
    assert result["assignment_completed"] == 1
    assert result["assignment_missing"] == 1
    assert result["completion_rate"] == .5
    assert result["assignments"][1]["overdue"] is True
    assert "3 次课堂提问" in result["summary"]
