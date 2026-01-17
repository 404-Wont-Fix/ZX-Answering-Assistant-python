"""
项目打包脚本
支持单文件模式和目录模式
"""

import os
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime


def update_version_info():
    """更新版本信息（构建日期、时间、Git提交等）"""
    try:
        # 获取当前时间
        now = datetime.now()
        build_date = now.strftime("%Y-%m-%d")
        build_time = now.strftime("%H:%M:%S")
        
        # 获取Git提交信息
        git_commit = ""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()
        except:
            pass
        
        # 读取version.py文件
        version_file = Path(__file__).parent / "version.py"
        with open(version_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 更新构建信息
        content = content.replace('BUILD_DATE = ""', f'BUILD_DATE = "{build_date}"')
        content = content.replace('BUILD_TIME = ""', f'BUILD_TIME = "{build_time}"')
        content = content.replace('GIT_COMMIT = ""', f'GIT_COMMIT = "{git_commit}"')
        content = content.replace('BUILD_MODE = ""', 'BUILD_MODE = "release"')
        
        # 写回文件
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 版本信息已更新:")
        print(f"   构建日期: {build_date}")
        print(f"   构建时间: {build_time}")
        print(f"   Git提交: {git_commit}")
        
    except Exception as e:
        print(f"⚠️ 更新版本信息失败: {e}")


def build_project(mode="onedir"):
    """
    构建项目
    
    Args:
        mode: 打包模式，"onefile" 或 "onedir"
    """
    # 导入版本信息
    import version
    print(f"📦 打包版本: {version.get_version_string()}")
    
    # 更新构建信息
    update_version_info()
    
    # 重新导入版本信息以获取更新后的数据
    import importlib
    importlib.reload(version)
    print(f"📦 完整版本: {version.get_full_version_string()}")
    
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
    
    # 打包项目
    mode_name = "单文件" if mode == "onefile" else "目录模式"
    print(f"\n正在打包项目（{mode_name}）...")
    
    cmd = [
        "pyinstaller",
        f"--{mode}",
        "--clean",
        "--noconfirm",
        "--add-data", "src" + os.pathsep + "src",
        "--add-data", "config" + os.pathsep + "config",
        "--add-data", "playwright_browsers" + os.pathsep + "playwright_browsers",
        "--add-data", "version.py" + os.pathsep + ".",
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
    
    # 输出结果
    print("\n" + "=" * 60)
    print("✅ 项目打包完成！")
    print("=" * 60)
    
    if mode == "onefile":
        exe_path = Path.cwd() / 'dist' / 'ZX-Answering-Assistant.exe'
        print(f"📁 可执行文件位于: {exe_path}")
        print(f"📦 版本: {version.get_full_version_string()}")
        print("\n" + "=" * 60)
        print("📋 使用说明:")
        print("=" * 60)
        print("✨ 零依赖运行：已包含Playwright浏览器，无需下载")
        print("1. 首次运行可执行文件时，会自动解压到临时目录")
        print("2. Playwright浏览器已内置，无需下载")
        print("3. 建议将exe文件放在单独的目录中运行")
        print("4. 首次启动可能需要1-2分钟（解压文件）")
    else:
        exe_path = Path.cwd() / 'dist' / 'ZX-Answering-Assistant' / 'ZX-Answering-Assistant.exe'
        print(f"📁 可执行文件位于: {exe_path}")
        print(f"📦 版本: {version.get_full_version_string()}")
        print("\n" + "=" * 60)
        print("📋 使用说明:")
        print("=" * 60)
        print("✨ 优化版：使用目录模式，启动速度快10-20倍")
        print("1. 运行 dist/ZX-Answering-Assistant/ZX-Answering-Assistant.exe")
        print("2. Playwright浏览器已内置，无需下载")
        print("3. 可以将整个 ZX-Answering-Assistant 文件夹分发给用户")
        print("4. 首次启动几乎秒开（无需解压）")
    
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ZX Answering Assistant - 项目打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['onefile', 'onedir'],
        default='onedir',
        help='打包模式: onefile(单文件，启动慢) 或 onedir(目录模式，启动快，默认)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ZX Answering Assistant - 项目打包工具")
    print("=" * 60)
    print(f"📦 打包模式: {args.mode}")
    
    # 构建项目
    build_project(mode=args.mode)


if __name__ == "__main__":
    main()