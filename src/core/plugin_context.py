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

    def __init__(self, plugin_id: str, api_client, browser_manager, settings_manager, page=None):
        """
        初始化插件上下文

        Args:
            plugin_id: 插件唯一标识符
            api_client: APIClient 单例实例
            browser_manager: BrowserManager 单例实例
            settings_manager: SettingsManager 单例实例
            page: Flet Page 实例，用于线程安全的 UI 更新调度
        """
        self.plugin_id = plugin_id
        self._api_client = api_client
        self._browser_manager = browser_manager
        self._settings_manager = settings_manager
        self._page = page
        self._resources = []

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

    @property
    def page(self):
        """获取 Flet Page 实例（只读，可能为空）"""
        return self._page

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
        def schedule_update():
            if not self._page:
                return

            update = getattr(self._page, "schedule_update", None)
            if callable(update):
                update()
                return

            update = getattr(self._page, "update", None)
            if callable(update):
                update()

        def wrapper():
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                result = {"error": str(e)}

            if callback:
                callback(result)
                schedule_update()

        page_runner = getattr(self._page, "run_thread", None) if self._page else None
        if callable(page_runner):
            try:
                return page_runner(wrapper)
            except Exception as e:
                print(f"[PluginContext] page.run_thread failed, falling back to thread: {e}")

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread

    def register_resource(self, resource):
        """
        注册需要随插件上下文一起释放的资源。

        资源对象可实现 cleanup()、dispose() 或 close()。
        """
        if resource is not None and resource not in self._resources:
            self._resources.append(resource)
        return resource

    def cleanup(self):
        """释放通过 register_resource() 注册的资源。"""
        resources = list(self._resources)
        self._resources.clear()

        for resource in resources:
            self._cleanup_resource(resource)

    @staticmethod
    def _cleanup_resource(resource):
        for method_name in ("cleanup", "dispose", "close"):
            cleanup = getattr(resource, method_name, None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception as e:
                    print(f"[PluginContext] Failed to {method_name} resource: {e}")
                return

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
