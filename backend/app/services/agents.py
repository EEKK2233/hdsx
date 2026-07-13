import json

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.integrations.ollama import OllamaClient
from app.rag.service import KnowledgeService


async def generate_lesson(db: Session, request) -> tuple[dict, list]:
    chunks = KnowledgeService(db).keyword_search(request.course_id, request.chapter_title, 8)
    context = "\n\n".join(f"[资料{i+1}] {c.content}" for i, c in enumerate(chunks))
    if not context:
        raise AppError("INSUFFICIENT_EVIDENCE", "知识库中没有该章节资料", 422)
    schema = {
        "title": "标题", "objectives": ["目标"], "key_points": ["重点"],
        "difficulties": ["难点"], "procedure": [{"stage": "环节", "minutes": 5, "content": "内容"}],
        "examples": [], "exercises": [], "summary": "总结", "homework": []
    }
    prompt = (
        f"请生成{request.resource_type}，对象：{request.audience}，课时：{request.duration_minutes}分钟。"
        f"章节：{request.chapter_title}。额外要求：{request.requirements or '无'}。"
        f"必须输出 JSON，结构参考：{json.dumps(schema, ensure_ascii=False)}。\n资料：\n{context}"
    )
    raw = await OllamaClient().chat("你是教师备课助手，只依据所给资料。", prompt, json_mode=True)
    try:
        content = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError("MODEL_OUTPUT_INVALID", "模型未返回有效 JSON", 502) from exc
    citations = [{"chunk_id": c.chunk_id, "filename": c.filename} for c in chunks]
    return content, citations


async def grade_subjective(question, answer: str) -> dict:
    payload = {
        "standard_answer": question.standard_answer,
        "rubric": question.rubric_json or [],
        "max_score": float(question.max_score),
        "student_answer": answer,
    }
    prompt = (
        "逐评分点判断学生答案，返回JSON：score(数字), confidence(0~1), feedback(字符串), "
        "evidence(数组，每项含criterion, matched, reason)。分数不得超过max_score。\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    raw = await OllamaClient().chat("你是谨慎的作业辅助批改助手，评分结果必须由教师复核。", prompt, True)
    try:
        result = json.loads(raw)
        result["score"] = max(0, min(float(question.max_score), float(result.get("score", 0))))
        result["confidence"] = max(0, min(1, float(result.get("confidence", 0))))
        return result
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AppError("MODEL_OUTPUT_INVALID", "批改模型输出格式无效", 502) from exc

