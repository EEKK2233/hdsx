"""Read-only web knowledge supplementation for grounded classroom Q&A."""

import asyncio
from dataclasses import dataclass, field
from typing import Callable

from app.integrations.web import WebArticleCrawler


@dataclass(slots=True)
class WebKnowledgeSupplement:
    context: str = ""
    citations: list[dict] = field(default_factory=list)


class WebSupplementService:
    """Search and fetch a small, bounded set of public learning pages."""

    def __init__(self, crawler_factory: Callable[[], WebArticleCrawler] = WebArticleCrawler):
        self.crawler_factory = crawler_factory

    async def collect(self, query: str, max_articles: int = 2) -> WebKnowledgeSupplement:
        max_articles = max(1, min(2, max_articles))
        try:
            results = await self.crawler_factory().search(query, max(max_articles * 2, 4))
        except Exception:
            return WebKnowledgeSupplement()

        async def fetch(item: dict):
            try:
                return item, await self.crawler_factory().fetch(item["url"])
            except Exception:
                return None

        fetched = await asyncio.gather(*(fetch(item) for item in results[: max_articles * 2]))
        sections, citations = [], []
        for value in fetched:
            if not value or len(sections) >= max_articles:
                continue
            item, article = value
            index = len(sections) + 1
            sections.append(
                f"[网络资料{index}|{article.title}|{article.resolved_url}]\n"
                f"{article.text[:6000]}"
            )
            citations.append({
                "chunk_id": None, "document_id": None, "chunk_index": 0,
                "filename": article.title, "source_url": article.resolved_url,
                "source_type": "web", "platform": item.get("platform", "网络资料"),
            })
        return WebKnowledgeSupplement(context="\n\n".join(sections), citations=citations)
