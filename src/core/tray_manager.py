"""
系统托盘管理器模块

提供系统托盘图标功能，允许应用程序最小化到系统托盘并在后台运行。
"""

import threading
import queue
from typing import Optional, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# 可选依赖：pystray
# 如果未安装，托盘功能将被禁用
try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray 未安装，系统托盘功能将被禁用。请运行: pip install pystray Pillow")


class TrayManager:
    """系统托盘管理器"""

    def __init__(self):
        self._icon: Optional['pystray.Icon'] = None
        self._thread: Optional[threading.Thread] = None
        self._enabled = False
        self._running = False

        # 回调函数
        self._on_show: Optional[Callable] = None
        self._on_hide: Optional[Callable] = None
        self._on_quit: Optional[Callable] = None

        # 线程安全的任务队列
        self._task_queue = queue.Queue()

    def is_available(self) -> bool:
        """检查托盘功能是否可用"""
        return PYSTRAY_AVAILABLE

    def set_callbacks(self, on_show: Callable = None, on_hide: Callable = None, on_quit: Callable = None):
        """
        设置托盘图标的回调函数

        Args:
            on_show: 显示窗口的回调
            on_hide: 隐藏窗口的回调
            on_quit: 退出应用的回调
        """
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_quit = on_quit

    def _create_icon_image(self) -> 'Image.Image':
        """创建托盘图标图片"""
        # 尝试使用项目图标文件
        try:
            from pathlib import Path
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            icon_path = project_root / "build" / "flutter" / "windows" / "runner" / "resources" / "app_icon.ico"

            if icon_path.exists():
                # 使用现有图标文件
                return Image.open(icon_path)
            else:
                # 如果图标文件不存在，创建一个简单的图标
                return self._create_default_icon()
        except Exception as e:
            logger.debug(f"加载图标文件失败: {e}，使用默认图标")
            return self._create_default_icon()

    def _create_default_icon(self) -> 'Image.Image':
        """创建默认的托盘图标"""
        # 创建一个简单的图标
        width = 64
        height = 64

        # 创建蓝色背景
        image = Image.new('RGB', (width, height), color='#1E88E5')
        draw = ImageDraw.Draw(image)

        # 绘制"ZX"文字
        draw.text((10, 15), "ZX", fill='white')

        return image

    def _on_double_click(self, icon, item):
        """双击托盘图标时的处理"""
        if self._on_show:
            self._task_queue.put(('show', None))

    def _on_show_window(self, icon, item):
        """显示窗口菜单项"""
        if self._on_show:
            self._task_queue.put(('show', None))

    def _on_hide_window(self, icon, item):
        """隐藏窗口菜单项"""
        if self._on_hide:
            self._task_queue.put(('hide', None))

    def _on_quit_app(self, icon, item):
        """退出应用菜单项"""
        if self._on_quit:
            self._task_queue.put(('quit', None))

    def _run_icon(self):
        """在单独线程中运行托盘图标"""
        if not self._icon:
            return

        self._running = True
        logger.info("系统托盘图标已启动")

        try:
            self._icon.run()
        except Exception as e:
            logger.error(f"托盘图标运行错误: {e}")
        finally:
            self._running = False
            logger.info("系统托盘图标已停止")

    def start(self, title: str = "ZX答题助手"):
        """
        启动系统托盘图标

        Args:
            title: 托盘图标的提示文本
        """
        if not PYSTRAY_AVAILABLE:
            logger.warning("无法启动系统托盘：pystray 未安装")
            return False

        if self._icon is not None:
            logger.warning("系统托盘已在运行")
            return True

        try:
            # 创建图标
            icon_image = self._create_icon_image()

            # 创建菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self._on_show_window),
                pystray.MenuItem("隐藏窗口", self._on_hide_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._on_quit_app)
            )

            # 创建图标对象
            self._icon = pystray.Icon(
                "zx_answering_assistant",
                icon_image,
                title,
                menu
            )

            # 设置双击事件
            self._icon.on_double_click = self._on_double_click

            # 在单独线程中运行托盘图标
            self._thread = threading.Thread(target=self._run_icon, daemon=True)
            self._thread.start()

            self._enabled = True
            logger.info(f"系统托盘图标已创建: {title}")
            return True

        except Exception as e:
            logger.error(f"创建系统托盘图标失败: {e}")
            self._icon = None
            return False

    def stop(self):
        """停止系统托盘图标"""
        if not self._icon:
            return

        logger.info("正在停止系统托盘图标...")
        self._enabled = False

        try:
            self._icon.stop()
            logger.info("系统托盘图标已停止")
        except Exception as e:
            logger.error(f"停止托盘图标时出错: {e}")
        finally:
            self._icon = None
            self._thread = None

    def is_running(self) -> bool:
        """检查托盘图标是否正在运行"""
        return self._icon is not None and self._running

    def is_enabled(self) -> bool:
        """检查托盘功能是否已启用"""
        return self._enabled

    def process_pending_actions(self):
        """
        处理托盘图标的待办操作

        此方法应该在主线程中定期调用，以处理来自托盘图标的操作
        """
        try:
            while not self._task_queue.empty():
                action, data = self._task_queue.get_nowait()

                if action == 'show' and self._on_show:
                    self._on_show()
                elif action == 'hide' and self._on_hide:
                    self._on_hide()
                elif action == 'quit' and self._on_quit:
                    self._on_quit()

        except queue.Empty:
            pass


# 全局托盘管理器实例
_tray_manager: Optional[TrayManager] = None


def get_tray_manager() -> TrayManager:
    """
    获取全局托盘管理器实例（单例模式）

    Returns:
        TrayManager: 托盘管理器实例
    """
    global _tray_manager
    if _tray_manager is None:
        _tray_manager = TrayManager()
    return _tray_manager