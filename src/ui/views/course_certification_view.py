"""
ZX Answering Assistant - 课程认证视图模块

This module contains the UI components for the course certification page.
"""

import flet as ft
import json
from pathlib import Path
from src.extraction.importer import QuestionBankImporter
from src.core.config import get_settings_manager


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
        self.current_content = ft.AnimatedSwitcher(
            content=main_content,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
        )

        return ft.Column(
            [self.current_content],
            expand=True,
            spacing=0,
        )

    def _get_main_content(self) -> ft.Column:
        """
        获取主界面内容

        Returns:
            ft.Column: 主界面组件
        """
        return ft.Column(
            [
                ft.Text(
                    "课程认证",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                    animate_opacity=200,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.BLUE),
                                    title=ft.Text("教师端登录", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("登录教师端平台进行身份验证"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.ATTACH_FILE, color=ft.Colors.GREEN),
                                    title=ft.Text("导入题库", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("加载JSON格式的课程认证题库"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.ORANGE),
                                    title=ft.Text("API答题", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用API快速模式自动完成课程认证"),
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        width=600,
                    ),
                    elevation=2,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "开始答题",
                    icon=ft.Icons.PLAY_ARROW,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                        animation_duration=200,
                    ),
                    on_click=lambda e: self._on_start_answer_click(e),
                    animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
                ft.Text(
                    "教师端登录",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                    animate_opacity=200,
                ),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.SCHOOL,
                                    size=64,
                                    color=ft.Colors.BLUE_400,
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                self.username_field,
                                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                self.password_field,
                                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                                ft.Row(
                                    [
                                        ft.OutlinedButton(
                                            "返回",
                                            icon=ft.Icons.ARROW_BACK,
                                            style=ft.ButtonStyle(
                                                animation_duration=200,
                                            ),
                                            on_click=lambda e: self._on_back_from_login(e),
                                            animate_scale=ft.Animation(
                                                200, ft.AnimationCurve.EASE_OUT
                                            ),
                                        ),
                                        ft.ElevatedButton(
                                            "登录",
                                            icon=ft.Icons.LOGIN,
                                            bgcolor=ft.Colors.BLUE,
                                            color=ft.Colors.WHITE,
                                            style=ft.ButtonStyle(
                                                shape=ft.RoundedRectangleBorder(radius=10),
                                                padding=ft.padding.symmetric(
                                                    horizontal=30, vertical=15
                                                ),
                                                animation_duration=200,
                                            ),
                                            on_click=lambda e: self._on_login_click(e),
                                            animate_scale=ft.Animation(
                                                200, ft.AnimationCurve.EASE_OUT
                                            ),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=20,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=30,
                        width=500,
                    ),
                    elevation=5,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _get_course_list_content(self) -> ft.Row:
        """
        获取课程列表界面内容（左右分栏布局）

        Returns:
            ft.Row: 左右分栏的界面组件
        """
        # 左侧课程列表面板（独立滚动）
        left_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "课程列表",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    # 课程卡片列表容器，独立滚动
                    ft.ListView(
                        controls=self._create_course_cards(),
                        expand=True,
                        spacing=10,
                    ),
                ],
                expand=True,
            ),
            expand=2,  # 占据2/3宽度
            padding=ft.padding.all(10),
            bgcolor=ft.Colors.GREY_50,
            border_radius=10,
        )

        # 右侧信息面板（固定布局，不滚动）
        right_panel = ft.Container(
            content=ft.Column(
                [
                    # 上半部分：统计信息
                    self._create_course_stats_panel() if self.selected_course else self._create_empty_stats_panel(),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    # 下半部分：功能按钮
                    self._create_action_panel(),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            expand=1,  # 占据1/3宽度
            padding=ft.padding.all(10),
        )

        # 计算可用高度（视口高度减去导航栏和边距）
        available_height = (self.page.window.height - 100) if hasattr(self.page, 'window') else 600

        return ft.Row(
            [
                left_panel,
                ft.VerticalDivider(width=1),
                right_panel,
            ],
            height=available_height,  # 设置明确的高度，关键！
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.START,
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

            card = ft.GestureDetector(
                content=ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.BOOK,
                                        color=ft.Colors.BLUE,
                                        size=36,
                                    ),
                                    title=ft.Text(
                                        course_name,
                                        weight=ft.FontWeight.BOLD,
                                        size=16,
                                    ),
                                    subtitle=ft.Text(
                                        f"ID: {ecourse_id[:16]}...",
                                        size=12,
                                        color=ft.Colors.GREY_600,
                                    ),
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=15,
                        bgcolor=ft.Colors.BLUE_50 if self.selected_course == course else None,
                    ),
                    elevation=2,
                    margin=ft.margin.only(bottom=10),
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
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.INFO_OUTLINE,
                        size=48,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        "请选择一门课程",
                        size=16,
                        color=ft.Colors.GREY_600,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            bgcolor=ft.Colors.GREY_100,
            border_radius=10,
            alignment=ft.Alignment(0, 0),
        )

    def _create_course_stats_panel(self) -> ft.Container:
        """
        创建课程统计信息面板

        Returns:
            ft.Container: 统计信息面板
        """
        course_name = self.selected_course.get('lessonName', '未知课程')
        ecourse_id = self.selected_course.get('eCourseID', '')

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "课程信息",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.BLUE),
                        title=ft.Text("课程名称", size=12, color=ft.Colors.GREY_600),
                        subtitle=ft.Text(course_name, size=14, weight=ft.FontWeight.BOLD),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.VPN_KEY, color=ft.Colors.GREEN),
                        title=ft.Text("课程ID", size=12, color=ft.Colors.GREY_600),
                        subtitle=ft.Text(ecourse_id, size=12, selectable=True),
                    ),
                ],
                spacing=0,
            ),
            padding=20,
            bgcolor=ft.Colors.BLUE_50,
            border_radius=10,
        )

    def _create_action_panel(self) -> ft.Container:
        """
        创建功能按钮面板

        Returns:
            ft.Container: 功能按钮面板
        """
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "操作",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    ft.ElevatedButton(
                        "导入题库",
                        icon=ft.Icons.ATTACH_FILE,
                        bgcolor=ft.Colors.GREEN,
                        color=ft.Colors.WHITE,
                        width=280,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=20, vertical=12),
                        ),
                        on_click=lambda e: self._on_select_json_bank(e),
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.ElevatedButton(
                        "开始答题（API模式）",
                        icon=ft.Icons.FLASH_ON,
                        bgcolor=ft.Colors.ORANGE,
                        color=ft.Colors.WHITE,
                        width=280,
                        disabled=not self.question_bank_data,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=20, vertical=12),
                        ),
                        on_click=lambda e: self._on_start_api_answer(e),
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.OutlinedButton(
                        "返回主界面",
                        icon=ft.Icons.HOME,
                        width=280,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.padding.symmetric(horizontal=20, vertical=12),
                        ),
                        on_click=lambda e: self._on_back_to_main(e),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
            bgcolor=ft.Colors.GREY_50,
            border_radius=10,
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
                print(f"✅ 成功获取 access_token: {access_token[:20]}...")

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
                    dialog = ft.AlertDialog(
                        title=ft.Row(
                            [
                                ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
                                ft.Text("题库课程不匹配", color=ft.Colors.ORANGE, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=10,
                        ),
                        content=ft.Column(
                            [
                                ft.Text("⚠️ 警告：您已导入的题库与新选择的课程不匹配！", size=16, weight=ft.FontWeight.BOLD),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text("📋 课程信息：", weight=ft.FontWeight.BOLD),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.ORANGE),
                                    title=ft.Text("已导入的题库"),
                                    subtitle=ft.Column(
                                        [
                                            ft.Text(f"课程名: {bank_course_name}"),
                                            ft.Text(f"ID: {bank_course_id}", size=12, color=ft.Colors.GREY_600),
                                        ],
                                        spacing=2,
                                    ),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.BLUE),
                                    title=ft.Text("新选择的课程"),
                                    subtitle=ft.Column(
                                        [
                                            ft.Text(f"课程名: {new_course_name}"),
                                            ft.Text(f"ID: {new_course_id}", size=12, color=ft.Colors.GREY_600),
                                        ],
                                        spacing=2,
                                    ),
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "💡 请选择以下操作：",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=5,
                            tight=True,
                        ),
                        actions=[
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "清除题库",
                                        icon=ft.Icons.DELETE,
                                        bgcolor=ft.Colors.RED,
                                        color=ft.Colors.WHITE,
                                        on_click=lambda e: self._on_clear_question_bank(e, course),
                                    ),
                                    ft.ElevatedButton(
                                        "取消选择",
                                        icon=ft.Icons.CANCEL,
                                        bgcolor=ft.Colors.GREY,
                                        color=ft.Colors.WHITE,
                                        on_click=lambda e: self._on_cancel_course_selection(e, old_course),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=20,
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.CENTER,
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

        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)

            file_path = filedialog.askopenfilename(
                title="选择JSON题库文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )

            root.destroy()

            if file_path:
                print(f"DEBUG: 选择的文件 = {file_path}")
                self._process_selected_json_file(file_path)

        except Exception as ex:
            print(f"❌ 打开文件选择对话框失败: {ex}")
            dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                        ft.Text("打开文件选择器失败", color=ft.Colors.RED),
                    ],
                    spacing=10,
                ),
                content=ft.Text(f"❌ 无法打开文件选择对话框：{str(ex)}"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)

    def _process_selected_json_file(self, file_path: str):
        """处理选中的JSON文件"""
        from pathlib import Path

        file_name = Path(file_path).name

        try:
            importer = QuestionBankImporter()
            success = importer.import_from_file(file_path)

            if not success:
                raise ValueError("无法导入题库文件")

            bank_type = importer.get_bank_type()
            print("\n" + importer.format_output())

            if bank_type == "single":
                parsed = importer.parse_single_course()
                stats = parsed["statistics"] if parsed else {}
                preview = f"""
📊 题库统计：
  班级：{parsed['class']['name'] if parsed else '未知'}
  课程：{parsed['course']['courseName'] if parsed else '未知'}
  章节数：{stats.get('totalChapters', 0)}
  知识点数：{stats.get('totalKnowledges', 0)}
  题目数：{stats.get('totalQuestions', 0)}
  选项数：{stats.get('totalOptions', 0)}
"""
            elif bank_type == "multiple":
                parsed = importer.parse_multiple_courses()
                stats = parsed["statistics"] if parsed else {}
                preview = f"""
📊 题库统计：
  班级：{parsed['class']['name'] if parsed else '未知'}
  课程数：{stats.get('totalCourses', 0)}
  章节数：{stats.get('totalChapters', 0)}
  知识点数：{stats.get('totalKnowledges', 0)}
  题目数：{stats.get('totalQuestions', 0)}
  选项数：{stats.get('totalOptions', 0)}
"""
            else:
                preview = "⚠️ 未知的题库类型"

            self.question_bank_data = importer.data

            print(f"✅ 成功加载JSON题库: {file_name}")

            # 验证题库课程ID与选择的课程ID是否匹配
            if self.selected_course and bank_type == "single":
                # 从题库中提取课程ID
                parsed = importer.parse_single_course()
                bank_course_id = ""
                if parsed and 'course' in parsed:
                    bank_course_id = parsed['course'].get('courseID', '')

                # 获取当前选择的课程ID
                selected_course_id = self.selected_course.get('eCourseID', '')

                print(f"DEBUG: 题库课程ID = {bank_course_id}")
                print(f"DEBUG: 选择课程ID = {selected_course_id}")

                # 如果题库中有课程ID，且与选择的课程ID不匹配，显示错误提示
                if bank_course_id and selected_course_id and bank_course_id != selected_course_id:
                    print(f"❌ 题库课程不匹配")
                    dialog = ft.AlertDialog(
                        title=ft.Row(
                            [
                                ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                                ft.Text("题库课程不匹配", color=ft.Colors.RED, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=10,
                        ),
                        content=ft.Column(
                            [
                                ft.Text("❌ 错误：您导入的题库与当前选择的课程不匹配！", size=16, weight=ft.FontWeight.BOLD),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text("📋 课程信息：", weight=ft.FontWeight.BOLD),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.BLUE),
                                    title=ft.Text("当前选择的课程"),
                                    subtitle=ft.Column(
                                        [
                                            ft.Text(f"课程名: {self.selected_course.get('lessonName', '未知')}"),
                                            ft.Text(f"ID: {selected_course_id}", size=12, color=ft.Colors.GREY_600),
                                        ],
                                        spacing=2,
                                    ),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.ORANGE),
                                    title=ft.Text("题库中的课程"),
                                    subtitle=ft.Column(
                                        [
                                            ft.Text(f"课程名: {parsed['course'].get('courseName', '未知')}"),
                                            ft.Text(f"ID: {bank_course_id}", size=12, color=ft.Colors.GREY_600),
                                        ],
                                        spacing=2,
                                    ),
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "💡 提示：请选择与题库匹配的课程，或导入正确的题库文件",
                                    size=14,
                                    color=ft.Colors.GREY_700,
                                    italic=True,
                                ),
                            ],
                            spacing=5,
                            tight=True,
                        ),
                        actions=[
                            ft.ElevatedButton(
                                "知道了",
                                icon=ft.Icons.CHECK,
                                bgcolor=ft.Colors.RED,
                                color=ft.Colors.WHITE,
                                on_click=lambda _: self.page.pop_dialog(),
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.CENTER,
                    )
                    self.page.show_dialog(dialog)

                    # 清除已导入的题库数据
                    self.question_bank_data = None
                    return

            # 创建并显示成功对话框（不刷新界面，避免动画冲突）
            dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                        ft.Text("题库加载成功", color=ft.Colors.GREEN),
                    ],
                    spacing=10,
                ),
                content=ft.Column(
                    [
                        ft.Text(f"✅ 成功加载题库文件"),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Text(f"📄 文件名: {file_name}"),
                        ft.Text(f"📁 路径: {file_path}"),
                        ft.Text(f"🏷️ 类型: {bank_type if bank_type else '未知'}"),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Text(preview, size=12, color=ft.Colors.GREY_700),
                    ],
                    spacing=5,
                    tight=True,
                ),
                actions=[
                    ft.TextButton("确定", on_click=self._on_import_dialog_close),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)

        except json.JSONDecodeError as je:
            print(f"❌ JSON解析失败: {je}")
            dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                        ft.Text("JSON格式错误", color=ft.Colors.RED),
                    ],
                    spacing=10,
                ),
                content=ft.Column(
                    [
                        ft.Text("❌ 文件不是有效的JSON格式"),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Text(f"📄 文件: {file_name}"),
                        ft.Text(f"💡 错误信息: {str(je)}", size=12, color=ft.Colors.RED_700),
                    ],
                    spacing=5,
                    tight=True,
                ),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)

        except Exception as ex:
            print(f"❌ 读取文件失败: {ex}")
            dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                        ft.Text("读取文件失败", color=ft.Colors.RED),
                    ],
                    spacing=10,
                ),
                content=ft.Column(
                    [
                        ft.Text("❌ 无法读取文件内容"),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Text(f"📄 文件: {file_name}"),
                        ft.Text(f"💡 错误信息: {str(ex)}", size=12, color=ft.Colors.RED_700),
                    ],
                    spacing=5,
                    tight=True,
                ),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)

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
                        ft.Container(
                            content=ft.Column(
                                [self.log_text],
                                scroll=ft.ScrollMode.ALWAYS,
                                auto_scroll=False,
                            ),
                            width=600,
                            height=400,
                            bgcolor=ft.Colors.GREY_100,
                            border=ft.border.all(1, ft.Colors.GREY_300),
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
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                    ),
                    on_click=self._on_stop_answering,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        return dialog

    def _append_log(self, message: str):
        """追加日志"""
        if self.log_text:
            current_text = self.log_text.value if self.log_text.value else ""
            new_text = current_text + message + "\n"
            if len(new_text) > 2000:
                new_text = "...(日志已截断)\n" + new_text[-2000:]
            self.log_text.value = new_text
            try:
                self.log_text.update()
            except Exception as e:
                print(f"⚠️ UI更新失败: {e}")

    def _on_stop_answering(self, e):
        """处理停止答题"""
        print("🛑 用户请求停止答题")
        self._append_log("🛑 正在停止答题...\n")
        self.should_stop_answering = True

        if self.auto_answer_instance and hasattr(self.auto_answer_instance, 'request_stop'):
            self.auto_answer_instance.request_stop()

        if self.answer_dialog:
            self.page.pop_dialog()
            self.answer_dialog = None

        self.is_answering = False
        self._append_log("✅ 答题已停止\n")

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

            # 创建API答题器
            answerer = APICourseAnswer(access_token=self.access_token)
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
            self.is_answering = False
            self.should_stop_answering = False
            self.auto_answer_instance = None
