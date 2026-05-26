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

from src.core.browser import get_browser_manager
from src.core.app_state import get_app_state
from src.core.plugin_manager import get_plugin_manager
from src.core.api_client import get_api_client
from src.core.tray_manager import get_tray_manager
from src.core.config import get_settings_manager
from pathlib import Path


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

        # 导航栏展开状态
        self.rail_expanded = True
        self.rail_width = 200

        # 初始化插件管理器（在创建视图之前）
        self.plugin_manager = get_plugin_manager()
        self._initialize_plugins()

        # 初始化视图模块（传递MainApp引用以便视图可以切换导航）
        self.answering_view = AnsweringView(page, main_app=self)
        self.extraction_view = ExtractionView(page)
        self.plugin_center_view = PluginCenterView(page, main_app=self)
        self.settings_view = SettingsView(page)
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

        # 初始化系统托盘
        self._initialize_tray()

        # 在页面加载完成后居中窗口
        self._center_window_async()

        # 启动托盘事件处理
        self._start_tray_event_loop()

    def _setup_page(self):
        """配置页面属性"""
        self.page.title = "ZX Answering Assistant"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 1000
        self.page.window.height = 700
        # 不使用异步center()方法，而是在页面加载后手动居中
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.GREY_50

        # 注册窗口事件处理
        self.page.window.on_event = self._on_window_event

        # 设置托盘相关属性
        settings_manager = get_settings_manager()
        if settings_manager.get_close_to_tray():
            self.page.window.prevent_close = True  # 阻止默认关闭行为

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

    def _on_window_event(self, e):
        """
        统一的窗口事件处理函数

        Args:
            e: WindowEvent 对象，包含事件类型信息
        """
        import flet as ft

        settings_manager = get_settings_manager()
        tray_manager = get_tray_manager()

        if e.type == ft.WindowEventType.CLOSE:
            # 窗口关闭事件
            if settings_manager.get_close_to_tray() and tray_manager.is_available():
                # 关闭到托盘
                print("[MainApp] Close to tray enabled, hiding window...")
                self._hide_to_tray()
            else:
                # 真正关闭应用
                print("[MainApp] Closing window...")
                print("[MainApp] Browser resources will be cleaned up on exit")
                # 停止托盘图标
                if tray_manager.is_running():
                    tray_manager.stop()
                # 销毁窗口
                self.page.window.destroy()

        elif e.type == ft.WindowEventType.MINIMIZE:
            # 窗口最小化事件
            if settings_manager.get_minimize_to_tray() and tray_manager.is_available():
                # 最小化到托盘
                print("[MainApp] Minimize to tray enabled, hiding window...")
                self._hide_to_tray()

    def _hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        try:
            print("[MainApp] _hide_to_tray called")
            # 设置标志，让主循环处理
            self._should_hide_window = True
            # 直接执行（因为隐藏操作比较简单）
            self.page.window.visible = False
            self.page.window.skip_task_bar = True  # 从任务栏隐藏
            self.page.update()
            self._should_hide_window = False
            print("[MainApp] Window hidden to tray successfully")
        except Exception as e:
            print(f"[MainApp] Error hiding window to tray: {e}")
            import traceback
            traceback.print_exc()

    def _show_from_tray(self):
        """从系统托盘显示窗口"""
        try:
            print("[MainApp] _show_from_tray called")

            # 直接设置窗口属性
            self.page.window.visible = True
            self.page.window.skip_task_bar = False
            self.page.update()
            print("[MainApp] Window properties updated")

            # 使用 Windows API 强制显示窗口
            def force_show_window():
                try:
                    import time
                    import ctypes.wintypes

                    # 等待 Flet 更新生效
                    time.sleep(0.3)

                    # 定义 Windows API 函数
                    EnumWindows = ctypes.windll.user32.EnumWindows
                    EnumWindows.argtypes = [ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM), ctypes.wintypes.LPARAM]
                    EnumWindows.restype = ctypes.wintypes.BOOL

                    GetWindowText = ctypes.windll.user32.GetWindowTextW
                    GetWindowText.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.wintypes.INT]
                    GetWindowText.restype = ctypes.wintypes.INT

                    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                    GetWindowTextLength.argtypes = [ctypes.wintypes.HWND]
                    GetWindowTextLength.restype = ctypes.wintypes.INT

                    ShowWindow = ctypes.windll.user32.ShowWindow
                    ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.INT]
                    ShowWindow.restype = ctypes.wintypes.BOOL

                    SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
                    SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]
                    SetForegroundWindow.restype = ctypes.wintypes.BOOL

                    # SW_RESTORE = 9, SW_SHOW = 5
                    SW_RESTORE = 9
                    SW_SHOW = 5

                    found_windows = []

                    def callback(hwnd, lParam):
                        try:
                            length = GetWindowTextLength(hwnd) + 1
                            buffer = ctypes.create_unicode_buffer(length)
                            GetWindowText(hwnd, buffer, length)
                            title = buffer.value

                            if "ZX" in title and ("Answering" in title or "答题" in title):
                                found_windows.append(hwnd)
                                print(f"[MainApp] Found window: {title}")

                                # 显示并恢复窗口
                                ShowWindow(hwnd, SW_RESTORE)
                                time.sleep(0.1)
                                # 设置为前台窗口
                                SetForegroundWindow(hwnd)
                                print("[MainApp] Window activated via Windows API")
                        except:
                            pass
                        return True

                    # 创建回调函数类型并枚举窗口
                    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
                    EnumWindows(WNDENUMPROC(callback), 0)

                    if found_windows:
                        print("[MainApp] Successfully showed window via Windows API")
                    else:
                        print("[MainApp] Window not found via Windows API, trying alternative method...")

                        # 备用方法：查找所有包含 "ZX" 的窗口
                        def callback_alternative(hwnd, lParam):
                            try:
                                length = GetWindowTextLength(hwnd) + 1
                                if length > 1:
                                    buffer = ctypes.create_unicode_buffer(length)
                                    GetWindowText(hwnd, buffer, length)
                                    title = buffer.value

                                    if "ZX" in title:
                                        ShowWindow(hwnd, SW_RESTORE)
                                        SetForegroundWindow(hwnd)
                                        print(f"[MainApp] Showed window via alternative method: {title}")
                            except:
                                pass
                            return True

                        EnumWindows(WNDENUMPROC(callback_alternative), 0)

                except Exception as e:
                    print(f"[MainApp] Windows API method failed: {e}")
                    import traceback
                    traceback.print_exc()

            import threading
            thread = threading.Thread(target=force_show_window, daemon=True)
            thread.start()

            print("[MainApp] Window show operations completed")

        except Exception as e:
            print(f"[MainApp] Error showing window from tray: {e}")
            import traceback
            traceback.print_exc()

    def _quit_app(self):
        """退出应用程序"""
        print("[MainApp] Quitting application...")

        # 停止托盘图标
        tray_manager = get_tray_manager()
        if tray_manager.is_running():
            tray_manager.stop()

        # 关闭窗口并强制退出程序
        try:
            print("[MainApp] Destroying Flet window...")
            self.page.window.destroy()
        except Exception as e:
            print(f"[MainApp] Error destroying window: {e}")

        # 无论窗口是否成功销毁，都强制退出程序
        import sys
        import time
        import threading

        def force_quit():
            """强制退出程序的线程函数"""
            try:
                time.sleep(0.5)  # 等待清理完成
                print("[MainApp] Force quitting application...")
                # 使用多种方法确保程序退出
                try:
                    sys.exit(0)
                except:
                    # 如果 sys.exit() 不工作，使用 os._exit()
                    import os
                    os._exit(0)
            except Exception as e:
                print(f"[MainApp] Force quit failed: {e}")
                import os
                os._exit(0)

        # 在单独线程中强制退出，避免阻塞当前操作
        quit_thread = threading.Thread(target=force_quit, daemon=False)
        quit_thread.start()

        print("[MainApp] Quit sequence initiated")

    def _initialize_tray(self):
        """初始化系统托盘功能"""
        tray_manager = get_tray_manager()

        if not tray_manager.is_available():
            print("[MainApp] System tray not available (pystray not installed)")
            return

        # 设置托盘回调函数
        tray_manager.set_callbacks(
            on_show=self._show_from_tray,
            on_hide=self._hide_to_tray,
            on_quit=self._quit_app
        )

        # 启动托盘图标
        settings_manager = get_settings_manager()
        if settings_manager.get_minimize_to_tray() or settings_manager.get_close_to_tray():
            if tray_manager.start("ZX答题助手"):
                print("[MainApp] System tray started successfully")
            else:
                print("[MainApp] Failed to start system tray")

    def _start_tray_event_loop(self):
        """启动托盘事件处理循环"""
        import threading
        import time

        def process_tray_events():
            """处理托盘事件的后台线程"""
            while True:
                try:
                    tray_manager = get_tray_manager()
                    if tray_manager.is_running():
                        # 处理托盘事件，将操作放入队列
                        tray_manager.process_pending_actions()
                    time.sleep(0.1)  # 每100ms检查一次
                except Exception as e:
                    print(f"[MainApp] Error processing tray events: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)  # 出错时等待1秒

        # 启动后台线程处理托盘事件
        tray_thread = threading.Thread(target=process_tray_events, daemon=True)
        tray_thread.start()
        print("[MainApp] Tray event loop started")

    def _build_ui(self):
        """构建用户界面"""
        # 创建导航栏
        self.navigation_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=self.rail_width,
            leading=ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.SCHOOL, size=40, color=ft.Colors.BLUE),
                        ft.Text(
                            "ZX助手",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5,
                ),
                padding=ft.Padding.symmetric(vertical=20),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.CHECK_CIRCLE,
                    selected_icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    label="评估答题",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD,
                    selected_icon=ft.Icons.DOWNLOAD_DONE,
                    label="答案提取",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.EXTENSION,
                    selected_icon=ft.Icons.WIDGETS,
                    label="插件中心",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS,
                    selected_icon=ft.Icons.SETTINGS,
                    label="系统设置",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INFO,
                    selected_icon=ft.Icons.INFO_OUTLINE,
                    label="关于",
                ),
            ],
            on_change=self._on_destination_changed,
            bgcolor=ft.Colors.BLUE_50,
        )

        # 初始化第一个视图（评估答题）并缓存
        print("[MainApp] Initializing answering view...")
        initial_content = self.answering_view.get_content()
        self.cached_contents[0] = initial_content
        print("[MainApp] Answering view initialized")

        # 创建内容区域（添加滚动支持）- 使用初始化的内容
        self.content_area = ft.Column(
            [
                ft.Container(
                    content=initial_content,  # 使用刚初始化的评估答题页面
                    expand=True,
                )
            ],
            scroll=ft.ScrollMode.AUTO,  # 关键：内容区域需要滚动
            expand=True,
        )

        # 主布局 - 完全按照 StackOverflow 的正确答案
        # NavigationRail 直接放在 Row 中，不要用 Column 包裹！
        main_row = ft.Row(
            [
                # NavigationRail 直接放在这里
                self.navigation_rail,
                # 分隔线
                ft.VerticalDivider(width=1),
                # 右侧内容区域
                self.content_area,
            ],
            expand=True,  # Row 必须设置 expand=True
        )

        # 添加到页面
        self.page.add(main_row)

    def _on_destination_changed(self, e):
        """导航栏切换事件处理（使用缓存保持状态）"""
        self.current_destination = e.control.selected_index

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
            # 展开导航栏
            self.navigation_rail.label_type = ft.NavigationRailLabelType.ALL
            self.navigation_rail.min_extended_width = self.rail_width
            self.collapse_button.icon = ft.Icons.MENU_OPEN
        else:
            # 折叠导航栏
            self.navigation_rail.label_type = ft.NavigationRailLabelType.SELECTED
            self.navigation_rail.min_extended_width = 56
            self.collapse_button.icon = ft.Icons.MENU

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
                    color=ft.Colors.BLUE,
                    animate_opacity=200,
                ),

                # 标题
                ft.Text(
                    "ZX 智能答题助手",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_900,
                    animate_opacity=200,
                ),

                ft.Text(
                    version.VERSION if hasattr(version, 'VERSION') else "v3.2.0",
                    size=16,
                    color=ft.Colors.GREY_600,
                    opacity=0.7,
                ),

                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),

                # 加载进度条（带动画）
                ft.ProgressBar(
                    width=300,
                    color=ft.Colors.BLUE,
                    bgcolor=ft.Colors.BLUE_50,
                    bar_height=20,
                ),

                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 加载提示文字（带切换动画）
                ft.Text(
                    "正在初始化组件...",
                    size=14,
                    color=ft.Colors.GREY_600,
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
                "#ffffff",  # 白色
                "#f0f4ff",  # 淡蓝色
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
