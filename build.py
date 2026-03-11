#!/usr/bin/env python3
"""
ZX Answering Assistant - Build Script

Main build script for creating standalone executables using PyInstaller.

Usage:
    python build.py                    # Build in onedir mode
    python build.py --mode onefile     # Build in onefile mode
    python build.py --mode both        # Build both modes
    python build.py --upx              # Enable UPX compression
    python build.py --clean            # Clean build artifacts
    python build.py --help             # Show help
"""

import argparse
import os
import shutil
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.build_tools import (
    compile_source_to_pyc,
    BrowserBundler,
    FletBundler,
    SpecGenerator,
    generate_version_info,
    print_step, print_success, print_error, print_warning, print_info,
    check_command_exists, get_project_root, ensure_directory, clean_directory,
    get_file_size_human
)


class BuildSystem:
    """
    Main build system orchestrator
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize build system

        Args:
            config_path: Path to build configuration file
        """
        self.project_root = get_project_root()
        self.config_path = config_path or self.project_root / "build_config.yaml"
        self.config = self._load_config()
        self.dist_dir = self.project_root / self.config.get('build', {}).get('output_dir', 'dist')

    def _load_config(self) -> Dict[str, Any]:
        """Load build configuration from YAML file"""
        if not self.config_path.exists():
            print_error(f"Configuration file not found: {self.config_path}")
            print_info("Using default configuration")
            return self._get_default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print_success(f"Loaded configuration from: {self.config_path}")
            return config
        except Exception as e:
            print_error(f"Failed to load configuration: {e}")
            print_info("Using default configuration")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default build configuration"""
        return {
            'build': {
                'mode': 'onedir',
                'output_dir': 'dist',
                'clean_before_build': True
            },
            'pyinstaller': {
                'path': None,
                'options': {
                    'console': True,
                    'debug': False,
                    'strip': True
                }
            },
            'upx': {
                'enabled': False,
                'path': None
            },
            'compilation': {
                'enabled': True,
                'output_dir': 'src_compiled',
                'keep_init_files': True,
                'optimize': 2
            },
            'playwright': {
                'enabled': True,
                'dest_path': 'playwright_browsers'
            },
            'flet': {
                'enabled': True
            },
            'app': {
                'name': 'ZX Answering Assistant',
                'exe_name': 'ZX-Answering-Assistant',
                'icon': None
            },
            'hidden_imports': [
                'playwright.sync_api',
                'playwright.async_api',
                'flet',
                'requests',
                'keyboard'
            ]
        }

    def check_dependencies(self) -> bool:
        """
        Check if all required dependencies are installed

        Returns:
            True if all dependencies are available, False otherwise
        """
        print_step("Checking dependencies...")

        all_ok = True

        # Check PyInstaller
        if not check_command_exists("pyinstaller"):
            print_warning("PyInstaller not found")
            print_info("Installing PyInstaller...")
            if not self._install_pyinstaller():
                all_ok = False
        else:
            print_success("PyInstaller is installed")

        # Check Python packages
        required_packages = ['playwright', 'flet', 'requests', 'keyboard']
        for package in required_packages:
            try:
                __import__(package)
                print_success(f"{package} is installed")
            except ImportError:
                print_error(f"{package} is not installed")
                all_ok = False

        return all_ok

    def _install_pyinstaller(self) -> bool:
        """Install PyInstaller"""
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                check=True,
                capture_output=True
            )
            print_success("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print_error("Failed to install PyInstaller")
            return False

    def clean_build(self) -> bool:
        """
        Clean build artifacts

        Returns:
            True if successful, False otherwise
        """
        print_step("Cleaning build artifacts...")

        directories_to_clean = [
            self.dist_dir,
            self.project_root / "build",
            self.project_root / "*.spec",
            self.project_root / "src_compiled",
            self.project_root / "__pycache__",
        ]

        for directory in directories_to_clean:
            if isinstance(directory, str):
                # Handle glob patterns
                for path in self.project_root.glob(directory):
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                        print_info(f"Removed: {path}")
            elif directory.exists():
                if directory.is_dir():
                    shutil.rmtree(directory, ignore_errors=True)
                    print_info(f"Removed: {directory}")
                else:
                    directory.unlink()
                    print_info(f"Removed: {directory}")

        print_success("Build artifacts cleaned")
        return True

    def compile_sources(self) -> bool:
        """
        Compile Python source files to bytecode

        Returns:
            True if successful, False otherwise
        """
        compilation_config = self.config.get('compilation', {})

        if not compilation_config.get('enabled', False):
            print_info("Source compilation disabled in configuration")
            return True

        source_dir = self.project_root / "src"
        output_dir = self.project_root / compilation_config.get('output_dir', 'src_compiled')

        return compile_source_to_pyc(
            source_dir=source_dir,
            output_dir=output_dir,
            optimize=compilation_config.get('optimize', 2),
            keep_init_files=compilation_config.get('keep_init_files', True),
            remove_source=True
        )

    def bundle_browser(self) -> bool:
        """
        Bundle Playwright browser

        Returns:
            True if successful, False otherwise
        """
        playwright_config = self.config.get('playwright', {})

        if not playwright_config.get('enabled', False):
            print_info("Browser bundling disabled in configuration")
            return True

        bundler = BrowserBundler(self.config)

        # Install browser if needed
        if not bundler.get_browser_path():
            print_info("Installing Playwright browser...")
            bundler.install_playwright()

        return True

    def prepare_flet(self) -> bool:
        """
        Prepare Flet framework

        Returns:
            True if successful, False otherwise
        """
        flet_config = self.config.get('flet', {})

        if not flet_config.get('enabled', False):
            print_info("Flet preparation disabled in configuration")
            return True

        bundler = FletBundler(self.config)
        
        # Try to pre-download Flet desktop executable
        if not bundler.pre_download_flet():
            print_warning("Flet desktop executable will be downloaded on first run")
        
        return bundler.bundle_flet(self.dist_dir)

    def generate_version_file(self) -> Optional[Path]:
        """
        Generate Windows version information file

        Returns:
            Path to version file or None if failed
        """
        app_config = self.config.get('app', {})
        version_config = app_config.get('version', {})

        version = f"{version_config.get('major', 2)}.{version_config.get('minor', 7)}.{version_config.get('micro', 2)}.{version_config.get('build', 0)}"

        return generate_version_info(
            version=version,
            file_description=app_config.get('name', 'ZX Answering Assistant'),
            company_name=app_config.get('company', 'ZX Project'),
            product_name=app_config.get('name', 'ZX Answering Assistant'),
            copyright=app_config.get('copyright', 'Copyright (C) 2024-2026')
        )

    def build(self, mode: str = 'onedir', clean: bool = False, upx: bool = False) -> bool:
        """
        Build the executable

        Args:
            mode: Build mode ('onedir' or 'onefile')
            clean: Clean build artifacts before building
            upx: Enable UPX compression

        Returns:
            True if successful, False otherwise
        """
        print(f"\n{'='*60}")
        print(f"ZX Answering Assistant - Build System")
        print(f"{'='*60}\n")

        # Override config with command-line options
        if clean:
            self.config['build']['clean_before_build'] = True
        if upx:
            self.config['upx']['enabled'] = True

        # Clean build
        if self.config['build'].get('clean_before_build', False):
            self.clean_build()

        # Check dependencies
        if not self.check_dependencies():
            print_error("Dependency check failed")
            return False

        # Pre-build steps
        print_step("Running pre-build steps...")

        # Compile sources
        if not self.compile_sources():
            print_error("Source compilation failed")
            return False

        # Bundle browser
        if not self.bundle_browser():
            print_warning("Browser bundling failed, browser will download on first run")

        # Prepare Flet
        if not self.prepare_flet():
            print_warning("Flet preparation failed")

        # Generate version info
        version_file = self.generate_version_file()

        # Generate spec file
        spec_generator = SpecGenerator(self.config)
        spec_file = spec_generator.generate_spec(mode=mode)

        # Build with PyInstaller
        print_step(f"Building with PyInstaller ({mode} mode)...")
        pyinstaller_args = [
            "pyinstaller",
            spec_file,
            "--clean",
            "--noconfirm"
        ]

        if self.config.get('pyinstaller', {}).get('options', {}).get('debug', False):
            pyinstaller_args.append("--debug")

        try:
            subprocess.run(pyinstaller_args, check=True)
        except subprocess.CalledProcessError as e:
            print_error(f"PyInstaller failed: {e}")
            return False

        # Post-build steps
        print_step("Running post-build steps...")

        # Calculate output size
        if mode == 'onefile':
            exe_name = self.config['app'].get('exe_name', 'ZX-Answering-Assistant') + '.exe'
            exe_path = self.dist_dir / exe_name
        else:
            exe_dir = self.dist_dir / self.config['app'].get('exe_name', 'ZX-Answering-Assistant')
            exe_name = self.config['app'].get('exe_name', 'ZX-Answering-Assistant') + '.exe'
            exe_path = exe_dir / exe_name

        if exe_path.exists():
            size = get_file_size_human(exe_path)
            print_success(f"Built executable: {exe_path} ({size})")
        else:
            print_error("Executable not found after build")
            return False

        print(f"\n{'='*60}")
        print_success("Build completed successfully!")
        print(f"{'='*60}\n")

        return True


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Build ZX Answering Assistant executable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py                    # Build in onedir mode (default)
  python build.py --mode onefile     # Build in onefile mode
  python build.py --mode both        # Build both modes
  python build.py --upx              # Enable UPX compression
  python build.py --clean            # Clean build artifacts only
  python build.py --build-dir CUSTOM  # Custom output directory
        """
    )

    parser.add_argument(
        '--mode',
        choices=['onedir', 'onefile', 'both'],
        default='onedir',
        help='Build mode: onedir (directory), onefile (single executable), or both'
    )

    parser.add_argument(
        '--upx',
        action='store_true',
        help='Enable UPX compression (requires UPX in PATH)'
    )

    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean build artifacts without building'
    )

    parser.add_argument(
        '--build-dir',
        type=str,
        help='Custom build output directory'
    )

    parser.add_argument(
        '--no-compile',
        action='store_true',
        help='Skip source compilation to .pyc'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Initialize build system
    build_system = BuildSystem()

    # Override config with command-line arguments
    if args.build_dir:
        build_system.config['build']['output_dir'] = args.build_dir
        build_system.dist_dir = Path(args.build_dir)

    if args.no_compile:
        build_system.config['compilation']['enabled'] = False

    # Handle clean-only mode
    if args.clean and args.mode == 'onedir':
        # Only clean, don't build
        success = build_system.clean_build()
        if success:
            print_success("Clean completed successfully")
        return 0 if success else 1

    # Build based on mode
    if args.mode == 'both':
        # Build both modes
        success = True
        for mode in ['onedir', 'onefile']:
            if not build_system.build(mode=mode, clean=False, upx=args.upx):
                success = False
        return 0 if success else 1
    else:
        # Build single mode
        success = build_system.build(mode=args.mode, clean=False, upx=args.upx)
        return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_warning("\nBuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Build failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
