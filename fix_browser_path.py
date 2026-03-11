"""
修复脚本：修复 Playwright 浏览器路径和版本号匹配问题
"""
import shutil
from pathlib import Path
import sys

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def fix_browser_path(dist_dir):
    """
    修复浏览器目录结构和版本号

    确保目录结构为: playwright_browsers/chromium-1208/chrome-win64/
    """
    browsers_dir = Path(dist_dir) / "_internal" / "playwright_browsers"

    if not browsers_dir.exists():
        print(f"[ERROR] 找不到浏览器目录: {browsers_dir}")
        return False

    # 查找所有 chromium-* 目录
    chromium_dirs = list(browsers_dir.glob("chromium-*"))

    if chromium_dirs:
        # 如果已有 chromium-* 目录，检查结构
        print(f"[INFO] 找到 {len(chromium_dirs)} 个 chromium 版本目录")

        for chromium_dir in chromium_dirs:
            print(f"  - {chromium_dir.name}")

            # 检查是否有 chrome-win64
            chrome_win64 = chromium_dir / "chrome-win64"
            chrome_win = chromium_dir / "chrome-win"

            if chrome_win64.exists():
                print(f"[OK] {chromium_dir.name} 结构正确（使用 chrome-win64）")
                return True
            elif chrome_win.exists():
                # 需要重命名为 chrome-win64
                print(f"[INFO] {chromium_dir.name} 使用 chrome-win，需要重命名为 chrome-win64")
                try:
                    shutil.move(str(chrome_win), str(chrome_win64))
                    print(f"[OK] 已重命名为 chrome-win64")
                    return True
                except Exception as e:
                    print(f"[ERROR] 重命名失败: {e}")
                    return False
            else:
                print(f"[WARN] {chromium_dir.name} 下没有找到浏览器目录")

    # 如果没有找到正确的结构，尝试从旧位置修复
    old_dirs = list(browsers_dir.glob("chrome-win*"))

    if not old_dirs:
        print("[INFO] 未找到需要修复的浏览器目录")
        return False

    old_chrome_dir = old_dirs[0]
    print(f"[INFO] 找到旧版本浏览器目录: {old_chrome_dir.name}")

    # 尝试从 manifest 文件中读取版本号
    revision = "1208"  # Playwright 默认版本号
    manifest_files = list(old_chrome_dir.glob("*.manifest"))

    if manifest_files:
        try:
            import json
            import re
            with open(manifest_files[0], 'r') as f:
                manifest = json.load(f)
                # 尝试从 manifest 中提取版本号
                if 'content_version' in manifest:
                    revision = manifest['content_version']
                    print(f"[INFO] 从 manifest 读取到版本号: {revision}")
        except:
            pass

    # 创建新的目录结构
    new_structure_dir = browsers_dir / f"chromium-{revision}"
    new_chrome_dir_name = "chrome-win64"  # 使用 win64
    new_chrome_dir = new_structure_dir / new_chrome_dir_name

    try:
        # 移动到新位置
        print(f"[INFO] 正在移动浏览器到: chromium-{revision}/{new_chrome_dir_name}/")
        shutil.move(str(old_chrome_dir), str(new_chrome_dir))

        print("[OK] 浏览器目录结构修复成功！")
        print(f"\n新路径: {new_chrome_dir}")
        print(f"可执行文件: {new_chrome_dir / 'chrome.exe'}")
        return True

    except Exception as e:
        print(f"[ERROR] 修复失败: {e}")
        print("\n尝试手动修复:")
        print(f"1. 在 {browsers_dir} 下创建目录 chromium-{revision}")
        print(f"2. 将 {old_chrome_dir.name} 重命名并移动到 chromium-{revision}/ 下")
        print(f"3. 确保最终路径为: chromium-{revision}/chrome-win64/")
        return False

if __name__ == "__main__":
    # 默认修复 dist 目录下的第一个版本
    dist_base = Path("dist")
    if not dist_base.exists():
        print("[ERROR] 找不到 dist 目录")
        sys.exit(1)

    # 查找打包后的目录
    version_dirs = [d for d in dist_base.iterdir() if d.is_dir() and d.name.startswith("ZX-")]

    if not version_dirs:
        print("[ERROR] 找不到打包后的版本目录")
        sys.exit(1)

    # 使用第一个找到的版本目录
    target_dir = version_dirs[0]
    print(f"[INFO] 目标目录: {target_dir}")

    if fix_browser_path(target_dir):
        print("\n" + "=" * 60)
        print("[SUCCESS] 修复完成！现在可以运行程序了")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[ERROR] 修复失败")
        print("=" * 60)
        print("\n手动修复步骤:")
        browsers_dir = target_dir / "_internal" / "playwright_browsers"
        print(f"1. 打开目录: {browsers_dir}")
        print("2. 创建目录: chromium-1208")
        print("3. 将 chrome-win 目录移动到 chromium-1208/ 下")
        print("4. 重命名 chrome-win 为 chrome-win64")
        print("5. 最终路径应该是: chromium-1208/chrome-win64/chrome.exe")
