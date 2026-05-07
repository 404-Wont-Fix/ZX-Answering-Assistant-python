"""
独立警告窗口 - 使用Tkinter实现

使用tkinter创建完全独立的警告窗口
"""

import tkinter as tk
from tkinter import font
import json
from pathlib import Path
import sys


def show_warning_window():
    """显示独立警告窗口"""

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
            print(f"加载配置失败: {e}")

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
    root.attributes('-toolwindow', False)  # 不显示在任务栏

    # 禁用最大化按钮
    root.attributes('-fullscreen', False)

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

    # 运行窗口
    root.mainloop()


if __name__ == "__main__":
    show_warning_window()
