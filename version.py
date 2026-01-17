"""
版本信息文件
用于记录程序的版本号、构建信息等
"""

VERSION = "1.1.0"
VERSION_NAME = "ZX Answering Assistant"

# 构建信息（会在打包时自动更新）
BUILD_DATE = ""
BUILD_TIME = ""
GIT_COMMIT = ""
BUILD_MODE = ""  # "development" 或 "release"


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