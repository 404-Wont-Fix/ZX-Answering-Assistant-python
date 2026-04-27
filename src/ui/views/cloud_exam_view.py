"""
ZX Answering Assistant - 云考试视图模块

This module contains the UI components for the cloud exam page.
"""

import flet as ft
import threading
from pathlib import Path
from src.cloud_exam.workflow import CloudExamWorkflow, NetworkMonitor
from src.core.config import get_settings_manager
from src.auth.student import get_student_access_token


class CloudExamView:
    """云考试页面视图"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化云考试视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于导航切换）
        """
        self.page = page
        self.main_app = main_app
        self.current_content = None  # 保存当前内容容器的引用

        # 登录相关
        self.username_field = None  # 用户名输入框
        self.password_field = None  # 密码输入框
        self.remember_password_checkbox = None  # 记住密码复选框
        self.progress_dialog = None  # 登录进度对话框
        self.exp_id_field = None  # 考试ID输入框

        # 状态数据
        self.access_token = None
        self.username = ""
        self.exam_paper = None
        self.question_bank_data = None
        self.workflow = None

        # 设置管理器
        self.settings_manager = get_settings_manager()

    def get_content(self) -> ft.Column:
        """
        获取云考试页面的内容

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

    # ==================== 简介页面 ====================

    def _get_main_content(self) -> ft.Column:
        """获取简介页面内容"""
        return ft.Column(
            [
                ft.Text(
                    "云考试助手",
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
                                    leading=ft.Icon(ft.Icons.LOGIN, color=ft.Colors.BLUE),
                                    title=ft.Text("学生端登录", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("使用学生端账号登录系统"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CLOUD_DOWNLOAD, color=ft.Colors.GREEN),
                                    title=ft.Text("获取试卷", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("自动捕获浏览器中的云考试试卷"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.LIBRARY_BOOKS, color=ft.Colors.ORANGE),
                                    title=ft.Text("加载题库", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("导入JSON格式的题目答案库"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.AUTO_FIX_HIGH, color=ft.Colors.RED),
                                    title=ft.Text("答案注入", weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text("自动匹配并提交答案到考试系统"),
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
                    "开始使用",
                    icon=ft.Icons.PLAY_ARROW,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.padding.symmetric(horizontal=30, vertical=15),
                        animation_duration=200,
                    ),
                    on_click=lambda e: self._on_start_click(e),
                    animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ==================== 登录页面 ====================

    def _get_login_content(self) -> ft.Column:
        """获取学生登录界面内容"""
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
            value=bool(saved_username and saved_password),
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

    # ==================== 功能面板页面 ====================

    def _get_function_panel_content(self) -> ft.Column:
        """获取功能面板内容"""
        return ft.Column(
            [
                ft.Text(
                    "云考试助手",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 状态卡片
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.CHECK_CIRCLE if self.access_token else ft.Icons.PENDING,
                                        color=ft.Colors.GREEN if self.access_token else ft.Colors.GREY
                                    ),
                                    title=ft.Text("登录状态"),
                                    subtitle=ft.Text("已登录" if self.access_token else "未登录"),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.CHECK_CIRCLE if self.exam_paper else ft.Icons.PENDING,
                                        color=ft.Colors.GREEN if self.exam_paper else ft.Colors.GREY
                                    ),
                                    title=ft.Text("试卷状态"),
                                    subtitle=ft.Text(
                                        f"已获取 ({self.exam_paper.get_total_questions_count()}题)" if self.exam_paper
                                        else "未获取"
                                    ),
                                ),
                                ft.ListTile(
                                    leading=ft.Icon(
                                        ft.Icons.CHECK_CIRCLE if self.question_bank_data else ft.Icons.PENDING,
                                        color=ft.Colors.GREEN if self.question_bank_data else ft.Colors.GREY
                                    ),
                                    title=ft.Text("题库状态"),
                                    subtitle=ft.Text("已加载" if self.question_bank_data else "未加载"),
                                ),
                            ],
                            spacing=0,
                        ),
                        padding=20,
                        width=500,
                    ),
                    elevation=2,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                # 三个功能按钮
                ft.ElevatedButton(
                    "📥 获取试卷",
                    icon=ft.Icons.CLOUD_DOWNLOAD,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    width=400,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                    on_click=lambda e: self._on_get_paper_click(e),
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "📚 加载题库",
                    icon=ft.Icons.LIBRARY_BOOKS,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE,
                    width=400,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                    on_click=lambda e: self._on_load_bank_click(e),
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.ElevatedButton(
                    "💉 答案注入",
                    icon=ft.Icons.AUTO_FIX_HIGH,
                    bgcolor=ft.Colors.ORANGE,
                    color=ft.Colors.WHITE,
                    width=400,
                    disabled=not (self.exam_paper and self.question_bank_data),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                    on_click=lambda e: self._on_inject_click(e),
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.OutlinedButton(
                    "返回",
                    icon=ft.Icons.ARROW_BACK,
                    width=400,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                    on_click=lambda e: self._on_back_to_main(e),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ==================== 事件处理 ====================

    def _on_start_click(self, e):
        """处理开始使用按钮点击 - 切换到登录界面"""
        print("DEBUG: 切换到登录界面")

        # 使用动画切换到登录界面
        login_content = self._get_login_content()
        self.current_content.content = login_content
        self.page.update()

    def _on_back_click(self, e):
        """处理返回按钮点击事件 - 返回主界面"""
        print("DEBUG: 返回主界面")

        # 使用动画切换回主界面
        main_content = self._get_main_content()
        self.current_content.content = main_content
        self.page.update()

    def _on_back_to_main(self, e):
        """处理从功能面板返回简介页"""
        print("DEBUG: 返回简介页面")
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
                        ft.Text("✅ 登录成功！\n正在初始化工作流程..."),
                        ft.ProgressRing(stroke_width=3),
                    ],
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
                self.page.update()

                # 初始化工作流程（但不启动网络监听器）
                from src.cloud_exam.workflow import CloudExamWorkflow
                workflow = CloudExamWorkflow(log_callback=self._append_log)
                self.workflow = workflow
                workflow.access_token = access_token

                print("✅ 工作流程已初始化")
                print("💡 网络监听器将在获取试卷时启动")

                # 关闭进度对话框
                self.page.pop_dialog()

                # 切换到功能面板
                function_panel = self._get_function_panel_content()
                self.current_content.content = function_panel
                self.page.update()

            else:
                print("❌ 登录失败")
                self.page.pop_dialog()

                error_dialog = ft.AlertDialog(
                    title=ft.Text("登录失败"),
                    content=ft.Text(
                        "❌ 学生端登录失败，请检查账号密码是否正确。"
                    ),
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

    def _on_get_paper_click(self, e):
        """处理获取试卷按钮点击"""
        if not self.access_token:
            self._show_error_dialog("请先登录学生端账号")
            return

        # 创建TextField引用
        self.exp_id_field = ft.TextField(
            hint_text="粘贴考试ID，例如: b6205e42cfdf4b1da7e6ecd2c03f1179",
            width=500,
            autofocus=True,
        )

        # 显示提示对话框
        waiting_dialog = ft.AlertDialog(
            title=ft.Text("获取试卷"),
            content=ft.Column(
                [
                    ft.Text("请按以下步骤操作："),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text("1. 在已登录的浏览器中打开云考试页面", weight=ft.FontWeight.BOLD),
                    ft.Text("2. 选择并进入要完成的考试"),
                    ft.Text("3. 从浏览器地址栏复制考试ID（expID参数）"),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text("示例URL:"),
                    ft.Text(
                        "https://ai.cqzuxia.com/#/exam?expID=b6205e42cfdf4b1da7e6ecd2c03f1179",
                        size=10,
                        color=ft.Colors.GREY_600,
                    ),
                    ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                    ft.Text("请输入考试ID（expID）："),
                    self.exp_id_field,
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                ft.ElevatedButton(
                    "获取试卷",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=lambda _: self._confirm_get_paper(waiting_dialog),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(waiting_dialog)

    def _confirm_get_paper(self, dialog: ft.AlertDialog):
        """确认获取试卷"""
        # 获取输入的exp_id
        exp_id_input = self.exp_id_field.value

        if not exp_id_input or len(exp_id_input) < 10:
            self._show_error_dialog("请输入有效的考试ID")
            return

        self.page.pop_dialog()

        # 显示加载对话框
        loading_dialog = ft.AlertDialog(
            title=ft.Text("正在获取试卷"),
            content=ft.Column(
                [
                    ft.Text(f"正在获取试卷: {exp_id_input[:16]}..."),
                    ft.ProgressRing(stroke_width=3),
                ],
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            actions=[],
            modal=True,
        )
        self.page.show_dialog(loading_dialog)

        # 在后台线程中获取试卷
        def capture_task():
            try:
                workflow = self.workflow or CloudExamWorkflow(log_callback=self._append_log)
                self.workflow = workflow

                # 直接使用API获取试卷（不需要网络监听）
                exam_paper = workflow.capture_exam_paper(exp_id_input)

                self.page.pop_dialog()

                if exam_paper:
                    self.exam_paper = exam_paper

                    # 刷新界面
                    self._refresh_function_panel()

                    # 显示成功对话框
                    self._show_success_dialog(
                        "试卷获取成功",
                        f"✅ 成功获取试卷\n\n"
                        f"考试ID: {exp_id_input[:16]}...\n"
                        f"题目数量: {exam_paper.get_total_questions_count()} 题"
                    )
                else:
                    # 获取失败，显示详细错误信息
                    self._show_error_dialog(
                        "试卷获取失败\n\n"
                        "可能的原因：\n"
                        "1. 该考试已交卷（已完成）\n"
                        "2. 考试ID不正确\n"
                        "3. 网络连接问题\n\n"
                        "💡 请检查控制台日志了解详情"
                    )

            except Exception as ex:
                self.page.pop_dialog()
                self._show_error_dialog(f"获取试卷失败: {str(ex)}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=capture_task, daemon=True).start()

    def _on_load_bank_click(self, e):
        """处理加载题库按钮点击"""
        def on_file_picked(file_picker_result):
            """文件选择回调（不使用类型注解以兼容 Flet 0.82.2）"""
            if hasattr(file_picker_result, 'path') and file_picker_result.path:
                self._process_question_bank(file_picker_result.path)
            elif hasattr(file_picker_result, 'files') and file_picker_result.files:
                files = file_picker_result.files
                if files and len(files) > 0:
                    self._process_question_bank(files[0].path)

        # 创建并显示文件选择器
        pick_files_dialog = ft.FilePicker(on_result=on_file_picked)
        self.page.overlay.append(pick_files_dialog)
        self.page.update()

        # 打开文件选择对话框
        pick_files_dialog.pick_files(
            allowed_extensions=["json"],
            dialog_title="选择JSON题库文件"
        )

    def _process_question_bank(self, file_path: str):
        """处理选中的题库文件"""
        def load_task():
            try:
                workflow = self.workflow or CloudExamWorkflow(log_callback=self._append_log)
                self.workflow = workflow

                success = workflow.load_question_bank(file_path)

                if success:
                    self.question_bank_data = workflow.question_bank_data

                    # 如果已有试卷，验证题库
                    if self.exam_paper:
                        validation = workflow.validate_question_bank()
                        if not validation['valid']:
                            self._show_warning_dialog(
                                "题库匹配度较低",
                                f"⚠️ 题库匹配率: {validation['match_rate']:.1%}\n\n"
                                f"可能不是对应的题库，请检查后再使用"
                            )

                    # 刷新界面
                    self._refresh_function_panel()

                    self._show_success_dialog(
                        "题库加载成功",
                        f"✅ 题库文件已加载\n\n"
                        f"文件: {Path(file_path).name}"
                    )
                else:
                    self._show_error_dialog("题库加载失败，请查看日志")

            except Exception as ex:
                self._show_error_dialog(f"加载题库失败: {str(ex)}")

        threading.Thread(target=load_task, daemon=True).start()

    def _on_inject_click(self, e):
        """处理答案注入按钮点击"""
        if not self.exam_paper:
            self._show_error_dialog("请先获取试卷")
            return

        if not self.question_bank_data:
            self._show_error_dialog("请先加载题库")
            return

        # 显示确认对话框
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("确认注入答案"),
            content=ft.Column(
                [
                    ft.Text("即将开始自动答题，请确认："),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text(f"• 试卷题目: {self.exam_paper.get_total_questions_count()} 题"),
                    ft.Text(f"• 已提交: {self.exam_paper.get_answered_questions_count()} 题"),
                    ft.Text(f"• 未提交: {self.exam_paper.get_total_questions_count() - self.exam_paper.get_answered_questions_count()} 题"),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ft.Text("⚠️ 答案提交后无法修改，请谨慎操作", color=ft.Colors.RED),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self.page.pop_dialog()),
                ft.ElevatedButton(
                    "确认开始",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=lambda _: self._confirm_inject(confirm_dialog),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(confirm_dialog)

    def _confirm_inject(self, dialog: ft.AlertDialog):
        """确认注入答案"""
        self.page.pop_dialog()

        # 创建日志对话框
        log_dialog = self._create_log_dialog("答案注入")
        self.page.show_dialog(log_dialog)

        # 在后台线程中执行注入
        def inject_task():
            try:
                workflow = self.workflow or CloudExamWorkflow(log_callback=self._append_log)
                self.workflow = workflow

                # 执行答案注入
                result = workflow.inject_answers()

                # 显示结果
                self._append_log("\n" + "=" * 50)
                self._append_log("📊 最终统计")
                self._append_log("=" * 50)
                self._append_log(f"总计: {result['total']} 题")
                self._append_log(f"成功: {result['success']} 题")
                self._append_log(f"失败: {result['failed']} 题")
                self._append_log(f"跳过: {result['skipped']} 题")
                self._append_log("=" * 50)

                if result['success'] > 0:
                    self._append_log("\n🎉 答案注入完成！", "success")

                # 延迟关闭对话框
                import time
                time.sleep(2)
                if log_dialog in self.page.dialogs:
                    self.page.pop_dialog()

                # 刷新界面
                self._refresh_function_panel()

            except Exception as ex:
                self._append_log(f"\n❌ 注入失败: {str(ex)}", "error")
                import traceback
                self._append_log(f"详细错误: {traceback.format_exc()}")

        threading.Thread(target=inject_task, daemon=True).start()

    # ==================== 辅助方法 ====================

    def _refresh_function_panel(self):
        """刷新功能面板"""
        function_panel = self._get_function_panel_content()
        self.current_content.content = function_panel
        self.page.update()

    def _append_log(self, message: str, level: str = "info"):
        """追加日志（暂未实现，预留接口）"""
        # 可以在日志对话框中显示
        print(f"[{level.upper()}] {message}")

    def _create_log_dialog(self, title: str) -> ft.AlertDialog:
        """创建日志对话框"""
        log_text = ft.Text(
            "",
            size=12,
            color=ft.Colors.BLACK,
            selectable=True,
            no_wrap=False,
        )

        # 保存引用以便更新
        self._current_log_text = log_text

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("答题日志：", size=12, weight=ft.FontWeight.BOLD),
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        ft.Container(
                            content=ft.Column(
                                [log_text],
                                scroll=ft.ScrollMode.ALWAYS,
                            ),
                            width=500,
                            height=300,
                            bgcolor=ft.Colors.GREY_100,
                            border=ft.border.all(1, ft.Colors.GREY_300),
                            border_radius=8,
                            padding=10,
                        ),
                    ],
                    spacing=0,
                ),
                width=550,
                padding=20,
            ),
            actions=[
                ft.TextButton("关闭", on_click=lambda _: self.page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        return dialog

    def _show_success_dialog(self, title: str, message: str):
        """显示成功对话框"""
        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                    ft.Text(title, color=ft.Colors.GREEN),
                ],
                spacing=10,
            ),
            content=ft.Text(message),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def _show_error_dialog(self, message: str):
        """显示错误对话框"""
        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED),
                    ft.Text("错误", color=ft.Colors.RED),
                ],
                spacing=10,
            ),
            content=ft.Text(message),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def _show_warning_dialog(self, title: str, message: str):
        """显示警告对话框"""
        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.ORANGE),
                    ft.Text(title, color=ft.Colors.ORANGE),
                ],
                spacing=10,
            ),
            content=ft.Text(message),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)
