import json
import re

from sqlalchemy.orm import Session

from app.agents.answer import StandardAnswerAgent
from app.agents.assignment import AssignmentAgent
from app.agents.grading import GradingAgent
from app.agents.lesson import LessonAgent
from app.agents.report import ReportAgent
from app.agents.runtime import AgentRuntime
from app.agents.structured import (
    AssignmentMaterial, AssignmentMaterialsOutput, GradingOutput, ParentReportOutput,
    extract_json, validate_or_fallback,
)
from app.core.exceptions import AppError
from app.integrations.ollama import OllamaClient
from app.rag.service import KnowledgeService


def _load_model_json(raw: str):
    return extract_json(raw)


async def generate_lesson(db: Session, request) -> tuple[dict, list]:
    knowledge = KnowledgeService(db)
    chunks = knowledge.keyword_search(request.course_id, request.chapter_title, 8)
    if not chunks:
        candidates = await knowledge.hybrid_search(request.course_id, request.chapter_title, 8)
        chunks = [chunk for chunk in candidates if chunk.rerank_score is not None and chunk.rerank_score > 0]
    context = "\n\n".join(f"[资料{i+1}] {chunk.content}" for i, chunk in enumerate(chunks))
    if not context:
        raise AppError("INSUFFICIENT_EVIDENCE", "当前课程知识库没有找到与该主题相关的资料，请检查课程、主题名称或上传对应教材", 422)
    rules = {
        "lesson_plan": "使用完整教案格式，依次包含课程信息、教学目标、重点与难点、课前准备、教学过程、互动、示例、练习、总结和课后任务。",
        "lecture": "使用可直接讲授的课堂讲稿格式，包含开场、知识讲解、案例、互动、易错提醒和总结。",
        "ppt_outline": "使用 PPT 逐页提纲，每页写明页码、标题、3～6 个要点、建议图示和讲解提示。",
        "exercise": "按例题、练习题、思考题分组，每题包含题干、参考答案和简要解析。",
    }
    result = await LessonAgent().run({
        "resource_type": request.resource_type, "audience": request.audience,
        "duration_minutes": request.duration_minutes, "chapter_title": request.chapter_title,
        "requirements": request.requirements or "无",
        "format_rules": rules.get(request.resource_type, rules["lesson_plan"]), "context": context,
    }, tools_used=["search_course_knowledge"])
    text = str(result.content).strip()
    if not text:
        raise AppError("MODEL_OUTPUT_INVALID", "模型未返回备课文本", 502)
    type_name = {"lesson_plan": "完整教案", "lecture": "课堂讲稿", "ppt_outline": "PPT 提纲", "exercise": "课堂练习"}.get(request.resource_type, "备课资料")
    content = {"title": f"{request.chapter_title}｜{type_name}", "text": text, "format": "markdown", "resource_type": request.resource_type}
    citations = [{"chunk_id": chunk.chunk_id, "filename": chunk.filename, "source_url": chunk.source_url} for chunk in chunks]
    return content, citations


async def grade_subjective(question, answer: str, knowledge_context: str = "") -> dict:
    payload = {"standard_answer": question.standard_answer, "rubric": question.rubric_json or [],
               "max_score": float(question.max_score), "student_answer": answer,
               "course_knowledge": knowledge_context}
    result = await GradingAgent().run(
        {"payload": json.dumps(payload, ensure_ascii=False)},
        output_schema=GradingOutput.model_json_schema(),
        tools_used=["get_course_context"] if knowledge_context else [],
    )
    max_score = float(question.max_score)

    def fallback() -> GradingOutput:
        reference = str(question.standard_answer or knowledge_context).strip()
        expected = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", reference.lower()))
        actual = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", answer.lower()))
        ratio = len(expected & actual) / max(1, min(len(expected), 12))
        score = round(max_score * min(1.0, ratio), 2) if answer.strip() else 0
        return GradingOutput(score=score, confidence=.35,
            feedback="模型返回格式异常，系统已按参考答案关键词完成保守评分，建议教师复核。",
            evidence=[{"point": "参考答案关键词匹配", "source": "标准答案与课程知识库"}])

    data = validate_or_fallback(str(result.content), GradingOutput, fallback).model_dump()
    data["score"] = max(0, min(max_score, data["score"]))
    return data


def _normalize_assignment_materials(data) -> dict:
    items = data if isinstance(data, list) else data.get("items") or data.get("questions") or data.get("materials") or []
    if isinstance(items, dict):
        items = list(items.values())
    output = []
    material_alias = {"例题": "example", "练习题": "exercise", "思考题": "thinking", "拓展材料": "extension"}
    question_alias = {"单选题": "single_choice", "多选题": "multiple_choice", "判断题": "true_false", "简答题": "short_answer", "论述题": "essay"}
    for item in items:
        if not isinstance(item, dict):
            continue
        material_type = material_alias.get(item.get("material_type"), item.get("material_type", "exercise"))
        raw_type = item.get("question_type") or item.get("type")
        question_type = question_alias.get(raw_type, raw_type)
        options = item.get("options") or item.get("选项")
        if isinstance(options, dict):
            options = [{"key": str(key), "content": str(value)} for key, value in options.items()]
        elif isinstance(options, list):
            options = [value if isinstance(value, dict) else {"key": chr(65 + index), "content": str(value)} for index, value in enumerate(options)]
        answer = item.get("standard_answer") or item.get("answer") or item.get("参考答案") or ""
        if isinstance(answer, list):
            answer = ",".join(map(str, answer))
        if question_type == "true_false":
            options = [{"key": "true", "content": "正确"}, {"key": "false", "content": "错误"}]
            answer = "true" if str(answer).lower().strip() in {"true", "正确", "对", "是", "1"} else "false"
        output.append({"material_type": material_type, "question_type": question_type,
            "stem": str(item.get("stem") or item.get("question") or item.get("题干") or "").strip(),
            "standard_answer": str(answer).strip(), "options": options,
            "max_score": max(1, min(20, float(item.get("max_score") or item.get("score") or 5)))})
    return {"items": output}


