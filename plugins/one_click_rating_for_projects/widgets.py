"""UI 构建组件（纯 widgets，从 LazyAIGradingView._build_* 下沉）。

这些函数只负责"画界面"，不持有状态；调用方（view）传入数据 + 回调。
依赖 src.ui.theme（Palette/Fonts/Radius）、src.ui.components（按钮/chip/card）、scoring 常量。

副作用转译约定：
- 读 view 状态 → 入参（如 is_selected 由调用方预计算）
- 写 view 控件引用 → 返回值（如 build_batch_toolbar 返回 count_text/grade_btn 引用）
- 回调 → callable 参数（on_click/on_check 等）
"""

import flet as ft
from dataclasses import dataclass
from typing import Callable

from src.ui.components import primary_button, secondary_button, status_chip, surface_card
from src.ui.theme import Fonts, Palette, Radius

from .models import ClassProject, ProjectResult
from .scoring import MINIMUM_NOT_MET_SCORE, NO_ATTACHMENT_DEDUCTION


def build_grading_rules_content(cfg) -> list:
    """构造确认弹窗里的「评分规则 + 免责声明」内容块（单项目/批量共用）。

    Args:
        cfg: STRICTNESS_CONFIG[strictness] dict，需含 cfg["tier3"] = (low, high)。
    """
    range_min = MINIMUM_NOT_MET_SCORE  # 内容不达标时的保底分（76）
    low, high = cfg["tier3"]
    return [
        ft.Text("评分规则：", size=12, weight=ft.FontWeight.W_600),
        ft.Text(f"• 分数范围：{range_min} ~ {high}", size=12),
        ft.Text(f"• 截图>9 或 字数>500 → {low}~{high}", size=12),
        ft.Text("• 截图≥6 或 字数≥400 → 中间档", size=12),
        ft.Text(f"• 内容不达标(截图<3且字数<150) → 保底{range_min}分（标注混子）", size=12),
        ft.Text("• 日志不足3个 → 酌情扣3~5分", size=12),
        ft.Text(f"• 无附件 → 酌情扣{NO_ATTACHMENT_DEDUCTION}分", size=12),
        ft.Text("• ≥80分评语≥20字，≥95分评语≥100字", size=12),
        ft.Divider(height=4, color=ft.Colors.TRANSPARENT),
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.INFO_OUTLINE,
                                size=14,
                                color=Palette.WARNING,
                            ),
                            ft.Text(
                                "免责声明",
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=Palette.WARNING,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        "本功能由程序既定规则自动评分，分数与评语仅供参考，可能存在偏差。"
                        "最终成绩以教师人工复核为准，建议提交后抽检。"
                        "使用本功能即表示知悉并接受上述风险。",
                        size=10,
                        color=Palette.TEXT_MUTED,
                    ),
                ],
                spacing=2,
            ),
            padding=8,
            bgcolor=Palette.WARNING_SOFT,
            border_radius=Radius.SMALL,
        ),
    ]


def build_template_item(pool, index, text, min_chars, *, on_edit, on_delete) -> ft.Container:
    """单条评语模板卡片：全文预览 + 字数状态徽标 + 编辑/删除。

    Args:
        on_edit/on_delete: 回调，签名 (pool, index)。
    """
    n = len(text.strip())
    ok = n >= min_chars
    badge_color = Palette.ACCENT if ok else Palette.WARNING
    badge_bg = Palette.ACCENT_SOFT if ok else Palette.WARNING_SOFT

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    text,
                    size=12,
                    color=Palette.TEXT,
                    selectable=True,
                ),
                ft.Row(
                    [
                        status_chip(
                            f"{n} 字",
                            color=badge_color,
                            bgcolor=badge_bg,
                        ),
                        ft.Text(
                            "✓ 达标" if ok else f"建议 ≥ {min_chars} 字",
                            size=10,
                            color=badge_color,
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            ft.Icons.EDIT_OUTLINED,
                            icon_size=16,
                            icon_color=Palette.TEXT_MUTED,
                            tooltip="编辑",
                            on_click=lambda ev, p=pool, i=index: on_edit(p, i),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_size=16,
                            icon_color=Palette.DANGER,
                            tooltip="删除",
                            on_click=lambda ev, p=pool, i=index: on_delete(p, i),
                        ),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=6,
        ),
        padding=10,
        bgcolor=Palette.SURFACE,
        border=ft.Border.all(1, Palette.BORDER),
        border_radius=Radius.SMALL,
    )


