"""
ZX Answering Assistant - 设置视图模块

This module contains the UI components for the settings page.
"""

import flet as ft


class SettingsView:
    """设置页面视图"""

    def __init__(self, page: ft.Page):
        """
        初始化设置视图

        Args:
            page (ft.Page): Flet页面对象
        """
        self.page = page

    def get_content(self) -> ft.Column:
        """
        获取设置页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        return ft.Column(
            [
                ft.Text(
                    "设置",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.TIMER, color=ft.Colors.RED),
                                    title=ft.Text("请求延迟", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("设置API请求之间的延迟时间"),
                                    trailing=ft.TextField(
                                        value="600",
                                        width=100,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.REFRESH, color=ft.Colors.ORANGE),
                                    title=ft.Text("最大重试次数", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("设置请求失败时的最大重试次数"),
                                    trailing=ft.TextField(
                                        value="3",
                                        width=100,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PALETTE, color=ft.Colors.PINK),
                                    title=ft.Text("主题模式", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("选择界面主题（浅色/深色）"),
                                    trailing=ft.Dropdown(
                                        options=[
                                            ft.dropdown.Option("LIGHT", "浅色"),
                                            ft.dropdown.Option("DARK", "深色"),
                                            ft.dropdown.Option("SYSTEM", "跟随系统"),
                                        ],
                                        value="LIGHT",
                                        width=150,
                                    ),
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        width=600,
                    ),
                    elevation=2,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "保存设置",
                    icon=ft.Icons.SAVE,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                    ),
                    on_click=lambda e: self._on_save_click(e),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def _on_save_click(self, e):
        """处理保存设置按钮点击事件"""
        # 使用 AlertDialog 显示消息
        dialog = ft.AlertDialog(
            title=ft.Text("提示"),
            content=ft.Text("设置已保存"),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)
