"""
ZX Answering Assistant - GUI Main Module

This module is responsible for the underlying structure setup of the UI using Flet framework.
It provides the foundation for building the graphical user interface with a collapsible navigation bar.
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径（支持开发和打包环境）
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 在导入 flet 之前设置环境变量
# 让 Flet 使用 pip 而不是 uv
os.environ["UV_SYSTEM_PYTHON"] = "1"

import flet as ft
import webbrowser

# 动态导入 version 模块（支持打包环境）
try:
    import version
except ImportError:
    # 如果导入失败，使用默认版本
    class DefaultVersion:
        VERSION = "Unknown"
        VERSION_NAME = "ZX Answering Assistant"
    version = DefaultVersion()

from src.ui.views.answering_view import AnsweringView
from src.ui.views.extraction_view import ExtractionView
from src.ui.views.settings_view import SettingsView
from src.ui.views.plugin_center_view import PluginCenterView
from src.ui.views.about_view import AboutView
from src.ui.components import status_chip
from src.ui.theme import Fonts, Palette, Radius, configure_page

from src.core.browser import get_browser_manager
from src.core.plugin_manager import get_plugin_manager
from src.core.api_client import get_api_client
from src.core.config import get_settings_manager
from src.core.tray_manager import get_tray_manager


class MainApp:
    """主应用程序类"""

    def __init__(self, page: ft.Page):
        """
        初始化应用程序

        Args:
            page (ft.Page): Flet页面对象
        """
        self.page = page
        self.navigation_rail = None
        self.content_area = None
        self.current_destination = None
        self.sidebar = None
        self.sidebar_header = None
        self.brand_logo = None
        self.brand_text = None
        self.sidebar_footer = None
        self.collapse_button = None
        self.header_title = None
        self.header_subtitle = None
        self.settings_manager = get_settings_manager()
        self.tray_manager = get_tray_manager()
        self._window_hidden_to_tray = False
        self._manual_tray_session = False
        self._quitting = False

        # 导航栏展开状态
        self.rail_expanded = True
        self.rail_width = 252
        self.destination_details = [
            ("评估答题", "选择课程并执行智能答题任务"),
            ("答案提取", "从教师端课程生成可复用题库"),
            ("插件中心", "管理扩展能力与插件入口"),
            ("系统设置", "账号、浏览器和后台行为配置"),
            ("关于", "应用版本与项目说明"),
        ]

        # 初始化插件管理器（在创建视图之前）
        self.plugin_manager = get_plugin_manager()
        self._initialize_plugins()

        # 初始化视图模块（传递MainApp引用以便视图可以切换导航）
        self.answering_view = AnsweringView(page, main_app=self)
        self.extraction_view = ExtractionView(page, main_app=self)
        self.plugin_center_view = PluginCenterView(page, main_app=self)
        self.settings_view = SettingsView(page, main_app=self)
        self.about_view = AboutView(page)

        # 缓存每个视图的内容（保持状态）
        self.cached_contents = {
            0: None,  # 评估答题
            1: None,  # 答案提取
            2: None,  # 插件中心
            3: None,  # 系统设置
            4: None,  # 关于
        }

        # 初始化UI
        self._setup_page()
        self._build_ui()

        # 根据设置启动系统托盘；设置稍后修改时也可即时重配
        self._initialize_tray()

        # 在页面加载完成后居中窗口
        self._center_window_async()

        # 注册窗口关闭看门狗（退出兜底，不依赖 Flet 事件循环）
        self._setup_window_close_watchdog()

    def _setup_page(self):
        """配置页面属性"""
        self.page.title = "ZX Answering Assistant"
        configure_page(self.page)
        self.page.window.width = 1180
        self.page.window.height = 780
        self.page.window.min_width = 940
        self.page.window.min_height = 620
        # 不使用异步center()方法，而是在页面加载后手动居中
        self.page.padding = 0

        # prevent_close 仅在托盘图标可用且关闭到托盘启用时开启。
        self.page.window.prevent_close = False
        self.page.window.on_event = self._on_window_event

    def _center_window_async(self):
        """在页面加载完成后异步居中窗口"""
        import threading
        import time

        def center_after_delay():
            time.sleep(0.1)  # 等待页面完全加载
            try:
                # 使用线程安全的方式更新UI状态
                if hasattr(self.page, 'window') and hasattr(self.page.window, 'center'):
                    # 调用异步center方法
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        # 如果已有事件循环，在线程中创建新循环
                        def run_center():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            new_loop.run_until_complete(self.page.window.center())
                            new_loop.close()

                        thread = threading.Thread(target=run_center)
                        thread.start()
                    except RuntimeError:
                        # 没有事件循环，直接运行
                        import asyncio
                        asyncio.run(self.page.window.center())
            except Exception as e:
                print(f"窗口居中失败（不影响功能）: {e}")

        thread = threading.Thread(target=center_after_delay)
        thread.daemon = True
        thread.start()

    def _initialize_plugins(self):
        """初始化插件系统"""
        print("[MainApp] Initializing plugin system...")

        # 扫描插件目录
        # __file__ 是 src/main_gui.py，所以 parent.parent 就是项目根目录
        project_root = Path(__file__).parent.parent
        plugins_dir = project_root / "plugins"

        print(f"[MainApp] Project root: {project_root}")
        print(f"[MainApp] Plugins directory: {plugins_dir}")
        print(f"[MainApp] Plugins directory exists: {plugins_dir.exists()}")

        plugin_count = self.plugin_manager.scan_plugins(plugins_dir)

        if plugin_count > 0:
            print(f"[MainApp] Plugin system initialized, found {plugin_count} plugins")
        else:
            print("[MainApp] No plugins found")

    def _cache_all_contents(self):
        """首次加载时缓存所有视图内容"""
        print("[MainApp] Initializing all views...")
        self.cached_contents[0] = self.answering_view.get_content()  # 评估答题
        self.cached_contents[1] = self.extraction_view.get_content()  # 答案提取
        self.cached_contents[2] = self.plugin_center_view.get_content()  # 插件中心
        self.cached_contents[3] = self.settings_view.get_content()  # 系统设置
        print("[MainApp] All views initialized")

    def _initialize_tray(self):
        """安装托盘菜单回调并应用当前设置。"""
        self.tray_manager.set_callbacks(
            on_show=lambda: self._dispatch_tray_action("show"),
            on_hide=lambda: self._dispatch_tray_action("hide"),
            on_quit=lambda: self._dispatch_tray_action("quit"),
        )
        self.apply_tray_settings()

    def apply_tray_settings(self) -> bool:
        """
        立即应用托盘设置。

        Returns:
            bool: 请求托盘功能时，图标是否成功启动。
        """
        configured = (
            self.settings_manager.get_minimize_to_tray()
            or self.settings_manager.get_close_to_tray()
        )
        should_run = configured or self._manual_tray_session or self._window_hidden_to_tray

        if should_run:
            available = self.tray_manager.start("ZX 答题助手")
        else:
            self.tray_manager.stop()
            available = False

        self.page.window.prevent_close = bool(
            self.settings_manager.get_close_to_tray() and available
        )
        self.page.update()

        if configured and not available:
            print("[MainApp] System tray unavailable; close/minimize interception disabled")
        return not configured or available

    def _dispatch_tray_action(self, action: str) -> None:
        """将 pystray 线程中的动作调度回 Flet 事件循环。"""
        async def handle_action():
            if action == "show":
                await self._show_from_tray()
            elif action == "hide":
                await self._hide_to_tray(manual=True)
            elif action == "quit":
                await self._quit_app()

        try:
            self.page.run_task(handle_action)
        except Exception as exc:
            print(f"[MainApp] Failed to dispatch tray action: {exc}")

    def request_hide_to_tray(self) -> None:
        """供页面操作请求隐藏到托盘，例如后台执行提取任务。"""
        self._dispatch_tray_action("hide")

    async def _on_window_event(self, e):
        """处理窗口的最小化和关闭动作。"""
        if self._quitting:
            return

        if e.type == ft.WindowEventType.CLOSE:
            if self.settings_manager.get_close_to_tray() and self.tray_manager.is_running():
                await self._hide_to_tray()
            else:
                await self._quit_app()
        elif e.type == ft.WindowEventType.MINIMIZE:
            if self.settings_manager.get_minimize_to_tray() and self.tray_manager.is_running():
                await self._hide_to_tray()

    async def _hide_to_tray(self, manual: bool = False) -> bool:
        """隐藏主窗口，保留可恢复的托盘入口。"""
        if manual:
            self._manual_tray_session = True

        if not self.tray_manager.start("ZX 答题助手"):
            self._manual_tray_session = False
            self._show_tray_error()
            return False

        self.page.window.minimized = False
        self.page.window.skip_task_bar = True
        self.page.window.visible = False
        self._window_hidden_to_tray = True
        self.page.update()
        return True

    async def _show_from_tray(self) -> None:
        """从托盘恢复并激活主窗口。"""
        if self._quitting:
            return

        self.page.window.skip_task_bar = False
        self.page.window.visible = True
        self.page.window.minimized = False
        self._window_hidden_to_tray = False
        self.page.update()
        try:
            await self.page.window.to_front()
        except Exception as exc:
            print(f"[MainApp] Unable to focus restored window: {exc}")
        finally:
            self._manual_tray_session = False
            self.apply_tray_settings()

    def _setup_window_close_watchdog(self) -> None:
        """
        注册窗口关闭看门狗：桌面客户端进程退出后强制清理并退出。

        关键问题（桌面模式）：用户点窗口 X 时，
          - on_disconnect 是 web 模式专用事件（见其 docstring："Called when a
            web user disconnects"），桌面模式不会触发；
          - prevent_close=False 时窗口直接关闭，不会派发 window.on_event(CLOSE)；
          - Flet 管道断裂让 asyncio 卡住（ProactorBasePipeTransport 的
            ConnectionResetError），ft.run(main) 不返回，main.py 的 finally 也进不到。
        于是 _quit_app、finally、断连看门狗全部失效，进程挂起、浏览器残留。

        本看门狗彻底绕开 Flet 事件系统：flet 桌面客户端是当前 Python 进程的子进程，
        用户关窗时它退出；独立守护线程轮询该子进程是否存在，消失即判定窗口已关闭，
        强杀整棵子进程树并 os._exit。该线程只用 time.sleep + psutil，不依赖 asyncio。
        """
        import os
        import threading
        import time

        def _direct_child_pids():
            """返回直接子进程 PID 集合；枚举失败返回 None（与「确无子进程」的空集区分）。"""
            try:
                import psutil
                return {c.pid for c in psutil.Process(os.getpid()).children(recursive=False)}
            except Exception:
                return None

        def _flet_client_pids() -> set:
            """识别 flet 桌面客户端子进程（按可执行路径/名称含 'flet' 过滤）。"""
            try:
                import psutil
                pids = set()
                for c in psutil.Process(os.getpid()).children(recursive=False):
                    try:
                        exe = (c.exe() or "").lower()
                        name = (c.name() or "").lower()
                        if "flet" in exe or "flet" in name:
                            pids.add(c.pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                return pids
            except Exception:
                return set()

        # 在 MainApp 初始化时刻快照：此时插件还没启动浏览器，直接子进程只有 flet 客户端。
        # 这样后续插件派生的 node.exe / chrome.exe 不会进入监控集合，避免误判。
        targets = _flet_client_pids() or _direct_child_pids()

        # 同时注册 on_disconnect 作为 web 模式的备用信号（桌面模式下不会触发，无副作用）
        self._disconnect_event = threading.Event()

        def _on_disconnect(_e):
            try:
                self._disconnect_event.set()
            except Exception:
                pass

        try:
            self.page.on_disconnect = _on_disconnect
        except Exception:
            pass

        def _force_exit():
            print("[MainApp] Window closed — forcing exit.")
            try:
                from src.core.browser import get_browser_manager
                get_browser_manager().force_kill_process_tree()
            except Exception:
                pass
            try:
                import sys as _sys
                _sys.stdout.flush()
            except Exception:
                pass
            os._exit(0)

        def _watch():
            if not targets:
                print("[MainApp] Window-close watchdog: no client process to monitor.")
                return
            while True:
                time.sleep(1.5)
                # 信号 A：web 模式 on_disconnect
                if self._disconnect_event.is_set():
                    time.sleep(1.0)
                    _force_exit()
                    return
                # 信号 B：桌面模式 flet 客户端子进程消失
                current = _direct_child_pids()
                if current is None:
                    continue  # psutil 枚举失败：跳过本轮，避免误判为窗口关闭
                if not (targets & current):
                    time.sleep(1.0)  # 短暂等待，给优雅路径最后的机会
                    _force_exit()
                    return

        threading.Thread(target=_watch, daemon=True).start()

    async def _quit_app(self) -> None:
        """从窗口或托盘菜单正常退出应用。"""
        if self._quitting:
            return

        print("[MainApp] Quitting application...")

        # 停止托盘
        self.tray_manager.stop()

        # 设置退出标志
        self._quitting = True
        self.page.window.prevent_close = False

        # 1) 立即启动看门狗（必须在任何 await 之前）。
        #    窗口关闭后 Flet 与子进程的管道会被强行打断，触发 ProactorBasePipeTransport
        #    的 ConnectionResetError，后续 await 可能永远完不成。看门狗在独立线程里计时，
        #    到点强杀整棵子进程树并 os._exit，确保进程一定退出、浏览器不会成为孤儿。
        self._start_exit_watchdog()

        # 2) 关闭窗口（给用户视觉反馈；即便此处挂起，看门狗也会兜底）
        try:
            await self.page.window.close()
        except Exception as e:
            print(f"[MainApp] Error closing window: {e}")

        # 3) 在独立线程中清理浏览器 + 强杀子进程树
        import asyncio
        await asyncio.to_thread(self._cleanup_browser_before_exit)

        # 4) 销毁页面连接
        try:
            self.page.destroy()
        except Exception as e:
            print(f"[MainApp] Error destroying page: {e}")

    def _cleanup_browser_before_exit(self) -> None:
        """退出前尽力清理 Playwright 浏览器，并强杀整棵子进程树（带超时保护）。"""
        import threading

        # 1) 优雅关闭浏览器（close_browser 内部派发到工作线程，这里再加一层超时）
        try:
            from src.core.browser import get_browser_manager
            manager = get_browser_manager()
            if manager._browser is not None or manager._playwright is not None:
                print("[MainApp] Closing browser before exit...")
                done = threading.Event()

                def _do_close():
                    try:
                        manager.close_browser()
                    except Exception as exc:
                        print(f"[MainApp] Browser close error (ignored): {exc}")
                    finally:
                        done.set()

                threading.Thread(target=_do_close, daemon=True).start()
                done.wait(timeout=2.0)  # 最多等 2 秒，避免阻塞退出流程
        except Exception as exc:
            print(f"[MainApp] Browser cleanup skipped: {exc}")

        # 2) 强杀整棵子进程树：Playwright Node driver 是当前进程的子进程，
        #    但浏览器（Chrome/Edge）由 Node 派生属于孙进程，只优雅关闭或只杀 node.exe
        #    会让浏览器成为孤儿继续驻留。递归杀掉全部后代才能彻底清理。
        try:
            from src.core.browser import get_browser_manager
            get_browser_manager().force_kill_process_tree()
        except Exception as exc:
            print(f"[MainApp] Process tree cleanup skipped: {exc}")

    def _start_exit_watchdog(self, delay: float = 3.0) -> None:
        """启动看门狗守护线程：超时后强杀子进程树并强制结束进程，确保终端不会挂起。"""
        import os
        import threading
        import time

        def _watchdog():
            time.sleep(delay)
            print("[MainApp] Forcing process exit (watchdog).")
            try:
                from src.core.browser import get_browser_manager
                get_browser_manager().force_kill_process_tree()
            except Exception:
                pass
            try:
                import sys as _sys
                _sys.stdout.flush()
            except Exception:
                pass
            os._exit(0)

        threading.Thread(target=_watchdog, daemon=True).start()

    def _show_tray_error(self) -> None:
        """在无法进入后台模式时向用户说明原因。"""
        reason = self.tray_manager.get_unavailable_reason()
        snack = ft.SnackBar(
            content=ft.Text(f"系统托盘不可用，无法隐藏到后台；{reason}。"),
            bgcolor=ft.Colors.ORANGE,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

    def _build_ui(self):
        """构建用户界面"""
        nav_icon_color = Palette.NAV_TEXT
        selected_icon_color = Palette.SURFACE
        self.navigation_rail = ft.NavigationRail(
            selected_index=0,
            extended=True,
            min_width=72,
            min_extended_width=220,
            bgcolor=Palette.NAV,
            indicator_color=Palette.NAV_SELECTED,
            group_alignment=-0.8,
            selected_label_text_style=Fonts.text(
                color=Palette.SURFACE,
                weight=ft.FontWeight.W_600,
            ),
            unselected_label_text_style=Fonts.text(color=Palette.NAV_TEXT),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=nav_icon_color),
                    selected_icon=ft.Icon(ft.Icons.CHECK_CIRCLE, color=selected_icon_color),
                    label="评估答题",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.DOWNLOAD_OUTLINED, color=nav_icon_color),
                    selected_icon=ft.Icon(ft.Icons.DOWNLOAD_DONE, color=selected_icon_color),
                    label="答案提取",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.EXTENSION_OUTLINED, color=nav_icon_color),
                    selected_icon=ft.Icon(ft.Icons.EXTENSION, color=selected_icon_color),
                    label="插件中心",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=nav_icon_color),
                    selected_icon=ft.Icon(ft.Icons.SETTINGS, color=selected_icon_color),
                    label="系统设置",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.INFO_OUTLINE, color=nav_icon_color),
                    selected_icon=ft.Icon(ft.Icons.INFO, color=selected_icon_color),
                    label="关于",
                ),
            ],
            on_change=self._on_destination_changed,
            expand=True,
        )

        print("[MainApp] Initializing answering view...")
        initial_content = self.answering_view.get_content()
        self.cached_contents[0] = initial_content
        print("[MainApp] Answering view initialized")

        self.content_area = ft.Column(
            [
                ft.Container(
                    content=initial_content,
                    padding=ft.Padding.only(left=30, top=24, right=30, bottom=30),
                    expand=True,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.brand_text = ft.Column(
            [
                ft.Text("ZX Assistant", size=17, weight=ft.FontWeight.BOLD, color=Palette.SURFACE),
                ft.Text("智能答题工作台", size=11, color=Palette.NAV_TEXT),
            ],
            spacing=1,
            tight=True,
        )
        self.collapse_button = ft.IconButton(
            icon=ft.Icons.MENU_OPEN,
            icon_color=Palette.NAV_TEXT,
            tooltip="折叠导航栏",
            on_click=self._toggle_rail,
        )
        self.sidebar_footer = ft.Container(
            content=ft.Column(
                [
                    ft.Text("DESKTOP APP", size=10, color=Palette.NAV_TEXT),
                    ft.Text(
                        f"v{version.VERSION if hasattr(version, 'VERSION') else '--'}",
                        size=12,
                        color=Palette.SURFACE,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=18, vertical=16),
            bgcolor="#182236",
            border_radius=Radius.MEDIUM,
        )
        self.brand_logo = ft.Container(
            content=ft.Icon(ft.Icons.SCHOOL, size=25, color=Palette.SURFACE),
            width=43,
            height=43,
            bgcolor=Palette.PRIMARY,
            border_radius=Radius.MEDIUM,
            alignment=ft.Alignment(0, 0),
        )
        self.sidebar_header = ft.Container(
            content=ft.Row(
                [
                    self.brand_logo,
                    self.brand_text,
                    ft.Container(expand=True),
                    self.collapse_button,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(left=13, top=18, right=9, bottom=12),
        )
        self.sidebar = ft.Container(
            content=ft.Column(
                [
                    self.sidebar_header,
                    self.navigation_rail,
                    self.sidebar_footer,
                ],
                spacing=8,
                expand=True,
            ),
            width=self.rail_width,
            bgcolor=Palette.NAV,
            padding=ft.Padding.only(left=8, right=8, bottom=15),
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        )

        self.header_title = ft.Text(
            self.destination_details[0][0],
            size=20,
            weight=ft.FontWeight.BOLD,
            color=Palette.TEXT,
        )
        self.header_subtitle = ft.Text(
            self.destination_details[0][1],
            size=12,
            color=Palette.TEXT_MUTED,
        )
        top_bar = ft.Container(
            content=ft.Row(
                [
                    ft.Column([self.header_title, self.header_subtitle], spacing=2, tight=True),
                    ft.Container(expand=True),
                    status_chip("本地运行", color=Palette.ACCENT, bgcolor=Palette.ACCENT_SOFT),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=30, vertical=18),
            bgcolor=Palette.SURFACE,
            border=ft.border.only(bottom=ft.BorderSide(1, Palette.BORDER)),
        )
        workspace = ft.Column(
            [top_bar, self.content_area],
            spacing=0,
            expand=True,
        )

        main_row = ft.Row(
            [
                self.sidebar,
                workspace,
            ],
            spacing=0,
            expand=True,
        )

        self.page.add(main_row)

    def _on_destination_changed(self, e):
        """导航栏切换事件处理（使用缓存保持状态）"""
        self.current_destination = e.control.selected_index
        title, subtitle = self.destination_details[self.current_destination]
        self.header_title.value = title
        self.header_subtitle.value = subtitle

        # 使用缓存的内容，而不是重新创建
        # 这样可以保持各个视图的状态（如输入框内容、滚动位置等）
        cached_content = self.cached_contents.get(self.current_destination)

        if cached_content is None:
            # 如果缓存不存在（不应该发生），则创建并缓存
            print(f"[MainApp] View {self.current_destination} not cached, creating...")
            if self.current_destination == 0:
                cached_content = self.answering_view.get_content()
            elif self.current_destination == 1:
                cached_content = self.extraction_view.get_content()
            elif self.current_destination == 2:
                cached_content = self.plugin_center_view.get_content()
            elif self.current_destination == 3:
                cached_content = self.settings_view.get_content()
            elif self.current_destination == 4:
                cached_content = self.about_view.get_content()
            else:
                return

            # 缓存新创建的内容
            self.cached_contents[self.current_destination] = cached_content

        # 更新 Column 中第一个 Container 的 content
        self.content_area.controls[0].content = cached_content
        self.page.update()

    def _toggle_rail(self, e):
        """切换导航栏展开/折叠状态"""
        self.rail_expanded = not self.rail_expanded

        if self.rail_expanded:
            self.navigation_rail.extended = True
            self.navigation_rail.label_type = None
            self.sidebar.width = self.rail_width
            self.brand_logo.visible = True
            self.brand_text.visible = True
            self.sidebar_footer.visible = True
            self.sidebar_header.content.spacing = 10
            self.sidebar_header.padding = ft.Padding.only(left=13, top=18, right=9, bottom=12)
            self.collapse_button.icon = ft.Icons.MENU_OPEN
            self.collapse_button.tooltip = "折叠导航栏"
        else:
            self.navigation_rail.extended = False
            self.navigation_rail.label_type = ft.NavigationRailLabelType.SELECTED
            self.sidebar.width = 88
            self.brand_logo.visible = False
            self.brand_text.visible = False
            self.sidebar_footer.visible = False
            self.sidebar_header.content.spacing = 0
            self.sidebar_header.padding = ft.Padding.only(left=12, top=18, right=12, bottom=12)
            self.collapse_button.icon = ft.Icons.MENU
            self.collapse_button.tooltip = "展开导航栏"

        self.page.update()


def main(page: ft.Page):
    """
    Main entry point for the Flet GUI application.

    Args:
        page (ft.Page): The main page control provided by Flet framework
    """
    # 创建启动加载界面
    loading_view = create_loading_view(page)
    page.add(loading_view)
    page.update()

    # 使用 asyncio 在后台初始化应用
    import asyncio

    async def initialize_app():
        """异步初始化应用"""
        try:
            # 模拟加载延迟（确保用户能看到启动动画）
            await asyncio.sleep(0.5)

            # 清空加载界面
            page.clean()
            page.update()

            # 创建主应用
            app = MainApp(page)

            # 添加淡入动画效果
            await fade_in_app(page)

        except Exception as e:
            page.clean()
            page.add(
                ft.Column(
                    [
                        ft.Icon(ft.Icons.ERROR, size=50, color=ft.Colors.RED),
                        ft.Text("启动失败", size=30, weight=ft.FontWeight.BOLD),
                        ft.Text(f"错误信息: {e}", color=ft.Colors.RED),
                        ft.ElevatedButton(
                            "重试",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda _: page.window.close()
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20
                )
            )
            page.update()

    # 检查是否在 asyncio 事件循环中
    try:
        asyncio.get_running_loop()
        # 如果已经在事件循环中，直接创建同步版本
        page.clean()
        app = MainApp(page)
    except RuntimeError:
        # 没有事件循环，使用异步初始化
        # Flet 会自动处理事件循环
        import threading
        import time

        def sync_init():
            """同步初始化（兼容模式）"""
            time.sleep(0.5)  # 显示加载动画
            page.clean()
            app = MainApp(page)

        # 在新线程中运行同步初始化
        thread = threading.Thread(target=sync_init)
        thread.start()


def create_loading_view(page: ft.Page):
    """
    创建启动加载界面

    Args:
        page: Flet 页面对象

    Returns:
        加载界面的控件
    """
    return ft.Container(
        content=ft.Column(
            [
                # Logo/图标
                ft.Icon(
                    ft.Icons.SCHOOL,
                    size=80,
                    color=Palette.PRIMARY,
                    animate_opacity=200,
                ),

                # 标题
                ft.Text(
                    "ZX 智能答题助手",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=Palette.TEXT,
                    animate_opacity=200,
                ),

                ft.Text(
                    version.VERSION if hasattr(version, 'VERSION') else "v3.2.0",
                    size=16,
                    color=Palette.TEXT_MUTED,
                    opacity=0.7,
                ),

                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),

                # 加载进度条（带动画）
                ft.ProgressBar(
                    width=300,
                    color=Palette.PRIMARY,
                    bgcolor=Palette.PRIMARY_SOFT,
                    bar_height=20,
                ),

                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 加载提示文字（带切换动画）
                ft.Text(
                    "正在初始化组件...",
                    size=14,
                    color=Palette.TEXT_MUTED,
                    animate_opacity=300,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        alignment=ft.Alignment(0, 0),  # 使用 Alignment(0, 0) 代替 alignment.center
        expand=True,
        # 渐变背景
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),  # 使用 Alignment(-1, -1) 代替 alignment.top_center
            end=ft.Alignment(1, 1),      # 使用 Alignment(1, 1) 代替 alignment.bottom_center
            colors=[
                Palette.SURFACE,
                Palette.PRIMARY_SOFT,
            ],
        ),
    )


def fade_in_app(page: ft.Page):
    """
    应用淡入动画（简化版本）

    Args:
        page: Flet 页面对象
    """
    # 简化版本，不添加复杂动画以兼容 Flet 0.82+
    # 只需要更新页面即可
    page.update()


def run_app():
    """
    Launch the Flet application.

    This function serves as the entry point for running the GUI application.
    It can be called from other modules or run directly.
    """
    try:
        # 尝试使用桌面可执行文件
        ft.run(main)
    except Exception as e:
        # 如果桌面可执行文件不可用，尝试使用内置 WebView
        error_msg = str(e)
        if "flet.exe" in error_msg or "flet executable" in error_msg:
            print("⚠️  Flet 桌面可执行文件未找到")
            print("📥 正在切换到内置 WebView 模式...")

            # 设置使用内置模式
            os.environ["FLET_DESKTOP_EXE_PATH"] = ""
            os.environ["FLET_WEB_BROWSER_PATH"] = ""

            # 重新尝试启动
            try:
                ft.run(main, view=ft.AppView.WEB_BROWSER)
            except Exception as e2:
                print(f"❌ 启动 Flet 失败: {e2}")
                print("\n💡 可能的解决方案:")
                print("   1. 确保已安装 Flet: pip install flet")
                print("   2. 检查网络连接（首次运行需要下载组件）")
                raise
        else:
            print(f"❌ 启动 Flet 失败: {e}")
            raise


if __name__ == "__main__":
    run_app()
