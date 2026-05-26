"""Shared visual tokens and Flet theme configuration for the desktop app."""

import flet as ft
import platform


class Fonts:
    """Font family tokens for clear text rendering across platforms."""

    # Windows: 使用微软雅黑和Segoe UI，更清晰
    WINDOWS = "Microsoft YaHei UI, Segoe UI, sans-serif"
    # macOS: 使用系统字体
    MACOS = "-apple-system, BlinkMacSystemFont, sans-serif"
    # Linux: 使用常见开源字体
    LINUX = "Ubuntu, Noto Sans, sans-serif"

    @staticmethod
    def get_system_font() -> str:
        """获取适合当前系统的清晰字体"""
        system = platform.system()
        if system == "Windows":
            return Fonts.WINDOWS
        elif system == "Darwin":
            return Fonts.MACOS
        else:
            return Fonts.LINUX


class Palette:
    """Color tokens used by the modern application shell and core views."""

    PRIMARY = "#335CFF"
    PRIMARY_DARK = "#1D3BC1"
    PRIMARY_SOFT = "#EEF3FF"
    ACCENT = "#12B981"
    ACCENT_SOFT = "#E8FBF4"
    WARNING = "#F59E0B"
    WARNING_SOFT = "#FFF7E6"
    DANGER = "#DC4C64"
    NAV = "#111827"
    NAV_SELECTED = "#263452"
    NAV_TEXT = "#94A3B8"
    CANVAS = "#F5F7FB"
    SURFACE = "#FFFFFF"
    SURFACE_ALT = "#F8FAFD"
    BORDER = "#E5EAF2"
    BORDER_STRONG = "#CCD5E3"
    TEXT = "#162033"
    TEXT_MUTED = "#66758C"
    TEXT_SOFT = "#94A3B8"


class Radius:
    SMALL = 10
    MEDIUM = 14
    CARD = 18
    LARGE = 24


def build_theme() -> ft.Theme:
    """Return the Material 3 theme shared by all application pages."""
    system_font = Fonts.get_system_font()

    return ft.Theme(
        use_material3=True,
        color_scheme_seed=Palette.PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=Palette.PRIMARY,
            on_primary=Palette.SURFACE,
            primary_container=Palette.PRIMARY_SOFT,
            on_primary_container=Palette.PRIMARY_DARK,
            secondary=Palette.ACCENT,
            secondary_container=Palette.ACCENT_SOFT,
            surface=Palette.SURFACE,
            on_surface=Palette.TEXT,
            on_surface_variant=Palette.TEXT_MUTED,
            outline=Palette.BORDER_STRONG,
            outline_variant=Palette.BORDER,
            error=Palette.DANGER,
        ),
        scaffold_bgcolor=Palette.CANVAS,
        card_bgcolor=Palette.SURFACE,
        divider_color=Palette.BORDER,
        font_family=system_font,
        text_theme=ft.TextTheme(
            title_large=ft.TextStyle(
                size=24,
                weight=ft.FontWeight.BOLD,
                color=Palette.TEXT,
                font_family=system_font,
            ),
            title_medium=ft.TextStyle(
                size=16,
                weight=ft.FontWeight.W_600,
                color=Palette.TEXT,
                font_family=system_font,
            ),
            body_medium=ft.TextStyle(
                size=14,
                color=Palette.TEXT,
                font_family=system_font,
            ),
            body_small=ft.TextStyle(
                size=12,
                color=Palette.TEXT_MUTED,
                font_family=system_font,
            ),
        ),
        card_theme=ft.CardTheme(
            color=Palette.SURFACE,
            elevation=1,
            shadow_color="#14233D12",
            shape=ft.RoundedRectangleBorder(radius=Radius.CARD),
            margin=0,
        ),
        navigation_rail_theme=ft.NavigationRailTheme(
            bgcolor=Palette.NAV,
            indicator_color=Palette.NAV_SELECTED,
            selected_label_text_style=ft.TextStyle(
                color=Palette.SURFACE,
                weight=ft.FontWeight.W_600,
                font_family=system_font,
            ),
            unselected_label_text_style=ft.TextStyle(
                color=Palette.NAV_TEXT,
                font_family=system_font,
            ),
            min_width=72,
            min_extended_width=232,
            use_indicator=True,
        ),
    )


def configure_page(page: ft.Page) -> None:
    """Apply app-wide visual defaults to the current Flet page."""
    page.theme = build_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = Palette.CANVAS
    page.font_family = Fonts.get_system_font()
    # 启用更清晰的字体渲染
    page.theme.text_style = ft.TextStyle(font_family=Fonts.get_system_font())
