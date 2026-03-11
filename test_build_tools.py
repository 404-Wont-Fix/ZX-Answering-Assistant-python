"""
测试构建工具模块
验证浏览器和 Flet 打包功能是否正常
"""

import os
import sys
from pathlib import Path

# 设置控制台编码为 UTF-8（修复 Windows GBK 编码问题）
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.build_tools import (
    get_playwright_browser_version,
    ensure_browser_ready,
    ensure_flet_ready,
    verify_browser,
    verify_flet
)


def test_browser():
    """测试浏览器功能"""
    print("=" * 60)
    print("测试 Playwright 浏览器")
    print("=" * 60)

    # 1. 获取浏览器版本
    print("\n[1/4] 获取浏览器版本...")
    version = get_playwright_browser_version()
    if version:
        print(f"✅ 浏览器版本: {version}")
    else:
        print("❌ 无法获取浏览器版本")
        print("[INFO] 请确保已运行: python -m playwright install chromium")
        return False

    # 2. 验证浏览器
    print("\n[2/4] 验证浏览器目录...")
    if verify_browser(project_root=project_root):
        print("✅ 浏览器已存在且完整")
    else:
        print("❌ 浏览器不存在或不完整")
        print("[INFO] 将尝试复制浏览器...")

    # 3. 准备浏览器
    print("\n[3/4] 准备浏览器...")
    result = ensure_browser_ready(project_root=project_root)
    if result["ready"]:
        print(f"✅ 浏览器准备成功 ({result['size_mb']:.2f} MB)")
        if result["copied"]:
            print("   （已复制）")
        else:
            print("   （已存在）")
    else:
        print("❌ 浏览器准备失败")
        return False

    # 4. 检查目录结构
    print("\n[4/4] 检查目录结构...")
    playwright_browsers_dir = project_root / "playwright_browsers"
    if playwright_browsers_dir.exists():
        subdirs = [d for d in playwright_browsers_dir.iterdir() if d.is_dir()]
        if subdirs:
            for subdir in subdirs:
                print(f"✅ 发现浏览器目录: {subdir.name}")
                # 检查关键文件
                if subdir.name.startswith("chromium-"):
                    chrome_exe = subdir / "chrome-win" / "chrome.exe"
                    if chrome_exe.exists():
                        print(f"   ✅ chrome.exe 存在")
                    else:
                        print(f"   ❌ chrome.exe 不存在")
        else:
            print("❌ playwright_browsers 目录为空")
            return False
    else:
        print("❌ playwright_browsers 目录不存在")
        return False

    return True


def test_flet():
    """测试 Flet 功能"""
    print("\n" + "=" * 60)
    print("测试 Flet 可执行文件")
    print("=" * 60)

    # 1. 验证 Flet
    print("\n[1/3] 验证 Flet 目录...")
    if verify_flet(project_root=project_root):
        print("✅ Flet 已存在且完整")
    else:
        print("❌ Flet 不存在或不完整")
        print("[INFO] 将尝试下载 Flet...")

    # 2. 准备 Flet
    print("\n[2/3] 准备 Flet...")
    result = ensure_flet_ready(project_root=project_root)
    if result["ready"]:
        print(f"✅ Flet 准备成功 ({result['size_mb']:.2f} MB)")
        if result["copied"]:
            print("   （已下载）")
        else:
            print("   （已存在）")
    else:
        print("❌ Flet 准备失败")
        return False

    # 3. 检查目录结构
    print("\n[3/3] 检查目录结构...")
    flet_unpacked_dir = project_root / "flet_browsers" / "unpacked"
    if flet_unpacked_dir.exists():
        flet_exe = flet_unpacked_dir / "app" / "flet" / "flet" / "flet.exe"
        if flet_exe.exists():
            print(f"✅ flet.exe 存在: {flet_exe.relative_to(project_root)}")
            # 检查文件大小
            size_mb = flet_exe.stat().st_size / (1024 * 1024)
            print(f"   文件大小: {size_mb:.2f} MB")
        else:
            print("❌ flet.exe 不存在")
            return False
    else:
        print("❌ flet_browsers/unpacked 目录不存在")
        return False

    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("ZX Answering Assistant - 构建工具测试")
    print("=" * 60)

    # 测试浏览器
    browser_ok = test_browser()

    # 测试 Flet
    flet_ok = test_flet()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"Playwright 浏览器: {'✅ 通过' if browser_ok else '❌ 失败'}")
    print(f"Flet 可执行文件: {'✅ 通过' if flet_ok else '❌ 失败'}")

    if browser_ok and flet_ok:
        print("\n✅ 所有测试通过！可以开始打包。")
        print("\n运行以下命令开始打包:")
        print("  python build.py --mode onedir")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
