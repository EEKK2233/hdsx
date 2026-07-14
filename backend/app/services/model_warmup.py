"""Application startup model warm-up orchestration."""

import asyncio
import logging

from app.core.config import get_settings
from app.integrations.ollama import OllamaClient
from app.integrations.reranker import BGEReranker


logger = logging.getLogger(__name__)


async def warmup_models() -> dict:
    settings = get_settings()
    if not settings.model_warmup_enabled:
        return {"ok": True, "enabled": False, "components": {}}

    components: dict[str, dict] = {}
    try:
        components["ollama"] = {"ok": True, **await OllamaClient().preload()}
    except Exception as exc:
        logger.exception("Ollama 模型启动预热失败")
        components["ollama"] = {"ok": False, "error": str(exc)}

    try:
        reranker = await asyncio.to_thread(BGEReranker().preload)
        components["reranker"] = {"ok": True, **reranker}
    except Exception as exc:
        logger.exception("重排模型启动预热失败")
        components["reranker"] = {"ok": False, "error": str(exc)}

    status = {"ok": all(value["ok"] for value in components.values()), "enabled": True, "components": components}
    if settings.model_warmup_strict and not status["ok"]:
        raise RuntimeError(f"模型预热失败：{components}")
    return status
