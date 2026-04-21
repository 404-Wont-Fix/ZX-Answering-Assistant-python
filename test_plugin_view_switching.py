"""
测试插件中心视图切换功能

验证修复后的视图切换机制是否能正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.plugin_manager import get_plugin_manager


class MockContentArea:
    """模拟 MainApp 的 content_area"""
    def __init__(self):
        self.controls = [MockContainer()]

    def update_content(self, new_content):
        """更新内容"""
        self.controls[0].content = new_content
        print(f"[OK] Content updated successfully: {type(new_content).__name__}")


class MockContainer:
    """模拟 Container"""
    def __init__(self):
        self.content = None


class MockPage:
    """模拟 Flet Page 对象"""
    def __init__(self):
        self.snack_bar = None
        self.content_area = MockContentArea()

    def update(self):
        print("[OK] Page updated")

    def show_dialog(self, dialog):
        print(f"[MockPage] Would show dialog")

    def pop_dialog(self):
        print("[MockPage] Dialog closed")


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

        # 模拟 content_area
        self.content_area = MockContentArea()


def test_view_switching():
    """测试视图切换功能"""
    print("=" * 60)
    print("Testing Plugin Center View Switching")
    print("=" * 60)

    # 1. 创建模拟 MainApp
    main_app = MockMainApp()

    # 2. 创建模拟 Page
    page = MockPage()
    page.content_area = main_app.content_area

    # 3. 导入 PluginCenterView
    from src.ui.views.plugin_center_view import PluginCenterView

    # 4. 创建插件中心视图
    plugin_center_view = PluginCenterView(page, main_app=main_app)

    # 5. 测试初始内容构建
    print("\n[Test 1] Building initial content...")
    try:
        initial_content = plugin_center_view.get_content()
        print(f"[OK] Initial content type: {type(initial_content).__name__}")
        assert initial_content is not None, "Initial content should not be None"
        print("[OK] Test 1 PASSED: Initial content built successfully")
    except Exception as e:
        print(f"[FAIL] Test 1 FAILED: {e}")
        return False

    # 6. 测试切换到"我的插件"视图
    print("\n[Test 2] Switching to 'My Plugins' view...")
    try:
        # 模拟按钮点击事件
        class MockEvent:
            def __init__(self):
                self.control = MockSwitch()

        class MockSwitch:
            def __init__(self):
                self.value = True

        plugin_center_view._show_enabled_view(MockEvent())
        print("[OK] Test 2 PASSED: Switched to 'My Plugins' view without error")
    except AttributeError as e:
        if "'Column' object has no attribute 'content'" in str(e):
            print(f"[FAIL] Test 2 FAILED: Still has the Column.content bug")
            return False
        else:
            print(f"[FAIL] Test 2 FAILED: {e}")
            return False
    except Exception as e:
        print(f"[FAIL] Test 2 FAILED: {e}")
        return False

    # 7. 测试切换到"插件管理"视图
    print("\n[Test 3] Switching to 'Plugin Management' view...")
    try:
        plugin_center_view._show_management_view(MockEvent())
        print("[OK] Test 3 PASSED: Switched to 'Plugin Management' view without error")
    except AttributeError as e:
        if "'Column' object has no attribute 'content'" in str(e):
            print(f"[FAIL] Test 3 FAILED: Still has the Column.content bug")
            return False
        else:
            print(f"[FAIL] Test 3 FAILED: {e}")
            return False
    except Exception as e:
        print(f"[FAIL] Test 3 FAILED: {e}")
        return False

    # 8. 测试插件切换功能
    print("\n[Test 4] Testing plugin enable/disable toggle...")
    try:
        # 获取一个插件ID进行测试
        plugins = main_app.plugin_manager.get_all_plugins()
        if plugins:
            plugin_id = list(plugins.keys())[0]
            print(f"[Test 4] Testing with plugin: {plugin_id}")

            # 模拟切换开关
            mock_event = MockEvent()
            mock_event.control.value = False  # 尝试禁用

            plugin_center_view._on_plugin_toggle(mock_event, plugin_id)
            print("[OK] Test 4 PASSED: Plugin toggle handled without error")
        else:
            print("[WARN] Test 4 SKIPPED: No plugins available to test")
    except AttributeError as e:
        if "'Column' object has no attribute 'content'" in str(e):
            print(f"[FAIL] Test 4 FAILED: Still has the Column.content bug")
            return False
        else:
            print(f"[FAIL] Test 4 FAILED: {e}")
            return False
    except Exception as e:
        print(f"[FAIL] Test 4 FAILED: {e}")
        return False

    return True


if __name__ == "__main__":
    success = test_view_switching()
    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] All plugin center view switching tests PASSED")
        print("=" * 60)
        print("\nThe fix successfully resolves the AttributeError!")
        print("View switching now works correctly through MainApp's content_area.")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("[ERROR] Plugin center view switching tests FAILED")
        print("=" * 60)
        sys.exit(1)
