import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError


class OllamaClient:
    def __init__(self):
        self.settings = get_settings()

    @property
    def keep_alive(self) -> int | str:
        value = self.settings.ollama_keep_alive.strip()
        return int(value) if value.lstrip("-").isdigit() else value

    async def chat(self, system: str, user: str, json_mode: bool | dict = False) -> str:
        payload = {
            "model": self.settings.ollama_llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": 0.2},
        }
        if json_mode:
            payload["format"] = json_mode if isinstance(json_mode, dict) else "json"
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
                    json={"model": self.settings.ollama_embedding_model, "input": texts, "keep_alive": self.keep_alive},
                )
                response.raise_for_status()
                return response.json()["embeddings"]
        except (httpx.HTTPError, KeyError) as exc:
            raise AppError("EMBEDDING_UNAVAILABLE", f"Embedding 调用失败：{exc}", 503) from exc

    async def preload(self) -> dict:
        """Load configured Ollama weights before the API starts accepting traffic."""
        timeout = self.settings.model_warmup_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            llm = await client.post(
                f"{self.settings.ollama_base_url}/api/generate",
                json={"model": self.settings.ollama_llm_model, "prompt": "模型预热", "stream": False,
                      "keep_alive": self.keep_alive, "options": {"num_predict": 1}},
            )
            llm.raise_for_status()
            embedding = await client.post(
                f"{self.settings.ollama_base_url}/api/embed",
                json={"model": self.settings.ollama_embedding_model, "input": ["模型预热"],
                      "keep_alive": self.keep_alive},
            )
            embedding.raise_for_status()
        return {"llm": self.settings.ollama_llm_model, "embedding": self.settings.ollama_embedding_model,
                "keep_alive": self.keep_alive}

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{self.settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            names = [item["name"] for item in response.json().get("models", [])]
            return {"ok": True, "models": names}
