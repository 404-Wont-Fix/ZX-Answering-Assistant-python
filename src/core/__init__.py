"""
核心模块

包含应用的核心业务逻辑，如浏览器管理、API客户端、配置管理等。
"""

# 状态管理
from src.core.app_state import AppState, get_app_state

# 常量定义
from src.core import constants

# 浏览器管理
from src.core.browser import BrowserManager, get_browser_manager, BrowserType

# API客户端
from src.core.api_client import APIClient, get_api_client

# 配置管理
from src.core.config import SettingsManager, get_settings_manager, APIRateLevel

__all__ = [
    # 状态管理
    'AppState', 'get_app_state',
    # 常量
    'constants',
    # 浏览器
    'BrowserManager', 'get_browser_manager', 'BrowserType',
    # API客户端
    'APIClient', 'get_api_client',
    # 配置
    'SettingsManager', 'get_settings_manager', 'APIRateLevel',
]
