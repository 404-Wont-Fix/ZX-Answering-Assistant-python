"""
Playwright浏览器处理模块
负责复制和验证Playwright浏览器
"""

import shutil
import os
from pathlib import Path
import sys


def copy_browser_to_project(target_dir: Path = None, project_root: Path = None) -> dict:
    """
    复制Playwright浏览器到项目目录

    Args:
        target_dir: 目标目录路径，默认为 project_root/playwright_browsers/chromium-1200
        project_root: 项目根目录，默认为当前脚本所在目录的父目录

    Returns:
        dict: 包含操作结果的字典
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
    print("复制Playwright浏览器到项目目录")
    print("=" * 60)

    # 获取项目根目录
    if project_root is None:
        # 从当前模块位置向上两级到项目根目录
        project_root = Path(__file__).parent.parent.parent

    # 获取目标目录
    if target_dir is None:
        target_dir = project_root / "playwright_browsers" / "chromium-1200"

    try:
        # 获取Playwright浏览器路径
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            print(f"✅ 找到浏览器路径: {browser_path}")

            # 浏览器根目录
            browser_root = Path(browser_path).parent.parent
            print(f"✅ 浏览器根目录: {browser_root}")

            print(f"\n正在复制浏览器到: {target_dir}")
            print("这可能需要几分钟...")

            # 删除旧的浏览器目录
            if target_dir.exists():
                print(f"删除旧的浏览器目录...")
                shutil.rmtree(target_dir)

            # 复制浏览器目录
            shutil.copytree(browser_root, target_dir)

            print(f"\n✅ 浏览器复制完成！")
            print(f"📁 目标目录: {target_dir}")

            # 计算大小
            total_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            print(f"📊 大小: {size_mb:.2f} MB")

            # 创建标记文件
            (target_dir / "INSTALLATION_COMPLETE").touch()
            (target_dir / "DEPENDENCIES_VALIDATED").touch()

            print("\n" + "=" * 60)
            print("✅ 浏览器准备完成！")
            print("=" * 60)

            # 更新结果
            result["success"] = True
            result["target_dir"] = target_dir
            result["size_mb"] = size_mb
            return result

    except Exception as e:
        error_msg = f"复制失败: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        traceback.print_exc()

        result["error"] = error_msg
        return result


def verify_browser(browser_dir: Path = None, project_root: Path = None) -> bool:
    """
    验证Playwright浏览器是否存在且完整

    Args:
        browser_dir: 浏览器目录路径
        project_root: 项目根目录

    Returns:
        bool: 浏览器是否有效
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if browser_dir is None:
        browser_dir = project_root / "playwright_browsers" / "chromium-1200"

    # 检查目录是否存在
    if not browser_dir.exists():
        return False

    # 检查标记文件
    if not (browser_dir / "INSTALLATION_COMPLETE").exists():
        return False

    if not (browser_dir / "DEPENDENCIES_VALIDATED").exists():
        return False

    return True


def get_browser_size(browser_dir: Path = None, project_root: Path = None) -> float:
    """
    获取浏览器目录大小

    Args:
        browser_dir: 浏览器目录路径
        project_root: 项目根目录

    Returns:
        float: 大小(MB)
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    if browser_dir is None:
        browser_dir = project_root / "playwright_browsers" / "chromium-1200"

    if not browser_dir.exists():
        return 0.0

    total_size = sum(f.stat().st_size for f in browser_dir.rglob('*') if f.is_file())
    return total_size / (1024 * 1024)


def ensure_browser_ready(project_root: Path = None, force_copy: bool = False) -> dict:
    """
    确保Playwright浏览器已准备就绪

    Args:
        project_root: 项目根目录
        force_copy: 是否强制重新复制

    Returns:
        dict: 操作结果
            - ready: bool, 是否准备就绪
            - copied: bool, 是否进行了复制操作
            - size_mb: float, 浏览器大小
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    result = {
        "ready": False,
        "copied": False,
        "size_mb": 0
    }

    browser_dir = project_root / "playwright_browsers" / "chromium-1200"

    # 如果不强制复制且浏览器已存在
    if not force_copy and verify_browser(browser_dir, project_root):
        print("✅ Playwright浏览器已存在且完整")
        result["ready"] = True
        result["size_mb"] = get_browser_size(browser_dir, project_root)
        return result

    # 需要复制浏览器
    print("📦 正在准备Playwright浏览器...")
    copy_result = copy_browser_to_project(browser_dir, project_root)

    if copy_result["success"]:
        result["ready"] = True
        result["copied"] = True
        result["size_mb"] = copy_result["size_mb"]

    return result
