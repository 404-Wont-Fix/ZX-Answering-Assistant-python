"""
ZX Answering Assistant - 云考试视图模块

This module contains the UI components for the cloud exam page.
"""

import flet as ft


class CloudExamView:
    """云考试页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化云考试视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app

    def get_content(self) -> ft.Column:
        """
        获取云考试页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        return ft.Column(
            [
                ft.Text(
                    "云考试",
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
                                    ft.Icons.CLOUD_QUEUE,
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
                                    "云考试功能正在开发中",
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
                                        "云考试模块将为用户提供在线考试支持和自动化答题功能"
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
                                            ft.Text("• 支持在线考试模式", size=14),
                                            ft.Text("• 实时答题进度追踪", size=14),
                                            ft.Text("• 智能答案匹配", size=14),
                                            ft.Text("• 考试结果分析", size=14),
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
