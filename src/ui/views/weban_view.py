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

from src.modules.weban_adapter import get_weban_adapter
from src.ui.dialogs.input_dialog import WeBanInputDialog
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
        self.input_dialog = WeBanInputDialog(page)  # 创建输入对话框实例
        self.adapter = get_weban_adapter(
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
        return ft.Column(
            [
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

                # 功能说明卡片
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

                # 开始按钮
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
                ),
            ],
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
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
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
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _create_console_dialog(self) -> ft.AlertDialog:
        """创建控制台对话框"""
        # 日志显示区域
        self.log_text = ft.Column(
            [],
            scroll=ft.ScrollMode.AUTO,
            height=400,
            spacing=5,
        )

        # 状态文本
        self.status_text = ft.Text(
            "就绪",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREY_700,
        )

        # 开始按钮
        self.start_button = ft.ElevatedButton(
            "开始执行",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            on_click=self._on_start_task,
            disabled=False,
        )

        # 测试输入按钮
        self.test_input_button = ft.ElevatedButton(
            "测试输入",
            icon=ft.Icons.HELP_OUTLINE,  # 使用存在的图标
            bgcolor=ft.Colors.PURPLE,
            color=ft.Colors.WHITE,
            on_click=self._on_test_input,
            disabled=False,
        )

        # 停止按钮
        self.stop_button = ft.ElevatedButton(
            "停止执行",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            on_click=self._on_stop_task,
            disabled=True,
        )

        # 返回按钮
        back_button = ft.ElevatedButton(
            "返回",
            icon=ft.Icons.ARROW_BACK,
            on_click=self._on_close_console,
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SECURITY, color=ft.Colors.BLUE, size=30),
                    ft.Text(
                        f"WeBan 控制台 - {self.school_name}",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        # 状态栏
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE),
                                    ft.Text("状态：", weight=ft.FontWeight.BOLD),
                                    self.status_text,
                                ],
                            ),
                            padding=10,
                            bgcolor=ft.Colors.BLUE_50,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                        # 日志区域
                        ft.Container(
                            content=self.log_text,
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                        ),

                        # 提示信息
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            "💡 所有交互（验证码、手动答题）将通过弹窗完成",
                            size=11,
                            color=ft.Colors.BLUE,
                        ),
                        ft.Text(
                            "⚠️ OCR 验证码识别已启用，失败 3 次后需要手动输入",
                            size=11,
                            color=ft.Colors.ORANGE,
                        ),
                    ],
                    spacing=0,
                ),
                width=700,
            ),
            # 将按钮放在 actions 中，而不是 content 中
            actions=[
                self.start_button,
                self.stop_button,
                self.test_input_button,  # 测试输入按钮
                back_button,
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        return dialog

    # ========== 事件处理 ==========

    def _on_start_click(self, e):
        """处理简介页面的开始按钮点击"""
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_click(self, e):
        """处理返回按钮点击"""
        intro_content = self._get_intro_content()
        self.current_content.content = intro_content
        self.page.update()

    async def _on_validate_school(self, e):
        """验证学校名称"""
        school = self.school_field.value.strip()
        if not school:
            self._show_snackbar("请输入学校名称", ft.Colors.RED)
            return

        self._show_snackbar("正在验证学校...", ft.Colors.BLUE)

        # 在后台线程中运行验证（避免阻塞UI）
        def do_validate():
            return self.adapter.validate_tenant(school)

        # 使用 asyncio 在线程池中执行验证
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, do_validate)

        # 显示结果（现在已经在主事件循环中）
        if result["success"]:
            self._show_snackbar(f"✓ {result['message']}", ft.Colors.GREEN)
        else:
            self._show_snackbar(f"✗ {result['message']}", ft.Colors.RED)

    def _on_login_click(self, e):
        """处理登录按钮点击"""
        print("[DEBUG] _on_login_click 被调用")  # 调试信息

        # 获取输入
        self.school_name = self.school_field.value.strip()
        self.account = self.account_field.value.strip()
        self.password = self.password_field.value.strip()

        print(f"[DEBUG] 学校: {self.school_name}, 账号: {self.account}")  # 调试信息

        # 验证输入
        if not self.school_name:
            self._show_snackbar("请输入学校名称", ft.Colors.RED)
            return

        if not self.account:
            self._show_snackbar("请输入账号", ft.Colors.RED)
            return

        if not self.password:
            self._show_snackbar("请输入密码", ft.Colors.RED)
            return

        # 保存凭据（如果勾选了"记住我"）
        if self.remember_checkbox.value:
            self.settings_manager.set_weban_credentials(
                self.school_name,
                self.account,
                self.password
            )
            print("[WeBan] 凭据已保存")
        else:
            # 如果取消勾选，清除已保存的凭据
            self.settings_manager.clear_weban_credentials()
            print("[WeBan] 凭据已清除")

        # 打开控制台
        try:
            print("[DEBUG] 正在创建控制台对话框...")  # 调试信息
            self.console_dialog = self._create_console_dialog()
            print("[DEBUG] 对话框创建完成")  # 调试信息

            self.page.show_dialog(self.console_dialog)
            print("[DEBUG] 对话框已打开")  # 调试信息

            # 记录登录信息
            self._log(f"学校：{self.school_name}", "info")
            self._log(f"账号：{self.account}", "info")
            self._log("准备就绪，请点击「开始执行」按钮开始任务", "success")
        except Exception as ex:
            print(f"[ERROR] 打开控制台失败: {ex}")  # 错误信息
            import traceback
            traceback.print_exc()

    def _on_start_task(self, e):
        """开始执行任务"""
        print(f"[DEBUG] _on_start_task 被调用")  # 调试信息

        if not self.adapter.check_available():
            self._log("❌ WeBan 模块依赖未安装，请运行：pip install -r requirements.txt", "error")
            return

        # 更新UI状态
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.status_text.value = "正在执行..."
        self.status_text.color = ft.Colors.BLUE
        # 更新对话框内的控件
        self.start_button.update()
        self.stop_button.update()
        self.status_text.update()

        # 构建配置
        config = {
            "tenant_name": self.school_name,
            "account": self.account,
            "password": self.password,
            "user": {"userId": "", "token": ""},
            "study": True,
            "study_time": 20,
            "restudy_time": 0,
            "exam": True,
            "exam_use_time": 250,
        }

        self._log("🚀 开始执行 WeBan 任务...", "info")
        self._log("💡 所有交互（验证码、答题）将通过弹窗完成", "info")

        # 在后台线程中执行
        def run_task():
            try:
                self.is_running = True
                self.adapter.load_config([config])
                result = self.adapter.start(use_multithread=False)

                # 更新结果
                if result["failed"] == 0:
                    self._log(f"✅ 任务完成！成功: {result['success']}", "success")
                    self.status_text.value = "执行完成"
                    self.status_text.color = ft.Colors.GREEN
                else:
                    self._log(f"⚠️ 任务完成！成功: {result['success']}, 失败: {result['failed']}", "warning")
                    self.status_text.value = "部分失败"
                    self.status_text.color = ft.Colors.ORANGE

            except Exception as e:
                self._log(f"❌ 执行出错: {str(e)}", "error")
                self.status_text.value = "执行出错"
                self.status_text.color = ft.Colors.RED

            finally:
                self.is_running = False
                self.start_button.disabled = False
                self.stop_button.disabled = True
                # 更新对话框内的控件
                self.start_button.update()
                self.stop_button.update()
                self.status_text.update()

        self.task_thread = threading.Thread(target=run_task, daemon=True)
        self.task_thread.start()

    def _on_stop_task(self, e):
        """停止执行任务"""
        print(f"[DEBUG] _on_stop_task 被调用")  # 调试信息

        if not self.is_running:
            self._log("⚠️ 任务未在运行", "warning")
            return

        self._log("⚠️ 正在发送停止信号...", "warning")

        # 先尝试优雅停止
        self.adapter.stop()
        self.status_text.value = "正在停止..."
        self.status_text.color = ft.Colors.ORANGE
        self.status_text.update()

        # 等待一小段时间
        import time
        stopped = False
        for i in range(6):  # 最多等待3秒
            if not self.is_running:
                stopped = True
                break
            time.sleep(0.5)

        if stopped:
            self._log("✅ 任务已停止", "success")
            self.status_text.value = "已停止"
            self.status_text.color = ft.Colors.GREY
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.start_button.update()
            self.stop_button.update()
            return

        # 如果优雅停止失败，强制停止
        self._log("⚠️ 优雅停止失败，正在强行停止...", "warning")
        self._log("💡 这可能会丢失部分进度", "info")

        # 强制停止 adapter
        if hasattr(self.adapter, 'force_stop'):
            self.adapter.force_stop()

        # 设置停止标志
        self.adapter._stop_event.set()
        self.adapter.is_running = False

        # 等待线程结束
        if self.task_thread and self.task_thread.is_alive():
            self._log("⚠️ 正在等待后台线程结束...", "warning")
            # 给线程 2 秒时间来优雅退出
            self.task_thread.join(timeout=2)

            # 如果线程还在运行，这就是 daemon 线程，会在主线程退出时自动清理
            if self.task_thread.is_alive():
                self._log("⚠️ 后台线程仍在运行，将在程序关闭时自动清理", "warning")
            else:
                self._log("✅ 后台线程已结束", "success")

        self.is_running = False
        self._log("✅ 已发送强行停止信号", "success")
        self.status_text.value = "已强行停止"
        self.status_text.color = ft.Colors.RED
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.start_button.update()
        self.stop_button.update()

    def _on_close_console(self, e):
        """关闭控制台"""
        print(f"[DEBUG] _on_close_console 被调用")  # 调试信息
        if self.is_running:
            self._show_snackbar("任务正在执行中，请先停止任务", ft.Colors.ORANGE)
            return

        if self.console_dialog:
            self.console_dialog.open = False
            self.page.update()

    def _on_test_input(self, e):
        """测试输入对话框"""
        print(f"[DEBUG] _on_test_input 被调用")  # 调试信息

        # 测试不同类型的输入
        import threading
        from pathlib import Path
        import webbrowser

        def test_in_background():
            self._log("🧪 开始测试输入对话框...", "info")

            # 测试 1: 验证码输入
            self._log("测试 1/3: 验证码输入对话框", "info")

            # 创建测试用的验证码图片
            test_image_filename = "verify_code_123456.png"
            test_image_path = Path.cwd() / test_image_filename

            try:
                # 优先尝试使用真实的 WeBan API 获取验证码
                try:
                    # 导入 WeBan API
                    from src.modules.weban_adapter import WEBAN_AVAILABLE, WeBanAPI

                    if WEBAN_AVAILABLE and self.school_name and self.account:
                        # 使用配置的学校和账号信息创建 API 实例
                        api = WeBanAPI(self.school_name)

                        # 获取时间戳
                        verify_time = api.get_timestamp(13, 0)

                        # 从服务器获取真实验证码图片
                        verify_image = api.rand_letter_image(verify_time)

                        # 保存验证码图片
                        test_image_path.write_bytes(verify_image)

                        self._log(f"✓ 已从 WeBan 服务器获取真实验证码: {test_image_filename}", "success")
                        self._log(f"💡 学校: {self.school_name}, 账号: {self.account}", "info")
                        self._log("💡 这是真实的验证码图片，请手动识别并输入", "info")

                    else:
                        # 未配置 WeBan 账号，使用本地生成的测试图片
                        self._log("⚠️ 未配置 WeBan 账号，使用本地测试图片", "warning")
                        self._log("💡 提示：配置 WeBan 账号后可获取真实验证码", "info")

                        # 使用 Pillow 创建本地测试图片
                        from PIL import Image, ImageDraw, ImageFont
                        import random

                        # 创建验证码图片（150x50像素）
                        width, height = 150, 50
                        image = Image.new('RGB', (width, height), color=(255, 255, 255))
                        draw = ImageDraw.Draw(image)

                        # 添加背景噪点
                        for _ in range(100):
                            x = random.randint(0, width)
                            y = random.randint(0, height)
                            draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))

                        # 生成4位测试验证码
                        test_code = "A7B2"

                        # 绘制验证码文字
                        try:
                            font = ImageFont.truetype("arial.ttf", 32)
                        except:
                            font = ImageFont.load_default()

                        # 绘制每个字符
                        for i, char in enumerate(test_code):
                            x_offset = 20 + i * 30
                            y_offset = random.randint(5, 15)
                            color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
                            draw.text((x_offset, y_offset), char, fill=color, font=font)

                        # 添加干扰线
                        for _ in range(5):
                            x1 = random.randint(0, width)
                            y1 = random.randint(0, height)
                            x2 = random.randint(0, width)
                            y2 = random.randint(0, height)
                            draw.line([(x1, y1), (x2, y2)], fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), width=1)

                        # 保存图片
                        image.save(test_image_path, 'PNG')
                        self._log(f"✓ 本地测试图片已创建: {test_image_filename} (测试验证码: {test_code})", "success")

                except Exception as e:
                    # 获取真实验证码失败，回退到本地生成
                    self._log(f"⚠️ 获取真实验证码失败 ({e})，使用本地测试图片", "warning")

                    # 使用 Pillow 创建本地测试图片
                    try:
                        from PIL import Image, ImageDraw, ImageFont
                        import random

                        # 创建验证码图片（150x50像素）
                        width, height = 150, 50
                        image = Image.new('RGB', (width, height), color=(255, 255, 255))
                        draw = ImageDraw.Draw(image)

                        # 添加背景噪点
                        for _ in range(100):
                            x = random.randint(0, width)
                            y = random.randint(0, height)
                            draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))

                        # 生成4位测试验证码
                        test_code = "A7B2"

                        # 绘制验证码文字
                        try:
                            font = ImageFont.truetype("arial.ttf", 32)
                        except:
                            font = ImageFont.load_default()

                        # 绘制每个字符
                        for i, char in enumerate(test_code):
                            x_offset = 20 + i * 30
                            y_offset = random.randint(5, 15)
                            color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
                            draw.text((x_offset, y_offset), char, fill=color, font=font)

                        # 添加干扰线
                        for _ in range(5):
                            x1 = random.randint(0, width)
                            y1 = random.randint(0, height)
                            x2 = random.randint(0, width)
                            y2 = random.randint(0, height)
                            draw.line([(x1, y1), (x2, y2)], fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), width=1)

                        # 保存图片
                        image.save(test_image_path, 'PNG')
                        self._log(f"✓ 本地测试图片已创建: {test_image_filename} (测试验证码: {test_code})", "success")

                    except ImportError:
                        # Pillow 不可用，使用最小 PNG
                        minimal_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
                        test_image_path.write_bytes(minimal_png)
                        self._log(f"✓ 简单测试图片已创建: {test_image_filename}", "success")

                # 打开测试图片（模拟 WeBan 行为）
                webbrowser.open(f"file://{test_image_path.absolute()}")
                self._log("💡 测试图片已在系统默认程序中打开", "info")
            except Exception as e:
                self._log(f"⚠️ 创建测试图片失败: {e}", "warning")

            result1 = self._handle_input("请查看 verify_code_123456.png 输入验证码：")
            if result1:
                self._log(f"✓ 验证码输入测试成功: {result1}", "success")
            else:
                self._log("✗ 验证码输入测试取消", "warning")

            import time
            time.sleep(1)

            # 测试 2: 重考选择
            self._log("测试 2/3: 重考选择对话框", "info")
            result2 = self._handle_input("考试项目 XXX 最高成绩 80 分。已考试次数 1 次，还剩 2 次。需要重考吗(y/N)？")
            if result2:
                self._log(f"✓ 重考选择测试成功: {result2}", "success")
            else:
                self._log("✗ 重考选择测试取消", "warning")

            time.sleep(1)

            # 测试 3: 手动答题
            self._log("测试 3/3: 手动答题对话框", "info")
            result3 = self._handle_input("[1/5]题目类型：单选题\n题目标题：这是一个测试题目\n\n请输入答案序号（多个选项用英文逗号分隔，如 1,2,3,4）：")
            if result3:
                self._log(f"✓ 手动答题测试成功: {result3}", "success")
            else:
                self._log("✗ 手动答题测试取消", "warning")

            self._log("🎉 所有输入对话框测试完成！", "success")

            # 清理测试图片
            try:
                if test_image_path.exists():
                    test_image_path.unlink()
                    self._log(f"✓ 测试图片已清理: {test_image_filename}", "info")
            except Exception as e:
                self._log(f"⚠️ 清理测试图片失败: {e}", "warning")

        # 在后台线程中运行测试，模拟真实场景
        threading.Thread(target=test_in_background, daemon=True).start()

    # ========== 辅助方法 ==========

    def _log(self, message: str, level: str = "info"):
        """
        添加日志到控制台

        Args:
            message: 日志消息
            level: 日志级别
        """
        # 同时输出到控制台和 GUI
        print(f"[WeBan] {message}")

        if self.log_text is None:
            return

        color_map = {
            "info": ft.Colors.BLUE,
            "success": ft.Colors.GREEN,
            "warning": ft.Colors.ORANGE,
            "error": ft.Colors.RED,
        }

        # 创建新的文本控件
        new_log = ft.Text(message, color=color_map.get(level, ft.Colors.BLACK), size=12)

        # 线程安全更新
        if threading.current_thread() is threading.main_thread():
            # 在主线程中，直接添加和更新
            self.log_text.controls.append(new_log)
            # 限制日志数量
            if len(self.log_text.controls) > 200:
                self.log_text.controls.pop(0)
            self.log_text.update()
        else:
            # 在后台线程中，使用 run_task 在主线程更新
            def update_in_main_thread():
                self.log_text.controls.append(new_log)
                if len(self.log_text.controls) > 200:
                    self.log_text.controls.pop(0)
                self.log_text.update()

            try:
                # 尝试使用 run_task
                if hasattr(self.page, 'run_task'):
                    # 创建一个协程来执行更新
                    async def async_update():
                        update_in_main_thread()
                    self.page.run_task(async_update)
                else:
                    # 回退到直接调用
                    update_in_main_thread()
            except Exception:
                # 最后的尝试：直接调用
                update_in_main_thread()

    def _show_snackbar(self, message: str, color: ft.Colors):
        """显示提示信息"""
        print(f"[SnackBar] 显示消息: {message}")

        # 使用 Flet 0.82.2 官方推荐的方式：page.show_dialog()
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=color,
                duration=3000,
            )
        )

    def _handle_input(self, prompt: str) -> str:
        """
        处理用户输入请求（在后台线程中被调用）

        Args:
            prompt: 提示信息

        Returns:
            用户输入的字符串
        """
        print(f"[WeBan Input] 收到输入请求: {prompt}")

        # 判断输入类型
        if "验证码" in prompt or "captcha" in prompt.lower():
            # 验证码输入：显示图片对话框
            import re
            match = re.search(r'请查看 (.+?) 输入验证码', prompt)
            if match:
                image_filename = match.group(1)
                print(f"[DEBUG] 提取的图片文件名: {image_filename}")  # 调试日志
                # 验证码图片应该已经在项目目录中
                image_path = str(Path.cwd() / image_filename)
                print(f"[DEBUG] 完整图片路径: {image_path}")  # 调试日志

                # 检查图片是否存在
                if Path(image_path).exists():
                    self._log(f"✓ 验证码图片已找到: {image_filename}", "success")
                else:
                    self._log(f"⚠️ 验证码图片不存在: {image_path}", "warning")
                    self._log("💡 WeBan 可能会在后台打开图片，请稍候...", "info")

                # 无论图片是否存在，都显示对话框
                # WeBan 模块会负责打开图片
                result = self.input_dialog.show_image_prompt_dialog(
                    title="请输入验证码",
                    image_path=image_path,
                    prompt="请输入验证码："
                )
                return result if result else ""

        elif "重考" in prompt or "需要重考吗" in prompt:
            # 重考选择：显示确认对话框
            import re
            # 提取考试信息
            match = re.search(r'考试项目 (.+?) 最高成绩 (\d+) 分。已考试次数 (\d+) 次，还剩 (\d+) 次', prompt)
            if match:
                project_name = match.group(1)
                score = match.group(2)
                finished_times = match.group(3)
                remaining_times = match.group(4)

                # 创建美观的重考确认对话框
                result = self.input_dialog.show_retake_dialog(
                    title="重考确认",
                    project_name=project_name,
                    score=int(score),
                    finished_times=int(finished_times),
                    remaining_times=int(remaining_times)
                )
                return "y" if result == "是" else "n"
            else:
                # 正则匹配失败，使用原始提示
                result = self.input_dialog.show_input_dialog(
                    title="重考确认",
                    prompt=prompt,
                    options=["是", "否"],
                    default_value="否"
                )
                return "y" if result == "是" else "n"

        elif "答案序号" in prompt or "请输入答案" in prompt:
            # 手动答题：显示题目对话框
            result = self.input_dialog.show_input_dialog(
                title="手动答题",
                prompt=prompt,
                default_value=""
            )
            return result if result else ""

        else:
            # 通用输入：显示简单输入对话框
            result = self.input_dialog.show_input_dialog(
                title="请输入",
                prompt=prompt,
                default_value=""
            )
            return result if result else ""
