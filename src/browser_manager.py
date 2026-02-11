"""
浏览器管理器模块

统一管理项目中所有 Playwright 浏览器实例，使用单浏览器 + 多上下文模式，
确保不同模块（学生端、教师端、课程认证）可以同时运行而互不干扰。

设计原理：
- 单个浏览器实例（Browser）共享，减少资源占用
- 每个模块拥有独立的浏览器上下文（BrowserContext）
- 上下文之间完全隔离（Cookie、Session、LocalStorage）
- 支持 AsyncIO 环境（Flet GUI 兼容）
- 所有 Playwright 操作在专用工作线程中执行，避免 greenlet 线程切换问题
"""

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional, Dict, Tuple, Callable, Any
from enum import Enum
import threading
import logging
import asyncio
import queue
import concurrent.futures

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
            self._playwright = None
            self._browser: Optional[Browser] = None
            self._contexts: Dict[BrowserType, BrowserContext] = {}
            self._pages: Dict[BrowserType, Page] = {}
            self._headless = False
            self._worker_thread = None
            self._task_queue = queue.Queue()
            self._result_futures = {}
            self._task_id = 0
            self._task_id_lock = threading.Lock()
            self._thread_local = threading.local()
            self.initialized = True
            logger.info("浏览器管理器初始化完成")

    def start_browser(self, headless: bool = None) -> Browser:
        """
        启动浏览器实例（单例）

        Args:
            headless: 是否无头模式，默认从设置读取
                     如果不指定，则使用配置文件中的设置

        Returns:
            Browser: 浏览器实例
        """
        if self._browser is None:
            # 如果没有指定 headless 参数，从配置文件读取
            if headless is None:
                try:
                    from src.settings import get_settings_manager
                    settings = get_settings_manager()
                    headless = settings.get_browser_headless()
                    logger.info(f"从配置文件读取无头模式设置: headless={headless}")
                except Exception:
                    headless = False  # 默认显示浏览器
                    logger.debug("无法读取配置文件，使用默认设置（显示浏览器）")

            self._headless = headless
            self._playwright = sync_playwright().start()

            # Playwright 1.57.0+ 使用 chromium_headless_shell
            # 为了兼容打包的完整 Chromium，使用 args 参数替代 headless
            launch_args = {
                'headless': headless,
            }
            # 如果需要 headless 模式，使用 args 参数以确保使用完整 Chromium
            if headless:
                launch_args['args'] = ['--headless=new']

            self._browser = self._playwright.chromium.launch(**launch_args)

            mode_str = "无头模式（隐藏浏览器）" if headless else "有头模式（显示浏览器）"
            logger.info(f"浏览器已启动 - {mode_str}")

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
        # 先关闭页面
        if browser_type in self._pages:
            try:
                self._pages[browser_type].close()
                logger.debug(f"页面已关闭 ({browser_type.value})")
            except Exception as e:
                # 忽略 EPIPE 错误
                if "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                    logger.warning(f"关闭页面失败 ({browser_type.value}): {e}")
            finally:
                # 无论是否成功，都从字典中移除
                self._pages[browser_type] = None
                del self._pages[browser_type]

        # 再关闭上下文
        if browser_type in self._contexts:
            try:
                # 尝试先移除所有监听器
                try:
                    self._contexts[browser_type]._impl_obj._channels = []
                except Exception:
                    pass

                self._contexts[browser_type].close()
                logger.debug(f"上下文已关闭 ({browser_type.value})")
            except Exception as e:
                # 忽略 EPIPE 错误
                if "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                    logger.warning(f"关闭上下文失败 ({browser_type.value}): {e}")
            finally:
                # 无论是否成功，都从字典中移除
                self._contexts[browser_type] = None
                del self._contexts[browser_type]

        logger.info(f"已关闭 {browser_type.value} 上下文")

    def close_all_contexts(self):
        """关闭所有上下文和页面"""
        for browser_type in list(self._pages.keys()):
            self.close_context(browser_type)
        logger.info("已关闭所有上下文")

    def close_browser(self):
        """
        关闭浏览器和 Playwright 实例

        注意：此方法会尝试优雅地关闭所有资源。
        如果遇到 greenlet 线程切换错误，会强制清理引用。
        """
        # 先关闭所有上下文和页面
        self.close_all_contexts()

        # 关闭浏览器
        if self._browser:
            try:
                # 先移除所有监听器，避免关闭时触发事件
                self._browser._impl_obj._channels = []
            except Exception:
                pass

            try:
                self._browser.close()
                logger.info("浏览器已关闭")
            except Exception as e:
                # 检查是否是 greenlet 线程切换错误
                if "greenlet" in str(e) or "Cannot switch" in str(e):
                    logger.warning("检测到 greenlet 线程切换错误，强制清理浏览器引用")
                # 忽略 EPIPE 和连接错误
                elif "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                    logger.warning(f"关闭浏览器失败: {e}")
                # 对于 greenlet 错误，继续执行清理
            finally:
                # 无论是否成功，都清理引用
                self._browser = None

        # 停止 Playwright
        if self._playwright:
            try:
                self._playwright.stop()
                logger.info("Playwright 已停止")
            except Exception as e:
                # 检查是否是 greenlet 线程切换错误
                if "greenlet" in str(e) or "Cannot switch" in str(e):
                    logger.warning("检测到 greenlet 线程切换错误，强制清理 Playwright 引用")
                # 忽略 EPIPE 和连接错误
                elif "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                    logger.warning(f"停止 Playwright 失败: {e}")
            finally:
                # 无论是否成功，都清理引用
                self._playwright = None

        logger.info("浏览器资源已完全清理")

    def _ensure_worker_thread(self):
        """确保工作线程已启动"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            logger.info("启动 Playwright 工作线程")
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            logger.info("Playwright 工作线程已启动")

    def _worker_loop(self):
        """工作线程的主循环，处理任务队列"""
        worker_thread_id = threading.get_ident()
        logger.info(f"Playwright 工作线程开始运行，线程ID: {worker_thread_id}")
        # 标记这是工作线程
        self._thread_local.is_worker = True

        while True:
            try:
                # 从队列获取任务，超时1秒
                try:
                    task_id, func, args, kwargs = self._task_queue.get(timeout=1.0)
                    logger.info(f"[工作线程 {worker_thread_id}] 收到任务 {task_id}: {func.__name__}")
                except queue.Empty:
                    continue

                # 执行任务
                try:
                    logger.debug(f"[工作线程] 开始执行任务 {task_id}")
                    result = func(*args, **kwargs)
                    logger.debug(f"[工作线程] 任务 {task_id} 执行成功")
                    # 将结果保存到 Future
                    if task_id in self._result_futures:
                        future = self._result_futures[task_id]
                        if not future.done():
                            future.set_result(result)
                        del self._result_futures[task_id]
                except Exception as e:
                    logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
                    if task_id in self._result_futures:
                        future = self._result_futures[task_id]
                        if not future.done():
                            future.set_exception(e)
                        del self._result_futures[task_id]

                self._task_queue.task_done()

            except Exception as e:
                logger.error(f"工作线程主循环异常: {e}", exc_info=True)

    def submit_task(self, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务到工作线程执行

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数的返回值
        """
        self._ensure_worker_thread()

        # 检查是否已经在工作线程中
        is_worker = getattr(self._thread_local, 'is_worker', False)
        logger.debug(f"submit_task: 是否在工作线程中? {is_worker}, 当前线程ID: {threading.get_ident()}")

        if is_worker:
            # 已经在工作线程中，直接执行
            logger.debug("已在工作线程中，直接执行任务")
            return func(*args, **kwargs)

        # 生成任务ID
        with self._task_id_lock:
            task_id = self._task_id
            self._task_id += 1

        logger.debug(f"提交任务 {task_id} 到工作线程队列，函数: {func.__name__}")

        # 创建 Future 用于获取结果
        future = concurrent.futures.Future()
        self._result_futures[task_id] = future

        # 提交任务到队列
        self._task_queue.put((task_id, func, args, kwargs))

        # 等待结果
        try:
            result = future.result(timeout=300)  # 最多等待5分钟
            logger.debug(f"任务 {task_id} 完成")
            return result
        except concurrent.futures.TimeoutError:
            logger.error(f"任务 {task_id} 超时")
            raise TimeoutError(f"任务执行超时: {func.__name__}")

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
    始终在工作线程中执行函数，避免 greenlet 线程切换问题
    确保 Playwright 操作都在同一个工作线程中执行

    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数的返回值
    """
    # 强制使用 BrowserManager 的工作线程
    # 这样可以确保所有 Playwright 操作都在同一个线程中执行
    manager = get_browser_manager()
    return manager.submit_task(func, *args, **kwargs)
