"""
快速版本号修复：创建 chromium-1208 符号链接指向 chromium-1155
"""
import shutil
from pathlib import Path
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def create_version_link(dist_dir):
    browsers_dir = Path(dist_dir) / "_internal" / "playwright_browsers"
    
    # 查找现有的 chromium-* 目录
    chromium_dirs = list(browsers_dir.glob("chromium-*"))
    
    if not chromium_dirs:
        print("[ERROR] 未找到 chromium 目录")
        return False
    
    actual_dir = chromium_dirs[0]
    print(f"[INFO] 实际目录: {actual_dir.name}")
    
    # 检查是否已经存在 chromium-1208
    expected_dir = browsers_dir / "chromium-1208"
    
    if expected_dir.exists():
        print("[OK] chromium-1208 已存在，无需创建链接")
        return True
    
    # 在 Windows 上，我们直接重命名目录而不是创建符号链接
    # 因为符号链接需要管理员权限
    print(f"[INFO] 重命名 {actual_dir.name} -> chromium-1208")
    
    try:
        shutil.move(str(actual_dir), str(expected_dir))
        print(f"[OK] 已重命名为: chromium-1208")
        return True
    except Exception as e:
        print(f"[ERROR] 重命名失败: {e}")
        return False

if __name__ == "__main__":
    dist_base = Path("dist")
    version_dirs = [d for d in dist_base.iterdir() if d.is_dir() and d.name.startswith("ZX-")]
    
    if version_dirs:
        target_dir = version_dirs[0]
        print(f"[INFO] 目标: {target_dir}")
        
        if create_version_link(target_dir):
            print("\n[SUCCESS] 版本号修复完成！")
        else:
            print("\n[ERROR] 版本号修复失败")
    else:
        print("[ERROR] 未找到打包目录")
