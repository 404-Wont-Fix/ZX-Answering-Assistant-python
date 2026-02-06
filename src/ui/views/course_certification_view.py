"""
ZX Answering Assistant - 课程认证视图模块

This module contains the UI components for the course certification page.
"""

import flet as ft
import json
from pathlib import Path
from src.question_bank_importer import QuestionBankImporter
from src.settings import get_settings_manager


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
        self.question_bank_data = None  # 存储加载的题库数据
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框

        # 答题相关状态
        self.is_answering = False  # 是否正在答题
        self.answer_dialog = None  # 答题日志对话框
        self.log_text = None  # 日志文本控件
        self.auto_answer_instance = None  # 自动答题实例
        self.should_stop_answering = False  # 停止答题标志

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
                                    title=ft.Text("课程认证答题", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用API模式快速完成课程认证"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.ATTACH_FILE, color=ft.Colors.GREEN),
                                    title=ft.Text("导入题库", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("支持JSON格式的题库文件"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.FLASH_ON, color=ft.Colors.ORANGE),
                                    title=ft.Text("快速答题", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用API暴力模式自动答题"),
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

    def _get_answer_content(self) -> ft.Column:
        """
        获取答题界面内容

        Returns:
            ft.Column: 答题界面组件
        """
        return ft.Column(
            [
                ft.Text(
                    "课程认证答题",
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
                                ft.Icon(
                                    ft.Icons.ATTACH_FILE,
                                    size=64,
                                    color=ft.Colors.GREEN_400,
                                ),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "请先导入题库文件",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.GREY_700,
                                ),
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "支持JSON格式的题库文件",
                                    size=14,
                                    color=ft.Colors.GREY_600,
                                ),
                                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                                ft.ElevatedButton(
                                    "选择题库文件",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    bgcolor=ft.Colors.GREEN,
                                    color=ft.Colors.WHITE,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                                    ),
                                    on_click=lambda e: self._on_select_json_bank(e),
                                ),
                                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                ft.ElevatedButton(
                                    "开始答题（API模式）",
                                    icon=ft.Icons.FLASH_ON,
                                    bgcolor=ft.Colors.ORANGE,
                                    color=ft.Colors.WHITE,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                                    ),
                                    on_click=lambda e: self._on_start_api_answer(e),
                                    disabled=not self.question_bank_data,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=30,
                        width=600,
                    ),
                    elevation=5,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.OutlinedButton(
                    "返回",
                    icon=ft.Icons.ARROW_BACK,
                    style=ft.ButtonStyle(
                        animation_duration=200,
                    ),
                    on_click=lambda e: self._on_back_click(e),
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

    def _on_start_answer_click(self, e):
        """处理开始答题按钮点击事件"""
        print("DEBUG: 切换到登录界面")

        # 使用动画切换到登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_from_login(self, e):
        """处理从登录界面返回的按钮点击事件"""
        print("DEBUG: 从登录界面返回主界面")

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

        # 保存教师凭据
        settings_manager = get_settings_manager()
        print("💾 保存教师端凭据...")
        settings_manager.set_teacher_credentials(username, password)

        # 登录成功，跳转到答题界面
        login_success_dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                    ft.Text("登录成功", color=ft.Colors.GREEN),
                ],
                spacing=10,
            ),
            content=ft.Text(f"✅ 欢迎回来，{username}！\n\n正在跳转到答题界面..."),
            actions=[
                ft.TextButton(
                    "确定",
                    on_click=lambda _: self._navigate_to_answer_after_login(),
                ),
            ],
        )
        self.page.show_dialog(login_success_dialog)

    def _navigate_to_answer_after_login(self):
        """登录成功后跳转到答题界面"""
        self.page.pop_dialog()  # 关闭成功对话框
        answer_content = self._get_answer_content()
        self.current_content.content = answer_content
        self.page.update()

    def _on_back_click(self, e):
        """处理返回按钮点击事件"""
        print("DEBUG: 返回主界面")

        # 使用动画切换回主界面
        main_content = self._get_main_content()
        self.current_content.content = main_content
        self.page.update()

    def _on_select_json_bank(self, e):
        """处理选择题库按钮点击事件"""
        print("DEBUG: 选择题库文件")

        # 使用 tkinter 文件选择器
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

        file_name = Path(file_path).name

        try:
            # 使用 QuestionBankImporter 导入并解析题库
            importer = QuestionBankImporter()
            success = importer.import_from_file(file_path)

            if not success:
                raise ValueError("无法导入题库文件")

            # 获取题库类型
            bank_type = importer.get_bank_type()

            # 格式化输出题库信息
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

            # 刷新界面以启用"开始答题"按钮
            answer_content = self._get_answer_content()
            self.current_content.content = answer_content
            self.page.update()

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

        # 检查题库类型
        importer = QuestionBankImporter()
        importer.data = self.question_bank_data
        bank_type = importer.get_bank_type()

        if bank_type != "single":
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("课程认证仅支持单课程题库，请选择单课程题库文件"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 解析课程信息
        parsed = importer.parse_single_course()
        if not parsed:
            dialog = ft.AlertDialog(
                title=ft.Text("错误"),
                content=ft.Text("无法解析题库文件"),
                actions=[
                    ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
                ],
            )
            self.page.show_dialog(dialog)
            return

        # 提取课程ID（从题库数据中）
        # 注意：课程认证的courseID可能需要用户手动输入或从题库中提取
        # 这里我们显示一个对话框让用户输入courseID

        course_name = parsed['course']['courseName']
        default_course_id = parsed['course'].get('courseID', '')

        # 创建输入对话框
        course_id_field = ft.TextField(
            label="课程ID",
            hint_text="请输入课程认证的课程ID",
            value=default_course_id,
            width=400,
        )

        def confirm_input(_):
            course_id = course_id_field.value
            if not course_id:
                return

            self.page.pop_dialog()
            self._start_certification_answer(course_id, self.question_bank_data)

        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE),
                    ft.Text("输入课程ID", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            content=ft.Column(
                [
                    ft.Text(f"课程名称: {course_name}"),
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    course_id_field,
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                ft.ElevatedButton(
                    "确定",
                    on_click=confirm_input,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    def _start_certification_answer(self, course_id: str, question_bank_data: dict):
        """
        开始课程认证答题

        Args:
            course_id: 课程ID
            question_bank_data: 题库数据
        """
        # 设置答题状态
        self.is_answering = True
        self.should_stop_answering = False

        # 创建并显示日志对话框
        self.answer_dialog = self._create_answer_log_dialog("课程认证答题 - API模式")
        self.page.show_dialog(self.answer_dialog)

        # 在后台线程中运行答题任务
        self.page.run_thread(lambda: self._run_certification_task(course_id, question_bank_data))

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
            no_wrap=False,
            max_lines=None,
        )

        # 创建对话框
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
            try:
                self.log_text.update()
            except Exception as e:
                print(f"⚠️ UI更新失败: {e}")

    def _on_stop_answering(self, e):
        """处理停止答题按钮点击事件"""
        print("🛑 用户请求停止答题")
        self._append_log("🛑 正在停止答题...\n")
        self.should_stop_answering = True

        # 如果有自动答题实例，调用其停止方法
        if self.auto_answer_instance and hasattr(self.auto_answer_instance, 'request_stop'):
            self.auto_answer_instance.request_stop()

        # 关闭对话框
        if self.answer_dialog:
            self.page.pop_dialog()
            self.answer_dialog = None

        self.is_answering = False
        self._append_log("✅ 答题已停止\n")

    def _run_certification_task(self, course_id: str, question_bank_data: dict):
        """
        在后台线程中运行课程认证答题任务

        Args:
            course_id: 课程ID
            question_bank_data: 题库数据
        """
        try:
            from src.course_certification import CourseCertificationManager
            from src.settings import get_settings_manager

            self._append_log("🚀 开始课程认证答题\n")
            self._append_log(f"📚 课程ID: {course_id}\n")
            self._append_log("-" * 50 + "\n")

            # 获取设置管理器
            settings_manager = get_settings_manager()

            # 获取教师凭据（用于API认证）
            username, password = settings_manager.get_teacher_credentials()

            if not username or not password:
                self._append_log("❌ 未找到教师端凭据\n")
                self._append_log("💡 请先在设置中配置教师端账号密码\n")
                return

            self._append_log(f"👤 教师账号: {username}\n")

            # 创建课程认证管理器
            manager = CourseCertificationManager(
                teacher_username=username,
                teacher_password=password,
                log_callback=self._append_log
            )
            self.auto_answer_instance = manager

            # 加载题库
            self._append_log("📖 正在加载题库...\n")
            success = manager.load_question_bank(question_bank_data)

            if not success:
                self._append_log("❌ 题库加载失败\n")
                return

            self._append_log("✅ 题库加载成功\n")
            self._append_log("-" * 50 + "\n")

            # 开始答题
            result = manager.auto_answer_course(course_id)

            # 显示结果
            self._append_log("\n" + "=" * 50 + "\n")
            self._append_log("📊 最终统计\n")
            self._append_log("=" * 50 + "\n")
            self._append_log(f"📍 知识点: {result.get('completed_knowledges', 0)}/{result.get('total_knowledges', 0)}\n")
            self._append_log(f"📝 题目总计: {result.get('total_questions', 0)} 题\n")
            self._append_log(f"✅ 成功: {result.get('success', 0)} 题\n")
            self._append_log(f"❌ 失败: {result.get('failed', 0)} 题\n")
            self._append_log("=" * 50 + "\n")

            if result.get('completed_knowledges', 0) >= result.get('total_knowledges', 0):
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
