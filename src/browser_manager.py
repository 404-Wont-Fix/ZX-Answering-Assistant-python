"""
浏览器管理器模块

统一管理项目中所有 Playwright 浏览器实例，使用单浏览器 + 多上下文模式，
确保不同模块（学生端、教师端、课程认证）可以同时运行而互不干扰。

设计原理：
- 单个浏览器实例（Browser）共享，减少资源占用
- 每个模块拥有独立的浏览器上下文（BrowserContext）
- 上下文之间完全隔离（Cookie、Session、LocalStorage）
- 支持 AsyncIO 环境（Flet GUI 兼容）
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, Dict, Tuple
from enum import Enum
import threading
import logging
import asyncio

logger = logging.getLogger(__name__)


class BrowserType(Enum):
    """浏览器上下文类型枚举"""
    STUDENT = "student"                      # 学生端
    TEACHER = "teacher"                      # 教师端（答案提取）
    COURSE_CERTIFICATION = "course_cert"     # 课程认证


class BrowserManager:
    """
    浏览器管理器（单例模式）

    负责管理 Playwright 浏览器实例和多个上下文，确保：
    1. 整个应用只有一个浏览器实例
    2. 每个模块有独立的上下文，互不干扰
    3. 支持 AsyncIO 环境下的兼容性
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
            self._playwright = None
            self._browser: Optional[Browser] = None
            self._contexts: Dict[BrowserType, BrowserContext] = {}
            self._pages: Dict[BrowserType, Page] = {}
            self._headless = False
            self.initialized = True
            logger.info("浏览器管理器初始化完成")

    def start_browser(self, headless: bool = False) -> Browser:
        """
        启动浏览器实例（单例）

        Args:
            headless: 是否无头模式，默认 False（显示浏览器窗口）

        Returns:
            Browser: 浏览器实例
        """
        if self._browser is None:
            self._headless = headless
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=headless)
            logger.info(f"浏览器已启动 (headless={headless})")
        return self._browser

    def get_browser(self) -> Optional[Browser]:
        """
        获取浏览器实例（如果未启动则返回 None）

        Returns:
            Optional[Browser]: 浏览器实例或 None
        """
        return self._browser

    def create_context(self, browser_type: BrowserType, **kwargs) -> BrowserContext:
        """
        创建或获取指定类型的浏览器上下文

        Args:
            browser_type: 浏览器类型（STUDENT/TEACHER/COURSE_CERTIFICATION）
            **kwargs: 传递给 new_context() 的额外参数

        Returns:
            BrowserContext: 浏览器上下文实例
        """
        if browser_type in self._contexts:
            logger.debug(f"使用已存在的上下文: {browser_type.value}")
            return self._contexts[browser_type]

        if self._browser is None:
            self.start_browser()

        # 为不同类型的上下文设置默认参数
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
        """
        获取指定类型的上下文（如果不存在则返回 None）

        Args:
            browser_type: 浏览器类型

        Returns:
            Optional[BrowserContext]: 上下文实例或 None
        """
        return self._contexts.get(browser_type)

    def create_page(self, browser_type: BrowserType) -> Page:
        """
        在指定上下文中创建新页面

        Args:
            browser_type: 浏览器类型

        Returns:
            Page: 页面实例
        """
        context = self.get_context(browser_type)
        if context is None:
            context = self.create_context(browser_type)

        page = context.new_page()
        self._pages[browser_type] = page
        logger.debug(f"在 {browser_type.value} 上下文中创建新页面")
        return page

    def get_page(self, browser_type: BrowserType) -> Optional[Page]:
        """
        获取指定类型的页面（如果不存在则返回 None）

        Args:
            browser_type: 浏览器类型

        Returns:
            Optional[Page]: 页面实例或 None
        """
        return self._pages.get(browser_type)

    def get_context_and_page(self, browser_type: BrowserType) -> Tuple[Optional[BrowserContext], Optional[Page]]:
        """
        获取指定类型的上下文和页面

        Args:
            browser_type: 浏览器类型

        Returns:
            Tuple[Optional[BrowserContext], Optional[Page]]: (上下文, 页面) 元组
        """
        context = self.get_context(browser_type)
        page = self.get_page(browser_type)
        return context, page

    def close_context(self, browser_type: BrowserType):
        """
        关闭指定类型的上下文和页面

        Args:
            browser_type: 浏览器类型
        """
        if browser_type in self._pages:
            try:
                self._pages[browser_type].close()
            except Exception as e:
                logger.warning(f"关闭页面失败 ({browser_type.value}): {e}")
            del self._pages[browser_type]

        if browser_type in self._contexts:
            try:
                self._contexts[browser_type].close()
            except Exception as e:
                logger.warning(f"关闭上下文失败 ({browser_type.value}): {e}")
            del self._contexts[browser_type]

        logger.info(f"已关闭 {browser_type.value} 上下文")

    def close_all_contexts(self):
        """关闭所有上下文和页面"""
        for browser_type in list(self._pages.keys()):
            self.close_context(browser_type)
        logger.info("已关闭所有上下文")

    def close_browser(self):
        """关闭浏览器和 Playwright 实例"""
        self.close_all_contexts()

        if self._browser:
            try:
                self._browser.close()
            except Exception as e:
                logger.warning(f"关闭浏览器失败: {e}")
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning(f"停止 Playwright 失败: {e}")
            self._playwright = None

        logger.info("浏览器已完全关闭")

    def is_browser_alive(self) -> bool:
        """
        检查浏览器是否存活

        Returns:
            bool: 浏览器是否连接正常
        """
        if self._browser is None:
            return False
        try:
            # 尝试访问浏览器的上下文列表来检查连接状态
            _ = self._browser.contexts
            return True
        except Exception as e:
            logger.warning(f"浏览器健康检查失败: {e}")
            return False

    def is_context_alive(self, browser_type: BrowserType) -> bool:
        """
        检查指定上下文是否存活

        Args:
            browser_type: 浏览器类型

        Returns:
            bool: 上下文是否存活
        """
        if not self.is_browser_alive():
            return False
        context = self.get_context(browser_type)
        if context is None:
            return False
        try:
            # 尝试访问上下文的页面列表来检查状态
            _ = context.pages
            return True
        except Exception as e:
            logger.warning(f"上下文健康检查失败 ({browser_type.value}): {e}")
            return False

    def cleanup_type(self, browser_type: BrowserType):
        """
        清理指定类型的所有资源

        Args:
            browser_type: 浏览器类型
        """
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


