import json
import tempfile
import unittest
from pathlib import Path

from src.core.config import SettingsManager
from src.core.plugin_manager import PluginInfo, PluginManager


class SettingsManagerTests(unittest.TestCase):
    def test_explicit_config_file_is_created_and_updated(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "settings" / "cli_config.json"
            settings = SettingsManager(config_file)

            self.assertTrue(config_file.exists())
            self.assertTrue(settings.set_browser_headless(True))

            reloaded = SettingsManager(config_file)
            self.assertTrue(reloaded.get_browser_headless())
            self.assertFalse(config_file.with_suffix(".json.tmp").exists())


class StubSettings:
    def is_plugin_enabled(self, _plugin_id):
        return True

    def set_plugin_enabled(self, _plugin_id, _enabled):
        return True


def plugin_info(plugin_id, dependencies=None, enabled=True):
    return PluginInfo(
        id=plugin_id,
        name=plugin_id,
        version="1.0.0",
        description="",
        icon="extension",
        author="",
        entry_ui="ui.create_view",
        entry_core=None,
        min_app_version=None,
        dependencies=dependencies or [],
        enabled=enabled,
        path=Path("/tmp") / plugin_id,
    )


class PluginManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = object.__new__(PluginManager)
        self.manager.settings_manager = StubSettings()
        self.manager._plugins = {}

    def test_rejects_invalid_manifest_identity(self):
        invalid = plugin_info("Bad-Plugin")

        with self.assertRaises(ValueError):
            self.manager._validate_plugin_info(invalid)

    def test_scanning_twice_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir) / "demo"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.json").write_text(
                json.dumps({
                    "id": "demo",
                    "name": "Demo",
                    "entry_ui": "ui.create_view",
                    "dependencies": [],
                }),
                encoding="utf-8",
            )

            self.assertEqual(self.manager.scan_plugins(Path(tmp_dir)), 1)
            self.assertEqual(self.manager.scan_plugins(Path(tmp_dir)), 1)
            self.assertIn("demo", self.manager.get_all_plugins())

    def test_cannot_enable_plugin_without_enabled_dependency(self):
        addon = plugin_info("addon", dependencies=["base"], enabled=False)
        self.manager._plugins = {"addon": addon}

        self.assertFalse(self.manager.enable_plugin("addon"))
        self.assertFalse(addon.enabled)

    def test_cannot_disable_dependency_of_enabled_plugin(self):
        base = plugin_info("base")
        addon = plugin_info("addon", dependencies=["base"])
        self.manager._plugins = {"base": base, "addon": addon}

        self.assertFalse(self.manager.disable_plugin("base"))
        self.assertTrue(base.enabled)


if __name__ == "__main__":
    unittest.main()
