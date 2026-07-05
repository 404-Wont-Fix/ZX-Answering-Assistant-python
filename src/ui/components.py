"""Reusable presentation components for modernized application views."""

from typing import Callable, Optional

import flet as ft

from src.ui.theme import Fonts, Palette, Radius


def surface_card(
    content: ft.Control,
    *,
    padding: int = 22,
    width: Optional[int] = None,
    bgcolor: str = Palette.SURFACE,
) -> ft.Container:
    """Wrap content in the standard bordered surface used throughout the app."""
    return ft.Container(
        content=content,
        padding=padding,
        width=width,
        bgcolor=bgcolor,
        border=ft.border.all(1, Palette.BORDER),
        border_radius=Radius.CARD,
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=0,
            color="#0A102008",
            offset=ft.Offset(0, 5),
        ),
    )


def page_heading(title: str, subtitle: str, icon) -> ft.Row:
    """Create the title block displayed at the beginning of a feature page."""
    return ft.Row(
        [
            ft.Container(
                content=ft.Icon(icon, size=25, color=Palette.PRIMARY),
                width=52,
                height=52,
                alignment=ft.Alignment(0, 0),
                bgcolor=Palette.PRIMARY_SOFT,
                border_radius=Radius.MEDIUM,
            ),
            ft.Column(
                [
                    ft.Text(
                        title,
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=Palette.TEXT,
                    ),
                    ft.Text(subtitle, size=13, color=Palette.TEXT_MUTED),
                ],
                spacing=3,
                tight=True,
            ),
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def status_chip(label: str, *, color: str = Palette.PRIMARY, bgcolor: str = Palette.PRIMARY_SOFT) -> ft.Container:
    """Create a compact informational status pill."""
    return ft.Container(
        content=ft.Text(
            label,
            size=12,
            color=color,
            weight=ft.FontWeight.W_600,
        ),
        padding=ft.Padding.symmetric(horizontal=11, vertical=6),
        bgcolor=bgcolor,
        border_radius=30,
    )


def workflow_step(number: str, title: str, description: str, icon) -> ft.Container:
    """Render one concise workflow step for feature landing pages."""
    return surface_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                number,
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=Palette.PRIMARY,
                            ),
                            width=29,
                            height=29,
                            alignment=ft.Alignment(0, 0),
                            bgcolor=Palette.PRIMARY_SOFT,
                            border_radius=20,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(icon, size=22, color=Palette.TEXT_SOFT),
                    ],
                ),
                ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                ft.Text(description, size=12, color=Palette.TEXT_MUTED),
            ],
            spacing=12,
        ),
        padding=18,
    )


def primary_button(label: str, icon, on_click: Callable, *, width: Optional[int] = None) -> ft.FilledButton:
    """Create the standard high-emphasis application action."""
    return ft.FilledButton(
        label,
        icon=icon,
        width=width,
        bgcolor=Palette.PRIMARY,
        color=Palette.SURFACE,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
            text_style=Fonts.text(size=14, weight=ft.FontWeight.W_600),
        ),
    )


def secondary_button(label: str, icon, on_click: Callable, *, width: Optional[int] = None) -> ft.OutlinedButton:
    """Create a low-emphasis action paired with primary buttons."""
    return ft.OutlinedButton(
        label,
        icon=icon,
        width=width,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=Palette.TEXT,
            side=ft.BorderSide(1, Palette.BORDER_STRONG),
            shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
            padding=ft.Padding.symmetric(horizontal=22, vertical=15),
        ),
    )


def hero_panel(
    title: str,
    description: str,
    *,
    action: ft.Control,
    chips: list[ft.Control],
    icon,
) -> ft.Container:
    """Create an emphasized feature banner with a single primary action."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            title,
                            size=23,
                            weight=ft.FontWeight.BOLD,
                            color=Palette.SURFACE,
                        ),
                        ft.Text(
                            description,
                            size=13,
                            color="#D9E4FF",
                            max_lines=2,
                        ),
                        ft.Row(chips, spacing=8, wrap=True),
                        action,
                    ],
                    spacing=16,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Icon(icon, size=58, color="#DCE6FF"),
                    width=128,
                    height=128,
                    alignment=ft.Alignment(0, 0),
                    bgcolor=ft.Colors.with_opacity(0.1, Palette.SURFACE),
                    border_radius=Radius.LARGE,
                ),
            ],
            spacing=24,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(horizontal=28, vertical=26),
        border_radius=Radius.LARGE,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=[Palette.PRIMARY, Palette.PRIMARY_DARK],
        ),
    )


def section_label(title: str, description: str = "") -> ft.Column:
    """Create a compact section heading above card collections."""
    controls = [
        ft.Text(title, size=17, weight=ft.FontWeight.W_600, color=Palette.TEXT)
    ]
    if description:
        controls.append(ft.Text(description, size=12, color=Palette.TEXT_MUTED))
    return ft.Column(controls, spacing=3, tight=True)


def create_animated_switcher(
    main_content: ft.Control,
) -> tuple:
    """
    创建带 AnimatedSwitcher 的标准视图容器。

    所有视图的 get_content() 方法共享相同的 AnimatedSwitcher 包装模式，
    此函数消除重复。

    Args:
        main_content: 视图的主要内容控件

    Returns:
        (switcher, column) 元组：
        - switcher: AnimatedSwitcher 实例（赋值给 self.current_content）
        - column: 包含 switcher 的 Column 容器（作为 get_content 返回值）
    """
    switcher = ft.AnimatedSwitcher(
        content=main_content,
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=300,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
        expand=True,
    )
    column = ft.Column(
        [switcher],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )
    return switcher, column


def show_info_dialog(
    page: ft.Page,
    title: str,
    message: str,
) -> None:
    """
    显示简单的信息提示弹窗（标题 + 文本内容 + 确定按钮）。

    替代代码中大量重复的 Pattern A AlertDialog 样板。

    Args:
        page: Flet 页面对象
        title: 弹窗标题（如 "提示"、"错误"）
        message: 弹窗内容文本
    """
    dialog = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            ft.TextButton("确定", on_click=lambda _: page.pop_dialog()),
        ],
    )
    page.show_dialog(dialog)


def handle_stop_answering(
    view,
    log_fn=None,
) -> None:
    """
    共享的停止答题逻辑。

    Args:
        view: 视图实例，需具有 should_stop_answering、auto_answer_instance、
              answer_dialog、is_answering、page 属性
        log_fn: 可选的日志回调函数（如 course_certification_view 的 _append_log）
    """
    print("🛑 用户请求停止答题")
    if log_fn:
        log_fn("🛑 正在停止答题...\n")

    view.should_stop_answering = True

    if view.auto_answer_instance and hasattr(view.auto_answer_instance, 'request_stop'):
        view.auto_answer_instance.request_stop()

    if view.answer_dialog:
        view.page.pop_dialog()
        view.answer_dialog = None

    view.is_answering = False

    if log_fn:
        log_fn("✅ 答题已停止\n")