async def generate_assignment_materials(documents, chunks, request) -> list[dict]:
    documents = documents if isinstance(documents, list) else [documents]
    filenames = "、".join(document.filename for document in documents)
    if len(documents) > 1 and all(hasattr(chunk, "document_id") for chunk in chunks):
        selected = []
        for document in documents:
            selected.extend([chunk for chunk in chunks if chunk.document_id == document.id][:max(2, 16 // len(documents))])
    else:
        selected = chunks[:16]
    names = {getattr(document, "id", None): document.filename for document in documents}
    context = "\n\n".join(f"[来源：{names.get(getattr(chunk, 'document_id', None), filenames)}]\n{chunk.content}" for chunk in selected)
    client = OllamaClient()
    result = await AssignmentAgent(AgentRuntime(client)).run({
        "topic": request.chapter_or_topic,
        "counts": f"课堂例题{request.example_count}，练习题{request.exercise_count}，思考题{request.thinking_count}，拓展材料{request.extension_count}",
        "schema": json.dumps({"items": [AssignmentMaterial.model_json_schema()]}, ensure_ascii=False),
        "filenames": filenames, "context": context,
    }, output_schema=AssignmentMaterialsOutput.model_json_schema(), tools_used=["get_document_context"])

    def fallback() -> AssignmentMaterialsOutput:
        source = re.sub(r"\s+", " ", context).strip()[:900] or request.chapter_or_topic
        plan = [("example", request.example_count), ("exercise", request.exercise_count),
                ("thinking", request.thinking_count), ("extension", request.extension_count)]
        items = []
        for material_type, count in plan:
            for index in range(count):
                excerpt = source[index * 120:(index + 1) * 120] or source[:120]
                items.append(AssignmentMaterial(material_type=material_type, question_type="short_answer",
                    stem=f"结合所选资料，说明“{request.chapter_or_topic}”的核心内容与应用要点（{index+1}）。",
                    standard_answer=f"答案应围绕以下资料要点展开：{excerpt}", max_score=5))
        if not items:
            items.append(AssignmentMaterial(material_type="exercise", question_type="short_answer",
                stem=f"概述“{request.chapter_or_topic}”的核心内容。", standard_answer=source[:240], max_score=5))
        return AssignmentMaterialsOutput(items=items)

    validated = validate_or_fallback(str(result.content), AssignmentMaterialsOutput, fallback, _normalize_assignment_materials)
    return [item.model_dump() for item in validated.items]


async def generate_standard_answer(db: Session, course_id: int, question_type: str, stem: str, options: list | None) -> str:
    context = "\n\n".join(chunk.content for chunk in KnowledgeService(db).course_context(course_id, 6))
    result = await StandardAnswerAgent().run({"question_type": question_type, "stem": stem,
        "options": json.dumps(options or [], ensure_ascii=False), "context": context},
        tools_used=["get_course_context"])
    return str(result.content).strip().strip("`").strip()


async def generate_parent_report(metrics: dict) -> dict:
    result = await ReportAgent().run({"metrics": json.dumps(metrics, ensure_ascii=False)},
        output_schema=ParentReportOutput.model_json_schema(), tools_used=["get_student_mastery_summary"])

    def normalize(value):
        for field in ("highlights", "needs_attention", "action_plan"):
            item = value.get(field, [])
            value[field] = [part.strip() for part in re.split(r"[\n；;]+", item) if part.strip()] if isinstance(item, str) else (item if isinstance(item, list) else [])
        for field in ("overview", "encouragement", "metrics_explanation"):
            item = value.get(field, "")
            value[field] = "；".join(map(str, item)) if isinstance(item, list) else str(item or "")
        return value

    def fallback() -> ParentReportOutput:
        average, weak_count = float(metrics.get("average_mastery") or 0), len(metrics.get("weak_points") or [])
        return ParentReportOutput(overview=f"本阶段平均掌握度为 {average:.0%}，共有 {weak_count} 个知识点需要继续巩固。",
            highlights=["已完成本阶段学习与练习记录"], needs_attention=[f"优先复习 {weak_count} 个薄弱知识点"] if weak_count else ["继续保持当前学习节奏"],
            action_plan=["每天安排固定复习时间", "结合错题进行一次针对性练习"], encouragement="稳步积累比一次高分更重要，请继续保持。",
            metrics_explanation="掌握度综合参考作业表现和知识点学习记录。")

    return validate_or_fallback(str(result.content), ParentReportOutput, fallback, normalize).model_dump()
