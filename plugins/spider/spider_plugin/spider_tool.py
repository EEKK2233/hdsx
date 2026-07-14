"""
spider_tool.py — Agent Tool 函数 / 脚本工具
============================================
供 agents.py 或其他后端脚本调用的封装函数。

两种使用方式：
1. 作为独立脚本：python spider_tool.py <url> [topic]
2. 作为模块导入：from spider_plugin.spider_tool import fetch_article, search_topic
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from .spider_fetcher import TextCourseFetcher, ArticleResult, SearchResult


def search_topic(topic: str, max_results: int = 15) -> list[SearchResult]:
    """搜索主题 → 返回搜索结果列表

    典型用法（在 agents.py 中）：
        from app.spider_plugin.spider_tool import search_topic
        results = search_topic("Python装饰器")
        for r in results:
            print(f"[{r.platform}] {r.title}")
    """
    fetcher = TextCourseFetcher()
    return fetcher.search(topic, max_results)


def fetch_article(url: str) -> ArticleResult:
    """抓取单篇文章 → 返回结构化结果

    典型用法：
        from app.spider_plugin.spider_tool import fetch_article
        article = fetch_article("https://...")
        print(article.title, len(article.text))
    """
    fetcher = TextCourseFetcher()
    return fetcher.fetch(url)


def fetch_and_save(url: str, topic: str, output_dir: str = ".") -> str:
    """抓取并保存到本地磁盘 → 返回 .md 文件路径"""
    fetcher = TextCourseFetcher()
    article = fetcher.fetch(url)
    return fetcher.save_to_disk(article, topic, output_dir)


def fetch_as_text(url: str) -> str:
    """快速获取纯文本正文（不含标题元数据）"""
    fetcher = TextCourseFetcher()
    return fetcher.fetch(url).text


# ==================== 命令行入口 ====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python spider_tool.py search <主题>        # 搜索")
        print("  python spider_tool.py fetch <url>          # 抓取")
        print("  python spider_tool.py save <url> <主题>    # 抓取+保存")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "search":
        topic = sys.argv[2] if len(sys.argv) > 2 else "Python"
        results = search_topic(topic)
        print(f"\n🔍 搜索「{topic}」共 {len(results)} 条结果:\n")
        for i, r in enumerate(results, 1):
            print(f"  {i:2d}. [{r.platform}] {r.title}")
            print(f"      {r.url}")
            print()

    elif cmd == "fetch":
        url = sys.argv[2]
        article = fetch_article(url)
        print(f"\n📄 {article.title}")
        print(f"🔗 {article.url}")
        print(f"📏 {article.length} 字符\n")
        print(article.text[:2000])
        if len(article.text) > 2000:
            print(f"\n...（共 {article.length} 字符，已截断）")

    elif cmd == "save":
        url = sys.argv[2]
        topic = sys.argv[3] if len(sys.argv) > 3 else "web"
        path = fetch_and_save(url, topic)
        print(f"\n✅ 已保存到: {path}")
