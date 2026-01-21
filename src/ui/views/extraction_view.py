"""
ZX Answering Assistant - 答案提取视图模块

This module contains the UI components for the answer extraction page.
"""

import flet as ft
import threading
import asyncio
from typing import Optional, List, Dict
from src.extract import Extractor


class ExtractionView:
    """答案提取页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化答案提取视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app  # 保存MainApp引用
        self.current_content = None  # 保存当前内容容器的引用
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框

        # 数据相关
        self.extractor = None  # Extractor实例
        self.access_token = None  # 教师端access_token
        self.class_list = []  # 班级列表
        self.grades = []  # 年级列表
        self.selected_grade = None  # 选中的年级
        self.filtered_classes = []  # 过滤后的班级列表
        self.selected_class = None  # 选中的班级
        self.course_list = []  # 课程列表
        self.selected_course = None  # 选中的课程

        # UI组件引用
        self.grade_list_view = None  # 年级列表
        self.class_list_view = None  # 班级列表
        self.course_list_view = None  # 课程列表
        self.progress_dialog = None  # 加载对话框

        # 线程同步
        self.login_event = threading.Event()
        self.course_load_event = threading.Event()
        self.login_success = False
        self.login_error = None
        self.course_load_success = False
        self.course_load_error = None

    def get_content(self) -> ft.Column:
        """
        获取答案提取页面的内容

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
                    "答案提取",
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
                                    leading=ft.Icon(ft.Icons.PERSON, color=ft.Colors.PURPLE),
                                    title=ft.Text("教师端登录", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用教师账号登录管理平台"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.GROUPS, color=ft.Colors.RED),
                                    title=ft.Text("选择班级", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("选择要提取答案的班级"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.DOWNLOAD, color=ft.Colors.CYAN),
                                    title=ft.Text("提取答案", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("从课程中提取题目和答案"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.SAVE, color=ft.Colors.AMBER),
                                    title=ft.Text("导出数据", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("将提取的答案导出为JSON文件"),
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
                    "提取答案",
                    icon=ft.Icons.DOWNLOAD,
                    bgcolor=ft.Colors.PURPLE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                        animation_duration=200,
                    ),
                    on_click=lambda e: self._on_extract_click(e),
                    animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _on_extract_click(self, e):
        """处理提取答案按钮点击事件 - 切换到登录界面"""
        print("DEBUG: 切换到教师端登录界面")  # 调试信息

        # 使用动画切换到登录界面
        login_content = self._get_teacher_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _get_teacher_login_content(self) -> ft.Column:
        """
        获取教师端登录界面内容

        Returns:
            ft.Column: 登录界面组件
        """
        # 初始化输入框
        self.username_field = ft.TextField(
            label="教师账号",
            hint_text="请输入教师端账号",
            width=400,
            icon=ft.Icons.PERSON,
            autofocus=True,
        )

        self.password_field = ft.TextField(
            label="密码",
            hint_text="请输入教师端密码",
            width=400,
            password=True,
            can_reveal_password=True,
            icon=ft.Icons.LOCK,
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
                                    ft.Icons.PERSON,
                                    size=64,
                                    color=ft.Colors.PURPLE_400,
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
                                            bgcolor=ft.Colors.PURPLE,
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

    def _on_back_click(self, e):
        """处理返回按钮点击事件 - 返回主界面"""
        print("DEBUG: 返回主界面")  # 调试信息

        # 切换回主界面
        main_content = self._get_main_content()
        self.current_content.content = main_content
        self.page.update()

    def _on_login_click(self, e):
        """处理登录按钮点击事件"""
        username = self.username_field.value.strip()
        password = self.password_field.value.strip()

        if not username or not password:
            dialog = ft.AlertDialog(
                title=ft.Text("错误"),
                content=ft.Text("请输入用户名和密码"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 显示加载对话框
        self.progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("登录中"),
            content=ft.Column(
                [
                    ft.ProgressRing(stroke_width=4),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text("正在登录教师端，请稍候...", size=14),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        self.page.show_dialog(self.progress_dialog)

        # 重置状态
        self.login_success = False
        self.login_error = None
        self.login_event.clear()

        # 在后台线程中执行登录
        def login_task():
            try:
                self.extractor = Extractor()
                success = self.extractor.login(username, password)

                if success:
                    self.access_token = self.extractor.access_token
                    # 获取班级列表
                    self.class_list = self.extractor.get_class_list()
                    if self.class_list:
                        # 提取年级列表
                        self.grades = sorted(
                            set(cls.get("grade", "") for cls in self.class_list),
                            reverse=True
                        )
                        self.login_success = True
                        self.login_error = None
                    else:
                        self.login_success = False
                        self.login_error = "获取班级列表失败"
                else:
                    self.login_success = False
                    self.login_error = "用户名或密码错误"
            except Exception as ex:
                self.login_success = False
                self.login_error = str(ex)
            finally:
                # 标记完成
                self.login_event.set()

        # 启动后台线程
        threading.Thread(target=login_task, daemon=True).start()

        # 在主线程中等待并更新UI（使用定时器）
        async def check_login():
            while not self.login_event.is_set():
                # 等待100ms后再次检查
                await asyncio.sleep(0.1)

            # 关闭加载对话框
            self.progress_dialog.open = False
            self.page.update()

            if self.login_success and not self.login_error:
                # 登录成功，切换界面
                selection_content = self._get_class_selection_content()
                self.current_content.content = selection_content
                self.page.update()
            else:
                # 登录失败，显示错误
                dialog = ft.AlertDialog(
                    title=ft.Text("错误"),
                    content=ft.Text(self.login_error or "未知错误"),
                    actions=[
                        ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(dialog)

        # 开始检查
        self.page.run_task(check_login)

    def _get_class_selection_content(self) -> ft.Column:
        """
        获取班级选择界面内容（左右分栏）

        Returns:
            ft.Column: 班级选择界面组件
        """
        # 创建年级列表
        grade_cards = []
        for i, grade in enumerate(self.grades):
            grade_card = ft.GestureDetector(
                content=ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"{grade}级",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.PURPLE_700,
                                ),
                                ft.Text(
                                    f"{len([c for c in self.class_list if c.get('grade') == grade])} 个班级",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=15,
                        alignment=ft.Alignment.CENTER,
                    ),
                    elevation=2,
                    bgcolor=ft.Colors.PURPLE_50 if i == 0 else None,
                ),
                on_tap=lambda _, g=grade: self._on_grade_click(g),
            )
            grade_cards.append(grade_card)

        self.grade_list_view = ft.Column(
            controls=grade_cards,
            spacing=10,
        )

        # 初始班级列表为空
        self.class_list_view = ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SCHOOL, size=48, color=ft.Colors.GREY_400),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            ft.Text("请先选择年级", size=16, color=ft.Colors.GREY_600),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=30,
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                )
            ],
            expand=True,
        )

        # 左右分栏布局
        split_view = ft.Row(
            [
                # 左侧：年级列表
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "选择年级",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            self.grade_list_view,
                        ],
                        spacing=0,
                    ),
                    width=300,
                    bgcolor=ft.Colors.GREY_50,
                    padding=20,
                    border=ft.border.only(right=ft.BorderSide(2, ft.Colors.GREY_200)),
                ),
                # 右侧：班级列表
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "选择班级",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            self.class_list_view,
                        ],
                        spacing=0,
                    ),
                    expand=True,
                    padding=20,
                ),
            ],
            expand=True,
        )

        return ft.Column(
            [
                # 顶部返回按钮
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "返回",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: self._on_back_to_login_click(e),
                        ),
                    ],
                ),
                split_view,
            ],
            expand=True,
            spacing=0,
        )

    def _on_grade_click(self, grade: str):
        """处理年级点击事件"""
        self.selected_grade = grade
        print(f"DEBUG: 选择年级 {grade}")  # 调试信息

        # 过滤班级列表
        self.filtered_classes = [
            cls for cls in self.class_list
            if cls.get("grade") == grade
        ]

        # 创建班级卡片列表
        class_cards = []
        for cls in self.filtered_classes:
            class_card = ft.GestureDetector(
                content=ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.CLASS_,
                                        color=ft.Colors.BLUE_600,
                                    ),
                                    title=ft.Text(
                                        cls.get("className", ""),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    subtitle=ft.Text(
                                        f"ClassID: {cls.get('id', '')[:16]}...",
                                        size=12,
                                    ),
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=10,
                    ),
                    elevation=3,
                ),
                on_tap=lambda _, c=cls: self._on_class_click(c),
            )
            class_cards.append(class_card)

        # 使用 ResponsiveRow 实现卡片网格布局
        self.class_list_view = ft.ResponsiveRow(
            controls=class_cards,
            spacing=10,
            run_spacing=10,
        )

        # 重新渲染整个界面
        selection_content = self._get_class_selection_content_with_grades()
        self.current_content.content = selection_content
        self.page.update()

    def _get_class_selection_content_with_grades(self) -> ft.Column:
        """
        获取班级选择界面内容（已选择年级）

        Returns:
            ft.Column: 班级选择界面组件
        """
        # 重新创建年级列表
        grade_cards = []
        for i, grade in enumerate(self.grades):
            grade_card = ft.GestureDetector(
                content=ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"{grade}级",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.PURPLE_700 if grade == self.selected_grade else ft.Colors.BLUE_GREY_700,
                                ),
                                ft.Text(
                                    f"{len([c for c in self.class_list if c.get('grade') == grade])} 个班级",
                                    size=12,
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=15,
                        alignment=ft.Alignment.CENTER,
                    ),
                    elevation=2,
                    bgcolor=ft.Colors.PURPLE_100 if grade == self.selected_grade else ft.Colors.PURPLE_50,
                ),
                on_tap=lambda _, g=grade: self._on_grade_click(g),
            )
            grade_cards.append(grade_card)

        grade_list_view = ft.Column(
            controls=grade_cards,
            spacing=10,
        )

        # 左右分栏布局
        split_view = ft.Row(
            [
                # 左侧：年级列表
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "选择年级",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            grade_list_view,
                        ],
                        spacing=0,
                    ),
                    width=300,
                    bgcolor=ft.Colors.GREY_50,
                    padding=20,
                    border=ft.border.only(right=ft.BorderSide(2, ft.Colors.GREY_200)),
                ),
                # 右侧：班级列表
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"选择班级 ({self.selected_grade}级)",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                            self.class_list_view,
                        ],
                        spacing=0,
                    ),
                    expand=True,
                    padding=20,
                ),
            ],
            expand=True,
        )

        return ft.Column(
            [
                # 顶部返回按钮
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "返回",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: self._on_back_to_login_click(e),
                        ),
                    ],
                ),
                split_view,
            ],
            expand=True,
            spacing=0,
        )

    def _on_class_click(self, class_info: Dict):
        """处理班级点击事件"""
        self.selected_class = class_info
        print(f"DEBUG: 选择班级 {class_info.get('className')}")  # 调试信息

        # 显示加载对话框
        self.progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("加载中"),
            content=ft.Column(
                [
                    ft.ProgressRing(stroke_width=4),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text("正在获取课程列表，请稍候...", size=14),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
        )
        self.page.show_dialog(self.progress_dialog)

        # 重置状态
        self.course_load_success = False
        self.course_load_error = None
        self.course_load_event.clear()

        # 在后台线程中获取课程列表
        def load_courses_task():
            try:
                class_id = class_info.get("id")
                self.course_list = self.extractor.get_course_list(class_id)

                if self.course_list:
                    self.course_load_success = True
                    self.course_load_error = None
                else:
                    self.course_load_success = False
                    self.course_load_error = "获取课程列表失败"
            except Exception as ex:
                self.course_load_success = False
                self.course_load_error = str(ex)
            finally:
                # 标记完成
                self.course_load_event.set()

        # 启动后台线程
        threading.Thread(target=load_courses_task, daemon=True).start()

        # 在主线程中等待并更新UI（使用定时器）
        async def check_courses():
            while not self.course_load_event.is_set():
                # 等待100ms后再次检查
                await asyncio.sleep(0.1)

            # 关闭加载对话框
            self.progress_dialog.open = False
            self.page.update()

            if self.course_load_success and not self.course_load_error:
                # 成功，切换到课程界面
                course_content = self._get_course_selection_content()
                self.current_content.content = course_content
                self.page.update()
            else:
                # 失败，显示错误
                dialog = ft.AlertDialog(
                    title=ft.Text("错误"),
                    content=ft.Text(self.course_load_error or "未知错误"),
                    actions=[
                        ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                    ],
                )
                self.page.show_dialog(dialog)

        # 开始检查
        self.page.run_task(check_courses)

    def _get_course_selection_content(self) -> ft.Column:
        """
        获取课程选择界面内容（卡片化布局）

        Returns:
            ft.Column: 课程选择界面组件
        """
        # 创建课程卡片列表
        course_cards = []
        for course in self.course_list:
            knowledge_count = course.get("knowledgeSum", 0)
            completed_count = course.get("shulian", 0)
            completion_rate = (completed_count / knowledge_count * 100) if knowledge_count > 0 else 0

            course_card = ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.BOOK,
                                    color=ft.Colors.BLUE_600,
                                ),
                                title=ft.Text(
                                    course.get("courseName", ""),
                                    weight=ft.FontWeight.BOLD,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                subtitle=ft.Column(
                                    [
                                        ft.Text(
                                            f"知识点: {knowledge_count} | 已完成: {completed_count}",
                                            size=12,
                                        ),
                                        ft.Text(
                                            f"完成率: {completion_rate:.1f}%",
                                            size=12,
                                            color=ft.Colors.GREEN_600 if completion_rate >= 80 else ft.Colors.ORANGE_600,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ),
                            ft.Divider(height=1, color=ft.Colors.GREY_300),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.TextButton(
                                            "提取答案",
                                            icon=ft.Icons.DOWNLOAD,
                                            on_click=lambda _, c=course: self._on_extract_course_click(c),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            ),
                        ],
                        spacing=0,
                    ),
                    padding=0,
                ),
                elevation=3,
                col={"md": 6},
            )
            course_cards.append(course_card)

        self.course_list_view = ft.ResponsiveRow(
            controls=course_cards,
            spacing=15,
            run_spacing=15,
            columns=12,
        )

        return ft.Column(
            [
                # 顶部标题和返回按钮
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "返回",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: self._on_back_to_class_selection_click(e),
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "课程列表",
                                        size=24,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_800,
                                    ),
                                    ft.Text(
                                        f"{self.selected_class.get('className', '')} - 共 {len(self.course_list)} 门课程",
                                        size=14,
                                        color=ft.Colors.GREY_600,
                                    ),
                                ],
                                spacing=5,
                            ),
                            expand=True,
                            padding=ft.padding.only(left=20),
                        ),
                    ],
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=self.course_list_view,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        )

    def _on_extract_course_click(self, course: Dict):
        """处理课程提取按钮点击事件"""
        self.selected_course = course
        print(f"DEBUG: 提取课程 {course.get('courseName')}")  # 调试信息

        dialog = ft.AlertDialog(
            title=ft.Text("提示"),
            content=ft.Text(f"准备提取课程：{course.get('courseName')}\n\n此功能正在开发中..."),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def _on_back_to_login_click(self, e):
        """返回登录界面"""
        login_content = self._get_teacher_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_to_class_selection_click(self, e):
        """返回班级选择界面"""
        selection_content = self._get_class_selection_content_with_grades()
        self.current_content.content = selection_content
        self.page.update()
