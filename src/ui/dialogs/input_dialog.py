"""
WeBan 用户输入对话框

用于在 GUI 模式下处理 WeBan 模块的用户输入需求
"""

import flet as ft
import threading
from typing import Optional, List

# 尝试导入 pyperclip，如果不可用则禁用复制按钮
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    pyperclip = None


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
        dialog = None  # 初始化对话框变量

        def on_confirm(e):
            if options:
                self.input_result = dropdown.value
            else:
                self.input_result = input_field.value
            self.dialog_event.set()  # 设置事件，表示输入完成
            dialog.open = False
            self.page.update()

        def on_cancel(e):
            self.input_result = None
            self.dialog_event.set()  # 设置事件，表示输入完成（但值为 None）
            dialog.open = False
            self.page.update()

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
            # 判断是否为手动答题（包含"题目"、"答案序号"等关键词）
            is_manual_answer = any(keyword in prompt for keyword in ["题目", "答案序号", "题目标题", "题目类型"])

            if is_manual_answer:
                # 手动答题：显示可复制的题目文本框 + 答案输入框
                # 题目显示区域（只读，可复制）
                question_text_field = ft.TextField(
                    label="题目信息（可选择复制）",
                    value=prompt,
                    multiline=True,
                    max_lines=15,
                    width=500,
                    read_only=True,  # 只读，但可以选择和复制
                    text_style=ft.TextStyle(size=12),
                )

                # 答案输入框
                input_field = ft.TextField(
                    label="请输入答案序号",
                    hint_text="多个选项用英文逗号分隔，如：1,2,3,4",
                    value=default_value,
                    width=500,
                    autofocus=True,
                    on_submit=on_confirm,  # 回车确认
                )

                # 创建对话框内容
                dialog_content = [
                    question_text_field,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ]

                # 如果 pyperclip 可用，添加复制按钮
                if PYPERCLIP_AVAILABLE:
                    def copy_question(e):
                        pyperclip.copy(prompt)
                        self.page.snack_bar = ft.SnackBar(
                            content=ft.Text("✓ 题目已复制到剪贴板"),
                            duration=2000,
                        )
                        self.page.snack_bar.open = True
                        self.page.update()

                    copy_button = ft.ElevatedButton(
                        "📋 复制题目",
                        icon=ft.Icons.COPY,
                        bgcolor=ft.Colors.BLUE_100,
                        color=ft.Colors.BLUE_800,
                        on_click=copy_question,
                    )
                    dialog_content.append(
                        ft.Row(
                            [copy_button],
                            alignment=ft.MainAxisAlignment.END,
                        )
                    )
                    dialog_content.append(ft.Divider(height=10, color=ft.Colors.TRANSPARENT))

                # 继续添加答案输入框和提示
                dialog_content.extend([
                    input_field,
                    ft.Text(
                        f"💡 提示：上方文本框可选择{'或点击按钮一键' if PYPERCLIP_AVAILABLE else ''}复制，按 Enter 键确认",
                        size=12,
                        color=ft.Colors.GREY_600,
                    ),
                ])

                # 创建对话框
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                    content=ft.Container(
                        content=ft.Column(
                            dialog_content,
                            tight=True,
                        ),
                        width=550,
                        padding=20,
                    ),
                    actions=[
                        ft.TextButton("取消", on_click=on_cancel),
                        ft.ElevatedButton("确认", on_click=on_confirm),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
            else:
                # 普通输入：使用原来的方式
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

        # 显示对话框 - 使用 run_task 在主线程中执行
        async def show_dialog_async():
            self.page.show_dialog(dialog)

        try:
            # 检查是否在主线程
            import threading
            current_thread = threading.current_thread()
            main_thread = threading.main_thread()

            print(f"[WeBan Input] 当前线程: {current_thread.name}, 主线程: {main_thread.name}")

            if current_thread is main_thread:
                # 在主线程中，直接显示对话框
                print("[WeBan Input] 在主线程中显示对话框")
                self.page.show_dialog(dialog)
            else:
                # 在后台线程中，使用 run_task
                print("[WeBan Input] 在后台线程中，使用 run_task 显示对话框")
                self.page.run_task(show_dialog_async)

        except Exception as ex:
            print(f"[WeBan Input] ❌ 显示对话框失败: {ex}")
            import traceback
            traceback.print_exc()
            # 返回空字符串，而不是阻塞
            return ""

        # 等待用户输入或取消
        self.dialog_event.wait(timeout=300)  # 5分钟超时

        # 如果超时，关闭对话框
        if not self.dialog_event.is_set():
            try:
                if dialog:
                    dialog.open = False
                    self.page.update()
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

        注意：WeBan模块已经使用系统默认程序打开了图片
         这个对话框只用于收集用户输入

        Args:
            title: 对话框标题
            image_path: 图片路径（已由WeBan打开，此参数保留用于提示信息）
            prompt: 提示信息

        Returns:
            用户输入的字符串
        """
        self.input_result = None
        self.dialog_event.clear()

        # 提取图片文件名用于提示
        import os
        image_filename = os.path.basename(image_path) if image_path else "验证码图片"

        def on_confirm(e):
            self.input_result = input_field.value
            self.dialog_event.set()
            dialog.open = False
            self.page.update()

        def on_cancel(e):
            self.input_result = None
            self.dialog_event.set()
            dialog.open = False
            self.page.update()

        # 创建输入控件
        input_field = ft.TextField(
            label=prompt,
            width=400,
            autofocus=True,
            on_submit=on_confirm,
        )

        # 创建对话框（简化版，假设图片已被WeBan打开）
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"📸 WeBan 已打开验证码图片 ({image_filename})",
                            size=14,
                            color=ft.Colors.BLUE,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                        # 输入框
                        input_field,
                        ft.Text(
                            "💡 请查看已打开的图片窗口，然后在此输入验证码",
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

        # 显示对话框 - 使用 run_task 在主线程中执行
        async def show_dialog_async():
            self.page.show_dialog(dialog)

        try:
            # 检查是否在主线程
            import threading
            current_thread = threading.current_thread()
            main_thread = threading.main_thread()

            print(f"[WeBan Input] 当前线程: {current_thread.name}, 主线程: {main_thread.name}")

            if current_thread is main_thread:
                # 在主线程中，直接显示对话框
                print("[WeBan Input] 在主线程中显示对话框")
                self.page.show_dialog(dialog)
            else:
                # 在后台线程中，使用 run_task
                print("[WeBan Input] 在后台线程中，使用 run_task 显示对话框")
                self.page.run_task(show_dialog_async)

        except Exception as ex:
            print(f"[WeBan Input] ❌ 显示对话框失败: {ex}")
            import traceback
            traceback.print_exc()
            return ""

        # 等待用户输入
        self.dialog_event.wait(timeout=300)  # 5分钟超时

        # 如果超时，关闭对话框
        if not self.dialog_event.is_set():
            try:
                if dialog:
                    dialog.open = False
                    self.page.update()
            except:
                pass

        return self.input_result if self.input_result is not None else ""
