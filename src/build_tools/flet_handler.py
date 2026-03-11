"""
Flet Framework Bundler Module

Handles bundling of Flet desktop framework with the executable.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional
from .utils import (
    print_step, print_success, print_error, print_info,
    check_command_exists, get_command_output, ensure_directory
)


class FletBundler:
    """
    Bundles Flet desktop framework for distribution
    """

    def __init__(self, config: dict):
        """
        Initialize Flet bundler

        Args:
            config: Build configuration dictionary
        """
        self.config = config
        self.flet_config = config.get('flet', {})
        self.enabled = self.flet_config.get('enabled', True)

    def get_flet_version(self) -> Optional[str]:
        """
        Get the installed Flet version

        Returns:
            Flet version string or None if not installed
        """
        try:
            import flet
            return flet.__version__
        except ImportError:
            return None

    def check_flet_installed(self) -> bool:
        """
        Check if Flet is installed

        Returns:
            True if Flet is installed, False otherwise
        """
        return self.get_flet_version() is not None

    def bundle_flet(self, output_dir: Path) -> bool:
        """
        Bundle Flet framework with the executable

        Note: Flet automatically downloads the desktop executable on first run.
        This method prepares the environment for offline use if needed.

        Args:
            output_dir: Output directory for bundled Flet

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            print_info("Flet bundling disabled in configuration")
            return True

        print_step("Preparing Flet framework...")

        # Check if Flet is installed
        if not self.check_flet_installed():
            print_error("Flet is not installed")
            print_info("Install with: pip install flet")
            return False

        flet_version = self.get_flet_version()
        print_success(f"Flet version: {flet_version}")

        # Flet will automatically download the desktop executable
        # We just need to ensure it's set up correctly
        print_info("Flet desktop executable will be downloaded on first run")
        print_info("To pre-download, run: flet pack --help")

        return True

    def get_flet_executable_path(self) -> Optional[Path]:
        """
        Get the path to the Flet desktop executable

        Returns:
            Path to Flet executable or None if not found
        """
        # Flet stores its executable in different locations depending on the platform
        possible_paths = []

        if sys.platform == 'win32':
            # Windows
            possible_paths = [
                Path.home() / ".flet" / "bin" / "flet.exe",
                Path(os.environ.get('LOCALAPPDATA', '')) / "Flet" / "flet.exe",
            ]
        elif sys.platform == 'darwin':
            # macOS
            possible_paths = [
                Path.home() / ".flet" / "bin" / "flet",
            ]
        else:
            # Linux
            possible_paths = [
                Path.home() / ".flet" / "bin" / "flet",
                Path.home() / ".local" / "share" / "flet" / "flet",
            ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def pre_download_flet(self) -> bool:
        """
        Pre-download Flet desktop executable for offline use

        Returns:
            True if successful, False otherwise
        """
        print_step("Pre-downloading Flet desktop executable...")

        if not check_command_exists("flet"):
            print_error("Flet CLI not found")
            print_info("Flet will be downloaded on first run")
            return False

        # Try to trigger Flet download by running a simple command
        try:
            import subprocess
            result = subprocess.run(
                ["flet", "--version"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print_success("Flet is ready")
                return True
            else:
                print_warning(f"Flet command failed: {result.stderr}")
                return False

        except Exception as e:
            print_error(f"Failed to pre-download Flet: {e}")
            return False


if __name__ == "__main__":
    # Test Flet bundler
    test_config = {
        'flet': {
            'enabled': True
        }
    }

    bundler = FletBundler(test_config)

    if bundler.check_flet_installed():
        version = bundler.get_flet_version()
        print_success(f"Flet version: {version}")

        # Try to find executable
        exe_path = bundler.get_flet_executable_path()
        if exe_path:
            print_success(f"Flet executable: {exe_path}")
        else:
            print_info("Flet executable will be downloaded on first run")
    else:
        print_error("Flet is not installed")
        print_info("Install with: pip install flet")
