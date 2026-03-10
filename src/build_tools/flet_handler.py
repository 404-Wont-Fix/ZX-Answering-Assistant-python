"""
Flet可执行文件处理模块
负责下载和缓存Flet可执行文件，避免程序运行时从GitHub下载
"""

import os
import sys
import zipfile
import shutil
import urllib.request
from pathlib import Path
from typing import Optional


# Flet版本配置
FLET_VERSION = "0.80.2"  # 与requirements.txt中的flet版本保持一致

# Flet 下载源配置（按优先级排序）
FLET_DOWNLOAD_SOURCES = {
    "official": "https://github.com/flet-dev/flet/releases/download/v{version}/flet-windows.zip",
    "mirror": "https://gh.nxnow.top/https://github.com/flet-dev/flet/releases/download/v{version}/flet-windows.zip",
}

# 默认使用官方源
DEFAULT_DOWNLOAD_SOURCE = "official"


def get_flet_temp_dir() -> Path:
    """
    获取Flet临时目录路径（与Flet内部逻辑一致）

    Returns:
        Path: Flet临时目录路径
    """
    # Flet使用的临时目录模式
    temp_base = Path(os.environ.get("TEMP", "/tmp"))
    # Flet会查找类似 _MEIXXXXXX 的临时目录
    # 我们使用固定的目录名来缓存
    return temp_base / "flet_cache"


def get_flet_executable_path() -> Path:
    """
    获取Flet可执行文件的目标路径

    Returns:
        Path: flet.exe的路径
    """
    flet_temp = get_flet_temp_dir()
    return flet_temp / "app" / "flet" / "flet.exe"


