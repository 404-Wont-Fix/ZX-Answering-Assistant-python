"""
源码编译模块
负责将 .py 文件编译为 .pyc 字节码
"""

import shutil
import py_compile
from pathlib import Path


def compile_to_pyc(
    source_dir: Path,
    output_dir: Path,
    exclude_files=None
) -> bool:
    """
    编译源目录下的所有 .py 文件为 .pyc 文件

    Args:
        source_dir: 源代码目录
        output_dir: 编译输出目录
        exclude_files: 要排除的文件列表

    Returns:
        bool: 编译是否成功
    """
    if exclude_files is None:
        exclude_files = []

    source_path = Path(source_dir).absolute()
    output_path = Path(output_dir).absolute()

    print("=" * 60)
    print("预编译源码为 .pyc 字节码")
    print("=" * 60)
    print(f"源目录: {source_path}")
    print(f"输出目录: {output_path}")

    # 清空输出目录
    if output_path.exists():
        print(f"\n🔄 清理旧的编译输出...")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 复制整个目录结构
    print(f"\n📋 复制目录结构...")
    shutil.copytree(source_path, output_path, dirs_exist_ok=True)

    # 收集所有需要编译的 Python 文件
    py_files = []
    for py_file in output_path.rglob("*.py"):
        # 跳过 __pycache__
        if "__pycache__" in str(py_file):
            continue

        rel_path = py_file.relative_to(output_path)

        # __init__.py 必须保留
        if py_file.name == "__init__.py":
            print(f"⏭️  跳过（__init__.py 必须保留）: {rel_path}")
            continue

        # 检查是否在排除列表中
        if any(exclude in str(rel_path) for exclude in exclude_files):
            print(f"⏭️  跳过（排除）: {rel_path}")
            continue

        py_files.append(py_file)

    print(f"\n📦 找到 {len(py_files)} 个文件需要编译")

    if not py_files:
        print("\n⚠️  没有需要编译的文件")
        return True

    # 编译为 .pyc
    print("\n🔧 开始编译...")
    compiled_count = 0
    failed_count = 0

    for py_file in py_files:
        rel_path = py_file.relative_to(output_path)
        try:
            # 编译为 .pyc
            py_compile.compile(str(py_file), optimize=2)
            compiled_count += 1
            print(f"  ✅ {rel_path}")
        except Exception as e:
            failed_count += 1
            print(f"  ❌ {rel_path}: {e}")

    print(f"\n编译完成: {compiled_count} 成功, {failed_count} 失败")

    print("\n" + "=" * 60)
    print("✅ 编译完成！")
    print("=" * 60)
    print(f"编译输出目录: {output_path}")
    print(f"编译文件数: {compiled_count}")

    return True


def clean_source_files(internal_dir: Path) -> int:
    """
    删除打包后目录中的 .py 源码文件（保留 .pyc 和 __init__.py）

    Args:
        internal_dir: 打包后的 _internal 目录路径

    Returns:
        int: 删除的文件数量
    """
    print("\n[INFO] 正在清理打包后的源码文件...")

    if not internal_dir.exists():
        print("[WARN] _internal 目录不存在")
        return 0

    internal_src = internal_dir / "src"
    if not internal_src.exists():
        print("[WARN] _internal/src 目录不存在")
        return 0

    removed_count = 0

    for py_file in internal_src.rglob("*.py"):
        # 保留 __init__.py（包导入需要）
        if py_file.name == "__init__.py":
            continue

        # 删除 .py 文件
        try:
            py_file.unlink()
            removed_count += 1
        except Exception as e:
            print(f"  ⚠️  删除失败: {py_file.relative_to(internal_src)}: {e}")

    print(f"[OK] 已删除 {removed_count} 个 .py 源码文件")
    print(f"[INFO] 保留了 __init__.py 和编译后的 .pyc 文件")

    return removed_count
