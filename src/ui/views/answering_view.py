"""
ZX Answering Assistant - 评估答题视图模块

This module contains the UI components for the answering page.
"""

import flet as ft
from src.student_login import get_student_access_token, get_student_courses, get_uncompleted_chapters


class AnsweringView:
    """评估答题页面视图"""

    def __init__(self, page: ft.Page):
        """
        初始化评估答题视图

        Args:
            page (ft.Page): Flet页面对象
        """
        self.page = page
        self.current_content = None  # 保存当前内容容器的引用
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框
        self.access_token = None  # 存储获取的access_token
        self.progress_dialog = None  # 登录进度对话框
        self.course_list = []  # 存储课程列表
        self.username = ""  # 存储登录的用户名

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
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
                                    subtitle=ft.Text("登录学生端平台获取access_token"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.BOOK, color=ft.Colors.GREEN),
                                    title=ft.Text("选择课程", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("查看课程列表和完成情况"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.ORANGE),
                                    title=ft.Text("开始答题", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用题库自动完成课程答题"),
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
        # 初始化输入框
        self.username_field = ft.TextField(
            label="账号",
            hint_text="请输入学生端账号",
            width=400,
            icon=ft.Icons.PERSON,
            autofocus=True,
        )

        self.password_field = ft.TextField(
            label="密码",
            hint_text="请输入学生端密码",
            width=400,
            password=True,
            can_reveal_password=True,
            icon=ft.Icons.LOCK,
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

                # 创建课程卡片
                card = ft.Card(
                    content=ft.Container(
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
                                    ],
                                    spacing=20,
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=20,
                        width=700,
                    ),
                    elevation=3,
                    margin=ft.margin.only(bottom=15),
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
