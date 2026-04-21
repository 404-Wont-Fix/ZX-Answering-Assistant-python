"""
插件中心视图模块

此模块将在第二阶段实现完整的插件中心功能
目前为占位符实现
"""

import flet as ft


class PluginCenterView:
    """插件中心视图类"""

    def __init__(self, page: ft.Page):
        """
        初始化插件中心视图

        Args:
            page (ft.Page): Flet页面对象
        """
        self.page = page

    def get_content(self) -> ft.Control:
        """
        获取插件中心页面内容

        Returns:
            ft.Control: 插件中心页面的根控件
        """
        return ft.Column(
            [
                ft.Text(
                    "插件中心",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.EXTENSION, size=80, color=ft.Colors.BLUE),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "插件中心即将上线",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "敬请期待更多功能插件",
                                    size=16,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "未来将通过插件系统支持：",
                                    size=14,
                                    color=ft.Colors.GREY_700,
                                ),
                                ft.Text(
                                    "• 课程认证",
                                    size=14,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Text(
                                    "• 云考试",
                                    size=14,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Text(
                                    "• 评估出题",
                                    size=14,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Text(
                                    "• 安全微伴",
                                    size=14,
                                    color=ft.Colors.GREY_600,
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
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