def build_template_section(
    pool, title, usage, icon, items, min_chars, accent, accent_soft,
    *, on_add, on_edit, on_delete,
) -> ft.Container:
    """设置弹窗里的一个评语分区：彩色标题栏 + 可滚动模板卡片列表。

    Args:
        on_add: 回调，签名 (pool)，绑定到「添加」按钮。
        on_edit/on_delete: 传给 build_template_item，签名 (pool, index)。
    """
    if items:
        cards = [
            build_template_item(pool, i, t, min_chars, on_edit=on_edit, on_delete=on_delete)
            for i, t in enumerate(items)
        ]
    else:
        cards = [
            ft.Container(
                content=ft.Text(
                    "暂无模板，点右上角「添加」",
                    size=12,
                    color=Palette.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                padding=20,
                alignment=ft.Alignment(0, 0),
            )
        ]
    list_view = ft.ListView(
        controls=cards,
        spacing=8,
        height=150,
        scroll=ft.ScrollMode.AUTO,
    )
    header = ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, size=16, color=accent),
                ft.Text(
                    title,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=Palette.TEXT,
                ),
                ft.Text(
                    f"{usage} · 共 {len(items)} 条 · 建议 ≥ {min_chars} 字",
                    size=11,
                    color=Palette.TEXT_MUTED,
                ),
                ft.Container(expand=True),
                secondary_button(
                    "添加",
                    ft.Icons.ADD,
                    lambda ev, p=pool: on_add(p),
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=accent_soft,
        border_radius=Radius.SMALL,
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
    )
    return ft.Container(
        content=ft.Column([header, list_view], spacing=8),
        border=ft.Border.all(1, Palette.BORDER),
        border_radius=Radius.MEDIUM,
        padding=8,
    )


