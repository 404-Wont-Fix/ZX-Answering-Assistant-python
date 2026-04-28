"""
ZX Answering Assistant - 评估答题视图模块

This module contains the UI components for the answering page.
"""

import flet as ft
import json
import sys
from pathlib import Path
from io import StringIO
from src.auth.student import (
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
from src.core.config import get_settings_manager


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
        self.answer_dialog = None  # 答题进度对话框
        self.progress_percent_text = None  # 进度百分比文本控件
        self.progress_info_text = None  # 进度信息文本控件（显示：10/16）
        self.progress_bar = None  # 进度条控件
        self.auto_answer_instance = None  # 自动答题实例
        self.should_stop_answering = False  # 停止答题标志
        self.answer_progress = {"current": 0, "total": 0}  # 答题进度信息

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

        # 创建密码输入框（去除边框，由外部容器提供）
        self.password_field = ft.TextField(
            label="密码",
            hint_text="请输入学生端密码",
            value=saved_password or "",
            expand=True,
            password=True,
            border=ft.InputBorder.NONE,
            prefix_icon=ft.Icons.LOCK,
            content_padding=ft.padding.only(left=12, top=12, bottom=12, right=0),
        )

        # 填充密码后缀图标按钮
        fill_password_icon = ft.IconButton(
            icon=ft.Icons.KEY,
            icon_size=20,
            tooltip="使用账号后六位作为密码",
            on_click=lambda e: self._on_fill_password_click(e),
            icon_color=ft.Colors.GREY_600,
            width=40,
            height=40,
            padding=5,
        )

        # 显示/隐藏密码按钮
        reveal_password_icon = ft.IconButton(
            icon=ft.Icons.VISIBILITY,
            icon_size=20,
            tooltip="显示/隐藏密码",
            on_click=lambda e: self._toggle_password_visibility(e),
            icon_color=ft.Colors.GREY_600,
            width=40,
            height=40,
            padding=5,
        )

        # 密码输入行（使用 Container 模拟 TextField 外观）
        password_row = ft.Container(
            content=ft.Row(
                [
                    self.password_field,
                    fill_password_icon,
                    reveal_password_icon,
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            width=400,
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=4,
            padding=ft.padding.only(left=0, top=0, right=0, bottom=0),
            # bgcolor=ft.Colors.WHITE,
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
                                password_row,
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

    def _on_fill_password_click(self, e):
        """处理填充密码按钮点击事件 - 将账号后六位填充到密码框"""
        username = self.username_field.value
        if username and len(username) >= 6:
            last_six = username[-6:]
            self.password_field.value = last_six
            self.page.update()
            print(f"DEBUG: 已将账号后六位 '{last_six}' 填充到密码框")
        else:
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("账号长度不足6位，无法提取后六位"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)

    def _toggle_password_visibility(self, e):
        """处理显示/隐藏密码按钮点击事件"""
        self.password_field.password = not self.password_field.password
        if self.password_field.password:
            self.password_field.prefix_icon = ft.Icons.LOCK
        else:
            self.password_field.prefix_icon = ft.Icons.LOCK_OPEN
        self.page.update()

    def _on_start_answer_click(self, e):
        """处理开始答题按钮点击事件 - 切换到登录界面"""
        print("DEBUG: 切换到登录界面")  # 调试信息

        # 使用动画切换到登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _cleanup_user_state(self):
        """
        完全清理用户状态（用于切换账号或重新登录）

        清理内容包括：
        - access_token
        - 浏览器上下文和 cookies
        - 内存中的课程数据
        - 题库数据
        """
        print("🧹 正在清理用户状态...")

        try:
            # 1. 清理 access_token
            if self.access_token:
                print("  - 清理 access_token")
                clear_access_token()
                self.access_token = None

            # 2. 清理浏览器上下文
            print("  - 清理浏览器上下文")
            try:
                cleanup_browser()
            except Exception as e:
                print(f"  ⚠️ 清理浏览器失败: {e}")

            # 3. 清理内存中的状态
            print("  - 清理内存状态")
            self.username = ""
            self.course_list = []
            self.current_course = None
            self.current_progress = None
            self.current_uncompleted = None

            # 4. 清理题库数据
            if self.question_bank_data:
                print("  - 清理题库数据")
                self.question_bank_data = None

            print("✅ 用户状态清理完成")

        except Exception as e:
            print(f"❌ 清理用户状态时出错: {e}")
            import traceback
            traceback.print_exc()

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

                # 课程统计信息（带刷新按钮）
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
                                ft.Container(expand=True),  # Spacer
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH,
                                    icon_color=ft.Colors.BLUE,
                                    tooltip="刷新课程列表",
                                    on_click=lambda e: self._on_refresh_courses(e),
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

        # 清理所有用户状态（返回登录界面时完全清理）
        self._cleanup_user_state()

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
        """处理使用JSON题库按钮点击事件（使用新的 FilePicker API）"""
        print("DEBUG: 使用JSON题库")

        # 使用 page.run_task() 来运行异步操作
        async def pick_file_async():
            # 使用新的 FilePicker API（async/await 模式）
            file_picker = ft.FilePicker()
            files = await file_picker.pick_files(
                allowed_extensions=["json"],
                dialog_title="选择JSON题库文件"
            )

            # 处理选择的文件
            if files and len(files) > 0:
                file_path = files[0].path
                print(f"DEBUG: 选择的文件 = {file_path}")
                self._process_selected_json_file(file_path)
            else:
                print("DEBUG: 用户取消了文件选择")

        # 使用 Flet 的 run_task 方法运行异步函数
        self.page.run_task(pick_file_async)

    def _process_selected_json_file(self, file_path: str):
        """
        处理选中的JSON文件

        Args:
            file_path: JSON文件路径
        """
        from pathlib import Path
        from src.extraction.importer import QuestionBankImporter

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
        创建答题进度对话框（简洁版）

        Args:
            title: 对话框标题

        Returns:
            ft.AlertDialog: 进度对话框
        """
        # 进度百分比文本
        self.progress_percent_text = ft.Text(
            "0%",
            size=32,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE,
        )

        # 进度信息文本（显示：10/16）
        self.progress_info_text = ft.Text(
            "准备开始...",
            size=16,
            color=ft.Colors.GREY_700,
        )

        # 进度条
        self.progress_bar = ft.ProgressBar(
            width=400,
            value=0.0,
            color=ft.Colors.BLUE,
            bgcolor=ft.Colors.BLUE_GREY_100,
            bar_height=10,
        )

        # 创建对话框
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.AUTO_GRAPH, color=ft.Colors.BLUE, size=28),
                    ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        # 进度百分比
                        ft.Container(
                            content=self.progress_percent_text,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

                        # 进度条
                        self.progress_bar,
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

                        # 进度信息（如：10/16）
                        self.progress_info_text,
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                width=400,
                padding=ft.padding.symmetric(horizontal=20, vertical=25),
            ),
            actions=[
                ft.ElevatedButton(
                    "🛑 停止答题",
                    icon=ft.Icons.STOP,
                    bgcolor=ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=30, vertical=12),
                    ),
                    on_click=self._on_stop_answering,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        return dialog

    def _update_progress(self, message: str, current: int = None, total: int = None):
        """
        更新答题进度（使用 page.run_task 确保UI实时更新）

        Args:
            message: 进度消息
            current: 当前进度（可选）
            total: 总数（可选）
        """
        print(f"[进度更新] {message} - 当前: {current}, 总数: {total}")

        # 检查控件是否已初始化
        if not all([self.progress_info_text, self.progress_bar, self.progress_percent_text]):
            print(f"⚠️ 进度控件未初始化")
            return

        # 检查page是否可用
        if not self.page:
            print(f"⚠️ page 对象不可用")
            return

        # 在主线程中更新UI（使用 run_task 确保实时更新）
        async def update_ui():
            try:
                # 构建进度信息文本
                if current is not None and total is not None and total > 0:
                    progress_info = f"{current}/{total}"
                else:
                    progress_info = "正在处理..."

                # 更新进度信息文本
                self.progress_info_text.value = progress_info

                # 更新进度条和百分比
                if current is not None and total is not None and total > 0:
                    # 确定进度：显示具体百分比
                    progress_value = min(current / total, 1.0)
                    self.progress_bar.value = progress_value
                    self.progress_percent_text.value = f"{int(progress_value * 100)}%"
                    self.answer_progress = {"current": current, "total": total}
                    print(f"[进度UI] 进度条更新为 {progress_value:.2%} ({current}/{total})")
                else:
                    # 不确定进度：显示动画
                    self.progress_bar.value = None
                    self.progress_percent_text.value = "⏳"
                    print(f"[进度UI] 不确定进度模式")

                # 刷新UI
                self.page.update()
                print(f"[进度UI] UI刷新成功")

            except Exception as e:
                print(f"❌ UI更新异常: {e}")
                import traceback
                traceback.print_exc()

        # 使用 run_task 调度UI更新（关键！）
        self.page.run_task(update_ui)

    def _on_stop_answering(self, e):
        """处理停止答题按钮点击事件"""
        print("🛑 用户请求停止答题")
        self.should_stop_answering = True

        # 如果有自动答题实例，调用其停止方法
        if self.auto_answer_instance and hasattr(self.auto_answer_instance, 'request_stop'):
            self.auto_answer_instance.request_stop()

        # 关闭对话框（使用 pop_dialog 而不是 close）
        if self.answer_dialog:
            self.page.pop_dialog()
            self.answer_dialog = None

        self.is_answering = False

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

        # 使用 Flet 的 run_thread 来确保 UI 更新的线程安全
        self.page.run_thread(lambda: self._run_answering_task(mode, course_id))

    def _run_answering_task(self, mode: str, course_id: str):
        """
        在后台线程中运行答题任务

        Args:
            mode: 答题模式
            course_id: 课程ID
        """
        def _log(msg):
            """内部日志函数，只打印到控制台"""
            print(msg.strip())

        try:
            mode_name = "兼容模式" if mode == "compatibility" else "暴力模式"
            _log(f"🚀 开始{mode_name}答题")
            _log(f"📚 课程ID: {course_id}")

            if mode == "compatibility":
                # ========== 兼容模式：使用浏览器自动化 ==========
                _log("📌 模式：浏览器自动化（兼容模式）")
                self._update_progress("正在初始化浏览器...")

                from src.auth.student import get_browser_page, get_cached_access_token, get_uncompleted_chapters
                from src.answering.browser_answer import AutoAnswer

                # 获取浏览器实例
                browser_page = get_browser_page()
                if not browser_page:
                    _log("❌ 无法获取浏览器实例")
                    self._update_progress("❌ 无法获取浏览器实例")
                    return

                _log("✅ 浏览器实例获取成功")
                self._update_progress("正在获取未完成知识点...")

                # 获取未完成知识点列表
                access_token = get_cached_access_token()
                if not access_token:
                    _log("❌ 无法获取 access_token")
                    self._update_progress("❌ 无法获取 access_token")
                    return

                uncompleted_list = get_uncompleted_chapters(access_token, course_id, delay_ms=0, max_retries=1)
                total_knowledges = len(uncompleted_list) if uncompleted_list else 0
                _log(f"✅ 获取到 {total_knowledges} 个未完成知识点")

                self._update_progress("正在加载题库...")

                # 创建自动做题器（传入日志回调）
                page = browser_page[1]  # 使用page对象
                auto_answer = AutoAnswer(page, log_callback=_log)
                self.auto_answer_instance = auto_answer

                # 加载题库
                _log("📖 正在加载题库...")
                auto_answer.load_question_bank(self.question_bank_data)
                _log("✅ 题库加载成功")
                self._update_progress("准备开始答题...")

                # 答题循环
                knowledge_count = 0
                total_success = 0
                total_failed = 0

                while True:
                    # 检查停止信号
                    if self.should_stop_answering:
                        _log("⚠️ 检测到停止信号，答题已终止")
                        break

                    # 第一个知识点：检索并开始做题
                    # 之后的知识点：网站自动跳转后继续做题
                    if knowledge_count == 0:
                        _log("🔍 检索第一个可作答的知识点...")
                        result = auto_answer.run_auto_answer(max_questions=5)
                    else:
                        _log("⏳ 网站已自动跳转，继续做题...")
                        import time
                        time.sleep(2)  # 等待跳转完成
                        result = auto_answer.continue_auto_answer(max_questions=5)

                    # 统计（先增加计数）
                    knowledge_count += 1
                    total_success += result['success']
                    total_failed += result['failed']

                    # 显示本次统计
                    _log(f"📊 知识点完成统计: 总题数={result['total']}, 成功={result['success']}, 失败={result['failed']}, 跳过={result['skipped']}")

                    # 检查用户是否请求停止
                    if result.get('stopped', False) or self.should_stop_answering:
                        _log("⚠️ 用户请求停止做题")
                        break

                    # 更新进度（在完成当前知识点后更新）
                    if total_knowledges > 0:
                        _log(f"📍 已完成 {knowledge_count}/{total_knowledges} 个知识点")
                        self._update_progress(
                            f"已完成 {knowledge_count}/{total_knowledges} 个知识点，成功 {total_success} 题",
                            knowledge_count,
                            total_knowledges
                        )
                    else:
                        _log(f"📍 已完成 {knowledge_count} 个知识点")
                        self._update_progress(
                            f"已完成 {knowledge_count} 个知识点，成功 {total_success} 题",
                            knowledge_count,
                            None
                        )

                    # 检查是否还有更多知识点
                    import time
                    time.sleep(1)

                    try:
                        has_next = auto_answer.has_next_knowledge()
                        if has_next:
                            # 找到了，可以继续
                            _log("✅ 检测到下一个知识点，继续...")
                            continue
                        else:
                            # 没找到，说明所有知识点都完成了
                            _log("✅ 所有知识点已完成！")
                            break
                    except Exception as e:
                        _log(f"❌ 检查失败: {str(e)}")
                        _log("💡 可能所有知识点都已完成")
                        break

                # 最终统计
                _log("📊 最终统计")
                _log(f"📍 完成知识点: {knowledge_count} 个")
                _log(f"✅ 成功作答: {total_success} 题")
                _log(f"❌ 失败: {total_failed} 题")

                if total_knowledges > 0:
                    self._update_progress(
                        f"✅ 完成！已处理 {knowledge_count}/{total_knowledges} 个知识点",
                        knowledge_count,
                        total_knowledges
                    )
                else:
                    self._update_progress(
                        f"✅ 完成！已处理 {knowledge_count} 个知识点",
                        knowledge_count,
                        knowledge_count
                    )

            elif mode == "brute":
                # ========== 暴力模式：使用API直接请求 ==========
                _log("📌 模式：API直接请求（暴力模式）")
                self._update_progress("正在获取 access_token...")

                from src.auth.student import get_cached_access_token, get_uncompleted_chapters
                from src.answering.api_answer import APIAutoAnswer

                # 获取access_token（使用缓存管理）
                access_token = get_cached_access_token()

                if not access_token:
                    _log("⚠️ 自动获取access_token失败")
                    self._update_progress("❌ 无法获取 access_token")
                    return

                _log("✅ access_token获取成功")
                self._update_progress("正在获取未完成知识点...")

                # 获取未完成知识点数量
                try:
                    uncompleted_list = get_uncompleted_chapters(access_token, course_id, delay_ms=0, max_retries=1)
                    total_knowledges = len(uncompleted_list) if uncompleted_list else 0
                    _log(f"✅ 获取到 {total_knowledges} 个未完成知识点")
                except Exception as e:
                    _log(f"⚠️ 获取知识点列表失败: {e}")
                    total_knowledges = 0

                self._update_progress("正在加载题库...")

                # 创建进度回调函数
                def _progress_update(current: int, total: int, message: str = ""):
                    """进度回调函数"""
                    msg = message or f"已完成 {current}/{total} 个知识点"
                    self._update_progress(msg, current, total)

                # 创建API自动做题器（传入日志回调和进度回调）
                api_answer = APIAutoAnswer(
                    access_token,
                    log_callback=_log,
                    progress_callback=_progress_update
                )
                self.auto_answer_instance = api_answer

                # 加载题库
                _log("📖 正在加载题库...")
                api_answer.load_question_bank(self.question_bank_data)
                _log("✅ 题库加载成功")

                # 执行自动做题（进度条会在 auto_answer_all_knowledges 内部自动更新）
                _log("🚀 开始自动完成所有知识点")

                result = api_answer.auto_answer_all_knowledges(
                    course_id,
                    max_knowledges=None  # None表示完成所有知识点
                )

                # 显示结果
                _log("📊 最终统计")
                _log(f"📍 知识点: {result['completed_knowledges']}/{result['total_knowledges']}")
                _log(f"📝 题目总计: {result['total_questions']} 题")
                _log(f"✅ 成功: {result['success']} 题")
                _log(f"❌ 失败: {result['failed']} 题")
                _log(f"⏭️  跳过: {result['skipped']} 题")

                # 显示最终完成状态
                completed = result['completed_knowledges']
                total = result['total_knowledges']
                self._update_progress(
                    f"✅ 完成！已处理 {completed}/{total} 个知识点，成功 {result['success']} 题",
                    completed,
                    total
                )

                if completed >= total:
                    _log("🎉 恭喜！所有知识点已完成！")

            # 完成
            _log("🎉 答题任务完成！")

            # 延迟后自动关闭对话框
            import time
            time.sleep(2)
            if self.answer_dialog:
                self.page.pop_dialog()
                self.answer_dialog = None

        except KeyboardInterrupt:
            _log("⚠️ 用户中断答题")
        except Exception as e:
            _log(f"❌ 答题过程出错: {str(e)}")
            import traceback
            _log(f"📋 详细错误:\n{traceback.format_exc()}")
        finally:
            self.is_answering = False
            self.should_stop_answering = False
            self.auto_answer_instance = None

    def _on_back_from_course_detail(self, e):
        """处理从课程详情返回的按钮点击事件"""
        print("DEBUG: 返回课程列表")

        # 立即切换回课程列表界面（快速返回，不刷新数据）
        courses_content = self._get_courses_content()
        self.current_content.content = courses_content
        self.page.update()

        # 可选：在后台静默刷新课程数据（不阻塞UI，不显示进度）
        # 如果需要看到刷新进度，可以点击"刷新课程列表"按钮
        print("💡 提示：如需刷新最新数据，请点击刷新按钮")

    def _on_refresh_courses(self, e):
        """手动刷新课程列表（用户主动触发）"""
        print("🔄 用户请求刷新课程列表")

        # 显示刷新提示
        self.page.snack_bar = ft.SnackBar(
            ft.Text("正在刷新课程数据...", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE,
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()

        # 在后台线程中刷新
        def refresh_in_background():
            """后台刷新课程数据"""
            try:
                from src.auth.student import get_cached_access_token, get_student_courses
                access_token = get_cached_access_token()

                if not access_token:
                    def show_error():
                        self.page.snack_bar = ft.SnackBar(
                            ft.Text("⚠️ 无法获取 access_token", color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.RED,
                            duration=3000,
                        )
                        self.page.snack_bar.open = True
                        self.page.update()

                    async def async_error():
                        show_error()
                    self.page.run_task(async_error)
                    return

                # 获取最新的课程列表
                courses = get_student_courses(access_token)

                if not courses or len(courses) == 0:
                    def show_no_courses():
                        self.page.snack_bar = ft.SnackBar(
                            ft.Text("⚠️ 未获取到课程列表", color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.ORANGE,
                            duration=3000,
                        )
                        self.page.snack_bar.open = True
                        self.page.update()

                    async def async_no_courses():
                        show_no_courses()
                    self.page.run_task(async_no_courses)
                    return

                self.course_list = courses
                print(f"✅ 成功刷新 {len(courses)} 门课程")

                # 为每门课程获取未完成的知识点
                for idx, course in enumerate(courses, 1):
                    course_id = course.get('courseID')
                    if course_id:
                        try:
                            print(f"[{idx}/{len(courses)}] 正在获取 {course.get('courseName')} 的未完成知识点...")
                            uncompleted = get_uncompleted_chapters(
                                access_token,
                                course_id,
                                delay_ms=0,
                                max_retries=1
                            )
                            course['uncompleted_knowledges'] = uncompleted if uncompleted else []
                            print(f"  ✅ {course.get('courseName')}: {len(uncompleted) if uncompleted else 0} 个未完成知识点")
                        except Exception as ex:
                            print(f"  ❌ 获取课程 {course.get('courseName')} 未完成知识点失败: {ex}")
                            course['uncompleted_knowledges'] = []

                # 更新UI
                def update_ui_success():
                    new_courses_content = self._get_courses_content()
                    self.current_content.content = new_courses_content
                    self.page.update()

                    self.page.snack_bar = ft.SnackBar(
                        ft.Text(f"✅ 已刷新 {len(courses)} 门课程数据", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN,
                        duration=2000,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()

                async def async_update():
                    update_ui_success()

                self.page.run_task(async_update)

            except Exception as ex:
                print(f"❌ 刷新课程列表失败: {ex}")
                import traceback
                traceback.print_exc()

                def show_error():
                    self.page.snack_bar = ft.SnackBar(
                        ft.Text(f"❌ 刷新失败: {str(ex)}", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.RED,
                        duration=3000,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()

                async def async_error():
                    show_error()

                self.page.run_task(async_error)

        # 使用后台线程执行刷新
        import threading
        threading.Thread(target=refresh_in_background, daemon=True).start()

    def _on_relogin_from_navigation(self, e):
        """处理从导航失败后重新登录的按钮点击事件"""
        print("🔄 用户选择重新登录")

        # 关闭对话框
        self.page.pop_dialog()

        # 清理所有用户状态
        self._cleanup_user_state()

        # 返回登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_relogin_from_progress(self, e):
        """处理从进度更新失败后重新登录的按钮点击事件"""
        print("🔄 用户选择重新登录")

        # 关闭对话框
        self.page.pop_dialog()

        # 清理所有用户状态
        self._cleanup_user_state()

        # 返回登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_course_card_click(self, e, course: dict):
        """处理课程卡片点击事件"""
        print(f"DEBUG: 点击课程卡片 - {course.get('courseName')}")

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
            from src.auth.student import get_student_courses
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
