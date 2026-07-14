# 模型 Provider 源码组合模块

本目录从 `hdsx-main` 的 Provider 思路提取而来，提供 Ollama 与 OpenAI 兼容 API 两种 LLM/Embedding 实现。模块不依赖 FastAPI、SQLAlchemy 或项目业务模型；主工程通过 `backend/app/integrations/model_runtime.py` 薄适配调用。

- `contracts.py`：稳定配置和 Provider 契约。
- `providers.py`：Ollama、OpenAI-compatible 实现和工厂。
- `store.py`：使用主工程 `SECRET_KEY` 加密保存管理员配置。

OpenAI-compatible 可用于实现 `/v1/chat/completions`、`/v1/embeddings`、`/v1/models` 协议的服务。API Key 不会通过查询接口返回，也不会明文写入仓库。
