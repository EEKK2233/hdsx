import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    name: str
    version: str
    description: str
    prompt: str
    prompt_version: str = "1.0.0"
    allowed_tools: list[str] = Field(default_factory=list)
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    instructions: str = ""


class SkillRegistry:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).parent / "definitions"
        self._items: dict[tuple[str, str], SkillDefinition] = {}
        self.reload()

    def reload(self) -> None:
        self._items.clear()
        for manifest in sorted(self.root.glob("*/manifest.json")):
            data = json.loads(manifest.read_text(encoding="utf-8"))
            guide = manifest.with_name("SKILL.md")
            data["instructions"] = guide.read_text(encoding="utf-8") if guide.exists() else ""
            item = SkillDefinition.model_validate(data)
            key = (item.name, item.version)
            if key in self._items:
                raise ValueError(f"重复 Skill：{item.name}@{item.version}")
            self._items[key] = item

    def get(self, name: str, version: str = "1.0.0") -> SkillDefinition:
        try:
            return self._items[(name, version)]
        except KeyError as exc:
            raise KeyError(f"未注册 Skill：{name}@{version}") from exc

    def list(self) -> list[SkillDefinition]:
        return sorted(self._items.values(), key=lambda item: (item.name, item.version))


@lru_cache
def get_skill_registry() -> SkillRegistry:
    return SkillRegistry()