def start_browser(headless: bool = False) -> Browser:
    """快捷方式：启动浏览器"""
    return get_browser_manager().start_browser(headless=headless)


def get_browser() -> Optional[Browser]:
    """快捷方式：获取浏览器实例"""
    return get_browser_manager().get_browser()


def create_context(browser_type: BrowserType, **kwargs) -> BrowserContext:
    """快捷方式：创建上下文"""
    return get_browser_manager().create_context(browser_type, **kwargs)


def get_context(browser_type: BrowserType) -> Optional[BrowserContext]:
    """快捷方式：获取上下文"""
    return get_browser_manager().get_context(browser_type)


def create_page(browser_type: BrowserType) -> Page:
    """快捷方式：创建页面"""
    return get_browser_manager().create_page(browser_type)


def get_page(browser_type: BrowserType) -> Optional[Page]:
    """快捷方式：获取页面"""
    return get_browser_manager().get_page(browser_type)


def get_context_and_page(browser_type: BrowserType) -> Tuple[Optional[BrowserContext], Optional[Page]]:
    """快捷方式：获取上下文和页面"""
    return get_browser_manager().get_context_and_page(browser_type)


def close_context(browser_type: BrowserType):
    """快捷方式：关闭上下文"""
    get_browser_manager().close_context(browser_type)


def close_browser():
    """快捷方式：关闭浏览器"""
    get_browser_manager().close_browser()


def is_browser_alive() -> bool:
    """快捷方式：检查浏览器是否存活"""
    return get_browser_manager().is_browser_alive()


def is_context_alive(browser_type: BrowserType) -> bool:
    """快捷方式：检查上下文是否存活"""
    return get_browser_manager().is_context_alive(browser_type)


# ============================================================================
# AsyncIO 兼容性支持
# ============================================================================

def run_in_thread_if_asyncio(func, *args, **kwargs):
    """
    如果当前在 AsyncIO 环境中，在新线程中执行函数
    用于兼容 Flet GUI 的 AsyncIO 环境

    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数的返回值
    """
    try:
        asyncio.get_running_loop()
        # 检测到 asyncio 环境，使用新线程
        logger.debug("检测到 asyncio 环境，在新线程中执行")

        result = [None]
        exception = [None]

        def run_in_new_loop():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
            finally:
                new_loop.close()

        thread = threading.Thread(target=run_in_new_loop)
        thread.start()
        thread.join()

        if exception[0]:
            raise exception[0]

        return result[0]

    except RuntimeError:
        # 没有 asyncio 事件循环，直接执行
        return func(*args, **kwargs)
