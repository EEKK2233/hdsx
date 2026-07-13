import json
import re

from sqlalchemy.orm import Session

from app.agents.answer import StandardAnswerAgent
from app.agents.assignment import AssignmentAgent
from app.agents.grading import GradingAgent
from app.agents.lesson import LessonAgent
from app.agents.runtime import AgentRuntime
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
        candidates = await knowledge.hybrid_search(request.course_id, request.chapter_title, 8)
        chunks = [chunk for chunk in candidates if chunk.rerank_score is not None and chunk.rerank_score > 0]
    context = "\n\n".join(f"[资料{i+1}] {c.content}" for i, c in enumerate(chunks))
    if not context:
        raise AppError("INSUFFICIENT_EVIDENCE", "当前课程知识库没有找到与该主题相关的资料，请检查课程、主题名称或上传对应教材", 422)
    format_rules = {
        "lesson_plan": "使用完整教案格式，依次包含：课程信息、教学目标、重点与难点、课前准备、教学过程（每个环节标注分钟数）、课堂互动、示例、练习、课堂总结和课后任务。",
        "lecture": "使用可直接讲授的课堂讲稿格式，包含：开场导入、知识讲解、案例串讲、提问互动、易错提醒、课堂总结；语言自然，避免只列关键词。",
        "ppt_outline": "使用 PPT 逐页提纲格式，每页写明“第N页｜标题”，并列出该页要点、建议图示和讲解提示；控制每页 3～6 个要点。",
        "exercise": "使用课堂练习文本格式，按“例题、练习题、思考题”分组；每题包含题干、参考答案和简要解析。",
    }
    result = await LessonAgent().run({
        "resource_type": request.resource_type, "audience": request.audience,
        "duration_minutes": request.duration_minutes, "chapter_title": request.chapter_title,
        "requirements": request.requirements or "无",
        "format_rules": format_rules.get(request.resource_type, format_rules["lesson_plan"]),
        "context": context,
    }, tools_used=["search_course_knowledge"])
    raw = str(result.content)
    text = raw.strip()
    if not text:
        raise AppError("MODEL_OUTPUT_INVALID", "模型未返回备课文本", 502)
    title = f"{request.chapter_title}｜{ {'lesson_plan':'完整教案','lecture':'课堂讲稿','ppt_outline':'PPT 提纲','exercise':'课堂练习'}.get(request.resource_type, '备课资料') }"
    content = {"title": title, "text": text, "format": "markdown", "resource_type": request.resource_type}
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
    result = await GradingAgent().run(
        {"payload": json.dumps(payload, ensure_ascii=False)},
        tools_used=["get_course_context"] if knowledge_context else [],
    )
    raw = str(result.content)
    try:
        result = _load_model_json(raw)
        result["score"] = max(0, min(float(question.max_score), float(result.get("score", 0))))
        result["confidence"] = max(0, min(1, float(result.get("confidence", 0))))
        return result
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AppError("MODEL_OUTPUT_INVALID", "批改模型输出格式无效", 502) from exc


async def generate_assignment_materials(documents, chunks, request) -> list[dict]:
    documents = documents if isinstance(documents, list) else [documents]
    filenames = "、".join(document.filename for document in documents)
    if len(documents) > 1 and all(hasattr(chunk, "document_id") for chunk in chunks):
        per_document = max(2, 16 // len(documents))
        selected_chunks = []
        for document in documents:
            selected_chunks.extend([chunk for chunk in chunks if chunk.document_id == document.id][:per_document])
    else:
        selected_chunks = chunks[:16]
    filename_map = {getattr(document, "id", None): document.filename for document in documents}
    context = "\n\n".join(f"[来源：{filename_map.get(getattr(chunk, 'document_id', None), filenames)}]\n{chunk.content}" for chunk in selected_chunks)
    schema = {
        "items": [{
            "material_type": "example|exercise|thinking|extension",
            "question_type": "single_choice|true_false|short_answer|essay",
            "stem": "题干或材料说明", "standard_answer": "参考答案",
            "options": [{"key": "A", "content": "选项"}], "max_score": 5,
        }]
    }
    client = OllamaClient()
    output_schema = {
        "type": "object", "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": {
                "material_type": {"type": "string", "enum": ["example", "exercise", "thinking", "extension"]},
                "question_type": {"type": "string", "enum": ["single_choice", "multiple_choice", "true_false", "short_answer", "essay"]},
                "stem": {"type": "string"}, "standard_answer": {"type": "string"},
                "options": {"type": ["array", "null"], "items": {"type": "object", "properties": {"key": {"type": "string"}, "content": {"type": "string"}}, "required": ["key", "content"]}},
                "max_score": {"type": "number"},
            }, "required": ["material_type", "question_type", "stem", "standard_answer", "max_score"]
        }}}, "required": ["items"]
    }
    result = await AssignmentAgent(AgentRuntime(client)).run({
        "topic": request.chapter_or_topic,
        "counts": f"课堂例题{request.example_count}，练习题{request.exercise_count}，思考题{request.thinking_count}，拓展材料{request.extension_count}",
        "schema": json.dumps(schema, ensure_ascii=False), "filenames": filenames, "context": context,
    }, output_schema=output_schema, tools_used=["get_document_context"])
    raw = str(result.content)
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
            fallback = await client.chat(
                "你是课程例题设计助手，只依据资料。",
                f"根据资料为“{request.chapter_or_topic}”生成一道简答题。严格只输出两行：\n题目：...\n答案：...\n资料：{context[:5000]}",
                False,
            )
            match = re.search(r"题目[:：]\s*(.+?)\s*答案[:：]\s*(.+)", fallback, re.S)
            if match:
                output.append({"material_type": "example", "question_type": "short_answer", "stem": match.group(1).strip(), "standard_answer": match.group(2).strip(), "options": None, "max_score": 5})
        if not output:
            raise ValueError("empty items")
        return output
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
        fallback = await client.chat(
            "你是课程例题设计助手，只依据资料。",
            f"根据资料为“{request.chapter_or_topic}”生成一道简答题。严格只输出两行：\n题目：...\n答案：...\n资料：{context[:5000]}",
            False,
        )
        match = re.search(r"题目[:：]\s*(.+?)\s*答案[:：]\s*(.+)", fallback, re.S)
        if match:
            return [{"material_type": "example", "question_type": "short_answer", "stem": match.group(1).strip(), "standard_answer": match.group(2).strip(), "options": None, "max_score": 5}]
        raise AppError("MODEL_OUTPUT_INVALID", "作业材料生成失败，请缩小生成数量或更换章节主题后重试", 502) from exc


async def generate_standard_answer(db: Session, course_id: int, question_type: str, stem: str, options: list | None) -> str:
    chunks = KnowledgeService(db).course_context(course_id, 6)
    context = "\n\n".join(chunk.content for chunk in chunks)
    result = await StandardAnswerAgent().run({
        "question_type": question_type, "stem": stem,
        "options": json.dumps(options or [], ensure_ascii=False), "context": context,
    }, tools_used=["get_course_context"])
    return str(result.content).strip().strip('`').strip()
