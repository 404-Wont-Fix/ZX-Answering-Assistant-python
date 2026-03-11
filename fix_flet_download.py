"""
快速修复 Flet 下载问题
清理损坏的文件并重新下载
"""

import os
import sys
from pathlib import Path

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

def main():
    print("=" * 60)
    print("Flet 下载问题修复工具")
    print("=" * 60)

    project_root = Path(__file__).parent
    flet_dir = project_root / "flet_browsers"

    # 1. 删除整个 flet_browsers 目录
    print("\n[1/3] 清理旧的 Flet 文件...")
    if flet_dir.exists():
        import shutil
        print(f"正在删除: {flet_dir}")
        shutil.rmtree(flet_dir)
        print("✅ 清理完成")
    else:
        print("✅ 无需清理（目录不存在）")

    # 2. 重新下载
    print("\n[2/3] 重新下载 Flet...")
    from src.build_tools import ensure_flet_ready

    result = ensure_flet_ready(project_root=project_root, force_copy=True)

    if result["ready"]:
        print(f"\n[OK] Flet 下载成功！大小: {result['size_mb']:.2f} MB")
    else:
        print("\n[ERROR] Flet 下载失败")
        return 1

    # 3. 验证
    print("\n[3/3] 验证下载...")
    from src.build_tools import verify_flet

    if verify_flet(project_root=project_root):
        print("✅ 验证通过！Flet 可执行文件已准备就绪")
        return 0
    else:
        print("❌ 验证失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
