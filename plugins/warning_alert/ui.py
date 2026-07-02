"""
警告提示器插件 UI 模块

提供自定义警告提示的 UI 组件
"""

import flet as ft
import json
import threading
import time
from pathlib import Path


class WarningAlertPlugin:
    """警告提示器插件UI类"""

    def __init__(self, page, context):
        """
        初始化警告提示器插件

        Args:
            page: Flet 页面对象
            context: PluginContext 实例
        """
        self.page = page
        self.context = context

        # 循环弹窗控制
        self.loop_timer = None
        self.is_loop_running = False
        self.loop_lock = threading.Lock()

        # 默认警告配置（完整版）
        self.default_config = {
            "title": "⚠️ 重要警告",
            "content": "这是一条重要的警告信息！\n\n请注意仔细阅读相关内容。",
            "window_size": "large",
            "window_width": 700,
            "window_height": 450,
            "warning_level": "warning",
            "bgcolor": "red",
            "title_color": "red_800",
            "show_icon": True,
            "icon_type": "unicode",
            "icon_size": 48,
            "font_family": "Microsoft YaHei",
            "title_size": 32,
            "content_size": 16,
            "button_text": "✓ 我知道了",
            "button_style": "modern",
            "enable_sound": False,
            "auto_close": False,
            "auto_close_seconds": 10,
            "enable_animation": True,
            "window_opacity": 1.0,
            "always_on_top": True,
            "enable_escape": True,
            "theme_preset": "default",
            "enable_loop": False,
            "loop_interval": 60,
        }

        # 加载保存的配置
        self.load_config()

    def load_config(self):
        """加载保存的警告配置"""
        saved_config = self.context.get_plugin_config("settings", {})
        if isinstance(saved_config, dict):
            self.default_config.update(saved_config)

        # 兼容旧版本在插件目录中写入的配置，并在读取后迁移到统一配置。
        legacy_config_file = Path(__file__).parent / "warning_config.json"
        if legacy_config_file.exists():
            try:
                with open(legacy_config_file, 'r', encoding='utf-8') as f:
                    legacy_config = json.load(f)
                if isinstance(legacy_config, dict):
                    self.default_config.update(legacy_config)
                    if self.context.set_plugin_config("settings", legacy_config):
                        legacy_config_file.unlink(missing_ok=True)
            except Exception as e:
                print(f"[WarningAlert] 加载配置失败: {e}")

    def stop_loop(self, e=None):
        """停止循环弹窗"""
        print(f"[WarningAlert] 尝试停止循环弹窗")

        with self.loop_lock:
            was_running = self.is_loop_running
            print(f"[WarningAlert] 循环状态: {was_running}")

            if self.loop_timer:
                try:
                    self.loop_timer.cancel()
                    print(f"[WarningAlert] 定时器已取消")
                except Exception as ex:
                    print(f"[WarningAlert] 取消定时器失败: {ex}")
                self.loop_timer = None
            self.is_loop_running = False

        if was_running:
            print(f"[WarningAlert] 循环弹窗已停止")

            # 显示提示（不在后台线程中更新UI）
            try:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("循环弹窗已停止！"),
                    bgcolor=ft.Colors.ORANGE,
                    duration=2000,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as ex:
                print(f"[WarningAlert] 更新UI失败: {ex}")
        else:
            print(f"[WarningAlert] 没有循环弹窗在运行")

            try:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text("当前没有循环弹窗在运行"),
                    bgcolor=ft.Colors.GREY,
                    duration=2000,
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as ex:
                print(f"[WarningAlert] 更新UI失败: {ex}")

    def save_config(self, new_config):
        """保存警告配置"""
        try:
            if not self.context.set_plugin_config("settings", new_config):
                raise OSError("统一配置写入失败")
            self.default_config.update(new_config)
            print(f"[WarningAlert] 配置已保存")
        except Exception as e:
            print(f"[WarningAlert] 保存配置失败: {e}")

    def show_warning_dialog(self, e=None, show_ui_feedback=True):
        """显示独立警告窗口 - 使用Tkinter在独立线程中运行"""
        try:
            # 检查是否启用循环弹窗
            enable_loop = self.default_config.get('enable_loop', False)

            # 启动循环模式（如果启用且未运行）
            if enable_loop and not self.is_loop_running:
                with self.loop_lock:
                    self.is_loop_running = True
                print(f"[WarningAlert] 循环弹窗模式已启动")

            # 在后台运行 tkinter 窗口，避免阻塞 Flet UI。
            self._run_background(self._run_tkinter_window)

            print(f"[WarningAlert] Tkinter警告窗口已启动")

            # 显示提示（仅在主线程中）
            if show_ui_feedback:
                try:
                    if self.is_loop_running:
                        status_msg = f"循环弹窗已启动！间隔：{self.default_config.get('loop_interval', 60)}秒"
                        status_color = ft.Colors.ORANGE
                    else:
                        status_msg = "警告窗口已打开！"
                        status_color = ft.Colors.GREEN

                    self.page.snack_bar = ft.SnackBar(
                        ft.Text(status_msg),
                        bgcolor=status_color,
                        duration=3000,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                except Exception as ex:
                    print(f"[WarningAlert] 更新UI失败: {ex}")

        except Exception as ex:
            print(f"[WarningAlert] 启动警告窗口失败: {ex}")
            if show_ui_feedback:
                try:
                    self.page.snack_bar = ft.SnackBar(
                        ft.Text(f"启动警告窗口失败: {str(ex)}"),
                        bgcolor=ft.Colors.RED,
                        duration=3000,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                except Exception as ui_ex:
                    print(f"[WarningAlert] 显示错误消息失败: {ui_ex}")

    def _run_background(self, target, *args, **kwargs):
        """通过插件上下文运行后台任务，独立预览时回落到普通线程。"""
        if self.context and hasattr(self.context, "run_task"):
            return self.context.run_task(target, None, *args, **kwargs)

        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread

    def _schedule_next_window(self):
        """安排下一次弹窗"""
        with self.loop_lock:
            if not self.is_loop_running:
                return

            interval = self.default_config.get('loop_interval', 60)
            print(f"[WarningAlert] 循环弹窗：{interval}秒后重新弹出")

            def show_next():
                """定时器触发后显示窗口"""
                with self.loop_lock:
                    if not self.is_loop_running:
                        print(f"[WarningAlert] 循环已停止，取消弹窗")
                        return

                print(f"[WarningAlert] 定时器触发，显示警告窗口")
                # 在定时器回调中不显示UI反馈，避免跨线程UI更新
                self.show_warning_dialog(show_ui_feedback=False)

            # 使用Timer替代time.sleep和Thread
            self.loop_timer = threading.Timer(interval, show_next)
            self.loop_timer.start()

    def _run_tkinter_window(self):
        """在线程中运行Tkinter窗口"""
        try:
            import tkinter as tk
            from tkinter import font, messagebox
            import time

            config = self.default_config

            # 颜色映射
            color_map = {
                "red": "#FFEBEE",
                "orange": "#FFF3E0",
                "yellow": "#FFFDE7",
                "blue": "#E3F2FD",
                "green": "#E8F5E9",
                "purple": "#F3E5F5",
                "grey": "#F5F5F5",
            }

            title_color_map = {
                "red_800": "#C62828",
                "orange_800": "#E65100",
                "blue_800": "#1565C0",
                "green_800": "#2E7D32",
                "purple_800": "#6A1B9A",
                "grey_800": "#424242",
            }

            button_color_map = {
                "red": "#F44336",
                "orange": "#FF9800",
                "yellow": "#FFC107",
                "blue": "#2196F3",
                "green": "#4CAF50",
                "purple": "#9C27B0",
                "grey": "#9E9E9E",
            }

            bg_color = color_map.get(config['bgcolor'], "#FFEBEE")
            title_color = title_color_map.get(config['title_color'], "#C62828")
            button_color = button_color_map.get(config['bgcolor'], "#F44336")

            # 创建主窗口
            root = tk.Tk()
            root.title("警告提示")

            # 设置窗口大小和居中
            window_width = config.get('window_width', 700)
            window_height = config.get('window_height', 450)
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            root.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # 设置窗口不可调整大小
            root.resizable(False, False)

            # 设置窗口总是在最前面
            if config.get('always_on_top', True):
                root.attributes('-topmost', True)

            # 设置窗口透明度
            opacity = config.get('window_opacity', 1.0)
            if opacity < 1.0:
                try:
                    root.attributes('-alpha', opacity)
                except:
                    pass

            # 设置背景颜色
            root.configure(bg=bg_color)

            # 创建字体
            title_font = font.Font(
                family=config.get('font_family', 'Microsoft YaHei'),
                size=config.get('title_size', 32),
                weight="bold"
            )
            content_font = font.Font(
                family=config.get('font_family', 'Microsoft YaHei'),
                size=config.get('content_size', 16)
            )
            button_font = font.Font(
                family=config.get('font_family', 'Microsoft YaHei'),
                size=14,
                weight="bold"
            )

            # 主容器
            main_frame = tk.Frame(root, bg=bg_color, padx=30, pady=30)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # 标题区域
            title_frame = tk.Frame(main_frame, bg=bg_color)
            title_frame.pack(fill=tk.X, pady=(0, 20))

            # 标题文本（标题本身已包含图标，居中显示）
            title_label = tk.Label(
                title_frame,
                text=config.get('title', '警告'),
                font=title_font,
                bg=bg_color,
                fg=title_color
            )
            title_label.pack()  # 默认居中显示

            # 内容区域
            content_frame = tk.Frame(
                main_frame,
                bg="white",
                relief=tk.RAISED,
                bd=0,
                padx=30,
                pady=30
            )
            content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 30))

            # 内容文本
            content_label = tk.Label(
                content_frame,
                text=config.get('content', ''),
                font=content_font,
                bg="white",
                fg="#424242",
                justify=tk.CENTER,
                wraplength=window_width - 120
            )
            content_label.pack(expand=True)

            # 按钮区域
            button_frame = tk.Frame(main_frame, bg=bg_color)
            button_frame.pack(fill=tk.X)

            # 自动关闭计时器
            auto_close_timer = None

            def close_window():
                """关闭窗口"""
                nonlocal auto_close_timer
                if auto_close_timer:
                    root.after_cancel(auto_close_timer)
                root.destroy()

                # 如果启用了循环弹窗，安排下一次弹窗
                if config.get('enable_loop', False):
                    print(f"[WarningAlert] 窗口已关闭，等待{config.get('loop_interval', 60)}秒后重新弹出")
                    # 调度下一次弹窗
                    self._schedule_next_window()

            def update_button_text(remaining_seconds):
                """更新按钮文本显示倒计时"""
                if remaining_seconds > 0:
                    button_text = f"{config.get('button_text', '我知道了')} ({remaining_seconds}s)"
                    close_button.config(text=button_text)
                    return root.after(1000, update_button_text, remaining_seconds - 1)
                else:
                    close_window()
                    return None

            # 关闭按钮
            button_text = config.get('button_text', '✓ 我知道了')
            close_button = tk.Button(
                button_frame,
                text=button_text,
                font=button_font,
                bg=button_color,
                fg="white",
                activebackground=self._darken_color(button_color),
                activeforeground="white",
                relief=tk.FLAT,
                cursor="hand2",
                padx=50,
                pady=15,
                command=close_window,
                borderwidth=0,
                highlightthickness=0
            )
            close_button.pack()

            # 按钮悬停效果
            def on_enter(e):
                close_button.config(bg=self._darken_color(button_color))

            def on_leave(e):
                close_button.config(bg=button_color)

            close_button.bind('<Enter>', on_enter)
            close_button.bind('<Leave>', on_leave)

            # 绑定ESC键关闭
            if config.get('enable_escape', True):
                root.bind('<Escape>', lambda e: close_window())

            # 自动关闭功能
            if config.get('auto_close', False):
                auto_close_seconds = config.get('auto_close_seconds', 10)
                auto_close_timer = update_button_text(auto_close_seconds)

            # 设置窗口焦点到关闭按钮
            close_button.focus_set()

            # 淡入动画
            if config.get('enable_animation', True):
                try:
                    for i in range(0, 11):
                        alpha = i / 10.0 * config.get('window_opacity', 1.0)
                        root.attributes('-alpha', alpha)
                        root.update()
                        time.sleep(0.02)
                except:
                    pass

            # 运行窗口（阻塞当前线程）
            root.mainloop()

        except Exception as e:
            print(f"[WarningAlert] Tkinter窗口运行错误: {e}")
            import traceback
            traceback.print_exc()

    def _darken_color(self, hex_color, percent=20):
        """使颜色变暗"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

            r = int(r * (100 - percent) / 100)
            g = int(g * (100 - percent) / 100)
            b = int(b * (100 - percent) / 100)

            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color

    def show_settings_dialog(self, e=None):
        """显示设置对话框"""
        config = self.default_config

        # 创建输入字段
        title_field = ft.TextField(
            label="警告标题",
            value=config['title'],
            multiline=False,
            width=500,
        )

        content_field = ft.TextField(
            label="警告内容",
            value=config['content'],
            multiline=True,
            min_lines=5,
            max_lines=8,
            width=500,
        )

        # 窗口大小
        window_size_dropdown = ft.Dropdown(
            label="窗口大小预设",
            options=[
                ft.dropdown.Option("small", "小 (500x350)"),
                ft.dropdown.Option("medium", "中 (600x400)"),
                ft.dropdown.Option("large", "大 (700x450)"),
                ft.dropdown.Option("xlarge", "超大 (800x500)"),
            ],
            value=config['window_size'],
            width=240,
        )

        # 警告级别
        warning_level_dropdown = ft.Dropdown(
            label="警告级别",
            options=[
                ft.dropdown.Option("info", "信息 ℹ️"),
                ft.dropdown.Option("warning", "警告 ⚠️"),
                ft.dropdown.Option("error", "错误 ❌"),
                ft.dropdown.Option("success", "成功 ✅"),
                ft.dropdown.Option("critical", "严重 🚨"),
            ],
            value=config['warning_level'],
            width=240,
        )

        # 颜色选择
        bgcolor_options = [
            ft.dropdown.Option("red", "红色"),
            ft.dropdown.Option("orange", "橙色"),
            ft.dropdown.Option("yellow", "黄色"),
            ft.dropdown.Option("blue", "蓝色"),
            ft.dropdown.Option("green", "绿色"),
            ft.dropdown.Option("purple", "紫色"),
            ft.dropdown.Option("grey", "灰色"),
        ]

        title_color_options = [
            ft.dropdown.Option("red_800", "深红"),
            ft.dropdown.Option("orange_800", "深橙"),
            ft.dropdown.Option("blue_800", "深蓝"),
            ft.dropdown.Option("green_800", "深绿"),
            ft.dropdown.Option("purple_800", "深紫"),
            ft.dropdown.Option("grey_800", "深灰"),
        ]

        bgcolor_dropdown = ft.Dropdown(
            label="背景颜色",
            options=bgcolor_options,
            value=config['bgcolor'],
            width=240,
        )

        title_color_dropdown = ft.Dropdown(
            label="标题颜色",
            options=title_color_options,
            value=config['title_color'],
            width=240,
        )

        # 按钮文本
        button_text_field = ft.TextField(
            label="按钮文本",
            value=config['button_text'],
            width=240,
        )

        # 开关选项
        show_icon_switch = ft.Switch(
            label="显示图标",
            value=config['show_icon'],
        )

        enable_animation_switch = ft.Switch(
            label="启用动画",
            value=config['enable_animation'],
        )

        always_on_top_switch = ft.Switch(
            label="总是置顶",
            value=config['always_on_top'],
        )

        auto_close_switch = ft.Switch(
            label="自动关闭",
            value=config['auto_close'],
        )

        auto_close_seconds_field = ft.TextField(
            label="自动关闭时间（秒）",
            value=str(config['auto_close_seconds']),
            width=150,
            visible=config['auto_close'],
        )

        window_opacity_slider = ft.Slider(
            label="窗口透明度",
            min=0.3,
            max=1.0,
            value=config['window_opacity'],
            divisions=7,
        )

        # 字体大小
        title_size_slider = ft.Slider(
            label="标题大小",
            min=20,
            max=48,
            value=config['title_size'],
            divisions=7,
        )

        content_size_slider = ft.Slider(
            label="内容大小",
            min=12,
            max=24,
            value=config['content_size'],
            divisions=6,
        )

        icon_size_slider = ft.Slider(
            label="图标大小",
            min=32,
            max=64,
            value=config['icon_size'],
            divisions=4,
        )

        # 循环弹窗控件
        enable_loop_switch = ft.Switch(
            label="启用循环弹窗",
            value=config.get('enable_loop', False),
        )

        loop_interval_field = ft.TextField(
            label="间隔时间",
            value=str(config.get('loop_interval', 60)),
            width=100,
            visible=config.get('enable_loop', False),
        )

        def on_enable_loop_change(e):
            """循环弹窗开关变化"""
            loop_interval_field.visible = e.control.value
            self.page.update()

        enable_loop_switch.on_change = on_enable_loop_change

        def save_settings(e):
            """保存设置"""
            # 窗口大小映射
            size_map = {
                "small": (500, 350),
                "medium": (600, 400),
                "large": (700, 450),
                "xlarge": (800, 500),
            }

            width, height = size_map.get(window_size_dropdown.value, (700, 450))

            new_config = {
                "title": title_field.value,
                "content": content_field.value,
                "window_size": window_size_dropdown.value,
                "window_width": width,
                "window_height": height,
                "warning_level": warning_level_dropdown.value,
                "bgcolor": bgcolor_dropdown.value,
                "title_color": title_color_dropdown.value,
                "show_icon": show_icon_switch.value,
                "icon_type": "unicode",
                "icon_size": int(icon_size_slider.value),
                "font_family": "Microsoft YaHei",
                "title_size": int(title_size_slider.value),
                "content_size": int(content_size_slider.value),
                "button_text": button_text_field.value,
                "button_style": "modern",
                "enable_sound": False,
                "auto_close": auto_close_switch.value,
                "auto_close_seconds": int(auto_close_seconds_field.value) if auto_close_switch.value else 10,
                "enable_animation": enable_animation_switch.value,
                "window_opacity": window_opacity_slider.value,
                "always_on_top": always_on_top_switch.value,
                "enable_escape": True,
                "theme_preset": "default",
                "enable_loop": enable_loop_switch.value,
                "loop_interval": int(loop_interval_field.value) if loop_interval_field.value else 60,
            }

            # 保存到文件
            self.save_config(new_config)

            # 关闭设置对话框
            settings_dialog.open = False
            self.page.update()

            # 显示成功提示
            self.page.snack_bar = ft.SnackBar(
                ft.Text("设置已保存！"),
                bgcolor=ft.Colors.GREEN,
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()

        def on_auto_close_change(e):
            """自动关闭开关变化"""
            auto_close_seconds_field.visible = e.control.value
            self.page.update()

        auto_close_switch.on_change = on_auto_close_change

        # 创建设置对话框（优化布局，使用卡片分组）
        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.BLUE, size=32),
                    ft.Text("警告提示器设置", size=24, weight=ft.FontWeight.BOLD),
                ],
                spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        # 基本设置卡片
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE, size=20),
                                                ft.Text("基本设置", size=16, weight=ft.FontWeight.BOLD),
                                            ],
                                            spacing=10,
                                        ),
                                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                        title_field,
                                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                        content_field,
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                window_size_dropdown,
                                                ft.Container(width=20),
                                                warning_level_dropdown,
                                            ],
                                            spacing=0,
                                        ),
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                bgcolor_dropdown,
                                                ft.Container(width=20),
                                                title_color_dropdown,
                                            ],
                                            spacing=0,
                                        ),
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        button_text_field,
                                    ],
                                    spacing=0,
                                ),
                                padding=20,
                            ),
                            elevation=1,
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

                        # 外观样式卡片
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Icon(ft.Icons.PALETTE, color=ft.Colors.PURPLE, size=20),
                                                ft.Text("外观样式", size=16, weight=ft.FontWeight.BOLD),
                                            ],
                                            spacing=10,
                                        ),
                                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                show_icon_switch,
                                                ft.Container(width=40),
                                                enable_animation_switch,
                                            ],
                                            spacing=0,
                                        ),
                                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                        ft.Text("字体大小", size=14, color=ft.Colors.GREY_700),
                                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                        title_size_slider,
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        ft.Text("内容大小", size=14, color=ft.Colors.GREY_700),
                                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                        content_size_slider,
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        ft.Text("图标大小", size=14, color=ft.Colors.GREY_700),
                                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                        icon_size_slider,
                                    ],
                                    spacing=0,
                                ),
                                padding=20,
                            ),
                            elevation=1,
                        ),
                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

                        # 高级选项卡片
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Icon(ft.Icons.TUNE, color=ft.Colors.GREEN, size=20),
                                                ft.Text("高级选项", size=16, weight=ft.FontWeight.BOLD),
                                            ],
                                            spacing=10,
                                        ),
                                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                always_on_top_switch,
                                                ft.Container(width=40),
                                                auto_close_switch,
                                            ],
                                            spacing=0,
                                        ),
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                ft.Text("自动关闭时间：", size=14),
                                                ft.Container(width=10),
                                                auto_close_seconds_field,
                                            ],
                                            visible=config['auto_close'],
                                        ),
                                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                        ft.Text("窗口透明度", size=14, color=ft.Colors.GREY_700),
                                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                        window_opacity_slider,
                                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                        ft.Text("循环弹窗", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                enable_loop_switch,
                                            ],
                                        ),
                                        ft.Text(
                                            "启用后会在窗口关闭后自动重新弹出警告窗口",
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        ),
                                        ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                                        ft.Row(
                                            [
                                                ft.Text("循环间隔（秒）：", size=14),
                                                ft.Container(width=10),
                                                loop_interval_field,
                                            ],
                                        ),
                                    ],
                                    spacing=0,
                                ),
                                padding=20,
                            ),
                            elevation=1,
                        ),
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=0,
                ),
                width=700,
                height=600,
            ),
            actions=[
                ft.Row(
                    [
                        ft.TextButton(
                            "取消",
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=25, vertical=12),
                            ),
                            on_click=lambda e: self._close_settings_dialog(settings_dialog),
                        ),
                        ft.Button(
                            "保存设置",
                            icon=ft.Icons.SAVE,
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=8),
                                padding=ft.Padding.symmetric(horizontal=35, vertical=15),
                            ),
                            on_click=save_settings,
                        ),
                    ],
                    spacing=25,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            actions_padding=25,
            bgcolor=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            elevation=10,
        )

        # 显示对话框（独立于主界面，自动居中显示）
        self.page.show_dialog(settings_dialog)

    def _close_settings_dialog(self, dialog):
        """关闭设置对话框"""
        dialog.open = False
        self.page.update()

    def reset_config(self, e):
        """重置配置为默认值"""
        try:
            self.context.set_plugin_config("settings", {})

            # 重置为默认配置
            self.default_config = {
                "title": "⚠️ 重要警告",
                "content": "这是一条重要的警告信息！\n\n请注意仔细阅读相关内容。",
                "window_size": "large",
                "window_width": 700,
                "window_height": 450,
                "warning_level": "warning",
                "bgcolor": "red",
                "title_color": "red_800",
                "show_icon": True,
                "icon_type": "unicode",
                "icon_size": 48,
                "font_family": "Microsoft YaHei",
                "title_size": 32,
                "content_size": 16,
                "button_text": "✓ 我知道了",
                "button_style": "modern",
                "enable_sound": False,
                "auto_close": False,
                "auto_close_seconds": 10,
                "enable_animation": True,
                "window_opacity": 1.0,
                "always_on_top": True,
                "enable_escape": True,
                "theme_preset": "default",
                "enable_loop": False,
                "loop_interval": 60,
            }

            # 显示提示
            self.page.snack_bar = ft.SnackBar(
                ft.Text("配置已重置为默认值！"),
                bgcolor=ft.Colors.ORANGE,
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()

        except Exception as ex:
            print(f"[WarningAlert] 重置配置失败: {ex}")
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"重置配置失败: {str(ex)}"),
                bgcolor=ft.Colors.RED,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def export_config(self, e):
        """导出配置到文件"""
        try:
            from tkinter import filedialog
            import tkinter as tk

            # 创建隐藏的tkinter窗口
            root = tk.Tk()
            root.withdraw()

            # 选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="导出配置文件",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile="warning_config_export.json"
            )

            root.destroy()

            if file_path:
                # 保存配置到指定位置
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.default_config, f, ensure_ascii=False, indent=2)

                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"配置已导出到：{file_path}"),
                    bgcolor=ft.Colors.GREEN,
                    duration=3000,
                )
                self.page.snack_bar.open = True
                self.page.update()

        except Exception as ex:
            print(f"[WarningAlert] 导出配置失败: {ex}")
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"导出配置失败: {str(ex)}"),
                bgcolor=ft.Colors.RED,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def import_config(self, e):
        """从文件导入配置"""
        try:
            from tkinter import filedialog
            import tkinter as tk

            # 创建隐藏的tkinter窗口
            root = tk.Tk()
            root.withdraw()

            # 选择文件
            file_path = filedialog.askopenfilename(
                title="导入配置文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )

            root.destroy()

            if file_path:
                # 加载配置文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)

                # 保存到插件配置文件
                self.save_config(imported_config)

                self.page.snack_bar = ft.SnackBar(
                    ft.Text("配置导入成功！"),
                    bgcolor=ft.Colors.GREEN,
                    duration=2000,
                )
                self.page.snack_bar.open = True
                self.page.update()

        except Exception as ex:
            print(f"[WarningAlert] 导入配置失败: {ex}")
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"导入配置失败: {str(ex)}"),
                bgcolor=ft.Colors.RED,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def get_content(self) -> ft.Control:
        """
        获取插件UI内容

        Returns:
            ft.Control: 插件的根控件
        """
        config = self.default_config

        self.main_content = ft.Container(
            content=ft.Column(
                [
                    # 标题区域
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.WARNING,
                                size=40,
                                color=ft.Colors.RED,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "警告提示器",
                                        size=28,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.RED_800,
                                    ),
                                    ft.Text(
                                        "创建完全独立的警告窗口，不受主界面影响",
                                        size=14,
                                        color=ft.Colors.GREY_600,
                                    ),
                                ],
                                spacing=5,
                            ),
                        ],
                        spacing=15,
                    ),
                    ft.Divider(height=30, color=ft.Colors.TRANSPARENT),

                    # 预览卡片
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.PREVIEW,
                                                color=ft.Colors.BLUE,
                                            ),
                                            ft.Text(
                                                "当前警告配置",
                                                size=18,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                    ft.Text(
                                        f"标题: {config['title']}",
                                        size=14,
                                    ),
                                    ft.Text(
                                        f"级别: {config['warning_level'].upper()}",
                                        size=14,
                                    ),
                                    ft.Text(
                                        f"内容: {config['content'][:50]}{'...' if len(config['content']) > 50 else ''}",
                                        size=14,
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Text(
                                        f"大小: {config['window_width']}x{config['window_height']}",
                                        size=14,
                                    ),
                                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.LOOP,
                                                color=ft.Colors.ORANGE if self.is_loop_running else ft.Colors.GREY,
                                            ),
                                            ft.Text(
                                                f"循环状态: {'运行中' if self.is_loop_running else '未启动'}",
                                                size=14,
                                                color=ft.Colors.ORANGE if self.is_loop_running else ft.Colors.GREY,
                                            ),
                                        ],
                                        spacing=5,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                spacing=5,
                            ),
                            padding=20,
                        ),
                        elevation=2,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                    # 操作按钮区域
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Button(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.OPEN_IN_NEW, color=ft.Colors.WHITE),
                                                ft.Text("打开独立警告窗口", color=ft.Colors.WHITE),
                                            ],
                                            spacing=10,
                                        ),
                                        bgcolor=ft.Colors.RED,
                                        color=ft.Colors.WHITE,
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            padding=ft.Padding.symmetric(horizontal=30, vertical=15),
                                        ),
                                        on_click=self.show_warning_dialog,
                                        tooltip="打开完全独立的警告窗口",
                                    ),
                                    ft.Button(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.TUNE),
                                                ft.Text("高级设置"),
                                            ],
                                            spacing=10,
                                        ),
                                        bgcolor=ft.Colors.BLUE_50,
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                            padding=ft.Padding.symmetric(horizontal=30, vertical=15),
                                        ),
                                        on_click=self.show_settings_dialog,
                                    ),
                                ],
                                spacing=20,
                            ),

                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),

                            # 配置管理按钮
                            ft.Row(
                                [
                                    ft.TextButton(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.REFRESH, size=16),
                                                ft.Text("重置配置"),
                                            ],
                                            spacing=5,
                                        ),
                                        on_click=self.reset_config,
                                        tooltip="恢复为默认配置",
                                    ),
                                    ft.TextButton(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.FILE_UPLOAD, size=16),
                                                ft.Text("导出配置"),
                                            ],
                                            spacing=5,
                                        ),
                                        on_click=self.export_config,
                                        tooltip="导出配置到文件",
                                    ),
                                    ft.TextButton(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.FILE_DOWNLOAD, size=16),
                                                ft.Text("导入配置"),
                                            ],
                                            spacing=5,
                                        ),
                                        on_click=self.import_config,
                                        tooltip="从文件导入配置",
                                    ),
                                    ft.Container(
                                        width=1,
                                        height=20,
                                        bgcolor=ft.Colors.GREY_300,
                                    ),
                                    ft.TextButton(
                                        content=ft.Row(
                                            [
                                                ft.Icon(ft.Icons.STOP, size=16),
                                                ft.Text("停止循环"),
                                            ],
                                            spacing=5,
                                        ),
                                        on_click=self.stop_loop,
                                        tooltip="停止循环弹窗",
                                    ),
                                ],
                                spacing=10,
                            ),
                        ],
                        spacing=0,
                    ),

                    ft.Divider(height=30, color=ft.Colors.TRANSPARENT),

                    # 说明区域
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.INFO_OUTLINE,
                                                color=ft.Colors.BLUE,
                                            ),
                                            ft.Text(
                                                "功能特性",
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                    ft.Text(
                                        "✓ 完全独立的窗口，不影响主界面",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "✓ 可在屏幕上自由移动",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "✓ 5种警告级别，7种颜色主题",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "✓ 支持自动关闭和倒计时",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "✓ 淡入动画效果，可调透明度",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "✓ 可自定义字体大小和窗口尺寸",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "✓ 循环弹窗功能，定时重复提醒",
                                        size=13,
                                        color=ft.Colors.RED_700 if self.default_config.get('enable_loop') else None,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                spacing=5,
                            ),
                            padding=20,
                            bgcolor=ft.Colors.BLUE_50,
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

        return self.main_content

    def cleanup(self):
        """插件卸载时停止循环弹窗。"""
        self.stop_loop()


def create_view(page, context):
    """
    创建警告提示器的 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 警告提示器的根控件
    """
    plugin = WarningAlertPlugin(page, context)
    if hasattr(context, "register_resource"):
        context.register_resource(plugin)
    return plugin.get_content()
