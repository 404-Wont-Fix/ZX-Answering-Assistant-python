"""
系统托盘管理器。

pystray 的菜单回调在托盘线程中执行。本模块只负责发出用户动作，
窗口更新由 MainApp 调度回 Flet 事件循环执行。
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw

    PYSTRAY_AVAILABLE = True
except Exception as exc:
    pystray = None
    Image = None
    ImageDraw = None
    PYSTRAY_AVAILABLE = False
    logger.debug("系统托盘依赖或运行后端不可用: %s", exc)


class TrayManager:
    """管理应用的单个系统托盘图标。"""

    def __init__(self):
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._ready: Optional[threading.Event] = None
        self._startup_failed: Optional[threading.Event] = None
        self._on_show: Optional[Callable[[], None]] = None
        self._on_hide: Optional[Callable[[], None]] = None
        self._on_quit: Optional[Callable[[], None]] = None

    def is_available(self) -> bool:
        """返回当前环境是否具备托盘依赖。"""
        return PYSTRAY_AVAILABLE

    def set_callbacks(
        self,
        on_show: Optional[Callable[[], None]] = None,
        on_hide: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_show = on_show
        self._on_hide = on_hide
        self._on_quit = on_quit

    def _invoke(self, callback: Optional[Callable[[], None]]) -> None:
        if callback is None:
            return
        try:
            callback()
        except Exception:
            logger.exception("处理系统托盘动作失败")

    def _show(self, icon, item) -> None:
        self._invoke(self._on_show)

    def _hide(self, icon, item) -> None:
        self._invoke(self._on_hide)

    def _quit(self, icon, item) -> None:
        self._invoke(self._on_quit)

    def _create_image(self):
        project_root = Path(__file__).resolve().parents[2]
        for icon_path in (
            project_root / "assets" / "icon.ico",
            project_root / "build" / "flutter" / "windows" / "runner" / "resources" / "app_icon.ico",
        ):
            if icon_path.exists():
                try:
                    with Image.open(icon_path) as source:
                        return source.copy()
                except Exception:
                    logger.debug("无法读取托盘图标 %s", icon_path, exc_info=True)

        image = Image.new("RGBA", (64, 64), "#1976D2")
        draw = ImageDraw.Draw(image)
        draw.rectangle((7, 7, 57, 57), outline="white", width=3)
        draw.text((17, 24), "ZX", fill="white")
        return image

    def _run(
        self,
        icon,
        ready: threading.Event,
        startup_failed: threading.Event,
    ) -> None:
        def setup(active_icon) -> None:
            try:
                active_icon.visible = True
            except Exception:
                startup_failed.set()
                logger.exception("显示系统托盘图标失败")
            finally:
                ready.set()

        try:
            icon.run(setup=setup)
        except Exception:
            startup_failed.set()
            ready.set()
            logger.exception("系统托盘图标运行失败")
        finally:
            with self._lock:
                if self._icon is icon:
                    self._icon = None
                    self._thread = None
                    self._ready = None
                    self._startup_failed = None

    def start(self, title: str = "ZX 答题助手") -> bool:
        """启动图标；已启动时保持幂等。"""
        if not self.is_available():
            logger.warning("系统托盘不可用：请安装 pystray 和 Pillow")
            return False

        with self._lock:
            if self._icon is not None:
                ready = self._ready
                startup_failed = self._startup_failed
            else:
                try:
                    menu = pystray.Menu(
                        pystray.MenuItem("显示窗口", self._show, default=True),
                        pystray.MenuItem("隐藏窗口", self._hide),
                        pystray.Menu.SEPARATOR,
                        pystray.MenuItem("退出", self._quit),
                    )
                    icon = pystray.Icon(
                        "zx_answering_assistant",
                        self._create_image(),
                        title,
                        menu,
                    )
                    ready = threading.Event()
                    startup_failed = threading.Event()
                    thread = threading.Thread(
                        target=self._run,
                        args=(icon, ready, startup_failed),
                        name="zx-system-tray",
                        daemon=True,
                    )
                    self._icon = icon
                    self._thread = thread
                    self._ready = ready
                    self._startup_failed = startup_failed
                    thread.start()
                except Exception:
                    self._icon = None
                    self._thread = None
                    self._ready = None
                    self._startup_failed = None
                    logger.exception("创建系统托盘图标失败")
                    return False

        if ready is None or startup_failed is None:
            return False
        if not ready.wait(timeout=2) or startup_failed.is_set():
            logger.error("系统托盘未能及时启动，取消隐藏窗口操作")
            self.stop()
            return False
        return self.is_running()

    def stop(self) -> None:
        """停止并移除托盘图标。"""
        with self._lock:
            icon = self._icon
            thread = self._thread
            self._icon = None
            self._thread = None
            self._ready = None
            self._startup_failed = None

        if icon is None:
            return

        try:
            icon.stop()
        except Exception:
            logger.exception("移除系统托盘图标失败")

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)

    def is_running(self) -> bool:
        with self._lock:
            return self._icon is not None


_tray_manager: Optional[TrayManager] = None
_manager_lock = threading.Lock()


def get_tray_manager() -> TrayManager:
    """获取进程内唯一的托盘管理器。"""
    global _tray_manager
    if _tray_manager is None:
        with _manager_lock:
            if _tray_manager is None:
                _tray_manager = TrayManager()
    return _tray_manager
