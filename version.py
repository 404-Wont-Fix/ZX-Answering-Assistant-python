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

VERSION = "2.3.0"
VERSION_NAME = "ZX Answering Assistant"

# Windows EXE 版本信息配置
# 用于设置编译后 exe 文件的属性（右键属性查看）
VERSION_INFO = {
    "file_version": (2, 3, 0, 0),           # 文件版本 (主.次.修订.构建)
    "product_version": (2, 3, 0, 0),        # 产品版本
    "file_description": "智能答题助手 - 自动化答题工具",  # 文件说明
    "product_name": "ZX Answering Assistant",            # 产品名称
    "company_name": "TianJiaJi",            # 作者
    "legal_copyright": "Licensed under Apache License 2.0",  # 版权信息
    "legal_trademarks": "",                 # 商标（可选）
    "original_filename": "",                # 原始文件名（留空自动生成）
    "internal_name": "zx-assistant",        # 内部名称
    "comments": "自动化答题系统 - 支持学生和教师门户 | Apache License 2.0",  # 备注
    "private_build": "",                    # 私有构建信息（可选）
    "special_build": "",                    # 特殊构建信息（可选）
    "lang_id": 0x0804,                      # 语言 ID: 0x0804=中文(中国), 0x0409=英语(美国)
    "charset_id": 0x04b0,                   # 字符集 ID: Unicode (UTF-8)
}

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


def generate_version_file():
    """
    生成 PyInstaller 版本文件内容（用于 Windows EXE 版本信息）

    Returns:
        str: 版本文件内容（UTF-16LE 编码的文本格式）
    """
    # 将版本元组转换为点分隔的字符串
    file_version_str = ".".join(map(str, VERSION_INFO["file_version"]))
    product_version_str = ".".join(map(str, VERSION_INFO["product_version"]))

    # 生成版本文件内容
    # VSVersionInfo 格式：PyInstaller 使用的 Windows 版本资源格式
    content = f"""#
# UTF-16LE encoding
# For more details: https://docs.microsoft.com/en-us/windows/win32/menurc/versioninfo-resource
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={VERSION_INFO["file_version"]},
    prodvers={VERSION_INFO["product_version"]},
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
        u'{VERSION_INFO["lang_id"]:04x}{VERSION_INFO["charset_id"]:04x}',
        [StringStruct(u'CompanyName', u'{VERSION_INFO["company_name"]}'),
        StringStruct(u'FileDescription', u'{VERSION_INFO["file_description"]}'),
        StringStruct(u'FileVersion', u'{file_version_str}'),
        StringStruct(u'InternalName', u'{VERSION_INFO["internal_name"]}'),
        StringStruct(u'LegalCopyright', u'{VERSION_INFO["legal_copyright"]}'),
        StringStruct(u'LegalTrademarks', u'{VERSION_INFO["legal_trademarks"]}'),
        StringStruct(u'OriginalFilename', u'{VERSION_INFO["original_filename"]}'),
        StringStruct(u'ProductName', u'{VERSION_INFO["product_name"]}'),
        StringStruct(u'ProductVersion', u'{product_version_str}'),
        StringStruct(u'Comments', u'{VERSION_INFO["comments"]}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [{VERSION_INFO["lang_id"]}, {VERSION_INFO["charset_id"]}])])
  ]
)"""
    return content


def create_version_file(path=None):
    """
    创建 PyInstaller 版本文件（.txt 格式）

    Args:
        path: 版本文件保存路径，默认保存在项目根目录的 file_version_info.txt

    Returns:
        Path: 版本文件路径
    """
    if path is None:
        path = Path(__file__).parent / "file_version_info.txt"
    else:
        path = Path(path)

    # 生成版本文件内容
    content = generate_version_file()

    # 写入文件（使用 UTF-8 编码，PyInstaller 会自动处理）
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return path