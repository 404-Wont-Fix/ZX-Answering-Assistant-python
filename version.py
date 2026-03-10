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

VERSION = "2.7.0"
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
    'file_version': (2, 6, 6, 0),
    'product_version': (2, 6, 6, 0),
    'file_description': '智能答题助手 - 自动化答题系统',
    'copyright': 'Copyright (C) 2024-2026',
    'company_name': 'ZX Project',
    'product_name': VERSION_NAME,
}


def create_version_file(output_path: str = None) -> Path:
    """
    生成 Windows 版本资源文件

    用于 PyInstaller 的 --version-file 参数，为 .exe 添加版本信息。

    Args:
        output_path: 输出文件路径，默认为项目根目录的 file_version_info.txt

    Returns:
        Path: 生成的版本文件路径
    """
    if output_path is None:
        project_root = Path(__file__).parent
        output_path = project_root / "file_version_info.txt"

    output_path = Path(output_path)

    # 解析版本号
    major, minor, patch, build = VERSION_INFO['file_version']
    file_version_str = f"{major}, {minor}, {patch}, {build}"
    file_version_display = f"{major}.{minor}.{patch}.{build}"

    # 生成版本文件内容（PyInstaller 格式）
    version_content = f"""\
# UTF-8
#
# For more details about fixed file info:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
#
# Translation: 0x0409 0x04b0 (英语(美国) Unicode)
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({file_version_str}),
    prodvers=({file_version_str}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{VERSION_INFO['company_name']}'),
        StringStruct(u'FileDescription', u'{VERSION_INFO['file_description']}'),
        StringStruct(u'FileVersion', u'{file_version_display}'),
        StringStruct(u'InternalName', u'{VERSION_NAME}'),
        StringStruct(u'LegalCopyright', u'{VERSION_INFO['copyright']}'),
        StringStruct(u'OriginalFilename', u'{VERSION_NAME.replace(" ", "-")}-{VERSION}.exe'),
        StringStruct(u'ProductName', u'{VERSION_INFO['product_name']}'),
        StringStruct(u'ProductVersion', u'{file_version_display}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

    # 写入文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(version_content)

        print(f"[OK] 版本信息文件已生成: {output_path}")
        print(f"[INFO] 文件版本: {file_version_display}")
        print(f"[INFO] 产品版本: {file_version_display}")

        return output_path

    except Exception as e:
        print(f"[ERROR] 生成版本信息文件失败: {e}")
        raise