"""
警告提示器插件 UI 模块

提供自定义警告提示的 UI 组件
"""

import flet as ft
import json
import sys
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


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

        # 默认警告配置
        self.default_title = "⚠️ 重要警告"
        self.default_content = "这是一条重要的警告信息！\n\n请注意仔细阅读相关内容。"
        self.default_bgcolor = ft.Colors.RED_50
        self.default_title_color = ft.Colors.RED_800

        # 加载保存的配置
        self.load_config()

    def load_config(self):
        """加载保存的警告配置"""
        config_file = Path(__file__).parent / "warning_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.default_title = config.get('title', self.default_title)
                    self.default_content = config.get('content', self.default_content)
                    # 恢复颜色（从字符串转换）
                    if 'bgcolor' in config:
                        self.default_bgcolor = config['bgcolor']
                    if 'title_color' in config:
                        self.default_title_color = config['title_color']
            except Exception as e:
                print(f"[WarningAlert] 加载配置失败: {e}")

    def save_config(self, title, content, bgcolor_name, title_color_name):
        """保存警告配置"""
        config_file = Path(__file__).parent / "warning_config.json"
        try:
            config = {
                'title': title,
                'content': content,
                'bgcolor': bgcolor_name,
                'title_color': title_color_name
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"[WarningAlert] 配置已保存")
        except Exception as e:
            print(f"[WarningAlert] 保存配置失败: {e}")

    def show_warning_dialog(self, e=None):
        """显示独立警告窗口 - 使用Tkinter在独立线程中运行"""
        try:
            # 在新线程中运行tkinter窗口，避免阻塞Flet UI
            warning_thread = threading.Thread(
                target=self._run_tkinter_window,
                daemon=True
            )
            warning_thread.start()

            print(f"[WarningAlert] Tkinter警告窗口已启动")

            # 显示提示
            self.page.snack_bar = ft.SnackBar(
                ft.Text("警告窗口已打开！"),
                bgcolor=ft.Colors.GREEN,
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()

        except Exception as ex:
            print(f"[WarningAlert] 启动警告窗口失败: {ex}")
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"启动警告窗口失败: {str(ex)}"),
                bgcolor=ft.Colors.RED,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _run_tkinter_window(self):
        """在线程中运行Tkinter窗口"""
        try:
            import tkinter as tk
            from tkinter import font
            from pathlib import Path

            # 加载配置
            config_file = Path(__file__).parent / "warning_config.json"
            default_title = "⚠️ 重要警告"
            default_content = "这是一条重要的警告信息！\n\n请注意仔细阅读相关内容。"
            bg_color = "#FFEBEE"  # 红色背景
            title_color = "#C62828"  # 深红色标题
            button_color = "#F44336"  # 按钮红色

            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        default_title = config.get('title', default_title)
                        default_content = config.get('content', default_content)
                        bgcolor_name = config.get('bgcolor', 'red')
                        title_color_name = config.get('title_color', 'red_800')

                        # 颜色映射
                        color_map = {
                            "red": "#FFEBEE",  # RED_50
                            "orange": "#FFF3E0",  # ORANGE_50
                            "yellow": "#FFFDE7",  # YELLOW_50
                            "blue": "#E3F2FD",  # BLUE_50
                        }

                        title_color_map = {
                            "red_800": "#C62828",
                            "orange_800": "#E65100",
                            "blue_800": "#1565C0",
                        }

                        bg_color = color_map.get(bgcolor_name, bg_color)
                        title_color = title_color_map.get(title_color_name, title_color)
                except Exception as e:
                    print(f"[WarningAlert] 加载配置失败: {e}")

            # 创建主窗口
            root = tk.Tk()
            root.title("警告提示")

            # 设置窗口大小和居中
            window_width = 700
            window_height = 450
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            root.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # 设置窗口不可调整大小
            root.resizable(False, False)

            # 设置窗口总是在最前面
            root.attributes('-topmost', True)

            # 设置背景颜色
            root.configure(bg=bg_color)

            # 创建字体
            title_font = font.Font(family="Microsoft YaHei", size=32, weight="bold")
            content_font = font.Font(family="Microsoft YaHei", size=16)
            button_font = font.Font(family="Microsoft YaHei", size=14, weight="bold")

            # 主容器
            main_frame = tk.Frame(root, bg=bg_color, padx=30, pady=30)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # 标题区域
            title_frame = tk.Frame(main_frame, bg=bg_color)
            title_frame.pack(fill=tk.X, pady=(0, 20))

            # 警告图标（使用Unicode字符）
            icon_label = tk.Label(
                title_frame,
                text="⚠️",
                font=("Segoe UI Emoji", 48),
                bg=bg_color,
                fg=title_color
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 20))

            # 标题文本
            title_label = tk.Label(
                title_frame,
                text=default_title,
                font=title_font,
                bg=bg_color,
                fg=title_color
            )
            title_label.pack(side=tk.LEFT)

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
                text=default_content,
                font=content_font,
                bg="white",
                fg="#B71C1C",
                justify=tk.CENTER,
                wraplength=600
            )
            content_label.pack(expand=True)

            # 按钮区域
            button_frame = tk.Frame(main_frame, bg=bg_color)
            button_frame.pack(fill=tk.X)

            def close_window():
                """关闭窗口"""
                root.destroy()

            # 关闭按钮
            close_button = tk.Button(
                button_frame,
                text="✓ 我知道了",
                font=button_font,
                bg=button_color,
                fg="white",
                activebackground="#D32F2F",
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

            # 添加按钮悬停效果
            def on_enter(e):
                close_button.config(bg="#D32F2F")

            def on_leave(e):
                close_button.config(bg=button_color)

            close_button.bind('<Enter>', on_enter)
            close_button.bind('<Leave>', on_leave)

            # 绑定ESC键关闭
            root.bind('<Escape>', lambda e: close_window())

            # 设置窗口焦点到关闭按钮
            close_button.focus_set()

            # 运行窗口（阻塞当前线程）
            root.mainloop()

        except Exception as e:
            print(f"[WarningAlert] Tkinter窗口运行错误: {e}")
            import traceback
            traceback.print_exc()

    def show_settings_dialog(self, e=None):
        """显示设置对话框"""
        # 创建输入字段
        title_field = ft.TextField(
            label="警告标题",
            value=self.default_title,
            multiline=False,
            width=500,
        )

        content_field = ft.TextField(
            label="警告内容",
            value=self.default_content,
            multiline=True,
            min_lines=5,
            max_lines=8,
            width=500,
        )

        # 颜色选择
        bgcolor_options = [
            ft.dropdown.Option("red", "红色"),
            ft.dropdown.Option("orange", "橙色"),
            ft.dropdown.Option("yellow", "黄色"),
            ft.dropdown.Option("blue", "蓝色"),
        ]

        title_color_options = [
            ft.dropdown.Option("red_800", "深红"),
            ft.dropdown.Option("orange_800", "深橙"),
            ft.dropdown.Option("blue_800", "深蓝"),
        ]

        bgcolor_dropdown = ft.Dropdown(
            label="背景颜色",
            options=bgcolor_options,
            value=self._color_to_name(self.default_bgcolor),
            width=240,
        )

        title_color_dropdown = ft.Dropdown(
            label="标题颜色",
            options=title_color_options,
            value=self._color_to_name(self.default_title_color),
            width=240,
        )

        def save_settings(e):
            """保存设置"""
            new_title = title_field.value
            new_content = content_field.value
            new_bgcolor = bgcolor_dropdown.value
            new_title_color = title_color_dropdown.value

            # 转换颜色名称到Flet颜色
            color_map = {
                "red": ft.Colors.RED_50,
                "orange": ft.Colors.ORANGE_50,
                "yellow": ft.Colors.YELLOW_50,
                "blue": ft.Colors.BLUE_50,
            }

            title_color_map = {
                "red_800": ft.Colors.RED_800,
                "orange_800": ft.Colors.ORANGE_800,
                "blue_800": ft.Colors.BLUE_800,
            }

            self.default_title = new_title
            self.default_content = new_content
            self.default_bgcolor = color_map.get(new_bgcolor, ft.Colors.RED_50)
            self.default_title_color = title_color_map.get(new_title_color, ft.Colors.RED_800)

            # 保存到文件
            self.save_config(new_title, new_content, new_bgcolor, new_title_color)

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

        # 创建设置对话框（独立屏幕中央显示）
        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.BLUE, size=32),
                    ft.Text("自定义警告设置", size=24, weight=ft.FontWeight.BOLD),
                ],
                spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        title_field,
                        content_field,
                        ft.Text("选择颜色方案：", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        ft.Row(
                            [
                                bgcolor_dropdown,
                                title_color_dropdown,
                            ],
                            spacing=20,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    spacing=15,
                ),
                width=600,
                height=500,
                padding=20,
            ),
            actions=[
                ft.Row(
                    [
                        ft.TextButton(
                            "取消",
                            style=ft.ButtonStyle(
                                padding=ft.Padding.symmetric(horizontal=20, vertical=10),
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
                                padding=ft.Padding.symmetric(horizontal=30, vertical=12),
                            ),
                            on_click=save_settings,
                        ),
                    ],
                    spacing=20,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            actions_padding=20,
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

    def _color_to_name(self, color):
        """将Flet颜色对象转换为名称"""
        color_map = {
            ft.Colors.RED_50: "red",
            ft.Colors.ORANGE_50: "orange",
            ft.Colors.YELLOW_50: "yellow",
            ft.Colors.BLUE_50: "blue",
        }

        for c, name in color_map.items():
            if color == c:
                return name
        return "red"

    def get_content(self) -> ft.Control:
        """
        获取插件UI内容

        Returns:
            ft.Control: 插件的根控件
        """
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
                                        f"标题: {self.default_title}",
                                        size=14,
                                    ),
                                    ft.Text(
                                        f"内容: {self.default_content[:50]}{'...' if len(self.default_content) > 50 else ''}",
                                        size=14,
                                        color=ft.Colors.GREY_700,
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
                                        ft.Icon(ft.Icons.SETTINGS),
                                        ft.Text("自定义设置"),
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
                                                "使用说明",
                                                size=16,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                    ft.Text(
                                        "1. 点击「打开独立警告窗口」会启动完全独立的新窗口",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "2. 独立窗口可以在屏幕上自由移动，不影响主界面",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "3. 点击「自定义设置」可以修改警告标题、内容和样式",
                                        size=13,
                                    ),
                                    ft.Text(
                                        "4. 设置会自动保存，下次打开时使用上次保存的配置",
                                        size=13,
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
    return plugin.get_content()
