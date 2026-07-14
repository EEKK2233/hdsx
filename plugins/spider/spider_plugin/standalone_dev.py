"""
standalone_dev.py — 爬虫服务独立开发模式
========================================
无需依赖项目，独立启动 FastAPI 服务。
用于前端开发联调、爬虫功能单独验证。

启动：
    cd D:\hdsx-d\newcode
    pip install fastapi uvicorn requests beautifulsoup4
    python -m spider_plugin.standalone_dev

访问：
    http://127.0.0.1:8765/docs          # Swagger 文档
    http://127.0.0.1:8765/api/v1/spider/search   # 搜索接口
    http://127.0.0.1:8765/api/v1/spider/fetch     # 抓取接口

【注意】独立模式下 /spider/ingest 不可用（需 MySQL + Milvus + Ollama）
       如需完整入库，请使用插件模式接入主项目。
"""

import sys
from pathlib import Path

# 将上级目录加入 sys.path，确保可以直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from spider_plugin.spider_fetcher import TextCourseFetcher

app = FastAPI(
    title="爬虫服务（独立开发模式）",
    version="1.0.0",
    description="独立于主项目的爬虫 API，用于前端联调和功能验证",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    max_results: int = Field(default=15, ge=1, le=30)


class SearchItem(BaseModel):
    title: str
    url: str
    platform: str


class SearchResponse(BaseModel):
    topic: str
    total: int
    results: list[SearchItem]


class FetchRequest(BaseModel):
    url: str = Field(min_length=5, max_length=2000)


class FetchResponse(BaseModel):
    title: str
    url: str
    platform: str
    text: str
    length: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "spider-standalone"}


@app.post("/api/v1/spider/search", response_model=SearchResponse)
def search(data: SearchRequest):
    """搜索网络学习资料"""
    try:
        fetcher = TextCourseFetcher()
        results = fetcher.search(data.topic, data.max_results)
        return SearchResponse(
            topic=data.topic,
            total=len(results),
            results=[SearchItem(title=r.title, url=r.url, platform=r.platform)
                     for r in results],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/spider/fetch", response_model=FetchResponse)
def fetch(data: FetchRequest):
    """抓取文章正文"""
    try:
        fetcher = TextCourseFetcher()
        article = fetcher.fetch(data.url)
        return FetchResponse(
            title=article.title,
            url=article.url,
            platform=article.platform,
            text=article.text[:50000],
            length=len(article.text),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  爬虫服务 — 独立开发模式")
    print("  http://127.0.0.1:8765/docs")
    print("=" * 50)
    uvicorn.run("spider_plugin.standalone_dev:app", host="127.0.0.1", port=8765, reload=True)
