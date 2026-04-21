"""
WeBan Plugin UI - 安全微伴插件界面

提供安全微伴插件的用户界面
"""

import flet as ft
import sys
from pathlib import Path

# 添加插件lib目录到Python路径
plugin_lib_path = Path(__file__).parent / "lib"
if str(plugin_lib_path) not in sys.path:
    sys.path.insert(0, str(plugin_lib_path))

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入插件内部的 WeBanView
from weban_view import WeBanView


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
    view = WeBanView(page)
    return view.get_content()
