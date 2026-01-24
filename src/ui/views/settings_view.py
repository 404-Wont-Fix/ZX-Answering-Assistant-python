"""
ZX Answering Assistant - 设置视图模块

This module contains the UI components for the settings page.
"""

import flet as ft
from src.settings import get_settings_manager, APIRateLevel


class SettingsView:
    """设置页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化设置视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app
        self.current_content = None
        self.settings_manager = get_settings_manager()

        # 输入框引用
        self.student_username_field = None
        self.student_password_field = None
        self.teacher_username_field = None
        self.teacher_password_field = None
        self.rate_level_dropdown = None
        self.max_retries_field = None

        # 显示状态
        self.student_status_icon = None
        self.student_status_text = None
        self.teacher_status_icon = None
        self.teacher_status_text = None

    def get_content(self) -> ft.Column:
        """
        获取设置页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        # 创建主界面内容
        main_content = self._get_main_content()

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

    def _get_main_content(self) -> ft.Column:
        """
        获取主界面内容

        Returns:
            ft.Column: 主界面组件
        """
        # 加载当前设置
        student_user, _ = self.settings_manager.get_student_credentials()
        teacher_user, _ = self.settings_manager.get_teacher_credentials()
        rate_level = self.settings_manager.get_rate_level()
        max_retries = self.settings_manager.get_max_retries()

        # 创建状态指示器
        student_has_config = bool(student_user)
        teacher_has_config = bool(teacher_user)

        return ft.Column(
            [
                # 页面标题
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SETTINGS, size=32, color=ft.Colors.BLUE_800),
                            ft.Text(
                                "系统设置",
                                size=32,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                        ],
                        spacing=15,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(vertical=10),
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                # 账号管理区域
                self._create_accounts_section(student_has_config, teacher_has_config),

                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # API设置区域
                self._create_api_settings_section(rate_level, max_retries),

                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 保存按钮
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "保存设置",
                            icon=ft.Icons.SAVE,
                            bgcolor=ft.Colors.GREEN,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.padding.symmetric(horizontal=40, vertical=15),
                                animation_duration=200,
                            ),
                            on_click=lambda e: self._on_save_click(e),
                            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )

    def _create_accounts_section(
        self, student_has_config: bool, teacher_has_config: bool
    ) -> ft.Container:
        """
        创建账号管理区域

        Args:
            student_has_config: 学生端是否已配置
            teacher_has_config: 教师端是否已配置

        Returns:
            ft.Container: 账号管理区域
        """
        # 学生端状态
        student_status_color = ft.Colors.GREEN if student_has_config else ft.Colors.ORANGE
        student_status_text = "已配置" if student_has_config else "未配置"

        # 教师端状态
        teacher_status_color = ft.Colors.GREEN if teacher_has_config else ft.Colors.ORANGE
        teacher_status_text = "已配置" if teacher_has_config else "未配置"

        # 获取已保存的凭据
        student_user, student_pass = self.settings_manager.get_student_credentials()
        teacher_user, teacher_pass = self.settings_manager.get_teacher_credentials()

        # 创建输入框
        self.student_username_field = ft.TextField(
            label="学生端账号",
            hint_text="请输入学生端账号",
            value=student_user or "",
            width=400,
            icon=ft.Icons.PERSON,
            prefix_icon=ft.Icons.SCHOOL,
        )

        self.student_password_field = ft.TextField(
            label="学生端密码",
            hint_text="请输入学生端密码",
            value=student_pass or "",
            width=400,
            password=True,
            can_reveal_password=True,
            icon=ft.Icons.LOCK,
        )

        self.teacher_username_field = ft.TextField(
            label="教师端账号",
            hint_text="请输入教师端账号",
            value=teacher_user or "",
            width=400,
            icon=ft.Icons.PERSON,
            prefix_icon=ft.Icons.PERSON_4,
        )

        self.teacher_password_field = ft.TextField(
            label="教师端密码",
            hint_text="请输入教师端密码",
            value=teacher_pass or "",
            width=400,
            password=True,
            can_reveal_password=True,
            icon=ft.Icons.LOCK,
        )

        return ft.Container(
            content=ft.Column(
                [
                    # 区域标题
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=28, color=ft.Colors.PURPLE),
                                ft.Text(
                                    "账号管理",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_800,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=ft.padding.only(bottom=15),
                    ),

                    # 账号卡片
                    ft.ResponsiveRow(
                        [
                            # 学生端账号卡片
                            ft.Container(
                                content=ft.Card(
                                    content=ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.ListTile(
                                                    leading=ft.Icon(
                                                        ft.Icons.SCHOOL,
                                                        color=ft.Colors.BLUE,
                                                        size=30,
                                                    ),
                                                    title=ft.Text(
                                                        "学生端账号",
                                                        weight=ft.FontWeight.BOLD,
                                                        size=18,
                                                    ),
                                                    subtitle=ft.Row(
                                                        [
                                                            ft.Icon(
                                                                ft.Icons.CHECK_CIRCLE
                                                                if student_has_config
                                                                else ft.Icons.WARNING,
                                                                color=student_status_color,
                                                                size=16,
                                                            ),
                                                            ft.Text(
                                                                student_status_text,
                                                                color=student_status_color,
                                                                size=12,
                                                            ),
                                                        ],
                                                        spacing=5,
                                                    ),
                                                ),
                                                ft.Divider(height=1, color=ft.Colors.GREY_300),
                                                ft.Container(
                                                    content=ft.Column(
                                                        [
                                                            self.student_username_field,
                                                            ft.Divider(
                                                                height=10,
                                                                color=ft.Colors.TRANSPARENT,
                                                            ),
                                                            self.student_password_field,
                                                        ],
                                                        spacing=0,
                                                    ),
                                                    padding=ft.padding.all(15),
                                                ),
                                            ],
                                            spacing=0,
                                        ),
                                        padding=0,
                                    ),
                                    elevation=3,
                                ),
                                col={"md": 6},
                                padding=10,
                            ),

                            # 教师端账号卡片
                            ft.Container(
                                content=ft.Card(
                                    content=ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.ListTile(
                                                    leading=ft.Icon(
                                                        ft.Icons.PERSON_4,
                                                        color=ft.Colors.PURPLE,
                                                        size=30,
                                                    ),
                                                    title=ft.Text(
                                                        "教师端账号",
                                                        weight=ft.FontWeight.BOLD,
                                                        size=18,
                                                    ),
                                                    subtitle=ft.Row(
                                                        [
                                                            ft.Icon(
                                                                ft.Icons.CHECK_CIRCLE
                                                                if teacher_has_config
                                                                else ft.Icons.WARNING,
                                                                color=teacher_status_color,
                                                                size=16,
                                                            ),
                                                            ft.Text(
                                                                teacher_status_text,
                                                                color=teacher_status_color,
                                                                size=12,
                                                            ),
                                                        ],
                                                        spacing=5,
                                                    ),
                                                ),
                                                ft.Divider(height=1, color=ft.Colors.GREY_300),
                                                ft.Container(
                                                    content=ft.Column(
                                                        [
                                                            self.teacher_username_field,
                                                            ft.Divider(
                                                                height=10,
                                                                color=ft.Colors.TRANSPARENT,
                                                            ),
                                                            self.teacher_password_field,
                                                        ],
                                                        spacing=0,
                                                    ),
                                                    padding=ft.padding.all(15),
                                                ),
                                            ],
                                            spacing=0,
                                        ),
                                        padding=0,
                                    ),
                                    elevation=3,
                                ),
                                col={"md": 6},
                                padding=10,
                            ),
                        ],
                        spacing=10,
                        run_spacing=10,
                    ),
                ],
                spacing=0,
            ),
            width=900,
            padding=20,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=15,
        )

    def _create_api_settings_section(
        self, rate_level: APIRateLevel, max_retries: int
    ) -> ft.Container:
        """
        创建API设置区域

        Args:
            rate_level: 当前速率级别
            max_retries: 当前最大重试次数

        Returns:
            ft.Container: API设置区域
        """
        # 创建速率级别下拉框
        self.rate_level_dropdown = ft.Dropdown(
            label="请求速率级别",
            hint_text="选择API请求速率",
            options=[
                ft.dropdown.Option(
                    key="one_second",
                    text="1秒 - 快速请求",
                ),
                ft.dropdown.Option(
                    key="two_seconds",
                    text="2秒 - 较快请求",
                ),
                ft.dropdown.Option(
                    key="three_seconds",
                    text="3秒 - 较慢请求",
                ),
                ft.dropdown.Option(
                    key="four_seconds",
                    text="4秒 - 默认推荐",
                ),
            ],
            value=rate_level.value,
            width=400,
            leading_icon=ft.Icons.SPEED,
            text_style=ft.TextStyle(size=14),
        )

        # 创建重试次数输入框
        self.max_retries_field = ft.TextField(
            label="最大重试次数",
            hint_text="请求失败时的最大重试次数",
            value=str(max_retries),
            width=400,
            icon=ft.Icons.REFRESH,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        return ft.Container(
            content=ft.Column(
                [
                    # 区域标题
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.API, size=28, color=ft.Colors.CYAN),
                                ft.Text(
                                    "API设置",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_800,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=ft.padding.only(bottom=15),
                    ),

                    # API设置卡片
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    # 请求速率设置
                                    ft.ListTile(
                                        leading=ft.Icon(
                                            ft.Icons.SPEED,
                                            color=ft.Colors.ORANGE,
                                            size=28,
                                        ),
                                        title=ft.Text(
                                            "请求速率控制",
                                            weight=ft.FontWeight.BOLD,
                                            size=16,
                                        ),
                                        subtitle=ft.Text(
                                            "控制API请求之间的延迟时间，避免触发速率限制",
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        ),
                                    ),
                                    ft.Container(
                                        content=self.rate_level_dropdown,
                                        padding=ft.padding.symmetric(
                                            horizontal=20, vertical=10
                                        ),
                                    ),

                                    ft.Divider(height=1, color=ft.Colors.GREY_300),

                                    # 最大重试次数设置
                                    ft.ListTile(
                                        leading=ft.Icon(
                                            ft.Icons.REFRESH,
                                            color=ft.Colors.BLUE,
                                            size=28,
                                        ),
                                        title=ft.Text(
                                            "最大重试次数",
                                            weight=ft.FontWeight.BOLD,
                                            size=16,
                                        ),
                                        subtitle=ft.Text(
                                            "网络请求失败时的自动重试次数（0-10次）",
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        ),
                                    ),
                                    ft.Container(
                                        content=self.max_retries_field,
                                        padding=ft.padding.symmetric(
                                            horizontal=20, vertical=10
                                        ),
                                    ),

                                    # 提示信息
                                    ft.Container(
                                        content=ft.Row(
                                            [
                                                ft.Icon(
                                                    ft.Icons.INFO_OUTLINE,
                                                    color=ft.Colors.BLUE_400,
                                                    size=20,
                                                ),
                                                ft.Text(
                                                    "提示：如果遇到频繁的网络错误，可以增加重试次数或降低请求速率",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                    italic=True,
                                                ),
                                            ],
                                            spacing=10,
                                        ),
                                        padding=ft.padding.all(15),
                                        bgcolor=ft.Colors.BLUE_50,
                                        border_radius=8,
                                    ),
                                ],
                                spacing=0,
                            ),
                            padding=0,
                        ),
                        elevation=3,
                    ),
                ],
                spacing=0,
            ),
            width=900,
            padding=20,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=15,
        )

    def _on_save_click(self, e):
        """处理保存设置按钮点击事件"""
        # 获取输入值
        student_username = self.student_username_field.value.strip()
        student_password = self.student_password_field.value.strip()
        teacher_username = self.teacher_username_field.value.strip()
        teacher_password = self.teacher_password_field.value.strip()

        # 验证输入
        errors = []

        # 如果输入了账号但没输入密码，或反之
        if student_username and not student_password:
            errors.append("学生端：请输入密码")
        if not student_username and student_password:
            errors.append("学生端：请输入账号")
        if teacher_username and not teacher_password:
            errors.append("教师端：请输入密码")
        if not teacher_username and teacher_password:
            errors.append("教师端：请输入账号")

        # 验证API设置
        try:
            max_retries = int(self.max_retries_field.value.strip())
            if max_retries < 0 or max_retries > 10:
                errors.append("最大重试次数必须在 0-10 之间")
        except ValueError:
            errors.append("最大重试次数必须是有效的数字")

        # 如果有错误，显示错误对话框
        if errors:
            error_content = ft.Column(
                [ft.Text(f"• {error}", size=13) for error in errors],
                spacing=5,
                tight=True,
            )

            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                        ft.Text("输入错误", color=ft.Colors.RED),
                    ],
                    spacing=10,
                ),
                content=error_content,
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(error_dialog)
            return

        # 保存设置
        success = True
        save_errors = []

        # 保存学生端凭据
        if student_username and student_password:
            if not self.settings_manager.set_student_credentials(
                student_username, student_password
            ):
                save_errors.append("学生端凭据保存失败")
                success = False
        else:
            # 清空学生端凭据
            self.settings_manager.clear_student_credentials()

        # 保存教师端凭据
        if teacher_username and teacher_password:
            if not self.settings_manager.set_teacher_credentials(
                teacher_username, teacher_password
            ):
                save_errors.append("教师端凭据保存失败")
                success = False
        else:
            # 清空教师端凭据
            self.settings_manager.clear_teacher_credentials()

        # 保存API设置
        rate_level_name = self.rate_level_dropdown.value
        rate_level = APIRateLevel.from_name(rate_level_name)

        if not self.settings_manager.set_rate_level(rate_level):
            save_errors.append("请求速率保存失败")
            success = False

        if not self.settings_manager.set_max_retries(max_retries):
            save_errors.append("最大重试次数保存失败")
            success = False

        # 显示结果
        if success and not save_errors:
            # 成功对话框
            success_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=28),
                        ft.Text(
                            "保存成功", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN
                        ),
                    ],
                    spacing=10,
                ),
                content=ft.Column(
                    [
                        ft.Text("✅ 所有设置已成功保存！"),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                        ft.Text("已保存的配置：", size=13, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            f"• 学生端：{'已配置' if student_username else '未配置'}", size=12
                        ),
                        ft.Text(
                            f"• 教师端：{'已配置' if teacher_username else '未配置'}", size=12
                        ),
                        ft.Text(f"• 请求速率：{rate_level.get_display_name()}", size=12),
                        ft.Text(f"• 最大重试：{max_retries} 次", size=12),
                    ],
                    spacing=0,
                    tight=True,
                ),
                actions=[
                    ft.ElevatedButton(
                        "确定",
                        icon=ft.Icons.CHECK,
                        bgcolor=ft.Colors.GREEN,
                        color=ft.Colors.WHITE,
                        on_click=lambda _: self.page.pop_dialog(),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
            )
            self.page.show_dialog(success_dialog)

            # 刷新界面以更新状态显示
            self._refresh_settings_display()
        else:
            # 部分失败对话框
            content = ft.Column(
                [
                    ft.Text("⚠️ 部分设置保存失败："),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    *[ft.Text(f"• {error}", size=12) for error in save_errors],
                ],
                spacing=3,
                tight=True,
            )

            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
                        ft.Text("保存部分失败", color=ft.Colors.ORANGE),
                    ],
                    spacing=10,
                ),
                content=content,
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(error_dialog)

    def _refresh_settings_display(self):
        """刷新设置显示"""
        # 刷新界面（会重新加载最新的设置）
        new_content = self._get_main_content()
        self.current_content.content = new_content
        self.page.update()
