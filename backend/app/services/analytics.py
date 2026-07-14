from __future__ import annotations

from datetime import datetime


def build_course_learning_analysis(assignments, submissions, qa_questions: int, qa_attention: int) -> dict:
    """按全部已发布作业（含未完成）与课堂答疑形成可解释学情概览。"""
    latest = {}
    for submission in submissions:
        current = latest.get(submission.assignment_id)
        if current is None or submission.attempt_no > current.attempt_no:
            latest[submission.assignment_id] = submission
    now = datetime.utcnow()
    items, rates = [], []
    for assignment in assignments:
        submission = latest.get(assignment.id)
        rate = None
        if submission and submission.total_score is not None and float(assignment.total_score or 0) > 0:
            rate = max(0.0, min(1.0, float(submission.total_score) / float(assignment.total_score)))
            rates.append(rate)
        items.append({
            "assignment_id": assignment.id, "title": assignment.title,
            "completed": submission is not None, "attempt_no": submission.attempt_no if submission else None,
            "score_rate": rate, "due_at": assignment.due_at,
            "overdue": bool(not submission and assignment.due_at and assignment.due_at < now),
        })
    completed = sum(item["completed"] for item in items)
    total = len(items)
    completion_rate = completed / total if total else 0.0
    average_score_rate = sum(rates) / len(rates) if rates else None
    missing = [item for item in items if not item["completed"]]
    if not total:
        summary = "当前课程尚未发布作业；答疑记录将作为现阶段学习参与度参考。"
    elif completion_rate < .6:
        summary = f"作业完成率为 {completion_rate:.0%}，未完成任务较多，应优先补齐课程作业。"
    elif average_score_rate is not None and average_score_rate < .6:
        summary = f"作业完成率为 {completion_rate:.0%}，但已完成作业平均得分率为 {average_score_rate:.0%}，需要加强基础知识。"
    else:
        score_text = f"，已完成作业平均得分率为 {average_score_rate:.0%}" if average_score_rate is not None else ""
        summary = f"作业完成率为 {completion_rate:.0%}{score_text}，整体学习进度较稳定。"
    if qa_questions:
        summary += f" 本课程已进行 {qa_questions} 次课堂提问。"
    if qa_attention:
        summary += f" 其中 {qa_attention} 条回答置信度较低或需要教师关注。"
    return {
        "assignment_total": total, "assignment_completed": completed,
        "assignment_missing": len(missing), "completion_rate": completion_rate,
        "average_score_rate": average_score_rate, "assignments": items,
        "qa_questions": qa_questions, "qa_attention": qa_attention, "summary": summary,
    }
