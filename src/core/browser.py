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
"""

from playwright.sync_api import (
    sync_playwright,
    Browser,
    BrowserContext,
    Page,
    Error as PlaywrightError,
)
from typing import Optional, Dict, Tuple, Callable, Any
from enum import Enum
import threading
import logging
import asyncio
import queue
import concurrent.futures
import subprocess
import sys
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)
_NO_DISPATCH = object()


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
            self._worker_lock = threading.Lock()
            self._worker_ready_event = threading.Event()
            self._task_queue = queue.Queue()
            self._result_futures = {}
            self._cancelled_task_ids = set()
            self._task_id = 0
            self._task_id_lock = threading.Lock()
            self._result_futures_lock = threading.Lock()
            self._thread_local = threading.local()
            self._worker_generation = 0  # worker 代际，reset 时升，旧 worker 自知退出
            self._state_lock = threading.RLock()  # 保护 _browser/_playwright/_contexts/_pages（reset 跨线程清理）
            self.initialized = True
            self._browser_checked = False  # 标记是否已检查过浏览器
            logger.info("浏览器管理器初始化完成")

    def is_worker_thread(self) -> bool:
        """判断当前代码是否运行在 Playwright 专用工作线程。"""
        return getattr(self._thread_local, 'is_worker', False)

    def _dispatch_to_worker_if_needed(self, func: Callable, *args, **kwargs):
        """将 Playwright 操作统一调度到专用工作线程，避免跨线程冲突。"""
        if self.is_worker_thread():
            return _NO_DISPATCH
        return self.submit_task(func, *args, **kwargs)

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

    def _is_page_usable(self, page: Optional[Page]) -> bool:
        """检查页面对象是否仍可用。"""
        if page is None:
            return False
        try:
            return not page.is_closed()
        except (PlaywrightError, RuntimeError):
            return False

    def _is_context_usable(self, context: Optional[BrowserContext]) -> bool:
        """检查上下文对象是否仍可用。"""
        if context is None:
            return False
        try:
            _ = context.pages
            return True
        except (PlaywrightError, RuntimeError):
            return False

    def _check_playwright_browser(self) -> Tuple[bool, str]:
        """
        检查 Playwright 浏览器是否已安装

        Returns:
            Tuple[bool, str]: (是否已安装, 错误信息)
        """
        try:
            # 尝试启动 Playwright 来检测浏览器
            with sync_playwright() as p:
                # 尝试获取已安装的浏览器路径
                try:
                    executable_path = p.chromium.executable_path
                    if Path(executable_path).exists():
                        logger.info(f"Chromium 浏览器已安装: {executable_path}")
                        return True, ""
                    else:
                        return False, f"浏览器可执行文件不存在: {executable_path}"
                except (PlaywrightError, RuntimeError, OSError) as e:
                    return False, f"无法获取浏览器路径: {str(e)}"
        except (PlaywrightError, RuntimeError, OSError) as e:
            return False, f"Playwright 浏览器检查失败: {str(e)}"

    def _install_playwright_browser(self, show_progress: bool = True) -> Tuple[bool, str]:
        """
        安装 Playwright 浏览器

        Args:
            show_progress: 是否显示安装进度

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        if show_progress:
            logger.info("开始安装 Playwright Chromium 浏览器...")

        try:
            # 使用 subprocess 调用 playwright install
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                if show_progress:
                    logger.info("[OK] Playwright 浏览器安装成功！")
                return True, ""
            else:
                error_msg = result.stderr or result.stdout or "未知错误"
                if show_progress:
                    logger.error(f"✗ 浏览器安装失败: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = "浏览器安装超时（10分钟）"
            if show_progress:
                logger.error(f"✗ {error_msg}")
            return False, error_msg
        except OSError as e:
            error_msg = f"安装过程出错: {str(e)}"
            if show_progress:
                logger.error(f"✗ {error_msg}")
            return False, error_msg

    def _install_from_local_directory(self, local_path: str) -> Tuple[bool, str]:
        """
        从本地目录安装 Playwright 浏览器

        Args:
            local_path: 本地浏览器路径或包含浏览器的目录

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        logger.info(f"尝试从本地路径安装浏览器: {local_path}")

        try:
            local_path_obj = Path(local_path)

            # 检查路径是否存在
            if not local_path_obj.exists():
                return False, f"指定的路径不存在: {local_path}"

            # 如果是目录，尝试找到 chromium 可执行文件
            if local_path_obj.is_dir():
                # 常见的 Chromium 可执行文件位置
                possible_executables = [
                    local_path_obj / "chrome.exe" if os.name == 'nt' else local_path_obj / "chrome",
                    local_path_obj / "chromium.exe" if os.name == 'nt' else local_path_obj / "chromium",
                    local_path_obj / "chrome" / "chrome.exe" if os.name == 'nt' else local_path_obj / "chrome" / "chrome",
                ]

                executable_path = None
                for possible_path in possible_executables:
                    if possible_path.exists():
                        executable_path = possible_path
                        break

                if executable_path:
                    logger.info(f"找到本地浏览器: {executable_path}")
                    # 设置环境变量指向本地浏览器
                    os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = str(executable_path)
                    return True, ""
                else:
                    return False, f"在目录中未找到浏览器可执行文件: {local_path}"

            # 如果是文件，检查是否为可执行文件
            elif local_path_obj.is_file():
                logger.info(f"使用指定的浏览器文件: {local_path_obj}")
                os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = str(local_path_obj)
                return True, ""

            return False, f"无效的路径类型: {local_path}"

        except (OSError, TypeError) as e:
            return False, f"从本地目录安装失败: {str(e)}"

    @staticmethod
    def detect_system_browsers() -> Dict[str, str]:
        """
        检测系统中已安装的浏览器

        Returns:
            Dict[str, str]: 可用浏览器及其路径，格式 {"chrome": "路径", "msedge": "路径"}
        """
        browsers = {}

        try:
            # Windows 系统常见浏览器路径
            if sys.platform == 'win32':
                # Google Chrome
                chrome_paths = [
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                    Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                    Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                ]

                # Microsoft Edge
                edge_paths = [
                    Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
                    Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
                ]

            # Linux 系统常见浏览器路径
            elif sys.platform == 'linux':
                chrome_paths = [
                    Path('/usr/bin/google-chrome'),
                    Path('/usr/bin/google-chrome-stable'),
                    Path('/opt/google/chrome/chrome'),
                ]
                edge_paths = [
                    Path('/usr/bin/microsoft-edge'),
                    Path('/opt/microsoft-edge/msedge'),
                ]

            # macOS 系统常见浏览器路径
            elif sys.platform == 'darwin':
                chrome_paths = [
                    Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
                ]
                edge_paths = [
                    Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'),
                ]
            else:
                return browsers

            # 检测 Google Chrome
            for path in chrome_paths:
                if path.exists():
                    browsers['chrome'] = str(path)
                    logger.info(f"[OK] 检测到 Google Chrome: {path}")
                    break

            # 检测 Microsoft Edge
            for path in edge_paths:
                if path.exists():
                    browsers['msedge'] = str(path)
                    logger.info(f"[OK] 检测到 Microsoft Edge: {path}")
                    break

            if not browsers:
                logger.warning("未检测到系统浏览器（Chrome 或 Edge）")

        except (OSError, TypeError) as e:
            logger.error(f"检测系统浏览器时出错: {e}")

        return browsers

    def get_available_browser_channel(self) -> Tuple[str, str]:
        """
        获取可用的浏览器通道

        Returns:
            Tuple[str, str]: (浏览器通道, 显示信息)

        优先级：
        1. 配置文件中指定的浏览器通道
        2. 自动检测系统浏览器
        3. 使用 Playwright 内置浏览器
        """
        try:
            from src.core.config import get_settings_manager
            settings = get_settings_manager()
            config_channel = settings.get_browser_channel()

            # 如果配置了通道且不是空字符串，直接使用
            if config_channel and config_channel != BrowserChannel.BUNDLED.value:
                # 验证该浏览器是否可用
                if config_channel in ['chrome', 'msedge']:
                    system_browsers = self.detect_system_browsers()
                    if config_channel in system_browsers:
                        logger.info(f"[OK] 使用配置的浏览器通道: {config_channel}")
                        return config_channel, f"使用系统浏览器: {BrowserChannel.from_string(config_channel).get_display_name()}"
                    else:
                        logger.warning(f"⚠️ 配置的浏览器通道 '{config_channel}' 不可用，将尝试其他选项")

                # 对于 chromium 或检测失败的通道，继续尝试其他选项

            # 尝试自动检测系统浏览器（优先级：Chrome > Edge）
            system_browsers = self.detect_system_browsers()
            if system_browsers:
                # 优先使用 Chrome
                if 'chrome' in system_browsers:
                    logger.info("[OK] 自动选择系统 Google Chrome")
                    return 'chrome', "自动选择系统浏览器: Google Chrome"
                elif 'msedge' in system_browsers:
                    logger.info("[OK] 自动选择系统 Microsoft Edge")
                    return 'msedge', "自动选择系统浏览器: Microsoft Edge"

            # 使用 Playwright 内置浏览器
            logger.info("[OK] 使用 Playwright 内置浏览器")
            return '', "使用 Playwright 内置浏览器"

        except (ImportError, AttributeError, KeyError, TypeError, ValueError, OSError) as e:
            logger.warning(f"获取浏览器通道配置时出错: {e}，使用默认配置")
            return '', "使用 Playwright 内置浏览器（配置读取失败）"

    def ensure_browser_installed(self, local_browser_path: str = None) -> Tuple[bool, str]:
        """
        确保浏览器已安装，提供多种备选方案

        Args:
            local_browser_path: 本地浏览器路径（可选）

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        # 如果已经检查过，直接返回
        if self._browser_checked:
            return True, ""

        logger.info("检查 Playwright 浏览器安装状态...")

        # 方案1: 检查浏览器是否已安装
        is_installed, error_msg = self._check_playwright_browser()
        if is_installed:
            self._browser_checked = True
            return True, ""

        logger.warning(f"浏览器未安装: {error_msg}")

        # 方案2: 使用指定的本地浏览器
        if local_browser_path:
            logger.info(f"尝试使用本地浏览器: {local_browser_path}")
            success, error = self._install_from_local_directory(local_browser_path)
            if success:
                self._browser_checked = True
                return True, ""
            else:
                logger.warning(f"本地浏览器设置失败: {error}")

        # 方案3: 自动安装浏览器
        logger.info("尝试自动安装浏览器...")
        success, error = self._install_playwright_browser(show_progress=True)
        if success:
            self._browser_checked = True
            return True, ""

        # 所有方案都失败
        error_msg = f"""
        ================================================
        浏览器安装失败！
        ================================================

        自动安装失败原因: {error}

        请尝试以下备选方案:

        方案1: 手动安装浏览器
        ------------------------
        打开命令行，执行以下命令:
            python -m playwright install chromium

        方案2: 使用本地浏览器
        ------------------------
        如果您已经有 Chromium 浏览器，可以指定路径:
        1. 在应用设置中配置，或编辑用户配置目录中的 cli_config.json
        2. 添加: "local_browser_path": "浏览器路径"
        3. Windows 示例: "C:\\Program Files\\Chromium\\chrome.exe"
        4. Linux/Mac 示例: "/usr/bin/chromium"

        方案3: 下载 Playwright 浏览器到本地
        ------------------------
        1. 访问: https://playwright.dev/python/docs/cli
        2. 下载对应平台的 Chromium 浏览器
        3. 解压到指定目录
        4. 使用方案2指定路径

        详细文档: {Path(__file__).parent.parent.parent / "docs" / "BROWSER_SETUP.md"}
        ================================================
        """
        return False, error_msg.strip()

    def start_browser(self, headless: bool = None, local_browser_path: str = None, auto_install: bool = True) -> Browser:
        """
        启动浏览器实例（单例）

        Args:
            headless: 是否无头模式，默认从设置读取
                     如果不指定，则使用配置文件中的设置
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
                # 如果没有提供本地浏览器路径，从配置文件读取
                if local_browser_path is None:
                    try:
                        from src.core.config import get_settings_manager
                        settings = get_settings_manager()
                        local_browser_path = settings.get_local_browser_path()
                        if local_browser_path:
                            logger.info(f"从配置文件读取本地浏览器路径: {local_browser_path}")
                    except (ImportError, AttributeError, KeyError, TypeError, ValueError, OSError) as e:
                        logger.debug(f"读取本地浏览器路径配置失败: {e}")

                # 确保浏览器已安装
                if auto_install:
                    success, error_msg = self.ensure_browser_installed(local_browser_path)
                    if not success:
                        raise RuntimeError(error_msg)
                elif local_browser_path:
                    # 即使不自动安装，也要设置本地浏览器路径
                    self._install_from_local_directory(local_browser_path)

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

            # Playwright 1.57.0+ 使用 chromium_headless_shell
            # 为了兼容打包的完整 Chromium，使用 args 参数替代 headless
            launch_args = {
                'headless': headless,
            }

            # 如果使用系统浏览器通道，添加 channel 参数
            if browser_channel:
                launch_args['channel'] = browser_channel
                logger.info(f"[OK] 设置浏览器通道: {browser_channel}")
            else:
                # 使用 Playwright 内置浏览器
                # 如果需要 headless 模式，使用 args 参数以确保使用完整 Chromium
                if headless:
                    launch_args['args'] = ['--headless=new']

            # 检查是否有自定义浏览器路径（优先级高于 channel）
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'):
                launch_args['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']
                logger.info(f"使用自定义浏览器路径: {os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH']}")

            self._browser = self._playwright.chromium.launch(**launch_args)

            mode_str = "无头模式（隐藏浏览器）" if headless else "有头模式（显示浏览器）"
            browser_info = f"浏览器通道: {browser_channel if browser_channel else 'Playwright 内置'}, {mode_str}"
            logger.info(f"✅ 浏览器已启动 - {browser_info}")

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
            browser_type: 浏览器类型（STUDENT/TEACHER/COURSE_CERTIFICATION/CLOUD_EXAM）
            **kwargs: 传递给 new_context() 的额外参数

        Returns:
            BrowserContext: 浏览器上下文实例
        """
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
            browser_type: 浏览器类型（STUDENT, TEACHER, COURSE_CERTIFICATION）
        """
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
                # context.close() 会自动关闭其下所有页面
                context.close()
                logger.debug(f"上下文已关闭 ({browser_type.value})")
        except (PlaywrightError, RuntimeError, OSError) as e:
            # 忽略 EPIPE 和连接错误
            if "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                logger.warning(f"关闭上下文失败 ({browser_type.value}): {e}")
        finally:
            # 无论是否成功，都从字典中移除
            if browser_type in self._pages:
                self._pages[browser_type] = None
                del self._pages[browser_type]
            self._contexts[browser_type] = None
            del self._contexts[browser_type]

        logger.info(f"已关闭 {browser_type.value} 上下文")

    def close_all_contexts(self):
        """关闭所有上下文和页面"""
        dispatched = self._dispatch_to_worker_if_needed(self.close_all_contexts)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        for browser_type in list(set(self._contexts.keys()) | set(self._pages.keys())):
            self.close_context(browser_type)
        logger.info("已关闭所有上下文")

    def close_browser(self):
        """
        关闭浏览器和 Playwright 实例

        注意：此方法会尝试优雅地关闭所有资源。
        如果遇到 greenlet 线程切换错误，会强制清理引用。
        """
        dispatched = self._dispatch_to_worker_if_needed(self.close_browser)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        logger.info("开始关闭浏览器和 Playwright 实例...")

        # 先关闭所有上下文和页面
        self.close_all_contexts()

        # 关闭浏览器
        if self._browser:
            try:
                # 关闭浏览器
                try:
                    if self._browser.is_connected():
                        self._browser.close()
                        logger.info("浏览器已关闭")
                    else:
                        logger.info("浏览器已断开连接，跳过关闭操作")
                except (PlaywrightError, RuntimeError, OSError) as e:
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
                logger.debug("浏览器引用已清理")

        # 停止 Playwright
        if self._playwright:
            try:
                self._playwright.stop()
                logger.info("Playwright 已停止")
            except (PlaywrightError, RuntimeError, OSError) as e:
                # 检查是否是 greenlet 线程切换错误
                if "greenlet" in str(e) or "Cannot switch" in str(e):
                    logger.warning("检测到 greenlet 线程切换错误，强制清理 Playwright 引用")
                # 忽略 EPIPE 和连接错误
                elif "EPIPE" not in str(e) and "broken pipe" not in str(e).lower():
                    logger.warning(f"停止 Playwright 失败: {e}")
            finally:
                # 无论是否成功，都清理引用
                self._playwright = None
                logger.debug("Playwright 引用已清理")

        logger.info("浏览器资源已完全清理")

    def force_kill_process_tree(self, timeout: float = 2.0) -> None:
        """
        强制终止当前 Python 进程派生的所有子进程（递归整棵树）。

        Playwright 的 Node driver 是当前进程的子进程，而浏览器（Chrome/Edge）由 Node driver
        派生，属于孙进程——只杀 node.exe 会让浏览器成为孤儿继续驻留。这里用 psutil 递归杀掉
        全部后代，作为退出流程的兜底，确保不残留孤儿浏览器进程。

        Args:
            timeout: terminate 后等待进程退出的超时时间，超时则升级为 kill。
        """
        try:
            import psutil
        except ImportError:
            logger.debug("psutil 未安装，跳过子进程树强制终止")
            return

        try:
            parent = psutil.Process(os.getpid())
            children = parent.children(recursive=True)
            if not children:
                return

            logger.info(f"强制终止 {len(children)} 个子进程（Playwright/浏览器进程树）")
            for proc in children:
                try:
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            gone, alive = psutil.wait_procs(children, timeout=timeout)
            for proc in alive:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"获取子进程列表失败: {e}")
        except Exception as e:
            logger.debug(f"强制终止子进程树失败: {e}")

    def _drain_pending_tasks(self):
        """排空待处理任务队列（reset_worker 时调用，全部标记失败）。"""
        with self._result_futures_lock:
            while not self._task_queue.empty():
                try:
                    task_id, func, args, kwargs = self._task_queue.get_nowait()
                    future = self._result_futures.pop(task_id, None)
                    if future is not None and not future.done():
                        future.set_exception(RuntimeError("worker 已重置，任务被丢弃"))
                except queue.Empty:
                    break
            self._cancelled_task_ids.clear()

    def reset_worker(self, reason: str = "manual"):
        """重置 worker 线程：强杀浏览器进程逼卡死的 func 抛异常退出，清理状态。

        用于 worker 卡死（page.goto 永久阻塞）时的运行时自愈。
        下次 submit_task → _ensure_worker_thread 会自动起新 generation 的 worker。
        """
        with self._worker_lock:
            logger.warning(f"🔄 重置 worker 线程: {reason}")
            old_thread = self._worker_thread
            # 1. 升代际 → 旧 worker 从 func 异常恢复后读到不匹配会退出
            self._worker_generation += 1
            # 2. 强杀浏览器进程树，逼旧 worker 的 Playwright 调用抛 TargetClosedError
            try:
                self.force_kill_process_tree(timeout=2.0)
            except Exception as e:
                logger.error(f"reset force_kill 失败: {e}")
            # 3. 等旧 worker 退出（卡死则超时；旧线程作为 daemon 泄漏，进程退出时回收）
            if old_thread is not None and old_thread.is_alive():
                old_thread.join(timeout=5)
            # 4. 清理 Playwright 状态（加锁）
            with self._state_lock:
                self._browser = None
                self._playwright = None
                self._contexts.clear()
                self._pages.clear()
            # 5. 排空待处理任务队列（全部失败）
            self._drain_pending_tasks()
            # 6. worker_thread 置 None，下次 _ensure_worker_thread 起新 generation 的 worker
            self._worker_thread = None
            logger.info("✅ worker 线程已重置，下次操作将自动重建")

    def _ensure_worker_thread(self):
        """确保工作线程已启动"""
        with self._worker_lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                logger.info("启动 Playwright 工作线程")
                self._worker_ready_event.clear()
                self._worker_thread = threading.Thread(target=self._worker_loop, args=(self._worker_generation,), daemon=True)
                self._worker_thread.start()
                logger.info("Playwright 工作线程已创建，等待就绪信号")

        if not self._worker_ready_event.wait(timeout=5):
            raise RuntimeError("Playwright 工作线程启动超时")

    def _worker_loop(self, my_generation: int):
        """工作线程的主循环，处理任务队列。

        my_generation: 该 worker 的代际编号；reset_worker 会升代际，
        旧 worker 从 func 异常恢复后读到不匹配则退出（while 条件）。
        """
        worker_thread_id = threading.get_ident()
        logger.info(f"Playwright 工作线程开始运行，线程ID: {worker_thread_id}, 代际: {my_generation}")
        # 标记这是工作线程
        self._thread_local.is_worker = True
        self._worker_ready_event.set()

        while self._worker_generation == my_generation:
            try:
                # 从队列获取任务，超时1秒
                try:
                    task_id, func, args, kwargs = self._task_queue.get(timeout=1.0)
                    logger.info(f"[工作线程 {worker_thread_id}] 收到任务 {task_id}: {func.__name__}")
                except queue.Empty:
                    continue

                with self._result_futures_lock:
                    is_cancelled = task_id in self._cancelled_task_ids
                    if is_cancelled:
                        self._cancelled_task_ids.discard(task_id)
                        self._result_futures.pop(task_id, None)

                if is_cancelled:
                    logger.warning(f"[工作线程] 跳过已超时取消的任务 {task_id}: {func.__name__}")
                    self._task_queue.task_done()
                    continue

                # 执行任务
                try:
                    logger.debug(f"[工作线程] 开始执行任务 {task_id}")
                    # **关键保护**：确保在工作线程的 greenlet 中执行
                    # 使用 try-finally 确保 greenlet 状态正确
                    result = func(*args, **kwargs)
                    logger.debug(f"[工作线程] 任务 {task_id} 执行成功")
                    # 将结果保存到 Future
                    with self._result_futures_lock:
                        self._cancelled_task_ids.discard(task_id)
                        future = self._result_futures.pop(task_id, None)
                    if future and not future.done():
                        future.set_result(result)
                except Exception as e:
                    # 任务函数来自各业务模块，必须兜底捕获并回传给调用方，避免工作线程退出。
                    logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
                    with self._result_futures_lock:
                        self._cancelled_task_ids.discard(task_id)
                        future = self._result_futures.pop(task_id, None)
                    if future and not future.done():
                        future.set_exception(e)

                self._task_queue.task_done()

            except Exception as e:
                # 工作线程是 Playwright 的唯一执行通道，主循环必须自恢复。
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
        with self._result_futures_lock:
            self._result_futures[task_id] = future

        # 提交任务到队列
        self._task_queue.put((task_id, func, args, kwargs))

        # 等待结果
        try:
            result = future.result(timeout=300)  # 最多等待5分钟
            logger.debug(f"任务 {task_id} 完成")
            return result
        except concurrent.futures.TimeoutError:
            logger.error(f"任务 {task_id} 超时，触发 worker 重置以自愈")
            with self._result_futures_lock:
                timed_out_future = self._result_futures.pop(task_id, None)
                self._cancelled_task_ids.add(task_id)
            if timed_out_future and not timed_out_future.done():
                timed_out_future.cancel()
            # 300s 超时几乎必然是 worker 卡死，触发 reset 重建 worker + 浏览器
            self.reset_worker(reason="任务超时（300s）")
            raise TimeoutError(f"任务执行超时: {func.__name__}")

    def is_browser_alive(self) -> bool:
        """
        检查浏览器是否存活（增强版）

        Returns:
            bool: 浏览器是否连接正常
        """
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
        """
        检查指定上下文是否存活（增强版）

        Args:
            browser_type: 浏览器类型

        Returns:
            bool: 上下文是否存活
        """
        dispatched = self._dispatch_to_worker_if_needed(self.is_context_alive, browser_type)
        if dispatched is not _NO_DISPATCH:
            return dispatched

        # 先检查浏览器是否存活
        if not self.is_browser_alive():
            logger.debug(f"浏览器未存活，跳过上下文检查 ({browser_type.value})")
            return False

        # 检查上下文是否存在
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
