"""
插件管理器 - Plugin Manager

负责插件的扫描、加载、启用/禁用等生命周期管理
"""

import json
import sys
import importlib
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

        count = 0
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_file = plugin_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                plugin_info = PluginInfo.from_manifest(manifest_file)

                # 检查插件是否被禁用
                is_enabled = self.settings_manager.is_plugin_enabled(plugin_info.id)
                plugin_info.enabled = is_enabled

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
