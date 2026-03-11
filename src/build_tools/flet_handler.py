"""
Flet可执行文件处理模块
负责下载和缓存Flet可执行文件用于打包
"""

import os
import zipfile
import shutil
import urllib.request
from pathlib import Path
from typing import Optional


# Flet版本配置
FLET_VERSION = "0.82.2"

# Flet 下载源配置
FLET_DOWNLOAD_SOURCES = {
    "monlor": "https://gh.monlor.com/https://github.com/flet-dev/flet/releases/download/v{version}/flet-windows.zip",
    "nxnow": "https://gh.nxnow.top/https://github.com/flet-dev/flet/releases/download/v{version}/flet-windows.zip",
    "official": "https://github.com/flet-dev/flet/releases/download/v{version}/flet-windows.zip",
}

DEFAULT_DOWNLOAD_SOURCE = "monlor"


def download_flet_archive(target_dir: Path, version: str = FLET_VERSION, source: str = DEFAULT_DOWNLOAD_SOURCE) -> Optional[Path]:
    """下载Flet Windows压缩包"""
    download_dir = target_dir / "download"
    zip_path = download_dir / f"flet-windows-{version}.zip"

    # 检查文件是否已存在并验证
    if zip_path.exists():
        file_size = zip_path.stat().st_size / (1024 * 1024)

        # 验证文件是否是有效的 ZIP 文件
        is_valid_zip = False
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 尝试读取文件列表，如果成功则是有效的 ZIP
                zip_ref.namelist()
                is_valid_zip = True
        except Exception:
            is_valid_zip = False

        print("=" * 60)
        if is_valid_zip:
            print(f"✅ 发现已下载的 Flet v{version} 压缩包")
            print("=" * 60)
            print(f"📁 文件路径: {zip_path}")
            print(f"📊 文件大小: {file_size:.2f} MB")
            print("✅ 文件验证通过，使用已有文件")
            print()
            return zip_path
        else:
            print(f"⚠️ 发现已下载的文件但已损坏")
            print(f"📁 文件路径: {zip_path}")
            print(f"📊 文件大小: {file_size:.2f} MB")
            print("❌ 文件不是有效的 ZIP 格式，将删除并重新下载")
            zip_path.unlink()
            print()

    # 构建下载源列表
    sources_to_try = []
    if source in FLET_DOWNLOAD_SOURCES:
        sources_to_try.append((source, FLET_DOWNLOAD_SOURCES[source]))

    if source != "official":
        sources_to_try.append(("official", FLET_DOWNLOAD_SOURCES["official"]))

    # 尝试下载
    for source_name, url_template in sources_to_try:
        url = url_template.format(version=version)

        print("=" * 60)
        print(f"📥 正在下载 Flet v{version} 可执行文件")
        print("=" * 60)
        print(f"📥 下载源: {source_name}")
        print(f"📥 下载地址: {url}")
        print(f"📁 保存位置: {zip_path}")
        print("⏳ 这可能需要几分钟，请稍候...")

        try:
            download_dir.mkdir(parents=True, exist_ok=True)

            # 使用 requests 代替 urllib.request，支持更好的错误处理
            import requests
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()  # 检查 HTTP 错误

            # 下载文件
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = zip_path.stat().st_size / (1024 * 1024)
            print(f"✅ 下载完成！大小: {file_size:.2f} MB")

            # 验证下载的文件是否是有效的 ZIP
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.namelist()  # 验证文件列表
                print("✅ 文件完整性验证通过")
            except Exception as e:
                print(f"⚠️ 下载的文件验证失败: {e}")
                print("正在删除损坏的文件...")
                zip_path.unlink(missing_ok=True)
                continue

            if file_size < 1:
                print(f"⚠️ 文件过小 ({file_size:.2f} MB)，可能损坏")
                zip_path.unlink(missing_ok=True)
                continue

            return zip_path

        except Exception as e:
            print(f"❌ 从 {source_name} 下载失败: {e}")
            zip_path.unlink(missing_ok=True)

            if len(sources_to_try) > 1 and sources_to_try.index((source_name, url_template)) < len(sources_to_try) - 1:
                print(f"🔄 正在回退到官方源...")
                import time
                time.sleep(1)
            else:
                import traceback
                traceback.print_exc()
                return None

    return None


