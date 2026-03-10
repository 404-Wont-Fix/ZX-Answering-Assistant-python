"""
构建工具共享模块
提取 build.py 和 minimal_build.py 中的共享函数，避免代码重复
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def get_platform_info():
    """
    获取平台信息

    Returns:
        dict: 包含 platform 和 architecture 的字典
              - platform: 操作系统名称 (windows, macos, linux)
              - architecture: 系统架构 (x64, arm64, arm, x86)
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


def update_version_info(version_file: Path = None):
    """
    更新版本信息（构建日期、时间、Git提交等）

    Args:
        version_file: version.py 文件路径，默认为项目根目录下的 version.py
    """
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
        except Exception:
            pass

        # 确定版本文件路径
        if version_file is None:
            # 默认为项目根目录下的 version.py
            version_file = Path(__file__).parent.parent.parent / "version.py"

        # 读取version.py文件
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


def get_dist_name(mode, version, platform_info, build_type="full"):
    """
    获取分发文件名（不含扩展名）

    Args:
        mode: 打包模式 ("onedir" 或 "onefile")
        version: 版本号
        platform_info: 平台信息字典 (由 get_platform_info() 返回)
        build_type: 构建类型 ("full" 或 "minimal")

    Returns:
        str: 规范化的分发名称

    Examples:
        完整目录模式: "ZX-Answering-Assistant-v2.6.6-windows-x64-installer"
        完整单文件:   "ZX-Answering-Assistant-v2.6.6-windows-x64-portable"
        最小化目录:   "ZX-Answering-Assistant-v2.6.6-windows-x64-minimal-installer"
        最小化单文件: "ZX-Answering-Assistant-v2.6.6-windows-x64-minimal-portable"
    """
    base_name = "ZX-Answering-Assistant"

    # 添加类型标识（如果是最小化构建）
    if build_type == "minimal":
        type_suffix = "minimal"
    else:
        type_suffix = ""  # 完整构建不添加类型标识

    # 添加模式标识
    if mode == "onedir":
        mode_suffix = "installer"  # 目录模式，类似安装器
    else:  # onefile
        mode_suffix = "portable"   # 单文件模式，便携版

    # 组合名称
    if type_suffix:
        return f"{base_name}-v{version}-{platform_info['platform']}-{platform_info['architecture']}-{type_suffix}-{mode_suffix}"
    else:
        return f"{base_name}-v{version}-{platform_info['platform']}-{platform_info['architecture']}-{mode_suffix}"


def format_size(size_bytes: int) -> str:
    """
    格式化字节大小为人类可读的形式

    Args:
        size_bytes: 字节大小

    Returns:
        str: 格式化后的大小字符串（如 "1.23 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def calculate_directory_size(directory: Path) -> int:
    """
    计算目录的总大小（字节）

    Args:
        directory: 目录路径

    Returns:
        int: 总大小（字节）
    """
    if not directory.exists():
        return 0

    total_size = 0
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            try:
                total_size += file_path.stat().st_size
            except (OSError, PermissionError):
                # 跳过无法访问的文件
                pass

    return total_size
