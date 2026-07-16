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


class _ProgressTheme:
    """进度对话框主题配色。"""

    __slots__ = ("primary", "primary_dark", "bar_bgcolor")

    def __init__(self, primary, primary_dark, bar_bgcolor):
        self.primary = primary
        self.primary_dark = primary_dark
        self.bar_bgcolor = bar_bgcolor


_PROGRESS_THEMES = {
    "blue": _ProgressTheme(ft.Colors.BLUE, ft.Colors.BLUE_800, ft.Colors.BLUE_GREY_100),
    "orange": _ProgressTheme(ft.Colors.ORANGE, ft.Colors.ORANGE_700, ft.Colors.ORANGE_100),
}


class AnswerProgressDialog:
    """答题进度对话框（参数化主题、是否含日志区、是否大百分比）。

    统一 AnsweringView / CourseCertificationView 的 _create_answer_log_dialog，
    内聚进度条/百分比/计数/日志区的构建与更新。进度更新通过 page.run_task 调度，
    确保在后台线程驱动时 UI 仍能实时刷新。
    """

    def __init__(
        self,
        page: ft.Page,
        *,
        title: str,
        theme: str = "blue",
        title_icon=None,
        show_log_panel: bool = False,
        show_big_percent: bool = False,
        width: int = 400,
        log_panel_height: int = 300,
        on_stop: Optional[Callable] = None,
    ):
        self._page = page
        self._theme = _PROGRESS_THEMES.get(theme, _PROGRESS_THEMES["blue"])
        self._show_log_panel = show_log_panel
        self._on_stop = on_stop

        # 百分比文本（大字/小字）
        percent_size = 32 if show_big_percent else 16
        self._percent_text = ft.Text(
            "0%", size=percent_size, weight=ft.FontWeight.BOLD, color=self._theme.primary
        )
        # 大字时左对齐（用 Container 包裹），小字时跟随 Column 居中
        percent_control = (
            ft.Container(content=self._percent_text, alignment=ft.Alignment(0, 0))
            if show_big_percent
            else self._percent_text
        )

        # 进度条
        self._progress_bar = ft.ProgressBar(
            width=width - 50,
            value=0.0,
            color=self._theme.primary,
            bgcolor=self._theme.bar_bgcolor,
            bar_height=10,
        )

        # 计数/状态文本
        self._count_text = ft.Text("准备开始...", size=14, color=ft.Colors.GREY_700)

        # 日志区（可选）
        self._log_text = None
        controls = [
            percent_control,
            ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
            self._progress_bar,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            self._count_text,
        ]
        if show_log_panel:
            self._log_text = ft.Text(
                "", size=12, color=ft.Colors.BLACK, selectable=True, max_lines=None
            )
            log_panel = ft.Container(
                content=ft.Column([self._log_text], scroll=ft.ScrollMode.ALWAYS, auto_scroll=False),
                width=width - 50,
                height=log_panel_height,
                bgcolor=ft.Colors.GREY_100,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=8,
                padding=10,
            )
            controls += [
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text("答题日志：", size=12, weight=ft.FontWeight.BOLD),
                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                log_panel,
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Text(
                    "⏳ 正在答题中...点击下方按钮可随时停止",
                    size=12,
                    color=self._theme.primary_dark,
                    weight=ft.FontWeight.BOLD,
                ),
            ]

        icon = title_icon if title_icon is not None else ft.Icons.AUTO_GRAPH
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(icon, color=self._theme.primary, size=28),
                    ft.Text(
                        title,
                        size=18 if show_big_percent else 16,
                        weight=ft.FontWeight.BOLD,
                        color=self._theme.primary_dark,
                    ),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    controls,
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                width=width,
                padding=ft.Padding.symmetric(horizontal=20, vertical=25),
            ),
            actions=[
                ft.ElevatedButton(
                    "🛑 停止答题",
                    icon=ft.Icons.STOP,
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding.symmetric(horizontal=30, vertical=14),
                    ),
                    on_click=on_stop,
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

    @property
    def dialog(self) -> ft.AlertDialog:
        return self._dialog

    def update_progress(self, current=None, total=None, message: str = "") -> None:
        """更新进度。有 current/total 时显示具体百分比与计数；否则显示不确定动画。"""
        if not self._page:
            return

        async def update_ui():
            try:
                if current is not None and total is not None and total > 0:
                    progress_value = min(current / total, 1.0)
                    self._progress_bar.value = progress_value
                    self._percent_text.value = f"{int(progress_value * 100)}%"
                    self._count_text.value = f"{current}/{total}"
                else:
                    self._progress_bar.value = None
                    self._percent_text.value = "⏳"
                    self._count_text.value = message or "正在处理..."
                self._page.update()
            except Exception as e:
                print(f"❌ 进度UI更新异常: {e}")

        self._page.run_task(update_ui)

    def append_log(self, message: str) -> None:
        """追加日志到日志区（仅 show_log_panel=True 时有效）。"""
        if not self._log_text or not self._page:
            return

        current_text = self._log_text.value if self._log_text.value else ""
        new_text = current_text + message + "\n"
        if len(new_text) > 2000:
            new_text = "...(日志已截断)\n" + new_text[-2000:]

        async def update_log():
            try:
                self._log_text.value = new_text
                self._page.update()
            except Exception as e:
                print(f"⚠️ 日志UI更新失败: {e}")

        self._page.run_task(update_log)


def run_background_task(
    page: ft.Page,
    work_fn: Callable,
    *,
    on_done: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
    progress_dialog=None,
) -> None:
    """在 Flet 后台线程跑 work_fn，完成/异常后在同线程调 on_done/on_error。

    用 page.run_thread（Flet 保证该线程可直接 page.update/show_dialog）。
    替代 extraction_view 的 Event 轮询模式（裸 Thread + asyncio.sleep 轮询）。
    work_fn 通过返回值（而非 self 属性）把结果传给 on_done；抛异常走 on_error。
    progress_dialog 完成后自动关闭（open=False + page.update）。
    """

    def runner():
        try:
            result = work_fn()
            if progress_dialog is not None:
                progress_dialog.open = False
                page.update()
            if on_done is not None:
                on_done(result)
        except Exception as e:
            if progress_dialog is not None:
                progress_dialog.open = False
                page.update()
            if on_error is not None:
                on_error(e)

    page.run_thread(runner)
