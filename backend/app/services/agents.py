import json

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.integrations.ollama import OllamaClient
from app.rag.service import KnowledgeService


async def generate_lesson(db: Session, request) -> tuple[dict, list]:
    knowledge = KnowledgeService(db)
    chunks = knowledge.keyword_search(request.course_id, request.chapter_title, 8)
    if not chunks:
        chunks = knowledge.course_context(request.course_id, 8)
    context = "\n\n".join(f"[资料{i+1}] {c.content}" for i, c in enumerate(chunks))
    if not context:
        raise AppError("INSUFFICIENT_EVIDENCE", "当前课程知识库没有已完成入库的资料，请先上传文件并确认状态为 ready", 422)
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


async def generate_assignment_materials(document, chunks, request) -> list[dict]:
    context = "\n\n".join(chunk.content for chunk in chunks[:12])
    schema = {
        "items": [{
            "material_type": "example|exercise|thinking|extension",
            "question_type": "single_choice|true_false|short_answer|essay",
            "stem": "题干或材料说明", "standard_answer": "参考答案",
            "options": [{"key": "A", "content": "选项"}], "max_score": 5,
        }]
    }
    prompt = f"""根据指定资料和主题生成教学材料。主题：{request.chapter_or_topic}
数量要求：课堂例题{request.example_count}，练习题{request.exercise_count}，思考题{request.thinking_count}，拓展材料{request.extension_count}。
必须严格输出 JSON，结构参考：{json.dumps(schema, ensure_ascii=False)}。
拓展材料可使用 essay 类型；选择题必须提供 options 和正确选项编号。所有内容必须能从资料推导。
资料文件：{document.filename}
资料内容：
{context}"""
    raw = await OllamaClient().chat("你是课程作业与课堂材料设计助手，不得脱离给定资料。", prompt, True)
    try:
        data = json.loads(raw)
        items = data.get("items", [])
        allowed_materials = {"example", "exercise", "thinking", "extension"}
        allowed_questions = {"single_choice", "multiple_choice", "true_false", "short_answer", "essay"}
        output = []
        for item in items:
            if item.get("material_type") not in allowed_materials or item.get("question_type") not in allowed_questions:
                continue
            output.append({
                "material_type": item["material_type"], "question_type": item["question_type"],
                "stem": str(item.get("stem", "")).strip(),
                "standard_answer": str(item.get("standard_answer", "")).strip(),
                "options": item.get("options"), "max_score": max(1, min(20, float(item.get("max_score", 5)))),
            })
        if not output:
            raise ValueError("empty items")
        return output
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AppError("MODEL_OUTPUT_INVALID", "作业材料生成结果格式无效", 502) from exc
