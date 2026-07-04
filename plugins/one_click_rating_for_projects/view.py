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
from .models import ClassProject, ProjectResult
from .scoring import (
    calculate_score,
    CommentPicker,
    load_templates,
    save_templates,
    load_strictness,
    save_strictness,
    STRICTNESS_CONFIG,
    enforce_distribution_limits,
)


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

        # 学生成果屏状态
        self.current_project = None  # 当前选中的 ClassProject 实例
        self.result_list: list[ProjectResult] = []  # 当前项目的学生成果
        self.result_loading = False  # 成果列表加载中
        self.result_error = None  # 成果列表错误信息
        self.selected_result_ids: set[int] = set()  # 已选中的成果记录 ID

        # 成果屏动态控件引用
        self.result_list_view = None  # ft.ListView
        self.result_count_text = None  # 总人数统计文本
        self.result_action_column = None  # 右侧功能按钮面板容器
        # 右侧面板中需要随勾选状态动态更新的控件（持有引用以做定向刷新，
        # 避免每次点击学生都重建整块面板 + 触发整页 update 造成卡顿）
        self._stat_selected_text = None  # 「当前已选」数值文本
        self._grade_selected_btn = None  # 「评分已选学生」按钮（按已选数量切换禁用态）

        # 评分状态
        self._comment_picker = None  # CommentPicker 实例（评分会话内复用）
        self._grading_in_progress = False  # 防止重复触发
        self._student_card_refs: dict = {}  # {result_id: {'icon': Icon, 'container': Container}}
        self._strictness: str = load_strictness()  # 'high' / 'medium' / 'low'

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
                    "轮椅式批改 · 躺平也能把活干完 · 摸鱼神器 YYDS",
                    ft.Icons.AUTO_AWESOME,
                ),
                hero_panel(
                    "一眼丁真，发现混子",
                    "截图不够？字数凑？附件没交？通通拿捏。自动检测敷衍选手，精准识别摆烂达人，让混子无所遁形。",
                    action=start_button,
                    chips=[
                        status_chip(
                            "轮椅批改",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "一眼丁真",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "精准拿捏",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "拒绝内卷",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                    ],
                    icon=ft.Icons.AUTO_AWESOME,
                ),
                section_label("三步躺平批改法", "别人还在手动批改的时候，你已经摸完鱼了"),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            content=workflow_step(
                                "01",
                                "登个录",
                                "教师账号一键登录，告别翻车现场",
                                ft.Icons.PERSON_OUTLINE,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "02",
                                "选个班",
                                "选个项目开摆，支持搜索和筛选",
                                ft.Icons.FOLDER_OUTLINED,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "03",
                                "一键梭哈",
                                "AI 自动评分 + 批语，坐等收工就行",
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
        """点击项目卡片 → 切换到学生成果屏并后台拉取数据"""
        self.current_project = project
        self.result_list = []
        self.result_error = None
        self.selected_result_ids = set()
        self.current_content.content = self._get_project_results_content()
        self.page.update()
        self._load_results()

    # ==================== 学生成果屏 ====================

    def _get_project_results_content(self) -> ft.Column:
        """
        获取学生成果屏内容：左右分栏布局
        - 左侧：学生成果列表（可滚动，可勾选）
        - 右侧：统计摘要 + 功能操作按钮
        """
        project = self.current_project
        title = project.pro_name if project else "项目成果"
        subtitle = (
            f"{project.class_name} · {project.time_window}"
            if project
            else ""
        )

        # ---------- 左侧：学生列表 ----------
        # 总人数统计文本（局部刷新时更新）
        self.result_count_text = ft.Text(
            self._result_count_value(), size=13, color=Palette.TEXT_MUTED
        )
        # ListView 容器（独立滚动）
        self.result_list_view = ft.ListView(expand=True, spacing=10, padding=0)
        self._fill_result_list_view()

        left_panel = surface_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "学生提交列表",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=Palette.TEXT,
                            ),
                            ft.Container(expand=True),
                            self.result_count_text,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Divider(height=1, color=Palette.BORDER),
                    self.result_list_view,
                ],
                spacing=12,
                expand=True,
            ),
            padding=18,
        )
        left_panel.expand = 2

        # ---------- 右侧：功能按钮面板 ----------
        self.result_action_column = self._build_result_action_panel()
        right_panel = ft.Column(
            [
                self.result_action_column,
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=1,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        return ft.Column(
            [
                page_heading(
                    title,
                    subtitle or "查看学生提交的项目成果",
                    ft.Icons.GROUP_OUTLINED,
                ),
                ft.Row(
                    [
                        secondary_button(
                            "返回项目列表",
                            ft.Icons.ARROW_BACK,
                            lambda ev: self._back_to_project_list(ev),
                        ),
                        ft.Container(expand=True),
                        secondary_button(
                            "刷新",
                            ft.Icons.REFRESH,
                            lambda ev: self._load_results(),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [left_panel, right_panel],
                    height=620,
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _result_count_value(self) -> str:
        """左侧列表头的统计文案"""
        total = len(self.result_list)
        selected = len(self.selected_result_ids)
        if selected > 0:
            return f"共 {total} 人 · 已选 {selected} 人"
        return f"共 {total} 人"

    # ---------- 列表填充与局部刷新 ----------

    def _fill_result_list_view(self):
        """用当前状态（加载中/错误/空态/卡片列表）填充左侧 ListView"""
        if self.result_list_view is None:
            return
        self._student_card_refs.clear()  # 重建前清空旧引用

        if self.result_loading:
            self.result_list_view.controls = [
                ft.Row(
                    [ft.ProgressRing(stroke_width=4)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Text(
                    "正在加载学生成果...",
                    size=13,
                    color=Palette.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
            return

        if self.result_error:
            self.result_list_view.controls = [
                ft.Column(
                    [
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=30, color=Palette.DANGER),
                        ft.Text(
                            self.result_error,
                            size=13,
                            color=Palette.TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        primary_button(
                            "重试",
                            ft.Icons.REFRESH,
                            lambda ev: self._load_results(),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                )
            ]
            return

        if not self.result_list:
            self.result_list_view.controls = [
                ft.Column(
                    [
                        ft.Icon(ft.Icons.INBOX_OUTLINED, size=30, color=Palette.TEXT_SOFT),
                        ft.Text(
                            "暂无学生提交记录",
                            size=13,
                            color=Palette.TEXT_MUTED,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                )
            ]
            return

        self.result_list_view.controls = [
            self._build_student_card(r) for r in self.result_list
        ]

    def _refresh_results_area(self):
        """局部刷新成果屏的动态区域（列表 + 统计 + 右侧面板）"""
        self._fill_result_list_view()
        if self.result_count_text is not None:
            self.result_count_text.value = self._result_count_value()
        if self.result_action_column is not None:
            new_panel = self._build_result_action_panel()
            self.result_action_column.controls = new_panel.controls
        try:
            self.page.update()
        except Exception:
            pass

    # ---------- 数据加载 ----------

    def _load_results(self):
        """触发后台加载学生成果（先展示加载态，再后台取数）"""
        if self.api_client is None or self.current_project is None:
            return
        self.result_loading = True
        self.result_error = None
        self._refresh_results_area()
        self._run_background(self._fetch_results)

    def _fetch_results(self):
        """后台执行：调用 API 获取当前项目的学生成果"""
        try:
            project = self.current_project
            items = self.api_client.get_class_project_result(
                source_id=project.source_id,
                class_id=project.class_id,
                project_id=project.project_id,
            )
            self.result_list = items
            self.result_error = None
        except Exception as ex:
            self.result_error = str(ex)
            self.result_list = []
        finally:
            self.result_loading = False
            # 持久化的选择可能已不在列表里，清理一下
            existing_ids = {r.id for r in self.result_list}
            self.selected_result_ids &= existing_ids
            self._refresh_results_area()

    # ---------- 学生卡片 ----------

    def _build_student_card(self, r: ProjectResult) -> ft.Control:
        """构建单条学生成果卡片（带左侧勾选图标，整体可点击切换选择）"""
        selected = r.id in self.selected_result_ids

        # 选择状态图标（被动图标，点击由外层 GestureDetector 处理，
        # 避免 Checkbox + GestureDetector 双事件 toggle 冲突）
        check_icon = ft.Icon(
            ft.Icons.CHECK_BOX if selected else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
            size=22,
            color=Palette.PRIMARY if selected else Palette.TEXT_SOFT,
        )

        # 头像占位：姓名首字
        avatar = ft.Container(
            content=ft.Text(
                r.initial,
                size=15,
                weight=ft.FontWeight.BOLD,
                color=Palette.SURFACE,
            ),
            width=40,
            height=40,
            alignment=ft.Alignment(0, 0),
            bgcolor=Palette.PRIMARY,
            border_radius=Radius.SMALL,
        )

        # "混子"标签：评分后恰好为保底分的学生
        is_slacker = r.is_graded and r.pro_score == 70
        name_controls = [
            ft.Text(
                r.student_name or "未知",
                size=14,
                weight=ft.FontWeight.W_600,
                color=Palette.TEXT,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ]
        if is_slacker:
            name_controls.append(
                ft.Container(
                    content=ft.Text(
                        "混子",
                        size=10,
                        color=Palette.SURFACE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    bgcolor=Palette.DANGER,
                    border_radius=12,
                ),
            )

        # 左侧文本区
        name_col = ft.Column(
            [
                ft.Row(
                    name_controls,
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    f"学号: {r.student_id[:8]}…" if len(r.student_id) > 8 else f"学号: {r.student_id}",
                    size=11,
                    color=Palette.TEXT_SOFT,
                ),
            ],
            spacing=2,
            expand=True,
        )

        # 右侧状态 chips
        if r.is_graded:
            # 已评分：直接显示分数，状态标为"已评分"
            score_color, score_bg = Palette.ACCENT, Palette.ACCENT_SOFT
            score_label = f"评分 {r.pro_score}"
            status_label = "已评分"
            status_color, status_bg = Palette.ACCENT, Palette.ACCENT_SOFT
        else:
            # 未评分：分数区显示"—"，状态标为"待评分"
            score_color, score_bg = Palette.TEXT_MUTED, Palette.SURFACE_ALT
            score_label = "—"
            status_label = "待评分"
            status_color, status_bg = Palette.WARNING, Palette.WARNING_SOFT
        status_chip_ctl = status_chip(status_label, color=status_color, bgcolor=status_bg)
        score_chip_ctl = status_chip(score_label, color=score_color, bgcolor=score_bg)

        chips_col = ft.Column(
            [status_chip_ctl, score_chip_ctl],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.END,
        )

        # 提交时间（小字）
        submit_text = ft.Text(
            r.submit_date or "未提交",
            size=11,
            color=Palette.TEXT_SOFT,
        )

        card_bg = Palette.PRIMARY_SOFT if selected else Palette.SURFACE
        card_border = Palette.PRIMARY if selected else Palette.BORDER

        # 提取容器为变量，以便后续单独更新属性（不重建控件）
        container = ft.Container(
            content=ft.Row(
                [
                    check_icon,
                    avatar,
                    ft.VerticalDivider(width=1, color=Palette.BORDER),
                    name_col,
                    ft.Column(
                        [submit_text, chips_col],
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            bgcolor=card_bg,
            border=ft.border.all(1, card_border),
            border_radius=Radius.MEDIUM,
        )
        # 存储引用供 _update_single_card 使用
        self._student_card_refs[r.id] = {"icon": check_icon, "container": container}

        card = ft.GestureDetector(
            content=container,
            on_tap=lambda ev, rid=r.id: self._on_student_check(ev, rid),
            mouse_cursor=ft.MouseCursor.CLICK,
        )
        return card

    # ---------- 右侧功能面板 ----------

    def _build_result_action_panel(self) -> ft.Column:
        """构建右侧统计摘要 + 快速选择 + 功能操作按钮面板"""
        total = len(self.result_list)
        graded = sum(1 for r in self.result_list if r.is_graded)
        ungraded = total - graded
        completed = sum(1 for r in self.result_list if r.project_progress >= 100)
        selected = len(self.selected_result_ids)

        # 「当前已选」数值需要随勾选实时变化，持有引用以便局部刷新
        self._stat_selected_text = ft.Text(
            str(selected), size=14, weight=ft.FontWeight.W_600, color=Palette.TEXT
        )

        # 统计摘要卡片
        stats_card = surface_card(
            ft.Column(
                [
                    ft.Text(
                        "统计概览",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=Palette.TEXT,
                    ),
                    ft.Divider(height=1, color=Palette.BORDER),
                    _stat_row("总提交人数", str(total)),
                    _stat_row("已评分", str(graded)),
                    _stat_row("未评分", str(ungraded)),
                    _stat_row("进度100%", str(completed)),
                    ft.Divider(height=1, color=Palette.BORDER),
                    ft.Row(
                        [
                            ft.Text("当前已选", size=13, color=Palette.TEXT_MUTED),
                            ft.Container(expand=True),
                            self._stat_selected_text,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
            ),
            padding=18,
        )

        # ---- 操作按钮 ----
        grade_all_btn = primary_button(
            "一键 AI 评分（全部）",
            ft.Icons.AUTO_AWESOME,
            lambda ev: self._on_grade_all_click(ev),
            width=280,
        )
        # 持有引用：勾选状态变化时只改 disabled 属性，不重建按钮
        self._grade_selected_btn = ft.FilledButton(
            "评分已选学生",
            icon=ft.Icons.CHECKLIST,
            width=280,
            disabled=selected == 0,
            bgcolor=Palette.PRIMARY,
            color=Palette.SURFACE,
            on_click=lambda ev: self._on_grade_selected_click(ev),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=24, vertical=16),
                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
            ),
        )

        # ---- 快速选择按钮组 ----
        select_section = ft.Column(
            [
                ft.Text(
                    "快速选择",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=Palette.TEXT,
                ),
                ft.Row(
                    [
                        _quick_btn(
                            "全选",
                            ft.Icons.CHECKLIST_RTL,
                            lambda ev: self._on_select_all(ev),
                        ),
                        _quick_btn(
                            "取消选择",
                            ft.Icons.CLEAR_ALL,
                            lambda ev: self._on_deselect_all(ev),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                    run_spacing=8,
                ),
                ft.Row(
                    [
                        _quick_btn(
                            f"未评分（{ungraded}）",
                            ft.Icons.HOURGLASS_EMPTY,
                            lambda ev: self._on_select_ungraded(ev),
                        ),
                        _quick_btn(
                            f"进度100%（{completed}）",
                            ft.Icons.TASK_ALT,
                            lambda ev: self._on_select_completed(ev),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                    run_spacing=8,
                ),
            ],
            spacing=10,
        )

        refresh_btn = secondary_button(
            "刷新列表",
            ft.Icons.REFRESH,
            lambda ev: self._load_results(),
            width=280,
        )
        comment_settings_btn = secondary_button(
            "设置",
            ft.Icons.SETTINGS,
            lambda ev: self._show_comment_settings(ev),
            width=280,
        )

        return ft.Column(
            [
                stats_card,
                ft.Divider(height=1, color=Palette.BORDER),
                select_section,
                ft.Divider(height=1, color=Palette.BORDER),
                grade_all_btn,
                self._grade_selected_btn,
                ft.Divider(height=1, color=Palette.BORDER),
                refresh_btn,
                comment_settings_btn,
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    # ---------- 选择与功能按钮事件 ----------

    def _update_single_card(self, result_id: int):
        """只更新指定卡片的图标和背景色（不重建控件）"""
        refs = self._student_card_refs.get(result_id)
        if not refs:
            return
        selected = result_id in self.selected_result_ids
        refs["icon"].name = ft.Icons.CHECK_BOX if selected else ft.Icons.CHECK_BOX_OUTLINE_BLANK
        refs["icon"].color = Palette.PRIMARY if selected else Palette.TEXT_SOFT
        refs["container"].bgcolor = Palette.PRIMARY_SOFT if selected else Palette.SURFACE
        refs["container"].border = ft.border.all(1, Palette.PRIMARY if selected else Palette.BORDER)

    def _sync_all_cards(self):
        """批量同步所有卡片的选中状态（不重建控件）"""
        for rid in self._student_card_refs:
            self._update_single_card(rid)

    def _update_selection_stats(self):
        """
        只更新随勾选状态变化的动态控件属性（不重建右侧面板）。

        重建整块面板会创建十余个控件，再配合 page.update() 触发整页 diff，
        是学生列表点击卡顿的主因。这里改为只改属性，由调用方决定推送范围。
        """
        selected = len(self.selected_result_ids)
        if self.result_count_text is not None:
            self.result_count_text.value = self._result_count_value()
        if self._stat_selected_text is not None:
            self._stat_selected_text.value = str(selected)
        if self._grade_selected_btn is not None:
            self._grade_selected_btn.disabled = selected == 0

    @staticmethod
    def _safe_update(ctrl) -> None:
        """单控件定向推送；任何单个控件更新失败不影响其他控件。"""
        if ctrl is None:
            return
        try:
            ctrl.update()
        except Exception:
            pass

    def _on_student_check(self, e, result_id: int):
        """学生卡片点击切换勾选（逐控件定向推送，不触发整页 update）"""
        if result_id in self.selected_result_ids:
            self.selected_result_ids.discard(result_id)
        else:
            self.selected_result_ids.add(result_id)
        self._update_single_card(result_id)
        self._update_selection_stats()
        # 关键：图标是叶子控件，必须显式 icon.update() 才会刷新 name/color。
        # 用 page.update(container) 在部分 Flet 版本下不会把嵌套在列表里的子控件
        # 属性变更下发（list diff 只识别增删移动），导致复选框空心→实心不生效。
        # 逐个 control.update() 是 Flet 官方推荐写法，最稳。
        refs = self._student_card_refs.get(result_id, {})
        self._safe_update(refs.get("icon"))
        self._safe_update(refs.get("container"))
        self._safe_update(self.result_count_text)
        self._safe_update(self._stat_selected_text)
        self._safe_update(self._grade_selected_btn)

    def _on_select_all(self, e):
        """全选"""
        self.selected_result_ids = {r.id for r in self.result_list}
        self._sync_all_cards()
        self._update_selection_stats()
        self.page.update()

    def _on_deselect_all(self, e):
        """取消全部选择"""
        self.selected_result_ids.clear()
        self._sync_all_cards()
        self._update_selection_stats()
        self.page.update()

    def _on_select_ungraded(self, e):
        """选取未评分的学生（pro_score 为 0）"""
        self.selected_result_ids = {r.id for r in self.result_list if not r.is_graded}
        self._sync_all_cards()
        self._update_selection_stats()
        self.page.update()

    def _on_select_completed(self, e):
        """选取项目进度 100% 且未评分的学生"""
        self.selected_result_ids = {
            r.id for r in self.result_list
            if r.project_progress >= 100 and not r.is_graded
        }
        self._sync_all_cards()
        self._update_selection_stats()
        self.page.update()

    def _on_strictness_change(self, e):
        """严格度变更"""
        self._strictness = e.control.value or "high"
        save_strictness(self._strictness)

    def _on_grade_all_click(self, e):
        """一键 AI 评分（全部）→ 筛选未评分 + 进度100% 的学生"""
        targets = [
            r for r in self.result_list
            if not r.is_graded and r.project_progress >= 100
        ]
        if not targets:
            snack = ft.SnackBar(
                content=ft.Text("没有需要评分的学生（进度不足或已全部评分）"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return
        self._show_grade_confirm(targets)

    def _on_grade_selected_click(self, e):
        """评分已选学生 → 筛选已选 + 未评分 + 进度100%"""
        targets = [
            r for r in self.result_list
            if r.id in self.selected_result_ids
            and not r.is_graded
            and r.project_progress >= 100
        ]
        if not targets:
            snack = ft.SnackBar(
                content=ft.Text("选中的学生中没有需要评分的"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return
        self._show_grade_confirm(targets)

    # ---------- 评分确认弹窗 ----------

    def _show_grade_confirm(self, targets: list[ProjectResult]):
        """显示评分确认弹窗"""
        cfg = STRICTNESS_CONFIG.get(self._strictness, STRICTNESS_CONFIG["high"])
        label = cfg["label"]
        floor = cfg["floor"]
        low, high = cfg["tier3"]

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("确认开始 AI 评分"),
            content=ft.Column(
                [
                    ft.Text(f"即将为 {len(targets)} 名学生自动评分", size=14),
                    ft.Divider(height=6, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        f"当前严格度：{label}（{floor} ~ {high}）",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=Palette.PRIMARY,
                    ),
                    ft.Text("评分规则：", size=12, weight=ft.FontWeight.W_600),
                    ft.Text(f"• 分数范围：{floor} ~ {high}", size=12),
                    ft.Text(f"• 截图>9 或 字数>500 → {low}~{high}", size=12),
                    ft.Text("• 截图≥6 或 字数≥400 → 中间档", size=12),
                    ft.Text(f"• 最低要求不满足 → 保底 {floor}", size=12),
                    ft.Text("• 无附件有额外上限", size=12),
                    ft.Text("• ≥80分评语≥20字，≥95分评语≥100字", size=12),
                ],
                tight=True,
                spacing=4,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                ft.ElevatedButton(
                    "开始评分",
                    bgcolor=Palette.PRIMARY,
                    color=Palette.SURFACE,
                    on_click=lambda _: self._start_grading(confirm_dialog, targets),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(confirm_dialog)

    # ---------- 评分工作流 ----------

    def _start_grading(self, confirm_dialog, targets: list[ProjectResult]):
        """关闭确认弹窗，展示进度弹窗，后台执行评分任务"""
        if self._grading_in_progress:
            return
        self.page.pop_dialog()

        if self._comment_picker is None:
            self._comment_picker = CommentPicker()

        self._grading_in_progress = True
        strictness = self._strictness  # 快照，评中途改设置不影响本轮
        needs_distribution = strictness != "high"
        floor_score = STRICTNESS_CONFIG[strictness]["floor"]

        # 进度弹窗
        self._grading_progress_text = ft.Text(
            "准备开始评分...", size=13, text_align=ft.TextAlign.CENTER
        )
        progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("AI 评分中"),
            content=ft.Column(
                [
                    ft.ProgressRing(stroke_width=3),
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    self._grading_progress_text,
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                width=360,
            ),
        )
        self.page.show_dialog(progress_dialog)

        def grading_task():
            total = len(targets)
            stats = {
                "total": total,
                "graded": 0,
                "failed": 0,
                "min_score_names": [],
                "failed_names": [],
            }

            try:
                # ── 阶段一：逐个拉取详情 + 计算分数 ──
                analyzed: list[dict] = []
                for i, student in enumerate(targets, 1):
                    name = student.student_name or "未知"
                    self._grading_progress_text.value = (
                        f"正在分析：{name}（{i}/{total}）"
                    )
                    try:
                        self.page.update()
                    except Exception:
                        pass

                    try:
                        detail = self.api_client.get_student_result_with_logs(
                            student.id
                        )
                        student.commit_logs_raw = detail.get("commitLogs") or []

                        score = calculate_score(
                            screenshot_count=student.screenshot_count,
                            desc_char_count=student.desc_char_count,
                            has_attachment=student.has_attachment,
                            log_stage_count=student.log_stage_count,
                            log_total_chars=student.log_total_chars,
                            strictness=strictness,
                        )
                        analyzed.append({"student": student, "score": score})
                    except Exception as ex:
                        stats["failed"] += 1
                        stats["failed_names"].append(f"{name}（{ex}）")

                # ── 阶段二：应用分布限制（中等/宽松档） ──
                if needs_distribution and analyzed:
                    self._grading_progress_text.value = "正在调整分数分布..."
                    try:
                        self.page.update()
                    except Exception:
                        pass
                    analyzed = enforce_distribution_limits(analyzed)

                # ── 阶段三：逐个提交评分 ──
                for i, item in enumerate(analyzed, 1):
                    student = item["student"]
                    score = item["score"]
                    name = student.student_name or "未知"

                    self._grading_progress_text.value = (
                        f"正在提交：{name}（{i}/{len(analyzed)}）"
                    )
                    try:
                        self.page.update()
                    except Exception:
                        pass

                    try:
                        min_len = 100 if score >= 95 else 20 if score >= 80 else 0
                        comment = self._comment_picker.next(min_len=min_len)
                        self.api_client.audit_result(
                            rid=student.id,
                            pro_score=str(score),
                            review_comments=comment,
                        )
                        student.pro_score = score
                        student.review_comments = comment

                        stats["graded"] += 1
                        if score == floor_score:
                            stats["min_score_names"].append(name)
                    except Exception as ex:
                        stats["failed"] += 1
                        stats["failed_names"].append(f"{name}（{ex}）")

                    self._refresh_results_area()

            finally:
                self._grading_in_progress = False
                try:
                    progress_dialog.open = False
                    self.page.update()
                except Exception:
                    pass
                self._show_grading_completion(stats, floor_score)

        self._run_background(grading_task)

    # ---------- 评分完成弹窗 ----------

    def _show_grading_completion(self, stats: dict, floor_score: int = 70):
        """显示评分完成弹窗，75 分保底学生着重高亮"""
        controls = [
            ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.ACCENT, size=22),
                    ft.Text(
                        f"评分完成！共成功 {stats['graded']} 名",
                        size=15,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]

        if stats["failed"] > 0:
            controls.append(ft.Divider(height=4, color=ft.Colors.TRANSPARENT))
            controls.append(
                ft.Text(
                    f"⚠️ {stats['failed']} 名学生评分失败：",
                    size=12,
                    color=Palette.DANGER,
                )
            )
            for fname in stats["failed_names"][:10]:  # 最多显示10条
                controls.append(
                    ft.Text(f"  • {fname}", size=11, color=Palette.DANGER)
                )

        if stats["min_score_names"]:
            controls.append(ft.Divider(height=4, color=ft.Colors.TRANSPARENT))
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.WARNING_AMBER,
                                        color=Palette.DANGER,
                                        size=18,
                                    ),
                                    ft.Text(
                                        f"以下 {len(stats['min_score_names'])} 名学生"
                                        f"未达最低要求，给予保底分数（{floor_score}分）：",
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                        color=Palette.DANGER,
                                    ),
                                ],
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            *[
                                ft.Text(
                                    f"  • {name}",
                                    size=12,
                                    color=Palette.DANGER,
                                    weight=ft.FontWeight.W_500,
                                )
                                for name in stats["min_score_names"]
                            ],
                        ],
                        spacing=4,
                    ),
                    padding=12,
                    bgcolor="#FDE8ED",
                    border=ft.border.all(1, Palette.DANGER),
                    border_radius=Radius.SMALL,
                )
            )

        dialog = ft.AlertDialog(
            title=ft.Text("评分报告"),
            content=ft.Column(controls, tight=True, spacing=6, width=420),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    def _back_to_project_list(self, e):
        """返回项目列表屏"""
        self.current_project = None
        self.result_list = []
        self.selected_result_ids = set()
        self.result_error = None
        self.current_content.content = self._get_project_list_content()
        self.page.update()
        # 如果列表数据为空则刷新
        if not self.project_list:
            self._load_projects()

    # ---------- 设置弹窗（严格度 + 评语列表管理） ----------

    def _show_comment_settings(self, e):
        """显示设置弹窗：严格度 + 短/长评语模板列表"""
        from .scoring import STRICTNESS_CONFIG

        templates = load_templates()

        # 严格度下拉框
        strictness_dd = ft.Dropdown(
            value=self._strictness,
            options=[
                ft.dropdown.Option("high", "严格（70 ~ 90）"),
                ft.dropdown.Option("medium", "中等（70 ~ 95）"),
                ft.dropdown.Option("low", "宽松（70 ~ 100）"),
            ],
            width=220,
        )

        # ---- 短评语列表 ----
        short_column = ft.Column(spacing=6)
        for i, text in enumerate(templates.get("short", [])):
            short_column.controls.append(
                self._build_template_item("short", i, text)
            )

        # ---- 长评语列表 ----
        long_column = ft.Column(spacing=6)
        for i, text in enumerate(templates.get("long", [])):
            long_column.controls.append(
                self._build_template_item("long", i, text)
            )

        # 关闭时保存严格度
        def on_close(_):
            self._strictness = strictness_dd.value or "high"
            save_strictness(self._strictness)
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text("设置"),
            content=ft.Container(
                content=ft.Column(
                    [
                        # ---- 严格度 ----
                        ft.Row(
                            [
                                ft.Text(
                                    "批改严格度",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(expand=True),
                                strictness_dd,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=4),
                        # ---- 短评语 ----
                        ft.Row(
                            [
                                ft.Text(
                                    "短评语模板（< 95 分使用）",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "＋ 添加",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda ev: self._add_template("short"),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        short_column,
                        ft.Divider(height=4),
                        # ---- 长评语 ----
                        ft.Row(
                            [
                                ft.Text(
                                    "长评语模板（≥ 95 分使用，≥ 100 字）",
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "＋ 添加",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda ev: self._add_template("long"),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        long_column,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=600,
                padding=6,
            ),
            actions=[
                ft.ElevatedButton(
                    "关闭",
                    bgcolor=Palette.PRIMARY,
                    color=Palette.SURFACE,
                    on_click=on_close,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    def _build_template_item(
        self, pool: str, index: int, text: str
    ) -> ft.Container:
        """构建单条评语模板卡片（序号 + 预览 + 编辑/删除按钮）"""
        preview = text[:55] + ("..." if len(text) > 55 else "")
        return ft.Container(
            content=ft.Row(
                [
                    # 序号圆圈
                    ft.Container(
                        content=ft.Text(
                            str(index + 1),
                            size=10,
                            color=Palette.SURFACE,
                            weight=ft.FontWeight.BOLD,
                        ),
                        width=20,
                        height=20,
                        alignment=ft.Alignment(0, 0),
                        bgcolor=Palette.PRIMARY,
                        border_radius=10,
                    ),
                    # 预览文本
                    ft.Text(
                        preview,
                        size=12,
                        color=Palette.TEXT,
                        expand=True,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    # 操作按钮
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED,
                        icon_size=16,
                        icon_color=Palette.PRIMARY,
                        tooltip="编辑",
                        on_click=lambda ev, p=pool, i=index: self._edit_template(
                            p, i
                        ),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        icon_color=Palette.DANGER,
                        tooltip="删除",
                        on_click=lambda ev, p=pool, i=index: self._delete_template(
                            p, i
                        ),
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border=ft.border.all(1, Palette.BORDER),
            border_radius=Radius.SMALL,
        )

    def _edit_template(self, pool: str, index: int):
        """编辑单条评语（关闭设置弹窗 → 打开编辑弹窗 → 保存后返回设置弹窗）"""
        self.page.pop_dialog()
        templates = load_templates()
        current = templates.get(pool, [])[index] if index < len(templates.get(pool, [])) else ""

        field = ft.TextField(
            value=current,
            multiline=True,
            min_lines=3,
            max_lines=6,
            width=460,
            label="编辑评语",
        )

        def on_save(_):
            new_text = field.value.strip()
            if new_text:
                templates[pool][index] = new_text
                save_templates(templates)
                if self._comment_picker is not None:
                    self._comment_picker.reload()
            self.page.pop_dialog()
            self._show_comment_settings(None)

        def on_cancel(_):
            self.page.pop_dialog()
            self._show_comment_settings(None)

        dialog = ft.AlertDialog(
            title=ft.Text("编辑评语"),
            content=field,
            actions=[
                ft.TextButton("取消", on_click=on_cancel),
                ft.ElevatedButton(
                    "保存",
                    bgcolor=Palette.PRIMARY,
                    color=Palette.SURFACE,
                    on_click=on_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    def _add_template(self, pool: str):
        """新增一条评语（关闭设置弹窗 → 打开新增弹窗 → 保存后返回设置弹窗）"""
        self.page.pop_dialog()

        label = "短评语（≥20字）" if pool == "short" else "长评语（≥100字）"
        field = ft.TextField(
            value="",
            multiline=True,
            min_lines=3,
            max_lines=6,
            width=460,
            label=f"新增{label}",
            hint_text="请输入评语内容...",
        )

        def on_save(_):
            new_text = field.value.strip()
            if new_text:
                templates = load_templates()
                templates[pool].append(new_text)
                save_templates(templates)
                if self._comment_picker is not None:
                    self._comment_picker.reload()
            self.page.pop_dialog()
            self._show_comment_settings(None)

        def on_cancel(_):
            self.page.pop_dialog()
            self._show_comment_settings(None)

        dialog = ft.AlertDialog(
            title=ft.Text(f"新增{label}"),
            content=field,
            actions=[
                ft.TextButton("取消", on_click=on_cancel),
                ft.ElevatedButton(
                    "添加",
                    bgcolor=Palette.PRIMARY,
                    color=Palette.SURFACE,
                    on_click=on_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    def _delete_template(self, pool: str, index: int):
        """删除一条评语（直接删除并刷新设置弹窗）"""
        templates = load_templates()
        pool_list = templates.get(pool, [])
        if len(pool_list) <= 1:
            snack = ft.SnackBar(
                content=ft.Text("该类评语至少保留一条"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return
        pool_list.pop(index)
        save_templates(templates)
        if self._comment_picker is not None:
            self._comment_picker.reload()
        # 刷新设置弹窗
        self.page.pop_dialog()
        self._show_comment_settings(None)


def _stat_row(label: str, value: str) -> ft.Row:
    """统计面板中的一行 key-value（模块级函数，避免干扰类结构）。"""
    return ft.Row(
        [
            ft.Text(label, size=13, color=Palette.TEXT_MUTED),
            ft.Container(expand=True),
            ft.Text(value, size=14, weight=ft.FontWeight.W_600, color=Palette.TEXT),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _quick_btn(label: str, icon, on_click) -> ft.OutlinedButton:
    """快速选择区域的紧凑小按钮（模块级辅助函数）。"""
    return ft.OutlinedButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=Palette.TEXT,
            side=ft.BorderSide(1, Palette.BORDER_STRONG),
            shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.W_500),
        ),
    )
