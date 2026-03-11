"""
构建工具模块
包含浏览器处理和源码编译功能
"""

from .browser_handler import (
    get_playwright_browser_version,
    copy_browser_to_project,
    verify_browser,
    get_browser_size,
    ensure_browser_ready
)

from .flet_handler import (
    copy_flet_to_project,
    verify_flet,
    get_flet_size,
    ensure_flet_ready
)

from .compiler import (
    compile_to_pyc,
    clean_source_files
)

__all__ = [
    # Browser handlers
    "get_playwright_browser_version",
    "copy_browser_to_project",
    "verify_browser",
    "get_browser_size",
    "ensure_browser_ready",
    # Flet handlers
    "copy_flet_to_project",
    "verify_flet",
    "get_flet_size",
    "ensure_flet_ready",
    # Compiler
    "compile_to_pyc",
    "clean_source_files",
]
