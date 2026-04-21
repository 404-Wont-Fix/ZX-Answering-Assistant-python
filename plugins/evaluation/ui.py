"""
评估出题插件 UI 模块

提供评估出题的 UI 组件
"""

import flet as ft
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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
    return view.get_content()