def download_flet_archive(target_dir: Path, version: str = FLET_VERSION, source: str = DEFAULT_DOWNLOAD_SOURCE) -> Optional[Path]:
    """
    下载Flet Windows压缩包

    Args:
        target_dir: 目标目录
        version: Flet版本号
        source: 下载源 ("official" 或 "mirror")

    Returns:
        Path: 下载的zip文件路径，失败返回None
    """
    # 选择下载源
    if source in FLET_DOWNLOAD_SOURCES:
        url_template = FLET_DOWNLOAD_SOURCES[source]
    else:
        print(f"⚠️ 未知的下载源 '{source}'，使用官方源")
        url_template = FLET_DOWNLOAD_SOURCES["official"]

    url = url_template.format(version=version)
    # 保存到 download 子目录
    download_dir = target_dir / "download"
    zip_path = download_dir / f"flet-windows-{version}.zip"

    print("=" * 60)
    print(f"下载Flet v{version}可执行文件")
    print("=" * 60)
    print(f"📥 下载源: {source}")
    print(f"📥 下载地址: {url}")
    print(f"📁 保存位置: {zip_path}")
    print("这可能需要几分钟...")

    try:
        # 创建目标目录
        download_dir.mkdir(parents=True, exist_ok=True)

        # 下载文件
        urllib.request.urlretrieve(url, zip_path)

        file_size = zip_path.stat().st_size / (1024 * 1024)
        print(f"✅ 下载完成！大小: {file_size:.2f} MB")

        # 验证文件大小（Flet zip 文件应该在 50-150 MB 之间）
        if file_size < 50 or file_size > 300:
            print(f"⚠️ 警告：下载的文件大小异常 ({file_size:.2f} MB)")
            print(f"⚠️ 文件可能损坏或不完整，建议删除后重新下载")

        return zip_path

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_flet_archive(zip_path: Path, target_dir: Path) -> bool:
    """
    解压Flet压缩包

    Args:
        zip_path: zip文件路径
        target_dir: 目标目录

    Returns:
        bool: 是否成功
    """
    print(f"\n正在解压: {zip_path}")
    print(f"目标目录: {target_dir}")

    try:
        # 删除旧的目录（如果存在）
        if target_dir.exists():
            shutil.rmtree(target_dir)

        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)

        print("✅ 解压完成！")

        # 创建标记文件
        (target_dir / "FLET_CACHE_COMPLETE").touch()

        return True

    except Exception as e:
        print(f"❌ 解压失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def copy_flet_to_project(
    target_dir: Path = None,
    project_root: Path = None,
    version: str = FLET_VERSION,
    source: str = DEFAULT_DOWNLOAD_SOURCE
) -> dict:
    """
    下载并复制Flet可执行文件到项目目录

    Args:
        target_dir: 目标目录，默认为项目根目录/flet_browsers
        project_root: 项目根目录
        version: Flet版本号

    Returns:
        dict: 操作结果
            - success: bool, 操作是否成功
            - target_dir: Path, 目标目录路径
            - size_mb: float, 目录大小(MB)
            - error: str, 错误信息(如果失败)
    """
    result = {
        "success": False,
        "target_dir": None,
        "size_mb": 0,
        "error": None
    }

    print("=" * 60)
    print("准备Flet可执行文件")
    print("=" * 60)

    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    # 获取目标目录
    if target_dir is None:
        target_dir = project_root / "flet_browsers"

    try:
        # 1. 下载Flet压缩包（会保存到 download/ 子目录）
        zip_path = download_flet_archive(target_dir, version, source)
        if zip_path is None:
            result["error"] = "下载Flet压缩包失败"
            return result

        # 2. 解压到临时目录
        temp_extract_dir = target_dir / "temp_extract"
        if not extract_flet_archive(zip_path, temp_extract_dir):
            result["error"] = "解压Flet压缩包失败"
            return result

        # 3. 移动到最终位置（unpacked/ 子目录）
        # Flet解压后的结构通常是 flet/flet.exe，还有其他必要的 DLL
        # 我们需要创建两层 flet 目录：app/flet/flet/
        print(f"\n正在组织文件结构...")

        # 查找flet.exe
        flet_exe_candidates = list(temp_extract_dir.rglob("flet.exe"))
        if not flet_exe_candidates:
            result["error"] = "在压缩包中未找到flet.exe"
            return result

        flet_source_dir = flet_exe_candidates[0].parent  # 获取包含flet.exe的目录

        # 创建最终目录结构: target_dir/unpacked/app/flet/flet/
        # 注意：需要两层 flet 目录（app/flet/flet/flet.exe）
        final_dir = target_dir / "unpacked" / "app" / "flet" / "flet"
        final_dir.mkdir(parents=True, exist_ok=True)

        # 复制整个 flet 目录的内容
        for item in flet_source_dir.iterdir():
            if item.is_file():
                dest_file = final_dir / item.name
                shutil.copy2(item, dest_file)
            elif item.is_dir():
                dest_dir = final_dir / item.name
                shutil.copytree(item, dest_dir, dirs_exist_ok=True)

        print(f"✅ 复制Flet目录内容到: {final_dir}")

        final_exe = final_dir / "flet.exe"
        print(f"✅ flet.exe位置: {final_exe}")

        # 4. 清理临时文件
        shutil.rmtree(temp_extract_dir)
        # 注意：不删除zip文件，保留在 download/ 目录中
        print("✅ 清理临时文件完成")

        # 5. 创建完成标记文件
        (target_dir / "unpacked" / "FLET_CACHE_COMPLETE").touch()
        print("✅ 创建完成标记文件")

        # 6. 计算大小（只计算 unpacked 目录）
        unpacked_dir = target_dir / "unpacked"
        total_size = sum(f.stat().st_size for f in unpacked_dir.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)

        print(f"\n✅ Flet准备完成！")
        print(f"📁 目标目录: {unpacked_dir}")
        print(f"📊 大小: {size_mb:.2f} MB")
        print(f"🎯 可执行文件: {final_exe}")
        print("\n" + "=" * 60)

        result["success"] = True
        result["target_dir"] = unpacked_dir
        result["size_mb"] = size_mb
        return result

    except Exception as e:
        error_msg = f"操作失败: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        traceback.print_exc()

        result["error"] = error_msg
        return result


