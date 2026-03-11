"""
Build Tools Module for ZX Answering Assistant

This module provides utilities for building the application into a standalone
executable using PyInstaller.

Components:
- compile_pyc: Compile Python source to bytecode
- browser_handler: Bundle Playwright browser
- version_info: Generate Windows version resources
- flet_handler: Bundle Flet framework
- spec_generator: Generate PyInstaller spec files
- utils: Common utility functions
"""

from .compile_pyc import compile_source_to_pyc
from .browser_handler import BrowserBundler
from .version_info import generate_version_info
from .flet_handler import FletBundler
from .spec_generator import SpecGenerator
from .utils import (
    check_command_exists,
    get_command_output,
    get_project_root,
    ensure_directory,
    clean_directory,
    get_file_size_human,
    print_step,
    print_success,
    print_error,
    print_warning,
    print_info
)

__all__ = [
    'compile_source_to_pyc',
    'BrowserBundler',
    'generate_version_info',
    'FletBundler',
    'SpecGenerator',
    'check_command_exists',
    'get_command_output',
    'get_project_root',
    'ensure_directory',
    'clean_directory',
    'get_file_size_human',
    'print_step',
    'print_success',
    'print_error',
    'print_warning',
    'print_info'
]
