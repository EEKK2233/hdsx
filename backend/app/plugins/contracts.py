from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    name: str = Field(min_length=1, max_length=80)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    api_version: str = Field(default="1.0", pattern=r"^1\.0$")
    entrypoint: str = Field(default="plugin.py", pattern=r"^[A-Za-z0-9_.-]+\.py$")
    description: str = ""
    navigation_label: str | None = Field(default=None, max_length=30)
    navigation_roles: list[str] = Field(default_factory=list)
    ui_directory: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class PluginContext:
    plugin_id: str
    plugin_root: Path
    api_version: str = "1.0"


@dataclass(frozen=True)
class PluginContribution:
    router: APIRouter | None = None


@dataclass(frozen=True)
class LoadedPlugin:
    manifest: PluginManifest
    root: Path
    contribution: PluginContribution

    @property
    def ui_path(self) -> Path | None:
        if not self.manifest.ui_directory:
            return None
        path = (self.root / self.manifest.ui_directory).resolve()
        return path if self.root.resolve() in path.parents and path.is_dir() else None
