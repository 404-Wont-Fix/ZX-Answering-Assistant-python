"""
ZX Answering Assistant - 评估出题视图模块

This module contains the UI components for the evaluation page.
"""

import flet as ft


class EvaluationView:
    """评估出题页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化评估出题视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app

    def get_content(self) -> ft.Column:
        """
        获取评估出题页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        return ft.Column(
            [
                ft.Text(
                    "评估出题",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                    animate_opacity=200,
                ),
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.QUIZ,
                                    size=120,
                                    color=ft.Colors.BLUE_300,
                                ),
                                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "敬请期待",
                                    size=36,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700,
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "评估出题功能正在开发中",
                                    size=18,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "敬请期待后续版本更新",
                                    size=16,
                                    color=ft.Colors.GREY_500,
                                    style=ft.TextStyle(italic=True),
                                ),
                                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.BUILD, color=ft.Colors.ORANGE, size=20),
                                        ft.Text(
                                            "功能开发中...",
                                            size=14,
                                            color=ft.Colors.ORANGE_700,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        ),
                        padding=50,
                        width=700,
                    ),
                    elevation=3,
                ),
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE),
                                    title=ft.Text(
                                        "即将推出",
                                        weight=ft.FontWeight.BOLD,
                                        size=18,
                                    ),
                                    subtitle=ft.Text(
                                        "评估出题模块将为用户提供智能题目生成和评估管理功能"
                                    ),
                                ),
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.STARS, color=ft.Colors.AMBER),
                                    title=ft.Text(
                                        "新功能预览",
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    subtitle=ft.Column(
                                        [
                                            ft.Text("• 智能题目生成", size=14),
                                            ft.Text("• 题库管理", size=14),
                                            ft.Text("• 难度评估", size=14),
                                            ft.Text("• 试卷导出", size=14),
                                        ],
                                        spacing=5,
                                    ),
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=20,
                        width=700,
                    ),
                    elevation=2,
                    bgcolor=ft.Colors.BLUE_50,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
