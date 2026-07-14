from app.services.web_imports import WebImportService
from app.services.web_supplement import WebSupplementService
from app.tools.contracts import ToolContext


async def preview_web_source(context: ToolContext, arguments: dict) -> dict:
    draft = await WebImportService(context.db, context.user).create_preview(int(arguments["course_id"]), str(arguments["url"]))
    return {
        "draft_id": draft.id, "title": draft.title, "resolved_url": draft.resolved_url,
        "source_domain": draft.source_domain, "character_count": draft.metadata_json.get("character_count", len(draft.content)),
        "content_preview": draft.content[:4000], "status": draft.status,
        "confirmation_required": True, "expires_at": draft.expires_at.isoformat(),
    }


async def search_web_knowledge(context: ToolContext, arguments: dict) -> dict:
    supplement = await WebSupplementService().collect(str(arguments["query"]), int(arguments.get("max_articles", 2)))
    return {"context": supplement.context, "citations": supplement.citations}
