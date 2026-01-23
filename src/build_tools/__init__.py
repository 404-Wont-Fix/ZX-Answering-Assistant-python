"""
构建模块
包含项目打包相关的所有功能
"""

from .browser_handler import (
    copy_browser_to_project,
    verify_browser,
    get_browser_size,
    ensure_browser_ready
)

from .flet_handler import (
    copy_flet_to_project,
    verify_flet,
    get_flet_size,
    ensure_flet_ready,
    setup_flet_env,
    copy_flet_to_temp_on_startup
)

__all__ = [
    # Browser handlers
    "copy_browser_to_project",
    "verify_browser",
    "get_browser_size",
    "ensure_browser_ready",
    # Flet handlers
    "copy_flet_to_project",
    "verify_flet",
    "get_flet_size",
    "ensure_flet_ready",
    "setup_flet_env",
    "copy_flet_to_temp_on_startup"
]
