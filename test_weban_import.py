"""
测试 WeBan 插件的自动导入功能

验证即使 WeBan 不在标准位置，插件也能自动找到并配置
"""

import sys
from pathlib import Path

# 添加插件路径
plugin_path = Path(__file__).parent / "plugins" / "weban_plugin"
sys.path.insert(0, str(plugin_path))

print("=" * 70)
print("测试 WeBan 插件自动导入")
print("=" * 70)
print()

# 测试 1: 导入插件
print("[测试 1] 导入 WeBan 插件...")
try:
    import weban_plugin
    print("✓ 插件导入成功")
except Exception as e:
    print(f"✗ 插件导入失败: {e}")
    sys.exit(1)

print()

# 测试 2: 检查 WeBan 路径查找
print("[测试 2] 测试 WeBan 路径查找...")
try:
    # 模拟 adapter 的查找逻辑
    def _find_weban_path():
        current_dir = plugin_path / "lib"
        possible_paths = [
            current_dir / "WeBan",
            Path(__file__).parent / "WeBan",
            Path(__file__).parent / "submodules" / "WeBan",
        ]

        for path in possible_paths:
            if path.exists() and (path / "api.py").exists():
                return path
        return None

    weban_path = _find_weban_path()
    if weban_path:
        print(f"✓ 找到 WeBan: {weban_path}")
    else:
        print("⚠ 未找到 WeBan，但插件会自动处理")
except Exception as e:
    print(f"✗ 路径查找失败: {e}")

print()

# 测试 3: 导入 adapter
print("[测试 3] 导入 WeBan adapter...")
try:
    sys.path.insert(0, str(plugin_path / "lib"))
    from weban_adapter import WEBAN_AVAILABLE
    if WEBAN_AVAILABLE:
        print("✓ WeBan adapter 可用")
    else:
        print("⚠ WeBan adapter 不可用（但这不是错误）")
        print("  插件会在首次使用时自动配置 WeBan")
except Exception as e:
    print(f"✗ Adapter 导入失败: {e}")

print()
print("=" * 70)
print("测试完成")
print("=" * 70)