def verify_flet(flet_dir: Path = None, project_root: Path = None) -> bool:
    """
    验证Flet可执行文件是否存在且完整

    Args:
        flet_dir: Flet目录路径（指向flet_browsers目录）
        project_root: 项目根目录

    Returns:
        bool: Flet是否有效
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if flet_dir is None:
        flet_dir = project_root / "flet_browsers"

    # 检查可执行文件是否存在（主要检查）- 在unpacked子目录中
    # 注意：实际路径是 flet_browsers/unpacked/app/flet/flet/flet.exe（有两层 flet）
    flet_exe = flet_dir / "unpacked" / "app" / "flet" / "flet" / "flet.exe"
    if not flet_exe.exists():
        return False

    # 检查文件大小（确保不是空文件）
    if flet_exe.stat().st_size < 1000:  # 至少1KB
        return False

    # 检查关键DLL文件是否存在
    required_dlls = [
        "flutter_windows.dll",
        "audioplayers_windows_plugin.dll",
        "battery_plus_plugin.dll"
    ]

    # 注意：路径是 flet_browsers/unpacked/app/flet/flet/
    flet_app_dir = flet_dir / "unpacked" / "app" / "flet" / "flet"
    for dll in required_dlls:
        dll_path = flet_app_dir / dll
        if not dll_path.exists():
            print(f"⚠️ 缺少必要的DLL文件: {dll}")
            return False

    # 检查标记文件（可选，用于快速验证）
    # 如果没有标记文件但有可执行文件，自动创建标记文件
    marker_file = flet_dir / "unpacked" / "FLET_CACHE_COMPLETE"
    if not marker_file.exists():
        marker_file.touch()

    return True


def get_flet_size(flet_dir: Path = None, project_root: Path = None) -> float:
    """
    获取Flet目录大小

    Args:
        flet_dir: Flet目录路径（指向flet_browsers目录）
        project_root: 项目根目录

    Returns:
        float: 大小(MB)
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if flet_dir is None:
        flet_dir = project_root / "flet_browsers"

    # 只计算 unpacked 目录的大小
    unpacked_dir = flet_dir / "unpacked"
    if not unpacked_dir.exists():
        return 0.0

    total_size = sum(f.stat().st_size for f in unpacked_dir.rglob('*') if f.is_file())
    return total_size / (1024 * 1024)


def ensure_flet_ready(project_root: Path = None, force_copy: bool = False, source: str = DEFAULT_DOWNLOAD_SOURCE) -> dict:
    """
    确保Flet可执行文件已准备就绪

    Args:
        project_root: 项目根目录
        force_copy: 是否强制重新下载
        source: 下载源 ("official" 或 "mirror")

    Returns:
        dict: 操作结果
            - ready: bool, 是否准备就绪
            - copied: bool, 是否进行了下载操作
            - size_mb: float, Flet大小
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    result = {
        "ready": False,
        "copied": False,
        "size_mb": 0
    }

    flet_dir = project_root / "flet_browsers"

    # 如果不强制复制且Flet已存在
    if not force_copy and verify_flet(flet_dir, project_root):
        print("✅ Flet可执行文件已存在且完整")
        result["ready"] = True
        result["size_mb"] = get_flet_size(flet_dir, project_root)
        return result

    # 需要下载Flet
    print(f"📦 正在准备Flet可执行文件（使用 {source} 源）...")
    copy_result = copy_flet_to_project(flet_dir, project_root, source=source)

    if copy_result["success"]:
        result["ready"] = True
        result["copied"] = True
        result["size_mb"] = copy_result["size_mb"]

    return result


def setup_flet_env(project_root: Path = None):
    """
    设置环境变量，使Flet使用本地缓存的版本

    Args:
        project_root: 项目根目录
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    flet_dir = project_root / "flet_browsers"

    # Flet查找可执行文件的路径
    # 设置环境变量指向我们的缓存目录
    # 注意：Flet的内部逻辑可能需要特定的环境变量
    # 这里我们设置FLET_EXECUTABLE_PATH来提示使用本地版本

    # 将flet.exe所在目录添加到PATH（如果需要）
    # flet_exe_dir = str(flet_dir / "app" / "flet")
    # os.environ["PATH"] = flet_exe_dir + os.pathsep + os.environ.get("PATH", "")

    # 更重要：在打包后，Flet会在临时目录查找
    # 我们需要在程序启动时将缓存的flet.exe复制到正确的位置
    return flet_dir


