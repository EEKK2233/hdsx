import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.rag.cleaners.text import clean_text


@dataclass(slots=True)
class WebArticle:
    title: str
    source_url: str
    resolved_url: str
    text: str
    content_type: str


class ArticleHTMLParser(HTMLParser):
    excluded = {"script", "style", "nav", "footer", "header", "form", "iframe", "noscript", "svg"}
    blocks = {"p", "div", "article", "section", "main", "blockquote", "pre", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.in_title = False
        self.title_parts: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag in self.excluded:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if not self.skip_depth and tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n## ")
        elif not self.skip_depth and tag == "li":
            self.parts.append("\n- ")

    def handle_endtag(self, tag: str):
        if tag == "title":
            self.in_title = False
        if tag in self.excluded and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data: str):
        value = re.sub(r"\s+", " ", data).strip()
        if not value or self.skip_depth:
            return
        if self.in_title:
            self.title_parts.append(value)
        self.parts.append(value + " ")

    def result(self) -> tuple[str, str]:
        title = clean_text(" ".join(self.title_parts))[:500]
        return title, clean_text("".join(self.parts))


class BingResultParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_result = 0
        self.in_heading = False
        self.current_url = ""
        self.current_text: list[str] = []
        self.results: list[dict] = []

    def handle_starttag(self, tag: str, attrs):
        values = dict(attrs)
        if tag == "li" and "b_algo" in values.get("class", "").split():
            self.in_result = 1
        elif self.in_result:
            self.in_result += 1
        if self.in_result and tag == "h2":
            self.in_heading = True
        if self.in_result and self.in_heading and tag == "a" and values.get("href", "").startswith(("http://", "https://")):
            self.current_url = values["href"]
            self.current_text = []

    def handle_endtag(self, tag: str):
        if tag == "a" and self.current_url:
            title = clean_text(" ".join(self.current_text))
            if title:
                self.results.append({"title": title[:300], "url": self.current_url})
            self.current_url, self.current_text = "", []
        if tag == "h2":
            self.in_heading = False
        if self.in_result:
            self.in_result -= 1

    def handle_data(self, data: str):
        if self.current_url:
            self.current_text.append(data)


