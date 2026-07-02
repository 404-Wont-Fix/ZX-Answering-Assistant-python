"""
WeBan Plugin UI - 安全微伴插件界面

提供安全微伴插件的用户界面
"""

import flet as ft

from .weban_view import WeBanView


def create_view(page, context):
    """
    创建安全微伴的 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 安全微伴的根控件
    """
    # 创建WeBan视图（使用插件内部版本）
    view = WeBanView(page, settings_manager=context.settings_manager, context=context)
    if hasattr(context, "register_resource"):
        context.register_resource(view)
    return view.get_content()
