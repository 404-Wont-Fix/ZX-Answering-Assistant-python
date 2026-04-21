"""
测试插件中心视图

验证插件中心能否正确显示已扫描的插件
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.plugin_manager import get_plugin_manager


class MockPage:
    """模拟 Flet Page 对象"""
    def show_dialog(self, dialog):
        print(f"[MockPage] Would show dialog: {dialog}")

    def show_snack_bar(self, snack_bar):
        print(f"[MockPage] Would show snack bar: {snack_bar}")

    def update(self):
        print("[MockPage] Page updated")


class MockMainApp:
    """模拟 MainApp 对象"""
    def __init__(self):
        # 初始化插件管理器
        self.plugin_manager = get_plugin_manager()

        # 扫描插件
        plugins_dir = Path('plugins')
        count = self.plugin_manager.scan_plugins(plugins_dir)

        print(f"\n[MockMainApp] Plugin system initialized")
        print(f"[MockMainApp] Found {count} plugins")


def test_plugin_center():
    """测试插件中心视图"""
    print("=" * 60)
    print("Testing PluginCenterView")
    print("=" * 60)

    # 1. 创建模拟 MainApp
    main_app = MockMainApp()

    # 2. 创建模拟 Page
    page = MockPage()

    # 3. 导入 PluginCenterView
    from src.ui.views.plugin_center_view import PluginCenterView

    # 4. 创建插件中心视图
    plugin_center_view = PluginCenterView(page, main_app=main_app)

    # 5. 获取内容
    content = plugin_center_view.get_content()

    # 6. 验证结果
    print(f"\n[Test Result] PluginCenterView created successfully")
    print(f"[Test Result] Content type: {type(content).__name__}")

    # 检查是否是占位符
    if len(content.controls) > 0:
        first_control = content.controls[0]
        if hasattr(first_control, 'content'):
            inner_content = first_control.content
            if hasattr(inner_content, 'controls'):
                # 检查是否显示插件列表或占位符
                text_controls = [c for c in inner_content.controls if hasattr(c, 'value')]
                for text in text_controls:
                    if '发现' in str(text.value) or '个插件' in str(text.value):
                        print(f"[Test Result] Plugin list detected: {text.value}")
                        return True
                print("[Test Result] Placeholder content (no plugins listed)")
                return False
    else:
        print("[Test Result] Empty content")
        return False


if __name__ == "__main__":
    success = test_plugin_center()
    if success:
        print("\n" + "=" * 60)
        print("✅ Plugin center test PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Plugin center test FAILED")
        print("=" * 60)
        sys.exit(1)
