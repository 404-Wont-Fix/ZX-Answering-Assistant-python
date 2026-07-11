"""
ZX Answering Assistant - 课程认证视图模块

This module contains the UI components for the course certification page.
"""

import flet as ft
import json
from pathlib import Path
from src.extraction.importer import QuestionBankImporter
from src.extraction.bank_service import apply_bank_result, load_question_bank
from src.core.config import get_settings_manager
from src.ui.components import (
    build_select_mismatch_warning_dialog,
    create_animated_switcher,
    handle_stop_answering,
    hero_panel,
    page_heading,
    pick_json_file,
    primary_button,
    secondary_button,
    section_label,
    show_bank_load_result_dialog,
    status_chip,
    surface_card,
    workflow_step,
)
from src.ui.theme import Fonts, Palette, Radius


class CourseCertificationView:
    """课程认证页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化课程认证视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app
        self.current_content = None  # 保存当前内容容器的引用
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框

        # 课程数据
        self.access_token = None  # 存储登录后的access_token
        self.course_list = []  # 课程列表
        self.selected_course = None  # 当前选中的课程
        self.question_bank_data = None  # 存储加载的题库数据

        # 答题相关状态
        self.is_answering = False
        self.answer_dialog = None
        self.log_text = None
        self.auto_answer_instance = None
        self.should_stop_answering = False

    def get_content(self) -> ft.Column:
        """
        获取课程认证页面的内容

        Returns:
            ft.Column: 页面内容组件
        """
        # 创建主界面内容
        main_content = self._get_main_content()

        # 使用 AnimatedSwitcher 实现动画切换
        self.current_content, return_content = create_animated_switcher(main_content)

        return return_content

    def _get_main_content(self) -> ft.Column:
        """
        获取主界面内容

        Returns:
            ft.Column: 主界面组件
        """
        start_button = ft.FilledButton(
            "开始认证",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=Palette.SURFACE,
            color=Palette.PRIMARY,
            on_click=lambda e: self._on_start_answer_click(e),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                padding=ft.Padding.symmetric(horizontal=24, vertical=16),
                text_style=Fonts.text(weight=ft.FontWeight.W_600),
            ),
        )
        return ft.Column(
            [
                page_heading(
                    "课程认证",
                    "载入认证题库并使用 API 完成课程认证流程",
                    ft.Icons.VERIFIED_OUTLINED,
                ),
                hero_panel(
                    "快速完成课程认证任务",
                    "验证教师身份、导入课程题库，并通过 API 模式完成认证答题。",
                    action=start_button,
                    chips=[
                        status_chip(
                            "教师端认证",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "JSON 题库",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                        status_chip(
                            "API 模式",
                            color=Palette.SURFACE,
                            bgcolor=ft.Colors.with_opacity(0.12, Palette.SURFACE),
                        ),
                    ],
                    icon=ft.Icons.VERIFIED_USER_OUTLINED,
                ),
                section_label("认证流程", "三步启动安全、快速的课程认证任务"),
                ft.ResponsiveRow(
                    [
                        ft.Container(
                            content=workflow_step(
                                "01",
                                "教师端登录",
                                "完成账号身份验证",
                                ft.Icons.PERSON_OUTLINE,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "02",
                                "导入题库",
                                "加载认证 JSON 题库",
                                ft.Icons.ATTACH_FILE,
                            ),
                            col={"xs": 12, "md": 4},
                        ),
                        ft.Container(
                            content=workflow_step(
                                "03",
                                "API 答题",
                                "自动提交认证答案",
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

    def _get_login_content(self) -> ft.Column:
        """
        获取登录界面内容

        Returns:
            ft.Column: 登录界面组件
        """
        # 加载已保存的教师凭据
        settings_manager = get_settings_manager()
        saved_username, saved_password = settings_manager.get_teacher_credentials()

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
            label="教师密码",
            hint_text="请输入教师端密码",
            value=saved_password or "",
            width=400,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )

        return ft.Column(
            [
                page_heading(
                    "教师端登录",
                    "认证教师账号后进入课程认证任务",
                    ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
                ),
                surface_card(
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.SCHOOL, size=32, color=Palette.PRIMARY),
                                width=64,
                                height=64,
                                alignment=ft.Alignment(0, 0),
                                bgcolor=Palette.PRIMARY_SOFT,
                                border_radius=Radius.CARD,
                            ),
                            ft.Text("登录教师端", size=20, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                            ft.Text("登录后即可导入认证题库", size=12, color=Palette.TEXT_MUTED),
                            self.username_field,
                            self.password_field,
                            ft.Row(
                                [
                                    secondary_button(
                                        "返回",
                                        ft.Icons.ARROW_BACK,
                                        lambda e: self._on_back_from_login(e),
                                    ),
                                    primary_button(
                                        "登录并继续",
                                        ft.Icons.LOGIN,
                                        lambda e: self._on_login_click(e),
                                    ),
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

    def _get_course_list_content(self) -> ft.Column:
        """
        获取课程列表界面内容（左右分栏布局）

        Returns:
            ft.Column: 包含页面标题和左右分栏的界面组件
        """
        left_panel = surface_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("选择课程", size=18, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                            ft.Container(expand=True),
                            status_chip(f"{len(self.course_list)} 门课程"),
                        ],
                    ),
                    ft.ListView(
                        controls=self._create_course_cards(),
                        expand=True,
                        spacing=12,
                    ),
                ],
                spacing=18,
                expand=True,
            ),
            padding=20,
        )
        left_panel.expand = 2

        right_panel = ft.Column(
            [
                self._create_course_stats_panel() if self.selected_course else self._create_empty_stats_panel(),
                self._create_action_panel(),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=1,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        return ft.Column(
            [
                page_heading(
                    "课程认证",
                    "选择目标课程、载入题库并启动 API 答题",
                    ft.Icons.VERIFIED_OUTLINED,
                ),
                ft.Row(
                    [
                        left_panel,
                        right_panel,
                    ],
                    height=620,
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
            spacing=22,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _create_course_cards(self) -> list:
        """
        创建课程卡片列表

        Returns:
            list: 课程卡片列表
        """
        course_cards = []
        for idx, course in enumerate(self.course_list):
            course_name = course.get('lessonName', '未知课程')
            ecourse_id = course.get('eCourseID', '')
            selected = self.selected_course == course

            card = ft.GestureDetector(
                content=ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.BOOK_OUTLINED, color=Palette.PRIMARY, size=22),
                                width=45,
                                height=45,
                                alignment=ft.Alignment(0, 0),
                                bgcolor=Palette.SURFACE if selected else Palette.PRIMARY_SOFT,
                                border_radius=Radius.SMALL,
                            ),
                            ft.Column(
                                [
                                    ft.Text(course_name, weight=ft.FontWeight.W_600, size=15, color=Palette.TEXT),
                                    ft.Text(
                                        f"ID: {ecourse_id[:16]}...",
                                        size=12,
                                        color=Palette.TEXT_MUTED,
                                    ),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE if selected else ft.Icons.CHEVRON_RIGHT,
                                size=20,
                                color=Palette.PRIMARY if selected else Palette.TEXT_SOFT,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=14,
                    bgcolor=Palette.PRIMARY_SOFT if selected else Palette.SURFACE,
                    border=ft.Border.all(1, Palette.PRIMARY if selected else Palette.BORDER),
                    border_radius=Radius.MEDIUM,
                ),
                on_tap=lambda e, c=course: self._on_course_card_click(e, c),
                mouse_cursor=ft.MouseCursor.CLICK,
            )
            course_cards.append(card)

        return course_cards

    def _create_empty_stats_panel(self) -> ft.Container:
        """
        创建空的统计信息面板（未选择课程时）

        Returns:
            ft.Container: 空统计面板
        """
        return surface_card(
            ft.Column(
                [
                    ft.Icon(
                        ft.Icons.INFO_OUTLINE,
                        size=38,
                        color=Palette.TEXT_SOFT,
                    ),
                    ft.Text(
                        "请选择一门课程",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=Palette.TEXT,
                    ),
                    ft.Text("选中后将显示课程认证信息", size=12, color=Palette.TEXT_MUTED),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            padding=26,
            bgcolor=Palette.SURFACE_ALT,
        )

    def _create_course_stats_panel(self) -> ft.Container:
        """
        创建课程统计信息面板

        Returns:
            ft.Container: 统计信息面板
        """
        course_name = self.selected_course.get('lessonName', '未知课程')
        ecourse_id = self.selected_course.get('eCourseID', '')

        return surface_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("课程信息", size=17, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                            ft.Container(expand=True),
                            status_chip("已选择", color=Palette.ACCENT, bgcolor=Palette.ACCENT_SOFT),
                        ],
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BOOK_OUTLINED, color=Palette.PRIMARY),
                        title=ft.Text("课程名称", size=12, color=Palette.TEXT_MUTED),
                        subtitle=ft.Text(course_name, size=14, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.VPN_KEY_OUTLINED, color=Palette.ACCENT),
                        title=ft.Text("课程 ID", size=12, color=Palette.TEXT_MUTED),
                        subtitle=ft.Text(ecourse_id, size=12, selectable=True),
                    ),
                ],
                spacing=8,
            ),
            padding=20,
        )

    def _create_action_panel(self) -> ft.Container:
        """
        创建功能按钮面板

        Returns:
            ft.Container: 功能按钮面板
        """
        bank_ready = bool(self.question_bank_data)
        return surface_card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("任务操作", size=17, weight=ft.FontWeight.W_600, color=Palette.TEXT),
                            ft.Container(expand=True),
                            status_chip(
                                "题库已导入" if bank_ready else "等待题库",
                                color=Palette.ACCENT if bank_ready else Palette.TEXT_MUTED,
                                bgcolor=Palette.ACCENT_SOFT if bank_ready else Palette.SURFACE_ALT,
                            ),
                        ],
                    ),
                    secondary_button(
                        "导入题库",
                        ft.Icons.ATTACH_FILE,
                        lambda e: self._on_select_json_bank(e),
                        width=280,
                    ),
                    ft.FilledButton(
                        "开始答题（API模式）",
                        icon=ft.Icons.FLASH_ON,
                        bgcolor=Palette.PRIMARY,
                        color=Palette.SURFACE,
                        width=280,
                        disabled=not bank_ready,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=Radius.SMALL),
                            padding=ft.Padding.symmetric(horizontal=22, vertical=15),
                        ),
                        on_click=lambda e: self._on_start_api_answer(e),
                    ),
                    secondary_button(
                        "返回认证首页",
                        ft.Icons.HOME_OUTLINED,
                        lambda e: self._on_back_to_main(e),
                        width=280,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
            ),
            padding=20,
        )

    def _on_start_answer_click(self, e):
        """处理开始答题按钮点击事件"""
        print("DEBUG: 切换到登录界面")
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_from_login(self, e):
        """处理从登录界面返回的按钮点击事件"""
        print("DEBUG: 从登录界面返回主界面")
        main_content = self._get_main_content()
        self.current_content.content = main_content
        self.page.update()

    def _on_back_to_main(self, e):
        """处理返回主界面按钮点击事件"""
        print("DEBUG: 返回主界面")
        main_content = self._get_main_content()
        self.current_content.content = main_content
        self.page.update()

    def _on_login_click(self, e):
        """处理登录按钮点击事件"""
        username = self.username_field.value
        password = self.password_field.value

        print(f"DEBUG: 登录账号={username}, 密码={'*' * len(password) if password else ''}")

        # 验证输入
        if not username or not password:
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("请输入账号和密码"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 保存教师凭据
        settings_manager = get_settings_manager()
        print("💾 保存教师端凭据...")
        settings_manager.set_teacher_credentials(username, password)

        # 显示登录进度对话框
        progress_dialog = ft.AlertDialog(
            title=ft.Text("正在登录"),
            content=ft.Column(
                [
                    ft.Text(f"正在使用以下账号登录课程认证...\n账号: {username}"),
                    ft.ProgressRing(stroke_width=3),
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            modal=True,
        )
        self.page.show_dialog(progress_dialog)

        # 在后台线程中执行登录
        self.page.run_thread(self._perform_login, username, password, progress_dialog)

    def _perform_login(self, username: str, password: str, progress_dialog: ft.AlertDialog):
        """
        在后台线程中执行登录

        Args:
            username: 用户名
            password: 密码
            progress_dialog: 进度对话框
        """
        try:
            from src.certification.workflow import get_access_token

            # 调用真实的登录逻辑（GUI模式，跳过交互式提示）
            result = get_access_token(keep_browser_open=True, skip_prompt=True)

            if result and result[0]:  # result = (access_token, browser, page, playwright)
                access_token = result[0]
                self.access_token = access_token
                print("✅ 成功获取 access_token")

                # 获取课程列表
                self.course_list = self._fetch_course_list(access_token)

                if self.course_list:
                    print(f"✅ 成功获取 {len(self.course_list)} 门课程")

                    # 关闭进度对话框
                    self.page.pop_dialog()

                    # 切换到课程列表界面
                    courses_content = self._get_course_list_content()
                    self.current_content.content = courses_content
                    self.page.update()
                else:
                    print("❌ 未获取到课程列表")
                    self.page.pop_dialog()
                    error_dialog = ft.AlertDialog(
                        title=ft.Text("获取课程失败"),
                        content=ft.Text("❌ 未能获取到课程列表，请查看控制台日志了解详情。"),
                        actions=[
                            ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                        ],
                    )
                    self.page.show_dialog(error_dialog)
            else:
                print("❌ 登录失败")
                self.page.pop_dialog()
                error_dialog = ft.AlertDialog(
                    title=ft.Text("登录失败"),
                    content=ft.Text("❌ 课程认证登录失败，请检查账号密码是否正确。"),
                    actions=[
                        ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(error_dialog)

        except Exception as e:
            print(f"❌ 登录异常: {str(e)}")
            import traceback
            traceback.print_exc()

            self.page.pop_dialog()
            error_dialog = ft.AlertDialog(
                title=ft.Text("登录异常"),
                content=ft.Text(f"❌ 登录过程中发生异常：\n{str(e)}"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(error_dialog)

    def _fetch_course_list(self, access_token: str) -> list:
        """
        获取课程列表

        Args:
            access_token: 访问令牌

        Returns:
            list: 课程列表
        """
        from src.core.api_client import get_api_client

        api_url = "https://zxsz.cqzuxia.com/teacherCertifiApi/api/ModuleTeacher/GetLessonListByTeacher"

        headers = {
            'authorization': f'Bearer {access_token}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            api_client = get_api_client()
            response = api_client.get(api_url, headers=headers)

            if response is None:
                print("❌ 获取课程列表失败：未收到有效响应")
                return []

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and 'data' in data:
                    return data['data']
        except Exception as e:
            print(f"❌ 获取课程列表异常: {e}")

        return []

    def _on_course_card_click(self, e, course: dict):
        """处理课程卡片点击事件"""
        print(f"DEBUG: 点击课程卡片 - {course.get('lessonName')}")

        # 如果已导入题库，验证题库课程ID是否与新选择的课程匹配
        if self.question_bank_data:
            from src.extraction.importer import QuestionBankImporter

            importer = QuestionBankImporter()
            importer.data = self.question_bank_data
            bank_type = importer.get_bank_type()

            # 只对单课程题库进行验证
            if bank_type == "single":
                parsed = importer.parse_single_course()
                bank_course_id = ""
                bank_course_name = ""
                if parsed and 'course' in parsed:
                    bank_course_id = parsed['course'].get('courseID', '')
                    bank_course_name = parsed['course'].get('courseName', '')

                # 获取新选择的课程ID
                new_course_id = course.get('eCourseID', '')
                new_course_name = course.get('lessonName', '未知课程')

                print(f"DEBUG: 题库课程ID = {bank_course_id}")
                print(f"DEBUG: 新选择课程ID = {new_course_id}")

                # 如果题库课程ID与新选择的课程ID不匹配
                if bank_course_id and new_course_id and bank_course_id != new_course_id:
                    print(f"❌ 题库课程与新选择的课程不匹配")

                    # 暂存旧课程信息
                    old_course = self.selected_course

                    # 显示警告对话框
                    dialog = build_select_mismatch_warning_dialog(
                        bank_name=bank_course_name,
                        bank_id=bank_course_id,
                        new_name=new_course_name,
                        new_id=new_course_id,
                        on_clear=lambda e: self._on_clear_question_bank(e, course),
                        on_cancel=lambda e: self._on_cancel_course_selection(e, old_course),
                    )
                    self.page.show_dialog(dialog)
                    return

        # 没有题库或题库匹配，正常选择课程
        self.selected_course = course

        # 刷新界面
        courses_content = self._get_course_list_content()
        self.current_content.content = courses_content
        self.page.update()

    def _on_select_json_bank(self, e):
        """处理选择题库按钮点击事件"""
        print("DEBUG: 选择题库文件")
        pick_json_file(self.page, self._process_selected_json_file)

    def _process_selected_json_file(self, file_path: str):
        """处理选中的JSON文件：导入题库 + 校验课程匹配 + 显示结果对话框。"""
        result = load_question_bank(
            file_path,
            selected_course=self.selected_course,
            course_id_key="eCourseID",
            course_name_key="lessonName",
        )
        apply_bank_result(self, result)
        show_bank_load_result_dialog(self.page, result, on_close=self._on_import_dialog_close)

    def _on_import_dialog_close(self, e):
        """处理导入成功对话框关闭事件"""
        self.page.pop_dialog()

        # 对话框关闭后再刷新界面，以启用"开始答题"按钮
        print("DEBUG: 刷新界面以更新按钮状态")
        courses_content = self._get_course_list_content()
        self.current_content.content = courses_content
        self.page.update()

    def _on_clear_question_bank(self, e, new_course: dict):
        """清除题库并选择新课程"""
        print("DEBUG: 清除题库并选择新课程")
        self.page.pop_dialog()

        # 清除题库数据
        self.question_bank_data = None

        # 选择新课程
        self.selected_course = new_course

        # 刷新界面
        courses_content = self._get_course_list_content()
        self.current_content.content = courses_content
        self.page.update()

        # 显示提示信息
        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE),
                    ft.Text("题库已清除", color=ft.Colors.BLUE),
                ],
                spacing=10,
            ),
            content=ft.Text("✅ 题库已清除，请重新导入匹配的题库文件"),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def _on_cancel_course_selection(self, e, old_course: dict):
        """取消选择课程，保持之前的课程"""
        print("DEBUG: 取消选择课程")
        self.page.pop_dialog()

        # 恢复旧课程（如果没有旧课程，则清除选择）
        self.selected_course = old_course

        # 刷新界面
        courses_content = self._get_course_list_content()
        self.current_content.content = courses_content
        self.page.update()

    def _on_start_api_answer(self, e):
        """处理开始API答题按钮点击事件"""
        print("DEBUG: 开始API模式答题")

        if not self.question_bank_data:
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("请先加载题库文件"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        if not self.selected_course:
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("请先选择一门课程"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 注：题库课程ID验证已在导入时完成，此处直接开始答题
        ecourse_id = self.selected_course.get('eCourseID', '')
        self._start_certification_answer(ecourse_id, self.question_bank_data)

    def _get_question_bank_course_id(self) -> str:
        """
        从题库数据中获取课程ID

        Returns:
            str: 课程ID，如果无法获取则返回空字符串
        """
        try:
            importer = QuestionBankImporter()
            importer.data = self.question_bank_data
            bank_type = importer.get_bank_type()

            if bank_type == "single":
                parsed = importer.parse_single_course()
                if parsed and 'course' in parsed:
                    return parsed['course'].get('courseID', '')
            elif bank_type == "multiple":
                # 多课程题库，无法确定具体的课程ID
                return ""

        except Exception as e:
            print(f"⚠️ 获取题库课程ID失败: {e}")

        return ""

    def _start_certification_answer(self, course_id: str, question_bank_data: dict):
        """开始课程认证答题"""
        self.is_answering = True
        self.should_stop_answering = False

        self.answer_dialog = self._create_answer_log_dialog("课程认证答题 - API模式")
        self.page.show_dialog(self.answer_dialog)

        self.page.run_thread(lambda: self._run_certification_task(course_id, question_bank_data))

    def _create_answer_log_dialog(self, title: str) -> ft.AlertDialog:
        """创建答题日志对话框"""
        self.log_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLACK,
            selectable=True,
            no_wrap=False,
            max_lines=None,
        )

        # 添加进度条控件
        self.progress_text = ft.Text("准备开始...", size=14, weight=ft.FontWeight.BOLD)
        self.progress_bar = ft.ProgressBar(
            width=600,
            value=0.0,
            color=ft.Colors.ORANGE,
            bgcolor=ft.Colors.ORANGE_100,
            bar_height=12,
            visible=False,  # 初始隐藏，有进度时才显示
        )
        self.progress_percent = ft.Text("", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_700)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.ORANGE),
                    ft.Text(title, color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        # 进度显示区域
                        ft.Column(
                            [
                                self.progress_text,
                                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                self.progress_bar,
                                ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                ft.Row(
                                    [self.progress_percent],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            visible=False,  # 初始隐藏
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                        ft.Text("答题日志：", size=12, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        ft.Container(
                            content=ft.Column(
                                [self.log_text],
                                scroll=ft.ScrollMode.ALWAYS,
                                auto_scroll=False,
                            ),
                            width=600,
                            height=300,
                            bgcolor=ft.Colors.GREY_100,
                            border=ft.Border.all(1, ft.Colors.GREY_300),
                            border_radius=8,
                            padding=10,
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            "⏳ 正在答题中...点击下方按钮可随时停止",
                            size=12,
                            color=ft.Colors.ORANGE_700,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=0,
                ),
                width=650,
                padding=20,
            ),
            actions=[
                ft.ElevatedButton(
                    "🛑 停止答题",
                    icon=ft.Icons.STOP,
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding.symmetric(horizontal=30, vertical=15),
                    ),
                    on_click=self._on_stop_answering,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        # 保存进度区域的引用
        self.progress_column = dialog.content.content.controls[0]

        return dialog

    def _append_log(self, message: str):
        """追加日志（使用 page.run_task 确保实时更新）"""
        if not self.log_text:
            return

        # 准备新的日志文本
        current_text = self.log_text.value if self.log_text.value else ""
        new_text = current_text + message + "\n"
        if len(new_text) > 2000:
            new_text = "...(日志已截断)\n" + new_text[-2000:]

        # 在主线程中更新UI
        async def update_log():
            try:
                self.log_text.value = new_text
                self.page.update()
            except Exception as e:
                print(f"⚠️ UI更新失败: {e}")

        # 使用 run_task 调度UI更新
        self.page.run_task(update_log)

    def _update_progress(self, message: str, current: int = None, total: int = None):
        """
        更新进度（使用 page.run_task 确保实时更新）

        Args:
            message: 进度消息
            current: 当前进度（可选）
            total: 总数（可选）
        """
        print(f"[进度更新] {message} - 当前: {current}, 总数: {total}")

        # 检查控件是否已初始化
        if not all([self.progress_text, self.progress_bar, self.progress_percent]):
            print(f"⚠️ 进度控件未初始化")
            return

        # 在主线程中更新UI
        async def update_ui():
            try:
                # 更新进度文本
                self.progress_text.value = message

                # 更新进度条
                if current is not None and total is not None and total > 0:
                    # 显示进度区域
                    self.progress_column.visible = True
                    self.progress_bar.visible = True

                    # 计算进度
                    progress_value = min(current / total, 1.0)
                    self.progress_bar.value = progress_value
                    self.progress_percent.value = f"{int(progress_value * 100)}%"

                    print(f"[进度UI] 进度条更新为 {progress_value:.2%} ({current}/{total})")
                else:
                    # 隐藏进度条
                    self.progress_bar.visible = False
                    self.progress_percent.value = ""

                # 刷新UI
                self.page.update()
                print(f"[进度UI] UI刷新成功")

            except Exception as e:
                print(f"❌ UI更新异常: {e}")
                import traceback
                traceback.print_exc()

        # 使用 run_task 调度UI更新
        self.page.run_task(update_ui)

    def _on_stop_answering(self, e):
        """处理停止答题"""
        handle_stop_answering(self, log_fn=self._append_log)

    def _run_certification_task(self, course_id: str, question_bank_data: dict):
        """在后台线程中运行答题任务"""
        try:
            from src.certification.api_answer import APICourseAnswer

            self._append_log("🚀 开始课程认证答题\n")
            self._append_log(f"📚 课程ID: {course_id}\n")
            self._append_log("-" * 50 + "\n")

            # 检查access_token
            if not self.access_token:
                self._append_log("❌ 未找到access_token，请先重新登录\n")
                self._append_log("💡 点击返回按钮，重新登录即可\n")
                return

            self._append_log(f"✅ Access Token已获取\n")

            # 创建API答题器，传入日志回调
            answerer = APICourseAnswer(
                access_token=self.access_token,
                log_callback=self._append_log
            )
            self.auto_answer_instance = answerer

            self._append_log("📖 开始自动答题...\n")
            self._append_log("-" * 50 + "\n")

            # 调用自动答题
            result = answerer.auto_answer_course(course_id, question_bank_data)

            # 显示结果
            self._append_log("\n" + "=" * 50 + "\n")
            self._append_log("📊 最终统计\n")
            self._append_log("=" * 50 + "\n")
            self._append_log(f"📍 知识点: {result.get('completed_knowledge', 0)}/{result.get('total_knowledge', 0)}\n")
            self._append_log(f"📝 题目总计: {result.get('total_questions', 0)} 题\n")
            self._append_log(f"✅ 成功完成: {result.get('success_knowledge', 0)} 个知识点\n")
            self._append_log(f"❌ 失败: {result.get('failed_knowledge', 0)} 个知识点\n")
            self._append_log(f"⏭️ 跳过: {result.get('skipped_knowledge', 0)} 个知识点\n")
            self._append_log("=" * 50 + "\n")

            if result.get('success_knowledge', 0) >= result.get('total_knowledge', 0):
                self._append_log("\n🎉 恭喜！所有知识点已完成！\n")

            self._append_log("\n🎉 答题任务完成！\n")

            import time
            time.sleep(2)
            if self.answer_dialog:
                self.page.pop_dialog()
                self.answer_dialog = None

        except KeyboardInterrupt:
            self._append_log("\n⚠️ 用户中断答题\n")
        except Exception as e:
            self._append_log(f"\n❌ 答题过程出错: {str(e)}\n")
            import traceback
            self._append_log(f"📋 详细错误:\n{traceback.format_exc()}\n")
        finally:
            # 清理日志处理器
            if self.auto_answer_instance and hasattr(self.auto_answer_instance, '_cleanup_log_handler'):
                self.auto_answer_instance._cleanup_log_handler()

            self.is_answering = False
            self.should_stop_answering = False
            self.auto_answer_instance = None
