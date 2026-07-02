"""
插件运行时辅助函数。

该模块只负责插件 UI 的加载流程，不构建任何 Flet 页面布局。
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PluginOpenResult:
    """插件打开结果。"""

    status: str
    plugin_info: Any = None
    control: Any = None
    message: str = ""

    @property
    def loaded(self) -> bool:
        return self.status == "loaded"


def open_plugin_ui(
    plugin_manager,
    plugin_id: str,
    page,
    api_client=None,
    browser_manager=None,
) -> PluginOpenResult:
    """创建插件上下文并加载插件 UI。"""
    plugin_info = plugin_manager.get_plugin_info(plugin_id)
    if not plugin_info:
        return PluginOpenResult(
            status="not_found",
            message=f"Plugin not found: {plugin_id}",
        )

    if not plugin_info.enabled:
        return PluginOpenResult(
            status="disabled",
            plugin_info=plugin_info,
            message=f"Plugin is disabled: {plugin_id}",
        )

    if api_client is None:
        from src.core.api_client import get_api_client

        api_client = get_api_client()

    if browser_manager is None:
        from src.core.browser import get_browser_manager

        browser_manager = get_browser_manager()

    context = plugin_manager.create_plugin_context(
        plugin_id=plugin_id,
        api_client=api_client,
        browser_manager=browser_manager,
        page=page,
    )
    plugin_ui = plugin_manager.load_plugin_ui(plugin_id, page, context)

    if not plugin_ui:
        return PluginOpenResult(
            status="load_failed",
            plugin_info=plugin_info,
            message=f"Failed to load plugin UI: {plugin_id}",
        )

    return PluginOpenResult(
        status="loaded",
        plugin_info=plugin_info,
        control=plugin_ui,
    )