class WebArticleCrawler:
    """参考 course_spider.py 的正文提取思路，增加服务端安全边界。"""

    learning_domains = ("docs.python.org", "runoob.com", "liaoxuefeng.com", "w3school.com.cn", "developer.mozilla.org", "cnblogs.com", "juejin.cn", "segmentfault.com", "github.com")

    def __init__(self):
        self.settings = get_settings()
        self.headers = {"User-Agent": self.settings.web_fetch_user_agent, "Accept": "text/html,text/plain;q=0.9"}

    async def _validate_url(self, url: str) -> str:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise AppError("WEB_URL_INVALID", "只允许不含账号信息的 HTTP/HTTPS 网页地址", 422)
        if parsed.port and parsed.port not in {80, 443}:
            raise AppError("WEB_PORT_DENIED", "网页抓取只允许 80 或 443 端口", 422)
        try:
            addresses = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise AppError("WEB_HOST_UNRESOLVED", "网页域名无法解析", 422) from exc
        for address in {item[4][0] for item in addresses}:
            ip = ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                raise AppError("WEB_PRIVATE_ADDRESS_DENIED", "禁止抓取本机、内网或保留地址", 403)
        return parsed.geturl()

    async def _read_limited(self, response: httpx.Response, limit: int | None = None) -> bytes:
        maximum = limit or self.settings.web_fetch_max_bytes
        declared = int(response.headers.get("content-length", "0") or 0)
        if declared > maximum:
            raise AppError("WEB_CONTENT_TOO_LARGE", "网页内容超过允许大小", 413)
        chunks, total = [], 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > maximum:
                raise AppError("WEB_CONTENT_TOO_LARGE", "网页内容超过允许大小", 413)
            chunks.append(chunk)
        return b"".join(chunks)

    async def _robots_allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            await self._validate_url(robots_url)
            async with client.stream("GET", robots_url, headers=self.headers) as response:
                if response.status_code in {401, 403}:
                    return False
                if response.status_code >= 400:
                    return True
                body = await self._read_limited(response, 200_000)
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(body.decode("utf-8", errors="replace").splitlines())
            return parser.can_fetch(self.settings.web_fetch_user_agent, url)
        except AppError:
            raise
        except Exception:
            return True

    async def _fetch(self, url: str) -> WebArticle:
        original = await self._validate_url(url)
        current = original
        timeout = httpx.Timeout(self.settings.web_fetch_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            for _ in range(4):
                current = await self._validate_url(current)
                if not await self._robots_allowed(client, current):
                    raise AppError("WEB_ROBOTS_DENIED", "目标网站 robots.txt 不允许抓取该页面", 403)
                async with client.stream("GET", current, headers=self.headers) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise AppError("WEB_REDIRECT_INVALID", "网页返回了无目标重定向", 502)
                        current = urljoin(current, location)
                        continue
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        raise AppError("WEB_FETCH_FAILED", f"网页返回 HTTP {response.status_code}", 502) from exc
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(value in content_type for value in ("text/html", "text/plain", "application/xhtml+xml")):
                        raise AppError("WEB_CONTENT_TYPE_DENIED", "只支持 HTML 或纯文本网页", 415)
                    body = await self._read_limited(response)
                    encoding = response.encoding or "utf-8"
                    raw = body.decode(encoding, errors="replace")
                    if "text/plain" in content_type:
                        title, text = urlparse(current).path.rsplit("/", 1)[-1] or urlparse(current).hostname or "网页资料", clean_text(raw)
                    else:
                        parser = ArticleHTMLParser()
                        parser.feed(raw)
                        title, text = parser.result()
                    text = text[:self.settings.web_fetch_max_chars]
                    if len(text) < 200:
                        raise AppError("WEB_CONTENT_TOO_SHORT", "未提取到足够正文，页面可能需要登录或 JavaScript 渲染", 422)
                    return WebArticle(title=title or "网页学习资料", source_url=original, resolved_url=current, text=text, content_type=content_type.split(";")[0])
        raise AppError("WEB_TOO_MANY_REDIRECTS", "网页重定向次数过多", 422)

    async def fetch(self, url: str) -> WebArticle:
        try:
            return await self._fetch(url)
        except AppError:
            raise
        except httpx.HTTPError as exc:
            raise AppError("WEB_FETCH_FAILED", f"网页连接失败：{exc}", 502) from exc

    async def _search(self, keyword: str, limit: int = 10) -> list[dict]:
        query = clean_text(keyword)[:200]
        if not query:
            raise AppError("WEB_SEARCH_EMPTY", "搜索主题不能为空", 422)
        timeout = httpx.Timeout(self.settings.web_fetch_timeout_seconds)
        current = "https://www.bing.com/search"
        sites = " OR ".join(f"site:{domain}" for domain in self.learning_domains)
        params = {"q": f"({sites}) {query} 教程", "setlang": "zh-cn", "count": min(limit, 20)}
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            for _ in range(3):
                await self._validate_url(current)
                async with client.stream("GET", current, params=params, headers=self.headers) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise AppError("WEB_SEARCH_FAILED", "搜索服务返回无目标重定向", 502)
                        current, params = urljoin(str(response.url), location), None
                        continue
                    response.raise_for_status()
                    body = await self._read_limited(response)
                    break
            else:
                raise AppError("WEB_SEARCH_FAILED", "搜索服务重定向次数过多", 502)
        parser = BingResultParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        seen, results = set(), []
        for item in parser.results:
            if item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)
        return results[:limit]

    async def search(self, keyword: str, limit: int = 10) -> list[dict]:
        try:
            return await self._search(keyword, limit)
        except AppError:
            raise
        except httpx.HTTPError as exc:
            raise AppError("WEB_SEARCH_FAILED", f"网页搜索暂时不可用：{exc}", 502) from exc
