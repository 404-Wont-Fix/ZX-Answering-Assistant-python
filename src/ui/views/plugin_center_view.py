"""
插件中心视图模块

此模块提供插件中心的 UI，显示可用插件并允许启用/禁用
"""

import flet as ft
from typing import Optional


class PluginCenterView:
    """插件中心视图类"""

    def __init__(self, page: ft.Page, main_app=None):
        """
        初始化插件中心视图

        Args:
            page (ft.Page): Flet页面对象
            main_app: MainApp实例（用于获取插件管理器）
        """
        self.page = page
        self.main_app = main_app
        self.content = None
        self.current_dialog = None
        self.current_view = "enabled"  # 当前视图：enabled 或 management
        self.cached_plugin_content = {}  # 缓存不同视图的内容
        self.current_plugin_ui = None  # 当前打开的插件UI
        self.is_showing_plugin = False  # 是否正在显示插件UI

    def get_content(self) -> ft.Control:
        """
        获取插件中心页面内容

        Returns:
            ft.Control: 插件中心页面的根控件
        """
        # 获取插件管理器
        if self.main_app and hasattr(self.main_app, 'plugin_manager'):
            plugin_manager = self.main_app.plugin_manager
            all_plugins = plugin_manager.get_all_plugins()

            if all_plugins:
                # 有插件，显示分段按钮界面
                return self._build_segmented_interface(all_plugins)

        # 没有插件或管理器不可用，显示占位符
        return self._build_placeholder()

    def _build_segmented_interface(self, plugins: dict) -> ft.Control:
        """构建分段按钮界面"""
        # 分离已启用和所有插件
        enabled_plugins = {pid: info for pid, info in plugins.items() if info.enabled}
        disabled_plugins = {pid: info for pid, info in plugins.items() if not info.enabled}

        # 创建切换按钮
        toggle_buttons = ft.Row(
            [
                ft.ElevatedButton(
                    content=ft.Text(f"我的插件 ({len(enabled_plugins)})"),
                    bgcolor=ft.Colors.BLUE_100 if self.current_view == "enabled" else None,
                    on_click=self._show_enabled_view,
                ),
                ft.ElevatedButton(
                    content=ft.Text(f"插件管理 ({len(plugins)})"),
                    bgcolor=ft.Colors.BLUE_100 if self.current_view == "management" else None,
                    on_click=self._show_management_view,
                ),
            ],
            spacing=10,
        )

        # 创建内容区域（根据当前选择显示不同内容）
        content_area = ft.Column(
            [
                ft.Column(
                    [self._build_enabled_plugins_view(enabled_plugins)]
                    if self.current_view == "enabled"
                    else [self._build_plugin_management_view(plugins)]
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        return ft.Column(
            [
                ft.Text(
                    "插件中心",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                toggle_buttons,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                content_area,
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            expand=True,
        )

    def _show_enabled_view(self, e):
        """显示已启用插件视图"""
        self.current_view = "enabled"
        if self.main_app and hasattr(self.main_app, 'plugin_manager'):
            plugin_manager = self.main_app.plugin_manager
            plugins = plugin_manager.get_all_plugins()

            # 构建并缓存新内容
            new_content = self._build_segmented_interface(plugins)
            self.cached_plugin_content["enabled"] = new_content

            # 通过 MainApp 的 content_area 更新显示
            if hasattr(self.main_app, 'content_area'):
                self.main_app.content_area.controls[0].content = new_content
                self.page.update()

    def _show_management_view(self, e):
        """显示插件管理视图"""
        self.current_view = "management"
        if self.main_app and hasattr(self.main_app, 'plugin_manager'):
            plugin_manager = self.main_app.plugin_manager
            plugins = plugin_manager.get_all_plugins()

            # 构建并缓存新内容
            new_content = self._build_segmented_interface(plugins)
            self.cached_plugin_content["management"] = new_content

            # 通过 MainApp 的 content_area 更新显示
            if hasattr(self.main_app, 'content_area'):
                self.main_app.content_area.controls[0].content = new_content
                self.page.update()

    def _build_enabled_plugins_view(self, enabled_plugins: dict) -> ft.Control:
        """构建已启用插件视图"""
        if not enabled_plugins:
            return ft.Column(
                [
                    ft.Icon(
                        ft.Icons.POWER_OFF,
                        size=80,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Text(
                        "暂无已启用的插件",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_600,
                    ),
                    ft.Text(
                        "前往 \"插件管理\" 启用插件",
                        size=14,
                        color=ft.Colors.GREY_500,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )

        plugin_cards = []
        for plugin_id, plugin_info in enabled_plugins.items():
            card = self._build_simple_plugin_card(plugin_info)
            plugin_cards.append(card)

        # 创建两列网格布局
        card_rows = []
        for i in range(0, len(plugin_cards), 2):
            row_cards = plugin_cards[i:i+2]
            if len(row_cards) == 2:
                card_rows.append(
                    ft.Row(
                        [
                            ft.Container(content=row_cards[0], expand=True),
                            ft.Container(content=row_cards[1], expand=True),
                        ],
                        spacing=10,
                    )
                )
            else:
                card_rows.append(
                    ft.Row(
                        [
                            ft.Container(content=row_cards[0], expand=True),
                            ft.Container(expand=True),
                        ],
                        spacing=10,
                    )
                )

        return ft.Column(
            [
                ft.Text(
                    f"已启用 {len(enabled_plugins)} 个插件",
                    size=14,
                    color=ft.Colors.GREY_700,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                ft.Column(
                    card_rows,
                    spacing=10,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        )

    def _build_plugin_management_view(self, all_plugins: dict) -> ft.Control:
        """构建插件管理视图"""
        # 按状态分组
        enabled_plugins = {pid: info for pid, info in all_plugins.items() if info.enabled}
        disabled_plugins = {pid: info for pid, info in all_plugins.items() if not info.enabled}

        content = []

        # 添加标题行和打开插件目录按钮
        content.append(
            ft.Row(
                [
                    ft.Text(
                        "插件管理",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "打开插件目录",
                        icon=ft.Icons.FOLDER_OPEN,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=6),
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        ),
                        on_click=self._open_plugin_directory,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )
        content.append(ft.Divider(height=10, color=ft.Colors.TRANSPARENT))

        # 已启用插件部分
        if enabled_plugins:
            content.append(
                ft.Text(
                    f"已启用 ({len(enabled_plugins)})",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREEN_700,
                )
            )
            content.append(ft.Divider(height=8, color=ft.Colors.TRANSPARENT))

            # 创建两列网格布局，每行两个卡片
            card_rows = []
            plugin_cards = []
            for plugin_id, plugin_info in enabled_plugins.items():
                card = self._build_management_card(plugin_info)
                plugin_cards.append(card)

            for i in range(0, len(plugin_cards), 2):
                row_cards = plugin_cards[i:i+2]
                if len(row_cards) == 2:
                    card_rows.append(
                        ft.Row(
                            [
                                ft.Container(content=row_cards[0], expand=True),
                                ft.Container(content=row_cards[1], expand=True),
                            ],
                            spacing=10,
                        )
                    )
                else:
                    card_rows.append(
                        ft.Row(
                            [
                                ft.Container(content=row_cards[0], expand=True),
                                ft.Container(expand=True),
                            ],
                            spacing=10,
                        )
                    )

            content.append(
                ft.Column(
                    card_rows,
                    spacing=10,
                )
            )

        # 已禁用插件部分
        if disabled_plugins:
            if enabled_plugins:
                content.append(ft.Divider(height=15, color=ft.Colors.TRANSPARENT))

            content.append(
                ft.Text(
                    f"已禁用 ({len(disabled_plugins)})",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_600,
                )
            )
            content.append(ft.Divider(height=8, color=ft.Colors.TRANSPARENT))

            # 创建两列网格布局，每行两个卡片
            card_rows = []
            plugin_cards = []
            for plugin_id, plugin_info in disabled_plugins.items():
                card = self._build_management_card(plugin_info)
                plugin_cards.append(card)

            for i in range(0, len(plugin_cards), 2):
                row_cards = plugin_cards[i:i+2]
                if len(row_cards) == 2:
                    card_rows.append(
                        ft.Row(
                            [
                                ft.Container(content=row_cards[0], expand=True),
                                ft.Container(content=row_cards[1], expand=True),
                            ],
                            spacing=10,
                        )
                    )
                else:
                    card_rows.append(
                        ft.Row(
                            [
                                ft.Container(content=row_cards[0], expand=True),
                                ft.Container(expand=True),
                            ],
                            spacing=10,
                        )
                    )

            content.append(
                ft.Column(
                    card_rows,
                    spacing=10,
                )
            )

        return ft.Column(
            content,
            scroll=ft.ScrollMode.AUTO,
        )

    def _build_simple_plugin_card(self, plugin_info) -> ft.Control:
        """构建简单的插件卡片（用于已启用插件视图）"""
        try:
            icon = getattr(ft.Icons, plugin_info.icon.upper(), ft.Icons.EXTENSION)
        except AttributeError:
            icon = ft.Icons.EXTENSION

        return ft.GestureDetector(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        icon,
                                        size=28,
                                        color=ft.Colors.BLUE,
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    plugin_info.name,
                                                    size=14,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(
                                                    plugin_info.description,
                                                    size=11,
                                                    color=ft.Colors.GREY_600,
                                                    max_lines=2,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                ),
                                            ],
                                            spacing=2,
                                        ),
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.INFO_OUTLINE,
                                        tooltip="查看详情",
                                        icon_size=18,
                                        on_click=lambda e, pid=plugin_info.id: self._on_plugin_info(pid),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.LAUNCH,
                                        tooltip="打开插件",
                                        icon_size=18,
                                        on_click=lambda e, pid=plugin_info.id: self._on_plugin_open(pid),
                                    ),
                                ],
                            ),
                        ],
                        spacing=0,
                    ),
                    padding=12,
                ),
                elevation=1,
            ),
            on_tap=lambda e, pid=plugin_info.id: self._on_plugin_open(pid),
            mouse_cursor=ft.MouseCursor.CLICK,
        )

    def _build_management_card(self, plugin_info) -> ft.Control:
        """构建管理卡片（用于插件管理视图）"""
        # 状态标签
        status_text = "已启用" if plugin_info.enabled else "已禁用"
        status_color = ft.Colors.GREEN if plugin_info.enabled else ft.Colors.GREY

        # 确定图标
        try:
            icon = getattr(ft.Icons, plugin_info.icon.upper(), ft.Icons.EXTENSION)
        except AttributeError:
            icon = ft.Icons.EXTENSION

        # 构建卡片内容
        card_content = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    icon,
                                    size=28,
                                    color=ft.Colors.BLUE,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(
                                                plugin_info.name,
                                                size=14,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                f"v{plugin_info.version} · {plugin_info.author}",
                                                size=11,
                                                color=ft.Colors.GREY_600,
                                            ),
                                        ],
                                        spacing=2,
                                    ),
                                    expand=True,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        status_text,
                                        size=10,
                                        color=status_color,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                    padding=ft.padding.symmetric(horizontal=6, vertical=3),
                                    border_radius=6,
                                ),
                            ],
                            alignment=ft.CrossAxisAlignment.START,
                        ),
                        ft.Divider(height=6, color=ft.Colors.TRANSPARENT),
                        ft.Text(
                            plugin_info.description,
                            size=11,
                            color=ft.Colors.GREY_700,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.INFO_OUTLINE,
                                    tooltip="插件详情",
                                    icon_size=18,
                                    on_click=lambda e, pid=plugin_info.id: self._on_plugin_info(pid),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SETTINGS,
                                    tooltip="插件设置",
                                    icon_size=18,
                                    on_click=lambda e, pid=plugin_info.id: self._on_plugin_settings(pid),
                                ),
                                ft.Container(expand=True),  # 占据剩余空间
                                ft.Switch(
                                    value=plugin_info.enabled,
                                    label="启用" if plugin_info.enabled else "禁用",
                                    scale=0.8,
                                    on_change=lambda e, pid=plugin_info.id: self._on_plugin_toggle(e, pid),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    spacing=0,
                ),
                padding=12,
            ),
            elevation=1,
        )

        # 如果插件已启用，添加点击事件打开插件
        if plugin_info.enabled:
            return ft.GestureDetector(
                content=card_content,
                on_tap=lambda e, pid=plugin_info.id: self._on_plugin_open(pid),
                mouse_cursor=ft.MouseCursor.CLICK,
            )
        else:
            return card_content

    def _build_placeholder(self) -> ft.Control:
        """构建占位符内容"""
        return ft.Column(
            [
                ft.Text(
                    "插件中心",
                    size=32,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_800,
                ),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.EXTENSION, size=80, color=ft.Colors.BLUE),
                                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                                ft.Text(
                                    "暂无可用插件",
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "请将插件放在 plugins/ 目录下",
                                    size=16,
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5,
                        ),
                        padding=30,
                        width=500,
                    ),
                    elevation=2,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _open_plugin_directory(self, e):
        """打开插件目录"""
        import subprocess
        import sys
        from pathlib import Path

        # 获取插件目录路径
        project_root = Path(__file__).parent.parent.parent.parent
        plugins_dir = project_root / "plugins"

        # 确保目录存在
        plugins_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 根据操作系统打开文件夹
            if sys.platform == "win32":
                subprocess.run(["explorer", str(plugins_dir)])
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(plugins_dir)])
            else:  # Linux
                subprocess.run(["xdg-open", str(plugins_dir)])

            print(f"[PluginCenter] Opened plugin directory: {plugins_dir}")

            # 显示提示
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"已打开插件目录: {plugins_dir}"),
                bgcolor=ft.Colors.GREEN,
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()

        except Exception as ex:
            print(f"[PluginCenter] Failed to open plugin directory: {ex}")
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"打开插件目录失败: {str(ex)}"),
                bgcolor=ft.Colors.RED,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _on_plugin_settings(self, plugin_id: str):
        """处理插件设置按钮点击"""
        print(f"打开插件设置: {plugin_id}")
        # TODO: 实现插件设置对话框

    def _on_plugin_open(self, plugin_id: str):
        """处理插件卡片点击 - 打开插件UI"""
        if not self.main_app or not hasattr(self.main_app, 'plugin_manager'):
            print("[PluginCenter] MainApp or plugin_manager not available")
            return

        plugin_manager = self.main_app.plugin_manager
        plugin_info = plugin_manager.get_plugin_info(plugin_id)

        if not plugin_info:
            print(f"[PluginCenter] Plugin not found: {plugin_id}")
            return

        if not plugin_info.enabled:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"请先启用插件: {plugin_info.name}"),
                bgcolor=ft.Colors.ORANGE,
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        try:
            from src.core.plugin_context import PluginContext
            from src.core.api_client import get_api_client
            from src.core.browser import get_browser_manager
            from src.core.config import get_settings_manager

            # 创建插件上下文（使用单例）
            context = PluginContext(
                plugin_id=plugin_id,
                api_client=get_api_client(),
                browser_manager=get_browser_manager(),
                settings_manager=get_settings_manager(),
            )

            # 加载插件UI
            plugin_ui = plugin_manager.load_plugin_ui(plugin_id, self.page, context)

            if plugin_ui:
                # 保存当前插件中心视图
                if not self.is_showing_plugin:
                    self.cached_plugin_content["plugin_center"] = self._build_segmented_interface(
                        plugin_manager.get_all_plugins()
                    )

                # 构建插件UI页面（带返回按钮）
                plugin_page = self._build_plugin_page(plugin_info, plugin_ui)

                # 更新显示
                if hasattr(self.main_app, 'content_area'):
                    self.main_app.content_area.controls[0].content = plugin_page
                    self.page.update()

                self.is_showing_plugin = True
                self.current_plugin_ui = plugin_id

                print(f"[PluginCenter] Plugin UI opened: {plugin_id}")
            else:
                self.page.snack_bar = ft.SnackBar(
                    ft.Text(f"无法加载插件UI: {plugin_info.name}"),
                    bgcolor=ft.Colors.RED,
                    duration=2000,
                )
                self.page.snack_bar.open = True
                self.page.update()

        except Exception as e:
            print(f"[PluginCenter] Error opening plugin {plugin_id}: {e}")
            import traceback
            traceback.print_exc()

            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"打开插件失败: {str(e)}"),
                bgcolor=ft.Colors.RED,
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _build_plugin_page(self, plugin_info, plugin_ui) -> ft.Control:
        """构建插件显示页面（带返回按钮）"""
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="返回插件中心",
                            on_click=self._back_to_plugin_center,
                        ),
                        ft.Text(
                            plugin_info.name,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_800,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=plugin_ui,
                    expand=True,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _back_to_plugin_center(self, e):
        """返回插件中心"""
        if not self.main_app:
            return

        plugin_manager = self.main_app.plugin_manager
        plugins = plugin_manager.get_all_plugins()

        # 重新构建插件中心视图
        plugin_center_content = self._build_segmented_interface(plugins)

        # 更新显示
        if hasattr(self.main_app, 'content_area'):
            self.main_app.content_area.controls[0].content = plugin_center_content
            self.page.update()

        self.is_showing_plugin = False
        self.current_plugin_ui = None

        print("[PluginCenter] Returned to plugin center")

    def _on_plugin_info(self, plugin_id: str):
        """处理插件详情按钮点击"""
        if not self.main_app or not hasattr(self.main_app, 'plugin_manager'):
            return

        plugin_manager = self.main_app.plugin_manager
        plugin_info = plugin_manager.get_plugin_info(plugin_id)

        if not plugin_info:
            return

        # 确定图标
        try:
            icon = getattr(ft.Icons, plugin_info.icon.upper(), ft.Icons.EXTENSION)
        except AttributeError:
            icon = ft.Icons.EXTENSION

        # 构建详情列表项
        detail_items = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE),
                title=ft.Text("版本", size=14, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(plugin_info.version, size=12),
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PERSON, color=ft.Colors.GREEN),
                title=ft.Text("作者", size=14, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(plugin_info.author, size=12),
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.DESCRIPTION, color=ft.Colors.ORANGE),
                title=ft.Text("描述", size=14, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(plugin_info.description, size=12),
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.PURPLE),
                title=ft.Text("路径", size=14, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(str(plugin_info.path), size=12),
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN if plugin_info.enabled else ft.Colors.GREY),
                title=ft.Text("状态", size=14, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text("已启用" if plugin_info.enabled else "已禁用", size=12),
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.CODE, color=ft.Colors.BLUE),
                title=ft.Text("UI 入口", size=14, weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(plugin_info.entry_ui, size=12),
            ),
        ]

        # 如果有核心入口，添加到列表
        if plugin_info.entry_core:
            detail_items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.RED),
                    title=ft.Text("核心入口", size=14, weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(plugin_info.entry_core, size=12),
                )
            )

        # 创建详情对话框
        self.current_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(icon, color=ft.Colors.BLUE),
                    ft.Text(plugin_info.name, size=20),
                ],
                spacing=10,
            ),
            content=ft.Container(
                content=ft.Column(
                    detail_items,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    spacing=5,
                ),
                width=500,
                height=400,
            ),
            actions=[
                ft.TextButton("关闭", on_click=self._close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.show_dialog(self.current_dialog)

    def _close_dialog(self, e):
        """关闭对话框"""
        if self.current_dialog:
            self.page.pop_dialog()  # 使用正确的 API
            self.current_dialog = None

    def _on_plugin_toggle(self, e, plugin_id: str):
        """处理插件启用/禁用切换"""
        if not self.main_app or not hasattr(self.main_app, 'plugin_manager'):
            return

        plugin_manager = self.main_app.plugin_manager
        new_state = e.control.value

        if new_state:
            plugin_manager.enable_plugin(plugin_id)
        else:
            plugin_manager.disable_plugin(plugin_id)

        # 清除缓存以强制重新构建
        self.cached_plugin_content.clear()

        # 刷新当前视图
        if self.main_app and hasattr(self.main_app, 'plugin_manager'):
            plugins = plugin_manager.get_all_plugins()
            new_content = self._build_segmented_interface(plugins)

            # 通过 MainApp 的 content_area 更新显示
            if hasattr(self.main_app, 'content_area'):
                self.main_app.content_area.controls[0].content = new_content

        # 显示操作反馈
        self.page.snack_bar = ft.SnackBar(
            ft.Text(
                f"插件 {'已启用' if new_state else '已禁用'}: {plugin_id}",
                color=ft.Colors.WHITE if new_state else ft.Colors.BLACK,
            ),
            bgcolor=ft.Colors.GREEN if new_state else ft.Colors.GREY,
            duration=2000,
        )
        self.page.snack_bar.open = True
        self.page.update()
