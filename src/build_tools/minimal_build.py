"""
最小化构建模块
创建不包含可网络下载依赖的轻量级构建版本
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


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


def get_dist_name(mode, version, platform_info, build_type="minimal"):
    """
    获取分发文件名（不含扩展名）

    Args:
        mode: 打包模式 ("onedir" 或 "onefile")
        version: 版本号
        platform_info: 平台信息字典
        build_type: 构建类型 ("minimal" 或 "full")

    Returns:
        str: 规范化的分发名称
        最小化目录模式: "ZX-Answering-Assistant-v2.2.0-windows-x64-minimal-installer"
        最小化单文件: "ZX-Answering-Assistant-v2.2.0-windows-x64-minimal-portable"
    """
    base_name = "ZX-Answering-Assistant"

    # 添加类型标识
    type_suffix = "minimal" if build_type == "minimal" else "full"

    # 添加模式标识
    if mode == "onedir":
        mode_suffix = "installer"
    else:  # onefile
        mode_suffix = "portable"

    return f"{base_name}-v{version}-{platform_info['platform']}-{platform_info['architecture']}-{type_suffix}-{mode_suffix}"


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
        version_file = Path(__file__).parent.parent.parent / "version.py"
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
        # 导入 version 模块
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        import version
        version_file_path = version.create_version_file()
        print(f"[OK] 版本文件已生成: {version_file_path}")
        print(f"[INFO] 文件版本: {'.'.join(map(str, version.VERSION_INFO['file_version']))}")
        print(f"[INFO] 产品版本: {'.'.join(map(str, version.VERSION_INFO['product_version']))}")
        return version_file_path
    except Exception as e:
        print(f"[WARN] 生成版本文件失败: {e}")
        return None


def build_project_minimal(mode="onedir", use_upx=False):
    """
    最小化构建项目（不打包 Playwright 浏览器和 Flet 可执行文件）

    Args:
        mode: 打包模式，"onefile" 或 "onedir"
        use_upx: 是否使用 UPX 压缩
    """
    # 导入版本信息
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
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
    dist_name = get_dist_name(mode, version.VERSION, platform_info, build_type="minimal")
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
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                          str(Path(__file__).parent.parent.parent / "requirements.txt"), "-q"])

    print("\n[INFO] 最小化构建模式：不打包 Playwright 浏览器和 Flet 可执行文件")
    print("[INFO] 运行时会自动从网络下载所需依赖（首次启动较慢）")

    # 检查是否使用 UPX 压缩
    if use_upx:
        print("[INFO] UPX 压缩已启用（这将减小体积但会稍慢）")
        # 检查 UPX 是否可用
        try:
            subprocess.run(["upx", "--version"], capture_output=True, check=True)
            print("[OK] UPX 已安装并可用")
            upx_args = []
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[WARN] UPX 未安装，将跳过压缩")
            print("[INFO] 安装 UPX: https://upx.github.io/")
            upx_args = ["--noupx"]
    else:
        # 显式禁用 UPX
        upx_args = ["--noupx"]

    # 打包项目
    mode_name = "单文件" if mode == "onefile" else "目录模式"
    print(f"\n[INFO] 正在打包项目（{mode_name}，最小化构建）...")

    cmd = [
        "pyinstaller",
        f"--{mode}",
        "--clean",
        "--noconfirm",
        "--console",  # 确保显示控制台窗口
        # 注意：最小化构建不打包浏览器和 Flet
        # 但需要添加数据目录结构（空目录会在运行时创建）
        "--hidden-import", "version",
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
        "--hidden-import", "src.build_tools.minimal_build",
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
        str(Path(__file__).parent.parent.parent / "main.py")
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
    print("[OK] 最小化构建完成！")
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
        print("最小化单文件模式：体积最小，首次启动需要下载依赖")
        print("1. 首次运行时会自动下载 Playwright 浏览器（约 100-200 MB）")
        print("2. 首次运行时会自动下载 Flet 可执行文件（约 50-100 MB）")
        print("3. 后续启动会使用缓存，无需重新下载")
        print("4. 建议在良好的网络环境下首次运行")
        print("5. 首次启动可能需要 5-10 分钟（下载依赖）")
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
        print("最小化目录模式：体积小，启动快，首次启动需要下载依赖")
        print(f"1. 运行 dist/{dist_name}/{exe_filename}")
        print("2. 首次运行时会自动下载 Playwright 浏览器（约 100-200 MB）")
        print("3. 首次运行时会自动下载 Flet 可执行文件（约 50-100 MB）")
        print("4. 后续启动会使用缓存，无需重新下载")
        print("5. 建议在良好的网络环境下首次运行")
        print(f"6. 可以将整个 {dist_name} 文件夹分发给用户")

    print("=" * 60)

    return {
        "success": True,
        "dist_name": dist_name,
        "mode": mode,
        "exe_path": str(exe_path),
        "dist_dir": str(dist_dir) if mode == "onedir" else None
    }


def build_all_minimal_variants(use_upx=False):
    """
    构建所有最小化版本（onedir + onefile）

    Args:
        use_upx: 是否使用 UPX 压缩

    Returns:
        dict: 包含两个版本构建结果的字典
    """
    # 导入版本信息
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    import version
    platform_info = get_platform_info()

    onedir_name = get_dist_name("onedir", version.VERSION, platform_info, build_type="minimal")
    onefile_name = get_dist_name("onefile", version.VERSION, platform_info, build_type="minimal")
    if platform_info["platform"] == "windows":
        onefile_name += ".exe"

    results = {}

    print("\n" + "=" * 60)
    print("开始编译: 最小化目录模式")
    print("=" * 60)
    results["onedir"] = build_project_minimal(mode="onedir", use_upx=use_upx)

    print("\n\n" + "=" * 60)
    print("开始编译: 最小化单文件模式")
    print("=" * 60)
    results["onefile"] = build_project_minimal(mode="onefile", use_upx=use_upx)

    print("\n\n" + "=" * 60)
    print("[SUCCESS] 所有最小化版本编译完成！")
    print("=" * 60)
    print(f"最小化目录模式: dist/{onedir_name}/")
    print(f"最小化单文件模式: dist/{onefile_name}")
    print("=" * 60)

    return results
