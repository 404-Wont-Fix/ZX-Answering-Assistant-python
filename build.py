"""
ZX Answering Assistant - 构建脚本
使用 PyInstaller 将项目打包为可执行文件
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 版本信息
VERSION = "2.7.0"
APP_NAME = "ZX-Answering-Assistant"


def get_platform_info() -> dict:
    """获取平台信息"""
    import platform

    system = platform.system().lower()
    if system == "windows":
        os_name = "windows"
    elif system == "darwin":
        os_name = "macos"
    else:
        os_name = system

    machine = platform.machine().lower()
    if machine in ["x86_64", "amd64"]:
        arch = "x64"
    elif machine in ["arm64", "aarch64"]:
        arch = "arm64"
    else:
        arch = machine

    return {"platform": os_name, "architecture": arch}


def update_version_info():
    """更新版本信息"""
    try:
        now = datetime.now()
        build_date = now.strftime("%Y-%m-%d")
        build_time = now.strftime("%H:%M:%S")

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
        except Exception:
            pass

        version_file = PROJECT_ROOT / "version.py"
        with open(version_file, 'r', encoding='utf-8') as f:
            content = f.read()

        content = content.replace('BUILD_DATE = ""', f'BUILD_DATE = "{build_date}"')
        content = content.replace('BUILD_TIME = ""', f'BUILD_TIME = "{build_time}"')
        content = content.replace('GIT_COMMIT = ""', f'GIT_COMMIT = "{git_commit}"')
        content = content.replace('BUILD_MODE = ""', 'BUILD_MODE = "release"')

        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[OK] 版本信息已更新: {build_date} {build_time} ({git_commit})")
    except Exception as e:
        print(f"[WARN] 更新版本信息失败: {e}")


def get_output_name(mode: str, platform_info: dict) -> str:
    """获取输出文件名"""
    mode_suffix = "installer" if mode == "onedir" else "portable"
    return f"{APP_NAME}-v{VERSION}-{platform_info['platform']}-{platform_info['architecture']}-{mode_suffix}"


def install_dependencies():
    """安装项目依赖"""
    print("\n[INFO] 正在安装项目依赖...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"]
    )
    print("[OK] 依赖安装完成")


def install_playwright_browser():
    """安装 Playwright 浏览器"""
    print("\n[INFO] 正在安装 Playwright 浏览器...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    print("[OK] 浏览器安装完成")


def check_pyinstaller() -> bool:
    """检查 PyInstaller 是否已安装"""
    try:
        import PyInstaller
        print("[OK] PyInstaller 已安装")
        return True
    except ImportError:
        print("[INFO] 正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller 安装完成")
        return True


def compile_source_code() -> Path:
    """
    编译源代码为 .pyc 字节码

    Returns:
        Path: 编译后的目录路径
    """
    from src.build_tools import compile_to_pyc

    src_dir = PROJECT_ROOT / "src"
    compiled_dir = PROJECT_ROOT / "src_compiled"

    print("\n[INFO] 正在预编译源码为 .pyc 字节码...")
    compile_to_pyc(
        source_dir=src_dir,
        output_dir=compiled_dir
    )

    return compiled_dir


def prepare_browser_and_flet():
    """准备 Playwright 浏览器和 Flet 可执行文件"""
    from src.build_tools import ensure_browser_ready, ensure_flet_ready

    print("\n[INFO] 正在准备 Playwright 浏览器...")
    browser_result = ensure_browser_ready(project_root=PROJECT_ROOT)

    if browser_result["ready"]:
        if browser_result["copied"]:
            print(f"[OK] 浏览器已复制 ({browser_result['size_mb']:.2f} MB)")
        else:
            print(f"[OK] 浏览器已准备就绪 ({browser_result['size_mb']:.2f} MB)")
    else:
        print("[WARN] 浏览器准备失败，但继续打包...")

    print("\n[INFO] 正在准备 Flet 可执行文件...")
    flet_result = ensure_flet_ready(project_root=PROJECT_ROOT)

    if flet_result["ready"]:
        if flet_result["copied"]:
            print(f"[OK] Flet已下载 ({flet_result['size_mb']:.2f} MB)")
        else:
            print(f"[OK] Flet已准备就绪 ({flet_result['size_mb']:.2f} MB)")
    else:
        print("[WARN] Flet准备失败，打包后将从GitHub下载（首次启动较慢）")


def build(mode: str = "onedir", use_upx: bool = False, build_dir: str = None, compile_src: bool = False):
    """
    构建项目

    Args:
        mode: 打包模式 (onedir 或 onefile)
        use_upx: 是否使用 UPX 压缩
        build_dir: 构建输出目录
        compile_src: 是否预编译源码为 .pyc
    """
    # 更新版本信息
    update_version_info()

    # 获取平台信息
    platform_info = get_platform_info()
    print(f"\n[INFO] 平台: {platform_info['platform']} {platform_info['architecture']}")

    # 检查依赖
    check_pyinstaller()
    install_dependencies()
    install_playwright_browser()

    # 准备浏览器和 Flet（如果要打包）
    prepare_browser_and_flet()

    # 检查浏览器和 Flet 目录是否存在
    playwright_browsers_dir = PROJECT_ROOT / "playwright_browsers"
    flet_unpacked_dir = PROJECT_ROOT / "flet_browsers" / "unpacked"

    # 验证浏览器目录
    browser_ready = False
    if playwright_browsers_dir.exists():
        # 检查是否有版本子目录
        browser_subdirs = [d for d in playwright_browsers_dir.iterdir() if d.is_dir() and d.name.startswith("chromium-")]
        if browser_subdirs:
            browser_ready = True
            print(f"[OK] 浏览器目录已准备: {browser_subdirs[0].name}")
        else:
            print("[WARN] playwright_browsers 目录存在但为空")
    else:
        print("[WARN] playwright_browsers 目录不存在，打包后将需要下载浏览器")

    # 验证 Flet 目录
    flet_ready = flet_unpacked_dir.exists() and (flet_unpacked_dir / "app" / "flet" / "flet" / "flet.exe").exists()
    if flet_ready:
        print("[OK] Flet 目录已准备")
    else:
        print("[WARN] flet_browsers/unpacked 目录不存在，打包后将需要下载 Flet")

    # 源码预编译
    use_compiled = False
    src_dir_to_package = "src"

    if compile_src:
        compiled_dir = compile_source_code()
        print("[OK] 源码预编译成功")
        use_compiled = True
        src_dir_to_package = str(compiled_dir)

    # 输出名称
    output_name = get_output_name(mode, platform_info)
    print(f"\n[INFO] 输出名称: {output_name}")

    # 设置构建路径
    if build_dir:
        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)
        workpath = str(build_path / "build")
        distpath = str(build_path / "dist")
    else:
        workpath = "build"
        distpath = "dist"

    # 构建 PyInstaller 命令
    cmd = [
        "pyinstaller",
        f"--{mode}",
        "--clean",
        "--noconfirm",
        "--optimize", "2",
        "--workpath", workpath,
        "--distpath", distpath,
        "--add-data", f"{src_dir_to_package}{os.pathsep}src",
        "--add-data", f"version.py{os.pathsep}.",
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.sync_api",
        "--hidden-import", "playwright._impl._api_types",
        "--hidden-import", "playwright._impl._browser",
        "--hidden-import", "playwright._impl._connection",
        "--hidden-import", "playwright._impl._page",
        "--hidden-import", "playwright._impl._element_handle",
        "--hidden-import", "greenlet",
        "--hidden-import", "keyboard",
        "--hidden-import", "requests",
        "--hidden-import", "flet",
        "--hidden-import", "flet_desktop",
        "--hidden-import", "src.build_tools",
        "--hidden-import", "src.build_tools.browser_handler",
        "--hidden-import", "src.build_tools.flet_handler",
        "--hidden-import", "src.build_tools.compiler",
        "--collect-all", "flet",
        "--collect-all", "playwright",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "openpyxl",
        "--exclude-module", "loguru",
        "--exclude-module", "aiohttp",
        "--exclude-module", "scipy",
        "--exclude-module", "pyyaml",
        "--name", output_name,
        "main.py"
    ]

    # 添加浏览器数据（如果存在）
    if browser_ready:
        cmd.extend(["--add-data", f"playwright_browsers{os.pathsep}playwright_browsers"])
        print("[INFO] 将打包 Playwright 浏览器")
    else:
        print("[INFO] 跳过浏览器打包，运行时将下载")

    # 添加 Flet 数据（如果存在）
    if flet_ready:
        cmd.extend(["--add-data", f"flet_browsers/unpacked{os.pathsep}flet_browsers/unpacked"])
        print("[INFO] 将打包 Flet 可执行文件")
    else:
        print("[INFO] 跳过 Flet 打包，运行时将下载")

    # UPX 压缩
    if use_upx:
        print("[INFO] UPX 压缩已启用")
        try:
            subprocess.run(["upx", "--version"], capture_output=True, check=True)
            print("[OK] UPX 可用")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[WARN] UPX 未安装，将跳过压缩")
            cmd.append("--noupx")
    else:
        cmd.append("--noupx")

    # 执行构建
    print(f"\n[INFO] 开始构建 ({mode} 模式)...")
    if use_compiled:
        print("[INFO] 使用预编译的源码（打包后将删除 .py 文件）")
    print("[CMD] " + " ".join(cmd))
    subprocess.check_call(cmd)

    # 清理打包后的源码文件（如果启用了预编译）
    if compile_src and mode == "onedir":
        from src.build_tools import clean_source_files

        if build_dir:
            dist_dir = Path(build_dir) / "dist" / output_name
        else:
            dist_dir = Path(distpath) / output_name

        internal_dir = dist_dir / "_internal"
        if internal_dir.exists():
            clean_source_files(internal_dir)

    # 输出结果
    print("\n" + "=" * 60)
    print("[OK] 构建完成！")
    print("=" * 60)

    dist_path = Path(distpath)
    if mode == "onefile":
        exe_path = dist_path / f"{output_name}.exe" if platform_info['platform'] == "windows" else dist_path / output_name
        print(f"[PATH] 可执行文件: {exe_path}")
    else:
        exe_path = dist_path / output_name / (f"{output_name}.exe" if platform_info['platform'] == "windows" else output_name)
        print(f"[PATH] 可执行文件: {exe_path}")
        print(f"[PATH] 分发目录: {dist_path / output_name}")

    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ZX Answering Assistant - 构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python build.py                         # 构建目录模式
  python build.py --mode onefile          # 构建单文件模式
  python build.py --both                  # 构建两种模式
  python build.py --upx                   # 启用 UPX 压缩
  python build.py --compile-src           # 预编译源码为 .pyc
  python build.py --compile-src --upx     # 预编译 + UPX 压缩

输出文件名格式:
  目录模式: ZX-Answering-Assistant-v2.7.0-windows-x64-installer/
  单文件:   ZX-Answering-Assistant-v2.7.0-windows-x64-portable.exe

特性:
  --compile-src  预编译源码为 .pyc 字节码，减小体积并轻度保护源码
  --upx         使用 UPX 压缩可执行文件（减小 30-50%% 体积）
        """
    )

    parser.add_argument(
        '--mode', '-m',
        choices=['onedir', 'onefile', 'both'],
        default='onedir',
        help='打包模式 (默认: onedir)'
    )

    parser.add_argument(
        '--upx',
        action='store_true',
        help='使用 UPX 压缩可执行文件'
    )

    parser.add_argument(
        '--compile-src',
        action='store_true',
        help='预编译源码为 .pyc 字节码（减小体积，轻度保护源码）'
    )

    parser.add_argument(
        '--build-dir', '-b',
        type=str,
        default=None,
        help='构建输出目录'
    )

    parser.add_argument(
        '--copy-browser',
        action='store_true',
        help='仅复制 Playwright 浏览器（不进行打包）'
    )

    parser.add_argument(
        '--copy-flet',
        action='store_true',
        help='仅下载 Flet 可执行文件（不进行打包）'
    )

    parser.add_argument(
        '--copy-all',
        action='store_true',
        help='复制所有依赖（浏览器 + Flet，不进行打包）'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ZX Answering Assistant - 构建工具")
    print("=" * 60)

    try:
        # 如果只是复制浏览器
        if args.copy_browser:
            print("[TASK] 复制 Playwright 浏览器")
            from src.build_tools import ensure_browser_ready

            browser_result = ensure_browser_ready(project_root=PROJECT_ROOT, force_copy=True)

            if browser_result["ready"]:
                print(f"\n[OK] 浏览器已复制 ({browser_result['size_mb']:.2f} MB)")
                return 0
            else:
                print("\n[ERROR] 浏览器准备失败")
                return 1

        # 如果只是下载 Flet
        if args.copy_flet:
            print("[TASK] 下载 Flet 可执行文件")
            from src.build_tools import ensure_flet_ready

            flet_result = ensure_flet_ready(project_root=PROJECT_ROOT, force_copy=True)

            if flet_result["ready"]:
                print(f"\n[OK] Flet已下载 ({flet_result['size_mb']:.2f} MB)")
                return 0
            else:
                print("\n[ERROR] Flet准备失败")
                return 1

        # 如果复制所有依赖
        if args.copy_all:
            print("[TASK] 复制所有依赖（Playwright 浏览器 + Flet）")
            prepare_browser_and_flet()
            return 0

        # 正常打包流程
        if args.mode == 'both':
            print("[INFO] 构建模式: 目录 + 单文件\n")

            print("\n" + "=" * 60)
            print("1. 构建目录模式（推荐）")
            print("=" * 60)
            build("onedir", args.upx, args.build_dir, args.compile_src)

            print("\n\n" + "=" * 60)
            print("2. 构建单文件模式")
            print("=" * 60)
            build("onefile", args.upx, args.build_dir, args.compile_src)

            print("\n\n" + "=" * 60)
            print("[SUCCESS] 两种模式构建完成！")
            print("=" * 60)
        else:
            print(f"[INFO] 构建模式: {args.mode}")
            build(args.mode, args.upx, args.build_dir, args.compile_src)

        return 0

    except Exception as e:
        print(f"\n[ERROR] 构建失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
