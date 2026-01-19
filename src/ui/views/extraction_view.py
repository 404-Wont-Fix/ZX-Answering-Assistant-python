"""
ZX Answering Assistant - 答案提取视图模块

This module contains the UI components for the answer extraction page.
"""

import flet as ft


class ExtractionView:
    """答案提取页面视图"""

    def __init__(self, page: ft.Page):
        """
        初始化答案提取视图

        Args:
            page (ft.Page): Flet页面对象
        """
        self.page = page

    def get_content(self) -> ft.Column:
        """
        获取答案提取页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        return ft.Column(
            [
                ft.Text(
                    "答案提取",
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
                                    leading=ft.Icon(ft.Icons.PERSON, color=ft.Colors.PURPLE),
                                    title=ft.Text("教师端登录", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用教师账号登录管理平台"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.GROUPS, color=ft.Colors.RED),
                                    title=ft.Text("选择班级", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("选择要提取答案的班级"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.DOWNLOAD, color=ft.Colors.CYAN),
                                    title=ft.Text("提取答案", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("从课程中提取题目和答案"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.SAVE, color=ft.Colors.AMBER),
                                    title=ft.Text("导出数据", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("将提取的答案导出为JSON文件"),
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
                    "提取答案",
                    icon=ft.Icons.DOWNLOAD,
                    bgcolor=ft.Colors.PURPLE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                    ),
                    on_click=lambda e: self._on_extract_click(e),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def _on_extract_click(self, e):
        """处理提取答案按钮点击事件"""
        self.page.show_snack_bar(
            ft.SnackBar(ft.Text("功能开发中..."))
        )
