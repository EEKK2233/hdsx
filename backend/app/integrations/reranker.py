from functools import lru_cache

from app.core.config import get_settings


class BGEReranker:
    def __init__(self):
        self.settings = get_settings()

    @staticmethod
    @lru_cache(maxsize=1)
    def _load(model_path: str, configured_device: str):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
        device = configured_device if configured_device == "cpu" or torch.cuda.is_available() else "cpu"
        model.to(device).eval()
        return tokenizer, model, device

    def score(self, query: str, documents: list[str]) -> list[float | None]:
        if not documents or not self.settings.reranker_model_path:
            return [None] * len(documents)
        import torch

        tokenizer, model, device = self._load(
            self.settings.reranker_model_path, self.settings.reranker_device
        )
        pairs = [[query, document] for document in documents]
        inputs = tokenizer(pairs, padding=True, truncation=True, max_length=512, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            logits = model(**inputs).logits.view(-1).float().cpu().tolist()
        return [float(value) for value in logits]

    def preload(self) -> dict:
        if not self.settings.reranker_model_path:
            return {"loaded": False, "reason": "未配置本地重排模型路径"}
        _, _, device = self._load(self.settings.reranker_model_path, self.settings.reranker_device)
        return {"loaded": True, "model_path": self.settings.reranker_model_path, "device": device}
