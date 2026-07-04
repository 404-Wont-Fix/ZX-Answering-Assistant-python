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
            text_style=ft.TextStyle(
                size=14,
                weight=ft.FontWeight.W_600,
                font_family=Fonts.get_system_font(),
            ),
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
