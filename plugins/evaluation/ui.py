"""
评估出题插件 UI 模块

提供评估出题的 UI 组件
"""

import flet as ft

from src.ui.views.evaluation_view import EvaluationView


def create_view(page, context):
    """
    创建评估出题的 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 评估出题的根控件
    """
    # 创建评估出题视图（适配插件系统）
    view = EvaluationView(page)
    if hasattr(context, "register_resource"):
        context.register_resource(view)
    return view.get_content()
