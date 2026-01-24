"""
项目打包脚本
支持单文件模式和目录模式
默认编译两个版本，可通过参数选择编译单个版本
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

from src.build_tools import ensure_browser_ready, get_browser_size
from src.build_tools import ensure_flet_ready, get_flet_size
from src.build_tools import build_project_minimal, build_all_minimal_variants


def get_platform_info():
    """
    获取平台信息

    Returns:
        dict: 包含 platform 和 architecture 的字典
    """
    import platform

    # 获取操作系统
    system = platform.system().lower()
    if system == "windows":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    elif system == "linux":
        os_name = "linux"
    else:
        os_name = system

    # 获取架构
    machine = platform.machine().lower()
    if machine in ["x86_64", "amd64"]:
        arch = "x64"
    elif machine in ["arm64", "aarch64"]:
        arch = "arm64"
    elif machine in ["arm", "armv7l"]:
        arch = "arm"
    elif machine in ["i386", "i686"]:
        arch = "x86"
    else:
        arch = machine

    return {
        "platform": os_name,
        "architecture": arch
    }


def get_dist_name(mode, version, platform_info):
    """
    获取分发文件名（不含扩展名）

    Args:
        mode: 打包模式 ("onedir" 或 "onefile")
        version: 版本号
        platform_info: 平台信息字典

    Returns:
        str: 规范化的分发名称
        目录模式: "ZX-Answering-Assistant-v2.2.0-windows-x64-installer"
        单文件模式: "ZX-Answering-Assistant-v2.2.0-windows-x64-portable"
    """
    base_name = "ZX-Answering-Assistant"

    # 添加模式标识
    if mode == "onedir":
        mode_suffix = "installer"  # 目录模式，类似安装器
    else:  # onefile
        mode_suffix = "portable"   # 单文件模式，便携版

    return f"{base_name}-v{version}-{platform_info['platform']}-{platform_info['architecture']}-{mode_suffix}"


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

        print(f"[OK] 版本信息已更新:")
        print(f"   构建日期: {build_date}")
        print(f"   构建时间: {build_time}")
        print(f"   Git提交: {git_commit}")

    except Exception as e:
        print(f"[WARN] 更新版本信息失败: {e}")


def generate_exe_version_file():
    """
    生成 Windows EXE 版本信息文件

    Returns:
        Path: 版本文件路径，如果平台不是 Windows 则返回 None
    """
    platform_info = get_platform_info()

    # 只在 Windows 平台生成版本文件
    if platform_info["platform"] != "windows":
        print("[INFO] 非 Windows 平台，跳过版本文件生成")
        return None

    try:
        import version
        version_file_path = version.create_version_file()
        print(f"[OK] 版本文件已生成: {version_file_path}")
        print(f"[INFO] 文件版本: {'.'.join(map(str, version.VERSION_INFO['file_version']))}")
        print(f"[INFO] 产品版本: {'.'.join(map(str, version.VERSION_INFO['product_version']))}")
        return version_file_path
    except Exception as e:
        print(f"[WARN] 生成版本文件失败: {e}")
        return None


def build_project(mode="onedir", use_upx=False):
    """
    构建项目

    Args:
        mode: 打包模式，"onefile" 或 "onedir"
        use_upx: 是否使用 UPX 压缩
    """
    # 导入版本信息
    import version
    print(f"\n[INFO] 打包版本: {version.get_version_string()}")

    # 更新构建信息
    update_version_info()

    # 重新导入版本信息以获取更新后的数据
    import importlib
    importlib.reload(version)
    print(f"[INFO] 完整版本: {version.get_full_version_string()}")

    # 获取平台信息
    platform_info = get_platform_info()
    print(f"[INFO] 平台: {platform_info['platform']} {platform_info['architecture']}")

    # 生成分发名称
    dist_name = get_dist_name(mode, version.VERSION, platform_info)
    print(f"[INFO] 分发名称: {dist_name}")

    # 生成 EXE 版本信息文件（仅 Windows）
    version_file_path = generate_exe_version_file()

    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print("[OK] PyInstaller 已安装")
    except ImportError:
        print("[INFO] PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller 安装完成")

    # 确保所有依赖已安装
    print("\n[INFO] 正在安装项目依赖...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])

    # 确保Playwright浏览器已安装
    print("\n[INFO] 正在安装Playwright浏览器...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

    # 复制Playwright浏览器到项目目录
    print("\n[INFO] 正在准备Playwright浏览器用于打包...")
    project_root = Path(__file__).parent
    browser_result = ensure_browser_ready(project_root=project_root)

    if browser_result["ready"]:
        if browser_result["copied"]:
            print(f"[OK] 浏览器已复制 ({browser_result['size_mb']:.2f} MB)")
        else:
            print(f"[OK] 浏览器已准备就绪 ({browser_result['size_mb']:.2f} MB)")
    else:
        print("[WARN] 浏览器准备失败，但继续打包...")

    # 准备Flet可执行文件
    print("\n[INFO] 正在准备Flet可执行文件用于打包...")
    flet_result = ensure_flet_ready(project_root=project_root)

    if flet_result["ready"]:
        if flet_result["copied"]:
            print(f"[OK] Flet已下载 ({flet_result['size_mb']:.2f} MB)")
        else:
            print(f"[OK] Flet已准备就绪 ({flet_result['size_mb']:.2f} MB)")
    else:
        print("[WARN] Flet准备失败，打包后将从GitHub下载（首次启动较慢）")

    # 获取Playwright安装路径
    try:
        from playwright.sync_api import sync_playwright
        print("\n[INFO] 正在获取Playwright浏览器路径...")
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            print(f"[OK] Playwright浏览器路径: {browser_path}")
    except Exception as e:
        print(f"[WARN] 获取Playwright路径失败: {e}")

    # 打包项目
    mode_name = "单文件" if mode == "onefile" else "目录模式"
    print(f"\n[INFO] 正在打包项目（{mode_name}）...")

    # 检查是否使用 UPX 压缩
    if use_upx:
        print("[INFO] UPX 压缩已启用（这将减小体积但会稍慢）")
        # 检查 UPX 是否可用
        try:
            subprocess.run(["upx", "--version"], capture_output=True, check=True)
            print("[OK] UPX 已安装并可用")
            # PyInstaller 会自动检测并使用 PATH 中的 UPX，无需额外参数
            upx_args = []
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[WARN] UPX 未安装，将跳过压缩")
            print("[INFO] 安装 UPX: https://upx.github.io/")
            # 使用 --noupx 显式禁用 UPX
            upx_args = ["--noupx"]
    else:
        # 显式禁用 UPX
        upx_args = ["--noupx"]

    cmd = [
        "pyinstaller",
        f"--{mode}",
        "--clean",
        "--noconfirm",
        "--add-data", "playwright_browsers" + os.pathsep + "playwright_browsers",
        "--add-data", "flet_browsers/unpacked" + os.pathsep + "flet_browsers/unpacked",
        "--hidden-import", "version",  # 编译 version.py 为 .pyc
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
        "--hidden-import", "keyboard",
        "--hidden-import", "requests",
        "--hidden-import", "flet",
        "--hidden-import", "src.teacher_login",
        "--hidden-import", "src.student_login",
        "--hidden-import", "src.extract",
        "--hidden-import", "src.export",
        "--hidden-import", "src.auto_answer",
        "--hidden-import", "src.api_auto_answer",
        "--hidden-import", "src.settings",
        "--hidden-import", "src.question_bank_importer",
        "--hidden-import", "src.file_handler",
        "--hidden-import", "src.api_client",
        "--hidden-import", "src.main_gui",
        "--hidden-import", "src.ui.views.answering_view",
        "--hidden-import", "src.ui.views.extraction_view",
        "--hidden-import", "src.ui.views.settings_view",
        "--hidden-import", "src.build_tools",
        "--hidden-import", "src.build_tools.browser_handler",
        "--hidden-import", "src.build_tools.flet_handler",
        "--collect-all", "playwright",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "openpyxl",
        "--exclude-module", "loguru",
        "--exclude-module", "aiohttp",
        "--exclude-module", "tqdm",
        "--exclude-module", "scipy",
        "--exclude-module", "yaml",
        "--exclude-module", "dotenv",
        "--exclude-module", "pyyaml",
        "--name", dist_name,
        "main.py"
    ]

    # 添加版本文件（仅 Windows）
    if version_file_path:
        cmd.insert(4, "--version-file")
        cmd.insert(5, str(version_file_path))

    # 添加 UPX 参数（如果有）
    cmd.extend(upx_args)

    print("[CMD] " + " ".join(cmd))
    subprocess.check_call(cmd)

    # 输出结果
    print("\n" + "=" * 60)
    print("[OK] 项目打包完成！")
    print("=" * 60)

    if mode == "onefile":
        # 单文件模式：生成 .exe 文件（Windows）或无扩展名（Linux/Mac）
        if platform_info["platform"] == "windows":
            exe_filename = f"{dist_name}.exe"
        else:
            exe_filename = dist_name

        exe_path = Path.cwd() / 'dist' / exe_filename
        print(f"[PATH] 可执行文件位于: {exe_path}")
        print(f"[INFO] 版本: {version.get_full_version_string()}")
        print(f"[INFO] 平台: {platform_info['platform']} {platform_info['architecture']}")
        print("\n" + "=" * 60)
        print("[HELP] 使用说明:")
        print("=" * 60)
        print("单文件模式：所有文件打包到一个可执行文件中")
        print("1. 首次运行可执行文件时，会自动解压到临时目录")
        print("2. Playwright浏览器已内置，无需下载")
        print("3. Flet可执行文件已内置，首次启动无需从GitHub下载")
        print("4. 建议将可执行文件放在单独的目录中运行")
        print("5. 首次启动可能需要1-2分钟（解压文件）")
    else:
        # 目录模式：生成文件夹
        dist_dir = Path.cwd() / 'dist' / dist_name
        if platform_info["platform"] == "windows":
            exe_filename = f"{dist_name}.exe"
        else:
            exe_filename = dist_name

        exe_path = dist_dir / exe_filename
        print(f"[PATH] 可执行文件位于: {exe_path}")
        print(f"[PATH] 分发目录位于: {dist_dir}")
        print(f"[INFO] 版本: {version.get_full_version_string()}")
        print(f"[INFO] 平台: {platform_info['platform']} {platform_info['architecture']}")
        print("\n" + "=" * 60)
        print("[HELP] 使用说明:")
        print("=" * 60)
        print("目录模式：启动速度快10-20倍（推荐）")
        print(f"1. 运行 dist/{dist_name}/{exe_filename}")
        print("2. Playwright浏览器已内置，无需下载")
        print("3. Flet可执行文件已内置，首次启动无需从GitHub下载")
        print(f"4. 可以将整个 {dist_name} 文件夹分发给用户")
        print("5. 首次启动几乎秒开（无需解压）")

    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ZX Answering Assistant - 项目打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build.py                           # 编译所有4个版本（完整 + 最小化，onedir + onefile）
  python build.py --minimal                 # 仅编译最小化版本（onedir + onefile）
  python build.py --full                    # 仅编译完整版本（onedir + onefile）
  python build.py --mode onefile            # 仅编译单文件版本（完整）
  python build.py --mode onedir             # 仅编译目录版本（完整）
  python build.py --minimal --mode onefile  # 仅编译最小化单文件版本
  python build.py --copy-browser            # 仅复制浏览器
  python build.py --copy-all                # 复制所有依赖

输出文件名格式:
  完整目录模式:   ZX-Answering-Assistant-v2.2.0-windows-x64-installer/
  完整单文件:     ZX-Answering-Assistant-v2.2.0-windows-x64-portable.exe
  最小化目录模式: ZX-Answering-Assistant-v2.2.0-windows-x64-minimal-installer/
  最小化单文件:   ZX-Answering-Assistant-v2.2.0-windows-x64-minimal-portable.exe

说明:
  - installer: 目录模式，启动快，推荐使用
  - portable: 单文件模式，所有文件打包到一个可执行文件
  - minimal: 最小化构建，不打包浏览器和 Flet，运行时下载（体积小，首次启动慢）
  - full: 完整构建，包含所有依赖（体积大，启动快）

体积优化:
  python build.py --upx             # 启用 UPX 压缩（减小 30-50%% 体积）
  python build.py --upx --mode onefile  # 压缩单文件版本

  UPX 下载: https://upx.github.io/
  Windows: 下载 upx-4.2.2-win64.zip，解压后将 upx.exe 添加到 PATH
        """
    )

    parser.add_argument(
        '--mode', '-m',
        choices=['onefile', 'onedir', 'both'],
        default='both',
        help='打包模式: onefile(单文件), onedir(目录模式), both(两个版本，默认)'
    )

    parser.add_argument(
        '--minimal',
        action='store_true',
        help='使用最小化构建模式（不打包 Playwright 浏览器和 Flet）'
    )

    parser.add_argument(
        '--full',
        action='store_true',
        help='使用完整构建模式（打包所有依赖，默认行为）'
    )

    parser.add_argument(
        '--copy-browser',
        action='store_true',
        help='仅复制Playwright浏览器到项目目录（不进行打包）'
    )

    parser.add_argument(
        '--copy-flet',
        action='store_true',
        help='仅下载Flet可执行文件到项目目录（不进行打包）'
    )

    parser.add_argument(
        '--copy-all',
        action='store_true',
        help='复制所有依赖（Playwright浏览器 + Flet）到项目目录（不进行打包）'
    )

    parser.add_argument(
        '--force-copy',
        action='store_true',
        help='强制重新复制（覆盖已有文件）'
    )

    parser.add_argument(
        '--upx',
        action='store_true',
        help='使用 UPX 压缩可执行文件（减小 30-50%% 体积，但启动稍慢）'
    )

    parser.add_argument(
        '--no-upx',
        action='store_true',
        help='禁用 UPX 压缩（即使安装了 UPX 也不使用）'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ZX Answering Assistant - 项目打包工具")
    print("=" * 60)

    project_root = Path(__file__).parent

    # 如果只是复制浏览器
    if args.copy_browser:
        print("[TASK] 复制Playwright浏览器")
        browser_result = ensure_browser_ready(
            project_root=project_root,
            force_copy=args.force_copy
        )

        if browser_result["ready"]:
            status = "已重新复制" if args.force_copy or browser_result["copied"] else "已存在"
            print(f"\n[OK] 浏览器{status} ({browser_result['size_mb']:.2f} MB)")
            return 0
        else:
            print("\n[ERROR] 浏览器准备失败")
            return 1

    # 如果只是下载Flet
    if args.copy_flet:
        print("[TASK] 下载Flet可执行文件")
        flet_result = ensure_flet_ready(
            project_root=project_root,
            force_copy=args.force_copy
        )

        if flet_result["ready"]:
            status = "已重新下载" if args.force_copy or flet_result["copied"] else "已存在"
            print(f"\n[OK] Flet{status} ({flet_result['size_mb']:.2f} MB)")
            return 0
        else:
            print("\n[ERROR] Flet准备失败")
            return 1

    # 如果复制所有依赖
    if args.copy_all:
        print("[TASK] 复制所有依赖（Playwright浏览器 + Flet）")

        # 复制Playwright浏览器
        print("\n[1/2] 准备Playwright浏览器...")
        browser_result = ensure_browser_ready(
            project_root=project_root,
            force_copy=args.force_copy
        )

        if browser_result["ready"]:
            status = "已重新复制" if args.force_copy or browser_result["copied"] else "已存在"
            print(f"   [OK] 浏览器{status} ({browser_result['size_mb']:.2f} MB)")
        else:
            print("   [ERROR] 浏览器准备失败")
            return 1

        # 下载Flet
        print("\n[2/2] 准备Flet可执行文件...")
        flet_result = ensure_flet_ready(
            project_root=project_root,
            force_copy=args.force_copy
        )

        if flet_result["ready"]:
            status = "已重新下载" if args.force_copy or flet_result["copied"] else "已存在"
            print(f"   [OK] Flet{status} ({flet_result['size_mb']:.2f} MB)")
        else:
            print("   [ERROR] Flet准备失败")
            return 1

        print("\n" + "=" * 60)
        print("[OK] 所有依赖准备完成！")
        print(f"[INFO] Playwright浏览器: {browser_result['size_mb']:.2f} MB")
        print(f"[INFO] Flet可执行文件: {flet_result['size_mb']:.2f} MB")
        print(f"[INFO] 总计: {browser_result['size_mb'] + flet_result['size_mb']:.2f} MB")
        print("=" * 60)
        return 0

    # 正常打包流程
    use_upx = args.upx and not args.no_upx

    # 判断构建类型：默认构建所有版本
    if args.minimal and args.full:
        print("[ERROR] 不能同时指定 --minimal 和 --full")
        return 1

    # 如果没有指定 --minimal 或 --full，默认构建所有版本
    build_all = not args.minimal and not args.full

    # 获取平台信息用于显示
    platform_info = get_platform_info()
    import version

    # 构建完整版本（默认或明确指定 --full）
    if build_all or args.full:
        if build_all:
            print("[INFO] 构建所有4个版本（完整 + 最小化，onedir + onefile）")
        else:
            print("[INFO] 构建完整版本（包含所有依赖）")

        # 完整版本的文件名
        full_onedir_name = get_dist_name("onedir", version.VERSION, platform_info)
        full_onefile_name = get_dist_name("onefile", version.VERSION, platform_info)
        if platform_info["platform"] == "windows":
            full_onefile_name += ".exe"

        if args.mode == 'both':
            print("\n" + "=" * 60)
            print("开始编译: 完整目录模式（推荐）")
            print("=" * 60)
            build_project(mode="onedir", use_upx=use_upx)

            print("\n\n" + "=" * 60)
            print("开始编译: 完整单文件模式")
            print("=" * 60)
            build_project(mode="onefile", use_upx=use_upx)
        elif args.mode == 'onedir':
            print("\n" + "=" * 60)
            print("开始编译: 完整目录模式")
            print("=" * 60)
            build_project(mode="onedir", use_upx=use_upx)
        elif args.mode == 'onefile':
            print("\n" + "=" * 60)
            print("开始编译: 完整单文件模式")
            print("=" * 60)
            build_project(mode="onefile", use_upx=use_upx)

    # 构建最小化版本（默认或明确指定 --minimal）
    if build_all or args.minimal:
        if args.minimal:
            print("[INFO] 构建最小化版本（不打包浏览器和 Flet，运行时下载）")

        if args.mode == 'both':
            if build_all:
                print("\n\n" + "=" * 60)
                print("开始编译: 最小化目录模式")
                print("=" * 60)
            build_project_minimal(mode="onedir", use_upx=use_upx)

            if build_all:
                print("\n\n" + "=" * 60)
                print("开始编译: 最小化单文件模式")
                print("=" * 60)
            build_project_minimal(mode="onefile", use_upx=use_upx)
        elif args.mode == 'onedir':
            print("\n" + "=" * 60)
            print("开始编译: 最小化目录模式")
            print("=" * 60)
            build_project_minimal(mode="onedir", use_upx=use_upx)
        elif args.mode == 'onefile':
            print("\n" + "=" * 60)
            print("开始编译: 最小化单文件模式")
            print("=" * 60)
            build_project_minimal(mode="onefile", use_upx=use_upx)

    # 构建完成总结
    print("\n\n" + "=" * 60)
    print("[SUCCESS] 构建完成！")
    print("=" * 60)

    if build_all:
        # 显示所有4个版本
        full_onedir_name = get_dist_name("onedir", version.VERSION, platform_info)
        full_onefile_name = get_dist_name("onefile", version.VERSION, platform_info)
        minimal_onedir_name = full_onedir_name.replace("installer", "minimal-installer")
        minimal_onefile_name = full_onefile_name.replace("portable", "minimal-portable")
        if platform_info["platform"] == "windows":
            full_onefile_name += ".exe"
            minimal_onefile_name += ".exe"

        print("已构建以下4个版本：")
        print(f"  1. 完整目录模式: dist/{full_onedir_name}/")
        print(f"  2. 完整单文件模式: dist/{full_onefile_name}")
        print(f"  3. 最小化目录模式: dist/{minimal_onedir_name}/")
        print(f"  4. 最小化单文件模式: dist/{minimal_onefile_name}")
    elif args.full:
        full_onedir_name = get_dist_name("onedir", version.VERSION, platform_info)
        full_onefile_name = get_dist_name("onefile", version.VERSION, platform_info)
        if platform_info["platform"] == "windows":
            full_onefile_name += ".exe"

        print("已构建完整版本：")
        if args.mode == 'both':
            print(f"  1. 完整目录模式: dist/{full_onedir_name}/")
            print(f"  2. 完整单文件模式: dist/{full_onefile_name}")
        elif args.mode == 'onedir':
            print(f"  完整目录模式: dist/{full_onedir_name}/")
        elif args.mode == 'onefile':
            print(f"  完整单文件模式: dist/{full_onefile_name}")
    elif args.minimal:
        minimal_onedir_name = get_dist_name("onedir", version.VERSION, platform_info).replace("installer", "minimal-installer")
        minimal_onefile_name = get_dist_name("onefile", version.VERSION, platform_info).replace("portable", "minimal-portable")
        if platform_info["platform"] == "windows":
            minimal_onefile_name += ".exe"

        print("已构建最小化版本：")
        if args.mode == 'both':
            print(f"  1. 最小化目录模式: dist/{minimal_onedir_name}/")
            print(f"  2. 最小化单文件模式: dist/{minimal_onefile_name}")
        elif args.mode == 'onedir':
            print(f"  最小化目录模式: dist/{minimal_onedir_name}/")
        elif args.mode == 'onefile':
            print(f"  最小化单文件模式: dist/{minimal_onefile_name}")

    print("=" * 60)


if __name__ == "__main__":
    main()
