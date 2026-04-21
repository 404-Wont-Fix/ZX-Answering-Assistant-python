"""
插件上下文 - Plugin Context

为插件提供依赖注入和资源共享机制
"""

import threading
from typing import Any, Callable, Optional


class PluginContext:
    """
    插件上下文类

    向插件注入所需的依赖和资源，确保插件不直接访问全局单例
    """

    def __init__(self, plugin_id: str, api_client, browser_manager, settings_manager):
        """
        初始化插件上下文

        Args:
            plugin_id: 插件唯一标识符
            api_client: APIClient 单例实例
            browser_manager: BrowserManager 单例实例
            settings_manager: SettingsManager 单例实例
        """
        self.plugin_id = plugin_id
        self._api_client = api_client
        self._browser_manager = browser_manager
        self._settings_manager = settings_manager

    @property
    def api_client(self):
        """获取 API 客户端实例（只读）"""
        return self._api_client

    @property
    def browser_manager(self):
        """获取浏览器管理器实例（只读）"""
        return self._browser_manager

    @property
    def settings_manager(self):
        """获取设置管理器实例（只读）"""
        return self._settings_manager

    def run_task(self, func: Callable, callback: Optional[Callable] = None, *args, **kwargs):
        """
        在后台线程安全地执行耗时操作

        Args:
            func: 要执行的函数
            callback: 完成后的回调函数（接收函数返回值）
            *args, **kwargs: 传递给函数的参数

        Returns:
            threading.Thread: 后台线程对象
        """
        def wrapper():
            try:
                result = func(*args, **kwargs)
                if callback:
                    # 使用 Flet 的线程安全方式调用回调
                    callback(result)
            except Exception as e:
                if callback:
                    callback({"error": str(e)})

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread

    def get_plugin_config(self, key: str, default: Any = None) -> Any:
        """
        获取插件特定配置

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值，如果不存在则返回默认值
        """
        return self._settings_manager.get_plugin_config(self.plugin_id, key, default)

    def set_plugin_config(self, key: str, value: Any) -> bool:
        """
        设置插件特定配置

        Args:
            key: 配置键
            value: 配置值

        Returns:
            bool: 是否设置成功
        """
        return self._settings_manager.set_plugin_config(self.plugin_id, key, value)

    def __repr__(self):
        return f"PluginContext(plugin_id='{self.plugin_id}')"
