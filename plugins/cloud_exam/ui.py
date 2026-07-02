"""
云考试插件 UI 模块

提供云考试的 UI 组件
"""

import flet as ft

from .view import CloudExamView


def create_view(page, context):
    """
    创建云考试的 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 云考试的根控件
    """
    # 创建云考试视图（适配插件系统）
    view = CloudExamView(page, main_app=None, context=context)
    if hasattr(context, "register_resource"):
        context.register_resource(view)
    return view.get_content()
