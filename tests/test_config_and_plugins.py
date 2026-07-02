import json
import tempfile
import unittest
from pathlib import Path

from src.core.config import SettingsManager
from src.core.plugin_context import PluginContext
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
    def __init__(self):
        self.enabled = {}

    def is_plugin_enabled(self, _plugin_id):
        return self.enabled.get(_plugin_id, True)

    def set_plugin_enabled(self, plugin_id, enabled):
        self.enabled[plugin_id] = enabled
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
        self.manager._loaded_plugins = {}
        self.manager._contexts = {}

    def test_rejects_invalid_manifest_identity(self):
        invalid = plugin_info("Bad-Plugin")

        with self.assertRaises(ValueError):
            self.manager._validate_plugin_info(invalid)

    def test_rejects_entry_point_without_exact_module_callable(self):
        invalid = plugin_info("bad_entry")
        invalid.entry_ui = "nested.module.create_view"

        with self.assertRaises(ValueError):
            self.manager._validate_plugin_info(invalid)

        invalid.entry_ui = "create_view"
        with self.assertRaises(ValueError):
            self.manager._validate_plugin_info(invalid)

    def test_manifest_id_must_match_plugin_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir) / "actual_dir"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.json").write_text(
                json.dumps({
                    "id": "different_id",
                    "name": "Demo",
                    "entry_ui": "ui.create_view",
                    "dependencies": [],
                }),
                encoding="utf-8",
            )

            self.assertEqual(self.manager.scan_plugins(Path(tmp_dir)), 0)
            self.assertEqual(self.manager.get_all_plugins(), {})

    def test_min_app_version_blocks_incompatible_plugin(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_dir = Path(tmp_dir) / "future_plugin"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.json").write_text(
                json.dumps({
                    "id": "future_plugin",
                    "name": "Future",
                    "entry_ui": "ui.create_view",
                    "dependencies": [],
                    "min_app_version": "999.0.0",
                }),
                encoding="utf-8",
            )

            self.assertEqual(self.manager.scan_plugins(Path(tmp_dir)), 0)
            self.assertIsNone(self.manager.get_plugin_info("future_plugin"))

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

    def test_disable_unloads_plugin_resources(self):
        class Resource:
            def __init__(self):
                self.cleaned = False

            def cleanup(self):
                self.cleaned = True

        resource = Resource()
        self.manager._plugins = {"demo": plugin_info("demo")}
        self.manager._loaded_plugins = {"demo": {"ui": resource}}

        self.assertTrue(self.manager.disable_plugin("demo"))
        self.assertTrue(resource.cleaned)
        self.assertNotIn("demo", self.manager._loaded_plugins)


class FakePage:
    def __init__(self):
        self.run_thread_calls = []
        self.scheduled_updates = 0

    def run_thread(self, handler, *args, **kwargs):
        self.run_thread_calls.append((handler, args, kwargs))
        handler(*args, **kwargs)

    def schedule_update(self):
        self.scheduled_updates += 1


class PluginContextTests(unittest.TestCase):
    def test_run_task_uses_page_executor_and_schedules_callback_update(self):
        page = FakePage()
        context = PluginContext(
            "demo",
            api_client=None,
            browser_manager=None,
            settings_manager=None,
            page=page,
        )
        callback_results = []

        context.run_task(lambda value: value * 2, callback_results.append, 21)

        self.assertEqual(callback_results, [42])
        self.assertEqual(len(page.run_thread_calls), 1)
        self.assertEqual(page.scheduled_updates, 1)


if __name__ == "__main__":
    unittest.main()
