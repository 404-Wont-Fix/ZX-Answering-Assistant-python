"""
ZX Answering Assistant - 评估答题视图模块

This module contains the UI components for the answering page.
"""

import flet as ft
import json
import sys
from pathlib import Path
from io import StringIO
from src.student_login import (
    get_student_access_token,
    get_student_courses,
    get_uncompleted_chapters,
    navigate_to_course,
    get_course_progress_from_page,
    get_access_token_from_browser,
    is_browser_alive,
    clear_access_token,
    cleanup_browser,
)
from src.settings import get_settings_manager


class AnsweringView:
    """评估答题页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化评估答题视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app  # 保存MainApp引用
        self.current_content = None  # 保存当前内容容器的引用
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框
        self.remember_password_checkbox = None  # 记住密码复选框
        self.access_token = None  # 存储获取的access_token
        self.progress_dialog = None  # 登录进度对话框
        self.course_list = []  # 存储课程列表
        self.username = ""  # 存储登录的用户名
        self.current_course = None  # 当前选中的课程
        self.current_progress = None  # 当前课程进度信息
        self.current_uncompleted = None  # 当前课程未完成知识点列表
        self.question_bank_data = None  # 存储加载的题库数据

        # 答题相关状态
        self.is_answering = False  # 是否正在答题
        self.answer_dialog = None  # 答题日志对话框
        self.log_text = None  # 日志文本控件
        self.auto_answer_instance = None  # 自动答题实例
        self.should_stop_answering = False  # 停止答题标志

        # 设置管理器
        self.settings_manager = get_settings_manager()

    def get_content(self) -> ft.Column:
        """
        获取评估答题页面的内容

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
            expand=True,
        )

        return ft.Column(
            [self.current_content],
            scroll=ft.ScrollMode.AUTO,
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
                    "评估答题",
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
                                    title=ft.Text("学生端登录", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("登录学生端平台进行身份验证"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.GREEN),
                                    title=ft.Text("选择课程", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("查看并选择需要完成的课程"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.ORANGE),
                                    title=ft.Text("开始答题", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("自动加载题库并完成课程评估答题"),
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
        获取学生登录界面内容

        Returns:
            ft.Column: 登录界面组件
        """
        # 加载已保存的凭据
        saved_username, saved_password = self.settings_manager.get_student_credentials()

        # 初始化输入框（自动填充已保存的凭据）
        self.username_field = ft.TextField(
            label="账号",
            hint_text="请输入学生端账号",
            value=saved_username or "",
            width=400,
            prefix_icon=ft.Icons.PERSON,
            autofocus=True,
        )

        self.password_field = ft.TextField(
            label="密码",
            hint_text="请输入学生端密码",
            value=saved_password or "",
            width=400,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )

        # 创建"记住我"复选框
        self.remember_password_checkbox = ft.Checkbox(
            label="记住我（自动保存账号和密码）",
            value=bool(saved_username and saved_password),  # 如果已保存凭据，默认勾选
            fill_color=ft.Colors.BLUE,
        )

        return ft.Column(
            [
                ft.Text(
                    "学生端登录",
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
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                self.remember_password_checkbox,
                                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                                ft.Row(
                                    [
                                        ft.OutlinedButton(
                                            "返回",
                                            icon=ft.Icons.ARROW_BACK,
                                            style=ft.ButtonStyle(
                                                animation_duration=200,
                                            ),
                                            on_click=lambda e: self._on_back_click(e),
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

    def _on_start_answer_click(self, e):
        """处理开始答题按钮点击事件 - 切换到登录界面"""
        print("DEBUG: 切换到登录界面")  # 调试信息

        # 使用动画切换到登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_click(self, e):
        """处理返回按钮点击事件 - 返回主界面"""
        print("DEBUG: 返回主界面")  # 调试信息

        # 使用动画切换回主界面
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

        # 显示登录进度对话框
        self.progress_dialog = ft.AlertDialog(
            title=ft.Text("正在登录"),
            content=ft.Column(
                [
                    ft.Text(f"正在使用以下账号登录学生端...\n账号: {username}"),
                    ft.ProgressRing(stroke_width=3),
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.show_dialog(self.progress_dialog)

        # 使用 Flet 的线程安全方式执行登录
        self.page.run_thread(self._perform_login, username, password)

    def _perform_login(self, username: str, password: str):
        """
        在后台线程中执行学生端登录

        Args:
            username: 学生账号
            password: 学生密码
        """
        try:
            # 调用学生登录函数
            access_token = get_student_access_token(username, password, keep_browser=True)

            if access_token:
                self.access_token = access_token
                self.username = username
                print(f"✅ 成功获取 access_token: {access_token[:20]}...")

                # 根据复选框状态保存凭据
                if self.remember_password_checkbox.value:
                    print("💾 保存学生端凭据...")
                    self.settings_manager.set_student_credentials(username, password)
                else:
                    print("🗑️ 清除学生端凭据...")
                    self.settings_manager.clear_student_credentials()

                # 更新进度对话框
                self.progress_dialog.content = ft.Column(
                    [
                        ft.Text("✅ 登录成功！\n正在获取课程列表..."),
                        ft.ProgressRing(stroke_width=3),
                    ],
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
                self.page.update()

                # 获取课程列表
                try:
                    courses = get_student_courses(access_token)

                    if courses and len(courses) > 0:
                        self.course_list = courses
                        print(f"✅ 成功获取 {len(courses)} 门课程")

                        # 为每门课程获取未完成的知识点
                        for course in courses:
                            course_id = course.get('courseID')
                            if course_id:
                                try:
                                    print(f"正在获取课程 {course.get('courseName')} 的未完成知识点...")
                                    uncompleted = get_uncompleted_chapters(access_token, course_id)
                                    if uncompleted and len(uncompleted) > 0:
                                        course['uncompleted_knowledges'] = uncompleted
                                        print(f"  ✅ {course.get('courseName')}: {len(uncompleted)} 个未完成知识点")
                                    else:
                                        # 课程已完成或无未完成知识点
                                        course['uncompleted_knowledges'] = []
                                        print(f"  ✅ {course.get('courseName')}: 已完成或无未完成知识点")
                                except Exception as e:
                                    print(f"  ❌ 获取课程 {course.get('courseName')} 未完成知识点失败: {e}")
                                    course['uncompleted_knowledges'] = []

                        # 关闭进度对话框
                        self.page.pop_dialog()

                        # 切换到课程列表界面
                        courses_content = self._get_courses_content()
                        self.current_content.content = courses_content
                        self.page.update()

                    else:
                        print("❌ 未获取到课程列表")

                        # 关闭进度对话框
                        self.page.pop_dialog()

                        error_dialog = ft.AlertDialog(
                            title=ft.Text("获取课程失败"),
                            content=ft.Text(
                                "❌ 未能获取到课程列表\n"
                                "请查看控制台日志了解详情。"
                            ),
                            actions=[
                                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                            ],
                        )
                        self.page.show_dialog(error_dialog)

                except Exception as e:
                    print(f"❌ 获取课程列表异常: {str(e)}")

                    # 关闭进度对话框
                    self.page.pop_dialog()

                    error_dialog = ft.AlertDialog(
                        title=ft.Text("获取课程异常"),
                        content=ft.Text(
                            f"❌ 获取课程列表时发生异常：\n{str(e)}\n\n"
                            f"请查看控制台日志了解详情。"
                        ),
                        actions=[
                            ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                        ],
                    )
                    self.page.show_dialog(error_dialog)

            else:
                print("❌ 登录失败，未能获取 access_token")

                # 登录失败，更新UI
                self.page.pop_dialog()

                error_dialog = ft.AlertDialog(
                    title=ft.Text("登录失败"),
                    content=ft.Text(
                        "❌ 学生端登录失败，请检查账号密码是否正确\n"
                        "或查看控制台日志了解详情。"
                    ),
                    actions=[
                        ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(error_dialog)

        except Exception as e:
            print(f"❌ 登录过程中发生异常: {str(e)}")

            # 发生异常，更新UI
            try:
                self.page.pop_dialog()

                error_dialog = ft.AlertDialog(
                    title=ft.Text("登录异常"),
                    content=ft.Text(
                        f"❌ 登录过程中发生异常：\n{str(e)}\n\n"
                        f"请查看控制台日志了解详情。"
                    ),
                    actions=[
                        ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(error_dialog)
            except:
                pass

    def _get_courses_content(self) -> ft.Column:
        """
        获取课程列表界面内容

        Returns:
            ft.Column: 课程列表界面组件
        """
        # 创建课程卡片列表
        course_cards = []

        for idx, course in enumerate(self.course_list):
            try:
                print(f"正在渲染课程卡片 {idx + 1}/{len(self.course_list)}: {course.get('courseName', '未知')}")

                # 计算未完成的知识点数量
                uncompleted_count = course.get('kpCount', 0) - course.get('completeCount', 0)

                # 创建课程卡片（可点击）
                card_content = ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.BOOK,
                                    color=ft.Colors.BLUE,
                                    size=40,
                                ),
                                title=ft.Text(
                                    course.get('courseName', '未知课程'),
                                    weight=ft.FontWeight.BOLD,
                                    size=18,
                                ),
                                subtitle=ft.Column(
                                    [
                                        ft.Text(
                                            f"👤 指导老师: {course.get('teacherName', '未知')}",
                                            size=14,
                                        ),
                                        ft.Text(
                                            f"📊 完成进度: {course.get('completeCount', 0)}/{course.get('kpCount', 0)} 个知识点",
                                            size=14,
                                        ),
                                        ft.ProgressBar(
                                            value=course.get('completeRate', 0),
                                            width=300,
                                            color=ft.Colors.GREEN,
                                        ),
                                    ],
                                    spacing=5,
                                ),
                            ),
                            ft.Divider(height=1, color=ft.Colors.TRANSPARENT),
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.CHECK_CIRCLE,
                                        color=ft.Colors.GREEN if course.get('completeRate', 0) >= 1.0 else ft.Colors.GREY,
                                        size=20,
                                    ),
                                    ft.Text(
                                        f"已完成: {course.get('completeCount', 0)}",
                                        size=14,
                                    ),
                                    ft.Icon(
                                        ft.Icons.PENDING,
                                        color=ft.Colors.ORANGE if uncompleted_count > 0 else ft.Colors.GREY,
                                        size=20,
                                    ),
                                    ft.Text(
                                        f"未完成: {uncompleted_count}",
                                        size=14,
                                    ),
                                    ft.Container(expand=True),  # Spacer
                                    ft.Icon(
                                        ft.Icons.ARROW_FORWARD_IOS,
                                        color=ft.Colors.BLUE_400,
                                        size=16,
                                    ),
                                ],
                                    spacing=20,
                                ),
                        ],
                        spacing=0,
                    ),
                    padding=20,
                    width=700,
                )

                card = ft.GestureDetector(
                    content=ft.Card(
                        content=card_content,
                        elevation=3,
                        margin=ft.margin.only(bottom=15),
                    ),
                    on_tap=lambda e, c=course: self._on_course_card_click(e, c),
                    mouse_cursor=ft.MouseCursor.CLICK,
                )

                course_cards.append(card)
                print(f"  ✅ 课程卡片渲染成功: {course.get('courseName')}")

            except Exception as e:
                print(f"  ❌ 渲染课程卡片失败: {course.get('courseName')} - {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        return ft.Column(
            [
                # 标题栏
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            icon_color=ft.Colors.BLUE,
                            on_click=lambda e: self._on_back_from_courses(e),
                        ),
                        ft.Text(
                            "课程列表",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_800,
                            expand=True,
                        ),
                        ft.Text(
                            f"欢迎, {self.username}",
                            size=16,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 课程统计信息
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.BLUE, size=30),
                                ft.Text(
                                    f"共 {len(self.course_list)} 门课程",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=15,
                        width=700,
                    ),
                    elevation=2,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 课程卡片列表
                *course_cards,
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _on_back_from_courses(self, e):
        """处理从课程列表返回的按钮点击事件"""
        print("DEBUG: 返回登录界面")  # 调试信息

        # 切换回登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _get_course_detail_content(self, course: dict) -> ft.Column:
        """
        获取课程详情界面内容（左右分栏布局）

        Args:
            course (dict): 课程信息字典

        Returns:
            ft.Column: 课程详情界面组件（可滚动的左右分栏）
        """
        # 保存当前选中的课程
        self.current_course = course

        # 获取课程ID
        course_id = course.get('courseID')
        course_name = course.get('courseName', '未知课程')

        # 生成进度信息卡片内容
        progress_card = self._create_progress_card(course_name)

        # 生成未完成知识点列表卡片内容
        knowledge_card = self._create_knowledge_list_card(course)

        # 答题选项菜单（移到左侧）
        option_menu = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(
                                ft.Icons.SETTINGS,
                                color=ft.Colors.PURPLE,
                                size=30,
                            ),
                            title=ft.Text(
                                "答题选项菜单",
                                weight=ft.FontWeight.BOLD,
                                size=20,
                            ),
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                        ft.ElevatedButton(
                            "获取答案",
                            icon=ft.Icons.DOWNLOAD,
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                            width=280,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            ),
                            on_click=lambda e: self._on_extract_answers(e, course_id),
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.ElevatedButton(
                            "使用JSON题库",
                            icon=ft.Icons.ATTACH_FILE,
                            bgcolor=ft.Colors.GREEN,
                            color=ft.Colors.WHITE,
                            width=280,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            ),
                            on_click=lambda e: self._on_use_json_bank(e),
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.ElevatedButton(
                            "开始自动做题(兼容模式)",
                            icon=ft.Icons.PLAY_ARROW,
                            bgcolor=ft.Colors.ORANGE,
                            color=ft.Colors.WHITE,
                            width=280,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            ),
                            on_click=lambda e: self._on_start_compatibility_mode(e, course_id),
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.ElevatedButton(
                            "开始自动做题(暴力模式)",
                            icon=ft.Icons.FLASH_ON,
                            bgcolor=ft.Colors.RED,
                            color=ft.Colors.WHITE,
                            width=280,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            ),
                            on_click=lambda e: self._on_start_brute_mode(e, course_id),
                        ),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        ft.OutlinedButton(
                            "返回课程列表",
                            icon=ft.Icons.ARROW_BACK,
                            width=280,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            ),
                            on_click=lambda e: self._on_back_from_course_detail(e),
                        ),
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=25,
            ),
            elevation=3,
            margin=ft.margin.all(0),
        )

        # 左侧区域：进度信息 + 答题选项菜单（铺满左侧）
        left_column = ft.Column(
            [
                progress_card,
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=option_menu,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # 右侧区域：未完成知识点列表（填充剩余区域）
        right_column = ft.Container(
            content=knowledge_card,
            expand=True,
        )

        # 左右分栏内容
        detail_row = ft.Row(
            [
                # 左侧：进度信息 + 答题选项菜单（扩展填充）
                ft.Container(
                    content=left_column,
                    expand=True,
                ),
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                # 右侧：未完成知识点列表（填充剩余区域）
                right_column,
            ],
            expand=True,
            spacing=0,
        )

        # 包装在Column中，铺满窗口
        return ft.Column(
            [
                detail_row,
            ],
            expand=True,
            spacing=0,
        )

    def _update_progress_info(self):
        """更新课程进度信息卡片（已弃用，使用 _perform_course_navigation_and_load 代替）"""
        # 在后台线程中执行进度获取
        self.page.run_thread(self._perform_progress_update)

    def _perform_course_navigation_and_load(self):
        """在后台线程中执行课程导航和数据加载"""
        course_id = self.current_course.get('courseID')
        course_name = self.current_course.get('courseName', '未知课程')

        try:
            # 导航到课程页面
            print(f"正在导航到课程页面: {course_name}")
            success = navigate_to_course(course_id)

            if not success:
                # 检查浏览器是否挂掉
                if not is_browser_alive():
                    print("❌ 检测到浏览器已挂掉")

                    # 清理旧浏览器实例
                    cleanup_browser()
                    clear_access_token()

                    # 提示用户重新登录
                    self.page.pop_dialog()  # 关闭进度对话框

                    # 显示重新登录对话框
                    relogin_dialog = ft.AlertDialog(
                        title=ft.Row(
                            [
                                ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
                                ft.Text("浏览器已断开", weight=ft.FontWeight.BOLD),
                            ],
                            spacing=10,
                        ),
                        content=ft.Text(
                            "⚠️ 检测到浏览器已断开连接\n\n"
                            "可能原因：\n"
                            "• 浏览器进程意外退出\n"
                            "• 网络连接中断\n\n"
                            "请点击下方按钮重新登录"
                        ),
                        actions=[
                            ft.TextButton("重新登录", on_click=self._on_relogin_from_navigation),
                            ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                        ],
                    )
                    self.page.show_dialog(relogin_dialog)
                    return
                else:
                    print("❌ 导航到课程页面失败（浏览器正常）")
                    self._show_error_dialog("导航失败", "无法导航到课程页面，请查看控制台日志。")
                    return

            # 导航成功，继续后续流程
            # 刷新token（如果需要）
            new_token = get_access_token_from_browser()
            if new_token:
                self.access_token = new_token
            print("✅ 成功导航到课程页面")

            # 获取进度信息（从已加载的页面）
            print("正在获取课程进度...")
            progress = get_course_progress_from_page()
            if progress:
                self.current_progress = progress
                print(f"✅ 成功获取进度: {progress}")

                # 获取未完成知识点列表
                print("正在获取未完成知识点列表...")
                uncompleted = get_uncompleted_chapters(self.access_token, course_id)
                self.current_uncompleted = uncompleted or []
                print(f"✅ 成功获取 {len(self.current_uncompleted)} 个未完成知识点")

                # 直接调用UI更新（Flet应该会自动处理线程切换）
                self._refresh_course_detail_ui()
            else:
                print("❌ 获取课程进度失败")
                self._show_error_dialog("获取进度失败", "无法获取课程进度信息，请查看控制台日志。")
        except Exception as ex:
            print(f"❌ 导航异常: {str(ex)}")
            import traceback
            traceback.print_exc()
            self._show_error_dialog("导航异常", f"导航时发生异常：{str(ex)}")

    def _perform_progress_update(self):
        """在后台线程中执行进度更新（不包含浏览器操作）"""
        try:
            # 检查浏览器是否存活
            if not is_browser_alive():
                print("❌ 检测到浏览器已挂掉")

                # 清理旧浏览器实例
                cleanup_browser()
                clear_access_token()

                # 提示用户重新登录
                self.page.pop_dialog()  # 关闭进度对话框

                # 显示重新登录对话框
                relogin_dialog = ft.AlertDialog(
                    title=ft.Row(
                        [
                            ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
                            ft.Text("浏览器已断开", weight=ft.FontWeight.BOLD),
                        ],
                        spacing=10,
                    ),
                    content=ft.Text(
                        "⚠️ 检测到浏览器已断开连接\n\n"
                        "无法获取课程进度信息\n\n"
                        "请点击下方按钮重新登录"
                    ),
                    actions=[
                        ft.TextButton("重新登录", on_click=self._on_relogin_from_progress),
                        ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(relogin_dialog)
                return

            # 获取进度信息（从已加载的页面）
            print("正在获取课程进度...")
            progress = get_course_progress_from_page()
            if progress:
                self.current_progress = progress
                print(f"✅ 成功获取进度: {progress}")

                # 获取未完成知识点列表
                print("正在获取未完成知识点列表...")
                course_id = self.current_course.get('courseID')
                uncompleted = get_uncompleted_chapters(self.access_token, course_id)
                self.current_uncompleted = uncompleted or []
                print(f"✅ 成功获取 {len(self.current_uncompleted)} 个未完成知识点")

                # 在主线程中更新UI
                self.page.run_thread(self._refresh_course_detail_ui)
            else:
                print("❌ 获取课程进度失败")
                # 在主线程中显示错误对话框
                self.page.run_thread(lambda: self._show_error_dialog("获取进度失败", "无法获取课程进度信息，请查看控制台日志。"))
        except Exception as e:
            print(f"❌ 更新进度信息异常: {str(e)}")
            import traceback
            traceback.print_exc()
            # 在主线程中显示错误对话框
            self.page.run_thread(lambda: self._show_error_dialog("更新失败", f"更新进度信息时发生异常：{str(e)}"))

    def _refresh_course_detail_ui(self):
        """刷新课程详情界面（在主线程中调用）"""
        # 重新生成课程详情内容
        detail_content = self._get_course_detail_content(self.current_course)
        self.current_content.content = detail_content
        self.page.update()

    def _on_extract_answers(self, _e, course_id: str):
        """处理提取答案按钮点击事件"""
        print(f"DEBUG: 提取课程答案 - 课程ID: {course_id}")

        if self.main_app:
            # 切换到答案提取页面（导航索引 = 1）
            # 直接设置导航栏的选中索引
            self.main_app.navigation_rail.selected_index = 1

            # 创建一个模拟的事件对象，用于调用 _on_destination_changed
            class ControlEvent:
                def __init__(self, control):
                    self.control = control

            mock_event = ControlEvent(self.main_app.navigation_rail)
            self.main_app._on_destination_changed(mock_event)

            # 更新UI
            self.main_app.navigation_rail.update()

            # TODO: 可以在这里传递课程ID到答案提取页面
            # 让提取页面自动开始提取该课程的答案
            # self.main_app.extraction_view.start_extract_course(course_id)
        else:
            # 如果没有MainApp引用，显示提示
            dialog = ft.AlertDialog(
                title=ft.Text("错误"),
                content=ft.Text("无法切换到答案提取页面：MainApp引用未找到"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)

    def _on_use_json_bank(self, e):
        """处理使用JSON题库按钮点击事件"""
        print("DEBUG: 使用JSON题库")

        # 使用 tkinter 文件选择器（更可靠）
        try:
            import tkinter as tk
            from tkinter import filedialog

            # 创建隐藏的 tkinter 根窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            root.wm_attributes('-topmost', 1)  # 置顶显示

            # 打开文件选择对话框
            file_path = filedialog.askopenfilename(
                title="选择JSON题库文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )

            # 销毁 tkinter 窗口
            root.destroy()

            # 检查用户是否选择了文件
            if file_path:
                print(f"DEBUG: 选择的文件 = {file_path}")
                # 调用文件选择处理逻辑
                self._process_selected_json_file(file_path)
            else:
                print("DEBUG: 用户取消了文件选择")

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
        """
        处理选中的JSON文件

        Args:
            file_path: JSON文件路径
        """
        from pathlib import Path
        from src.question_bank_importer import QuestionBankImporter

        file_name = Path(file_path).name

        try:
            # 使用 QuestionBankImporter 导入并解析题库
            importer = QuestionBankImporter()
            success = importer.import_from_file(file_path)

            if not success:
                raise ValueError("无法导入题库文件")

            # 获取题库类型
            bank_type = importer.get_bank_type()

            # 格式化输出题库信息（打印到控制台）
            print("\n" + importer.format_output())

            # 计算统计数据
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

            # 保存原始数据供答题使用
            self.question_bank_data = importer.data

            # 验证题库课程ID与选择的课程ID是否匹配
            if self.current_course and bank_type == "single":
                # 从题库中提取课程ID
                parsed = importer.parse_single_course()
                bank_course_id = ""
                bank_course_name = ""
                if parsed and 'course' in parsed:
                    bank_course_id = parsed['course'].get('courseID', '')
                    bank_course_name = parsed['course'].get('courseName', '')

                # 获取当前选择的课程ID
                selected_course_id = self.current_course.get('courseID', '')
                selected_course_name = self.current_course.get('courseName', '未知课程')

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
                                            ft.Text(f"课程名: {selected_course_name}"),
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
                                            ft.Text(f"课程名: {bank_course_name}"),
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

            # 显示成功对话框
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
                        ft.Text(
                            preview,
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            "💡 详细题库信息已输出到控制台",
                            size=11,
                            color=ft.Colors.BLUE_700,
                            style=ft.TextStyle(italic=True),
                        ),
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

            print(f"✅ 成功加载JSON题库: {file_name}")

        except json.JSONDecodeError as je:
            # JSON解析错误
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
            # 其他错误
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

    def _on_json_file_selected(self, e):
        """
        处理JSON文件选择完成事件

        Args:
            e: 文件选择结果事件 (FilePickerResultEvent)
        """
        if e.files and len(e.files) > 0:
            # 用户选择了文件
            file_path = e.files[0].path
            file_name = e.files[0].name
            print(f"DEBUG: 选择的文件 = {file_path}")

            try:
                # 读取并解析JSON文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 显示成功对话框
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
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.Text(
                                f"📊 数据预览:\n{json.dumps(data, ensure_ascii=False, indent=2)[:500]}...",
                                size=12,
                                color=ft.Colors.GREY_700,
                                max_lines=10,
                            ),
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

                # TODO: 这里可以添加逻辑来保存题库数据供后续使用
                # 例如：self.question_bank_data = data

                print(f"✅ 成功加载JSON题库: {file_name}")

            except json.JSONDecodeError as je:
                # JSON解析错误
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
                # 其他错误
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
        elif e.error:
            # 文件选择器发生错误
            print(f"❌ 文件选择错误: {e.error}")
            dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                        ft.Text("文件选择错误", color=ft.Colors.RED),
                    ],
                    spacing=10,
                ),
                content=ft.Text(f"❌ {e.error}"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            self.page.show_dialog(dialog)
        else:
            # 用户取消了文件选择
            print("DEBUG: 用户取消了文件选择")

    def _on_start_compatibility_mode(self, e, course_id: str):
        """处理开始兼容模式按钮点击事件"""
        print(f"DEBUG: 开始兼容模式答题 - 课程ID: {course_id}")
        self._start_answering("compatibility", course_id)

    def _on_start_brute_mode(self, e, course_id: str):
        """处理开始暴力模式按钮点击事件"""
        print(f"DEBUG: 开始暴力模式答题 - 课程ID: {course_id}")
        self._start_answering("brute", course_id)

    def _create_answer_log_dialog(self, title: str) -> ft.AlertDialog:
        """
        创建答题日志对话框

        Args:
            title: 对话框标题

        Returns:
            ft.AlertDialog: 日志对话框
        """
        # 创建日志文本控件
        self.log_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLACK,
            selectable=True,
            no_wrap=False,  # 允许换行
            max_lines=None,  # 不限制行数
        )

        # 创建对话框
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.BLUE),
                    ft.Text(title, color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Column(
                                [self.log_text],
                                scroll=ft.ScrollMode.ALWAYS,  # 改为 ALWAYS
                                auto_scroll=False,  # 关闭 auto_scroll
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
        """
        追加日志到日志文本控件

        Args:
            message: 日志消息
        """
        if self.log_text:
            current_text = self.log_text.value if self.log_text.value else ""
            new_text = current_text + message + "\n"
            # 限制日志长度，只保留最后 2000 个字符
            if len(new_text) > 2000:
                new_text = "...(日志已截断)\n" + new_text[-2000:]
            self.log_text.value = new_text
            # 在后台线程中更新UI需要使用 update 方法
            # Flet 会自动处理线程安全的UI更新
            try:
                self.log_text.update()
            except Exception as e:
                # 如果更新失败（比如线程问题），忽略错误
                print(f"⚠️ UI更新失败: {e}")

    def _on_stop_answering(self, e):
        """处理停止答题按钮点击事件"""
        print("🛑 用户请求停止答题")
        self._append_log("🛑 正在停止答题...\n")
        self.should_stop_answering = True

        # 如果有自动答题实例，调用其停止方法
        if self.auto_answer_instance and hasattr(self.auto_answer_instance, 'request_stop'):
            self.auto_answer_instance.request_stop()

        # 关闭对话框（使用 pop_dialog 而不是 close）
        if self.answer_dialog:
            self.page.pop_dialog()
            self.answer_dialog = None

        self.is_answering = False
        self._append_log("✅ 答题已停止\n")

    def _start_answering(self, mode: str, course_id: str):
        """
        开始答题（兼容模式和暴力模式）

        Args:
            mode: 答题模式 ("compatibility" 或 "brute")
            course_id: 课程ID
        """
        if self.is_answering:
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("正在答题中，请先停止当前答题任务"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 检查是否已加载题库
        if not self.question_bank_data:
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("请先加载 JSON 题库文件"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 设置答题状态
        self.is_answering = True
        self.should_stop_answering = False

        # 创建并显示日志对话框
        mode_name = "兼容模式" if mode == "compatibility" else "暴力模式"
        self.answer_dialog = self._create_answer_log_dialog(f"自动答题 - {mode_name}")
        self.page.show_dialog(self.answer_dialog)

        # 在后台线程中运行答题任务
        self.page.run_thread(lambda: self._run_answering_task(mode, course_id))

    def _run_answering_task(self, mode: str, course_id: str):
        """
        在后台线程中运行答题任务

        Args:
            mode: 答题模式
            course_id: 课程ID
        """
        try:
            mode_name = "兼容模式" if mode == "compatibility" else "暴力模式"
            self._append_log(f"🚀 开始{mode_name}答题\n")
            self._append_log(f"📚 课程ID: {course_id}\n")
            self._append_log("-" * 50 + "\n")

            if mode == "compatibility":
                # ========== 兼容模式：使用浏览器自动化 ==========
                self._append_log("📌 模式：浏览器自动化（兼容模式）\n")
                self._append_log("⏳ 正在获取浏览器实例...\n")

                from src.student_login import get_browser_page
                from src.auto_answer import AutoAnswer

                # 获取浏览器实例
                browser_page = get_browser_page()
                if not browser_page:
                    self._append_log("❌ 无法获取浏览器实例\n")
                    self._append_log("💡 请确保已经登录学生端\n")
                    return

                self._append_log("✅ 浏览器实例获取成功\n")

                # 创建自动做题器（传入日志回调）
                page = browser_page[1]  # 使用page对象
                auto_answer = AutoAnswer(page, log_callback=self._append_log)
                self.auto_answer_instance = auto_answer

                # 加载题库
                self._append_log("📖 正在加载题库...\n")
                auto_answer.load_question_bank(self.question_bank_data)
                self._append_log("✅ 题库加载成功\n")
                self._append_log("-" * 50 + "\n")

                # 答题循环
                knowledge_count = 0
                total_success = 0
                total_failed = 0

                while True:
                    # 检查停止信号
                    if self.should_stop_answering:
                        self._append_log("⚠️ 检测到停止信号，答题已终止\n")
                        break

                    self._append_log(f"\n📍 知识点 #{knowledge_count + 1}\n")
                    self._append_log("-" * 50 + "\n")

                    # 第一个知识点：检索并开始做题
                    # 之后的知识点：网站自动跳转后继续做题
                    if knowledge_count == 0:
                        self._append_log("🔍 检索第一个可作答的知识点...\n")
                        result = auto_answer.run_auto_answer(max_questions=5)
                    else:
                        self._append_log("⏳ 网站已自动跳转，继续做题...\n")
                        import time
                        time.sleep(2)  # 等待跳转完成
                        result = auto_answer.continue_auto_answer(max_questions=5)

                    # 统计
                    knowledge_count += 1
                    total_success += result['success']
                    total_failed += result['failed']

                    # 显示本次统计
                    self._append_log(f"\n📊 知识点完成统计:\n")
                    self._append_log(f"  总题数: {result['total']}\n")
                    self._append_log(f"  ✅ 成功: {result['success']}\n")
                    self._append_log(f"  ❌ 失败: {result['failed']}\n")
                    self._append_log(f"  ⏭️  跳过: {result['skipped']}\n")

                    # 检查用户是否请求停止
                    if result.get('stopped', False) or self.should_stop_answering:
                        self._append_log("\n⚠️ 用户请求停止做题\n")
                        break

                    # 检查是否还有更多知识点
                    # 通过检查当前页面是否有"开始测评"按钮来判断
                    import time
                    time.sleep(1)

                    try:
                        has_next = auto_answer.has_next_knowledge()
                        if has_next:
                            # 找到了，可以继续
                            self._append_log(f"\n✅ 检测到下一个知识点，继续...\n")
                            continue
                        else:
                            # 没找到，说明所有知识点都完成了
                            self._append_log("\n✅ 所有知识点已完成！\n")
                            break
                    except Exception as e:
                        self._append_log(f"\n❌ 检查失败: {str(e)}\n")
                        self._append_log("💡 可能所有知识点都已完成\n")
                        break

                # 最终统计
                self._append_log("\n" + "=" * 50 + "\n")
                self._append_log("📊 最终统计\n")
                self._append_log("=" * 50 + "\n")
                self._append_log(f"📍 完成知识点: {knowledge_count} 个\n")
                self._append_log(f"✅ 成功作答: {total_success} 题\n")
                self._append_log(f"❌ 失败: {total_failed} 题\n")
                self._append_log("=" * 50 + "\n")

            elif mode == "brute":
                # ========== 暴力模式：使用API直接请求 ==========
                self._append_log("📌 模式：API直接请求（暴力模式）\n")
                self._append_log("⏳ 正在获取access_token...\n")

                from src.student_login import get_cached_access_token
                from src.api_auto_answer import APIAutoAnswer

                # 获取access_token（使用缓存管理）
                access_token = get_cached_access_token()

                if not access_token:
                    self._append_log("⚠️ 自动获取access_token失败\n")
                    self._append_log("💡 请先登录学生端获取token\n")
                    return

                self._append_log("✅ access_token获取成功\n")
                self._append_log(f"🔑 Token: {access_token[:20]}...\n")

                # 创建API自动做题器（传入日志回调）
                api_answer = APIAutoAnswer(access_token, log_callback=self._append_log)
                self.auto_answer_instance = api_answer

                # 加载题库
                self._append_log("📖 正在加载题库...\n")
                api_answer.load_question_bank(self.question_bank_data)
                self._append_log("✅ 题库加载成功\n")
                self._append_log("-" * 50 + "\n")

                # 执行自动做题
                self._append_log("🚀 开始自动完成所有知识点\n")
                self._append_log("💡 提示：按 Ctrl+C 可随时中断\n")
                self._append_log("-" * 50 + "\n")

                result = api_answer.auto_answer_all_knowledges(
                    course_id,
                    max_knowledges=None  # None表示完成所有知识点
                )

                # 显示结果
                self._append_log("\n" + "=" * 50 + "\n")
                self._append_log("📊 最终统计\n")
                self._append_log("=" * 50 + "\n")
                self._append_log(f"📍 知识点: {result['completed_knowledges']}/{result['total_knowledges']}\n")
                self._append_log(f"📝 题目总计: {result['total_questions']} 题\n")
                self._append_log(f"✅ 成功: {result['success']} 题\n")
                self._append_log(f"❌ 失败: {result['failed']} 题\n")
                self._append_log(f"⏭️  跳过: {result['skipped']} 题\n")
                self._append_log("=" * 50 + "\n")

                if result['completed_knowledges'] >= result['total_knowledges']:
                    self._append_log("\n🎉 恭喜！所有知识点已完成！\n")

            # 完成
            self._append_log("\n🎉 答题任务完成！\n")

            # 延迟后自动关闭对话框
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

    def _on_back_from_course_detail(self, e):
        """处理从课程详情返回的按钮点击事件"""
        print("DEBUG: 返回课程列表")
        # 切换回课程列表界面
        courses_content = self._get_courses_content()
        self.current_content.content = courses_content

    def _on_relogin_from_navigation(self, e):
        """处理从导航失败后重新登录的按钮点击事件"""
        print("🔄 用户选择重新登录")

        # 关闭对话框
        self.page.pop_dialog()

        # 返回登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_relogin_from_progress(self, e):
        """处理从进度更新失败后重新登录的按钮点击事件"""
        print("🔄 用户选择重新登录")

        # 关闭对话框
        self.page.pop_dialog()

        # 返回登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_course_card_click(self, e, course: dict):
        """处理课程卡片点击事件"""
        print(f"DEBUG: 点击课程卡片 - {course.get('courseName')}")

        # 如果已导入题库，验证题库课程ID是否与新选择的课程匹配
        if self.question_bank_data:
            from src.question_bank_importer import QuestionBankImporter

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
                new_course_id = course.get('courseID', '')
                new_course_name = course.get('courseName', '未知课程')

                print(f"DEBUG: 题库课程ID = {bank_course_id}")
                print(f"DEBUG: 新选择课程ID = {new_course_id}")

                # 如果题库课程ID与新选择的课程ID不匹配
                if bank_course_id and new_course_id and bank_course_id != new_course_id:
                    print(f"❌ 题库课程与新选择的课程不匹配")

                    # 暂存旧课程信息
                    old_course = self.current_course

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
                                        on_click=lambda e: self._on_clear_question_bank_student(e, course),
                                    ),
                                    ft.ElevatedButton(
                                        "取消选择",
                                        icon=ft.Icons.CANCEL,
                                        bgcolor=ft.Colors.GREY,
                                        color=ft.Colors.WHITE,
                                        on_click=lambda e: self._on_cancel_course_selection_student(e, old_course),
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

        # 先重置所有状态，确保不会显示旧课程的数据
        self.current_progress = None
        self.current_uncompleted = None

        # 保存当前选中的课程
        self.current_course = course

        # 切换到课程详情界面（此时会显示加载中状态）
        detail_content = self._get_course_detail_content(course)
        self.current_content.content = detail_content
        self.page.update()

        # 在后台线程中执行导航和数据获取（所有浏览器操作必须在同一线程）
        self.page.run_thread(self._perform_course_navigation_and_load)

    def _show_error_dialog(self, title: str, content: str):
        """显示错误对话框"""
        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def _on_clear_question_bank_student(self, e, new_course: dict):
        """清除题库并选择新课程（学生端）"""
        print("DEBUG: 清除题库并选择新课程")
        self.page.pop_dialog()

        # 清除题库数据
        self.question_bank_data = None

        # 先重置所有状态
        self.current_progress = None
        self.current_uncompleted = None

        # 选择新课程
        self.current_course = new_course

        # 切换到课程详情界面
        detail_content = self._get_course_detail_content(new_course)
        self.current_content.content = detail_content
        self.page.update()

        # 在后台线程中执行导航和数据获取
        self.page.run_thread(self._perform_course_navigation_and_load)

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

    def _on_cancel_course_selection_student(self, e, old_course: dict):
        """取消选择课程，保持之前的课程（学生端）"""
        print("DEBUG: 取消选择课程")
        self.page.pop_dialog()

        # 如果有旧课程，返回课程列表；如果没有，保持当前状态
        if old_course:
            # 恢复旧课程并显示课程列表
            from src.student_login import get_student_courses
            try:
                self.course_list = get_student_courses()
                course_list_content = self._get_course_list_content()
                self.current_content.content = course_list_content
                self.page.update()
            except Exception as ex:
                print(f"❌ 获取课程列表失败: {ex}")
                self._show_error_dialog("错误", f"获取课程列表失败：{str(ex)}")

    def _create_progress_card(self, course_name: str) -> ft.Card:
        """
        创建课程进度卡片

        Args:
            course_name: 课程名称

        Returns:
            ft.Card: 进度卡片组件
        """
        # 检查是否已有进度数据
        if self.current_progress:
            progress = self.current_progress
            # 生成进度条的填充字符（使用百分比）
            percentage = progress.get('progress_percentage', 0)
            filled_length = int(50 * percentage / 100)  # 50个字符的总长度

            return ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.ANALYTICS,
                                    color=ft.Colors.BLUE,
                                    size=30,
                                ),
                                title=ft.Text(
                                    "课程学习进度",
                                    weight=ft.FontWeight.BOLD,
                                    size=20,
                                ),
                                subtitle=ft.Text(
                                    f"📖 {course_name}",
                                    color=ft.Colors.GREY_600,
                                    size=14,
                                ),
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.ProgressBar(
                                            value=percentage / 100,
                                            expand=True,
                                            color=ft.Colors.GREEN,
                                            bgcolor=ft.Colors.GREY_200,
                                        ),
                                        ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                                        ft.Text(
                                            f"进度: {percentage:.1f}%",
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.BLUE_700,
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.padding.symmetric(horizontal=10),
                            ),
                            ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Icon(
                                                    ft.Icons.CHECK_CIRCLE,
                                                    color=ft.Colors.GREEN,
                                                    size=32,
                                                ),
                                                ft.Text(
                                                    str(progress.get('completed', 0)),
                                                    size=20,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=ft.Colors.GREEN,
                                                ),
                                                ft.Text(
                                                    "已完成",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                ),
                                            ],
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=5,
                                        ),
                                        expand=True,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Icon(
                                                    ft.Icons.CANCEL,
                                                    color=ft.Colors.RED,
                                                    size=32,
                                                ),
                                                ft.Text(
                                                    str(progress.get('failed', 0)),
                                                    size=20,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=ft.Colors.RED,
                                                ),
                                                ft.Text(
                                                    "做错过",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                ),
                                            ],
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=5,
                                        ),
                                        expand=True,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Icon(
                                                    ft.Icons.PENDING,
                                                    color=ft.Colors.ORANGE,
                                                    size=32,
                                                ),
                                                ft.Text(
                                                    str(progress.get('not_started', 0)),
                                                    size=20,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=ft.Colors.ORANGE,
                                                ),
                                                ft.Text(
                                                    "未开始",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                ),
                                            ],
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=5,
                                        ),
                                        expand=True,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Icon(
                                                    ft.Icons.LIST_ALT,
                                                    color=ft.Colors.BLUE,
                                                    size=32,
                                                ),
                                                ft.Text(
                                                    str(progress.get('total', 0)),
                                                    size=20,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=ft.Colors.BLUE,
                                                ),
                                                ft.Text(
                                                    "总计",
                                                    size=12,
                                                    color=ft.Colors.GREY_600,
                                                ),
                                            ],
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=5,
                                        ),
                                        expand=True,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                            ),
                        ],
                        spacing=0,
                    ),
                    padding=20,
                ),
                elevation=3,
                margin=ft.margin.all(0),
            )
        else:
            # 显示加载中状态
            return ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.ANALYTICS,
                                    color=ft.Colors.BLUE,
                                    size=30,
                                ),
                                title=ft.Text(
                                    "课程学习进度",
                                    weight=ft.FontWeight.BOLD,
                                    size=20,
                                ),
                                subtitle=ft.Text(
                                    f"📖 {course_name}",
                                    color=ft.Colors.GREY_600,
                                    size=14,
                                ),
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.Text(
                                "正在获取进度信息...",
                                color=ft.Colors.GREY_600,
                                size=14,
                            ),
                            ft.ProgressRing(stroke_width=2, width=30, height=30),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=20,
                ),
                elevation=3,
                margin=ft.margin.all(0),
            )

    def _create_knowledge_list_card(self, course: dict) -> ft.Card:
        """
        创建未完成知识点列表卡片

        Args:
            course: 课程信息字典

        Returns:
            ft.Card: 知识点列表卡片组件
        """
        # 检查是否已有知识点数据
        if self.current_uncompleted is not None:
            uncompleted_list = self.current_uncompleted

            if not uncompleted_list:
                # 所有知识点都已完成
                return ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.CHECK_CIRCLE,
                                        color=ft.Colors.GREEN,
                                        size=30,
                                    ),
                                    title=ft.Text(
                                        "未完成知识点列表",
                                        weight=ft.FontWeight.BOLD,
                                        size=20,
                                    ),
                                    subtitle=ft.Text(
                                        "🎉 太棒了！所有知识点都已完成！",
                                        color=ft.Colors.GREEN,
                                    ),
                                ),
                            ],
                            spacing=5,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=20,
                        expand=True,
                    ),
                    elevation=3,
                    margin=ft.margin.all(0),
                )

            # 检查数据格式（扁平化或嵌套）
            # 扁平化格式：每个元素包含章节和知识点信息
            # 嵌套格式：每个元素包含 chapterName 和 knowledge 列表
            is_flat_format = isinstance(uncompleted_list[0].get('knowledge'), str) if uncompleted_list else False

            knowledge_items = []
            chapter_count = 0
            knowledge_count = 0

            if is_flat_format:
                # 处理扁平化格式
                current_chapter = None
                for item in uncompleted_list:
                    # 打印完整的数据项来调试
                    print(f"DEBUG: 完整数据项 = {item}")

                    chapter_num = item.get('title', '')  # 例如："第2章"
                    chapter_name = item.get('titleContent', item.get('title', '未知章节'))  # 例如："数据通信基础"
                    knowledge_name = item.get('knowledge', '未知知识点')

                    # 组合完整的章节标题
                    full_chapter_title = f"{chapter_num} {chapter_name}" if chapter_num and chapter_num != chapter_name else chapter_name

                    # 调试输出
                    print(f"DEBUG: 章节='{full_chapter_title}', 知识点='{knowledge_name}'")

                    # 如果章节改变，添加章节标题
                    if current_chapter != full_chapter_title:
                        chapter_count += 1
                        current_chapter = full_chapter_title
                        knowledge_items.append(
                            ft.Container(
                                content=ft.Text(
                                    full_chapter_title,
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_800,
                                ),
                                padding=ft.padding.only(top=15 if chapter_count > 1 else 0, bottom=8),
                            )
                        )

                    # 添加知识点
                    knowledge_count += 1
                    knowledge_items.append(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            str(knowledge_count),
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.WHITE,
                                        ),
                                        width=24,
                                        height=24,
                                        bgcolor=ft.Colors.BLUE_400,
                                        border_radius=12,
                                        alignment=ft.Alignment.CENTER,
                                    ),
                                    ft.Text(
                                        knowledge_name,
                                        size=13,
                                        color=ft.Colors.GREY_800,
                                        expand=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            padding=ft.padding.only(left=20, bottom=8),
                        )
                    )
            else:
                # 处理嵌套格式（原始代码）
                for chapter in uncompleted_list:
                    chapter_count += 1
                    chapter_name = chapter.get('chapterName', chapter.get('title', '未知章节'))
                    knowledges = chapter.get('knowledge', [])

                    # 章节标题
                    knowledge_items.append(
                        ft.Container(
                            content=ft.Text(
                                f"📖 第{chapter_count}章 - {chapter_name}",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                            padding=ft.padding.only(top=10, bottom=5),
                        )
                    )

                    # 知识点列表
                    for idx, knowledge in enumerate(knowledges):
                        knowledge_count += 1
                        # 处理知识点的不同可能格式
                        if isinstance(knowledge, dict):
                            knowledge_name = knowledge.get('knowledgeName', knowledge.get('knowledge', '未知知识点'))
                        elif isinstance(knowledge, str):
                            knowledge_name = knowledge
                        else:
                            knowledge_name = str(knowledge)

                        knowledge_items.append(
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Text(
                                                str(knowledge_count),
                                                size=12,
                                                weight=ft.FontWeight.BOLD,
                                                color=ft.Colors.WHITE,
                                            ),
                                            width=24,
                                            height=24,
                                            bgcolor=ft.Colors.BLUE_400,
                                            border_radius=12,
                                            alignment=ft.Alignment.CENTER,
                                        ),
                                        ft.Text(
                                            knowledge_name,
                                            size=13,
                                            color=ft.Colors.GREY_800,
                                            expand=True,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                padding=ft.padding.only(left=20, bottom=8),
                            )
                        )

            return ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.LIST_ALT,
                                    color=ft.Colors.ORANGE,
                                    size=30,
                                ),
                                title=ft.Text(
                                    "未完成知识点列表",
                                    weight=ft.FontWeight.BOLD,
                                    size=20,
                                ),
                                subtitle=ft.Text(
                                    f"共 {chapter_count} 个章节，{knowledge_count} 个未完成知识点"
                                ),
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.Container(
                                content=ft.Column(
                                    knowledge_items,
                                    spacing=0,
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                expand=True,
                                border=ft.border.all(1, ft.Colors.GREY_300),
                                border_radius=8,
                                padding=10,
                            ),
                        ],
                        spacing=5,
                    ),
                    padding=20,
                    expand=True,
                ),
                elevation=3,
                margin=ft.margin.all(0),
            )
        else:
            # 显示加载中状态
            return ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.LIST_ALT,
                                    color=ft.Colors.ORANGE,
                                    size=30,
                                ),
                                title=ft.Text(
                                    "未完成知识点列表",
                                    weight=ft.FontWeight.BOLD,
                                    size=20,
                                ),
                                subtitle=ft.Text(
                                    f"共 {len(course.get('uncompleted_knowledges', []))} 个未完成知识点"
                                ),
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.Text(
                                "正在加载知识点列表...",
                                color=ft.Colors.GREY_600,
                                size=14,
                            ),
                            ft.ProgressRing(stroke_width=2, width=30, height=30),
                        ],
                        spacing=5,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=20,
                    expand=True,
                ),
                elevation=3,
                margin=ft.margin.all(0),
            )
