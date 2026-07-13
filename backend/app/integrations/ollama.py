import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError


class OllamaClient:
    def __init__(self):
        self.settings = get_settings()

    async def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        payload = {
            "model": self.settings.ollama_llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json=payload)
                response.raise_for_status()
                return response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError) as exc:
            raise AppError("MODEL_UNAVAILABLE", f"Ollama 调用失败：{exc}", 503) from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/embed",
                    json={"model": self.settings.ollama_embedding_model, "input": texts},
                )
                response.raise_for_status()
                return response.json()["embeddings"]
        except (httpx.HTTPError, KeyError) as exc:
            raise AppError("EMBEDDING_UNAVAILABLE", f"Embedding 调用失败：{exc}", 503) from exc

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{self.settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            names = [item["name"] for item in response.json().get("models", [])]
            return {"ok": True, "models": names}

