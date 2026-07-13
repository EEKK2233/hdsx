from app.integrations.ollama import OllamaClient


class OllamaEmbeddingProvider:
    dimension = 768

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = await OllamaClient().embed(texts)
        if any(len(vector) != self.dimension for vector in vectors):
            raise ValueError(f"Embedding 向量维度必须为 {self.dimension}")
        return vectors

