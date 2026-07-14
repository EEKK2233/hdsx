"""Compatibility import for the collaborator-owned implementation under /p.

The backend is commonly started from either ``Code1`` or ``Code1/backend``.
Make the project root importable in both cases before loading the composed
module.
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from p.course_web_crawler.crawler import ArticleHTMLParser, WebArticle, WebArticleCrawler

__all__ = ["ArticleHTMLParser", "WebArticle", "WebArticleCrawler"]
