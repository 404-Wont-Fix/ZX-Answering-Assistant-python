"""
复制Playwright浏览器到项目目录
用于打包时包含浏览器
"""

import shutil
import os
from pathlib import Path
import sys


def copy_browser():
    """复制Playwright浏览器到项目目录"""
    print("=" * 60)
    print("复制Playwright浏览器到项目目录")
    print("=" * 60)
    
    # 获取Playwright浏览器路径
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            print(f"✅ 找到浏览器路径: {browser_path}")
            
            # 浏览器根目录
            browser_root = Path(browser_path).parent.parent
            print(f"✅ 浏览器根目录: {browser_root}")
            
            # 目标目录
            project_root = Path(__file__).parent
            target_dir = project_root / "playwright_browsers" / "chromium-1200"
            
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
            
    except Exception as e:
        print(f"\n❌ 复制失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    copy_browser()