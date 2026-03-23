"""
WeBan View - 安全微伴课程自动化

WeBan 模块的 GUI 视图，提供安全微伴课程的自动化学习界面。
"""

import flet as ft
import json
import os
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.modules.weban_adapter import get_weban_adapter


class WeBanView:
    """WeBan 视图类"""

    def __init__(self, page: ft.Page):
        """
        初始化视图

        Args:
            page: Flet 页面对象
        """
        self.page = page
        self.adapter = get_weban_adapter(progress_callback=self._log)

        # UI 控件
        self.status_text = None
        self.log_text = None
        self.start_button = None
        self.stop_button = None
        self.config_dropdown = None
        self.account_list = None
        self.multithread_switch = None
        self.config_file_path = None

        # 账号配置
        self.accounts: List[Dict[str, Any]] = []
        self.config_path = Path(__file__).parent.parent.parent.parent / "weban_config.json"

    def _log(self, message: str, level: str = "info"):
        """
        添加日志到 UI

        Args:
            message: 日志消息
            level: 日志级别
        """
        if self.log_text:
            # 在主线程中更新 UI
            def update_log():
                color_map = {
                    "info": ft.Colors.BLUE,
                    "success": ft.Colors.GREEN,
                    "warning": ft.Colors.ORANGE,
                    "error": ft.Colors.RED,
                }
                self.log_text.controls.append(
                    ft.Text(message, color=color_map.get(level, ft.Colors.BLACK))
                )
                # 自动滚动到底部
                if len(self.log_text.controls) > 100:
                    self.log_text.controls.pop(0)
                self.page.update()

            # 如果在后台线程，需要通过主线程更新
            if threading.current_thread() is threading.main_thread():
                update_log()
            else:
                # 使用线程安全的方式更新 UI
                try:
                    self.page.update_threadsafe(update_log)
                except:
                    # 如果 update_threadsafe 不可用，直接更新（可能在新版本 Flet 中）
                    pass

    def _check_dependencies(self) -> bool:
        """检查依赖是否安装"""
        if not self.adapter.check_available():
            self._log("⚠️ WeBan 模块依赖未安装", "warning")
            self._log("依赖列表:", "info")
            for dep in self.adapter.get_dependencies():
                self._log(f"  - {dep}", "info")
            self._log("", "info")
            self._log("请在终端中运行以下命令安装依赖:", "warning")
            self._log("pip install -r requirements.txt", "info")
            return False
        return True

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            self._log(f"配置文件不存在: {self.config_path}", "warning")
            self._log("请先创建配置文件或添加账号配置", "info")
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.accounts = json.load(f)

            if not isinstance(self.accounts, list):
                self._log("配置文件格式错误: 应该是数组", "error")
                return False

            self._log(f"已加载 {len(self.accounts)} 个账号配置", "success")
            return True

        except json.JSONDecodeError as e:
            self._log(f"配置文件格式错误: {e}", "error")
            return False
        except Exception as e:
            self._log(f"加载配置文件失败: {e}", "error")
            return False

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, indent=2, ensure_ascii=False)
            self._log(f"配置已保存到: {self.config_path}", "success")
            return True
        except Exception as e:
            self._log(f"保存配置失败: {e}", "error")
            return False

    def _update_account_list(self):
        """更新账号列表显示"""
        if self.account_list:
            self.account_list.controls.clear()

            for i, account in enumerate(self.accounts):
                # 获取显示信息
                tenant_name = account.get("tenant_name", "未设置")
                account_id = account.get("account") or account.get("user", {}).get("userId") or "未设置"
                login_type = "Token" if account.get("user", {}).get("token") else "密码"

                self.account_list.controls.append(
                    ft.ListTile(
                        leading=ft.CircleAvatar(content=ft.Text(str(i + 1)), radius=16),
                        title=ft.Text(f"{tenant_name} - {login_type}登录"),
                        subtitle=ft.Text(f"账号: {account_id}"),
                        trailing=ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            tooltip="删除账号",
                            on_click=lambda e, idx=i: self._delete_account(idx),
                        ),
                    )
                )

            self.page.update()

    def _add_account_dialog(self, e=None):
        """显示添加账号对话框"""
        tenant_name_field = ft.TextField(label="学校名称", hint_text="例如: 重庆大学")
        account_field = ft.TextField(label="账号（可选）", hint_text="密码登录时必填")
        password_field = ft.TextField(label="密码（可选）", password=True, can_reveal_password=True)
        user_id_field = ft.TextField(label="User ID（可选）", hint_text="Token 登录时必填")
        token_field = ft.TextField(label="Token（可选）", hint_text="Token 登录时必填")

        study_switch = ft.Switch(label="学习课程", value=True)
        study_time_field = ft.TextField(
            label="学习时长（秒）",
            value="20",
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        exam_switch = ft.Switch(label="参加考试", value=True)
        exam_time_field = ft.TextField(
            label="考试时长（秒）",
            value="250",
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        def validate_tenant(e=None):
            """验证学校名称"""
            tenant = tenant_name_field.value.strip()
            if not tenant:
                tenant_name_field.error_text = "请输入学校名称"
                self.page.update()
                return

            result = self.adapter.validate_tenant(tenant)
            if result["success"]:
                tenant_name_field.error_text = None
                tenant_name_field.helper_text = result["message"]
                self.page.update()
            else:
                tenant_name_field.error_text = result["message"]
                self.page.update()

        validate_btn = ft.ElevatedButton(
            "验证学校",
            on_click=validate_tenant,
            icon=ft.Icons.CHECK,
        )

        def save_account(e=None):
            """保存账号"""
            tenant = tenant_name_field.value.strip()
            if not tenant:
                self._log("请输入学校名称", "warning")
                return

            # 构建账号配置
            account_config = {
                "tenant_name": tenant,
                "study": study_switch.value,
                "study_time": int(study_time_field.value or "20"),
                "restudy_time": 0,
                "exam": exam_switch.value,
                "exam_use_time": int(exam_time_field.value or "250"),
                "account": account_field.value or "",
                "password": password_field.value or "",
                "user": {
                    "userId": user_id_field.value or "",
                    "token": token_field.value or "",
                },
            }

            # 验证至少有一种登录方式
            has_password = bool(account_config["account"] and account_config["password"])
            has_token = bool(account_config["user"]["userId"] and account_config["user"]["token"])

            if not (has_password or has_token):
                self._log("请至少配置一种登录方式（密码或 Token）", "warning")
                return

            self.accounts.append(account_config)
            self._save_config()
            self._update_account_list()
            self._log(f"已添加账号: {tenant}", "success")
            dialog.open = False
            self.page.update()

        save_btn = ft.ElevatedButton(
            "保存",
            on_click=save_account,
            icon=ft.Icons.SAVE,
        )

        cancel_btn = ft.ElevatedButton(
            "取消",
            on_click=lambda e: setattr(dialog, "open", False) or self.page.update(),
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("添加账号配置"),
            content=ft.Container(
                content=ft.Column(
                    [
                        tenant_name_field,
                        ft.Row([validate_btn], alignment=ft.MainAxisAlignment.END),
                        ft.Divider(),
                        ft.Text("密码登录", weight=ft.FontWeight.BOLD),
                        account_field,
                        password_field,
                        ft.Divider(),
                        ft.Text("Token 登录（推荐）", weight=ft.FontWeight.BOLD),
                        user_id_field,
                        token_field,
                        ft.Divider(),
                        ft.Text("任务设置", weight=ft.FontWeight.BOLD),
                        ft.Row([study_switch, study_time_field]),
                        ft.Row([exam_switch, exam_time_field]),
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    height=500,
                ),
                width=500,
            ),
            actions=[cancel_btn, save_btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _delete_account(self, index: int):
        """删除账号"""
        if 0 <= index < len(self.accounts):
            account = self.accounts.pop(index)
            self._save_config()
            self._update_account_list()
            self._log(f"已删除账号: {account.get('tenant_name', 'Unknown')}", "info")

    def _start_task(self, e=None):
        """开始任务"""
        if not self._check_dependencies():
            return

        if not self.accounts:
            self._log("请先添加账号配置", "warning")
            return

        # 更新 UI 状态
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.status_text.value = "正在执行..."
        self.page.update()

        # 在后台线程中执行任务
        def run_task():
            try:
                # 加载配置到适配器
                if self.adapter.load_config(self.accounts):
                    # 执行任务
                    use_multithread = self.multithread_switch.value if self.multithread_switch else False
                    result = self.adapter.start(use_multithread=use_multithread)

                    # 更新结果
                    self._log(
                        f"任务完成！成功: {result['success']}, 失败: {result['failed']}",
                        "success" if result["failed"] == 0 else "warning"
                    )
                else:
                    self._log("配置加载失败", "error")

            finally:
                # 恢复 UI 状态
                def update_ui():
                    self.start_button.disabled = False
                    self.stop_button.disabled = True
                    self.status_text.value = "就绪"
                    self.page.update()

                if threading.current_thread() is threading.main_thread():
                    update_ui()
                else:
                    try:
                        self.page.update_threadsafe(update_ui)
                    except:
                        pass

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

    def _stop_task(self, e=None):
        """停止任务"""
        self.adapter.stop()
        self._log("正在停止任务...", "warning")
        self.status_text.value = "正在停止..."
        self.page.update()

    def get_content(self) -> ft.Container:
        """
        获取视图内容

        Returns:
            Flet Container 对象
        """
        # 状态栏
        self.status_text = ft.Text(
            "就绪",
            size=14,
            color=ft.Colors.GREY_600,
        )

        # 账号列表
        self.account_list = ft.Column(
            [],
            scroll=ft.ScrollMode.AUTO,
            height=200,
        )

        # 多线程开关
        self.multithread_switch = ft.Switch(
            label="多线程执行（多个账号时）",
            value=True,
            tooltip="启用后多个账号将同时执行",
        )

        # 按钮
        self.start_button = ft.ElevatedButton(
            "开始执行",
            icon=ft.Icons.PLAY_ARROW,
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE,
            on_click=self._start_task,
            disabled=False,
        )

        self.stop_button = ft.ElevatedButton(
            "停止执行",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            on_click=self._stop_task,
            disabled=True,
        )

        # 日志区域
        self.log_text = ft.Column(
            [],
            scroll=ft.ScrollMode.AUTO,
            height=300,
        )

        # 主内容
        content = ft.Container(
            content=ft.Column(
                [
                    # 标题
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.SECURITY, size=32, color=ft.Colors.BLUE),
                            ft.Text(
                                "安全微伴 (WeBan)",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_800,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                    # 说明卡片
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.ListTile(
                                        leading=ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE),
                                        title=ft.Text("功能说明", weight=ft.FontWeight.BOLD),
                                        subtitle=ft.Text(
                                            "自动化完成安全微伴课程的学习和考试。"
                                            "支持多账号并发执行，自动同步题库。"
                                        ),
                                    ),
                                    ft.ListTile(
                                        leading=ft.Icon(ft.Icons.LINK, color=ft.Colors.GREEN),
                                        title=ft.Text("项目地址", weight=ft.FontWeight.BOLD),
                                        subtitle=ft.Text("https://github.com/hangone/WeBan"),
                                    ),
                                ],
                            ),
                            padding=10,
                        ),
                        elevation=1,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                    # 账号管理区域
                    ft.Text(
                        "账号配置",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "添加账号",
                                icon=ft.Icons.ADD,
                                on_click=self._add_account_dialog,
                            ),
                            ft.ElevatedButton(
                                "刷新列表",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda e: self._load_config() or self._update_account_list(),
                            ),
                        ],
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                    ft.Card(
                        content=ft.Container(
                            content=self.account_list,
                            padding=10,
                        ),
                        elevation=1,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                    # 任务控制区域
                    ft.Text(
                        "任务控制",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                    self.multithread_switch,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                    ft.Row(
                        [
                            self.start_button,
                            self.stop_button,
                            ft.Container(width=20),  # 间距
                            self.status_text,
                        ],
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                    # 日志区域
                    ft.Text(
                        "执行日志",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_800,
                    ),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),

                    ft.Card(
                        content=ft.Container(
                            content=self.log_text,
                            padding=10,
                            bgcolor=ft.Colors.GREY_100,
                        ),
                        elevation=1,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=30,
            expand=True,
        )

        # 初始化时加载配置
        if self.config_path.exists():
            self._load_config()
            self._update_account_list()

        return content
