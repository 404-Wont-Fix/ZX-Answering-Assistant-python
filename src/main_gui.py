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

    def _setup_page(self):
        """配置页面属性"""
        self.page.title = "ZX Answering Assistant"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 1000
        self.page.window.height = 700
        self.page.window_center = True  # 使用属性而不是方法调用
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.GREY_50

        # 注册窗口关闭时的清理函数
        self.page.on_close = self._on_window_close

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

    def _on_window_close(self):
        """
        窗口关闭时的清理函数

        注意：不在此时直接关闭浏览器，避免 greenlet 线程切换问题
        atexit 处理器会负责清理
        """
        print("[MainApp] Closing window...")
        print("[MainApp] Browser resources will be cleaned up on exit")
        # 不在这里关闭浏览器，避免 greenlet 线程切换错误
        # atexit 处理器会在 Python 退出时自动清理

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
                padding=ft.padding.symmetric(vertical=20),
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
        ft.app(target=main)
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
                ft.app(target=main, view=ft.AppView.WEB_BROWSER)
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
