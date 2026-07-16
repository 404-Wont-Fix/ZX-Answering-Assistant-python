"""学生端浏览器健康检查/恢复（自洽簇，无登录依赖）。

从 src/auth/student.py 抽出。cleanup_browser 清理浏览器 + token 缓存；
ensure_browser_alive/check_and_recover_browser 基于它做健康检查。
restart_browser 留在 student.py façade（依赖 get_student_access_token，是 health↔login 环）。
"""

import logging

from src.core.browser import get_browser_manager, BrowserType
from src.auth.token_manager import get_token_manager

logger = logging.getLogger(__name__)
_token_manager = get_token_manager()


def close_browser():
    """关闭学生端浏览器上下文（不关整个浏览器，可能其他模块在用）。"""
    try:
        manager = get_browser_manager()
        manager.cleanup_type(BrowserType.STUDENT)
        logger.info("学生端浏览器上下文已关闭")
    except Exception as e:
        logger.error(f"关闭浏览器时发生错误: {str(e)}")


def is_browser_alive() -> bool:
    """检查浏览器实例是否仍然存活。"""
    manager = get_browser_manager()
    return manager.is_browser_alive()


def ensure_browser_alive() -> bool:
    """确保浏览器实例存活，挂掉则清理并准备重新登录。"""
    if is_browser_alive():
        return True
    logger.warning("⚠️ 检测到浏览器已挂掉，清理旧实例...")
    cleanup_browser()
    logger.info("✅ 浏览器实例已清理，请重新登录")
    return False


def cleanup_browser():
    """强制清理学生端浏览器实例（包括挂掉的浏览器）+ 清 token 缓存。"""
    try:
        manager = get_browser_manager()
        manager.cleanup_type(BrowserType.STUDENT)
    except Exception as e:
        logger.error(f"清理浏览器时发生错误: {str(e)}")
    finally:
        _token_manager.clear_student_token()
        logger.info("✅ 学生端浏览器实例已强制清理")


def check_and_recover_browser() -> bool:
    """检查浏览器状态并尝试恢复。"""
    if not is_browser_alive():
        logger.warning("⚠️ 浏览器不可用，准备清理...")
        cleanup_browser()
        return False
    return True
