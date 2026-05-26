"""
测试系统托盘功能

此脚本用于测试系统托盘功能是否正常工作。
"""

def test_tray_manager():
    """测试托盘管理器"""
    print("🧪 测试系统托盘功能...")

    try:
        from src.core.tray_manager import get_tray_manager
        import threading

        # 获取托盘管理器实例
        tray_manager = get_tray_manager()

        # 检查托盘功能是否可用
        if not tray_manager.is_available():
            print("❌ 系统托盘功能不可用（需要安装 pystray 和 Pillow）")
            print("   请运行: pip install pystray Pillow")
            return False

        print("✅ 系统托盘功能可用")
        quit_requested = threading.Event()

        # 设置回调函数
        def on_show():
            print("📺 显示窗口")

        def on_hide():
            print("🔒 隐藏窗口")

        def on_quit():
            print("👋 退出程序")
            quit_requested.set()

        tray_manager.set_callbacks(
            on_show=on_show,
            on_hide=on_hide,
            on_quit=on_quit
        )

        # 启动托盘图标
        if tray_manager.start("ZX答题助手 - 测试"):
            print("✅ 托盘图标已启动")
            print("ℹ️  请查看任务栏右下角的托盘图标")
            print("ℹ️  右键点击图标查看菜单，双击图标测试功能")
            print("ℹ️  按 Ctrl+C 停止测试")

            try:
                while not quit_requested.wait(0.1):
                    pass
            except KeyboardInterrupt:
                print("\n🛑 停止测试...")
            finally:
                tray_manager.stop()
            print("✅ 测试完成")
            return True
        else:
            print("❌ 托盘图标启动失败")
            return False

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("   请确保已安装所需依赖: pip install pystray Pillow")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  ZX答题助手 - 系统托盘功能测试")
    print("=" * 60)

    success = test_tray_manager()

    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  测试未通过，请检查错误信息")
        print("\n💡 解决方案:")
        print("   1. 安装依赖: pip install pystray Pillow")
        print("   2. 重新运行测试")

    print("=" * 60)
