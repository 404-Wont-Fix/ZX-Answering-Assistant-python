"""
About View - 关于页面

显示应用程序信息、版本号和版权信息
"""

import flet as ft
from pathlib import Path
from src.ui.components import page_heading, primary_button, secondary_button, status_chip, surface_card
from src.ui.theme import Palette, Radius


class AboutView:
    """关于页面视图"""

    def __init__(self, page):
        """
        初始化关于页面

        Args:
            page: Flet 页面对象
        """
        self.page = page

        # 动态导入 version 模块（支持打包环境）
        try:
            import version
            self.version = version.VERSION
            self.version_name = version.VERSION_NAME
            self.build_date = version.BUILD_DATE
            self.git_commit = version.GIT_COMMIT
            self.build_mode = version.BUILD_MODE
        except ImportError:
            self.version = "Unknown"
            self.version_name = "ZX Answering Assistant"
            self.build_date = ""
            self.git_commit = ""
            self.build_mode = ""

    def get_content(self):
        """
        获取关于页面的内容

        Returns:
            Flet 控件
        """
        def info_row(label: str, value: str) -> ft.Row:
            return ft.Row(
                [
                    ft.Text(label, size=12, color=Palette.TEXT_MUTED),
                    ft.Container(expand=True),
                    ft.Text(value or "-", size=13, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                ],
            )

        def feature(icon, title: str, description: str) -> ft.Row:
            return ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=20, color=Palette.PRIMARY),
                        width=40,
                        height=40,
                        bgcolor=Palette.PRIMARY_SOFT,
                        border_radius=Radius.SMALL,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        [
                            ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                            ft.Text(description, size=12, color=Palette.TEXT_MUTED),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=12,
            )

        return ft.Column(
            [
                page_heading(
                    "关于 ZX 智能答题助手",
                    "应用版本、能力概览与项目入口",
                    ft.Icons.INFO_OUTLINE,
                ),
                surface_card(
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.SCHOOL, size=38, color=Palette.SURFACE),
                                width=76,
                                height=76,
                                bgcolor=Palette.PRIMARY,
                                border_radius=Radius.CARD,
                                alignment=ft.Alignment(0, 0),
                            ),
                            ft.Column(
                                [
                                    ft.Text(self.version_name, size=23, weight=ft.FontWeight.BOLD, color=Palette.TEXT),
                                    ft.Text("Intelligent Answering Assistant System", size=13, color=Palette.TEXT_MUTED),
                                ],
                                spacing=5,
                                expand=True,
                            ),
                            status_chip(f"v{self.version}"),
                        ],
                        spacing=18,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=24,
                ),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            content=surface_card(
                                ft.Column(
                                    [
                                        ft.Text("版本信息", size=17, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                                        ft.Divider(height=16, color=Palette.BORDER),
                                        info_row("版本号", self.version),
                                        info_row("构建日期", self.build_date),
                                        info_row("Git 提交", self.git_commit),
                                        info_row("构建模式", self.build_mode),
                                    ],
                                    spacing=13,
                                ),
                            ),
                            col={"xs": 12, "md": 5},
                        ),
                        ft.Container(
                            content=surface_card(
                                ft.Column(
                                    [
                                        ft.Text("核心能力", size=17, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                                        feature(ft.Icons.EXTENSION_OUTLINED, "插件化架构", "动态加载功能扩展模块"),
                                        feature(ft.Icons.CHECK_CIRCLE_OUTLINE, "智能答题", "支持浏览器和 API 执行模式"),
                                        feature(ft.Icons.DOWNLOAD_OUTLINED, "题库提取", "生成可复用的课程题库文件"),
                                    ],
                                    spacing=15,
                                ),
                            ),
                            col={"xs": 12, "md": 7},
                        ),
                    ],
                    spacing=14,
                    run_spacing=14,
                ),
                ft.Row(
                    [
                        secondary_button(
                            "GitHub 仓库",
                            ft.Icons.CODE,
                            lambda _: self._open_url(
                                "https://github.com/TianJiaJi/ZX-Answering-Assistant-python"
                            ),
                        ),
                        primary_button(
                            "检查更新",
                            ft.Icons.UPDATE,
                            lambda _: self._open_url(
                                "https://github.com/TianJiaJi/ZX-Answering-Assistant-python/releases"
                            ),
                        ),
                    ],
                    spacing=12,
                ),
                ft.Text(
                    "Copyright (c) 2026 TianJiaJi  |  Licensed under Apache 2.0",
                    size=12,
                    color=Palette.TEXT_MUTED,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=22,
            expand=True,
        )

    def _open_url(self, url: str):
        """打开 URL"""
        try:
            import subprocess
            import sys
            # 使用系统默认浏览器打开 URL
            if sys.platform == 'win32':
                subprocess.run(['start', '', url], shell=True)
            elif sys.platform == 'darwin':
                subprocess.run(['open', url])
            else:
                subprocess.run(['xdg-open', url])
        except Exception as e:
            print(f"打开链接失败: {e}")
