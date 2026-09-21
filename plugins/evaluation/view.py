"""
评估出题向导 UI 与工作流编排 - Evaluation question wizard UI and workflow orchestration.

六步向导：① 课程信息 → ② 章节与知识点 → ③ 出题详情 → ④ 题量与题型 → ⑤ AI 生成 → ⑥ 结果与导出。

线程模型（§H-1）

- 生成跑在 ``page.run_thread`` 的 worker 线程；
- **worker 线程绝不直接操作 UI**（不碰 ``show_dialog`` / ``pop_dialog`` / ``update``）；
- 需要澄清时 worker 只 ``page.run_task(...)`` 调度弹窗，然后 ``Clarification.wait()`` 阻塞；
- 弹窗的回答在 Flet 事件循环线程写回后再 ``event.set()`` 唤醒 worker。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Optional

import flet as ft

from src.core.plugin_settings import setting_value
from src.ui.components import (
    AnswerProgressDialog,
    build_plugin_settings_dialog,
    hero_panel,
    page_heading,
    primary_button,
    run_background_task,
    secondary_button,
    section_label,
    show_confirm_dialog,
    show_error_dialog,
    show_snack,
    status_chip,
    surface_card,
    workflow_step,
)
from src.ui.theme import Fonts, Palette, Radius

from .ai_client import (
    DEFAULT_BASE_URL,
    DEFAULT_EXA_MCP_URL,
    DEFAULT_MODEL,
    AIConfigError,
    HttpMcpSearchClient,
    StructuredAIClient,
)
from .clarification import (
    STATUS_PENDING,
    Clarification,
    ClarificationQueue,
    summarize_records,
)
from .exporter import EvaluationExporter
from .generator import GenerationController
from .models import (
    DEFAULT_DIFFICULTY_RATIO,
    DEFAULT_QUESTION_COUNT,
    DEFAULT_SENSITIVITY,
    DEFAULT_TYPE_RATIO,
    DIFFICULTIES,
    KNOWLEDGE_LEVELS,
    KNOWLEDGE_TYPES,
    QUESTION_TYPES,
    SENSITIVITY_LEVELS,
    Chapter,
    CourseDraft,
    KnowledgePoint,
    Question,
)
from .prompts import build_tag_suggestion_prompt, parse_tag_suggestion
from .quality import answer_distribution_warning, estimate_cost
from .review import (
    GenerationRun,
    append_generated,
    assign_internal_ids,
    build_clarification_choices,
    mark_reviewed,
    points_for_export,
    ready_for_export,
    replace_question,
    review_summary,
)
from .state import (
    DraftStore,
    WizardValidator,
    apply_global_defaults,
    apply_global_details,
    generation_fingerprint,
    generation_is_stale,
    pending_clarifications,
)
from .template_manager import TemplateManager

PLUGIN_ID = "evaluation"
PLUGIN_NAME = "评估出题助手"
OUTPUT_SUBDIR = Path("output") / "evaluation"

STEP_TITLES = (
    "课程信息",
    "章节与知识点",
    "出题详情",
    "题量与题型",
    "AI 生成",
    "结果与导出",
)

LEVEL_COLORS = {
    "阻断": Palette.DANGER,
    "确认": Palette.WARNING,
    "自决": Palette.TEXT_MUTED,
}

CONFIDENCE_COLORS = {
    "green": Palette.ACCENT,
    "amber": Palette.WARNING,
    "red": Palette.DANGER,
}

# 可重排列表的单行高度与高度自适应下限/上限
_DRAG_ROW_HEIGHT = 46
_LIST_MIN_HEIGHT = 116

# 向导区高度 = 页面高度 - 主框架固定占用
#   顶栏（标题+副标题，vertical padding 18）≈ 71
#   内容区 padding（top 24 + bottom 30）        = 54
#   「返回插件中心」按钮行 + spacing 18          ≈ 68
_FRAME_CHROME_HEIGHT = 200
_MIN_WIZARD_HEIGHT = 420
# 生成日志面板高度（向导区拉高后给日志更多空间）
_LOG_PANEL_HEIGHT = 320


def _list_height(count: int, *, max_height: int) -> int:
    """按条目数自适应可重排列表的高度（避免少条目时留大片空白）。"""
    wanted = max(int(count), 0) * _DRAG_ROW_HEIGHT + 12
    return max(_LIST_MIN_HEIGHT, min(int(max_height), wanted))


class EvaluationView:
    """评估出题六步向导视图。"""

    def __init__(
        self,
        page: ft.Page,
        main_app=None,
        context=None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.page = page
        self.main_app = main_app
        self.context = context

        self.plugin_dir = Path(__file__).resolve().parent
        # plugins/evaluation/view.py -> parents[1] == 仓库根目录
        self.project_root = Path(project_root) if project_root else self.plugin_dir.parents[1]

        self.store = DraftStore(self.project_root)
        self.draft: CourseDraft = self.store.load()
        self.validator = WizardValidator()
        self.template_manager = TemplateManager(self.plugin_dir)
        self.exporter = EvaluationExporter(self.template_manager)

        self.queue = ClarificationQueue(
            sensitivity=self.draft.sensitivity,
            on_record=self._on_clarification_record,
        )
        self.controller: Optional[GenerationController] = None
        self.run: Optional[GenerationRun] = None
        self.progress: Optional[AnswerProgressDialog] = None

        self.busy = False
        self.ai_test_busy = False
        self.suggestion_busy: set[tuple[int, int]] = set()
        self.message = ""
        self.logs: list[str] = []

        # Step4 全局默认区（「应用到全部知识点」的来源）
        self.global_defaults: dict[str, Any] = {
            "question_count": DEFAULT_QUESTION_COUNT,
            "type_ratio": dict(DEFAULT_TYPE_RATIO),
            "difficulty_ratio": dict(DEFAULT_DIFFICULTY_RATIO),
        }
        # Step4 视图模式：按题数 / 按比例
        self.distribution_view = "counts"
        # Step3 全局填写栏
        self.global_details: dict[str, Any] = {
            "level": KNOWLEDGE_LEVELS[0],
            "knowledge_type": KNOWLEDGE_TYPES[0],
            "tags": [],
        }
        self.tag_input = ""
        self.detail_tag_input = ""
        self.selected_chapter_index = 0
        self.suggested_tags: dict[tuple[int, int], list[str]] = {}
        self._clar_dialog: Optional[ft.AlertDialog] = None
        self._clar_resolved = False
        self.review_expanded: set[str] = set()
        self._current_content: Optional[ft.AnimatedSwitcher] = None

        # 控件骨架（_render 只重建 inner controls）
        # 布局：步骤条固定在顶部，内容区撑满并自行滚动，操作栏固定在底部，
        # 这样主框架的剩余高度全部归内容使用，底部不会留下无用空白。
        self._step_bar = ft.Row(spacing=6, wrap=True)
        self._body = ft.Column(spacing=18, expand=True, scroll=ft.ScrollMode.AUTO)
        self._nav = ft.Row(spacing=10)
        self._wizard_shell: Optional[ft.Container] = None
        self._root = ft.Column(
            spacing=18,
            expand=True,
            controls=[
                # 主界面框架顶部已有标题，这里不再重复显示页面标题
                self._step_bar,
                self._body,
                self._nav,
            ],
        )

    # ================================================================ 生命周期
    def get_content(self) -> ft.Control:
        # 与其它插件一致：打开插件先展示说明/欢迎页，点「开始使用」才进入向导
        welcome = self._get_welcome_content()
        self._current_content = ft.AnimatedSwitcher(
            content=welcome,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )
        return ft.Column(
            [self._current_content],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )

    def _get_welcome_content(self) -> ft.Control:
        start_button = ft.FilledButton(
            "开始使用",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=Palette.SURFACE,
            color=Palette.PRIMARY,
            on_click=self._on_start_click,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=24, vertical=16),
                text_style=Fonts.text(weight=ft.FontWeight.W_600),
            ),
        )
        return ft.Column(
            [
                page_heading(
                    "评估出题助手",
                    "按平台模板生成课程评估题（单选/多选/判断）并导出 Word/Excel",
                    ft.Icons.QUIZ,
                ),
                hero_panel(
                    "还在手动编评估题？AI 帮你一键出完",
                    "录入知识点 → 配置题型 → AI 生成 → 审核导出，四步搞定课程评估题库",
                    action=start_button,
                    icon=ft.Icons.QUIZ,
                    chips=[
                        status_chip(
                            "AI 出题",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "平台模板",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "逐题审核",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                    ],
                ),
                section_label("四步出题法", "从零到题库，全程 AI 辅助"),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            content=workflow_step(
                                "01",
                                "录信息",
                                "填写课程、章节、知识点及考点清单",
                                ft.Icons.EDIT_NOTE,
                            ),
                            col={"xs": 12, "md": 3},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "02",
                                "配题型",
                                "设置单选/多选/判断的题数与难度配比",
                                ft.Icons.TUNE,
                            ),
                            col={"xs": 12, "md": 3},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "03",
                                "AI 出题",
                                "逐知识点智能生成，支持暂停与澄清",
                                ft.Icons.AUTO_AWESOME,
                            ),
                            col={"xs": 12, "md": 3},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "04",
                                "导出",
                                "审核后导出 Word/Excel 平台标准模板",
                                ft.Icons.FILE_DOWNLOAD,
                            ),
                            col={"xs": 12, "md": 3},
                        ),
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ],
            spacing=22,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _on_start_click(self, e=None) -> None:
        self._render()
        if self._current_content is not None:
            # 用一个「填满主框架」的容器包住向导（外层框架可滚动，
            # 插件内容必须自己给定高度才能撑满，否则底部会留白）
            self._wizard_shell = ft.Container(
                content=self._root,
                height=self._wizard_height(),
            )
            self._current_content.content = self._wizard_shell
            self._safe_update()

    def _wizard_height(self) -> int:
        """向导区高度：主框架剩余空间（窗口变化后在 _render 里重算）。"""
        page_height = getattr(self.page, "height", None)
        if not page_height:
            window = getattr(self.page, "window", None)
            page_height = getattr(window, "height", None) if window is not None else None
        try:
            base = int(page_height)
        except (TypeError, ValueError):
            base = _MIN_WIZARD_HEIGHT + _FRAME_CHROME_HEIGHT
        return max(_MIN_WIZARD_HEIGHT, base - _FRAME_CHROME_HEIGHT)

    def cleanup(self) -> None:
        """插件卸载钩子：停生成、唤醒所有等待中的澄清、强制落盘。"""
        try:
            if self.controller is not None:
                self.controller.cancel()
            self.queue.release_all()
            self.store.flush(self.draft, force=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[Evaluation] cleanup 失败: {exc}")

    # ================================================================ 渲染
    def _render(self) -> None:
        self._step_bar.controls = self._build_step_bar()
        self._body.controls = self._build_step_content()
        self._nav.controls = self._build_nav_bar()
        # 窗口尺寸可能变化：同步向导区高度，始终填满主框架
        if self._wizard_shell is not None:
            self._wizard_shell.height = self._wizard_height()
        self._safe_update()

    def _safe_update(self) -> None:
        try:
            self.page.update()
        except Exception as exc:  # noqa: BLE001 - 页面可能已销毁
            print(f"[Evaluation] update 跳过: {exc}")

    def _build_step_bar(self) -> list[ft.Control]:
        current = self.draft.current_step
        nodes: list[ft.Control] = []

        for index, title in enumerate(STEP_TITLES, start=1):
            done = index < current
            active = index == current

            if active:
                bgcolor, fg = Palette.PRIMARY, Palette.SURFACE
            elif done:
                bgcolor, fg = Palette.PRIMARY_SOFT, Palette.PRIMARY_DARK
            else:
                bgcolor, fg = Palette.SURFACE_ALT, Palette.TEXT_SOFT

            node = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "✓" if done else str(index),
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=fg,
                            ),
                            width=22,
                            height=22,
                            alignment=ft.Alignment(0, 0),
                            border_radius=11,
                            bgcolor=ft.Colors.with_opacity(0.18, fg),
                        ),
                        ft.Text(title, size=13, color=fg, weight=ft.FontWeight.W_600),
                    ],
                    spacing=8,
                    tight=True,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=9),
                bgcolor=bgcolor,
                border=ft.Border.all(1, Palette.BORDER if not active else Palette.PRIMARY),
                border_radius=Radius.MEDIUM,
                # 已完成步骤可点击回跳；未到达步骤置灰不可点
                on_click=(lambda e, s=index: self._jump(s)) if done or active else None,
                disabled=not (done or active),
                ink=done or active,
            )
            nodes.append(node)

        return nodes

    def _build_nav_bar(self) -> list[ft.Control]:
        step = self.draft.current_step
        errors = self.validator.validate_step(self.draft, step)

        controls: list[ft.Control] = []
        if step > 1:
            controls.append(
                secondary_button("上一步", ft.Icons.ARROW_BACK, self._previous)
            )
        if self.message:
            color = Palette.DANGER if errors else Palette.ACCENT
            controls.append(
                ft.Text(self.message, size=12, color=color, max_lines=2, expand=True)
            )
        else:
            controls.append(ft.Container(expand=True))

        if step == 5:
            controls.extend(self._build_generation_actions())
        elif step == 6:
            controls.extend(
                [
                    secondary_button(
                        "生成其他课程",
                        ft.Icons.REFRESH,
                        self._new_draft,
                    ),
                    primary_button("导出", ft.Icons.FILE_DOWNLOAD, self._export),
                ]
            )
        else:
            controls.append(
                primary_button(
                    "下一步",
                    ft.Icons.ARROW_FORWARD,
                    self._next,
                )
            )
        return controls

    # ================================================================ 步骤内容
    def _build_step_content(self) -> list[ft.Control]:
        step = self.draft.current_step
        if step == 1:
            return self._step_one()
        if step == 2:
            return self._step_two()
        if step == 3:
            return self._step_three()
        if step == 4:
            return self._step_four()
        if step == 5:
            return self._step_five()
        return self._step_six()

    # ---------------------------------------------------------------- Step1
    def _step_one(self) -> list[ft.Control]:
        counts = len(self.draft.chapters), len(self.draft.all_points)

        course_name = ft.TextField(
            label="课程名称 *",
            value=self.draft.course_name,
            width=320,
            on_change=lambda e: self._set_field("course_name", e.control.value),
        )
        target = ft.TextField(
            label="授课对象",
            value=self.draft.target,
            width=320,
            hint_text="如：24级大数据技术2班",
            on_change=lambda e: self._set_field("target", e.control.value),
        )
        tool_version = ft.TextField(
            label="软件/工具版本",
            value=self.draft.tool_version,
            width=320,
            hint_text="如：CorelDraw X4",
            on_change=lambda e: self._set_field("tool_version", e.control.value),
        )
        online = ft.Switch(
            value=self.draft.online_search,
            label="联网检索（考点不确定时用 Exa 检索辅助，默认关）",
            on_change=lambda e: self._set_field("online_search", e.control.value),
        )

        notice = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=Palette.TEXT_MUTED),
                    ft.Text(
                        "题目仅依据课程、章节、知识点和题型配置生成；联网检索为可选辅助。",
                        size=12,
                        color=Palette.TEXT_MUTED,
                        expand=True,
                    ),
                ],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            bgcolor=Palette.SURFACE_ALT,
            border_radius=Radius.SMALL,
        )

        return [
            self._card(
                "① 课程信息",
                [
                    ft.Row([course_name, target], spacing=14, wrap=True),
                    # Switch 必须包一层显式宽度才能放进 wrap Row（否则会被排成单独一行）
                    ft.Row(
                        [
                            tool_version,
                            ft.Container(content=online, width=430),
                        ],
                        spacing=14,
                        wrap=True,
                    ),
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        [
                            secondary_button("AI 设置", ft.Icons.SETTINGS, self._open_settings),
                            secondary_button(
                                "测试中…" if self.ai_test_busy else "测试连接",
                                ft.Icons.HOURGLASS_TOP if self.ai_test_busy else ft.Icons.WIFI_TETHERING,
                                self._test_ai_connection,
                                disabled=self.ai_test_busy,
                            ),
                        ],
                        spacing=10,
                    ),
                    notice,
                ],
            ),
            ft.Row(
                [
                    ft.Text(
                        f"当前草稿：{counts[0]} 个章节 ｜ {counts[1]} 个知识点 ｜ 计划 {self.draft.total_questions} 题",
                        size=12,
                        color=Palette.TEXT_MUTED,
                        expand=True,
                    ),
                    ft.TextButton(
                        "新建草稿",
                        icon=ft.Icons.NOTE_ADD_OUTLINED,
                        tooltip="清空当前草稿并重新开始（已导出的文件不受影响）",
                        on_click=self._new_draft,
                    ),
                ],
                spacing=8,
            ),
        ]

    def _upload_tile(self, title, subtitle, icon, on_click, *, enabled: bool) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=18, color=Palette.PRIMARY if enabled else Palette.TEXT_SOFT),
                            ft.Text(title, size=13, weight=ft.FontWeight.W_600, expand=True),
                        ],
                        spacing=8,
                    ),
                    ft.Text(subtitle, size=11, color=Palette.TEXT_MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.TextButton(
                        "选择文件",
                        icon=ft.Icons.UPLOAD_FILE,
                        disabled=not enabled,
                        on_click=on_click,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
            padding=14,
            width=330,
            bgcolor=Palette.SURFACE_ALT,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.MEDIUM,
        )

    # ---------------------------------------------------------------- Step2
    def _step_two(self) -> list[ft.Control]:
        chapters = self.draft.chapters
        self.selected_chapter_index = min(self.selected_chapter_index, max(len(chapters) - 1, 0))

        # 高度随条目数自适应：少条目时不留大片空白，多了则在 340 内滚动
        chapter_list = ft.ReorderableListView(
            controls=[
                self._chapter_row(index, chapter) for index, chapter in enumerate(chapters)
            ],
            on_reorder=self._on_chapter_reorder,
            height=_list_height(len(chapters), max_height=340),
            spacing=4,
            # 关闭 Flet 默认拖拽手柄（它会叠在行尾的删除按钮上）；改为左侧自带手柄
            show_default_drag_handles=False,
        )

        left = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("章节", size=14, weight=ft.FontWeight.W_600, expand=True),
                            ft.IconButton(
                                ft.Icons.ADD, tooltip="新建章节", icon_size=18,
                                on_click=self._add_chapter,
                            ),
                        ]
                    ),
                    ft.Container(
                        content=(
                            chapter_list
                            if chapters
                            else ft.Text("还没有章节，点击右上角 ＋ 新建", size=12, color=Palette.TEXT_MUTED)
                        ),
                        expand=True,
                    ),
                ],
                spacing=8,
                expand=True,
            ),
            width=320,
            padding=14,
            bgcolor=Palette.SURFACE_ALT,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.MEDIUM,
        )

        chapter = chapters[self.selected_chapter_index] if chapters else None
        right = self._knowledge_panel(chapter)

        return [
            self._card(
                "② 章节与知识点",
                [
                    ft.Row(
                        [
                            ft.Text(
                                "支持拖拽排序；知识点可手动录入或批量粘贴",
                                size=12,
                                color=Palette.TEXT_MUTED,
                                expand=True,
                            ),
                        ]
                    ),
                    ft.Row([left, ft.Container(content=right, expand=True)], spacing=14),
                ],
            )
        ]

    def _drag_handle(self, tooltip: str = "拖拽排序") -> ft.Control:
        """自带的拖拽手柄（只用图标作为拖拽区，避免误触整行）。"""
        return ft.ReorderableDragHandle(
            content=ft.Icon(ft.Icons.DRAG_HANDLE, size=16, color=Palette.TEXT_SOFT),
            tooltip=tooltip,
            mouse_cursor=ft.MouseCursor.CLICK,
        )

    def _chapter_row(self, index: int, chapter: Chapter) -> ft.Control:
        selected = index == self.selected_chapter_index
        return ft.Container(
            key=f"chapter-{index}",
            content=ft.Row(
                [
                    self._drag_handle(),
                    ft.Text(
                        f"{index + 1}. {chapter.name or '未命名章节'}",
                        size=13,
                        expand=True,
                        color=Palette.TEXT,
                        weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                    ),
                    ft.Text(f"{len(chapter.knowledge_points)}", size=11, color=Palette.TEXT_MUTED),
                    ft.IconButton(
                        ft.Icons.EDIT, icon_size=15, tooltip="编辑",
                        on_click=lambda e, i=index: self._edit_chapter(i),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, icon_size=15, tooltip="删除",
                        on_click=lambda e, i=index: self._delete_chapter(i),
                    ),
                ],
                spacing=4,
            ),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            bgcolor=Palette.PRIMARY_SOFT if selected else None,
            border_radius=Radius.SMALL,
            on_click=lambda e, i=index: self._select_chapter(i),
        )

    def _knowledge_panel(self, chapter: Optional[Chapter]) -> ft.Control:
        if chapter is None:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.LOCK_OUTLINE, size=34, color=Palette.TEXT_SOFT),
                        ft.Text("请先创建章节", size=14, color=Palette.TEXT_MUTED),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=40,
                bgcolor=Palette.SURFACE_ALT,
                border_radius=Radius.MEDIUM,
                alignment=ft.Alignment(0, 0),
                expand=True,
            )

        import_text_field = ft.TextField(
            hint_text="粘贴知识点名称，每行一个",
            multiline=True,
            min_lines=2,
            max_lines=3,
            expand=True,
        )

        def add_pasted(e):
            names = [line.strip() for line in (import_text_field.value or "").splitlines() if line.strip()]
            if not names:
                show_snack(self.page, "没有可添加的知识点", color=Palette.WARNING)
                return
            self._add_points(names)
            import_text_field.value = ""
            self._render()

        rows = [
            ft.Row(
                [
                    ft.Text(
                        f"知识点 — {chapter.name or '未命名章节'}",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.ADD, tooltip="新建知识点", icon_size=18,
                        on_click=self._add_point,
                    ),
                ]
            )
        ]

        if chapter.knowledge_points:
            rows.append(
                ft.ReorderableListView(
                    controls=[
                        self._point_row(index, point)
                        for index, point in enumerate(chapter.knowledge_points)
                    ],
                    on_reorder=self._on_point_reorder,
                    height=_list_height(len(chapter.knowledge_points), max_height=250),
                    spacing=4,
                    show_default_drag_handles=False,
                )
            )
        else:
            rows.append(
                ft.Text("该章节还没有知识点", size=12, color=Palette.TEXT_MUTED)
            )

        rows.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            import_text_field,
                            ft.TextButton("批量添加", icon=ft.Icons.PLAYLIST_ADD, on_click=add_pasted),
                        ],
                        spacing=8,
                    )
                ],
                spacing=4,
            )
        )

        return ft.Container(
            content=ft.Column(rows, spacing=8, expand=True),
            padding=14,
            bgcolor=Palette.SURFACE_ALT,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.MEDIUM,
            expand=True,
        )

    def _point_row(self, index: int, point: KnowledgePoint) -> ft.Control:
        return ft.Container(
            key=f"point-{index}",
            content=ft.Row(
                [
                    self._drag_handle(),
                    ft.Text(f"{index + 1}. {point.name or '未命名'}", size=13, expand=True),
                    ft.Text(
                        f"{point.question_count}题",
                        size=11,
                        color=Palette.TEXT_MUTED,
                    ),
                    ft.IconButton(
                        ft.Icons.EDIT, icon_size=15, tooltip="编辑",
                        on_click=lambda e, i=index: self._edit_point(i),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, icon_size=15, tooltip="删除",
                        on_click=lambda e, i=index: self._delete_point(i),
                    ),
                ],
                spacing=4,
            ),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            bgcolor=Palette.SURFACE,
            border_radius=Radius.SMALL,
        )

    # ---------------------------------------------------------------- Step3
    def _step_three(self) -> list[ft.Control]:
        if not self.draft.all_points:
            return [
                self._card(
                    "③ 出题详情",
                    [ft.Text("请先在 Step2 创建章节与知识点", size=13, color=Palette.TEXT_MUTED)],
                )
            ]

        global_card = self._card(
            "全局填写（批量应用到未填写知识点）",
            [
                ft.Row(
                    [
                        self._select(
                            "知识点等级",
                            self.global_details["level"],
                            KNOWLEDGE_LEVELS,
                            lambda e: self._set_global_detail("level", e.control.value),
                        ),
                        self._select(
                            "知识点类型",
                            self.global_details["knowledge_type"],
                            KNOWLEDGE_TYPES,
                            lambda e: self._set_global_detail("knowledge_type", e.control.value),
                        ),
                        ft.Container(
                            content=ft.TextField(
                                label="考点清单（逗号分隔）",
                                value=",".join(self.global_details["tags"]),
                                on_change=lambda e: self._set_global_detail(
                                "tags",
                                [part.strip() for part in (e.control.value or "").replace("，", ",").split(",") if part.strip()],
                                ),
                                width=320,
                            ),
                        ),
                        ft.Container(
                            content=primary_button(
                                "应用到全部未填写知识点",
                                ft.Icons.DOWNLOAD_DONE,
                                self._apply_global_details,
                            ),
                            alignment=ft.Alignment(1, 0),
                        ),
                    ],
                    spacing=12,
                    wrap=True,
                )
            ],
        )

        point_cards = [self._point_detail_card(index, point) for index, point in enumerate(self.draft.all_points)]
        return [global_card, *point_cards]

    def _point_detail_card(self, index: int, point: KnowledgePoint) -> ft.Control:
        tags_row = ft.Row(
            [
                self._tag_chip(tag, lambda value, p=point: self._remove_tag(p, value))
                for tag in point.tags
            ]
            or [ft.Text("未填写（生成时按 课程名+章节名+知识点名 自推）", size=11, color=Palette.TEXT_SOFT)],
            wrap=True,
            spacing=6,
        )

        tag_field = ft.TextField(
            hint_text="输入考点后回车添加（tag）",
            width=260,
            on_submit=lambda e, p=point: self._add_tag(p, e.control.value, e.control),
        )

        inferred = ft.Column(
            [ft.Text("、".join(point.inferred_tags) or "（生成前生成）", size=12)],
            spacing=4,
        )

        suggestion_key = (point.chapter_order, point.order)
        suggesting = suggestion_key in self.suggestion_busy

        controls: list[ft.Control] = [
            ft.Row(
                [
                    ft.Text(
                        f"{index + 1}. {point.name}",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        expand=True,
                    ),
                    ft.Text(
                        f"{point.chapter_name} ｜ {point.question_count} 题",
                        size=11,
                        color=Palette.TEXT_MUTED,
                    ),
                ]
            ),
            ft.Row(
                [
                    self._select(
                        "知识点等级",
                        point.level,
                        KNOWLEDGE_LEVELS,
                        lambda e, p=point: self._set_point_field(p, "level", e.control.value),
                        width=150,
                    ),
                    self._select(
                        "知识点类型",
                        point.knowledge_type,
                        KNOWLEDGE_TYPES,
                        lambda e, p=point: self._set_point_field(p, "knowledge_type", e.control.value),
                        width=150,
                    ),
                    secondary_button(
                        "建议中…" if suggesting else "AI 建议考点",
                        ft.Icons.HOURGLASS_TOP if suggesting else ft.Icons.AUTO_AWESOME,
                        lambda e, p=point: self._suggest_tags(p),
                        disabled=suggesting,
                    ),
                ],
                spacing=12,
                wrap=True,
            ),
            ft.Text("考点清单", size=12, weight=ft.FontWeight.W_600),
            tags_row,
            tag_field,
            ft.TextField(
                label="特殊要求",
                value=point.special_requirements,
                multiline=True,
                min_lines=1,
                max_lines=3,
                width=620,
                hint_text="平台不支持图片题，请描述为文字",
                on_change=lambda e, p=point: self._set_point_field(
                    p, "special_requirements", e.control.value
                ),
            ),
        ]

        candidate = self.suggested_tags.get((point.chapter_order, point.order))
        if candidate:
            controls.append(
                ft.ExpansionTile(
                    title=ft.Text(f"AI 建议考点（{len(candidate)} 个，点击选用）", size=12),
                    controls=[
                        ft.Row(
                            [
                                self._tag_chip(
                                    name,
                                    lambda value, p=point: self._add_tag(p, value, None),
                                    icon=ft.Icons.ADD,
                                )
                                for name in candidate
                            ],
                            wrap=True,
                            spacing=6,
                        )
                    ],
                    expanded=True,
                )
            )

        if point.inferred_tags:
            controls.append(
                ft.ExpansionTile(
                    title=ft.Text("自推考点清单（只读折叠区，可展开修改）", size=12),
                    controls=[
                        inferred,
                        ft.TextField(
                            value=",".join(point.inferred_tags),
                            multiline=True,
                            min_lines=1,
                            max_lines=2,
                            width=560,
                            on_change=lambda e, p=point: self._set_point_field(
                                p,
                                "inferred_tags",
                                [part.strip() for part in (e.control.value or "").replace("，", ",").split(",") if part.strip()],
                            ),
                        ),
                    ],
                    expanded=False,
                )
            )

        return self._card(None, controls)

    # ---------------------------------------------------------------- Step4
    def _step_four(self) -> list[ft.Control]:
        if not self.draft.all_points:
            return [
                self._card(
                    "④ 题量与题型",
                    [ft.Text("请先在 Step2 创建章节与知识点", size=13, color=Palette.TEXT_MUTED)],
                )
            ]

        global_card = self._card(
            "全局默认",
            [
                ft.Row(
                    [
                        ft.TextField(
                            label="每知识点题数",
                            value=str(self.global_defaults["question_count"]),
                            width=140,
                            keyboard_type=ft.KeyboardType.NUMBER,
                            on_change=lambda e: self._set_global_count(e.control.value),
                        ),
                        *[
                            ft.TextField(
                                label=f"{name}比例",
                                value=str(self.global_defaults["type_ratio"].get(name, 0)),
                                width=110,
                                keyboard_type=ft.KeyboardType.NUMBER,
                                on_change=lambda e, n=name: self._set_global_type_ratio(
                                    n, e.control.value
                                ),
                            )
                            for name in QUESTION_TYPES
                        ],
                        *[
                            ft.TextField(
                                label=f"{name}难度%",
                                value=str(self.global_defaults["difficulty_ratio"].get(name, 0)),
                                width=110,
                                keyboard_type=ft.KeyboardType.NUMBER,
                                on_change=lambda e, n=name: self._set_global_difficulty(
                                    n, e.control.value
                                ),
                            )
                            for name in DIFFICULTIES
                        ],
                        ft.Container(
                            content=primary_button(
                                "应用到全部知识点",
                                ft.Icons.DOWNLOAD_DONE,
                                self._apply_global_defaults,
                            ),
                            alignment=ft.Alignment(1, 0),
                        ),
                    ],
                    spacing=10,
                    wrap=True,
                ),
                # 不要与 expand 占位符同处一个 wrap Row（避免与上面那排输入框互相挤压）；
                # top margin 避开 Dropdown 浮动标签与上一行边框贴太紧
                ft.Container(
                    content=ft.Row(
                        [
                            self._distribution_toggle(),
                            self._sensitivity_select(),
                        ],
                        spacing=16,
                        wrap=True,
                    ),
                    margin=ft.Margin.only(top=10),
                ),
            ],
        )

        detail_card = self._card(
            f"明细（{self.distribution_view == 'counts' and '按题数' or '按比例'}）",
            [self._distribution_table()],
        )

        summary = self._summary_bar()
        return [global_card, detail_card, summary]

    def _sensitivity_select(self) -> ft.Control:
        return self._select(
            "澄清弹窗敏感度",
            self.draft.sensitivity,
            SENSITIVITY_LEVELS,
            self._set_sensitivity,
            width=160,
        )

    def _distribution_table(self) -> ft.Control:
        header = ft.Row(
            [
                ft.Text("知识点", size=12, weight=ft.FontWeight.W_600, expand=True),
                ft.Text("题数", size=12, weight=ft.FontWeight.W_600, width=70),
                *[
                    ft.Text(name, size=12, weight=ft.FontWeight.W_600, width=70)
                    for name in QUESTION_TYPES
                ],
                ft.Text("状态", size=12, weight=ft.FontWeight.W_600, width=90),
                ft.Text("", width=40),
            ],
            spacing=6,
        )

        rows: list[ft.Control] = [header, ft.Divider(height=6, color=Palette.BORDER)]

        for point in self.draft.all_points:
            rows.append(self._distribution_row(point))

        return ft.Column(rows, spacing=6)

    def _distribution_row(self, point: KnowledgePoint) -> ft.Control:
        def on_count(value: str) -> None:
            point.set_question_count(self._int_value(value, DEFAULT_QUESTION_COUNT))
            self._mark_overridden(point)

        def on_type(name: str, value: str) -> None:
            number = self._int_value(value, 0)
            if self.distribution_view == "counts":
                counts = dict(point.type_counts)
                counts[name] = number
                point.set_type_counts(counts)
            else:
                ratio = dict(point.type_ratio)
                ratio[name] = number
                point.set_type_ratio(ratio)
            self._mark_overridden(point)

        cells: list[ft.Control] = [
            ft.Text(point.name or "未命名", size=12, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.TextField(
                value=str(point.question_count),
                width=70,
                dense=True,
                text_size=12,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=lambda e: on_count(e.control.value),
            ),
        ]

        for name in QUESTION_TYPES:
            value = (
                point.type_counts.get(name, 0)
                if self.distribution_view == "counts"
                else point.type_ratio.get(name, 0)
            )
            cells.append(
                ft.TextField(
                    value=str(value),
                    width=70,
                    dense=True,
                    text_size=12,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=lambda e, n=name: on_type(n, e.control.value),
                )
            )

        issues = self.validator.validate_step(
            CourseDraft(chapters=[Chapter(knowledge_points=[point])]), 4
        )
        if point.overridden:
            badge = ft.Container(
                content=ft.Text("已覆盖", size=10, color=Palette.WARNING, weight=ft.FontWeight.BOLD),
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                bgcolor=Palette.WARNING_SOFT,
                border_radius=8,
                width=90,
            )
        else:
            badge = ft.Container(
                content=ft.Text("默认", size=10, color=Palette.TEXT_MUTED),
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                bgcolor=Palette.SURFACE_ALT,
                border_radius=8,
                width=90,
            )

        cells.append(badge)
        cells.append(
            ft.IconButton(
                ft.Icons.RESTART_ALT,
                icon_size=16,
                tooltip="恢复默认",
                on_click=lambda e, p=point: self._reset_point_distribution(p),
            )
        )

        row = ft.Row(cells, spacing=6)
        if issues:
            return ft.Column(
                [
                    row,
                    ft.Text("；".join(issues), size=11, color=Palette.DANGER),
                ],
                spacing=2,
            )
        return row

    def _summary_bar(self) -> ft.Control:
        points = self.draft.all_points
        total = sum(point.question_count for point in points)
        per_type = {
            name: sum(point.type_counts.get(name, 0) for point in points)
            for name in QUESTION_TYPES
        }
        cost = estimate_cost(len(points), total)

        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(f"知识点 {len(points)} 个", size=12, weight=ft.FontWeight.W_600),
                    ft.Text("｜", size=12, color=Palette.TEXT_SOFT),
                    ft.Text(f"总题数 {total} 题", size=12, weight=ft.FontWeight.W_600),
                    ft.Text("｜", size=12, color=Palette.TEXT_SOFT),
                    *[
                        ft.Text(f"{name} {per_type[name]}", size=12)
                        for name in QUESTION_TYPES
                    ],
                    ft.Text("｜", size=12, color=Palette.TEXT_SOFT),
                    ft.Text(
                        f"预计输出 {cost['total_tokens']} tokens（约 {cost['cost']} 元）",
                        size=12,
                        color=Palette.TEXT_MUTED,
                    ),
                ],
                spacing=8,
                wrap=True,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=Palette.PRIMARY_SOFT,
            border_radius=Radius.MEDIUM,
        )

    # ---------------------------------------------------------------- Step5
    def _step_five(self) -> list[ft.Control]:
        pending = len(self.queue.pending())
        records = summarize_records(self.draft.clarification_records)

        status = {
            "idle": "未开始",
            "running": "生成中",
            "paused": "已暂停",
            "complete": "已完成",
            "cancelled": "已取消",
        }.get(self.draft.generation_status, self.draft.generation_status)

        total_points = len(self.draft.all_points)
        completed = 0
        if self.controller is not None:
            completed = self.controller.progress[0]

        header = self._card(
            "⑤ AI 生成",
            [
                ft.Row(
                    [
                        self._status_chip(f"状态：{status}", Palette.PRIMARY, Palette.PRIMARY_SOFT),
                        self._status_chip(
                            f"进度：{completed}/{total_points}",
                            Palette.ACCENT,
                            Palette.ACCENT_SOFT,
                        ),
                        self._status_chip(
                            f"待澄清 {pending}",
                            Palette.DANGER if pending else Palette.TEXT_MUTED,
                            Palette.WARNING_SOFT if pending else Palette.SURFACE_ALT,
                        ),
                        self._status_chip(
                            f"澄清记录 {records['total']}",
                            Palette.TEXT_MUTED,
                            Palette.SURFACE_ALT,
                        ),
                        *(
                            [
                                self._status_chip(
                                    "草稿已修改，需重新生成",
                                    Palette.WARNING,
                                    Palette.WARNING_SOFT,
                                )
                            ]
                            if generation_is_stale(self.draft)
                            else []
                        ),
                    ],
                    spacing=10,
                    wrap=True,
                ),
                # 操作按钮单独一行：wrap Row 里不能放 expand 占位符
                # （Flutter 的 Wrap 不支持 Expanded，只会渲染成灰块并挤掉后续控件）
                ft.Row(
                    [
                        ft.TextButton(
                            "待澄清队列",
                            icon=ft.Icons.QUESTION_ANSWER_OUTLINED,
                            disabled=not pending,
                            on_click=self._open_clarifications,
                        ),
                        ft.TextButton(
                            "查看澄清记录",
                            icon=ft.Icons.HISTORY,
                            disabled=not records["total"],
                            on_click=self._show_clarification_records,
                        ),
                    ],
                    spacing=10,
                ),
                ft.ProgressBar(
                    value=(completed / total_points) if total_points else 0.0,
                    color=Palette.PRIMARY,
                    bgcolor=Palette.SURFACE_ALT,
                    bar_height=10,
                ),
                ft.Text(
                    "生成过程按知识点逐个进行；只有出问题的知识点会被挂起，其余继续。"
                    "澄清队列清空且全部完成后自动进入第⑥步。",
                    size=12,
                    color=Palette.TEXT_MUTED,
                ),
            ],
        )

        inference_card = self._inference_preview_card()

        log_card = self._card(
            "生成日志",
            [
                # 用 Row + expand 强制撑满卡片宽度（仅靠 Column 会按内容缩宽）
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(line, size=11, selectable=True)
                                    for line in (self.logs[-40:] or ["（暂无日志）"])
                                ],
                                scroll=ft.ScrollMode.AUTO,
                                spacing=2,
                            ),
                            height=_LOG_PANEL_HEIGHT,
                            padding=10,
                            bgcolor=Palette.SURFACE_ALT,
                            border=ft.Border.all(1, Palette.BORDER),
                            border_radius=Radius.SMALL,
                            expand=True,
                        )
                    ]
                )
            ],
        )

        return [header, inference_card, log_card]

    def _inference_preview_card(self) -> ft.Control:
        """FR3.4：自推考点清单在生成前以只读折叠区展示。"""
        inferred = [
            point for point in self.draft.all_points
            if not point.tags and point.inferred_tags
        ]
        if not inferred:
            return ft.Container(visible=False)

        return self._card(
            "自推考点清单（生成前请过目）",
            [
                ft.ExpansionTile(
                    title=ft.Text(f"{len(inferred)} 个知识点使用了自推考点", size=13),
                    controls=[
                        ft.Column(
                            [
                                ft.Text(
                                    f"{point.chapter_order}-{point.order} {point.name}："
                                    + "、".join(point.inferred_tags),
                                    size=11,
                                )
                                for point in inferred
                            ],
                            spacing=3,
                        )
                    ],
                    expanded=self.draft.force_review_inferred_tags,
                )
            ],
        )

    def _build_generation_actions(self) -> list[ft.Control]:
        status = self.draft.generation_status
        stale = generation_is_stale(self.draft)
        actions: list[ft.Control] = []

        if status in ("running", "paused"):
            actions.append(
                secondary_button(
                    "继续" if status == "paused" else "暂停",
                    ft.Icons.PLAY_ARROW if status == "paused" else ft.Icons.PAUSE,
                    self._toggle_pause,
                )
            )
            actions.append(
                secondary_button("取消", ft.Icons.STOP, self._cancel_generation)
            )
        elif status == "complete" and not stale:
            # 已完成且草稿未改：允许重生成，也可直接下一步
            actions.append(
                secondary_button("重新生成", ft.Icons.REFRESH, self._start_generation)
            )
            actions.append(
                primary_button("下一步", ft.Icons.ARROW_FORWARD, self._next)
            )
        elif status == "complete" and stale:
            # 草稿已改：旧产物不再对应当前草稿，强制重新生成
            actions.append(
                primary_button("重新生成", ft.Icons.AUTO_AWESOME, self._start_generation)
            )
        else:
            actions.append(
                primary_button("开始生成", ft.Icons.AUTO_AWESOME, self._start_generation)
            )

        if status == "complete" and pending_clarifications(self.draft):
            actions.insert(
                0,
                secondary_button(
                    "处理待澄清",
                    ft.Icons.QUESTION_ANSWER_OUTLINED,
                    self._open_clarifications,
                ),
            )

        return actions

    # ---------------------------------------------------------------- Step6
    def _step_six(self) -> list[ft.Control]:
        summary = review_summary(self.draft)
        ok, blockers = ready_for_export(self.draft)
        warnings = answer_distribution_warning(
            [q for point in self.draft.all_points for q in point.questions]
        )

        overview = self._card(
            "⑥ 结果与导出",
            [
                ft.Row(
                    [
                        self._status_chip(
                            f"知识点 {len(points_for_export(self.draft))} 个",
                            Palette.PRIMARY,
                            Palette.PRIMARY_SOFT,
                        ),
                        self._status_chip(
                            f"题目 {summary.question_count} 道",
                            Palette.ACCENT,
                            Palette.ACCENT_SOFT,
                        ),
                        self._status_chip(
                            f"已审核 {summary.reviewed}/{summary.question_count}",
                            Palette.TEXT,
                            Palette.SURFACE_ALT,
                        ),
                        self._status_chip(
                            f"绿 {summary.green}",
                            Palette.ACCENT,
                            Palette.ACCENT_SOFT,
                        ),
                        self._status_chip(
                            f"黄 {summary.amber}",
                            Palette.WARNING,
                            Palette.WARNING_SOFT,
                        ),
                        self._status_chip(
                            f"红 {summary.red}",
                            Palette.DANGER,
                            ft.Colors.with_opacity(0.12, Palette.DANGER),
                        ),
                    ],
                    spacing=8,
                    wrap=True,
                ),
                # 同上：操作按钮不能放在 wrap Row 里
                ft.Row(
                    [
                        ft.TextButton(
                            "查看澄清记录",
                            icon=ft.Icons.HISTORY,
                            disabled=not self.draft.clarification_records,
                            on_click=self._show_clarification_records,
                        ),
                    ],
                    spacing=8,
                ),
                # 非阻断的质量提醒：答案位置过于集中（学生可靠猜答案得分）
                *(
                    [
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.LIGHTBULB_OUTLINE,
                                        size=16,
                                        color=Palette.WARNING,
                                    ),
                                    ft.Text(
                                        "；".join(warnings),
                                        size=12,
                                        color=Palette.TEXT_MUTED,
                                        expand=True,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=10,
                            bgcolor=Palette.WARNING_SOFT,
                            border_radius=Radius.SMALL,
                        )
                    ]
                    if warnings
                    else []
                ),
                self._export_format_row(),
                *(
                    [
                        ft.Container(
                            content=ft.Text(
                                "导出前需处理：" + "；".join(blockers[:4]),
                                size=12,
                                color=Palette.DANGER,
                            ),
                            padding=10,
                            bgcolor=Palette.WARNING_SOFT,
                            border_radius=Radius.SMALL,
                        )
                    ]
                    if not ok
                    else []
                ),
            ],
        )

        tree = self._card("课程 → 章节 → 知识点（列表顺序即导出顺序）", self._result_tree())
        return [overview, tree]

    def _export_format_row(self) -> ft.Control:
        def on_word(e):
            self.draft.export_word = bool(e.control.value)
            self._save()

        def on_excel(e):
            self.draft.export_excel = bool(e.control.value)
            self._save()

        # ⚠ 不要用 wrap=True：实测（探针页）ft.Checkbox / ft.Switch 放在 wrap Row
        # 里会各自独占一行（Word / Excel 被竖排），且 wrap Row 会按内容缩宽。
        # 普通 ft.Row 既能横排又能撑满可用宽度。
        return ft.Row(
            [
                ft.Text("导出格式", size=12, weight=ft.FontWeight.W_600),
                ft.Checkbox(label="Word", value=self.draft.export_word, on_change=on_word),
                ft.Checkbox(label="Excel", value=self.draft.export_excel, on_change=on_excel),
                ft.Text("逐题审核", size=12, weight=ft.FontWeight.W_600),
                ft.Switch(
                    value=self.draft.review_mode == "逐题",
                    on_change=lambda e: self._set_review_mode(e.control.value),
                ),
            ],
            spacing=16,
        )

    def _result_tree(self) -> ft.Control:
        rows: list[ft.Control] = []

        for chapter in self.draft.chapters:
            rows.append(
                ft.Container(
                    content=ft.Text(
                        f"{chapter.order}. {chapter.name}（{len(chapter.knowledge_points)} 个知识点）",
                        size=13,
                        weight=ft.FontWeight.W_600,
                    ),
                    padding=ft.Padding.symmetric(vertical=4),
                )
            )
            for point in chapter.knowledge_points:
                rows.append(self._point_result_block(point))

        return ft.Column(rows, spacing=6)

    def _point_result_block(self, point: KnowledgePoint) -> ft.Control:
        summary = review_summary(
            CourseDraft(chapters=[Chapter(knowledge_points=[point])])
        )
        skipped = point.skipped or not point.questions

        header_cells: list[ft.Control] = [
            ft.Icon(
                ft.Icons.CHECK_CIRCLE if not skipped else ft.Icons.REMOVE_CIRCLE_OUTLINE,
                size=16,
                color=Palette.TEXT_SOFT if skipped else Palette.ACCENT,
            ),
            ft.Text(
                f"{point.chapter_order}-{point.order} {point.name}",
                size=13,
                expand=True,
                color=Palette.TEXT_SOFT if skipped else Palette.TEXT,
                weight=ft.FontWeight.W_600,
            ),
            ft.Text(f"{summary.question_count} 题", size=11, color=Palette.TEXT_MUTED),
            ft.Text(
                f"绿{summary.green}/黄{summary.amber}/红{summary.red}",
                size=11,
                color=Palette.TEXT_MUTED,
            ),
        ]

        if skipped:
            header_cells.append(
                ft.TextButton(
                    "补生成",
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    on_click=lambda e, p=point: self._regenerate_point(p, only_missing=True),
                )
            )
        else:
            header_cells.extend(
                [
                    ft.TextButton(
                        "预览/编辑",
                        icon=ft.Icons.EDIT_NOTE,
                        on_click=lambda e, p=point: self._toggle_preview(p),
                    ),
                    ft.TextButton(
                        "重生成",
                        icon=ft.Icons.REFRESH,
                        on_click=lambda e, p=point: self._regenerate_point(p, only_missing=False),
                    ),
                ]
            )

        expanded = point.name in self.review_expanded and bool(point.questions)
        if expanded:
            header_cells.extend(
                [
                    ft.TextButton(
                        "批量确认",
                        icon=ft.Icons.DONE_ALL,
                        on_click=lambda e, p=point: self._set_point_reviewed(p, True),
                    ),
                    ft.TextButton(
                        "取消全部确认",
                        icon=ft.Icons.REMOVE_DONE,
                        on_click=lambda e, p=point: self._set_point_reviewed(p, False),
                    ),
                ]
            )

        controls: list[ft.Control] = [ft.Row(header_cells, spacing=8)]

        if expanded:
            controls.extend(
                self._question_row(point, index, question)
                for index, question in enumerate(point.questions)
            )

        return ft.Container(
            content=ft.Column(controls, spacing=6),
            padding=12,
            bgcolor=Palette.SURFACE_ALT if skipped else Palette.SURFACE,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.SMALL,
            margin=ft.Margin.only(left=16),
        )

    def _question_row(self, point: KnowledgePoint, index: int, question: Question) -> ft.Control:
        color = CONFIDENCE_COLORS.get(question.confidence_color, Palette.TEXT_MUTED)

        def on_stem(e):
            question.stem = e.control.value
            self._save()

        def on_answer(e):
            question.answer = (e.control.value or "").strip().upper()
            self._save()

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    f"{question.confidence:.2f}",
                                    size=10,
                                    color=Palette.SURFACE,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                bgcolor=color,
                                border_radius=8,
                            ),
                            ft.Text(question.internal_id or "-", size=11, color=Palette.TEXT_MUTED),
                            ft.Text(question.question_type, size=11, color=Palette.TEXT_MUTED),
                            ft.Text(question.difficulty, size=11, color=Palette.TEXT_MUTED),
                            ft.Container(expand=True),
                            ft.Checkbox(
                                label="已确认",
                                value=question.reviewed,
                                on_change=lambda e, q=question: self._toggle_reviewed(q, e.control.value),
                            ),
                            ft.TextButton(
                                "重生成",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda e, p=point, i=index: self._regenerate_question(p, i),
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.TextField(
                        value=question.stem,
                        multiline=True,
                        min_lines=1,
                        max_lines=2,
                        text_size=12,
                        expand=True,
                        on_change=on_stem,
                    ),
                    ft.Container(
                        content=ft.TextField(
                            value=question.answer,
                            label="答案（如 A / BC）",
                            width=170,
                            dense=True,
                            text_size=12,
                            on_change=on_answer,
                        ),
                        # 给 Dropdown/TextField 的浮动标签留出空间，避免与上一行边框重叠
                        margin=ft.Margin.only(top=12),
                    ),
                    self._question_options(question),
                ],
                spacing=4,
            ),
            padding=10,
            bgcolor=Palette.SURFACE_ALT,
            border_radius=Radius.SMALL,
        )

    # ================================================================ 通用控件
    def _card(self, title: Optional[str], controls) -> ft.Control:
        """构建标准卡片；``controls`` 可以是控件列表或单个控件。"""
        if isinstance(controls, ft.Control):
            items: list[ft.Control] = [controls]
        else:
            items = list(controls)

        content: list[ft.Control] = []
        if title:
            content.append(
                ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=Palette.TEXT)
            )
        content.extend(items)
        return surface_card(ft.Column(content, spacing=12))

    def _select(
        self,
        label: str,
        value: str,
        options: tuple[str, ...] | list[str],
        on_select: Callable,
        *,
        width: int = 190,
    ) -> ft.Dropdown:
        return ft.Dropdown(
            label=label,
            value=str(value),
            width=width,
            options=[ft.DropdownOption(key=str(item), text=str(item)) for item in options],
            on_select=on_select,
            dense=True,
            text_size=12,
        )

    def _status_chip(self, label: str, color: str, bgcolor: str) -> ft.Control:
        return ft.Container(
            content=ft.Text(label, size=11, color=color, weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            bgcolor=bgcolor,
            border_radius=20,
        )

    def _tag_chip(self, text: str, on_delete: Callable, *, icon=None) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon or ft.Icons.CLOSE, size=12, color=Palette.PRIMARY),
                    ft.Text(text, size=11, color=Palette.PRIMARY_DARK),
                ],
                spacing=2,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            bgcolor=Palette.PRIMARY_SOFT,
            border_radius=12,
            on_click=lambda e: on_delete(text),
        )

    def _candidate_chip(self, name: str) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, size=12, color=Palette.PRIMARY),
                    ft.Text(name, size=11),
                ],
                spacing=2,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
            border=ft.Border.all(1, Palette.BORDER_STRONG),
            border_radius=12,
            on_click=lambda e, n=name: self._accept_candidate(n),
        )

    # ================================================================ 状态与持久化
    def _set_field(self, name: str, value: Any) -> None:
        setattr(self.draft, name, value)
        self._save()

    def _save(self) -> None:
        self.store.mark_dirty()
        self.store.flush_if_due(self.draft)

    def _save_now(self) -> None:
        self.store.flush(self.draft, force=True)

    def _new_draft(self, e=None) -> None:
        """清空草稿重新开始（已经导出的 zip 不受影响）。"""

        def do_reset():
            self.store.clear()
            self.draft = CourseDraft()
            self.queue = ClarificationQueue(
                sensitivity=self.draft.sensitivity,
                on_record=self._on_clarification_record,
            )
            self.controller = None
            self.progress = None
            self.logs = []
            self.selected_chapter_index = 0
            self.suggested_tags = {}
            self.review_expanded = set()
            self.message = ""
            self._save_now()
            self._render()
            show_snack(self.page, "已新建草稿", color=Palette.ACCENT)

        show_confirm_dialog(
            self.page,
            "新建草稿",
            "将清空当前课程、章节、知识点、生成结果与澄清记录（已导出的文件不受影响）。确定继续？",
            lambda ev: do_reset(),
            icon=ft.Icons.NOTE_ADD_OUTLINED,
        )

    def _set_point_field(self, point: KnowledgePoint, name: str, value: Any) -> None:
        setattr(point, name, value)
        self._save()

    def _mark_overridden(self, point: KnowledgePoint) -> None:
        point.overridden = True
        self._save()

    @staticmethod
    def _int_value(raw: Any, fallback: int) -> int:
        try:
            return max(int(str(raw).strip()), 0)
        except (TypeError, ValueError):
            return fallback

    def _set_global_count(self, raw: str) -> None:
        self.global_defaults["question_count"] = self._int_value(raw, DEFAULT_QUESTION_COUNT)

    def _set_global_type_ratio(self, name: str, raw: str) -> None:
        self.global_defaults["type_ratio"][name] = self._int_value(raw, 0)

    def _set_global_difficulty(self, name: str, raw: str) -> None:
        self.global_defaults["difficulty_ratio"][name] = self._int_value(raw, 0)

    def _set_global_detail(self, name: str, value: Any) -> None:
        self.global_details[name] = value

    def _set_sensitivity(self, e) -> None:
        self.draft.sensitivity = e.control.value or DEFAULT_SENSITIVITY
        self.queue.sensitivity = self.draft.sensitivity
        self._save()
        self._render()

    def _set_review_mode(self, enabled: bool) -> None:
        self.draft.review_mode = "逐题" if enabled else "按项"
        self._save()
        self._render()

    def _distribution_toggle(self) -> ft.Control:
        """［按题数｜按比例］切换（FR4.3）。

        这里用两个 TextButton 手搭分段控件，而不是 ``ft.SegmentedButton``：
        本机 Flet 0.82 的 SegmentedButton 在中文标签下会算错段宽，把文字
        挤压/截断（已用探针页对照验证）。plugin_center_view 的视图切换
        也是同一个写法，保持一致。
        """

        def make(value: str, label: str) -> ft.TextButton:
            active = self.distribution_view == value
            return ft.TextButton(
                label,
                on_click=lambda e, v=value: self._set_distribution_view(v),
                style=ft.ButtonStyle(
                    color=Palette.SURFACE if active else Palette.TEXT_MUTED,
                    bgcolor=Palette.PRIMARY if active else Palette.SURFACE_ALT,
                    shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                    padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                    text_style=Fonts.text(
                        size=13,
                        weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
                    ),
                ),
            )

        return ft.Container(
            content=ft.Row(
                [make("counts", "按题数"), make("ratio", "按比例")],
                spacing=4,
                tight=True,
            ),
            padding=4,
            bgcolor=Palette.SURFACE_ALT,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.MEDIUM,
        )

    def _set_distribution_view(self, value: str) -> None:
        self.distribution_view = "ratio" if value == "ratio" else "counts"
        self._save()
        self._render()

    def _on_distribution_view_change(self, e) -> None:
        """保留事件式入口（供外部/测试调用）；内部切换走 :meth:`_set_distribution_view`。

        事件携带空选择（``[]`` / ``None``）时**保持当前视图不变**，
        避免清空选择把用户已选的视图莫名重置。
        """
        selected = getattr(e.control, "selected", None)
        if isinstance(selected, (set, tuple)):
            selected = list(selected)
        if not selected:
            return
        self._set_distribution_view(selected[0])

    # ================================================================ 章节/知识点操作
    def _select_chapter(self, index: int) -> None:
        self.selected_chapter_index = index
        self._render()

    def _add_chapter(self, e) -> None:
        self._prompt_text(
            "新建章节",
            "章节名称",
            f"新章节 {len(self.draft.chapters) + 1}",
            self._commit_chapter,
        )

    def _commit_chapter(self, name: str) -> None:
        self.draft.chapters.append(Chapter(name=name))
        self.draft.renumber()
        self.selected_chapter_index = len(self.draft.chapters) - 1
        self._save_now()
        self._render()

    def _edit_chapter(self, index: int) -> None:
        chapter = self.draft.chapters[index]
        self._prompt_text("编辑章节", "章节名称", chapter.name, lambda text: self._rename_chapter(index, text))

    def _rename_chapter(self, index: int, name: str) -> None:
        self.draft.chapters[index].name = name
        self.draft.renumber()
        self._save()
        self._render()

    def _delete_chapter(self, index: int) -> None:
        chapter = self.draft.chapters[index]

        def do_delete():
            self.draft.chapters.pop(index)
            self.draft.renumber()
            self.selected_chapter_index = max(min(self.selected_chapter_index, len(self.draft.chapters) - 1), 0)
            self._save()
            self._render()

        show_confirm_dialog(
            self.page,
            "删除章节",
            f"确定删除「{chapter.name}」及其 {len(chapter.knowledge_points)} 个知识点？",
            lambda e: do_delete(),
        )

    def _on_chapter_reorder(self, e) -> None:
        old, new = e.old_index, e.new_index
        if old is None or new is None or old == new:
            return
        chapter = self.draft.chapters.pop(old)
        self.draft.chapters.insert(new, chapter)
        self.draft.renumber()
        self.selected_chapter_index = new
        self._save_now()
        self._render()

    def _add_point(self, e) -> None:
        self._prompt_text("新建知识点", "知识点名称", "", lambda text: self._add_points([text]))

    def _add_points(self, names: list[str]) -> None:
        if not self.draft.chapters:
            show_snack(self.page, "请先创建章节", color=Palette.WARNING)
            return
        chapter = self.draft.chapters[self.selected_chapter_index]
        for name in names:
            text = str(name).strip()
            if not text:
                continue
            chapter.knowledge_points.append(KnowledgePoint(name=text))
        self.draft.renumber()
        self._sync_existing_points()
        self._save_now()
        self._render()

    def _sync_existing_points(self) -> None:
        """把新知识点的默认题量/题型同步为 Step4 全局默认，避免首屏就是「已覆盖」。"""
        apply_global_defaults(
            self.draft,
            question_count=self.global_defaults["question_count"],
            type_ratio=self.global_defaults["type_ratio"],
            difficulty_ratio=self.global_defaults["difficulty_ratio"],
            targets=[
                point for point in self.draft.all_points if not point.questions and not point.overridden
            ],
        )

    def _edit_point(self, index: int) -> None:
        chapter = self.draft.chapters[self.selected_chapter_index]
        point = chapter.knowledge_points[index]
        self._prompt_text("编辑知识点", "知识点名称", point.name, lambda text: self._rename_point(index, text))

    def _rename_point(self, index: int, name: str) -> None:
        chapter = self.draft.chapters[self.selected_chapter_index]
        chapter.knowledge_points[index].name = name
        self.draft.renumber()
        self._save()
        self._render()

    def _delete_point(self, index: int) -> None:
        chapter = self.draft.chapters[self.selected_chapter_index]
        point = chapter.knowledge_points[index]

        def do_delete():
            chapter.knowledge_points.pop(index)
            self.draft.renumber()
            self._save()
            self._render()

        show_confirm_dialog(
            self.page, "删除知识点", f"确定删除「{point.name}」？", lambda e: do_delete()
        )

    def _on_point_reorder(self, e) -> None:
        old, new = e.old_index, e.new_index
        if old is None or new is None or old == new:
            return
        chapter = self.draft.chapters[self.selected_chapter_index]
        point = chapter.knowledge_points.pop(old)
        chapter.knowledge_points.insert(new, point)
        self.draft.renumber()
        self._save_now()
        self._render()

    def _prompt_text(self, title: str, label: str, value: str, on_submit: Callable[[str], None]) -> None:
        field = ft.TextField(label=label, value=value, autofocus=True, width=380)

        def submit(_):
            text = (field.value or "").strip()
            if not text:
                show_snack(self.page, f"{label}不能为空", color=Palette.WARNING)
                return
            self.page.pop_dialog()
            on_submit(text)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=field,
            actions=[
                ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                ft.FilledButton(
                    "确定",
                    on_click=submit,
                    style=ft.ButtonStyle(
                        bgcolor=Palette.PRIMARY,
                        color=Palette.SURFACE,
                        shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                        text_style=Fonts.text(size=14, weight=ft.FontWeight.W_600),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        field.on_submit = submit
        self.page.show_dialog(dialog)

    # ================================================================ AI 辅助
    def _settings_schema(self) -> list[dict]:
        import json

        try:
            payload = json.loads(
                (self.plugin_dir / "manifest.json").read_text(encoding="utf-8")
            )
        except Exception:  # noqa: BLE001
            payload = {}
        return payload.get("settings_schema") or []

    def _config(self) -> dict[str, Any]:
        schema = self._settings_schema()
        settings_manager = self._settings_manager()
        values: dict[str, Any] = {}

        for field in schema:
            stored = None
            if self.context is not None and hasattr(self.context, "get_plugin_config"):
                stored = self.context.get_plugin_config(field["key"])
            elif settings_manager is not None:
                stored = settings_manager.get_plugin_config(PLUGIN_ID, field["key"])
            values[field["key"]] = setting_value(field, stored)

        values.setdefault("base_url", DEFAULT_BASE_URL)
        values.setdefault("model", DEFAULT_MODEL)
        values.setdefault("exa_mcp_url", DEFAULT_EXA_MCP_URL)
        return values

    def _settings_manager(self):
        if self.context is not None and hasattr(self.context, "settings_manager"):
            return self.context.settings_manager
        return getattr(self.main_app, "settings_manager", None)

    def _build_clients(self) -> tuple[StructuredAIClient, Optional[HttpMcpSearchClient]]:
        config = self._config()
        ai = StructuredAIClient(config, logger=self._log)
        search = (
            HttpMcpSearchClient(config, logger=self._log)
            if config.get("exa_mcp_url")
            else None
        )
        return ai, search

    def _open_settings(self, e=None) -> None:
        settings_manager = self._settings_manager()
        if settings_manager is None:
            show_error_dialog(self.page, "无法打开设置", "设置服务不可用")
            return
        dialog = build_plugin_settings_dialog(
            self.page,
            PLUGIN_ID,
            PLUGIN_NAME,
            self._settings_schema(),
            settings_manager,
        )
        self.page.show_dialog(dialog)

    def _require_ai_config(self) -> bool:
        """检查 AI 配置；缺失时给出引导并返回 False。"""
        try:
            self._build_clients()[0].ensure_configured()
            return True
        except AIConfigError as exc:
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.KEY_OFF, color=Palette.WARNING),
                        ft.Text("需要配置 AI", weight=ft.FontWeight.BOLD),
                    ],
                    spacing=10,
                ),
                content=ft.Column(
                    [
                        ft.Text(str(exc)),
                        ft.Text(
                            "请在插件设置中填写 AI API Key（默认已预填 DeepSeek 的 "
                            "Base URL 与模型，可自行修改）。",
                            size=12,
                            color=Palette.TEXT_MUTED,
                        ),
                    ],
                    spacing=8,
                    tight=True,
                ),
                actions=[
                    ft.TextButton("稍后", on_click=lambda _: self.page.pop_dialog()),
                    ft.FilledButton(
                        "打开设置",
                        on_click=lambda _: (self.page.pop_dialog(), self._open_settings()),
                        style=ft.ButtonStyle(
                            bgcolor=Palette.PRIMARY,
                            color=Palette.SURFACE,
                            text_style=Fonts.text(size=14, weight=ft.FontWeight.W_600),
                        ),
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)
            return False

    def _test_ai_connection(self, e=None) -> None:
        if self.ai_test_busy or not self._require_ai_config():
            return
        self.ai_test_busy = True
        self._render()
        show_snack(self.page, "正在测试 AI 连接…", color=Palette.PRIMARY)

        def work():
            client, _ = self._build_clients()
            return client.test_connection()

        def done(_result):
            self.ai_test_busy = False
            self._render()
            show_snack(self.page, "AI 连接测试成功", color=Palette.ACCENT)

        def failed(err):
            self.ai_test_busy = False
            self._render()
            show_error_dialog(self.page, "AI 连接测试失败", str(err))

        run_background_task(self.page, work, on_done=done, on_error=failed)

    def _suggest_tags(self, point: KnowledgePoint) -> None:
        key = (point.chapter_order, point.order)
        if key in self.suggestion_busy or not self._require_ai_config():
            return
        self.suggestion_busy.add(key)
        self._render()
        show_snack(self.page, f"正在为「{point.name}」建议考点…", color=Palette.PRIMARY)

        def work():
            client, _ = self._build_clients()
            payload = client.complete_json(
                system="你是一位资深的职业教育教师。",
                user=build_tag_suggestion_prompt(
                    self.draft.course_name, point.chapter_name, point.name
                ),
            )
            return parse_tag_suggestion(payload)

        def done(tags):
            self.suggestion_busy.discard(key)
            self.suggested_tags[key] = tags
            self._render()
            show_snack(self.page, f"已建议 {len(tags)} 个考点", color=Palette.ACCENT)

        def failed(err):
            self.suggestion_busy.discard(key)
            self._render()
            show_error_dialog(self.page, "AI 建议失败", str(err))

        run_background_task(self.page, work, on_done=done, on_error=failed)

    # ================================================================ Step3 操作
    def _add_tag(self, point: KnowledgePoint, raw: str, field: Optional[ft.TextField]) -> None:
        text = str(raw or "").strip()
        if text and text not in point.tags:
            point.tags.append(text)
            self._save()
        if field is not None:
            field.value = ""
        self._render()

    def _remove_tag(self, point: KnowledgePoint, tag: str) -> None:
        if tag in point.tags:
            point.tags.remove(tag)
            self._save()
            self._render()

    def _apply_global_details(self, e) -> None:
        affected = apply_global_details(
            self.draft,
            level=self.global_details["level"],
            knowledge_type=self.global_details["knowledge_type"],
            tags=self.global_details["tags"] or None,
            only_unfilled=True,
        )
        self._save_now()
        self._render()
        show_snack(self.page, f"已应用到 {affected} 个知识点")

    # ================================================================ Step4 操作
    def _apply_global_defaults(self, e) -> None:
        ratio = self.global_defaults["type_ratio"]
        if sum(max(int(value or 0), 0) for value in ratio.values()) <= 0:
            show_snack(self.page, "题型比例不能全为 0", color=Palette.WARNING)
            return

        affected = apply_global_defaults(
            self.draft,
            question_count=self.global_defaults["question_count"],
            type_ratio=ratio,
            difficulty_ratio=self.global_defaults["difficulty_ratio"],
        )
        self._save_now()
        self._render()
        show_snack(self.page, f"已应用到 {affected} 个知识点")

    def _reset_point_distribution(self, point: KnowledgePoint) -> None:
        apply_global_defaults(
            self.draft,
            question_count=self.global_defaults["question_count"],
            type_ratio=self.global_defaults["type_ratio"],
            difficulty_ratio=self.global_defaults["difficulty_ratio"],
            targets=[point],
        )
        point.overridden = False
        self._save_now()
        self._render()

    # ================================================================ 生成
    def _log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{stamp}] {message}")
        if len(self.logs) > 400:
            del self.logs[:200]
        if self.progress is not None:
            self.progress.append_log(f"[{stamp}] {message}")

    def _on_clarification_record(self, record: dict) -> None:
        self.draft.clarification_records.append(record)
        self._save()

    def _start_generation(self, e) -> None:
        if self.busy:
            show_snack(self.page, "正在生成中，请稍候", color=Palette.WARNING)
            return
        if not self.draft.all_points:
            show_snack(self.page, "请先创建知识点", color=Palette.WARNING)
            return
        if not self._require_ai_config():
            return

        # 生成前准备：自推考点 + 预览展示
        self._ensure_inferred_tags()
        assign_internal_ids(self.draft)

        # 重新生成会**替换**上一轮结果：先清空旧题，避免未被重新生成的
        # 知识点残留旧产物（旧题暂存，若本轮该知识点无产出则回填）
        previous_questions = {
            id(point): list(point.questions) for point in self.draft.all_points
        }
        previous_skipped = {id(point): point.skipped for point in self.draft.all_points}
        for point in self.draft.all_points:
            point.questions = []
            point.skipped = False

        self.queue = ClarificationQueue(
            sensitivity=self.draft.sensitivity,
            on_record=self._on_clarification_record,
        )
        self.busy = True
        self.draft.generation_status = "running"
        self.run = GenerationRun(
            f"run-{int(time.time())}",
        )
        self.run.start()
        self._save_now()

        ai, search = self._build_clients()
        self.controller = GenerationController(ai, search, self.queue, logger=self._log)

        total = len(self.draft.all_points)
        self.progress = AnswerProgressDialog(
            self.page,
            title="AI 生成中",
            theme="blue",
            show_log_panel=True,
            show_big_percent=True,
            width=560,
            on_stop=lambda e: self._cancel_generation(e),
        )
        self.page.show_dialog(self.progress.dialog)

        def progress_callback(current: int, total_count: int, message: str = "") -> None:
            if self.progress is None:
                return
            self.progress.update_progress(current, total_count, message)
            if message:
                self.progress.append_log(message)

        def on_point_start(point: KnowledgePoint) -> None:
            progress_callback(
                self.controller.progress[0] if self.controller else 0,
                total,
                f"正在生成：{point.name}",
            )

        def on_point_done(point: KnowledgePoint, questions) -> None:
            index = self.controller.progress[0] if self.controller else 0
            progress_callback(index, total, f"完成：{point.name}（{len(questions)} 题）")
            self._save()

        def work():
            return self.controller.run(
                self.draft,
                on_point_start=on_point_start,
                on_point_done=on_point_done,
                on_clarification=self._schedule_clarification,
            )

        def _close_progress():
            if self.progress is not None:
                self.progress.dialog.open = False

        def _restore_missing():
            """本轮没有产出的知识点，回填上一轮产物（避免重生成失败丢题）。"""
            for point in self.draft.all_points:
                if not point.questions:
                    fallback = previous_questions.get(id(point)) or []
                    if fallback:
                        point.questions = fallback
                        point.skipped = previous_skipped.get(id(point), False)

        def done(result):
            _close_progress()
            self.busy = False
            self._ensure_inferred_tags()
            _restore_missing()
            assign_internal_ids(self.draft)
            self.draft.generation_status = (
                "cancelled" if result.get("cancelled") else "complete"
            )
            if self.draft.generation_status == "complete":
                # 记录本轮输入指纹：之后任何出题相关修改都会被识别为「需重新生成」
                self.draft.generation_fingerprint = generation_fingerprint(self.draft)
            if self.run is not None:
                self.run.finish()
            self._save_now()

            pending = pending_clarifications(self.draft)
            self._render()
            if pending:
                show_snack(
                    self.page,
                    f"生成结束，仍有 {len(pending)} 项待澄清",
                    color=Palette.WARNING,
                )
            elif self.draft.generation_status == "complete":
                # FR5.4：澄清队列清空且全部生成完成 → 自动进入 Step6
                self._go(6)

        def failed(err):
            _close_progress()
            self.busy = False
            _restore_missing()
            self.draft.generation_status = "idle"
            self._save_now()
            self._render()
            show_error_dialog(self.page, "生成失败", str(err))

        run_background_task(
            self.page,
            work,
            on_done=done,
            on_error=failed,
        )

    def _ensure_inferred_tags(self) -> None:
        """FR3.3：考点全未填写时用「课程名＋章节名＋知识点名」自推。"""
        for point in self.draft.all_points:
            if point.tags or point.inferred_tags:
                continue
            parts = [self.draft.course_name, point.chapter_name, point.name]
            point.inferred_tags = [part for part in parts if part]

    def _toggle_pause(self, e) -> None:
        if self.controller is None:
            return
        if self.draft.generation_status == "paused":
            self.controller.resume()
            self.draft.generation_status = "running"
            if self.run is not None:
                self.run.resume()
        else:
            self.controller.pause()
            self.draft.generation_status = "paused"
            if self.run is not None:
                self.run.pause()
        self._save_now()
        self._render()

    def _cancel_generation(self, e=None) -> None:
        if self.controller is not None:
            self.controller.cancel()
        self.queue.release_all()
        if self.progress is not None:
            try:
                self.progress.dialog.open = False
            except Exception:  # noqa: BLE001
                pass
        self.draft.generation_status = "cancelled"
        self._save_now()
        self._render()

    # ---------------------------------------------------------- 澄清弹窗
    def _schedule_clarification(self, clarification: Clarification) -> None:
        """（worker 线程调用）只调度，绝不直接操作 UI。"""
        self.page.run_task(self._show_clarification_dialog, clarification)

    async def _show_clarification_dialog(self, clarification: Clarification) -> None:
        """（Flet 事件循环线程）展示澄清弹窗。"""
        if clarification.status != STATUS_PENDING:
            return
        self._clar_resolved = False
        self._clar_dialog = self._build_clarification_dialog(clarification)
        self._render()
        self.page.show_dialog(self._clar_dialog)

    def _build_clarification_dialog(self, clarification: Clarification) -> ft.AlertDialog:
        level_color = LEVEL_COLORS.get(clarification.level, Palette.PRIMARY)
        pending = self.queue.pending()
        index = pending.index(clarification) + 1 if clarification in pending else 1

        choice_field = ft.TextField(
            hint_text="也可以直接输入你的处理方式",
            width=430,
            dense=True,
        )
        same_kind = ft.Checkbox(label="本批次同类问题都按此处理", value=False)

        def submit(choice: str) -> None:
            value = (choice or choice_field.value or "").strip()
            if not value:
                show_snack(self.page, "请选择或输入处理方式", color=Palette.WARNING)
                return
            self._answer_clarification(clarification, value, same_kind.value)

        option_buttons = []
        for option in build_clarification_choices(
            recommended=clarification.recommended or (clarification.options or ["按推荐处理"])[0],
            alternatives=clarification.options,
        ):
            is_recommended = option == clarification.recommended
            option_buttons.append(
                ft.FilledButton(
                    option,
                    on_click=lambda e, value=option: submit(value),
                    style=ft.ButtonStyle(
                        bgcolor=Palette.PRIMARY_SOFT if is_recommended else Palette.SURFACE_ALT,
                        color=Palette.PRIMARY_DARK if is_recommended else Palette.TEXT,
                        shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                        text_style=Fonts.text(
                            size=12,
                            weight=ft.FontWeight.W_600 if is_recommended else ft.FontWeight.W_400,
                        ),
                    ),
                )
            )

        controls = [
            ft.Text(clarification.location or "本批次", size=12, color=Palette.TEXT_MUTED),
            ft.Text(clarification.question, size=13),
            ft.ExpansionTile(
                title=ft.Text("查看依据", size=12),
                controls=[ft.Text(clarification.basis or "（无附加依据）", size=11, selectable=True)],
                expanded=False,
            ),
            ft.Row(option_buttons, spacing=8, wrap=True),
            choice_field,
            same_kind,
            ft.Row(
                [
                    ft.TextButton(
                        "由AI自行决定",
                        on_click=lambda e: submit("由AI自行决定"),
                    ),
                    ft.TextButton(
                        "跳过该知识点",
                        on_click=lambda e: self._skip_clarification(clarification),
                    ),
                ],
                spacing=8,
            ),
        ]

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HELP_OUTLINE, color=level_color),
                    ft.Text(f"【{clarification.level}】需要确认", weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Text(f"澄清 {index}/{max(len(pending), 1)}", size=11, color=Palette.TEXT_MUTED),
                ],
                spacing=8,
            ),
            content=ft.Column(controls, spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.FilledButton(
                    "确认并继续",
                    on_click=lambda e: submit(choice_field.value),
                    style=ft.ButtonStyle(
                        bgcolor=Palette.PRIMARY,
                        color=Palette.SURFACE,
                        shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                        text_style=Fonts.text(size=14, weight=ft.FontWeight.W_600),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: self._defer_clarification(clarification),
        )
        return dialog

    def _answer_clarification(self, clarification: Clarification, choice: str, apply_to_kind: bool) -> None:
        if clarification.status != STATUS_PENDING:
            return

        # 该澄清之前已被关闭(×)（worker 已不再等待）→ 答复后需要重跑对应知识点
        was_deferred = bool(clarification.event_released)

        self._clar_resolved = True
        self._close_clar_dialog()
        self.queue.answer(
            clarification,
            choice,
            apply_to_kind=apply_to_kind,
            scope=f"{clarification.point_name or '本批次'}（单条）",
        )
        self._after_clarification()

        if was_deferred and "跳过" not in choice:
            self._resume_suspended_point(clarification.point_name)

    def _resume_suspended_point(self, point_name: str) -> None:
        """对之前挂起（关闭(×)）的知识点重跑生成，补齐缺失题目。"""
        target = next(
            (point for point in self.draft.all_points if point.name == point_name),
            None,
        )
        if target is None:
            return
        show_snack(self.page, f"正在为「{point_name}」补生成…", color=Palette.PRIMARY)
        self._regenerate_point(target, only_missing=True)

    def _defer_clarification(self, clarification: Clarification) -> None:
        """关闭(×) = 暂不回答；必须唤醒 worker，避免线程永久阻塞。"""
        if self._clar_resolved or clarification.status != STATUS_PENDING:
            return
        self._clar_resolved = True
        self.queue.defer(clarification)
        self._after_clarification()

    def _skip_clarification(self, clarification: Clarification) -> None:
        if clarification.status != STATUS_PENDING:
            return
        self._clar_resolved = True
        self._close_clar_dialog()
        self.queue.skip(clarification)
        for point in self.draft.all_points:
            if point.name == clarification.point_name:
                point.skipped = True
                self.queue.mark_point_skipped(point.chapter_order, point.order)
        self._after_clarification()

    def _close_clar_dialog(self) -> None:
        try:
            self.page.pop_dialog()
        except Exception as exc:  # noqa: BLE001
            print(f"[Evaluation] 关闭澄清弹窗失败: {exc}")
        self._clar_dialog = None

    def _after_clarification(self) -> None:
        self._save()
        self._render()
        # 队列里可能还有被关闭后遗留的挂起项，但 worker 已在推进；不自动连弹。

    def _open_clarifications(self, e) -> None:
        pending = self.queue.pending()
        if not pending:
            show_snack(self.page, "没有待澄清项", color=Palette.ACCENT)
            return
        self.page.run_task(self._show_clarification_dialog, pending[0])

    def _show_clarification_records(self, e) -> None:
        records = self.draft.clarification_records or []
        rows: list[ft.Control] = [
            ft.Row(
                [
                    ft.Text("时间", size=11, weight=ft.FontWeight.W_600, width=130),
                    ft.Text("级别", size=11, weight=ft.FontWeight.W_600, width=50),
                    ft.Text("问题", size=11, weight=ft.FontWeight.W_600, expand=True),
                    ft.Text("选择", size=11, weight=ft.FontWeight.W_600, width=120),
                    ft.Text("影响范围", size=11, weight=ft.FontWeight.W_600, width=160),
                ],
                spacing=6,
            ),
            ft.Divider(height=4, color=Palette.BORDER),
        ]

        for record in reversed(records):
            rows.append(
                ft.Row(
                    [
                        ft.Text(str(record.get("timestamp", "")), size=11, width=130),
                        ft.Text(str(record.get("level", "")), size=11, width=50),
                        ft.Text(str(record.get("question", ""))[:60], size=11, expand=True),
                        ft.Text(str(record.get("choice", ""))[:24], size=11, width=120),
                        ft.Text(str(record.get("scope", ""))[:28], size=11, width=160),
                    ],
                    spacing=6,
                )
            )

        dialog = ft.AlertDialog(
            modal=False,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HISTORY, color=Palette.PRIMARY),
                    ft.Text("澄清记录", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(rows, spacing=4, scroll=ft.ScrollMode.AUTO),
                width=900,
                height=420,
            ),
            actions=[ft.TextButton("关闭", on_click=lambda _: self.page.pop_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    # ---------------------------------------------------------- Step6 操作
    def _toggle_preview(self, point: KnowledgePoint) -> None:
        if point.name in self.review_expanded:
            self.review_expanded.discard(point.name)
        else:
            self.review_expanded.add(point.name)
        self._render()

    def _question_options(self, question: Question) -> ft.Control:
        """显示题目选项，并突出显示 AI 给出的正确答案。"""
        answer_letters = set(question.answer_letters)
        if not question.options:
            return ft.Text("暂无选项数据", size=11, color=Palette.WARNING)

        items = []
        for index, option in enumerate(question.options):
            letter = chr(ord("A") + index)
            correct = letter in answer_letters
            items.append(
                ft.Text(
                    f"{letter}. {option}{'  ✓ 正确答案' if correct else ''}",
                    size=12,
                    color=Palette.ACCENT if correct else Palette.TEXT,
                    weight=ft.FontWeight.W_600 if correct else ft.FontWeight.W_400,
                )
            )
        return ft.Container(
            content=ft.Column(items, spacing=3),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            bgcolor=Palette.SURFACE,
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.SMALL,
        )

    def _set_point_reviewed(self, point: KnowledgePoint, reviewed: bool) -> None:
        for question in point.questions:
            mark_reviewed(question, reviewed)
        self._save_now()
        self._render()
        action = "确认" if reviewed else "取消确认"
        show_snack(self.page, f"已{action}「{point.name}」的 {len(point.questions)} 道题")

    def _toggle_reviewed(self, question: Question, value: bool) -> None:
        mark_reviewed(question, value)
        self._save_now()

    def _regenerate_point(self, point: KnowledgePoint, *, only_missing: bool) -> None:
        if not self._require_ai_config():
            return
        self._ensure_inferred_tags()

        ai, search = self._build_clients()
        controller = GenerationController(ai, search, self.queue, logger=self._log)

        def work():
            return controller.generate_point(
                point,
                self.draft,
                on_clarification=self._schedule_clarification,
            )

        def done(questions):
            append_generated(point, questions, replace=not only_missing)
            assign_internal_ids(self.draft)
            self._save_now()
            self._render()
            show_snack(self.page, f"「{point.name}」已生成 {len(questions)} 题")

        run_background_task(
            self.page, work, on_done=done,
            on_error=lambda err: show_error_dialog(self.page, "生成失败", str(err)),
        )

    def _regenerate_question(self, point: KnowledgePoint, index: int) -> None:
        """重生成单题：临时只把该题交给生成器，产出后原位替换。"""
        if not self._require_ai_config():
            return

        ai, search = self._build_clients()
        controller = GenerationController(ai, search, self.queue, logger=self._log)
        original = list(point.questions)
        target = point.questions[index]

        def work():
            point.questions = [target]
            try:
                return controller.generate_point(
                    point, self.draft, on_clarification=self._schedule_clarification
                )
            finally:
                point.questions = original

        def done(questions):
            if questions:
                replace_question(point, index, questions[0])
            else:
                show_snack(self.page, "未生成新题，已保留原题", color=Palette.WARNING)
            assign_internal_ids(self.draft)
            self._save_now()
            self._render()

        run_background_task(
            self.page,
            work,
            on_done=done,
            on_error=lambda err: show_error_dialog(self.page, "生成失败", str(err)),
        )

    # ---------------------------------------------------------- 导出
    def _export(self, e) -> None:
        ok, blockers = ready_for_export(self.draft)
        if not ok:
            show_error_dialog(
                self.page,
                "导出被阻断",
                "请先处理以下问题：\n\n" + "\n".join(f"· {item}" for item in blockers[:10]),
            )
            return

        if not (self.draft.export_word or self.draft.export_excel):
            show_snack(self.page, "请至少选择一种导出格式", color=Palette.WARNING)
            return

        date_text = time.strftime("%Y%m%d")
        out_dir = self.project_root / OUTPUT_SUBDIR

        def work():
            return self.exporter.export_zip(
                self.draft,
                date_text=date_text,
                want_word=self.draft.export_word,
                want_excel=self.draft.export_excel,
            )

        def done(result):
            name, data = result
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / name).write_bytes(data)
            except OSError as exc:
                show_error_dialog(self.page, "落盘失败", str(exc))
                return
            self.page.run_task(self._save_as, name, data, out_dir)

        run_background_task(
            self.page, work, on_done=done,
            on_error=lambda err: show_error_dialog(self.page, "导出失败", str(err)),
        )

    async def _save_as(self, name: str, data: bytes, out_dir: Path) -> None:
        picker = ft.FilePicker()
        try:
            await picker.save_file(
                dialog_title="另存评估题库包",
                file_name=name,
                initial_directory=str(out_dir),
                allowed_extensions=["zip"],
                src_bytes=data,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[Evaluation] 另存取消/失败: {exc}")
        show_snack(self.page, f"已导出：{out_dir / name}")

    # ================================================================ 导航
    def _jump(self, step: int) -> None:
        self._go(step)

    def _go(self, step: int) -> None:
        self.draft.current_step = max(1, min(int(step), len(STEP_TITLES)))
        self.message = ""
        self._save_now()
        self._render()

    def _previous(self, e) -> None:
        self._go(self.draft.current_step - 1)

    def _next(self, e) -> None:
        step = self.draft.current_step
        errors = self.validator.validate_step(self.draft, step)
        if errors:
            self.message = "；".join(errors[:3])
            self._render()
            show_snack(self.page, self.message, color=Palette.WARNING)
            return

        if step == 4:
            # 离开 Step4 前把自推考点算好（FR3.3 / FR3.4）
            self._ensure_inferred_tags()

        self.message = ""
        self._go(step + 1)
