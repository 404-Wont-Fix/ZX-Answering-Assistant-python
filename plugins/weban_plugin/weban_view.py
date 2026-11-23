"""
WeBan View - 安全微伴课程自动化

WeBan 模块的 GUI 视图，提供安全微伴课程的自动化学习界面。
采用简洁的三页面设计：简介 → 登录 → 控制台
"""

import threading
from collections import deque
from datetime import datetime

import flet as ft

from src.ui.components import run_background_task, show_snack, surface_card
from src.ui.theme import Fonts, Palette, Radius

from . import weban_adapter

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

    # 日志级别 → (深色终端面板中的文字颜色, emoji 前缀)
    _LOG_LEVEL_STYLE = {
        "info": ("#C9D4E8", "ℹ️"),
        "success": ("#3DDC97", "✅"),
        "warning": ("#FBBF24", "⚠️"),
        "error": ("#FF7B72", "❌"),
    }
    # 终端面板背景 / 顶部圆点颜色
    _TERM_BG = "#0F1724"
    _TERM_DOTS = ("#FF5F57", "#FEBC2E", "#28C840")
    # 日志面板最大行数（超出后丢弃最旧日志）
    _LOG_MAX_LINES = 400

    def __init__(self, page: ft.Page, settings_manager=None, context=None):
        """
        初始化视图

        Args:
            page: Flet 页面对象
        """
        self.page = page
        self.context = context

        # 创建输入对话框（如果可用）
        if HAS_INPUT_DIALOG and WeBanInputDialog:
            self.input_dialog = WeBanInputDialog(page)
        else:
            self.input_dialog = None

        self.adapter = weban_adapter.get_weban_adapter(
            progress_callback=self._log,
            input_callback=self._handle_input  # 传入输入回调
        )

        # 插件入口应传入共享配置服务；保留回退以支持独立预览。
        self.settings_manager = settings_manager or get_settings_manager()

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
        self.log_list = None          # 日志 ListView（auto_scroll 自动跟随底部）
        self.log_count_text = None    # 终端面板右上角行数
        self.start_button = None
        self.stop_button = None
        self.clear_button = None
        self.status_chip = None       # 状态 chip（准备就绪/正在执行/…）

        # UI 并发保护：WeBan 工作线程日志密集，所有面板变更/刷新必须串行化，
        # 避免多个 executor 线程并发 page.update() 触发 Flet diff 竞态
        # （"list index out of range"）
        self._ui_lock = threading.Lock()
        self._log_pending = deque()
        self._log_flush_scheduled = False

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

        # 外层包装：简介/登录页可滚动；控制台页切换为不可滚动
        # （可滚动容器主轴无界，会让内部 expand 全部失效、日志面板无限变长）
        self.content_wrapper = ft.Column(
            [self.current_content],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )
        return self.content_wrapper

    def _set_wrapper_scroll(self, auto_scroll: bool):
        """切换外层包装的滚动模式（True=可滚动，False=固定布局撑满）"""
        self.content_wrapper.scroll = ft.ScrollMode.AUTO if auto_scroll else None

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
        """获取控制台页面内容（深色终端风格日志面板 + 状态 chip）"""
        # 日志列表：auto_scroll=True 让新日志自动滚动到底部
        self.log_list = ft.ListView(
            expand=True,
            auto_scroll=True,
            spacing=3,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        )
        self.log_count_text = ft.Text(
            "0 行", size=11, color="#7C8AA5", font_family=Fonts.get_system_font()
        )

        # 终端面板顶栏：交通灯圆点 + 标题 + 行数
        term_header = ft.Container(
            content=ft.Row(
                [
                    *(
                        ft.Container(
                            width=9,
                            height=9,
                            bgcolor=dot_color,
                            border_radius=9,
                        )
                        for dot_color in self._TERM_DOTS
                    ),
                    ft.Container(width=8),
                    ft.Text(
                        "执行日志",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color="#AEB9CE",
                        font_family=Fonts.get_system_font(),
                    ),
                    ft.Container(expand=True),
                    self.log_count_text,
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(left=14, right=14, top=10),
            bgcolor=self._TERM_BG,
            border_radius=ft.BorderRadius(14, 14, 0, 0),
        )

        # 深色终端日志面板（顶栏 + 日志区）
        log_panel = ft.Container(
            content=ft.Column(
                [term_header, self.log_list],
                spacing=0,
                expand=True,
            ),
            bgcolor=self._TERM_BG,
            border_radius=Radius.MEDIUM,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            expand=True,
        )

        # 控制按钮
        self.start_button = ft.FilledButton(
            "开始执行",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=Palette.ACCENT,
            color="#FFFFFF",
            disabled=self.is_running,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=24, vertical=14),
                text_style=Fonts.text(size=13, weight=ft.FontWeight.W_600),
            ),
            on_click=self._on_console_start,
        )

        self.stop_button = ft.FilledButton(
            "停止执行",
            icon=ft.Icons.STOP,
            bgcolor=Palette.DANGER,
            color="#FFFFFF",
            disabled=not self.is_running,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=24, vertical=14),
                text_style=Fonts.text(size=13, weight=ft.FontWeight.W_600),
            ),
            on_click=self._on_console_stop,
        )

        self.clear_button = ft.OutlinedButton(
            "清空日志",
            icon=ft.Icons.DELETE_OUTLINE,
            style=ft.ButtonStyle(
                color=Palette.TEXT_MUTED,
                side=ft.BorderSide(1, Palette.BORDER_STRONG),
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=16, vertical=13),
            ),
            on_click=self._on_clear_log,
        )

        # 状态 chip
        self.status_chip = ft.Container(
            content=ft.Text(
                "正在执行..." if self.is_running else "准备就绪",
                size=12,
                weight=ft.FontWeight.W_600,
                color=Palette.PRIMARY if self.is_running else Palette.TEXT_MUTED,
                font_family=Fonts.get_system_font(),
            ),
            bgcolor=Palette.PRIMARY_SOFT if self.is_running else Palette.SURFACE_ALT,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=30,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        )

        # 登录信息 chip（学校 / 账号）
        def info_chip(icon, text: str) -> ft.Container:
            return ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, size=14, color=Palette.PRIMARY),
                        ft.Text(
                            text,
                            size=12,
                            color=Palette.TEXT_MUTED,
                            font_family=Fonts.get_system_font(),
                        ),
                    ],
                    spacing=5,
                    tight=True,
                ),
                bgcolor=Palette.SURFACE_ALT,
                border=ft.Border.all(1, Palette.BORDER),
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            )

        console_card = surface_card(
            ft.Column(
                [
                    # 登录信息 + 状态
                    ft.Row(
                        [
                            info_chip(ft.Icons.SCHOOL, self.school_name or "未知学校"),
                            ft.Container(width=4),
                            info_chip(ft.Icons.PERSON, self.account or "未登录"),
                            ft.Container(expand=True),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    # 控制按钮行
                    ft.Row(
                        [self.start_button, self.stop_button, ft.Container(expand=True), self.clear_button],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    # 日志面板（撑满剩余高度）
                    log_panel,
                ],
                spacing=14,
                expand=True,
            ),
            padding=18,
        )
        console_card.expand = True

        return ft.Column(
            [
                # 标题栏
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=Palette.PRIMARY,
                            on_click=self._on_back_to_login,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "执行控制台",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color=Palette.TEXT,
                                ),
                                ft.Text(
                                    "自动学习与答题任务将在这里运行",
                                    size=12,
                                    color=Palette.TEXT_MUTED,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                        ft.Container(expand=True),
                        self.status_chip,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                console_card,
            ],
            spacing=14,
            expand=True,
        )

    def _on_start_click(self, e):
        """开始按钮点击事件 - 切换到登录页面"""
        login_content = self._get_login_content()
        self._set_wrapper_scroll(True)
        self.current_content.content = login_content
        self.page.update()

    def _on_back_click(self, e):
        """返回按钮点击事件 - 返回简介页面"""
        intro_content = self._get_intro_content()
        self._set_wrapper_scroll(True)
        self.current_content.content = intro_content
        self.page.update()

    def _on_validate_school(self, e):
        """验证学校按钮点击事件"""
        school_name = self.school_field.value.strip()
        if not school_name:
            self._show_validation_dialog("错误", "请输入学校名称", ft.Colors.RED)
            return

        # 显示加载对话框
        loading_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.REFRESH, color=ft.Colors.BLUE),
                    ft.Text("正在验证", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Column(
                [
                    ft.Text(f"正在验证学校: {school_name}"),
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    ft.ProgressBar(width=300),
                ],
                tight=True,
                width=400,
            ),
        )

        self.page.show_dialog(loading_dialog)

        # 在后台线程验证学校
        def validate_school():
            try:
                result = self.adapter.validate_tenant(school_name)
                # 在主线程中显示结果
                def show_result():
                    self.page.pop_dialog()  # 关闭加载对话框
                    if result["success"]:
                        self._show_validation_dialog(
                            "验证成功",
                            f"✓ {result['message']}",
                            ft.Colors.GREEN
                        )
                    else:
                        self._show_validation_dialog(
                            "验证失败",
                            f"✗ {result['message']}",
                            ft.Colors.RED
                        )
                self.page.run_thread(show_result)
            except Exception as ex:
                # 在主线程中显示错误
                def show_error():
                    self.page.pop_dialog()  # 关闭加载对话框
                    self._show_validation_dialog(
                        "验证失败",
                        f"验证失败: {str(ex)}",
                        ft.Colors.RED
                    )
                self.page.run_thread(show_error)

        self._run_background(validate_school)

    def _show_validation_dialog(self, title: str, message: str, color: ft.Colors):
        """显示验证结果对话框"""
        # 选择图标
        if color == ft.Colors.GREEN:
            icon = ft.Icons.CHECK_CIRCLE
        elif color == ft.Colors.RED:
            icon = ft.Icons.ERROR
        else:
            icon = ft.Icons.INFO

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(icon, color=color, size=28),
                    ft.Text(title, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Text(message),
            actions=[
                ft.TextButton(
                    "确定",
                    on_click=lambda _: self.page.pop_dialog()
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

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

        # 切换到控制台页面（外层停止滚动，让日志面板撑满剩余高度）
        console_content = self._get_console_content()
        self._set_wrapper_scroll(False)
        self.current_content.content = console_content
        self.page.update()

        # 显示欢迎消息
        self._log(f"欢迎使用安全微伴！学校: {school_name}", "success")
        self._log(f"配置已加载，点击'开始执行'按钮开始任务", "info")

    def _on_back_to_login(self, e):
        """返回登录页面"""
        login_content = self._get_login_content()
        self._set_wrapper_scroll(True)
        self.current_content.content = login_content
        self.page.update()

    def _on_console_start(self, e):
        """控制台开始按钮点击事件"""
        if self.is_running:
            show_snack(self.page, "任务正在执行中，请先停止", color=ft.Colors.ORANGE)
            return

        self.is_running = True
        with self._ui_lock:
            self.start_button.disabled = True
            self.stop_button.disabled = False
            self._clear_log_items()
        self._set_status("正在执行", Palette.PRIMARY, Palette.PRIMARY_SOFT)
        self._log(f"开始执行任务: {self.school_name}", "info")
        self._log(f"账号: {self.account}", "info")
        self._log("-" * 46, "info")

        # 在后台线程执行任务
        def run_task():
            try:
                result = self.adapter.start(use_multithread=False)
                self._log("-" * 46, "info")
                self._log(
                    f"执行完成！成功: {result['success']}，失败: {result['failed']}",
                    "success",
                )
            except Exception as ex:
                stopped = bool(self.adapter) and self.adapter._stop_event.is_set()
                if stopped or "停止" in str(ex) or "取消" in str(ex):
                    # 用户主动停止 / 取消输入，不算错误
                    self._log(f"任务已中止: {ex}", "warning")
                else:
                    self._log(f"执行失败: {str(ex)}", "error")
                    import traceback
                    self._log(f"错误详情: {traceback.format_exc()}", "error")
            finally:
                # 线程安全的UI更新
                def update_final_state():
                    self.is_running = False
                    with self._ui_lock:
                        if self.start_button:
                            self.start_button.disabled = False
                        if self.stop_button:
                            self.stop_button.disabled = True
                    if bool(self.adapter) and self.adapter._stop_event.is_set():
                        self._set_status("已停止", Palette.WARNING, Palette.WARNING_SOFT)
                    else:
                        self._set_status("执行完成", Palette.ACCENT, Palette.ACCENT_SOFT)

                self.page.run_thread(update_final_state)

        self.task_thread = self._run_background(run_task)

    def _on_console_stop(self, e):
        """控制台停止按钮点击事件"""
        if not self.is_running:
            return

        with self._ui_lock:
            self.stop_button.disabled = True
            self.page.update()
        self._log("正在停止任务...", "warning")
        self._set_status("正在停止", Palette.WARNING, Palette.WARNING_SOFT)
        self.adapter.stop()

    def _on_clear_log(self, e):
        """清空日志按钮点击事件"""
        with self._ui_lock:
            self._clear_log_items()
            self.page.update()

    def _clear_log_items(self):
        """清空日志列表与行数（纯变更，调用方需持有 _ui_lock 并负责刷新）"""
        if self.log_list:
            self.log_list.controls.clear()
        if self.log_count_text:
            self.log_count_text.value = "0 行"

    def _set_status(self, label: str, color: str, bgcolor: str):
        """更新状态 chip 的文字与配色（与日志刷新共用 UI 锁）"""
        if not self.status_chip:
            return

        def update_ui():
            try:
                with self._ui_lock:
                    self.status_chip.content.value = label
                    self.status_chip.content.color = color
                    self.status_chip.bgcolor = bgcolor
                    self.page.update()
            except Exception as ex:
                print(f"[WeBan] 状态UI更新失败: {ex}")

        self.page.run_thread(update_ui)

    def _log(self, message: str, level: str = "info"):
        """日志输出函数（写入深色终端面板，自动滚动到底部）。

        WeBan 日志密集且来自工作线程：不再每条日志单独调度 update
        （多线程并发 page.update() 会触发 Flet diff 竞态，报
        "list index out of range"），而是先入队，由单个刷新任务
        批量写入并一次性 update。
        """
        # 如果日志面板还未初始化，输出到控制台
        if not self.log_list:
            print(f"[WeBan] {message}")
            return

        color, prefix = self._LOG_LEVEL_STYLE.get(level, self._LOG_LEVEL_STYLE["info"])
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_pending.append((f"[{timestamp}] {prefix} {message}", color))
        self._schedule_log_flush()

    def _schedule_log_flush(self):
        """确保同一时刻只有一个日志刷新任务在排队（防止 update 风暴）"""
        with self._ui_lock:
            if self._log_flush_scheduled:
                return
            self._log_flush_scheduled = True
        self.page.run_thread(self._flush_log_entries)

    def _flush_log_entries(self):
        """把队列中的日志批量写入面板（持锁串行化所有 UI 变更与刷新）"""
        try:
            with self._ui_lock:
                self._log_flush_scheduled = False
                entries = []
                while self._log_pending:
                    entries.append(self._log_pending.popleft())
                if not entries:
                    return
                for line, color in entries:
                    self.log_list.controls.append(
                        ft.Text(
                            line,
                            size=12,
                            color=color,
                            selectable=True,
                            font_family=Fonts.get_system_font(),
                        )
                    )
                if len(self.log_list.controls) > self._LOG_MAX_LINES:
                    del self.log_list.controls[
                        : len(self.log_list.controls) - self._LOG_MAX_LINES
                    ]
                if self.log_count_text:
                    self.log_count_text.value = f"{len(self.log_list.controls)} 行"
                self.page.update()
        except Exception as ex:
            print(f"[WeBan] 日志UI更新失败: {ex}")

    def _show_snackbar(self, message: str, bgcolor = None):
        """
        显示 SnackBar 提示（Flet 0.8.0+ 兼容）

        Args:
            message: 提示消息
            bgcolor: 背景颜色
        """
        try:
            show_snack(self.page, message, color=bgcolor)
        except Exception as e:
            # 如果 SnackBar 失败，输出到控制台
            print(f"[SnackBar] {message}")
            print(f"[SnackBar Error] {e}")

    def _handle_input(self, prompt: str) -> str:
        """处理用户输入（用于验证码、手动作答等），由 WeBan 后台线程调用。

        旧实现使用 Flet 0.7 的 page.dialog API（0.8+ 已移除），弹窗永远
        不会显示且 input_event 永久阻塞。现在改用 WeBanInputDialog。
        """
        # 取出 adapter 捕获的题目上下文（手动答题时为题目+选项文本）
        context = ""
        try:
            context = (getattr(self.adapter, "pending_context", "") or "").strip()
            self.adapter.pending_context = ""
        except Exception:
            context = ""

        # 题目上下文写入日志面板留档（用户关闭弹窗后仍可回看）
        if context and "答案序号" in prompt:
            for line in context.splitlines():
                if line.strip():
                    self._log(line, "info")

        if not self.input_dialog:
            self._log("GUI 输入组件不可用，无法完成交互", "error")
            raise RuntimeError("GUI 输入组件不可用")

        # 根据提示内容选择标题
        if "验证码" in prompt:
            title = "验证码输入"
        elif "答案序号" in prompt:
            title = "手动答题"
        else:
            title = "需要输入"

        result = self.input_dialog.show_input_dialog(title, prompt, context=context or None)
        if result is None:
            # 用户取消 / 超时：抛异常让 WeBan 中止当前账号，避免死循环重试
            raise RuntimeError("用户取消了输入")
        return result

    def _run_background(self, target, *args, **kwargs):
        """在后台线程安全执行耗时任务（委托 run_background_task）。"""
        run_background_task(self.page, lambda: target(*args, **kwargs))

    def cleanup(self):
        """插件卸载时停止正在运行的 WeBan 任务。"""
        try:
            self.adapter.stop()
        except Exception as e:
            print(f"[WeBan] 清理任务失败: {e}")
        self.is_running = False