def build_project_card(p: ClassProject, *, is_selected: bool, on_click, on_check) -> ft.Row:
    """构建单条项目卡片（GestureDetector 卡片 + 兄弟勾选框）。

    Args:
        is_selected: 是否已勾选（调用方预计算 p.source_id in selected_projects）。
        on_click/on_check: 回调，签名 (e, project)。
    """
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

    subtitle_children = [
        ft.Text(
            subtitle,
            size=12,
            color=Palette.TEXT_MUTED,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        ),
    ]
    if p.fb_name:
        subtitle_children.append(
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.PERSON_OUTLINE,
                        size=13,
                        color=Palette.TEXT_SOFT,
                    ),
                    ft.Text(
                        f"指导老师：{p.fb_name}",
                        size=12,
                        color=Palette.TEXT_SOFT,
                        max_lines=1,
                    ),
                ],
                spacing=2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

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
                                    ft.Row(
                                        subtitle_children,
                                        spacing=8,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
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
            border=ft.Border.all(1, Palette.BORDER),
            border_radius=Radius.MEDIUM,
        ),
        on_tap=lambda e, project=p: on_click(e, project),
        mouse_cursor=ft.MouseCursor.CLICK,
    )

    checkbox = ft.Checkbox(
        value=is_selected,
        on_change=lambda e, project=p: on_check(e, project),
        scale=0.9,
    )
    return ft.Row(
        [
            ft.Container(
                content=checkbox,
                width=30,
                alignment=ft.Alignment(0, 0),
            ),
            ft.Container(content=card, expand=True),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def build_batch_toolbar(*, on_batch_grade, on_select_all, on_clear, on_settings) -> tuple:
    """项目列表屏的批量评分操作行。

    Args:
        on_batch_grade/on_select_all/on_clear/on_settings: 回调，签名 (e)。

    Returns:
        (rows, count_text, grade_btn)：rows 用于展开注入 Column；
        count_text/grade_btn 由调用方挂到 self 供局部刷新。
    """
    count_text = ft.Text(
        "已选 0 个项目", size=13, color=Palette.TEXT_MUTED
    )
    grade_btn = primary_button(
        "批量评分", ft.Icons.GRADE, on_batch_grade
    )
    grade_btn.disabled = True
    rows = [
        ft.Row(
            [
                ft.Icon(ft.Icons.CHECKLIST, size=16, color=Palette.TEXT_MUTED),
                count_text,
                secondary_button(
                    "全选当前页",
                    ft.Icons.SELECT_ALL,
                    on_select_all,
                ),
                secondary_button(
                    "清空选择",
                    ft.Icons.DESELECT,
                    on_clear,
                ),
                ft.Container(expand=True),
                grade_btn,
                ft.IconButton(
                    ft.Icons.SETTINGS_OUTLINED,
                    icon_size=18,
                    icon_color=Palette.TEXT_MUTED,
                    tooltip="评语与严格度设置",
                    on_click=on_settings,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    ]
    return rows, count_text, grade_btn


def build_student_card(r: ProjectResult, *, is_selected: bool, on_tap) -> tuple:
    """构建单条学生成果卡片（带左侧勾选图标，整体可点击切换选择）。

    Args:
        is_selected: 是否已选中（调用方预计算 r.id in selected_result_ids）。
        on_tap: 回调，签名 (e, rid)。

    Returns:
        (card, refs)：card 是 GestureDetector；refs = {"icon":..., "container":...}，
        由调用方挂到 self._student_card_refs[r.id] 供局部刷新。
    """
    selected = is_selected

    check_icon = ft.Icon(
        ft.Icons.CHECK_BOX if selected else ft.Icons.CHECK_BOX_OUTLINE_BLANK,
        size=22,
        color=Palette.PRIMARY if selected else Palette.TEXT_SOFT,
    )

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

    is_slacker = r.is_graded and r.pro_score == MINIMUM_NOT_MET_SCORE
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
            )
        )

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

    if r.is_graded:
        score_color, score_bg = Palette.ACCENT, Palette.ACCENT_SOFT
        score_label = f"评分 {r.pro_score}"
        status_label = "已评分"
        status_color, status_bg = Palette.ACCENT, Palette.ACCENT_SOFT
    else:
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

    submit_text = ft.Text(
        r.submit_date or "未提交",
        size=11,
        color=Palette.TEXT_SOFT,
    )

    card_bg = Palette.PRIMARY_SOFT if selected else Palette.SURFACE
    card_border = Palette.PRIMARY if selected else Palette.BORDER

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
        border=ft.Border.all(1, card_border),
        border_radius=Radius.MEDIUM,
    )

    card = ft.GestureDetector(
        content=container,
        on_tap=lambda ev, rid=r.id: on_tap(ev, rid),
        mouse_cursor=ft.MouseCursor.CLICK,
    )
    refs = {"icon": check_icon, "container": container}
    return card, refs


@dataclass
class ResultPanelProps:
    """build_result_action_panel 的参数包（数据 + 回调），避免函数签名爆炸。"""

    result_list: list
    selected: int
    on_grade_all: Callable
    on_grade_selected: Callable
    on_select_all: Callable
    on_deselect_all: Callable
    on_select_ungraded: Callable
    on_select_completed: Callable
    on_export: Callable
    on_refresh: Callable
    on_settings: Callable


def _stat_row(label: str, value: str) -> ft.Row:
    """统计面板中的一行 key-value。"""
    return ft.Row(
        [
            ft.Text(label, size=13, color=Palette.TEXT_MUTED),
            ft.Container(expand=True),
            ft.Text(value, size=14, weight=ft.FontWeight.W_600, color=Palette.TEXT),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _quick_btn(label: str, icon, on_click) -> ft.OutlinedButton:
    """快速选择区域的紧凑小按钮。"""
    return ft.OutlinedButton(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=Palette.TEXT,
            side=ft.BorderSide(1, Palette.BORDER_STRONG),
            shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            text_style=Fonts.text(size=12, weight=ft.FontWeight.W_500),
        ),
    )


def build_result_action_panel(props: "ResultPanelProps") -> tuple:
    """构建右侧统计摘要 + 快速选择 + 功能操作按钮面板。

    Args:
        props: ResultPanelProps（result_list + selected + 9 个回调）。

    Returns:
        (panel, stat_selected_text, grade_selected_btn)：panel 是 ft.Column；
        stat_selected_text/grade_selected_btn 由调用方挂 self 供局部刷新。
    """
    total = len(props.result_list)
    graded = sum(1 for r in props.result_list if r.is_graded)
    ungraded = total - graded
    completed = sum(1 for r in props.result_list if r.project_progress >= 100)
    selected = props.selected

    stat_selected_text = ft.Text(
        str(selected), size=14, weight=ft.FontWeight.W_600, color=Palette.TEXT
    )

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
                        stat_selected_text,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
        ),
        padding=18,
    )

    grade_all_btn = primary_button(
        "一键评分（全部）",
        ft.Icons.AUTO_AWESOME,
        props.on_grade_all,
        width=280,
    )
    grade_selected_btn = ft.FilledButton(
        "评分已选学生",
        icon=ft.Icons.CHECKLIST,
        width=280,
        disabled=selected == 0,
        bgcolor=Palette.PRIMARY,
        color=Palette.SURFACE,
        on_click=props.on_grade_selected,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
            text_style=Fonts.text(size=14, weight=ft.FontWeight.W_600),
        ),
    )

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
                    _quick_btn("全选", ft.Icons.CHECKLIST_RTL, props.on_select_all),
                    _quick_btn("取消选择", ft.Icons.CLEAR_ALL, props.on_deselect_all),
                ],
                spacing=8,
                wrap=True,
                run_spacing=8,
            ),
            ft.Row(
                [
                    _quick_btn(f"未评分（{ungraded}）", ft.Icons.HOURGLASS_EMPTY, props.on_select_ungraded),
                    _quick_btn(f"进度100%（{completed}）", ft.Icons.TASK_ALT, props.on_select_completed),
                ],
                spacing=8,
                wrap=True,
                run_spacing=8,
            ),
        ],
        spacing=10,
    )

    export_btn = secondary_button("导出成绩", ft.Icons.DOWNLOAD, props.on_export, width=280)
    refresh_btn = secondary_button("刷新列表", ft.Icons.REFRESH, props.on_refresh, width=280)
    comment_settings_btn = secondary_button("设置", ft.Icons.SETTINGS, props.on_settings, width=280)

    panel = ft.Column(
        [
            stats_card,
            ft.Divider(height=1, color=Palette.BORDER),
            select_section,
            ft.Divider(height=1, color=Palette.BORDER),
            grade_all_btn,
            grade_selected_btn,
            ft.Divider(height=1, color=Palette.BORDER),
            export_btn,
            refresh_btn,
            comment_settings_btn,
        ],
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )
    return panel, stat_selected_text, grade_selected_btn
