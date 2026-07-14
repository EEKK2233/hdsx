"""Stable adapter for the collaborator crawler under ``plugins/spider``."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys

from app.core.exceptions import AppError


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plugins.spider import TextCourseFetcher


@dataclass(slots=True)
class WebArticle:
    title: str
    text: str
    source_url: str
    resolved_url: str
    content_type: str = "text/html"


class WebArticleCrawler:
    """Async project contract backed by the collaborator's requests crawler."""

    def __init__(self, fetcher: TextCourseFetcher | None = None):
        self.fetcher = fetcher or TextCourseFetcher()

    async def search(self, keyword: str, limit: int = 10) -> list[dict]:
        try:
            results = await asyncio.to_thread(self.fetcher.search, keyword, limit)
        except Exception as exc:
            raise AppError("WEB_SEARCH_FAILED", f"网络资料搜索失败：{exc}", 502) from exc
        return [{"title": item.title, "url": item.url, "platform": item.platform} for item in results]

    async def fetch(self, url: str) -> WebArticle:
        try:
            article = await asyncio.to_thread(self.fetcher.fetch, url)
        except ValueError as exc:
            message = str(exc)
            code = "WEB_PRIVATE_ADDRESS_DENIED" if "内网" in message or "保留地址" in message or "本机" in message else "WEB_URL_INVALID"
            raise AppError(code, message, 422) from exc
        except Exception as exc:
            raise AppError("WEB_FETCH_FAILED", f"网页正文抓取失败：{exc}", 502) from exc
        text = article.text.strip()
        if len(text) < 50:
            raise AppError("WEB_CONTENT_TOO_SHORT", "网页正文过短，可能需要登录或 JavaScript 渲染", 422)
        return WebArticle(
            title=article.title.strip() or "网页学习资料", text=text,
            source_url=url, resolved_url=article.url, content_type="text/html",
        )


__all__ = ["WebArticle", "WebArticleCrawler"]
