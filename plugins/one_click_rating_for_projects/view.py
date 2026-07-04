"""
ZX Answering Assistant - 懒狗一键评分视图模块

This module contains the UI components for the lazy AI grading page.
- 落地页：功能介绍 + 开始评分入口
- 登录页：复用答案提取的教师端登录框（Extractor.login）获取 Access Token
- 项目列表页：调用 GetTeacherClassProject 渲染产教融合项目列表（搜索 + 分页）
"""

import asyncio
import threading
import math

import flet as ft

from src.core.config import get_settings_manager
from src.extraction.extractor import Extractor
from src.ui.components import (
    hero_panel,
    page_heading,
    primary_button,
    secondary_button,
    section_label,
    status_chip,
    surface_card,
    workflow_step,
)
from src.ui.theme import Palette, Radius

from .api_client import LazyGradingAPIClient
from .models import ClassProject


class LazyAIGradingView:
    """懒狗一键评分页面视图"""

    def __init__(self, page: ft.Page, main_app=None, context=None):
        """
        初始化懒狗一键评分视图

        Args:
            page (ft.Page): Flet 页面对象
            main_app: MainApp 实例（用于导航切换）
            context: PluginContext 实例
        """
        self.page = page
        self.main_app = main_app
        self.context = context
        self.current_content = None  # AnimatedSwitcher 内容容器引用
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框
        self.remember_password_checkbox = None  # 记住密码复选框

        # 登录相关状态
        self.extractor = None  # Extractor 实例（复用其登录能力）
        self.access_token = None  # 教师端 access_token
        self.progress_dialog = None  # 登录进度对话框

        # 线程同步
        self.login_event = threading.Event()
        self.login_success = False
        self.login_error = None

        # 项目列表相关状态
        self.api_client = None  # LazyGradingAPIClient，登录成功后建立
        self.project_list = []  # 当前页项目列表
        self.total_count = 0  # 项目总数
        self.page_index = 1  # 当前页码（从 1 开始）
        self.page_size = 10  # 每页条数
        self.key_word = ""  # 搜索关键字
        self.class_status = 0  # 班级项目状态过滤（0=全部）
        self.list_loading = False  # 列表是否加载中
        self.list_error = None  # 列表加载错误信息

        # 列表屏动态控件引用（用于局部刷新，保留搜索框焦点）
        self.search_field = None
        self.page_size_dropdown = None
        self.count_text = None
        self.page_text = None
        self.prev_btn = None
        self.next_btn = None
        self.list_container = None

        # 设置管理器
        self.settings_manager = get_settings_manager()

    # ==================== 内容入口 ====================

    def get_content(self) -> ft.Column:
        """
        获取懒狗一键评分页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
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

    def _run_background(self, target, *args, **kwargs):
        """在后台线程安全执行耗时任务（参照 cloud_exam._run_background）。"""
        context = getattr(self, "context", None)
        if context and hasattr(context, "run_task"):
            return context.run_task(target, None, *args, **kwargs)
        if hasattr(self.page, "run_thread"):
            return self.page.run_thread(target, *args, **kwargs)
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread

    # ==================== 落地页 ====================

    def _get_main_content(self) -> ft.Column:
        """获取主界面（落地页）内容"""
        start_button = ft.FilledButton(
            "开始评分",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=Palette.SURFACE,
            color=Palette.PRIMARY,
            on_click=lambda e: self._on_start_click(e),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=24, vertical=16),
                text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
            ),
        )
        return ft.Column(
            [
                page_heading(
                    "懒狗一键评分",
                    "自动批改产教融合项目的分数，一键完成 评分评分",
                    ft.Icons.AUTO_AWESOME,
                ),
                hero_panel(
                    "一键智能批改产教融合项目",
                    "登录账号、选择待评分项目，由 评分完成产教融合项目的分数批改。",
                    action=start_button,
                    chips=[
                        status_chip(
                            "产教融合",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "评分评分",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "一键批改",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                    ],
                    icon=ft.Icons.AUTO_AWESOME,
                ),
                section_label("评分流程", "三步启动安全、快速的产教融合项目评分任务"),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            content=workflow_step(
                                "01",
                                "身份登录",
                                "完成账号身份验证",
                                ft.Icons.PERSON_OUTLINE,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "02",
                                "选择项目",
                                "选取待评分的产教融合项目",
                                ft.Icons.FOLDER_OUTLINED,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "03",
                                "AI 评分",
                                "一键智能批改项目分数",
                                ft.Icons.BOLT_OUTLINED,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ],
            spacing=22,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _on_start_click(self, e):
        """处理「开始评分」按钮点击事件。"""
        # 已登录且持有 token：直接进列表页并刷新，避免重复登录
        if self.access_token and self.api_client is not None:
            self.current_content.content = self._get_project_list_content()
            self.page.update()
            self._load_projects()
            return
        # 否则进入登录页
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    # ==================== 登录页（复用答案提取的教师端登录框） ====================

    def _get_login_content(self) -> ft.Column:
        """获取教师端登录界面内容（与答案提取一致）"""
        # 加载已保存的凭据
        saved_username, saved_password = self.settings_manager.get_teacher_credentials()

        # 初始化输入框（自动填充已保存的凭据）
        self.username_field = ft.TextField(
            label="教师账号",
            hint_text="请输入教师端账号",
            value=saved_username or "",
            width=400,
            prefix_icon=ft.Icons.PERSON,
            autofocus=True,
        )

        self.password_field = ft.TextField(
            label="密码",
            hint_text="请输入教师端密码",
            value=saved_password or "",
            width=400,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )

        # 创建“记住我”复选框
        self.remember_password_checkbox = ft.Checkbox(
            label="记住我（自动保存账号和密码）",
            value=bool(saved_username and saved_password),
            fill_color=Palette.PRIMARY,
        )

        return ft.Column(
            [
                page_heading(
                    "教师端登录",
                    "认证教师账号后开始产教融合项目评分",
                    ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                ),
                surface_card(
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.PERSON_4, size=32, color=Palette.PRIMARY),
                                width=64,
                                height=64,
                                alignment=ft.Alignment(0, 0),
                                bgcolor=Palette.PRIMARY_SOFT,
                                border_radius=Radius.CARD,
                            ),
                            ft.Text("登录教师端", size=20, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                            ft.Text("登录后即可开始批改产教融合项目", size=12, color=Palette.TEXT_MUTED),
                            self.username_field,
                            self.password_field,
                            self.remember_password_checkbox,
                            ft.Row(
                                [
                                    secondary_button("返回", ft.Icons.ARROW_BACK, lambda e: self._on_back_click(e)),
                                    primary_button("登录并继续", ft.Icons.LOGIN, lambda e: self._on_login_click(e)),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=12,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=16,
                    ),
                    padding=30,
                    width=520,
                ),
            ],
            spacing=24,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _on_back_click(self, e):
        """处理返回按钮点击事件 - 返回落地页"""
        main_content = self._get_main_content()
        self.current_content.content = main_content
        self.page.update()

    def _on_login_click(self, e):
        """处理登录按钮点击事件 - 复用 Extractor 的登录能力获取 Access Token"""
        username = self.username_field.value.strip()
        password = self.password_field.value.strip()

        if not username or not password:
            dialog = ft.AlertDialog(
                title=ft.Text("错误"),
                content=ft.Text("请输入用户名和密码"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 显示加载对话框
        self.progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("登录中"),
            content=ft.Column(
                [
                    ft.ProgressRing(stroke_width=4),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text("正在登录教师端，请稍候...", size=14),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        self.page.show_dialog(self.progress_dialog)

        # 重置状态
        self.login_success = False
        self.login_error = None
        self.login_event.clear()

        # 在后台线程中执行登录（复用答案提取的 Extractor.login）
        def login_task():
            try:
                self.extractor = Extractor()
                success = self.extractor.login(username, password)

                if success:
                    self.access_token = self.extractor.access_token

                    # 根据复选框状态保存凭据
                    if self.remember_password_checkbox.value:
                        self.settings_manager.set_teacher_credentials(username, password)
                    else:
                        self.settings_manager.clear_teacher_credentials()

                    self.login_success = True
                    self.login_error = None
                else:
                    self.login_success = False
                    self.login_error = "用户名或密码错误"
            except Exception as ex:
                self.login_success = False
                self.login_error = str(ex)
            finally:
                self.login_event.set()

        threading.Thread(target=login_task, daemon=True).start()

        # 在主线程中等待并更新 UI
        async def check_login():
            while not self.login_event.is_set():
                await asyncio.sleep(0.1)

            # 关闭加载对话框
            self.progress_dialog.open = False
            self.page.update()

            if self.login_success and not self.login_error:
                # 登录成功：建立 API 客户端并进入项目列表屏
                self.api_client = LazyGradingAPIClient(self.access_token)
                # 进入列表前重置分页/搜索状态
                self.page_index = 1
                self.key_word = ""
                self.total_count = 0
                self.project_list = []
                self.list_error = None
                self.current_content.content = self._get_project_list_content()
                self.page.update()
                # 后台拉取首页数据
                self._load_projects()
            else:
                # 登录失败，显示错误
                dialog = ft.AlertDialog(
                    title=ft.Text("错误"),
                    content=ft.Text(self.login_error or "未知错误"),
                    actions=[
                        ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(dialog)

        self.page.run_task(check_login)

    # ==================== 项目列表屏 ====================

    def _get_project_list_content(self) -> ft.Column:
        """获取项目列表屏内容（搜索 + 列表 + 分页）"""
        # 搜索框（回车触发搜索）
        self.search_field = ft.TextField(
            hint_text="搜索项目名称或班级名称",
            value=self.key_word,
            prefix_icon=ft.Icons.SEARCH,
            border_radius=Radius.SMALL,
            on_submit=lambda e: self._on_search_submit(e),
            expand=True,
        )

        # 每页条数下拉框
        self.page_size_dropdown = ft.Dropdown(
            label="每页",
            value=str(self.page_size),
            width=130,
            options=[
                ft.dropdown.Option("10"),
                ft.dropdown.Option("20"),
                ft.dropdown.Option("50"),
            ],
            on_select=lambda e: self._on_page_size_change(e),
        )

        # 计数文本（局部刷新时更新）
        self.count_text = ft.Text(self._count_text_value(), size=13, color=Palette.TEXT_MUTED)

        # 列表容器（局部刷新时替换其 controls）
        self.list_container = ft.Column(spacing=12)
        self._fill_list_container()

        # 分页控件
        self.prev_btn = secondary_button("上一页", ft.Icons.CHEVRON_LEFT, lambda e: self._on_prev_page(e))
        self.next_btn = secondary_button("下一页", ft.Icons.CHEVRON_RIGHT, lambda e: self._on_next_page(e))
        self.page_text = ft.Text(self._page_text_value(), size=13, color=Palette.TEXT_MUTED)
        self._apply_pagination_state()

        return ft.Column(
            [
                page_heading(
                    "产教融合项目",
                    "选择需要 AI 评分的产教融合项目",
                    ft.Icons.FOLDER_OUTLINED,
                ),
                # 工具栏：搜索 + 每页条数
                surface_card(
                    ft.Row(
                        [
                            self.search_field,
                            ft.IconButton(
                                icon=ft.Icons.SEARCH,
                                tooltip="搜索",
                                icon_color=Palette.PRIMARY,
                                on_click=lambda e: self._on_search_submit(e),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                tooltip="清空",
                                icon_color=Palette.TEXT_MUTED,
                                on_click=lambda e: self._on_clear_search(e),
                            ),
                            ft.Container(
                                content=self.page_size_dropdown,
                                padding=ft.Padding.only(top=4),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=16,
                ),
                # 计数 + 返回首页
                ft.Row(
                    [
                        self.count_text,
                        ft.Container(expand=True),
                        secondary_button("返回首页", ft.Icons.HOME, lambda e: self._on_back_click(e)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # 列表区
                self.list_container,
                # 分页行
                ft.Row(
                    [
                        self.prev_btn,
                        self.page_text,
                        self.next_btn,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
            ],
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _count_text_value(self) -> str:
        """计数文案"""
        return f"共 {self.total_count} 个项目"

    def _page_text_value(self) -> str:
        """分页文案"""
        total_pages = self._total_pages()
        return f"第 {self.page_index} / {total_pages} 页"

    def _total_pages(self) -> int:
        """总页数（至少 1）"""
        if self.page_size <= 0:
            return 1
        return max(1, math.ceil(self.total_count / self.page_size))

    def _fill_list_container(self):
        """根据当前状态填充列表区控件（加载中 / 错误 / 空态 / 卡片列表）"""
        if self.list_container is None:
            return

        if self.list_loading:
            self.list_container.controls = [
                ft.Row(
                    [ft.ProgressRing(stroke_width=4)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Text(
                    "正在加载项目列表...",
                    size=13,
                    color=Palette.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
            return

        if self.list_error:
            self.list_container.controls = [
                surface_card(
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.ERROR_OUTLINE, size=30, color=Palette.DANGER),
                            ft.Text(
                                self.list_error,
                                size=13,
                                color=Palette.TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            primary_button(
                                "重试",
                                ft.Icons.REFRESH,
                                lambda e: self._load_projects(),
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=24,
                )
            ]
            return

        if not self.project_list:
            self.list_container.controls = [
                surface_card(
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.INBOX_OUTLINED, size=30, color=Palette.TEXT_SOFT),
                            ft.Text(
                                "没有符合条件的产教融合项目",
                                size=13,
                                color=Palette.TEXT_MUTED,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=24,
                )
            ]
            return

        self.list_container.controls = [
            self._build_project_card(p) for p in self.project_list
        ]

    def _apply_pagination_state(self):
        """根据当前页码/总数更新分页按钮禁用态与文案"""
        if self.prev_btn is not None:
            self.prev_btn.disabled = self.list_loading or self.page_index <= 1
        if self.next_btn is not None:
            self.next_btn.disabled = self.list_loading or self.page_index >= self._total_pages()
        if self.page_text is not None:
            self.page_text.value = self._page_text_value()

    def _build_project_card(self, p: ClassProject) -> ft.Control:
        """构建单条项目卡片（参照 course_certification_view 的 GestureDetector 卡片）"""
        # 状态颜色：进行中(code=3)→ACCENT，其他→TEXT_MUTED
        if p.status_code == 3:
            status_color, status_bgcolor = Palette.ACCENT, Palette.ACCENT_SOFT
        else:
            status_color, status_bgcolor = Palette.TEXT_MUTED, Palette.SURFACE_ALT

        status_chip_ctl = (
            status_chip(p.status_str or "未知", color=status_color, bgcolor=status_bgcolor)
            if p.status_str
            else ft.Container()
        )

        subtitle_parts = [part for part in [p.class_name, p.project_type_name] if part]
        subtitle = " · ".join(subtitle_parts) if subtitle_parts else "—"

        # 进度统计 chip 行
        def count_chip(label: str, value: int, color: str, bgcolor: str) -> ft.Control:
            return status_chip(
                f"{label} {value}",
                color=color,
                bgcolor=bgcolor,
            )

        counts_row = ft.Row(
            [
                count_chip("进行中", p.jing_xing_count, Palette.PRIMARY, Palette.PRIMARY_SOFT),
                count_chip("待审批", p.to_sp_count, Palette.WARNING, Palette.WARNING_SOFT),
                count_chip("已完成", p.has_ok_count, Palette.ACCENT, Palette.ACCENT_SOFT),
                count_chip("共", p.class_count, Palette.TEXT_MUTED, Palette.SURFACE_ALT),
            ],
            spacing=8,
            wrap=True,
            run_spacing=6,
        )

        card = ft.GestureDetector(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(
                                        ft.Icons.WORK_OUTLINE,
                                        color=Palette.PRIMARY,
                                        size=22,
                                    ),
                                    width=45,
                                    height=45,
                                    alignment=ft.Alignment(0, 0),
                                    bgcolor=Palette.PRIMARY_SOFT,
                                    border_radius=Radius.SMALL,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            p.pro_name or "未命名项目",
                                            weight=ft.FontWeight.W_600,
                                            size=15,
                                            color=Palette.TEXT,
                                            max_lines=2,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            subtitle,
                                            size=12,
                                            color=Palette.TEXT_MUTED,
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                    ],
                                    spacing=4,
                                    expand=True,
                                ),
                                status_chip_ctl,
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=1, color=Palette.BORDER),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.SCHEDULE, size=14, color=Palette.TEXT_SOFT),
                                ft.Text(
                                    p.time_window or "时间未设置",
                                    size=12,
                                    color=Palette.TEXT_SOFT,
                                ),
                                ft.Container(expand=True),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        counts_row,
                    ],
                    spacing=10,
                ),
                padding=16,
                bgcolor=Palette.SURFACE,
                border=ft.border.all(1, Palette.BORDER),
                border_radius=Radius.MEDIUM,
            ),
            on_tap=lambda e, project=p: self._on_project_click(e, project),
            mouse_cursor=ft.MouseCursor.CLICK,
        )
        return card

    # ==================== 列表数据加载与刷新 ====================

    def _load_projects(self):
        """触发后台加载项目列表（先展示加载态，再后台取数）"""
        if self.api_client is None:
            return
        self.list_loading = True
        self.list_error = None
        self._refresh_list_area()
        self._run_background(self._fetch_projects)

    def _fetch_projects(self):
        """后台执行：调用 API 获取当前页项目"""
        try:
            items, total = self.api_client.get_class_projects(
                page_index=self.page_index,
                page_size=self.page_size,
                key_word=self.key_word,
                class_status=self.class_status,
            )
            self.project_list = items
            self.total_count = total
            self.list_error = None
        except Exception as ex:
            self.list_error = str(ex)
            self.project_list = []
        finally:
            self.list_loading = False
            self._refresh_list_area()

    def _refresh_list_area(self):
        """局部刷新列表屏的动态区域（不重建整屏，保留搜索框焦点）"""
        self._fill_list_container()
        self._apply_pagination_state()
        if self.count_text is not None:
            self.count_text.value = self._count_text_value()
        try:
            self.page.update()
        except Exception:
            pass

    # ==================== 搜索与分页事件 ====================

    def _on_search_submit(self, e):
        """搜索：读取关键字、回到第 1 页、重新加载"""
        self.key_word = (self.search_field.value or "").strip()
        self.page_index = 1
        self._load_projects()

    def _on_clear_search(self, e):
        """清空搜索"""
        self.key_word = ""
        if self.search_field is not None:
            self.search_field.value = ""
        self.page_index = 1
        self._load_projects()

    def _on_page_size_change(self, e):
        """改变每页条数：回到第 1 页、重新加载"""
        try:
            new_size = int(e.control.value)
        except (TypeError, ValueError):
            return
        if new_size == self.page_size:
            return
        self.page_size = new_size
        self.page_index = 1
        self._load_projects()

    def _on_prev_page(self, e):
        """上一页"""
        if self.list_loading or self.page_index <= 1:
            return
        self.page_index -= 1
        self._load_projects()

    def _on_next_page(self, e):
        """下一页"""
        if self.list_loading or self.page_index >= self._total_pages():
            return
        self.page_index += 1
        self._load_projects()

    def _on_project_click(self, e, project: ClassProject):
        """点击项目卡片 - 占位（AI 评分逻辑待开发）"""
        snack = ft.SnackBar(
            content=ft.Text(f"已选择：{project.pro_name}（AI 评分功能开发中）"),
            bgcolor=ft.Colors.ORANGE,
        )
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()
