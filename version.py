"""
版本信息文件
用于记录程序的版本号、构建信息等
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# 设置控制台编码为 UTF-8（修复 Windows GBK 编码问题）
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except:
        # 如果设置失败，尝试通过环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'

VERSION = "2.7.2"
VERSION_NAME = "ZX Answering Assistant"

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


# 版本信息字典（用于 Windows 版本资源）
VERSION_INFO = {
    'file_version': (2, 7, 0, 0),
    'product_version': (2, 7, 0, 0),
    'file_description': '智能答题助手 - 自动化答题系统',
    'copyright': 'Copyright (C) 2024-2026',
    'company_name': 'ZX Project',
    'product_name': VERSION_NAME,
}
