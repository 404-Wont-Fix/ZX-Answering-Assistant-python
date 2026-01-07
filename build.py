"""
项目打包脚本
用于将项目打包为可执行文件
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """主函数"""
    print("=" * 50)
    print("ZX Answering Assistant - 项目打包工具")
    print("=" * 50)
    
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
    
    # 打包项目
    print("\n正在打包项目...")
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--add-data", "src;src",
        "--add-data", "config;config",
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.sync_api",
        "--hidden-import", "playwright._impl._api_types",
        "--hidden-import", "playwright._impl._browser",
        "--hidden-import", "playwright._impl._connection",
        "--hidden-import", "playwright._impl._helper",
        "--name", "ZX-Answering-Assistant",
        "main.py"
    ]
    
    subprocess.check_call(cmd)
    
    print("\n✅ 项目打包完成！")
    print(f"可执行文件位于: {Path.cwd() / 'dist' / 'ZX-Answering-Assistant.exe'}")
    print("\n注意：首次运行可执行文件时，Playwright会自动下载浏览器，请确保网络连接正常。")


if __name__ == "__main__":
    main()