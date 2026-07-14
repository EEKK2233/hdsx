from app.integrations.ollama import OllamaClient
from app.integrations.model_runtime import get_model_runtime


class OllamaEmbeddingProvider:
    @property
    def dimension(self) -> int:
        return get_model_runtime().config().embedding_dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = await OllamaClient().embed(texts)
        if any(len(vector) != self.dimension for vector in vectors):
            raise ValueError(f"Embedding 向量维度必须为 {self.dimension}")
        return vectors
