import importlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"
for import_path in (PLUGINS_DIR, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))


class PluginEntryPointTests(unittest.TestCase):
    def test_plugin_entry_modules_do_not_mutate_sys_path(self):
        offenders = []

        for plugin_dir in sorted(path for path in PLUGINS_DIR.iterdir() if path.is_dir()):
            for module_name in ("__init__.py", "ui.py", "core.py"):
                module_path = plugin_dir / module_name
                if not module_path.exists():
                    continue
                source = module_path.read_text(encoding="utf-8")
                if "sys.path.insert" in source or "sys.path.append" in source:
                    offenders.append(str(module_path.relative_to(ROOT)))

        self.assertEqual(offenders, [])

    def test_enabled_plugin_entry_points_are_importable(self):
        failures = []

        for manifest_path in sorted(PLUGINS_DIR.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not manifest.get("enabled", True):
                continue

            plugin_id = manifest["id"]
            for key in ("entry_ui", "entry_core"):
                entry_point = manifest.get(key)
                if not entry_point:
                    continue

                module_name, attr_name = entry_point.split(".")
                try:
                    module = importlib.import_module(f"{plugin_id}.{module_name}")
                    getattr(module, attr_name)
                except Exception as exc:
                    failures.append(f"{plugin_id}.{entry_point}: {exc!r}")

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
