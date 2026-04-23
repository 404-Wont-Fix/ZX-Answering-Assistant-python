"""
版本信息文件
用于记录程序的版本号、构建信息等
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

from plugins.weban_plugin.modules.WeBan.main import VERSION

# 设置控制台编码为 UTF-8（修复 Windows GBK 编码问题）
if sys.platform == 'win32':
    try:
        import codecs
        # 检查 stdout 是否已经被重新定向，避免重复 detach
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, codecs.Codec):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)
    except:
        # 如果设置失败，尝试通过环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# 版本名称
VERSION_NAME = "ZX Answering Assistant"

def _get_version_from_git() -> str:
    """从 Git 标签读取版本号

    Returns:
        版本号字符串，如 '3.2.0'，如果失败返回 None
    """
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            # 移除前缀 'v'
            if version.startswith('v'):
                version = version[1:]
            return version
    except Exception:
        pass
    return None

def _get_version() -> str:
    """获取版本号（优先级：Git > 默认值）"""
    # 尝试从 Git 读取
    version = _get_version_from_git()
    if version:
        return version

    # 如果失败，使用默认值
    return "3.2.0"

# VERSION = _get_version()

VERSION = "3.4.0"

# 构建信息（会在打包时自动更新，开发时自动获取）
def _get_build_info():
    """获取构建信息"""
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

    # 判断构建模式
    build_mode = "development"
    # 检查是否在打包环境中运行
    if getattr(sys, 'frozen', False):
        build_mode = "release"
    # 或者检查是否在dist目录中
    elif 'dist' in str(Path(__file__).parent):
        build_mode = "release"

    return build_date, build_time, git_commit, build_mode

BUILD_DATE, BUILD_TIME, GIT_COMMIT, BUILD_MODE = _get_build_info()


def get_version_string():
    """获取完整的版本字符串"""
    return f"{VERSION_NAME} v{VERSION}"


def get_full_version_string():
    """获取包含构建信息的完整版本字符串"""
    version = get_version_string()
    if BUILD_DATE:
        version += f" (Build {BUILD_DATE})"
    return version


def get_build_info():
    """获取构建信息字典"""
    return {
        "version": VERSION,
        "name": VERSION_NAME,
        "build_date": BUILD_DATE,
        "build_time": BUILD_TIME,
        "git_commit": GIT_COMMIT,
        "build_mode": BUILD_MODE
    }


def print_version_info():
    """打印版本信息"""
    print("\n" + "=" * 60)
    print(f"📦 {get_full_version_string()}")
    print("=" * 60)
    info = get_build_info()
    print(f"版本号: {info['version']}")
    print(f"构建日期: {info['build_date']}")
    print(f"构建时间: {info['build_time']}")
    print(f"Git提交: {info['git_commit']}")
    print(f"构建模式: {info['build_mode']}")
    print("=" * 60 + "\n")


def create_version_file(file_path: str) -> Path:
    """创建版本信息文件

    Args:
        file_path: 文件路径

    Returns:
        Path对象
    """
    version_file = Path(file_path)
    version_file.parent.mkdir(parents=True, exist_ok=True)

    content = f"""{VERSION_NAME}
版本号: {VERSION}
构建日期: {BUILD_DATE}
构建时间: {BUILD_TIME}
Git提交: {GIT_COMMIT}
构建模式: {BUILD_MODE}
"""

    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return version_file


# 版本信息字典（用于 Windows 版本资源）
VERSION_INFO = {
    'file_version': (3, 2, 0, 0),
    'product_version': (3, 2, 0, 0),
    'file_description': '智能答题助手 - 自动化答题系统',
    'copyright': 'Copyright (C) 2024-2026',
    'company_name': 'ZX Project',
    'product_name': VERSION_NAME,
}
