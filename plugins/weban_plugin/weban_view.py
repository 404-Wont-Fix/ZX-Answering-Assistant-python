"""
WeBan View - 安全微伴课程自动化

WeBan 模块的 GUI 视图，提供安全微伴课程的自动化学习界面。
采用简洁的三页面设计：简介 → 登录 → 控制台
"""

import flet as ft
import threading
import asyncio
from pathlib import Path
from typing import Optional
import sys

# 导入插件内部的 weban_adapter
weban_adapter_path = Path(__file__).parent / "weban_adapter.py"
spec = __import__('importlib.util').util.spec_from_file_location("weban_adapter", weban_adapter_path)
weban_adapter = __import__('importlib.util').util.module_from_spec(spec)
spec.loader.exec_module(weban_adapter)

# 导入对话框（从主项目）
try:
    from src.ui.dialogs.input_dialog import WeBanInputDialog
    HAS_INPUT_DIALOG = True
except ImportError:
    HAS_INPUT_DIALOG = False
    WeBanInputDialog = None

from src.core.config import get_settings_manager


class WeBanView:
    """WeBan 视图类"""

    def __init__(self, page: ft.Page):
        """
        初始化视图

        Args:
            page: Flet 页面对象
        """
        self.page = page

        # 创建输入对话框（如果可用）
        if HAS_INPUT_DIALOG and WeBanInputDialog:
            self.input_dialog = WeBanInputDialog(page)
        else:
            self.input_dialog = None

        self.adapter = weban_adapter.get_weban_adapter(
            progress_callback=self._log,
            input_callback=self._handle_input  # 传入输入回调
        )

        # 设置管理器
        self.settings_manager = get_settings_manager()

        # UI 控件
        self.current_content = None
        self.school_field = None
        self.account_field = None
        self.password_field = None
        self.remember_checkbox = None  # 记住我复选框

        # 任务状态
        self.is_running = False
        self.task_thread = None

        # 登录信息
        self.school_name = ""
        self.account = ""
        self.password = ""

        # 控制台UI控件
        self.console_dialog = None
        self.log_text = None
        self.start_button = None
        self.stop_button = None
        self.status_text = None

        # 待输入的答案（用于手动作答）
        self.pending_answer = None
        self.answer_input_dialog = None

    def get_content(self) -> ft.Column:
        """
        获取视图内容

        Returns:
            Flet Column 对象
        """
        # 创建主界面内容（简介页面）
        main_content = self._get_intro_content()

        # 使用 AnimatedSwitcher 实现动画切换
        self.current_content = ft.AnimatedSwitcher(
            content=main_content,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )

        return ft.Column(
            [self.current_content],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

    def _get_intro_content(self) -> ft.Column:
        """获取简介页面内容"""
        # 检查 WeBan 是否可用
        weban_available = self.adapter.check_available() if hasattr(self.adapter, 'check_available') else False

        content = [
            ft.Row(
                [
                    ft.Icon(ft.Icons.SECURITY, size=40, color=ft.Colors.BLUE),
                    ft.Text(
                        "安全微伴 (WeBan)",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                ],
                spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
        ]

        # 如果 WeBan 不可用，显示警告
        if not weban_available:
            content.extend([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=40),
                                    title=ft.Text("WeBan 模块未找到", weight=ft.FontWeight.BOLD, size=20),
                                    subtitle=ft.Text(
                                        "插件缺少必要的 WeBan 代码库。\n\n"
                                        "解决方案：\n"
                                        "1. 将 WeBan 项目放在项目根目录的 WeBan/ 文件夹\n"
                                        "2. 或将 WeBan 添加为 Git Submodule 到 plugins/weban_plugin/modules/WeBan/\n"
                                        "3. 重启应用程序让插件自动配置\n\n"
                                        "详细说明请查看：plugins/weban_plugin/WEBAN_SUBMODULE_GUIDE.md",
                                    ),
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        width=700,
                        bgcolor=ft.Colors.RED_50,
                    ),
                    elevation=3,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ])

        # 功能说明卡片
        content.extend([
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.BLUE),
                                title=ft.Text("自动学习", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text("自动完成安全微伴课程的学习任务"),
                            ),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.QUIZ, color=ft.Colors.GREEN),
                                title=ft.Text("智能答题", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text("根据题库自动完成课程考试"),
                            ),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.SYNC, color=ft.Colors.ORANGE),
                                title=ft.Text("题库同步", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text("自动同步最新题库数据"),
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=20,
                    width=600,
                ),
                elevation=2,
            ),
            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),

            # 重要提示
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
                                title=ft.Text("重要提示", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(
                                    "⚠️ 如果题库中没有答案，会弹出窗口让您手动作答！\n"
                                    "⚠️ 部分学校使用腾讯云验证码，可能无法自动完成！"
                                ),
                            ),
                        ],
                    ),
                    padding=15,
                    width=600,
                    bgcolor=ft.Colors.ORANGE_50,
                ),
                elevation=2,
            ),
            ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
        ])

        # 开始按钮（如果 WeBan 可用）
        if weban_available:
            content.append(
                ft.ElevatedButton(
                    "开始使用",
                    icon=ft.Icons.PLAY_ARROW,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                    ),
                    on_click=self._on_start_click,
                    animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                )
            )

        return ft.Column(
            content,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _get_login_content(self) -> ft.Column:
        """获取登录页面内容"""
        # 加载已保存的凭据
        saved_school, saved_account, saved_password = self.settings_manager.get_weban_credentials()

        # 初始化输入框（自动填充已保存的凭据）
        self.school_field = ft.TextField(
            label="学校名称",
            hint_text="请输入完整的学校名称（如：重庆大学）",
            value=saved_school or "",
            width=400,
            prefix_icon=ft.Icons.SCHOOL,
            autofocus=True,
        )

        self.account_field = ft.TextField(
            label="账号",
            hint_text="请输入您的账号",
            value=saved_account or "",
            width=400,
            prefix_icon=ft.Icons.PERSON,
        )

        self.password_field = ft.TextField(
            label="密码",
            hint_text="请输入您的密码",
            value=saved_password or "",
            width=400,
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
        )

        # 创建"记住我"复选框
        self.remember_checkbox = ft.Checkbox(
            label="记住我（自动保存账号和密码）",
            value=bool(saved_school and saved_account and saved_password),  # 如果已保存凭据，默认勾选
            fill_color=ft.Colors.BLUE,
        )

        return ft.Column(
            [
                # 标题栏
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=ft.Colors.BLUE,
                            on_click=self._on_back_click,
                        ),
                        ft.Text(
                            "账号登录",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_800,
                            expand=True,
                        ),
                    ],
                ),

                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),

                # 输入表单
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "请输入您的登录信息",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_800,
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                                self.school_field,
                                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

                                self.account_field,
                                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

                                self.password_field,
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                self.remember_checkbox,
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                                ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            "验证学校",
                                            icon=ft.Icons.CHECK,
                                            on_click=self._on_validate_school,
                                        ),
                                        ft.Container(width=20),
                                        ft.Text(
                                            "💡 建议先验证学校名称是否正确",
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        ),
                                    ],
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=30,
                        width=500,
                    ),
                    elevation=3,
                ),
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),

                # 登录按钮
                ft.ElevatedButton(
                    "登录并开始",
                    icon=ft.Icons.LOGIN,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=40, vertical=15),
                    ),
                    on_click=self._on_login_click,
                    animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _get_console_content(self) -> ft.Column:
        """获取控制台页面内容"""
        # 创建日志显示区域
        self.log_text = ft.TextField(
            value="",
            multiline=True,
            width=700,
            height=350,
            read_only=True,
            bgcolor=ft.Colors.GREY_100,
            border_color=ft.Colors.GREY_300,
            border_radius=8,
        )

        # 创建控制按钮
        self.start_button = ft.ElevatedButton(
            "开始执行",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=30, vertical=12),
            ),
        )

        self.stop_button = ft.ElevatedButton(
            "停止执行",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            disabled=True,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=30, vertical=12),
            ),
        )

        # 绑定按钮事件
        self.start_button.on_click = self._on_console_start
        self.stop_button.on_click = self._on_console_stop

        # 状态文本
        self.status_text = ft.Text(
            "准备就绪",
            color=ft.Colors.GREY_600,
            size=14,
            italic=True,
        )

        return ft.Column(
            [
                # 标题栏
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=ft.Colors.BLUE,
                            on_click=self._on_back_to_login,
                        ),
                        ft.Text(
                            "执行控制台",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_800,
                            expand=True,
                        ),
                        ft.Container(width=20),
                        self.status_text,
                    ],
                ),

                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 控制按钮
                ft.Row(
                    [self.start_button, self.stop_button],
                    spacing=20,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 日志标题
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ARTICLE, color=ft.Colors.BLUE),
                        ft.Text(
                            "执行日志",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_800,
                        ),
                    ],
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                # 日志显示
                self.log_text,
            ],
        )

    def _on_start_click(self, e):
        """开始按钮点击事件 - 切换到登录页面"""
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_click(self, e):
        """返回按钮点击事件 - 返回简介页面"""
        intro_content = self._get_intro_content()
        self.current_content.content = intro_content
        self.page.update()

    def _on_validate_school(self, e):
        """验证学校按钮点击事件"""
        school_name = self.school_field.value.strip()
        if not school_name:
            self._show_snackbar("请输入学校名称", ft.Colors.RED)
            return

        # 显示加载提示
        self._show_snackbar(f"正在验证学校: {school_name}...", ft.Colors.BLUE)

        # 在后台线程验证学校
        def validate_school():
            try:
                result = self.adapter.validate_tenant(school_name)
                if result["success"]:
                    self._show_snackbar(result["message"], ft.Colors.GREEN)
                else:
                    self._show_snackbar(result["message"], ft.Colors.RED)
            except Exception as ex:
                self._show_snackbar(f"验证失败: {str(ex)}", ft.Colors.RED)

        threading.Thread(target=validate_school, daemon=True).start()

    def _on_login_click(self, e):
        """登录按钮点击事件"""
        school_name = self.school_field.value.strip()
        account = self.account_field.value.strip()
        password = self.password_field.value.strip()
        remember = self.remember_checkbox.value

        # 验证输入
        if not all([school_name, account, password]):
            self._show_snackbar("请填写完整的登录信息", ft.Colors.RED)
            return

        # 保存凭据
        if remember:
            self.settings_manager.set_weban_credentials(school_name, account, password)

        # 保存登录信息
        self.school_name = school_name
        self.account = account
        self.password = password

        # 准备配置
        config = [{
            "tenant_name": school_name,
            "account": account,
            "password": password,
            "study": True,
            "study_time": 20,
            "restudy_time": 0,
            "exam": True,
            "exam_use_time": 250,
        }]

        # 加载配置
        if not self.adapter.load_config(config):
            self._show_snackbar("配置加载失败", ft.Colors.RED)
            return

        # 切换到控制台页面
        console_content = self._get_console_content()
        self.current_content.content = console_content
        self.page.update()

        # 显示欢迎消息
        self._log(f"欢迎使用安全微伴！学校: {school_name}", "success")
        self._log(f"配置已加载，点击'开始执行'按钮开始任务", "info")

    def _on_back_to_login(self, e):
        """返回登录页面"""
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_console_start(self, e):
        """控制台开始按钮点击事件"""
        if self.is_running:
            return

        self.is_running = True
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.status_text.value = "正在执行..."
        self.status_text.color = ft.Colors.BLUE
        self.log_text.value = ""
        self.page.update()

        # 在后台线程执行任务
        def run_task():
            try:
                self._log(f"开始执行任务: {self.school_name}", "info")
                self._log(f"账号: {self.account}", "info")
                self._log("-" * 50, "info")

                result = self.adapter.start(use_multithread=False)

                self._log("-" * 50, "info")
                self._log(f"执行完成！成功: {result['success']}, 失败: {result['failed']}", "success")

            except Exception as ex:
                self._log(f"执行失败: {str(ex)}", "error")
                import traceback
                self._log(f"错误详情: {traceback.format_exc()}", "error")
            finally:
                self.is_running = False
                self.start_button.disabled = False
                self.stop_button.disabled = True
                self.status_text.value = "执行完成"
                self.status_text.color = ft.Colors.GREEN
                self.page.update()

        self.task_thread = threading.Thread(target=run_task, daemon=True)
        self.task_thread.start()

    def _on_console_stop(self, e):
        """控制台停止按钮点击事件"""
        if not self.is_running:
            return

        self._log("正在停止任务...", "warning")
        self.adapter.stop()

    def _log(self, message: str, level: str = "info"):
        """日志输出函数"""
        # 如果 log_text 还未初始化，输出到控制台
        if not hasattr(self, 'log_text') or self.log_text is None:
            print(f"[WeBan] {message}")
            return

        # 添加时间戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 根据日志级别设置颜色和图标
        color_map = {
            "info": ft.Colors.BLACK,
            "success": ft.Colors.GREEN,
            "warning": ft.Colors.ORANGE,
            "error": ft.Colors.RED,
        }
        prefix_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }

        prefix = prefix_map.get(level, "ℹ️")

        # 添加日志
        self.log_text.value += f"[{timestamp}] {prefix} {message}\n"
        self.page.update()

    def _show_snackbar(self, message: str, bgcolor: ft.Color = None):
        """
        显示 SnackBar 提示（Flet 0.8.0+ 兼容）

        Args:
            message: 提示消息
            bgcolor: 背景颜色
        """
        try:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=bgcolor,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as e:
            # 如果 SnackBar 失败，输出到控制台
            print(f"[SnackBar] {message}")
            print(f"[SnackBar Error] {e}")

    def _handle_input(self, prompt: str) -> str:
        """处理用户输入（用于验证码、手动作答等）"""
        # 创建一个事件来等待输入
        import threading
        input_event = threading.Event()
        input_result = [""]

        def show_input_dialog():
            """显示输入对话框"""
            # 创建对话框
            dialog = ft.AlertDialog(
                title=ft.Text("需要输入"),
                content=ft.Column(
                    [ft.Text(prompt)],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                    width=500,
                ),
                actions=[],
            )

            # 创建输入框
            input_field = ft.TextField(
                label="请输入",
                hint_text="请输入答案或验证码",
                width=400,
                autofocus=True,
            )

            # 更新对话框内容
            dialog.content = ft.Column(
                [
                    ft.Text(prompt),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    input_field,
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                width=500,
            )

            def on_confirm(e):
                input_result[0] = input_field.value
                dialog.open = False
                input_event.set()
                self.page.update()

            def on_cancel(e):
                input_result[0] = ""
                dialog.open = False
                input_event.set()
                self.page.update()

            # 添加按钮
            dialog.actions = [
                ft.TextButton("取消", on_click=on_cancel),
                ft.TextButton("确定", on_click=on_confirm),
            ]

            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

        # 在主线程中显示对话框
        self.page.run_thread(show_input_dialog)

        # 等待用户输入
        input_event.wait()
        return input_result[0]
