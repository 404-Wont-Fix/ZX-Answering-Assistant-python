"""
浏览器管理器模块

统一管理项目中所有 Playwright 浏览器实例，使用单浏览器 + 多上下文模式，
确保不同模块（学生端、教师端、课程认证、云考试）可以同时运行而互不干扰。

设计原理：
- 单个浏览器实例（Browser）共享，减少资源占用
- 每个模块拥有独立的浏览器上下文（BrowserContext）
- 上下文之间完全隔离（Cookie、Session、LocalStorage）
- 支持 AsyncIO 环境（Flet GUI 兼容）
- 所有 Playwright 操作在专用工作线程中执行，避免 greenlet 线程切换问题
- 支持系统浏览器（Chrome/Edge）和 Playwright 内置浏览器

拆分结构：
- `_browser_installer.py` — 浏览器安装/检测/通道选择（无状态函数）
- `_worker_engine.py`   — 工作线程引擎（WorkerEngine 类）
- 本文件（browser.py）  — BrowserManager 生命周期 + context/page 管理 + façade 重导出
"""

from playwright.sync_api import (
    sync_playwright,
    Browser,
    BrowserContext,
    Page,
    Error as PlaywrightError,
)
from typing import Optional, Dict, Tuple
from enum import Enum
import threading
import logging
import os

from src.core._browser_installer import (
    detect_system_browsers,
    ensure_browser_installed as _ensure_browser_installed_raw,
    get_available_browser_channel as _get_available_browser_channel,
)
from src.core._worker_engine import WorkerEngine, force_kill_process_tree

logger = logging.getLogger(__name__)
_NO_DISPATCH = object()


# ============================================================================
# 共享枚举与常量
# ============================================================================

class BrowserChannel(Enum):
    """浏览器通道枚举"""
    CHROME = "chrome"           # Google Chrome (系统安装)
    MSEdge = "msedge"          # Microsoft Edge (系统安装)
    CHROMIUM = "chromium"       # Playwright 内置 Chromium
    BUNDLED = ""               # Playwright 打包的 Chromium (默认)

    @classmethod
    def from_string(cls, channel_str: str) -> 'BrowserChannel':
        """从字符串获取浏览器通道"""
        if not channel_str:
            return cls.BUNDLED
        for channel in cls:
            if channel.value == channel_str.lower():
                return channel
        return cls.BUNDLED  # 默认使用打包浏览器

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            BrowserChannel.CHROME: "Google Chrome (系统)",
            BrowserChannel.MSEdge: "Microsoft Edge (系统)",
            BrowserChannel.CHROMIUM: "Chromium (Playwright)",
            BrowserChannel.BUNDLED: "Chromium (Playwright 内置)"
        }
        return names[self]


class BrowserType(Enum):
    """浏览器上下文类型枚举"""
    STUDENT = "student"                      # 学生端
    TEACHER = "teacher"                      # 教师端（答案提取）
    COURSE_CERTIFICATION = "course_cert"     # 课程认证
    CLOUD_EXAM = "cloud_exam"                # 云考试


# ---- 共享 BrowserContext 默认参数（消除 teacher/student/extractor/certification 4 处重复） ----
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
)


def create_browser_context(
    manager: 'BrowserManager',
    browser_type: BrowserType,
    *,
    viewport: dict = None,
    user_agent: str = None,
) -> tuple:
    """创建浏览器上下文和页面的标准入口。

    消除 4 个模块各自手写 viewport + user_agent + create_context + create_page 的样板。

    Args:
        manager: BrowserManager 单例
        browser_type: 上下文类型
        viewport: 视口大小（默认 DEFAULT_VIEWPORT）
        user_agent: User-Agent（默认 DEFAULT_USER_AGENT）

    Returns:
        tuple: (context, page)
    """
    context = manager.create_context(
        browser_type,
        viewport=viewport or DEFAULT_VIEWPORT,
        user_agent=user_agent or DEFAULT_USER_AGENT,
    )
    page = manager.create_page(browser_type)
    return context, page