def copy_flet_to_temp_on_startup(project_root: Path = None) -> bool:
    """
    程序启动时，将Flet从项目目录复制到系统临时目录

    这是必要的，因为Flet内部逻辑会在临时目录查找可执行文件

    Args:
        project_root: 项目根目录

    Returns:
        bool: 是否成功
    """
    # 确定项目根目录
    if project_root is None:
        if getattr(sys, 'frozen', False):
            # 打包环境：使用 PyInstaller 的临时目录
            project_root = Path(sys._MEIPASS)
        else:
            # 开发环境：使用模块路径
            project_root = Path(__file__).parent.parent.parent

    # 源目录（项目中的缓存，从unpacked子目录复制）
    source_dir = project_root / "flet_browsers" / "unpacked"
    if not source_dir.exists():
        print(f"⚠️ Flet缓存目录不存在: {source_dir}")
        return False

    # 注意：实际文件在 flet_browsers/unpacked/app/flet/flet/flet.exe
    # 目录结构中有两层 flet
    source_exe = source_dir / "app" / "flet" / "flet" / "flet.exe"
    if not source_exe.exists():
        print(f"⚠️ Flet可执行文件不存在: {source_exe}")
        print(f"💡 请检查: {source_dir}/app/flet/flet/ 目录")
        return False

    # 目标目录（系统临时目录）
    # Flet查找的路径模式: TEMP/_MEI??????/flet_desktop/app/flet/flet.exe
    temp_base = Path(os.environ.get("TEMP", "/tmp"))

    # 查找所有符合模式的 _MEI 目录
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包环境：使用_MEIPASS
        target_base = Path(sys._MEIPASS)
    else:
        # 开发环境：在 TEMP 中查找 _MEI 开头的目录
        mei_dirs = [d for d in temp_base.iterdir() if d.name.startswith('_MEI')]
        if not mei_dirs:
            print("⚠️ 未找到 _MEI 临时目录")
            return False
        # 使用最新的 _MEI 目录
        target_base = max(mei_dirs, key=lambda p: p.stat().st_mtime)

    # 构建目标路径
    target_dir = target_base / "flet_desktop" / "app" / "flet"

    try:
        # 创建目标目录
        target_dir.mkdir(parents=True, exist_ok=True)

        # 复制整个 flet 目录（包含 flet.exe 和所有 DLL）
        # 源目录是 source_dir / "app" / "flet" / "flet"
        source_flet_dir = source_dir / "app" / "flet" / "flet"

        if not source_flet_dir.exists():
            print(f"⚠️ Flet源目录不存在: {source_flet_dir}")
            return False

        # 复制整个目录内容
        for item in source_flet_dir.iterdir():
            dest_item = target_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest_item)
            elif item.is_dir():
                shutil.copytree(item, dest_item, dirs_exist_ok=True)

        target_exe = target_dir / "flet.exe"
        print(f"✅ Flet已复制到临时目录: {target_exe}")
        print(f"📁 包含 {len(list(target_dir.iterdir()))} 个文件/目录")

        return True

    except Exception as e:
        print(f"⚠️ 复制Flet到临时目录失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 测试代码
    print("Flet Handler 测试")
    print("-" * 60)

    # 检查是否已存在
    project_root = Path(__file__).parent.parent.parent
    flet_dir = project_root / "flet_browsers"

    if verify_flet(flet_dir):
        print(f"✅ Flet已存在，大小: {get_flet_size(flet_dir):.2f} MB")
    else:
        print("Flet不存在，开始下载...")
        result = ensure_flet_ready()
        if result["ready"]:
            print(f"✅ Flet准备完成，大小: {result['size_mb']:.2f} MB")
        else:
            print(f"❌ Flet准备失败")
