"""
ZX Answering Assistant - 摸鱼速评助手视图模块

This module contains the UI components for the lazy AI grading page.
- 落地页：功能介绍 + 开始评分入口
- 登录页：复用答案提取的教师端登录框（Extractor.login）获取 Access Token
- 项目列表页：调用 GetTeacherClassProject 渲染产教融合项目列表（搜索 + 分页）
"""

import asyncio
import math
import re
import threading

import flet as ft

from src.core.config import get_settings_manager
from src.extraction.extractor import Extractor
from src.ui.components import (
    hero_panel,
    page_heading,
    primary_button,
    run_background_task,
    secondary_button,
    section_label,
    status_chip,
    surface_card,
    workflow_step,
)
from src.ui.theme import Fonts, Palette, Radius

from .api_client import LazyGradingAPIClient
from .excel_exporter import ExcelExporter
from .grading_service import GradingService
from .models import ClassProject, ProjectResult
from .template_service import TemplateService
from .widgets import (
    ResultPanelProps,
    build_batch_toolbar,
    build_grading_rules_content,
    build_project_card,
    build_result_action_panel,
    build_student_card,
    build_template_section,
)
from .scoring import (
    CommentPicker,
    load_templates,
    load_strictness,
    save_strictness,
    STRICTNESS_CONFIG,
    MINIMUM_NOT_MET_SCORE,
)


