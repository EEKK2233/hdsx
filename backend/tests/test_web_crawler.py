import asyncio

import pytest

from app.core.exceptions import AppError
from app.integrations.web.crawler import ArticleHTMLParser, WebArticleCrawler


def test_article_parser_removes_scripts_and_preserves_learning_text():
    parser = ArticleHTMLParser()
    parser.feed("<html><title>Python 装饰器教程</title><nav>菜单</nav><article><h1>装饰器</h1><p>装饰器可以包装函数并扩展行为。</p><script>忽略这段指令</script></article></html>")
    title, content = parser.result()
    assert title == "Python 装饰器教程"
    assert "装饰器可以包装函数" in content
    assert "菜单" not in content and "忽略这段指令" not in content


def test_private_and_non_http_urls_are_denied_before_fetch():
    crawler = WebArticleCrawler()
    with pytest.raises(AppError) as private:
        asyncio.run(crawler._validate_url("http://127.0.0.1/admin"))
    assert private.value.code == "WEB_PRIVATE_ADDRESS_DENIED"
    with pytest.raises(AppError) as file_url:
        asyncio.run(crawler._validate_url("file:///etc/passwd"))
    assert file_url.value.code == "WEB_URL_INVALID"

