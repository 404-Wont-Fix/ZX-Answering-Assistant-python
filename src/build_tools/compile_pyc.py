"""
Python Source Code Compiler Module

Compiles Python source files (.py) to bytecode (.pyc) and optionally
removes the source files for distribution.
"""

import os
import sys
import shutil
import compileall
from pathlib import Path
from typing import Optional, List
from .utils import print_step, print_success, print_error, print_warning, print_info, ensure_directory


def compile_source_to_pyc(
    source_dir: Path,
    output_dir: Optional[Path] = None,
    optimize: int = 2,
    keep_init_files: bool = True,
    remove_source: bool = True
) -> bool:
    """
    Compile Python source files to bytecode (.pyc)

    Args:
        source_dir: Source directory containing .py files
        output_dir: Output directory for compiled files (defaults to source_dir)
        optimize: Optimization level (0, 1, or 2)
        keep_init_files: Keep __init__.py files (required for package imports)
        remove_source: Remove .py files after compilation

    Returns:
        True if successful, False otherwise
    """
    print_step("Compiling Python source to bytecode...")

    source_dir = Path(source_dir).resolve()
    if not source_dir.exists():
        print_error(f"Source directory not found: {source_dir}")
        return False

    # Use output directory or compile in-place
    if output_dir is None:
        output_dir = source_dir
    else:
        output_dir = Path(output_dir).resolve()
        ensure_directory(output_dir)
        # Copy source directory to output directory
        if output_dir != source_dir:
            print_step(f"Copying source files to {output_dir}...")
            if output_dir.exists():
                shutil.rmtree(output_dir)
            shutil.copytree(source_dir, output_dir,
                           ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

    print_info(f"Compiling files in: {output_dir}")
    print_info(f"Optimization level: {optimize}")

    # Compile the directory
    try:
        # Compile with optimization
        result = compileall.compile_dir(
            output_dir,
            optimize=optimize,
            force=True,
            quiet=0,
            legacy=False
        )

        if not result:
            print_error("Compilation failed")
            return False

        print_success(f"Compilation complete")

        # Remove .py files if requested
        if remove_source:
            print_step("Removing source files...")
            removed_count = 0
            kept_count = 0

            for py_file in output_dir.rglob("*.py"):
                # Keep __init__.py files if requested
                if keep_init_files and py_file.name == "__init__.py":
                    kept_count += 1
                    continue

                # Remove the source file
                py_file.unlink()
                removed_count += 1

            print_success(f"Removed {removed_count} source files")
            if kept_count > 0:
                print_info(f"Kept {kept_count} __init__.py files (required for imports)")

        return True

    except Exception as e:
        print_error(f"Compilation error: {e}")
        return False


def verify_compiled_directory(directory: Path) -> tuple[int, int]:
    """
    Verify that a directory has been compiled correctly

    Args:
        directory: Directory to verify

    Returns:
        Tuple of (pyc_count, py_count)
    """
    pyc_count = len(list(directory.rglob("*.pyc")))
    py_count = len(list(directory.rglob("*.py")))

    return pyc_count, py_count


if __name__ == "__main__":
    # Test compilation
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src"
    output_dir = project_root / "src_compiled"

    success = compile_source_to_pyc(
        source_dir=src_dir,
        output_dir=output_dir,
        optimize=2,
        keep_init_files=True,
        remove_source=True
    )

    if success:
        print_step("\nVerifying compilation...")
        pyc_count, py_count = verify_compiled_directory(output_dir)
        print_info(f"Compiled files: {pyc_count}")
        print_info(f"Remaining .py files: {py_count}")
        print_success("Compilation test complete!")
    else:
        sys.exit(1)
