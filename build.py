"""
项目打包脚本
支持单文件模式和目录模式
默认编译两个版本，可通过参数选择编译单个版本
"""

import os
import sys
import subprocess
import argparse
import shutil
import py_compile
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


def compile_to_pyc(
    source_dir="src",
    output_dir="src_compiled",
    exclude_files=None,
    remove_py=False
):
    """
    编译 src 目录下的所有 .py 文件为 .pyc 文件

    Args:
        source_dir: 源代码目录
        output_dir: 编译输出目录
        exclude_files: 要排除的文件列表
        remove_py: 是否删除原始 .py 文件（仅保留 .pyc）

    Returns:
        bool: 编译是否成功
    """
    if exclude_files is None:
        exclude_files = []

    source_path = Path(source_dir).absolute()
    output_path = Path(output_dir).absolute()

    print("=" * 60)
    print("预编译源码为 .pyc 字节码")
    print("=" * 60)
    print(f"源目录: {source_path}")
    print(f"输出目录: {output_path}")
    print(f"删除源码: {'是' if remove_py else '否（保留 .py）'}")

    # 清空输出目录
    if output_path.exists():
        print(f"\n🔄 清理旧的编译输出...")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 复制整个目录结构
    print(f"\n📋 复制目录结构...")
    shutil.copytree(source_path, output_path, dirs_exist_ok=True)

    # 收集所有需要编译的 Python 文件
    py_files = []
    for py_file in output_path.rglob("*.py"):
        # 跳过 __pycache__
        if "__pycache__" in str(py_file):
            continue

        rel_path = py_file.relative_to(output_path)

        # __init__.py 必须保留
        if py_file.name == "__init__.py":
            if remove_py:
                print(f"⏭️  跳过（__init__.py 必须保留）: {rel_path}")
            continue

        # 检查是否在排除列表中
        if any(exclude in str(rel_path) for exclude in exclude_files):
            print(f"⏭️  跳过（排除）: {rel_path}")
            continue

        py_files.append(py_file)

    print(f"\n📦 找到 {len(py_files)} 个文件需要编译")

    if not py_files:
        print("\n⚠️  没有需要编译的文件")
        return True

    # 编译为 .pyc
    print("\n🔧 开始编译...")
    compiled_count = 0
    failed_count = 0

    for py_file in py_files:
        rel_path = py_file.relative_to(output_path)
        try:
            # 编译为 .pyc
            py_compile.compile(str(py_file), optimize=2)
            compiled_count += 1
            print(f"  ✅ {rel_path}")
        except Exception as e:
            failed_count += 1
            print(f"  ❌ {rel_path}: {e}")

    print(f"\n编译完成: {compiled_count} 成功, {failed_count} 失败")

    # 删除原始 .py 文件（如果需要）
    if remove_py:
        print("\n🧹 删除原始 .py 文件...")
        deleted_count = 0

        for py_file in output_path.rglob("*.py"):
            if py_file.name != "__init__.py" and "__pycache__" not in str(py_file):
                rel_path = py_file.relative_to(output_path)

                # 检查是否有对应的 .pyc 文件
                pyc_file = py_file.with_suffix('.pyc')

                # .pyc 可能在 __pycache__ 目录中
                pycache_dir = py_file.parent / '__pycache__'
                if pycache_dir.exists():
                    # 查找匹配的 .pyc 文件
                    pyc_pattern = f"{py_file.stem}*.pyc"
                    for cached_pyc in pycache_dir.glob(pyc_pattern):
                        if cached_pyc.exists():
                            # 将 .pyc 移到父目录
                            target_pyc = py_file.with_suffix('.pyc')
                            shutil.copy2(cached_pyc, target_pyc)
                            break

                if py_file.with_suffix('.pyc').exists():
                    py_file.unlink()
                    deleted_count += 1
                    print(f"  删除: {rel_path}")

        print(f"删除了 {deleted_count} 个 .py 文件")

    print("\n" + "=" * 60)
    print("✅ 编译完成！")
    print("=" * 60)
    print(f"编译输出目录: {output_path}")
    print(f"编译文件数: {compiled_count}")

    return True


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


