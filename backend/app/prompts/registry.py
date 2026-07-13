import json
from functools import lru_cache
from pathlib import Path
from string import Formatter
from typing import Any, Literal

from pydantic import BaseModel


class PromptDefinition(BaseModel):
    name: str
    version: str
    description: str
    output_mode: Literal["text", "json"] = "text"
    variables: list[str]
    system: str
    user: str

    def render(self, **values: Any) -> tuple[str, str]:
        missing = set(self.variables) - values.keys()
        if missing:
            raise ValueError(f"Prompt {self.name}@{self.version} 缺少变量：{sorted(missing)}")
        return self.system.format(**values), self.user.format(**values)


class PromptRegistry:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).parent / "definitions"
        self._items: dict[tuple[str, str], PromptDefinition] = {}
        self.reload()

    def reload(self) -> None:
        self._items.clear()
        for path in sorted(self.root.glob("**/*.prompt.json")):
            item = PromptDefinition.model_validate(json.loads(path.read_text(encoding="utf-8")))
            declared = set(item.variables)
            used = {
                field for template in (item.system, item.user)
                for _, field, _, _ in Formatter().parse(template) if field
            }
            if used - declared:
                raise ValueError(f"{path.name} 使用了未声明变量：{sorted(used - declared)}")
            key = (item.name, item.version)
            if key in self._items:
                raise ValueError(f"重复 Prompt：{item.name}@{item.version}")
            self._items[key] = item

    def get(self, name: str, version: str = "1.0.0") -> PromptDefinition:
        try:
            return self._items[(name, version)]
        except KeyError as exc:
            raise KeyError(f"未注册 Prompt：{name}@{version}") from exc

    def list(self) -> list[PromptDefinition]:
        return sorted(self._items.values(), key=lambda item: (item.name, item.version))


@lru_cache
def get_prompt_registry() -> PromptRegistry:
    return PromptRegistry()

