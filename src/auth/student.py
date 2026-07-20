"""
学生端登录功能模块
用于获取学生端系统的access_token

已重构为使用统一的浏览器管理器 (src/browser_manager.py)
- 使用单浏览器 + 多上下文模式
- 支持与教师端、课程认证模块同时运行
- 上下文之间完全隔离，互不干扰
"""

from playwright.sync_api import Browser, Page, BrowserContext
from typing import Optional, List, Dict, Tuple
import time
import logging
import requests
import sys
import json

# 导入浏览器管理器
from src.core.browser import (
    get_browser_manager,
    BrowserType,
    run_in_thread_if_asyncio
)

# 导入Token管理器
from src.auth.token_manager import get_token_manager

# 从子模块 re-export（façade 兼容，保持 src.auth.student.* 可导入）
from ._student_browser_health import (
    check_and_recover_browser,
    cleanup_browser,
    close_browser,
    ensure_browser_alive,
    is_browser_alive,
)
from ._student_courses import get_student_courses, get_uncompleted_chapters
from ._student_browser_ops import (
    get_access_token_from_browser,
    get_browser_page,
    get_course_progress_from_page,
    navigate_to_course,
)
from ._student_login import (
    get_student_access_token,
    get_student_access_token_with_credentials,
    restart_browser,
)

# 日志初始化已迁移到 src.utils.logging.setup_app_logging()，由 main.py 启动期调用。
# 此处仅保留模块 logger；不再在 import 时副作用配置全局日志。
logger = logging.getLogger(__name__)

# 获取Token管理器实例
_token_manager = get_token_manager()


# ============================================================================
# 浏览器管理辅助函数（使用 BrowserManager）
# ============================================================================


# ==================== Access Token 管理函数 ====================

def set_access_token(token: str):
    """
    设置access_token缓存（向后兼容的包装函数）

    Args:
        token: access_token字符串
    """
    _token_manager.set_student_token(token)


def get_cached_access_token() -> Optional[str]:
    """
    获取缓存的access_token
    如果token不存在或已过期，则自动从浏览器获取

    Returns:
        Optional[str]: 有效的access_token，如果获取失败则返回None
    """
    # 先尝试从缓存获取
    cached_token = _token_manager.get_student_token()
    if cached_token:
        logger.info("✅ 使用缓存的access_token")
        return cached_token

    # 缓存不存在或已过期，从浏览器获取
    logger.info("💡 缓存中无有效access_token，尝试从浏览器获取...")
    new_token = get_access_token_from_browser()
    return new_token


def clear_access_token():
    """清除access_token缓存（向后兼容的包装函数）"""
    _token_manager.clear_student_token()
    logger.info("🗑️ access_token缓存已清除")


# ==================== 浏览器健康检查和恢复 ====================







