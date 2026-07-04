"""
核心模块

包含应用的核心业务逻辑，如浏览器管理、API客户端、配置管理等。
"""

from importlib import import_module


_EXPORTS = {
    # 浏览器
    'BrowserManager': ('src.core.browser', 'BrowserManager'),
    'get_browser_manager': ('src.core.browser', 'get_browser_manager'),
    'BrowserType': ('src.core.browser', 'BrowserType'),
    # API客户端
    'APIClient': ('src.core.api_client', 'APIClient'),
    'get_api_client': ('src.core.api_client', 'get_api_client'),
    # 配置
    'SettingsManager': ('src.core.config', 'SettingsManager'),
    'get_settings_manager': ('src.core.config', 'get_settings_manager'),
    'APIRateLevel': ('src.core.config', 'APIRateLevel'),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    """按需加载兼容导出，避免 import src.core 时触发重依赖导入。"""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
