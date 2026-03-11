"""
Utility functions for the build system
"""

import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional, List


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in the system PATH

    Args:
        command: Command to check

    Returns:
        True if command exists, False otherwise
    """
    return shutil.which(command) is not None


def get_command_output(command: List[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """
    Run a command and return its output

    Args:
        command: Command to run as a list of strings
        cwd: Working directory (optional)

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def run_command(command: List[str], cwd: Optional[Path] = None, check: bool = True) -> bool:
    """
    Run a command and return success status

    Args:
        command: Command to run as a list of strings
        cwd: Working directory (optional)
        check: Whether to check return code

    Returns:
        True if successful, False otherwise
    """
    try:
        subprocess.run(
            command,
            cwd=cwd,
            check=check,
            encoding='utf-8',
            errors='replace'
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def print_step(message: str):
    """Print a build step message"""
    print(f"\n[STEP] {message}")


def print_success(message: str):
    """Print a success message"""
    print(f"[OK] {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"[ERROR] {message}", file=sys.stderr)


def print_warning(message: str):
    """Print a warning message"""
    print(f"[WARN] {message}")


def print_info(message: str):
    """Print an info message"""
    print(f"[INFO] {message}")


def get_project_root() -> Path:
    """
    Get the project root directory

    Returns:
        Path to project root
    """
    return Path(__file__).parent.parent.parent


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, create if it doesn't

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_directory(path: Path, keep_files: Optional[List[str]] = None):
    """
    Clean a directory by removing all files and subdirectories

    Args:
        path: Directory path to clean
        keep_files: List of filenames to keep (optional)
    """
    if not path.exists():
        return

    keep_files = keep_files or []

    for item in path.iterdir():
        if item.is_file():
            if item.name not in keep_files:
                item.unlink()
        elif item.is_dir():
            shutil.rmtree(item, ignore_errors=True)


def copy_file_or_directory(src: Path, dst: Path):
    """
    Copy a file or directory

    Args:
        src: Source path
        dst: Destination path
    """
    if src.is_file():
        shutil.copy2(src, dst)
    elif src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def get_file_size_human(path: Path) -> str:
    """
    Get human-readable file size

    Args:
        path: File path

    Returns:
        Human-readable size string
    """
    if not path.exists():
        return "N/A"

    size = path.stat().st_size

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

    return f"{size:.2f} TB"