def build_project(mode="onedir", use_upx=False, build_dir=None, compile_src_flag=False):
    """
    构建项目

    Args:
        mode: 打包模式，"onefile" 或 "onedir"
        use_upx: 是否使用 UPX 压缩
        build_dir: 构建输出目录（如果路径包含中文，建议使用此参数指定无中文的路径）
        compile_src_flag: 是否预编译源码为 .pyc
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

    # 编译源码（可选）- 减小体积并轻度保护源码
    use_compiled = False
    src_dir_to_package = "src"

    if compile_src_flag:
        print("\n[INFO] 正在预编译源码为 .pyc 字节码...")
        try:
            compile_success = compile_to_pyc(
                source_dir=str(project_root / "src"),
                output_dir=str(project_root / "src_compiled"),
                remove_py=False  # 保留 .py 文件作为备份
            )

            if compile_success:
                print("[OK] 源码预编译成功")
                use_compiled = True
                src_dir_to_package = "src_compiled"
            else:
                print("[WARN] 源码预编译失败，将使用源码打包")

        except Exception as e:
            print(f"[WARN] 源码预编译出错: {e}")
            print("[INFO] 将使用源码打包")

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

    # 设置构建输出目录
    if build_dir:
        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)
        workpath = build_path / "build"
        distpath = build_path / "dist"
        print(f"[INFO] 构建输出目录: {build_path}")
    else:
        workpath = "build"
        distpath = "dist"

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

    # 根据编译结果选择使用编译后的源码还是原始源码
    src_dir_to_package = "src_compiled" if use_compiled else "src"
    if use_compiled:
        print("[INFO] 使用编译后的源码（.pyd 文件）")
    else:
        print("[INFO] 使用原始源码（.py 文件）")

    cmd = [
        "pyinstaller",
        f"--{mode}",
        "--clean",
        "--noconfirm",
        "--optimize", "2",  # 优化字节码（删除 docstrings 和其他非必要信息）
        "--workpath", str(workpath),
        "--distpath", str(distpath),
        "--add-data", src_dir_to_package + os.pathsep + "src",
        "--add-data", "playwright_browsers" + os.pathsep + "playwright_browsers",
        "--add-data", "flet_browsers/unpacked" + os.pathsep + "flet_browsers/unpacked",
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
        "--hidden-import", "keyboard",
        "--hidden-import", "requests",
        "--hidden-import", "flet",
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

        exe_path = Path(distpath) / exe_filename
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
        dist_dir = Path(distpath) / dist_name
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
  python build.py                    # 编译两个版本（onedir + onefile）
  python build.py --mode onefile     # 仅编译单文件版本
  python build.py --mode onedir      # 仅编译目录版本
  python build.py --copy-browser     # 仅复制浏览器
  python build.py --copy-all         # 复制所有依赖

输出文件名格式:
  目录模式: ZX-Answering-Assistant-v2.2.0-windows-x64-installer/
  单文件:   ZX-Answering-Assistant-v2.2.0-windows-x64-portable.exe

说明:
  - installer: 目录模式，启动快，推荐使用
  - portable: 单文件模式，所有文件打包到一个可执行文件

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

    parser.add_argument(
        '--build-dir',
        '-b',
        type=str,
        default=None,
        help='构建输出目录（用于解决路径包含中文字符的问题。例如: D:\\BuildOutput）'
    )

    parser.add_argument(
        '--compile-src',
        action='store_true',
        help='预编译源码为 .pyc 字节码（减小体积，轻度保护源码）'
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
    if args.mode == 'both':
        print("[INFO] 打包模式: 两个版本（onedir + onefile）")

        # 检查是否使用 UPX
        use_upx = args.upx and not args.no_upx

        # 获取平台信息用于显示
        platform_info = get_platform_info()
        import version
        onedir_name = get_dist_name("onedir", version.VERSION, platform_info)
        onefile_name = get_dist_name("onefile", version.VERSION, platform_info)
        if platform_info["platform"] == "windows":
            onefile_name += ".exe"

        print("\n" + "=" * 60)
        print("开始编译: 目录模式（推荐）")
        print("=" * 60)
        build_project(mode="onedir", use_upx=use_upx, build_dir=args.build_dir, compile_src_flag=args.compile_src)

        print("\n\n" + "=" * 60)
        print("开始编译: 单文件模式")
        print("=" * 60)
        build_project(mode="onefile", use_upx=use_upx, build_dir=args.build_dir, compile_src_flag=args.compile_src)

        print("\n\n" + "=" * 60)
        print("[SUCCESS] 两个版本编译完成！")
        print("=" * 60)
        print(f"目录模式: dist/{onedir_name}/")
        print(f"单文件模式: dist/{onefile_name}")
        print("=" * 60)
    else:
        print(f"[INFO] 打包模式: {args.mode}")
        use_upx = args.upx and not args.no_upx
        build_project(mode=args.mode, use_upx=use_upx, build_dir=args.build_dir, compile_src_flag=args.compile_src)


if __name__ == "__main__":
    main()
