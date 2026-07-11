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
        border=ft.Border.all(1, Palette.BORDER),
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


def pick_json_file(page: ft.Page, on_picked: Callable[[str], None], *, dialog_title: str = "选择JSON题库文件") -> None:
    """弹出 JSON 文件选择器，选中后回调 on_picked(file_path)。

    消除 answering_view._on_use_json_bank / course_certification_view._on_select_json_bank
    两处逐字相同的 pick_file_async 样板。
    """

    async def pick_file_async():
        file_picker = ft.FilePicker()
        files = await file_picker.pick_files(
            allowed_extensions=["json"],
            dialog_title=dialog_title,
        )
        if files and len(files) > 0:
            file_path = files[0].path
            print(f"DEBUG: 选择的文件 = {file_path}")
            on_picked(file_path)
        else:
            print("DEBUG: 用户取消了文件选择")

    page.run_task(pick_file_async)


def rich_dialog(
    *,
    title_icon,
    title_text: str,
    title_color: str,
    content_controls: list,
    actions: list,
    actions_alignment: ft.MainAxisAlignment = ft.MainAxisAlignment.END,
) -> ft.AlertDialog:
    """构建富 AlertDialog（Row[Icon,Text] 标题 + Column 内容 + actions）。

    题库导入/课程选择中各类富对话框的共同骨架。
    """
    return ft.AlertDialog(
        title=ft.Row(
            [
                ft.Icon(title_icon, color=title_color),
                ft.Text(title_text, color=title_color, weight=ft.FontWeight.BOLD),
            ],
            spacing=10,
        ),
        content=ft.Column(content_controls, spacing=5, tight=True),
        actions=actions,
        actions_alignment=actions_alignment,
    )


def _bank_course_listtile(label_title: str, icon, icon_color: str, course_name: str, course_id: str) -> ft.ListTile:
    """构建"课程对比"用 ListTile（题库课程/选中课程两列共用）。"""
    return ft.ListTile(
        leading=ft.Icon(icon, color=icon_color),
        title=ft.Text(label_title),
        subtitle=ft.Column(
            [
                ft.Text(f"课程名: {course_name}"),
                ft.Text(f"ID: {course_id}", size=12, color=ft.Colors.GREY_600),
            ],
            spacing=2,
        ),
    )


def build_select_mismatch_warning_dialog(
    *,
    bank_name: str,
    bank_id: str,
    new_name: str,
    new_id: str,
    on_clear: Callable,
    on_cancel: Callable,
) -> ft.AlertDialog:
    """构建"选课时发现题库与新课程不匹配"警告对话框（WARNING 橙色 + 清除/取消按钮）。

    消除 answering_view / course_certification_view 的 _on_course_card_click 中两处重复。
    """
    return rich_dialog(
        title_icon=ft.Icons.WARNING,
        title_text="题库课程不匹配",
        title_color=ft.Colors.ORANGE,
        content_controls=[
            ft.Text("⚠️ 警告：您已导入的题库与新选择的课程不匹配！", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("📋 课程信息：", weight=ft.FontWeight.BOLD),
            _bank_course_listtile("已导入的题库", ft.Icons.DESCRIPTION, ft.Colors.ORANGE, bank_name, bank_id),
            _bank_course_listtile("新选择的课程", ft.Icons.BOOK, ft.Colors.BLUE, new_name, new_id),
            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
            ft.Text("💡 请选择以下操作：", size=14, weight=ft.FontWeight.BOLD),
        ],
        actions=[
            ft.Row(
                [
                    ft.ElevatedButton(
                        "清除题库", icon=ft.Icons.DELETE, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, on_click=on_clear
                    ),
                    ft.ElevatedButton(
                        "取消选择", icon=ft.Icons.CANCEL, bgcolor=ft.Colors.GREY, color=ft.Colors.WHITE, on_click=on_cancel
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
            )
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )


def show_bank_load_result_dialog(page: ft.Page, result, *, success_note: str = "", on_close: Optional[Callable] = None) -> None:
    """根据题库导入结果（bank_service.BankLoadResult）显示对应对话框。

    分支：成功（含 preview + 可选 success_note）/ 课程不匹配（ERROR 红 + 知道了）/
    JSON 格式错误 / 其他读取错误。消除两处 _process_selected_json_file 的对话框样板。

    Args:
        page: Flet 页面。
        result: bank_service.load_question_bank 的返回值。
        success_note: 成功对话框底部可选的蓝色斜体提示（学生端用"💡 详细题库信息已输出到控制台"）。
        on_close: 成功对话框"确定"回调（认证端传 _on_import_dialog_close 刷新按钮）；None 时默认 pop_dialog。
    """
    close_handler = on_close if on_close is not None else (lambda _: page.pop_dialog())

    if result.success:
        controls = [
            ft.Text("✅ 成功加载题库文件"),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Text(f"📄 文件名: {result.file_name}"),
            ft.Text(f"📁 路径: {result.file_path}"),
            ft.Text(f"🏷️ 类型: {result.bank_type if result.bank_type else '未知'}"),
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Text(result.preview, size=12, color=ft.Colors.GREY_700),
        ]
        if success_note:
            controls.append(ft.Divider(height=10, color=ft.Colors.TRANSPARENT))
            controls.append(
                ft.Text(success_note, size=11, color=ft.Colors.BLUE_700, style=Fonts.text(italic=True))
            )
        page.show_dialog(
            rich_dialog(
                title_icon=ft.Icons.CHECK_CIRCLE,
                title_text="题库加载成功",
                title_color=ft.Colors.GREEN,
                content_controls=controls,
                actions=[ft.TextButton("确定", on_click=close_handler)],
            )
        )
        return

    if result.mismatch is not None:
        m = result.mismatch
        page.show_dialog(
            rich_dialog(
                title_icon=ft.Icons.ERROR,
                title_text="题库课程不匹配",
                title_color=ft.Colors.RED,
                content_controls=[
                    ft.Text("❌ 错误：您导入的题库与当前选择的课程不匹配！", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Text("📋 课程信息：", weight=ft.FontWeight.BOLD),
                    _bank_course_listtile("当前选择的课程", ft.Icons.BOOK, ft.Colors.BLUE, m["selected_name"], m["selected_id"]),
                    _bank_course_listtile("题库中的课程", ft.Icons.DESCRIPTION, ft.Colors.ORANGE, m["bank_name"], m["bank_id"]),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        "💡 提示：请选择与题库匹配的课程，或导入正确的题库文件",
                        size=14,
                        color=ft.Colors.GREY_700,
                        italic=True,
                    ),
                ],
                actions=[
                    ft.ElevatedButton(
                        "知道了",
                        icon=ft.Icons.CHECK,
                        bgcolor=ft.Colors.RED,
                        color=ft.Colors.WHITE,
                        on_click=lambda _: page.pop_dialog(),
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        return

    # 读取错误（含 JSON 格式错误——importer.import_from_file 已将 JSONDecodeError
    # 转为返回 False，故此处统一显示"读取文件失败"，与原 _process 实际行为一致）
    page.show_dialog(
        rich_dialog(
            title_icon=ft.Icons.ERROR,
            title_text="读取文件失败",
            title_color=ft.Colors.RED,
            content_controls=[
                ft.Text("❌ 无法读取文件内容"),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Text(f"📄 文件: {result.file_name}"),
                ft.Text(f"💡 错误信息: {result.error}", size=12, color=ft.Colors.RED_700),
            ],
            actions=[ft.TextButton("确定", on_click=lambda _: page.pop_dialog())],
        )
    )
