from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .contracts import ModelRuntimeConfig


class EncryptedModelConfigStore:
    """使用应用 SECRET_KEY 派生的 Fernet 密钥加密整个配置文件。"""

    def __init__(self, path: Path, secret_key: str):
        self.path = path
        self.secret_key = secret_key

    def _fernet(self):
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:
            raise RuntimeError("保存模型 API Key 需要安装 cryptography 依赖") from exc
        key = base64.urlsafe_b64encode(hashlib.sha256(self.secret_key.encode("utf-8")).digest())
        return Fernet(key)

    def load(self, fallback: ModelRuntimeConfig) -> ModelRuntimeConfig:
        if not self.path.exists():
            return fallback
        encrypted = self.path.read_bytes()
        try:
            data = json.loads(self._fernet().decrypt(encrypted).decode("utf-8"))
            allowed = set(asdict(fallback))
            merged = {**asdict(fallback), **{key: value for key, value in data.items() if key in allowed}}
            return ModelRuntimeConfig(**merged)
        except Exception as exc:
            raise RuntimeError(f"模型配置文件无法解密或已损坏：{self.path}") from exc

    def save(self, config: ModelRuntimeConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(config), ensure_ascii=False).encode("utf-8")
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(self._fernet().encrypt(payload))
        temporary.replace(self.path)
