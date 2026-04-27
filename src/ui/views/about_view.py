"""
About View - 关于页面

显示应用程序信息、版本号和版权信息
"""

import flet as ft
from pathlib import Path


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
        return ft.Container(
            content=ft.Column(
                [
                    # 标题
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "关于 ZX 智能答题助手",
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_900,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=10,
                        ),
                        padding=20,
                        margin=ft.margin.only(bottom=20),
                    ),

                    # 版本信息卡片
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.ListTile(
                                        title=ft.Text(f"版本号：{self.version}"),
                                    ),
                                    ft.Divider(),
                                    ft.ListTile(
                                        title=ft.Text(f"构建日期：{self.build_date}"),
                                    ),
                                    ft.Divider(),
                                    ft.ListTile(
                                        title=ft.Text(f"Git 提交：{self.git_commit}"),
                                    ),
                                    ft.Divider(),
                                    ft.ListTile(
                                        title=ft.Text(f"构建模式：{self.build_mode}"),
                                    ),
                                ],
                            ),
                            padding=10,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),

                    # 功能特性
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "插件化架构",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    ft.Text(
                                        "支持动态加载插件，扩展功能模块",
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Divider(height=20),
                                    ft.Text(
                                        "智能答题",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    ft.Text(
                                        "支持浏览器模式和 API 模式两种答题方式",
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Divider(height=20),
                                    ft.Text(
                                        "题库提取",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    ft.Text(
                                        "一键提取课程题库和答案",
                                        color=ft.Colors.GREY_700,
                                    ),
                                ],
                            ),
                            padding=20,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),

                    # 技术栈
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "技术栈",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_900,
                                    ),
                                    ft.Divider(),
                                    ft.Text(
                                        "• Flet - GUI 框架\n"
                                        "• Playwright - 浏览器自动化\n"
                                        "• Requests - HTTP 客户端\n"
                                        "• Python 3.10+",
                                        color=ft.Colors.GREY_700,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                spacing=10,
                            ),
                            padding=20,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),

                    # 链接按钮
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "GitHub 仓库",
                                on_click=lambda _: self._open_url(
                                    "https://github.com/TianJiaJi/ZX-Answering-Assistant-python"
                                ),
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.GREY_800,
                                ),
                            ),
                            ft.ElevatedButton(
                                "检查更新",
                                on_click=lambda _: self._open_url(
                                    "https://github.com/TianJiaJi/ZX-Answering-Assistant-python/releases"
                                ),
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE,
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20,
                    ),

                    # 版权信息
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Divider(),
                                ft.Text(
                                    "Copyright © 2026 TianJiaJi",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Text(
                                    "Licensed under Apache 2.0",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        margin=ft.margin.only(top=30),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=30,
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
