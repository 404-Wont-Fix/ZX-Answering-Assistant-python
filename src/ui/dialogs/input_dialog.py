"""
WeBan 用户输入对话框

用于在 GUI 模式下处理 WeBan 模块的用户输入需求
"""

import flet as ft
import threading
from typing import Optional, List


class WeBanInputDialog:
    """WeBan 输入对话框管理器"""

    def __init__(self, page: ft.Page):
        """
        初始化对话框管理器

        Args:
            page: Flet 页面对象
        """
        self.page = page
        self.input_result = None
        self.dialog_event = threading.Event()

    def show_input_dialog(
        self,
        title: str,
        prompt: str,
        options: Optional[List[str]] = None,
        default_value: str = ""
    ) -> str:
        """
        显示输入对话框

        Args:
            title: 对话框标题
            prompt: 提示信息
            options: 选项列表（如果提供，显示为下拉选择）
            default_value: 默认值

        Returns:
            用户输入的字符串
        """
        self.input_result = None
        self.dialog_event.clear()

        def on_confirm(e):
            self.input_result = input_field.value
            self.dialog_event.set()  # 设置事件，表示输入完成
            self.page.close_dialog()

        def on_cancel(e):
            self.input_result = None
            self.dialog_event.set()  # 设置事件，表示输入完成（但值为 None）
            self.page.close_dialog()

        # 创建输入控件
        if options:
            # 有选项：使用 Dropdown
            dropdown = ft.Dropdown(
                label=prompt,
                options=[ft.dropdown.Option(opt) for opt in options],
                value=options[0] if options else None,
                width=400,
            )

            # 创建确认按钮，因为 Dropdown 不会自动提交
            confirm_button = ft.ElevatedButton("确认", on_click=lambda e: on_confirm(e))

            # 创建对话框
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column(
                        [
                            dropdown,
                            ft.Text(
                                "💡 提示：选择后点击确认按钮",
                                size=12,
                                color=ft.Colors.GREY_600,
                            ),
                        ],
                        tight=True,
                    ),
                    width=500,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("取消", on_click=on_cancel),
                    confirm_button,
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

        else:
            # 无选项：使用 TextField
            input_field = ft.TextField(
                label=prompt,
                value=default_value,
                width=400,
                autofocus=True,
                on_submit=on_confirm,  # 回车确认
            )

            # 创建对话框
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                content=ft.Container(
                    content=ft.Column(
                        [
                            input_field,
                            ft.Text(
                                "💡 提示：按 Enter 键确认",
                                size=12,
                                color=ft.Colors.GREY_600,
                            ),
                        ],
                        tight=True,
                    ),
                    width=500,
                    padding=20,
                ),
                actions=[
                    ft.TextButton("取消", on_click=on_cancel),
                    ft.ElevatedButton("确认", on_click=on_confirm),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

        # 显示对话框
        self.page.show_dialog(dialog)

        # 等待用户输入或取消
        self.dialog_event.wait(timeout=300)  # 5分钟超时

        # 如果超时，关闭对话框
        if not self.dialog_event.is_set():
            try:
                self.page.close_dialog()
            except:
                pass

        return self.input_result if self.input_result is not None else ""

    def show_image_prompt_dialog(
        self,
        title: str,
        image_path: str,
        prompt: str
    ) -> str:
        """
        显示图片提示对话框（用于验证码输入）

        Args:
            title: 对话框标题
            image_path: 图片路径
            prompt: 提示信息

        Returns:
            用户输入的字符串
        """
        self.input_result = None
        self.dialog_event.clear()

        def on_confirm(e):
            self.input_result = input_field.value
            self.dialog_event.set()
            self.page.close_dialog()

        def on_cancel(e):
            self.input_result = None
            self.dialog_event.set()
            self.page.close_dialog()

        # 创建输入控件
        input_field = ft.TextField(
            label=prompt,
            width=400,
            autofocus=True,
            on_submit=on_confirm,
        )

        # 创建对话框
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    [
                        # 显示图片
                        ft.Image(
                            src=image_path,
                            width=300,
                            height=150,
                            fit=ft.ImageFit.CONTAIN,
                            error_content=ft.Text("无法加载验证码图片", color=ft.Colors.RED),
                        ),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        # 输入框
                        input_field,
                        ft.Text(
                            "💡 请查看上方验证码图片并输入",
                            size=12,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    tight=True,
                ),
                width=500,
                padding=20,
            ),
            actions=[
                ft.TextButton("取消", on_click=on_cancel),
                ft.ElevatedButton("确认", on_click=on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # 显示对话框
        self.page.show_dialog(dialog)

        # 等待用户输入
        self.dialog_event.wait(timeout=300)  # 5分钟超时

        # 如果超时，关闭对话框
        if not self.dialog_event.is_set():
            try:
                self.page.close_dialog()
            except:
                pass

        return self.input_result if self.input_result is not None else ""
