"""
ZX Answering Assistant - GUI Main Module

This module is responsible for the underlying structure setup of the UI using Flet framework.
It provides the foundation for building the graphical user interface with a collapsible navigation bar.
"""

import flet as ft
import webbrowser
import version
from src.ui.views.answering_view import AnsweringView
from src.ui.views.extraction_view import ExtractionView
from src.ui.views.settings_view import SettingsView
from src.ui.views.course_certification_view import CourseCertificationView
from src.ui.views.cloud_exam_view import CloudExamView


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

        # 初始化视图模块（传递MainApp引用以便视图可以切换导航）
        self.answering_view = AnsweringView(page, main_app=self)
        self.extraction_view = ExtractionView(page)
        self.settings_view = SettingsView(page)
        self.course_certification_view = CourseCertificationView(page)
        self.cloud_exam_view = CloudExamView(page)

        # 缓存每个视图的内容（保持状态）
        self.cached_contents = {
            0: None,  # 评估答题
            1: None,  # 答案提取
            2: None,  # 课程认证
            3: None,  # 云考试
            4: None,  # 设置
            5: None,  # 关于
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

    def _cache_all_contents(self):
        """首次加载时缓存所有视图内容"""
        print("🔄 正在初始化所有视图...")
        self.cached_contents[0] = self.answering_view.get_content()
        self.cached_contents[1] = self.extraction_view.get_content()
        self.cached_contents[2] = self.settings_view.get_content()
        self.cached_contents[3] = self._get_about_content()
        print("✅ 所有视图已初始化")

    def _on_window_close(self):
        """
        窗口关闭时的清理函数

        注意：不在此时直接关闭浏览器，避免 greenlet 线程切换问题
        atexit 处理器会负责清理
        """
        print("🔄 正在关闭窗口...")
        print("💡 浏览器资源将在程序退出时自动清理")
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
                    icon=ft.Icons.EDIT_NOTE,
                    selected_icon=ft.Icons.EDIT_NOTE,
                    label="评估答题",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD,
                    selected_icon=ft.Icons.DOWNLOAD,
                    label="答案提取",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SCHOOL,
                    selected_icon=ft.Icons.SCHOOL,
                    label="课程认证",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CLOUD_QUEUE,
                    selected_icon=ft.Icons.CLOUD,
                    label="云考试",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS,
                    selected_icon=ft.Icons.SETTINGS,
                    label="设置",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.INFO_OUTLINE,
                    selected_icon=ft.Icons.INFO,
                    label="关于",
                ),
            ],
            on_change=self._on_destination_changed,
            bgcolor=ft.Colors.BLUE_50,
        )

        # 初始化第一个视图（评估答题）并缓存
        print("🔄 正在初始化评估答题视图...")
        initial_content = self.answering_view.get_content()
        self.cached_contents[0] = initial_content
        print("✅ 评估答题视图已初始化")

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
            print(f"⚠️ 视图 {self.current_destination} 未缓存，正在创建...")
            if self.current_destination == 0:
                cached_content = self.answering_view.get_content()
            elif self.current_destination == 1:
                cached_content = self.extraction_view.get_content()
            elif self.current_destination == 2:
                cached_content = self.course_certification_view.get_content()
            elif self.current_destination == 3:
                cached_content = self.cloud_exam_view.get_content()
            elif self.current_destination == 4:
                cached_content = self.settings_view.get_content()
            elif self.current_destination == 5:
                cached_content = self._get_about_content()
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

    def _get_answering_content(self):
        """获取评估答题页面内容（使用视图模块）"""
        return self.answering_view.get_content()

    def _get_extraction_content(self):
        """获取答案提取页面内容（使用视图模块）"""
        return self.extraction_view.get_content()

    def _get_settings_content(self):
        """获取设置页面内容（使用视图模块）"""
        return self.settings_view.get_content()

    def _get_about_content(self):
        """获取关于页面内容"""
        return ft.Column(
            [
                ft.Text(
                    "关于",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.SCHOOL, size=80, color=ft.Colors.BLUE),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "ZX Answering Assistant",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "智能答题助手系统",
                                    size=16,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE),
                                    title=ft.Text("版本", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text(f"v{version.VERSION}"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CODE, color=ft.Colors.GREEN),
                                    title=ft.Text("开发语言", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("Python + Flet"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.WEB, color=ft.Colors.PURPLE),
                                    title=ft.Text("自动化框架", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("Playwright"),
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        padding=30,
                        width=500,
                    ),
                    elevation=2,
                ),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.GestureDetector(
                    content=ft.Text(
                        "© 2025 TianJiaJi. All rights reserved.",
                        size=12,
                        color=ft.Colors.BLUE,
                    ),
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap=lambda e: webbrowser.open("https://github.com/TianJiaJi/ZX-Answering-Assistant-python"),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


def main(page: ft.Page):
    """
    Main entry point for the Flet GUI application.

    Args:
        page (ft.Page): The main page control provided by Flet framework
    """
    app = MainApp(page)


def run_app():
    """
    Launch the Flet application.

    This function serves as the entry point for running the GUI application.
    It can be called from other modules or run directly.
    """
    ft.app(target=main)


if __name__ == "__main__":
    run_app()
