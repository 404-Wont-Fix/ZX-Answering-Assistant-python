"""
懒狗一键评分插件 UI 模块

提供产教融合项目自动评分的 UI 组件
"""

import flet as ft

from .view import LazyAIGradingView


def create_view(page: ft.Page, context):
    """
    创建懒狗一键评分的 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 插件的根控件
    """
    view = LazyAIGradingView(page, main_app=None, context=context)
    if hasattr(context, "register_resource"):
        context.register_resource(view)
    return view.get_content()
