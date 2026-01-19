"""
ZX Answering Assistant - 评估答题视图模块

This module contains the UI components for the answering page.
"""

import flet as ft


class AnsweringView:
    """评估答题页面视图"""

    def __init__(self, page: ft.Page):
        """
        初始化评估答题视图

        Args:
            page (ft.Page): Flet页面对象
        """
        self.page = page

    def get_content(self) -> ft.Column:
        """
        获取评估答题页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        return ft.Column(
            [
                ft.Text(
                    "评估答题",
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
                                    leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.BLUE),
                                    title=ft.Text("学生端登录", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("登录学生端平台获取access_token"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.GREEN),
                                    title=ft.Text("选择课程", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("查看课程列表和完成情况"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.ORANGE),
                                    title=ft.Text("开始答题", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用题库自动完成课程答题"),
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
                    "开始答题",
                    icon=ft.Icons.PLAY_ARROW,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                    ),
                    on_click=lambda e: self._on_start_answer_click(e),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def _on_start_answer_click(self, e):
        """处理开始答题按钮点击事件"""
        self.page.show_snack_bar(
            ft.SnackBar(ft.Text("功能开发中..."))
        )
