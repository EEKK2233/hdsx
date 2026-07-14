"""Course web crawler supplied as a source-composed module."""

from .spider_plugin import ArticleResult, SearchResult, TextCourseFetcher

__all__ = ["ArticleResult", "SearchResult", "TextCourseFetcher"]
