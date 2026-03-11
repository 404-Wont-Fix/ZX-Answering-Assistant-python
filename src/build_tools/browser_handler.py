"""
Playwright Browser Bundler Module

Handles bundling of Playwright browser files with the packaged executable.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, List
from .utils import (
    print_step, print_success, print_error, print_warning, print_info,
    check_command_exists, get_command_output, ensure_directory
)


class BrowserBundler:
    """
    Bundles Playwright browser for distribution with the executable
    """

    def __init__(self, config: dict):
        """
        Initialize browser bundler

        Args:
            config: Build configuration dictionary
        """
        self.config = config
        self.playwright_config = config.get('playwright', {})
        self.enabled = self.playwright_config.get('enabled', True)

    def get_browser_path(self) -> Optional[Path]:
        """
        Get the path to Playwright browser installation

        Returns:
            Path to browser directory or None if not found
        """
        print_step("Locating Playwright browser...")

        # Try to get browser path from Playwright
        try:
            import playwright
            playwright_path = Path(playwright.__file__).parent
        except ImportError:
            print_error("Playwright not installed")
            return None

        # Common browser paths
        possible_paths = [
            # Playwright 1.57+ uses different structure
            Path.home() / "AppData" / "Local" / "ms-playwright" if sys.platform == 'win32' else Path.home() / ".cache" / "ms-playwright",
            playwright_path / "driver" / "local-browsers",
        ]

        # Check environment variable
        env_browser_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
        if env_browser_path:
            possible_paths.insert(0, Path(env_browser_path))

        for browser_path in possible_paths:
            if not browser_path.exists():
                continue

            # Check for chromium installation
            chromium_paths = list(browser_path.glob("chromium-*"))
            if chromium_paths:
                browser_dir = chromium_paths[0]
                print_success(f"Found browser at: {browser_dir}")
                return browser_dir

        print_warning("Playwright browser not found")
        print_info("You may need to run: python -m playwright install chromium")
        return None

    def bundle_browser(self, output_dir: Path) -> bool:
        """
        Bundle Playwright browser to output directory

        Args:
            output_dir: Output directory for bundled browser

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            print_info("Browser bundling disabled in configuration")
            return True

        print_step("Bundling Playwright browser...")

        # Get browser source path
        if self.playwright_config.get('source_path'):
            browser_path = Path(self.playwright_config['source_path'])
        else:
            browser_path = self.get_browser_path()

        if not browser_path or not browser_path.exists():
            print_error("Browser source path not found")
            print_info("The browser will be downloaded on first run")
            return False

        # Determine destination path
        dest_path = output_dir / self.playwright_config.get('dest_path', 'playwright_browsers')

        # Create destination directory
        ensure_directory(dest_path)

        # Copy browser files
        print_info(f"Copying browser files to: {dest_path}")
        try:
            # Copy entire browser directory
            for item in browser_path.iterdir():
                dest_item = dest_path / item.name
                if item.is_dir():
                    if dest_item.exists():
                        shutil.rmtree(dest_item)
                    shutil.copytree(item, dest_item)
                else:
                    shutil.copy2(item, dest_item)

            # Calculate size
            total_size = sum(f.stat().st_size for f in dest_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)

            print_success(f"Browser bundled successfully ({size_mb:.1f} MB)")
            return True

        except Exception as e:
            print_error(f"Failed to bundle browser: {e}")
            return False

    def install_playwright(self) -> bool:
        """
        Install Playwright browser using playwright CLI

        Returns:
            True if successful, False otherwise
        """
        print_step("Installing Playwright browser...")

        if not check_command_exists(sys.executable):
            print_error("Python executable not found")
            return False

        # Run playwright install
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print_success("Playwright browser installed successfully")
                return True
            else:
                print_error(f"Installation failed: {result.stderr}")
                return False

        except Exception as e:
            print_error(f"Failed to install browser: {e}")
            return False

    def get_browser_size(self, browser_path: Optional[Path] = None) -> float:
        """
        Get the size of the browser installation in MB

        Args:
            browser_path: Path to browser (auto-detect if None)

        Returns:
            Size in MB
        """
        if browser_path is None:
            browser_path = self.get_browser_path()

        if not browser_path or not browser_path.exists():
            return 0.0

        total_size = sum(f.stat().st_size for f in browser_path.rglob('*') if f.is_file())
        return total_size / (1024 * 1024)


if __name__ == "__main__":
    # Test browser bundler
    test_config = {
        'playwright': {
            'enabled': True,
            'dest_path': 'playwright_browsers'
        }
    }

    bundler = BrowserBundler(test_config)
    browser_path = bundler.get_browser_path()

    if browser_path:
        size = bundler.get_browser_size(browser_path)
        print_info(f"Browser size: {size:.1f} MB")
        print_success("Browser bundler test complete!")
    else:
        print_warning("Browser not found")
        print_info("Install with: python -m playwright install chromium")
