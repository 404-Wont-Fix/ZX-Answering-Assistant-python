"""
测试浏览器无头模式设置
"""

import sys
from pathlib import Path

# Windows UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.settings import get_settings_manager
from src.browser_manager import get_browser_manager


def main():
    print("\n" + "=" * 60)
    print("  浏览器无头模式设置测试")
    print("=" * 60)

    settings = get_settings_manager()

    # 显示当前设置
    print(f"\n当前无头模式设置: {settings.get_browser_headless()}")
    print(f"  {'✅ 开启（隐藏浏览器）' if settings.get_browser_headless() else '❌ 关闭（显示浏览器）'}")

    # 测试切换
    print("\n测试切换无头模式...")
    new_value = settings.toggle_browser_headless()
    print(f"切换后的值: {new_value}")
    print(f"  {'✅ 开启（隐藏浏览器）' if new_value else '❌ 关闭（显示浏览器）'}")

    # 恢复原设置
    print("\n恢复原设置...")
    settings.set_browser_headless(not new_value)
    print(f"已恢复为: {settings.get_browser_headless()}")

    # 测试浏览器管理器读取设置
    print("\n测试浏览器管理器读取设置...")
    manager = get_browser_manager()
    print(f"✅ 浏览器管理器将从配置文件读取: {settings.get_browser_headless()}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