def extract_flet_archive(zip_path: Path, target_dir: Path) -> bool:
    """解压Flet压缩包"""
    print(f"\n正在解压: {zip_path}")
    print(f"目标目录: {target_dir}")

    try:
        if target_dir.exists():
            shutil.rmtree(target_dir)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)

        print("✅ 解压完成！")
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

    Returns:
        dict: 操作结果
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

    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if target_dir is None:
        target_dir = project_root / "flet_browsers"

    try:
        # 检查是否已存在
        unpacked_dir = target_dir / "unpacked"
        if unpacked_dir.exists() and verify_flet(target_dir, project_root):
            print("=" * 60)
            print("✅ Flet已解压并准备就绪")
            print("=" * 60)
            print(f"📁 解压目录: {unpacked_dir}")
            print("✅ 跳过解压步骤")

            total_size = sum(f.stat().st_size for f in unpacked_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)

            print(f"\n✅ Flet准备完成！")
            print(f"📁 目标目录: {unpacked_dir}")
            print(f"📊 大小: {size_mb:.2f} MB")

            result["success"] = True
            result["target_dir"] = unpacked_dir
            result["size_mb"] = size_mb
            return result

        # 1. 下载Flet压缩包
        zip_path = download_flet_archive(target_dir, version, source)
        if zip_path is None:
            result["error"] = "下载Flet压缩包失败"
            return result

        # 2. 解压到临时目录
        temp_extract_dir = target_dir / "temp_extract"
        if not extract_flet_archive(zip_path, temp_extract_dir):
            result["error"] = "解压Flet压缩包失败"
            return result

        # 3. 移动到最终位置
        print(f"\n正在组织文件结构...")

        flet_exe_candidates = list(temp_extract_dir.rglob("flet.exe"))
        if not flet_exe_candidates:
            result["error"] = "在压缩包中未找到flet.exe"
            return result

        flet_source_dir = flet_exe_candidates[0].parent

        # 创建最终目录结构
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

        # 4. 清理临时文件
        shutil.rmtree(temp_extract_dir)
        print("✅ 清理临时文件完成")

        # 5. 创建完成标记文件
        (target_dir / "unpacked" / "FLET_CACHE_COMPLETE").touch()
        print("✅ 创建完成标记文件")

        # 6. 计算大小
        unpacked_dir = target_dir / "unpacked"
        total_size = sum(f.stat().st_size for f in unpacked_dir.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)

        print(f"\n✅ Flet准备完成！")
        print(f"📁 目标目录: {unpacked_dir}")
        print(f"📊 大小: {size_mb:.2f} MB")

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
    """验证Flet可执行文件是否存在且完整"""
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if flet_dir is None:
        flet_dir = project_root / "flet_browsers"

    # 检查可执行文件是否存在
    flet_exe = flet_dir / "unpacked" / "app" / "flet" / "flet" / "flet.exe"
    if not flet_exe.exists():
        return False

    # 检查文件大小
    if flet_exe.stat().st_size < 1000:
        return False

    return True


def get_flet_size(flet_dir: Path = None, project_root: Path = None) -> float:
    """获取Flet目录大小"""
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if flet_dir is None:
        flet_dir = project_root / "flet_browsers"

    unpacked_dir = flet_dir / "unpacked"
    if not unpacked_dir.exists():
        return 0.0

    total_size = sum(f.stat().st_size for f in unpacked_dir.rglob('*') if f.is_file())
    return total_size / (1024 * 1024)


def ensure_flet_ready(project_root: Path = None, force_copy: bool = False, source: str = DEFAULT_DOWNLOAD_SOURCE) -> dict:
    """确保Flet可执行文件已准备就绪"""
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
