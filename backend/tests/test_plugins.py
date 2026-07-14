from pathlib import Path

import pytest

from app.plugins.loader import PluginRegistry


def test_enabled_collaboration_plugin_loads_router_and_ui():
    root = Path(__file__).parents[2] / "plugins"
    registry = PluginRegistry(root=root, enabled={"example_hello"})
    plugin = registry.list()[0]
    assert plugin.manifest.id == "example_hello"
    assert plugin.contribution.router is not None
    assert plugin.ui_path and (plugin.ui_path / "index.html").is_file()


def test_plugin_directory_must_match_manifest(tmp_path):
    folder = tmp_path / "wrong_name"
    folder.mkdir()
    (folder / "plugin.json").write_text(
        '{"id":"other_name","name":"x","version":"1.0.0","entrypoint":"plugin.py"}', encoding="utf-8"
    )
    (folder / "plugin.py").write_text("def setup(context): pass", encoding="utf-8")
    with pytest.raises(ValueError, match="不一致"):
        PluginRegistry(root=tmp_path, enabled={"wrong_name"})
