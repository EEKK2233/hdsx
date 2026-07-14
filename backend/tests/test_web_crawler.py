import asyncio

import pytest
from bs4 import BeautifulSoup

from app.core.exceptions import AppError
from app.integrations.web import WebArticleCrawler
from plugins.spider import ArticleResult, TextCourseFetcher


def test_spider_engine_removes_noise_and_preserves_learning_text():
    fetcher = TextCourseFetcher()
    soup = BeautifulSoup(
        "<body><nav>菜单</nav><article><h1>装饰器</h1><p>装饰器可以包装函数并扩展行为。</p><script>忽略指令</script></article></body>",
        "html.parser",
    )
    body = fetcher._clean_body(fetcher._extract_body(soup, "https://example.com/article"))
    text = body.get_text(" ", strip=True)
    assert "装饰器可以包装函数" in text
    assert "忽略指令" not in text


def test_private_and_non_http_urls_are_denied_before_fetch():
    with pytest.raises(ValueError, match="内网"):
        TextCourseFetcher.validate_public_url("http://127.0.0.1/admin")
    with pytest.raises(ValueError, match="http/https"):
        TextCourseFetcher.validate_public_url("file:///etc/passwd")


class FakeFetcher:
    def search(self, keyword, limit):
        return []

    def fetch(self, url):
        return ArticleResult(title="协作爬虫", url="https://example.com/final", text="有效课程正文" * 20, platform="测试")


def test_project_adapter_uses_plugins_spider_engine():
    crawler = WebArticleCrawler(FakeFetcher())
    article = asyncio.run(crawler.fetch("https://example.com/source"))
    assert isinstance(crawler.fetcher, FakeFetcher)
    assert article.title == "协作爬虫"
    assert article.resolved_url == "https://example.com/final"


class InvalidFetcher(FakeFetcher):
    def fetch(self, url):
        raise ValueError("不允许抓取本机或内网地址")


def test_adapter_maps_spider_security_error_to_api_error():
    with pytest.raises(AppError) as error:
        asyncio.run(WebArticleCrawler(InvalidFetcher()).fetch("http://127.0.0.1"))
    assert error.value.code == "WEB_PRIVATE_ADDRESS_DENIED"
