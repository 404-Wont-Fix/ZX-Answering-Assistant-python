"""
插件管理器 - Plugin Manager

负责插件的扫描、加载、启用/禁用等生命周期管理
"""

import json
import sys
import importlib
import importlib.metadata as importlib_metadata
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from src.core.plugin_context import PluginContext
from src.core.config import get_settings_manager


@dataclass
class PluginInfo:
    """插件信息数据类"""
    id: str
    name: str
    version: str
    description: str
    icon: str
    author: str
    entry_ui: str
    entry_core: Optional[str]
    min_app_version: Optional[str]
    dependencies: List[str]
    enabled: bool
    path: Path

    @classmethod
    def from_manifest(cls, manifest_path: Path) -> 'PluginInfo':
        """
        从 manifest.json 创建 PluginInfo

        Args:
            manifest_path: manifest.json 文件路径

        Returns:
            PluginInfo 实例
        """
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            version=data.get('version', '1.0.0'),
            description=data.get('description', ''),
            icon=data.get('icon', 'extension'),
            author=data.get('author', ''),
            entry_ui=data.get('entry_ui', ''),
            entry_core=data.get('entry_core'),
            min_app_version=data.get('min_app_version'),
            dependencies=data.get('dependencies', []),
            enabled=data.get('enabled', True),
            path=manifest_path.parent
        )


