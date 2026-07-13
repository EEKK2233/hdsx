import json
import re

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.integrations.ollama import OllamaClient
from app.rag.service import KnowledgeService


def _load_model_json(raw: str):
    value = raw.strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        start_candidates = [index for index in (value.find("{"), value.find("[")) if index >= 0]
        if not start_candidates:
            raise
        start = min(start_candidates)
        end = max(value.rfind("}"), value.rfind("]"))
        if end <= start:
            raise
        return json.loads(value[start:end + 1])


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


async def grade_subjective(question, answer: str, knowledge_context: str = "") -> dict:
    payload = {
        "standard_answer": question.standard_answer,
        "rubric": question.rubric_json or [],
        "max_score": float(question.max_score),
        "student_answer": answer,
        "course_knowledge": knowledge_context,
    }
    prompt = (
        "逐评分点判断学生答案，返回JSON：score(数字), confidence(0~1), feedback(字符串), "
        "evidence(数组，每项含criterion, matched, reason)。分数不得超过max_score。"
        "若提供了标准答案，应结合题目、标准答案和课程资料判分；否则根据题目和课程资料自行归纳评分依据。\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    raw = await OllamaClient().chat("你是谨慎的作业辅助批改助手，评分结果必须由教师复核。", prompt, True)
    try:
        result = _load_model_json(raw)
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
    client = OllamaClient()
    raw = await client.chat("你是课程作业与课堂材料设计助手，不得脱离给定资料。", prompt, True)
    try:
        try:
            data = _load_model_json(raw)
        except (json.JSONDecodeError, TypeError):
            repair_prompt = "将下面内容修复为严格 JSON，只返回包含 items 数组的 JSON，不要代码块或说明：\n" + raw
            data = _load_model_json(await client.chat("你是 JSON 格式修复器，不改变题目内容。", repair_prompt, True))
        items = data if isinstance(data, list) else data.get("items") or data.get("questions") or data.get("materials") or []
        if isinstance(items, dict):
            items = list(items.values())
        allowed_materials = {"example", "exercise", "thinking", "extension"}
        allowed_questions = {"single_choice", "multiple_choice", "true_false", "short_answer", "essay"}
        output = []
        material_aliases = {"例题": "example", "练习题": "exercise", "思考题": "thinking", "拓展材料": "extension"}
        question_aliases = {"单选题": "single_choice", "多选题": "multiple_choice", "判断题": "true_false", "简答题": "short_answer", "论述题": "essay"}
        for item in items:
            if not isinstance(item, dict):
                continue
            material_type = material_aliases.get(item.get("material_type"), item.get("material_type", "exercise"))
            question_type = question_aliases.get(item.get("question_type") or item.get("type"), item.get("question_type") or item.get("type"))
            if material_type not in allowed_materials or question_type not in allowed_questions:
                continue
            stem = str(item.get("stem") or item.get("question") or item.get("题干") or "").strip()
            standard_answer = item.get("standard_answer") or item.get("answer") or item.get("参考答案") or ""
            if isinstance(standard_answer, list):
                standard_answer = ",".join(str(value) for value in standard_answer)
            options = item.get("options") or item.get("选项")
            if isinstance(options, dict):
                options = [{"key": str(key), "content": str(value)} for key, value in options.items()]
            elif isinstance(options, list):
                options = [option if isinstance(option, dict) else {"key": chr(65 + index), "content": str(option)} for index, option in enumerate(options)]
            if question_type == "true_false":
                options = [{"key": "true", "content": "正确"}, {"key": "false", "content": "错误"}]
                normalized = str(standard_answer).strip().lower()
                standard_answer = "true" if normalized in {"true", "正确", "对", "是", "1"} else "false"
            if not stem or not str(standard_answer).strip():
                continue
            output.append({
                "material_type": material_type, "question_type": question_type,
                "stem": stem, "standard_answer": str(standard_answer).strip(),
                "options": options, "max_score": max(1, min(20, float(item.get("max_score") or item.get("score") or 5))),
            })
        if not output:
            raise ValueError("empty items")
        return output
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
        raise AppError("MODEL_OUTPUT_INVALID", "作业材料生成结果格式无效", 502) from exc


async def generate_standard_answer(db: Session, course_id: int, question_type: str, stem: str, options: list | None) -> str:
    chunks = KnowledgeService(db).course_context(course_id, 6)
    context = "\n\n".join(chunk.content for chunk in chunks)
    prompt = (
        f"请为题目生成准确、简洁的标准答案。题型：{question_type}；题目：{stem}；"
        f"选项：{json.dumps(options or [], ensure_ascii=False)}。"
        "单选题只返回选项编号，多选题返回用英文逗号分隔的选项编号，判断题只返回 true 或 false；主观题返回参考答案正文。"
        f"\n课程资料：\n{context}"
    )
    answer = await OllamaClient().chat("你是严谨的课程题目答案助手，只输出标准答案，不要解释或添加标题。", prompt, False)
    return answer.strip().strip('`').strip()
