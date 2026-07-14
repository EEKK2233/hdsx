import importlib.util
import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.plugins.contracts import LoadedPlugin, PluginContext, PluginContribution, PluginManifest


class PluginRegistry:
    """Load only explicitly enabled, repository-local trusted plugins."""

    def __init__(self, root: Path | None = None, enabled: set[str] | None = None):
        self.root = (root or Path(__file__).parents[3] / "plugins").resolve()
        configured = get_settings().enabled_plugins
        self.enabled = enabled if enabled is not None else {item.strip() for item in configured.split(",") if item.strip()}
        self._plugins = self._load()

    def _load(self) -> list[LoadedPlugin]:
        loaded = []
        if not self.root.is_dir():
            return loaded
        for plugin_id in sorted(self.enabled):
            plugin_root = (self.root / plugin_id).resolve()
            if self.root not in plugin_root.parents:
                raise ValueError(f"插件目录越界：{plugin_id}")
            manifest_path = plugin_root / "plugin.json"
            if not manifest_path.is_file():
                raise ValueError(f"已启用插件缺少 plugin.json：{plugin_id}")
            manifest = PluginManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
            if manifest.id != plugin_id:
                raise ValueError(f"插件目录名与 manifest.id 不一致：{plugin_id}")
            entrypoint = (plugin_root / manifest.entrypoint).resolve()
            if plugin_root not in entrypoint.parents or not entrypoint.is_file():
                raise ValueError(f"插件入口无效：{plugin_id}")
            spec = importlib.util.spec_from_file_location(f"edu_plugin_{plugin_id}", entrypoint)
            if not spec or not spec.loader:
                raise ValueError(f"无法加载插件入口：{plugin_id}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            setup = getattr(module, "setup", None)
            if not callable(setup):
                raise ValueError(f"插件必须提供 setup(context)：{plugin_id}")
            contribution = setup(PluginContext(plugin_id=plugin_id, plugin_root=plugin_root))
            if not isinstance(contribution, PluginContribution):
                raise TypeError(f"插件 setup 必须返回 PluginContribution：{plugin_id}")
            loaded.append(LoadedPlugin(manifest, plugin_root, contribution))
        return loaded

    def list(self) -> list[LoadedPlugin]:
        return list(self._plugins)


@lru_cache
def get_plugin_registry() -> PluginRegistry:
    return PluginRegistry()
