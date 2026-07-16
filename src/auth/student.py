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

# 日志目录（原 src.core.constants，已内联）
import os
from pathlib import Path
def get_log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "ZX-Answering-Assistant" / "Logs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "ZX-Answering-Assistant"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "ZX-Answering-Assistant" / "logs"

STUDENT_LOGIN_LOG_FILE = "student_login.log"

# 创建自定义的 StreamHandler 来处理 Unicode 编码
class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            # 检查 stream 是否已被关闭或分离
            if not hasattr(self, 'stream') or self.stream is None:
                return

            msg = self.format(record)
            stream = self.stream

            # 检查 stream 是否还有效（避免程序结束时的错误）
            try:
                # 尝试使用 UTF-8 编码，如果失败则使用 errors='replace'
                if hasattr(stream, 'buffer') and not stream.buffer.closed:
                    stream.buffer.write(msg.encode('utf-8') + b'\n')
                elif hasattr(stream, 'closed') and not stream.closed:
                    stream.write(msg + self.terminator)
                else:
                    # Stream 已关闭，静默忽略
                    return
                self.flush()
            except (ValueError, OSError):
                # Stream 已被分离或关闭，静默忽略
                return

        except Exception:
            # 只有在严重错误时才调用 handleError（避免递归错误）
            try:
                self.handleError(record)
            except Exception:
                pass  # 静默忽略 handleError 中的错误

# 配置日志记录；日志属于用户运行数据，不写入源码目录。
log_dir = get_log_dir()
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / STUDENT_LOGIN_LOG_FILE, encoding='utf-8'),
        UTF8StreamHandler(sys.stdout)
    ]
)

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







