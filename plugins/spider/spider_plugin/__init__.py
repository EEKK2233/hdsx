"""
spider_plugin — 课程资料爬虫集成插件

将 course_spider.py 封装为可被主项目 FastAPI 挂载的路由模块。
支持：搜索 / 预览 / 抓取入库 三种操作。
"""

from .spider_fetcher import TextCourseFetcher, ArticleResult, SearchResult
from .spider_tool import search_topic, fetch_article, fetch_and_save

__all__ = [
    "TextCourseFetcher",
    "ArticleResult",
    "SearchResult",
    "search_topic",
    "fetch_article",
    "fetch_and_save",
]
