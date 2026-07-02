"""
课程认证插件 UI 模块

提供插件的用户界面组件
"""

import flet as ft

from src.ui.views.course_certification_view import CourseCertificationView


def create_view(page, context):
    """
    创建插件的 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例，包含注入的依赖

    Returns:
        ft.Control: 插件的根控件
    """
    # 创建课程认证视图（适配插件系统）
    view = CourseCertificationView(page, main_app=None)
    if hasattr(context, "register_resource"):
        context.register_resource(view)
    return view.get_content()