# ============================================================================
# BrowserManager（生命周期 + context/page 管理）
# ============================================================================

class BrowserManager:
    """
    浏览器管理器（单例模式）

    负责管理 Playwright 浏览器实例和多个上下文，确保：
    1. 整个应用只有一个浏览器实例
    2. 每个模块有独立的上下文，互不干扰
    3. 支持 AsyncIO 环境下的兼容性
    4. 所有 Playwright 操作在专用工作线程中执行
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化管理器（只执行一次）"""
        if not hasattr(self, 'initialized'):
            # 浏览器状态
            self._playwright = None
            self._browser: Optional[Browser] = None
            self._contexts: Dict[BrowserType, BrowserContext] = {}
            self._pages: Dict[BrowserType, Page] = {}
            self._headless = False
            self._browser_checked = False

            # 跨线程保护（reset_worker 清理浏览器状态时使用）
            self._state_lock = threading.RLock()

            # 工作线程引擎（委托所有线程/队列管理）
            self._engine = WorkerEngine(
                state_lock=self._state_lock,
                cleanup_callback=self._clear_browser_state,
            )

            self.initialized = True
            logger.info("浏览器管理器初始化完成")

    # ---- 浏览器状态清理（WorkerEngine.reset_worker 回调） ----

    def _clear_browser_state(self):
        """在 _state_lock 保护下清理浏览器状态。由 WorkerEngine.reset_worker 调用。"""
        self._browser = None
        self._playwright = None
        self._contexts.clear()
        self._pages.clear()

    # ---- 内部辅助 ----

    def is_worker_thread(self) -> bool:
        """判断当前代码是否运行在 Playwright 专用工作线程。"""
        return self._engine.is_worker_thread()

    def _dispatch_to_worker_if_needed(self, func, *args, **kwargs):
        """将 Playwright 操作统一调度到专用工作线程，避免跨线程冲突。"""
        if self._engine.is_worker_thread():
            return _NO_DISPATCH
        return self._engine.submit_task(func, *args, **kwargs)

    def _discard_dead_browser_if_needed(self):
        """清理已断开的浏览器引用，下一次调用会重新启动。"""
        if self._browser is None:
            return

        try:
            if self._browser.is_connected():
                return
        except (PlaywrightError, RuntimeError) as e:
            logger.debug(f"检查浏览器连接状态失败: {e}")

        logger.warning("检测到浏览器实例已断开，清理旧引用")
        self._contexts.clear()
        self._pages.clear()
        self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except (PlaywrightError, RuntimeError) as e:
                logger.debug(f"清理断开 Playwright 实例失败: {e}")
            finally:
                self._playwright = None

    @staticmethod
    def _is_page_usable(page: Optional[Page]) -> bool:
        """检查页面对象是否仍可用。"""
        if page is None:
            return False
        try:
            return not page.is_closed()
        except (PlaywrightError, RuntimeError):
            return False

    @staticmethod
    def _is_context_usable(context: Optional[BrowserContext]) -> bool:
        """检查上下文对象是否仍可用。"""
        if context is None:
            return False
        try:
            _ = context.pages
            return True
        except (PlaywrightError, RuntimeError):
            return False

    # ---- 浏览器安装代理（委托 _browser_installer） ----

    def ensure_browser_installed(self, local_browser_path: str = None) -> Tuple[bool, str]:
        """确保浏览器已安装。代理到 _browser_installer.ensure_browser_installed。"""
        if self._browser_checked:
            return True, ""
        ok, msg, checked = _ensure_browser_installed_raw(local_browser_path)
        if checked:
            self._browser_checked = True
        return ok, msg

    def get_available_browser_channel(self) -> Tuple[str, str]:
        """获取可用的浏览器通道。代理到 _browser_installer.get_available_browser_channel。"""
        return _get_available_browser_channel()

    @staticmethod
    def detect_system_browsers() -> Dict[str, str]:
        """检测系统中已安装的浏览器。代理到 _browser_installer.detect_system_browsers。"""
        return detect_system_browsers()

    # ---- 浏览器生命周期 ----

    def start_browser(self, headless: bool = None, local_browser_path: str = None, auto_install: bool = True) -> Browser:
        """
        启动浏览器实例（单例）

        Args:
            headless: 是否无头模式，默认从设置读取
            local_browser_path: 本地浏览器路径（可选），如果未指定则从配置文件读取
            auto_install: 是否自动安装浏览器（默认True）

        Returns:
            Browser: 浏览器实例

        Raises:
            RuntimeError: 如果浏览器安装失败且auto_install为True
        """
        dispatched = self._dispatch_to_worker_if_needed(
            self.start_browser,
            headless,
            local_browser_path,
            auto_install
        )
        if dispatched is not _NO_DISPATCH:
            return dispatched

        self._discard_dead_browser_if_needed()

        if self._browser is None:
            # 获取浏览器通道（系统浏览器或内置浏览器）
            browser_channel, channel_info = self.get_available_browser_channel()
            logger.info(f"[INFO] {channel_info}")

            # 如果使用系统浏览器，跳过浏览器安装检查
            if browser_channel:
                logger.info("[OK] 使用系统浏览器，跳过 Playwright 浏览器安装检查")
                self._browser_checked = True
            else:
                # 使用 Playwright 内置浏览器，进行安装检查
                if local_browser_path is None:
                    try:
                        from src.core.config import get_settings_manager
                        settings = get_settings_manager()
                        local_browser_path = settings.get_local_browser_path()
                        if local_browser_path:
                            logger.info(f"从配置文件读取本地浏览器路径: {local_browser_path}")
                    except (ImportError, AttributeError, KeyError, TypeError, ValueError, OSError) as e:
                        logger.debug(f"读取本地浏览器路径配置失败: {e}")

                if auto_install:
                    success, error_msg = self.ensure_browser_installed(local_browser_path)
                    if not success:
                        raise RuntimeError(error_msg)
                elif local_browser_path:
                    from src.core._browser_installer import install_from_local_directory
                    install_from_local_directory(local_browser_path)

            # 如果没有指定 headless 参数，从配置文件读取
            if headless is None:
                try:
                    from src.core.config import get_settings_manager
                    settings = get_settings_manager()
                    headless = settings.get_browser_headless()
                    logger.info(f"从配置文件读取无头模式设置: headless={headless}")
                except (ImportError, AttributeError, KeyError, TypeError, ValueError, OSError) as e:
                    headless = False  # 默认显示浏览器
                    logger.debug(f"无法读取配置文件，使用默认设置（显示浏览器）: {e}")

            self._headless = headless
            self._playwright = sync_playwright().start()

            launch_args = {
                'headless': headless,
            }

            if browser_channel:
                launch_args['channel'] = browser_channel
                logger.info(f"[OK] 设置浏览器通道: {browser_channel}")
            else:
                if headless:
                    launch_args['args'] = ['--headless=new']

            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                launch_args['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
                logger.info(f"使用自定义浏览器路径: {os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']}")

            self._browser = self._playwright.chromium.launch(**launch_args)

            mode_str = "无头模式（隐藏浏览器）" if headless else "有头模式（显示浏览器）"
            browser_info = f"浏览器通道: {browser_channel if browser_channel else 'Playwright 内置'}, {mode_str}"
            logger.info(f"✅ 浏览器已启动 - {browser_info}")

        return self._browser

    def get_browser(self) -> Optional[Browser]:
        """获取浏览器实例（如果未启动则返回 None）"""
        return self._browser

    # ---- Context / Page 管理 ----

    def create_context(self, browser_type: BrowserType, **kwargs) -> BrowserContext:
        """创建或获取指定类型的浏览器上下文。"""
        dispatched = self._dispatch_to_worker_if_needed(self.create_context, browser_type, **kwargs)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        self._discard_dead_browser_if_needed()

        if browser_type in self._contexts and self._is_context_usable(self._contexts[browser_type]):
            logger.debug(f"使用已存在的上下文: {browser_type.value}")
            return self._contexts[browser_type]
        elif browser_type in self._contexts:
            logger.warning(f"上下文不可用，重新创建: {browser_type.value}")
            self._contexts.pop(browser_type, None)
            self._pages.pop(browser_type, None)

        if self._browser is None:
            self.start_browser()

        default_kwargs = {
            'user_agent': f'ZXAssistant/1.0 ({browser_type.value})',
            'viewport': {'width': 1280, 'height': 720},
            'locale': 'zh-CN',
            'timezone_id': 'Asia/Shanghai',
        }
        default_kwargs.update(kwargs)

        context = self._browser.new_context(**default_kwargs)
        self._contexts[browser_type] = context
        logger.info(f"创建浏览器上下文: {browser_type.value}")
        return context

    def get_context(self, browser_type: BrowserType) -> Optional[BrowserContext]:
        """获取指定类型的上下文（如果不存在则返回 None）"""
        return self._contexts.get(browser_type)

    def create_page(self, browser_type: BrowserType) -> Page:
        """在指定上下文中创建新页面。"""
        dispatched = self._dispatch_to_worker_if_needed(self.create_page, browser_type)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        self._discard_dead_browser_if_needed()

        context = self.get_context(browser_type)
        if not self._is_context_usable(context):
            context = self.create_context(browser_type)

        old_page = self._pages.get(browser_type)
        if old_page is not None:
            try:
                if not old_page.is_closed():
                    old_page.close()
                    logger.debug(f"已关闭旧页面: {browser_type.value}")
            except (PlaywrightError, RuntimeError) as e:
                logger.debug(f"关闭旧页面失败 ({browser_type.value}): {e}")

        page = context.new_page()
        self._pages[browser_type] = page
        logger.debug(f"在 {browser_type.value} 上下文中创建新页面")
        return page

    def get_page(self, browser_type: BrowserType) -> Optional[Page]:
        """获取指定类型的页面（如果不存在则返回 None）"""
        return self._pages.get(browser_type)

    def get_context_and_page(self, browser_type: BrowserType) -> Tuple[Optional[BrowserContext], Optional[Page]]:
        """获取指定类型的上下文和页面。"""
        context = self.get_context(browser_type)
        page = self.get_page(browser_type)
        return context, page

    def close_context(self, browser_type: BrowserType):
        """关闭指定类型的上下文和页面。"""
        dispatched = self._dispatch_to_worker_if_needed(self.close_context, browser_type)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        if browser_type not in self._contexts:
            old_page = self._pages.pop(browser_type, None)
            if old_page is not None:
                try:
                    if not old_page.is_closed():
                        old_page.close()
                except (PlaywrightError, RuntimeError) as e:
                    logger.debug(f"关闭孤立页面失败 ({browser_type.value}): {e}")
            logger.debug(f"上下文 {browser_type.value} 不存在")
            return

        context = self._contexts[browser_type]

        try:
            if context:
                context.close()
                logger.debug(f"上下文已关闭 ({browser_type.value})")
        except (PlaywrightError, RuntimeError, OSError) as e:
            if "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                logger.warning(f"关闭上下文失败 ({browser_type.value}): {e}")
        finally:
            if browser_type in self._pages:
                self._pages[browser_type] = None
                del self._pages[browser_type]
            self._contexts[browser_type] = None
            del self._contexts[browser_type]

        logger.info(f"已关闭 {browser_type.value} 上下文")

    def close_all_contexts(self):
        """关闭所有上下文和页面。"""
        dispatched = self._dispatch_to_worker_if_needed(self.close_all_contexts)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        for browser_type in list(set(self._contexts.keys()) | set(self._pages.keys())):
            self.close_context(browser_type)
        logger.info("已关闭所有上下文")

    def close_browser(self):
        """关闭浏览器和 Playwright 实例。"""
        dispatched = self._dispatch_to_worker_if_needed(self.close_browser)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        logger.info("开始关闭浏览器和 Playwright 实例...")

        self.close_all_contexts()

        if self._browser:
            try:
                try:
                    if self._browser.is_connected():
                        self._browser.close()
                        logger.info("浏览器已关闭")
                    else:
                        logger.info("浏览器已断开连接，跳过关闭操作")
                except (PlaywrightError, RuntimeError, OSError) as e:
                    if "greenlet" in str(e) or "Cannot switch" in str(e):
                        logger.warning("检测到 greenlet 线程切换错误，强制清理浏览器引用")
                    elif "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                        logger.warning(f"关闭浏览器失败: {e}")
            finally:
                self._browser = None
                logger.debug("浏览器引用已清理")

        if self._playwright:
            try:
                self._playwright.stop()
                logger.info("Playwright 已停止")
            except (PlaywrightError, RuntimeError, OSError) as e:
                if "greenlet" in str(e) or "Cannot switch" in str(e):
                    logger.warning("检测到 greenlet 线程切换错误，强制清理 Playwright 引用")
                elif "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                    logger.warning(f"停止 Playwright 失败: {e}")
            finally:
                self._playwright = None
                logger.debug("Playwright 引用已清理")

        logger.info("浏览器资源已完全清理")

    # ---- Worker 引擎代理 ----

    def submit_task(self, func, *args, **kwargs):
        """提交任务到工作线程执行。委托给 WorkerEngine。"""
        return self._engine.submit_task(func, *args, **kwargs)

    def reset_worker(self, reason: str = "manual"):
        """重置 worker 线程。委托给 WorkerEngine。"""
        self._engine.reset_worker(reason=reason)

    def force_kill_process_tree(self, timeout: float = 2.0) -> None:
        """强制终止子进程树。代理到 _worker_engine.force_kill_process_tree。"""
        force_kill_process_tree(timeout=timeout)

    # ---- 健康检查 ----

    def is_browser_alive(self) -> bool:
        """检查浏览器是否存活。"""
        dispatched = self._dispatch_to_worker_if_needed(self.is_browser_alive)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        if self._browser is None:
            logger.debug("浏览器实例为 None")
            return False
        try:
            if not self._browser.is_connected():
                logger.warning("浏览器已断开连接")
                return False
            _ = self._browser.contexts
            _ = self._browser.version
            logger.debug("浏览器健康检查通过")
            return True
        except (PlaywrightError, RuntimeError) as e:
            logger.warning(f"浏览器健康检查失败: {e}")
            return False

    def is_context_alive(self, browser_type: BrowserType) -> bool:
        """检查指定上下文是否存活。"""
        dispatched = self._dispatch_to_worker_if_needed(self.is_context_alive, browser_type)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        if not self.is_browser_alive():
            logger.debug(f"浏览器未存活，跳过上下文检查 ({browser_type.value})")
            return False

        context = self.get_context(browser_type)
        if context is None:
            logger.debug(f"上下文不存在 ({browser_type.value})")
            return False

        try:
            _ = context.pages
            logger.debug(f"上下文健康检查通过 ({browser_type.value})")
            return True
        except (PlaywrightError, RuntimeError) as e:
            logger.warning(f"上下文健康检查失败 ({browser_type.value}): {e}")
            return False

    def cleanup_type(self, browser_type: BrowserType):
        """清理指定类型的所有资源。"""
        self.close_context(browser_type)
        logger.info(f"已清理 {browser_type.value} 的所有资源")


# ============================================================================
# 全局访问函数（提供更简洁的 API）
# ============================================================================

_manager_instance: Optional[BrowserManager] = None
_manager_lock = threading.Lock()


def get_browser_manager() -> BrowserManager:
    """
    获取浏览器管理器单例实例（线程安全）

    Returns:
        BrowserManager: 管理器实例
    """
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = BrowserManager()
    return _manager_instance


# ============================================================================
# AsyncIO 兼容性支持
# ============================================================================

def run_in_thread_if_asyncio(func, *args, **kwargs):
    """
    始终在工作线程中执行函数，避免 greenlet 线程切换问题
    确保 Playwright 操作都在同一个工作线程中执行

    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数的返回值
    """
    manager = get_browser_manager()
    return manager.submit_task(func, *args, **kwargs)