class PluginManager:
    """
    插件管理器（单例模式）

    负责插件的扫描、加载、启用/禁用等生命周期管理
    """

    _instance: Optional['PluginManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化插件管理器"""
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return

        self._plugins: Dict[str, PluginInfo] = {}
        self._loaded_plugins: Dict[str, Any] = {}
        self._contexts: Dict[str, PluginContext] = {}
        self.settings_manager = get_settings_manager()
        self._initialized = True

        print("[PluginManager] Plugin manager initialized")

    def _check_package_installed(self, package_name: str) -> bool:
        """
        检查包是否已安装

        Args:
            package_name: 包名（可以是带版本的格式，如 package>=1.0.0）

        Returns:
            bool: 是否已安装
        """
        # 仅用于启动提示；实际版本约束由 pip 在安装阶段校验。
        clean_name = re.split(r"[<>=!~;\[\s]", package_name, maxsplit=1)[0].strip()
        if not clean_name:
            return True

        try:
            importlib_metadata.version(clean_name)
            return True
        except importlib_metadata.PackageNotFoundError:
            return False

    def _get_missing_plugin_dependencies(self, plugin_dir: Path) -> List[str]:
        """返回插件声明但当前环境尚未提供的包。"""
        requirements_file = plugin_dir / "requirements.txt"
        if not requirements_file.exists():
            return []

        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception as e:
            print(f"[PluginManager] Failed to read requirements.txt in {plugin_dir.name}: {e}")
            return []

        return [
            requirement
            for requirement in requirements
            if not self._check_package_installed(requirement)
        ]

    def _report_missing_dependencies(self, plugin_info: PluginInfo) -> List[str]:
        """提示缺少的依赖，不在应用启动或扫描期间修改运行环境。"""
        missing = self._get_missing_plugin_dependencies(plugin_info.path)
        if missing:
            requirements_file = plugin_info.path / "requirements.txt"
            print(f"[PluginManager] Missing dependencies for plugin: {plugin_info.name}")
            for requirement in missing:
                print(f"  - {requirement}")
            print(f"  Install with: {sys.executable} -m pip install -r {requirements_file}")
        return missing

    def _get_unavailable_plugin_dependencies(self, plugin_info: PluginInfo) -> List[str]:
        """返回缺失或未启用的插件级依赖。"""
        return [
            dependency_id
            for dependency_id in plugin_info.dependencies
            if dependency_id not in self._plugins or not self._plugins[dependency_id].enabled
        ]

    def _can_load_plugin(self, plugin_info: PluginInfo) -> bool:
        missing = self._get_unavailable_plugin_dependencies(plugin_info)
        if missing:
            print(
                f"[PluginManager] Plugin {plugin_info.id} requires enabled plugins: "
                f"{', '.join(missing)}"
            )
            return False
        return True

    @staticmethod
    def _validate_plugin_info(plugin_info: PluginInfo) -> None:
        """校验加载和路由所依赖的最低限度 manifest 字段。"""
        if not re.fullmatch(r"[a-z0-9_]+", plugin_info.id):
            raise ValueError("plugin id must contain only lowercase letters, digits, and underscores")
        if not plugin_info.name:
            raise ValueError("plugin name is required")
        if "." not in plugin_info.entry_ui:
            raise ValueError("entry_ui must use '<module>.<callable>' format")

    def scan_plugins(self, plugins_dir: Path = None) -> int:
        """
        扫描插件目录

        Args:
            plugins_dir: 插件目录路径，默认为项目根目录下的 plugins/

        Returns:
            int: 发现的插件数量
        """
        if plugins_dir is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            plugins_dir = project_root / "plugins"

        if not plugins_dir.exists():
            print(f"[PluginManager] Plugin directory not found: {plugins_dir}")
            return 0

        # Rebuild the discovered catalog so a rescan reflects the current disk state.
        self._plugins.clear()
        count = 0
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_file = plugin_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                plugin_info = PluginInfo.from_manifest(manifest_file)
                self._validate_plugin_info(plugin_info)
                if plugin_info.id in self._plugins:
                    raise ValueError(f"duplicate plugin id: {plugin_info.id}")

                # 检查插件是否被禁用
                is_enabled = self.settings_manager.is_plugin_enabled(plugin_info.id)
                plugin_info.enabled = is_enabled

                # 扫描阶段只提示缺少的依赖，启动应用不应改变运行环境。
                if plugin_info.enabled:
                    self._report_missing_dependencies(plugin_info)

                self._plugins[plugin_info.id] = plugin_info
                count += 1
                print(f"[PluginManager] Found plugin: {plugin_info.name} v{plugin_info.version}")

            except Exception as e:
                print(f"[PluginManager] Failed to load plugin {plugin_dir.name}: {e}")

        print(f"[PluginManager] Total plugins found: {count}")
        return count

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """
        获取插件信息

        Args:
            plugin_id: 插件ID

        Returns:
            PluginInfo 实例，如果不存在则返回 None
        """
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """
        获取所有插件信息

        Returns:
            Dict[str, PluginInfo]: 插件ID到插件信息的映射
        """
        return self._plugins.copy()

    def get_enabled_plugins(self) -> Dict[str, PluginInfo]:
        """
        获取所有已启用的插件

        Returns:
            Dict[str, PluginInfo]: 插件ID到插件信息的映射
        """
        return {
            pid: info for pid, info in self._plugins.items()
            if info.enabled
        }

    def load_plugin_ui(self, plugin_id: str, page, context: PluginContext):
        """
        加载插件 UI

        Args:
            plugin_id: 插件ID
            page: Flet 页面对象
            context: PluginContext 实例

        Returns:
            加载的 UI 控件，如果失败则返回 None
        """
        plugin_info = self._plugins.get(plugin_id)
        if not plugin_info:
            print(f"[PluginManager] Plugin not found: {plugin_id}")
            return None

        if not plugin_info.enabled:
            print(f"[PluginManager] Plugin is disabled: {plugin_id}")
            return None

        if not self._can_load_plugin(plugin_info):
            return None

        try:
            # 解析入口点
            module_name, func_name = plugin_info.entry_ui.split('.')

            # 添加插件目录到 Python 路径
            plugin_path = plugin_info.path
            if str(plugin_path.parent) not in sys.path:
                sys.path.insert(0, str(plugin_path.parent))

            # 导入插件模块
            module = importlib.import_module(f"{plugin_id}.{module_name}")

            # 获取 UI 创建函数
            create_func = getattr(module, func_name)

            # 创建 UI
            ui_control = create_func(page, context)

            print(f"[PluginManager] Plugin UI loaded successfully: {plugin_id}")
            return ui_control

        except Exception as e:
            print(f"[PluginManager] Failed to load plugin UI {plugin_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_plugin_core(self, plugin_id: str, context: PluginContext):
        """
        加载插件核心功能

        Args:
            plugin_id: 插件ID
            context: PluginContext 实例

        Returns:
            插件核心类实例，如果失败则返回 None
        """
        plugin_info = self._plugins.get(plugin_id)
        if not plugin_info:
            print(f"[PluginManager] Plugin not found: {plugin_id}")
            return None

        if not plugin_info.enabled:
            print(f"[PluginManager] Plugin is disabled: {plugin_id}")
            return None

        if not self._can_load_plugin(plugin_info):
            return None

        if not plugin_info.entry_core:
            print(f"[PluginManager] Plugin has no core entry point: {plugin_id}")
            return None

        try:
            # 解析入口点
            module_name, class_name = plugin_info.entry_core.split('.')

            # 添加插件目录到 Python 路径
            plugin_path = plugin_info.path
            if str(plugin_path.parent) not in sys.path:
                sys.path.insert(0, str(plugin_path.parent))

            # 导入插件模块
            module = importlib.import_module(f"{plugin_id}.{module_name}")

            # 获取核心类
            core_class = getattr(module, class_name)

            # 创建实例（传递 context）
            core_instance = core_class(context)

            print(f"[PluginManager] Plugin core loaded successfully: {plugin_id}")
            return core_instance

        except Exception as e:
            print(f"[PluginManager] Failed to load plugin core {plugin_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def enable_plugin(self, plugin_id: str) -> bool:
        """
        启用插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 是否成功
        """
        if plugin_id not in self._plugins:
            print(f"[PluginManager] Plugin not found: {plugin_id}")
            return False

        plugin_info = self._plugins[plugin_id]
        unavailable = self._get_unavailable_plugin_dependencies(plugin_info)
        if unavailable:
            print(
                f"[PluginManager] Cannot enable {plugin_id}; enable dependencies first: "
                f"{', '.join(unavailable)}"
            )
            return False

        self._report_missing_dependencies(plugin_info)

        success = self.settings_manager.set_plugin_enabled(plugin_id, True)
        if success:
            self._plugins[plugin_id].enabled = True
            print(f"[PluginManager] Plugin enabled: {plugin_id}")

        return success

    def disable_plugin(self, plugin_id: str) -> bool:
        """
        禁用插件

        Args:
            plugin_id: 插件ID

        Returns:
            bool: 是否成功
        """
        if plugin_id not in self._plugins:
            print(f"[PluginManager] Plugin not found: {plugin_id}")
            return False

        enabled_dependents = [
            info.id
            for info in self._plugins.values()
            if info.enabled and plugin_id in info.dependencies
        ]
        if enabled_dependents:
            print(
                f"[PluginManager] Cannot disable {plugin_id}; required by enabled plugins: "
                f"{', '.join(enabled_dependents)}"
            )
            return False

        success = self.settings_manager.set_plugin_enabled(plugin_id, False)
        if success:
            self._plugins[plugin_id].enabled = False
            print(f"[PluginManager] Plugin disabled: {plugin_id}")

        return success

    def create_plugin_context(self, plugin_id: str, api_client, browser_manager) -> PluginContext:
        """
        为插件创建上下文

        Args:
            plugin_id: 插件ID
            api_client: APIClient 实例
            browser_manager: BrowserManager 实例

        Returns:
            PluginContext 实例
        """
        context = PluginContext(
            plugin_id=plugin_id,
            api_client=api_client,
            browser_manager=browser_manager,
            settings_manager=self.settings_manager
        )

        self._contexts[plugin_id] = context
        return context


# 全局插件管理器实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
