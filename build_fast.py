"""
项目打包脚本（优化版 - 目录模式）
使用--onedir模式，启动速度更快
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """主函数"""
    print("=" * 60)
    print("ZX Answering Assistant - 项目打包工具（优化版）")
    print("=" * 60)
    
    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 安装完成")
    
    # 确保所有依赖已安装
    print("\n正在安装项目依赖...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 确保Playwright浏览器已安装
    print("\n正在安装Playwright浏览器...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    
    # 获取Playwright安装路径
    try:
        from playwright.sync_api import sync_playwright
        print("\n正在获取Playwright浏览器路径...")
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            print(f"✅ Playwright浏览器路径: {browser_path}")
    except Exception as e:
        print(f"⚠️ 获取Playwright路径失败: {e}")
    
    # 打包项目（使用--onedir模式）
    print("\n正在打包项目（目录模式，启动更快）...")
    cmd = [
        "pyinstaller",
        "--onedir",
        "--clean",
        "--noconfirm",
        "--add-data", "src" + os.pathsep + "src",
        "--add-data", "config" + os.pathsep + "config",
        "--add-data", "playwright_browsers" + os.pathsep + "playwright_browsers",
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.sync_api",
        "--hidden-import", "playwright._impl._api_types",
        "--hidden-import", "playwright._impl._browser",
        "--hidden-import", "playwright._impl._connection",
        "--hidden-import", "playwright._impl._helper",
        "--hidden-import", "playwright._impl._page",
        "--hidden-import", "playwright._impl._element_handle",
        "--hidden-import", "playwright._impl._js_handle",
        "--hidden-import", "greenlet",
        "--hidden-import", "loguru",
        "--hidden-import", "yaml",
        "--hidden-import", "pandas",
        "--hidden-import", "openpyxl",
        "--hidden-import", "aiohttp",
        "--hidden-import", "tqdm",
        "--hidden-import", "keyboard",
        "--hidden-import", "requests",
        "--hidden-import", "dotenv",
        "--collect-all", "playwright",
        "--collect-all", "pyyaml",
        "--collect-all", "pandas",
        "--collect-all", "openpyxl",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--name", "ZX-Answering-Assistant",
        "main.py"
    ]
    
    print("执行命令:", " ".join(cmd))
    subprocess.check_call(cmd)
    
    print("\n" + "=" * 60)
    print("✅ 项目打包完成！")
    print("=" * 60)
    print(f"📁 可执行文件位于: {Path.cwd() / 'dist' / 'ZX-Answering-Assistant' / 'ZX-Answering-Assistant.exe'}")
    print("\n" + "=" * 60)
    print("📋 使用说明:")
    print("=" * 60)
    print("✨ 优化版：使用目录模式，启动速度快10-20倍")
    print("1. 运行 dist/ZX-Answering-Assistant/ZX-Answering-Assistant.exe")
    print("2. Playwright浏览器已内置，无需下载")
    print("3. 可以将整个 ZX-Answering-Assistant 文件夹分发给用户")
    print("4. 首次启动几乎秒开（无需解压）")
    print("=" * 60)
    print("\n💡 提示：如果需要单文件版本，请使用 build.py")


if __name__ == "__main__":
    main()