class LazyAIGradingView:
    """摸鱼速评助手页面视图"""

    def __init__(self, page: ft.Page, main_app=None, context=None):
        """
        初始化摸鱼速评助手视图

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
        # 右侧面板中需要随勾选状态动态更新的控件（持有引用以直接改属性，
        # 避免每次点击学生都重建整块面板造成卡顿；最后用一次 page.update() 推送）
        self._stat_selected_text = None  # 「当前已选」数值文本
        self._grade_selected_btn = None  # 「评分已选学生」按钮（按已选数量切换禁用态）

        # 评分状态
        self._comment_picker = None  # CommentPicker 实例（评分会话内复用）
        self._grading_in_progress = False  # 防止重复触发
        self._student_card_refs: dict = {}  # {result_id: {'icon': Icon, 'container': Container}}
        self._strictness: str = load_strictness()  # 'high' / 'medium' / 'low'

        # 项目批量评分多选状态（跨页保持，按 ClassProject.source_id 去重）
        self.selected_projects: dict[int, ClassProject] = {}
        self._batch_count_text = None  # 「已选 N 个项目」文本控件引用
        self._batch_grade_btn = None   # 「批量评分」按钮引用（按已选数切禁用态）

        # 设置管理器
        self.settings_manager = get_settings_manager()

    # ==================== 内容入口 ====================

    def get_content(self) -> ft.Column:
        """
        获取摸鱼速评助手页面的内容

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
        """在后台线程安全执行耗时任务（委托 run_background_task）。"""
        run_background_task(self.page, lambda: target(*args, **kwargs))

    def _post(self, fn):
        """把 UI 变更投递到 Flet 会话线程执行。

        后台线程（_run_background 起的线程）严禁直接调用 page.update() / show_dialog()
        / 重建控件树——那会与 UI 线程的整树 diff（ObjectPatch.from_diff）竞争，触发
        'RuntimeError: dictionary changed size during iteration' 崩溃。这里用
        page.run_task（内部 asyncio.run_coroutine_threadsafe）把回调投递回会话事件
        循环，确保控件树的读写与 diff 始终发生在同一线程。
        """
        async def _run():
            try:
                fn()
            except Exception:
                pass

        try:
            self.page.run_task(_run)
        except Exception:
            # run_task 不可用时退化为直接执行（兜底，正常路径不会走到）
            try:
                fn()
            except Exception:
                pass

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
                text_style=Fonts.text(weight=ft.FontWeight.W_600),
            ),
        )
        return ft.Column(
            [
                page_heading(
                    "摸鱼速评助手",
                    "轮椅式批改 · 躺平也能把活干完 · 摸鱼神器 YYDS",
                    ft.Icons.AUTO_AWESOME,
                ),
                hero_panel(
                    "学生都在用 AI 写作业，你还在纯手动批改？",
                    "评分+批语一键搞定，活干得漂亮，鱼摸得安心，工资对得起自己",
                    action=start_button,
                    chips=[
                        status_chip(
                            "轮椅式批改",
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
                                "自动评分 + 预制批语，坐等收工就行",
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

        # 批量评分工具栏（返回 rows + 控件引用，引用挂 self 供局部刷新）
        batch_rows, self._batch_count_text, self._batch_grade_btn = build_batch_toolbar(
            on_batch_grade=self._on_batch_grade_click,
            on_select_all=self._on_select_all_projects,
            on_clear=self._on_clear_selected_projects,
            on_settings=self._show_comment_settings,
        )

        return ft.Column(
            [
                page_heading(
                    "产教融合项目",
                    "选择需要自动评分的产教融合项目",
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
                # 批量评分操作行（勾选多个项目后一键评分）
                *batch_rows,
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
            build_project_card(
                p,
                is_selected=p.source_id in self.selected_projects,
                on_click=self._on_project_click,
                on_check=self._on_project_check,
            )
            for p in self.project_list
        ]

    def _apply_pagination_state(self):
        """根据当前页码/总数更新分页按钮禁用态与文案"""
        if self.prev_btn is not None:
            self.prev_btn.disabled = self.list_loading or self.page_index <= 1
        if self.next_btn is not None:
            self.next_btn.disabled = self.list_loading or self.page_index >= self._total_pages()
        if self.page_text is not None:
            self.page_text.value = self._page_text_value()

    # ==================== 项目批量评分多选 ====================


    def _update_batch_selection_ui(self):
        """根据 selected_projects 数量刷新计数文案与按钮禁用态（局部 update，不重建列表）"""
        n = len(self.selected_projects)
        if self._batch_count_text is not None:
            self._batch_count_text.value = f"已选 {n} 个项目"
            try:
                self._batch_count_text.update()
            except Exception:
                pass
        if self._batch_grade_btn is not None:
            self._batch_grade_btn.disabled = n == 0
            try:
                self._batch_grade_btn.update()
            except Exception:
                pass

    def _on_project_check(self, e, project: ClassProject):
        """项目卡片勾选框：加入/移出批量选中集合（跨页保持）"""
        if getattr(e.control, "value", False):
            self.selected_projects[project.source_id] = project
        else:
            self.selected_projects.pop(project.source_id, None)
        self._update_batch_selection_ui()

    def _on_select_all_projects(self, e):
        """全选当前页项目（不影响其它页已选项）"""
        for p in self.project_list:
            self.selected_projects[p.source_id] = p
        self._refresh_list_area()  # 重建卡片以反映勾选态
        self._update_batch_selection_ui()

    def _on_clear_selected_projects(self, e):
        """清空所有已选项目（含其它页）"""
        self.selected_projects.clear()
        self._refresh_list_area()
        self._update_batch_selection_ui()


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
            # 后台线程不能直接 _refresh_list_area()（内部 page.update() 会与 UI 线程
            # 的整树 diff 竞争），投递到会话线程执行。
            self._post(self._refresh_list_area)

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

        cards = []
        for r in self.result_list:
            card, refs = build_student_card(
                r,
                is_selected=r.id in self.selected_result_ids,
                on_tap=self._on_student_check,
            )
            self._student_card_refs[r.id] = refs
            cards.append(card)
        self.result_list_view.controls = cards

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
            # 后台线程不能直接 _refresh_results_area()（内部 page.update() 会与 UI
            # 线程的整树 diff 竞争），投递到会话线程执行。
            self._post(self._refresh_results_area)

    # ---------- 学生卡片 ----------

    # ---------- 右侧功能面板 ----------

    def _build_result_action_panel(self) -> ft.Column:
        """构建右侧统计摘要 + 快速选择 + 功能操作按钮面板（委托 widgets）。"""
        props = ResultPanelProps(
            result_list=self.result_list,
            selected=len(self.selected_result_ids),
            on_grade_all=self._on_grade_all_click,
            on_grade_selected=self._on_grade_selected_click,
            on_select_all=self._on_select_all,
            on_deselect_all=self._on_deselect_all,
            on_select_ungraded=self._on_select_ungraded,
            on_select_completed=self._on_select_completed,
            on_export=self._on_export_grades,
            on_refresh=self._load_results,
            on_settings=self._show_comment_settings,
        )
        panel, self._stat_selected_text, self._grade_selected_btn = build_result_action_panel(props)
        return panel

    # ---------- 选择与功能按钮事件 ----------

    def _update_single_card(self, result_id: int):
        """只更新指定卡片的图标和背景色（不重建控件）"""
        refs = self._student_card_refs.get(result_id)
        if not refs:
            return
        selected = result_id in self.selected_result_ids
        # ⚠️ Flet 0.8.0+ 把 Icon 的属性名从 `name` 改成了 `icon`。
        # 写 `.name = ...` 只会设置一个 Flet 忽略的无效属性，图标永远不会变。
        refs["icon"].icon = ft.Icons.CHECK_BOX if selected else ft.Icons.CHECK_BOX_OUTLINE_BLANK
        refs["icon"].color = Palette.PRIMARY if selected else Palette.TEXT_SOFT
        refs["container"].bgcolor = Palette.PRIMARY_SOFT if selected else Palette.SURFACE
        refs["container"].border = ft.Border.all(1, Palette.PRIMARY if selected else Palette.BORDER)

    def _sync_all_cards(self):
        """批量同步所有卡片的选中状态（不重建控件）"""
        for rid in self._student_card_refs:
            self._update_single_card(rid)

    def _update_selection_stats(self):
        """
        只更新随勾选状态变化的动态控件属性（不重建右侧面板）。

        重建整块面板会创建十余个控件，是学生列表点击卡顿的主因。这里改为只改
        属性，由调用方在最后调一次 page.update() 批量推送（切勿为每个控件单独
        control.update()，那会拆成多条 websocket 消息造成逐帧刷新卡顿）。
        """
        selected = len(self.selected_result_ids)
        if self.result_count_text is not None:
            self.result_count_text.value = self._result_count_value()
        if self._stat_selected_text is not None:
            self._stat_selected_text.value = str(selected)
        if self._grade_selected_btn is not None:
            self._grade_selected_btn.disabled = selected == 0

    def _on_student_check(self, e, result_id: int):
        """学生卡片点击切换勾选

        定向推送：只对真正改了属性的控件各调一次 ``control.update()``。
        实测 ``self.page.update()`` 单次 ~370ms（且与改动数量无关——它会把
        整棵控件树 ~750 个节点重新 diff 一遍），单卡点击根本扛不住。
        改成只 diff 每个改动控件的子树（叶子控件几毫秒内），单卡点击即可秒回。
        唯一代价是发多条 websocket 消息而非一条，但每条只携带该控件的属性 diff，
        客户端会在同一帧内合并渲染。
        """
        # 关键：禁用本事件结束后的自动 page.update()。Flet 默认在每个事件处理
        # 器返回后会自动跑一次 page.update()（见 base_control._trigger_event →
        # after_event → __auto_update），那会再走一遍整树 diff（~370ms），并阻塞
        # 事件循环、把上面定向推送的 patch 卡在发送队列里迟迟不发——这就是「顿一下」。
        # disable_auto_update 由 asyncio.create_task 的 context 副本隔离，只在当前
        # 事件内生效，事件结束自动恢复，不会污染其它事件。
        ft.context.disable_auto_update()
        if result_id in self.selected_result_ids:
            self.selected_result_ids.discard(result_id)
        else:
            self.selected_result_ids.add(result_id)
        self._update_single_card(result_id)
        self._update_selection_stats()

        # 定向推送：每个改动控件各 control.update() 一次（container.update() 会
        # 顺带把内嵌 icon 的 name/color 变更一起下发）。
        refs = self._student_card_refs.get(result_id, {})
        for ctl in (
            refs.get("icon"),
            refs.get("container"),
            self.result_count_text,
            self._stat_selected_text,
            self._grade_selected_btn,
        ):
            if ctl is not None:
                ctl.update()

    def _push_all_cards_scoped(self):
        """批量勾选的定向推送：逐卡片 ``container.update()``（会顺带把内嵌 icon
        的 name/color 变更一起下发）+ 右侧统计控件。配合 handler 开头的
        ``ft.context.disable_auto_update()``，可彻底绕开 ``page.update()`` 的
        整树 diff（实测 ~370ms/次，且会阻塞事件循环、延迟定向 patch 的发送）。
        """
        for refs in self._student_card_refs.values():
            ctl = refs.get("container")
            if ctl is not None:
                ctl.update()
        for ctl in (self.result_count_text, self._stat_selected_text, self._grade_selected_btn):
            if ctl is not None:
                ctl.update()

    def _on_select_all(self, e):
        """全选"""
        ft.context.disable_auto_update()
        self.selected_result_ids = {r.id for r in self.result_list}
        self._sync_all_cards()
        self._update_selection_stats()
        self._push_all_cards_scoped()

    def _on_deselect_all(self, e):
        """取消全部选择"""
        ft.context.disable_auto_update()
        self.selected_result_ids.clear()
        self._sync_all_cards()
        self._update_selection_stats()
        self._push_all_cards_scoped()

    def _on_select_ungraded(self, e):
        """选取未评分的学生（pro_score 为 0）"""
        ft.context.disable_auto_update()
        self.selected_result_ids = {r.id for r in self.result_list if not r.is_graded}
        self._sync_all_cards()
        self._update_selection_stats()
        self._push_all_cards_scoped()

    def _on_select_completed(self, e):
        """选取项目进度 100% 的学生（含已评分，可重新评分）"""
        ft.context.disable_auto_update()
        self.selected_result_ids = {
            r.id for r in self.result_list
            if r.project_progress >= 100
        }
        self._sync_all_cards()
        self._update_selection_stats()
        self._push_all_cards_scoped()

    def _on_strictness_change(self, e):
        """严格度变更"""
        self._strictness = e.control.value or "high"
        save_strictness(self._strictness)

    def _on_export_grades(self, e):
        """导出当前班级成绩 → 弹出系统保存对话框让用户选择路径"""
        project = self.current_project
        if not project:
            return

        # 仅导出已评分的学生
        graded_list = [r for r in self.result_list if r.is_graded]
        if not graded_list:
            snack = ft.SnackBar(
                content=ft.Text("没有已评分的成绩可导出，请先完成评分"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return

        # 检查 openpyxl 是否可用
        try:
            from openpyxl import Workbook  # noqa: F401
        except ImportError:
            snack = ft.SnackBar(
                content=ft.Text(
                    "缺少 openpyxl 依赖，请执行: pip install openpyxl",
                ),
                bgcolor=ft.Colors.RED,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return

        # 文件名：课程名_班级名.xlsx，清理非法字符
        def _sanitize(name: str) -> str:
            return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")

        file_name = f"{_sanitize(project.pro_name)}_{_sanitize(project.class_name)}.xlsx"

        # save_file 是协程，需要用 page.run_task 调度
        async def do_export():
            save_path = await ft.FilePicker().save_file(
                dialog_title="导出成绩",
                file_name=file_name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xlsx"],
            )

            if not save_path:
                return

            try:
                ExcelExporter.export(graded_list, save_path)

                snack = ft.SnackBar(
                    content=ft.Text(f"成绩已导出: {save_path}"),
                    bgcolor=ft.Colors.GREEN,
                )
                self.page.snack_bar = snack
                snack.open = True
                self.page.update()

            except Exception as ex:
                snack = ft.SnackBar(
                    content=ft.Text(f"导出失败: {ex}"),
                    bgcolor=ft.Colors.RED,
                )
                self.page.snack_bar = snack
                snack.open = True
                self.page.update()

        self.page.run_task(do_export)

    def _on_grade_all_click(self, e):
        """一键评分（全部）→ 筛选进度100% 的学生（含已评分，可重新评分）"""
        targets = [
            r for r in self.result_list
            if r.project_progress >= 100
        ]
        if not targets:
            snack = ft.SnackBar(
                content=ft.Text("没有可评分的学生（进度均未达 100%）"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return
        self._show_grade_confirm(targets)

    def _on_grade_selected_click(self, e):
        """评分已选学生 → 筛选已选 + 进度100%（含已评分，可重新评分）"""
        targets = [
            r for r in self.result_list
            if r.id in self.selected_result_ids
            and r.project_progress >= 100
        ]
        if not targets:
            snack = ft.SnackBar(
                content=ft.Text("选中的学生中没有进度达 100% 可评分的"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return
        self._show_grade_confirm(targets)

    # ---------- 评分确认弹窗 ----------


    def _show_grade_confirm(self, targets: list[ProjectResult]):
        """显示评分确认弹窗（单项目）：人数 + 档位 + 规则 + 免责声明"""
        cfg = STRICTNESS_CONFIG.get(self._strictness, STRICTNESS_CONFIG["high"])
        label = cfg["label"]
        range_min = MINIMUM_NOT_MET_SCORE
        _, high = cfg["tier3"]

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("确认开始自动评分"),
            content=ft.Column(
                [
                    ft.Text(f"即将为 {len(targets)} 名学生自动评分", size=14),
                    ft.Divider(height=6, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        f"当前严格度：{label}（{range_min} ~ {high}）",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=Palette.PRIMARY,
                    ),
                    *build_grading_rules_content(cfg),
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

    def _show_batch_grade_confirm(self, groups):
        """显示批量评分确认弹窗：N 个项目 / M 名学生 + 档位 + 规则 + 免责声明"""
        cfg = STRICTNESS_CONFIG.get(self._strictness, STRICTNESS_CONFIG["high"])
        label = cfg["label"]
        range_min = MINIMUM_NOT_MET_SCORE
        _, high = cfg["tier3"]

        n_projects = len(groups)
        n_students = sum(len(t) for _, t in groups)

        # 项目清单（最多列 8 条，超出合并为一行，避免弹窗过长）
        proj_lines = []
        for i, (pname, _) in enumerate(groups):
            if i >= 8:
                proj_lines.append(
                    ft.Text(
                        f"  • ……等共 {n_projects} 个项目",
                        size=11,
                        color=Palette.TEXT_MUTED,
                    )
                )
                break
            proj_lines.append(
                ft.Text(
                    f"  • {pname}",
                    size=11,
                    color=Palette.TEXT_MUTED,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("确认批量评分"),
            content=ft.Column(
                [
                    ft.Text(
                        f"即将为 {n_projects} 个项目、共 {n_students} 名学生批量评分",
                        size=14,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                    *proj_lines,
                    ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        f"当前严格度：{label}（{range_min} ~ {high}）",
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=Palette.PRIMARY,
                    ),
                    *build_grading_rules_content(cfg),
                ],
                tight=True,
                spacing=4,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                ft.ElevatedButton(
                    "开始批量评分",
                    bgcolor=Palette.PRIMARY,
                    color=Palette.SURFACE,
                    on_click=lambda _: self._start_batch_grading(confirm_dialog, groups),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(confirm_dialog)

    def _on_batch_grade_click(self, e):
        """批量评分入口：先后台汇总所选项目的可评学生（进度≥100%），再弹确认窗"""
        if self._grading_in_progress:
            return
        if self.api_client is None:
            return
        projects = list(self.selected_projects.values())
        if not projects:
            snack = ft.SnackBar(
                content=ft.Text("请先勾选要批量评分的项目"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return

        # 汇总进度窗
        self._grading_progress_text = ft.Text(
            "正在汇总学生名单...", size=13, text_align=ft.TextAlign.CENTER
        )
        summary_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("批量评分准备"),
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
        self.page.show_dialog(summary_dialog)

        def summary_task():
            groups: list = []
            failed_projects: list = []
            n = len(projects)

            def set_progress(text: str):
                def _do():
                    self._grading_progress_text.value = text
                    try:
                        self._grading_progress_text.update()
                    except Exception:
                        pass

                self._post(_do)

            for i, p in enumerate(projects, 1):
                label = f"{p.pro_name or '未命名项目'}（{p.class_name or '未知班级'}）"
                set_progress(f"正在汇总：{label}（{i}/{n}）")
                try:
                    items = self.api_client.get_class_project_result(
                        source_id=p.source_id,
                        class_id=p.class_id,
                        project_id=p.project_id,
                    )
                    targets = [r for r in items if r.project_progress >= 100]
                    if targets:
                        groups.append((label, targets))
                except Exception as ex:
                    failed_projects.append(f"{label}（{ex}）")

            def _after():
                try:
                    self.page.pop_dialog()  # 关汇总进度窗
                except Exception:
                    pass
                if not groups:
                    msg = "所选项目没有可评分的学生（进度均未达 100%）"
                    if failed_projects:
                        msg += f"；且 {len(failed_projects)} 个项目拉取失败"
                    snack = ft.SnackBar(
                        content=ft.Text(msg), bgcolor=ft.Colors.ORANGE
                    )
                    self.page.snack_bar = snack
                    snack.open = True
                    self.page.update()
                    return
                if failed_projects:
                    snack = ft.SnackBar(
                        content=ft.Text(
                            f"{len(failed_projects)} 个项目拉取失败，已跳过"
                        ),
                        bgcolor=ft.Colors.ORANGE,
                    )
                    self.page.snack_bar = snack
                    snack.open = True
                    self.page.update()
                self._show_batch_grade_confirm(groups)

            self._post(_after)

        self._run_background(summary_task)

    # ---------- 评分工作流 ----------

    def _launch_grading(self, confirm_dialog, groups, is_batch: bool):
        """关闭确认弹窗 → 展示进度弹窗 → 后台跑 _grading_inner → 收尾。

        groups: list[(label, list[ProjectResult])]，单项目传 1 组；
        分布上限在 _grading_inner 内按组分别应用（每个项目独立）。
        """
        if self._grading_in_progress:
            return
        self.page.pop_dialog()

        if self._comment_picker is None:
            self._comment_picker = CommentPicker()

        self._grading_in_progress = True
        floor_score = MINIMUM_NOT_MET_SCORE  # 未达最低要求的保底分（76），用于标注与完成弹窗

        # 进度弹窗
        self._grading_progress_text = ft.Text(
            "准备开始评分...", size=13, text_align=ft.TextAlign.CENTER
        )
        progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("批量评分中" if is_batch else "自动评分中"),
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

        total = sum(len(t) for _, t in groups)

        def grading_task():
            stats = {
                "total": total,
                "graded": 0,
                "failed": 0,
                "min_score_names": [],
                "failed_names": [],
            }

            def set_progress(text: str):
                """更新进度文案（仅刷新这一个文本控件，投递到会话线程）。

                绝不要在这里调 self.page.update()——整树 diff 单次 ~370ms 且会与
                UI 线程竞争；只 update 这一个叶子控件即可秒级响应。
                """
                def _do():
                    self._grading_progress_text.value = text
                    try:
                        self._grading_progress_text.update()
                    except Exception:
                        pass

                self._post(_do)

            try:
                self._grading_inner(groups, set_progress, stats)
            finally:
                self._grading_in_progress = False

                # 收尾的 UI 变更（关弹窗 + 刷列表 + 出完成弹窗）统一投递到会话线程，
                # 避免后台线程直接 show_dialog()/page.update() 与整树 diff 竞争崩溃。
                def _finish():
                    try:
                        self.page.pop_dialog()  # 关闭进度弹窗（自动 update）
                    except Exception:
                        pass
                    if is_batch:
                        # 批量在项目列表屏：刷新项目卡（更新「已完成」计数等）
                        try:
                            self._load_projects()
                        except Exception:
                            pass
                    else:
                        # 单项目：一次性刷新学生列表，反映最终分数与统计
                        try:
                            self._refresh_results_area()
                        except Exception:
                            pass
                    self._show_grading_completion(stats, floor_score)

                self._post(_finish)

        self._run_background(grading_task)

    def _grading_inner(self, groups, set_progress, stats):
        """对每个 (label, targets) 分组执行评分（委托 GradingService）。

        stats 就地累加（GradingService.grade_groups 直接写入传入的 stats dict）。
        """
        GradingService(self.api_client).grade_groups(
            groups,
            strictness=self._strictness,
            comment_picker=self._comment_picker,
            on_progress=set_progress,
            stats=stats,
        )

    def _start_grading(self, confirm_dialog, targets: list[ProjectResult]):
        """单项目评分入口：包成 1 组（label=项目名（班级名））后启动"""
        p = self.current_project
        if p:
            label = f"{p.pro_name or '未命名项目'}（{p.class_name or '未知班级'}）"
        else:
            label = "当前项目"
        self._launch_grading(confirm_dialog, [(label, targets)], is_batch=False)

    def _start_batch_grading(self, confirm_dialog, groups):
        """批量评分入口：groups 由 _on_batch_grade_click 汇总而来"""
        self._launch_grading(confirm_dialog, groups, is_batch=True)

    # ---------- 评分完成弹窗 ----------

    def _show_grading_completion(self, stats: dict, floor_score: int = 76):
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
            _show_max = 15
            names = stats["min_score_names"]
            _truncated = len(names) > _show_max
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
                                        f"以下 {len(names)} 名学生"
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
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                )
                                for name in names[:_show_max]
                            ],
                            *(
                                [
                                    ft.Text(
                                        f"  • ……等共 {len(names)} 人（仅显示前 {_show_max} 条）",
                                        size=11,
                                        color=Palette.DANGER,
                                        weight=ft.FontWeight.W_500,
                                    )
                                ]
                                if _truncated
                                else []
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=12,
                    bgcolor="#FDE8ED",
                    border=ft.Border.all(1, Palette.DANGER),
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
        """显示设置弹窗：严格度卡片 + 短/长评语分区（彩色标题栏 + 卡片化列表）"""
        templates = load_templates()
        short_items = templates.get("short", [])
        long_items = templates.get("long", [])

        # 严格度下拉框（无事件，关闭时读 value）
        strictness_dd = ft.Dropdown(
            value=self._strictness,
            options=[
                ft.dropdown.Option("high", "严格（76 ~ 90）"),
                ft.dropdown.Option("medium", "中等（76 ~ 90）"),
                ft.dropdown.Option("low", "宽松（76 ~ 100）"),
            ],
            width=220,
        )

        # 关闭时保存严格度
        def on_close(_):
            self._strictness = strictness_dd.value or "high"
            save_strictness(self._strictness)
            self.page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.TUNE, size=20, color=Palette.PRIMARY),
                    ft.Text("评语与严格度设置", size=18, weight=ft.FontWeight.W_600),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        # ---- 严格度（紧凑卡片） ----
                        surface_card(
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.SPEED, size=18, color=Palette.PRIMARY),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "批改严格度",
                                                size=13,
                                                weight=ft.FontWeight.W_600,
                                                color=Palette.TEXT,
                                            ),
                                            ft.Text(
                                                "决定分数区间与扣分上限",
                                                size=11,
                                                color=Palette.TEXT_MUTED,
                                            ),
                                        ],
                                        spacing=0,
                                    ),
                                    ft.Container(expand=True),
                                    strictness_dd,
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=14,
                        ),
                        # ---- 短评语分区 ----
                        build_template_section(
                            pool="short",
                            title="短评语模板",
                            usage="用于 < 95 分",
                            icon=ft.Icons.SHORT_TEXT,
                            items=short_items,
                            min_chars=20,
                            accent=Palette.PRIMARY,
                            accent_soft=Palette.PRIMARY_SOFT,
                            on_add=self._add_template,
                            on_edit=self._edit_template,
                            on_delete=self._delete_template,
                        ),
                        # ---- 长评语分区 ----
                        build_template_section(
                            pool="long",
                            title="长评语模板",
                            usage="用于 ≥ 95 分",
                            icon=ft.Icons.ARTICLE_OUTLINED,
                            items=long_items,
                            min_chars=100,
                            accent=Palette.ACCENT,
                            accent_soft=Palette.ACCENT_SOFT,
                            on_add=self._add_template,
                            on_edit=self._edit_template,
                            on_delete=self._delete_template,
                        ),
                    ],
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=660,
                height=520,
                padding=4,
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

    def _edit_template(self, pool: str, index: int):
        """编辑单条评语（关闭设置弹窗 → 打开编辑弹窗 → 保存后返回设置弹窗）"""
        self.page.pop_dialog()
        current = TemplateService().get(pool, index) or ""

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
                TemplateService().edit(pool, index, new_text)
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
                TemplateService().add(pool, new_text)
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
        if not TemplateService().delete(pool, index):
            snack = ft.SnackBar(
                content=ft.Text("该类评语至少保留一条"),
                bgcolor=ft.Colors.ORANGE,
            )
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()
            return
        if self._comment_picker is not None:
            self._comment_picker.reload()
        # 刷新设置弹窗
        self.page.pop_dialog()
        self._show_comment_settings(None)


