import json
import sys
import tempfile
import unittest
from pathlib import Path

from src.core.config import SettingsManager
from src.core.plugin_context import PluginContext
from src.core.plugin_manager import PluginInfo, PluginManager
from src.ui.views.plugin_runtime import open_plugin_ui


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

    def test_load_plugin_ui_does_not_persist_plugin_parent_in_sys_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugins_dir = Path(tmp_dir)
            plugin_dir = plugins_dir / "isolated_plugin"
            plugin_dir.mkdir()
            (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
            (plugin_dir / "ui.py").write_text(
                "def create_view(page, context):\n"
                "    return 'loaded'\n",
                encoding="utf-8",
            )
            (plugin_dir / "manifest.json").write_text(
                json.dumps({
                    "id": "isolated_plugin",
                    "name": "Isolated",
                    "entry_ui": "ui.create_view",
                    "dependencies": [],
                }),
                encoding="utf-8",
            )

            sys.modules.pop("isolated_plugin", None)
            sys.modules.pop("isolated_plugin.ui", None)
            original_sys_path = list(sys.path)
            try:
                self.assertEqual(self.manager.scan_plugins(plugins_dir), 1)
                self.assertEqual(
                    self.manager.load_plugin_ui("isolated_plugin", page=None, context=None),
                    "loaded",
                )
                self.assertEqual(sys.path, original_sys_path)
            finally:
                sys.modules.pop("isolated_plugin", None)
                sys.modules.pop("isolated_plugin.ui", None)


class FakePage:
    def __init__(self):
        self.run_thread_calls = []
        self.scheduled_updates = 0

    def run_thread(self, handler, *args, **kwargs):
        self.run_thread_calls.append((handler, args, kwargs))
        handler(*args, **kwargs)

    def schedule_update(self):
        self.scheduled_updates += 1


class FailingPage(FakePage):
    def run_thread(self, handler, *args, **kwargs):
        self.run_thread_calls.append((handler, args, kwargs))
        raise RuntimeError("executor unavailable")


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

    def test_run_task_falls_back_when_page_executor_fails(self):
        page = FailingPage()
        context = PluginContext(
            "demo",
            api_client=None,
            browser_manager=None,
            settings_manager=None,
            page=page,
        )
        callback_results = []

        thread = context.run_task(lambda: "ok", callback_results.append)
        thread.join(timeout=2)

        self.assertEqual(callback_results, ["ok"])
        self.assertEqual(len(page.run_thread_calls), 1)
        self.assertEqual(page.scheduled_updates, 1)

    def test_registered_resources_are_cleaned_with_context(self):
        class Resource:
            def __init__(self):
                self.cleaned = False

            def cleanup(self):
                self.cleaned = True

        context = PluginContext(
            "demo",
            api_client=None,
            browser_manager=None,
            settings_manager=None,
        )
        resource = Resource()

        context.register_resource(resource)
        context.cleanup()

        self.assertTrue(resource.cleaned)


class PluginRuntimeTests(unittest.TestCase):
    def test_open_plugin_ui_builds_context_and_loads_control(self):
        class RuntimeManager:
            def __init__(self):
                self.info = plugin_info("demo")
                self.context_args = None
                self.load_args = None

            def get_plugin_info(self, plugin_id):
                return self.info if plugin_id == "demo" else None

            def create_plugin_context(self, **kwargs):
                self.context_args = kwargs
                return "context"

            def load_plugin_ui(self, plugin_id, page, context):
                self.load_args = (plugin_id, page, context)
                return "control"

        manager = RuntimeManager()
        page = object()
        api_client = object()
        browser_manager = object()

        result = open_plugin_ui(
            manager,
            "demo",
            page,
            api_client=api_client,
            browser_manager=browser_manager,
        )

        self.assertTrue(result.loaded)
        self.assertEqual(result.plugin_info, manager.info)
        self.assertEqual(result.control, "control")
        self.assertEqual(manager.load_args, ("demo", page, "context"))
        self.assertEqual(
            manager.context_args,
            {
                "plugin_id": "demo",
                "api_client": api_client,
                "browser_manager": browser_manager,
                "page": page,
            },
        )

    def test_open_plugin_ui_reports_disabled_plugin_without_loading(self):
        class RuntimeManager:
            def __init__(self):
                self.info = plugin_info("demo", enabled=False)
                self.load_called = False

            def get_plugin_info(self, plugin_id):
                return self.info

            def load_plugin_ui(self, plugin_id, page, context):
                self.load_called = True

        manager = RuntimeManager()

        result = open_plugin_ui(manager, "demo", object(), api_client=None, browser_manager=None)

        self.assertFalse(result.loaded)
        self.assertEqual(result.status, "disabled")
        self.assertFalse(manager.load_called)


if __name__ == "__main__":
    unittest.main()
