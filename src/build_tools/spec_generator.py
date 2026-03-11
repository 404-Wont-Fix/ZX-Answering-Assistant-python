"""
PyInstaller Spec File Generator

Generates PyInstaller spec files for building executables.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from .utils import (
    print_step, print_success, print_error, print_info,
    ensure_directory, get_project_root
)


class SpecGenerator:
    """
    Generates PyInstaller spec files based on build configuration
    """

    def __init__(self, config: dict):
        """
        Initialize spec generator

        Args:
            config: Build configuration dictionary
        """
        self.config = config
        self.pyinstaller_config = config.get('pyinstaller', {})
        self.app_config = config.get('app', {})
        self.build_config = config.get('build', {})
        self.upx_config = config.get('upx', {})

    def generate_spec(self, mode: str = 'onedir') -> str:
        """
        Generate a PyInstaller spec file

        Args:
            mode: Build mode ('onedir' or 'onefile')

        Returns:
            Path to generated spec file
        """
        print_step(f"Generating PyInstaller spec file for {mode} mode...")

        project_root = get_project_root()

        # Get configuration values
        exe_name_base = self.app_config.get('exe_name', 'ZX-Answering-Assistant')

        # Get version information
        version_config = self.app_config.get('version', {})
        major = version_config.get('major', 0)
        minor = version_config.get('minor', 0)
        micro = version_config.get('micro', 0)
        version_str = f"{major}.{minor}.{micro}"

        # Add version, platform info and mode suffix to exe/directory name
        # Format: ZX-Answering-Assistant-v2.7.2-windows-x64-installer (onedir)
        #         ZX-Answering-Assistant-v2.7.2-windows-x64-portable (onefile)
        mode_suffix = '-installer' if mode == 'onedir' else '-portable'
        exe_name = f"{exe_name_base}-v{version_str}-windows-x64{mode_suffix}"

        app_name = self.app_config.get('name', 'ZX Answering Assistant')
        icon = self.app_config.get('icon')
        console = self.pyinstaller_config.get('options', {}).get('console', True)

        # Hidden imports
        hidden_imports = self.config.get('hidden_imports', [])

        # Data files
        data_files = self._get_data_files(project_root)

        # Excluded modules
        excluded_modules = self.pyinstaller_config.get('options', {}).get('exclude_modules', [])

        # UPX configuration
        upx_dir = self.upx_config.get('path')
        upx_options = []
        if self.upx_config.get('enabled', False):
            if upx_dir:
                upx_options.append(f'upx_dir={repr(str(upx_dir))}')
            upx_options.append('upx=True')

        # Build the spec file content
        spec_content = self._build_spec_content(
            mode=mode,
            exe_name=exe_name,
            app_name=app_name,
            icon=icon,
            console=console,
            hidden_imports=hidden_imports,
            data_files=data_files,
            excluded_modules=excluded_modules,
            upx_options=upx_options
        )

        # Write spec file
        spec_filename = f"{exe_name_base}_{mode}.spec"
        spec_path = project_root / spec_filename

        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        print_success(f"Spec file generated: {spec_path}")
        return str(spec_path)

    def _get_data_files(self, project_root: Path) -> List[tuple]:
        """
        Get list of data files to include

        Args:
            project_root: Project root directory

        Returns:
            List of (source, destination) tuples
        """
        data_files = []

        # Add version.py
        version_file = project_root / "version.py"
        if version_file.exists():
            data_files.append((str(version_file), "."))

        # Add compiled sources if enabled
        # Note: We don't add compiled files here because PyInstaller needs .py files for analysis
        # The compiled .pyc files will be used at runtime if properly structured
        # For now, skip adding compiled sources to avoid complexity
        pass

        # Add Playwright browser if enabled
        playwright_config = self.config.get('playwright', {})
        if playwright_config.get('enabled', False):
            browser_dest = playwright_config.get('dest_path', 'playwright_browsers')
            browser_source = project_root / "dist" / browser_dest
            if browser_source.exists():
                data_files.append((str(browser_source), browser_dest))

        return data_files

    def _build_spec_content(
        self,
        mode: str,
        exe_name: str,
        app_name: str,
        icon: Optional[str],
        console: bool,
        hidden_imports: List[str],
        data_files: List[tuple],
        excluded_modules: List[str],
        upx_options: List[str]
    ) -> str:
        """
        Build the spec file content

        Returns:
            Spec file content as string
        """
        # Start with block comment
        spec = f'# -*- mode: python ; coding: utf-8 -*-\n'
        spec += f'# PyInstaller spec file for {app_name}\n'
        spec += f'# Generated automatically - DO NOT EDIT\n\n'

        # Build analysis
        spec += self._build_analysis(
            hidden_imports=hidden_imports,
            data_files=data_files,
            excluded_modules=excluded_modules
        )

        # Build PYZ
        spec += '\npyz = PYZ(a.pure)\n\n'

        # Build EXE
        spec += self._build_exe(
            mode=mode,
            exe_name=exe_name,
            app_name=app_name,
            icon=icon,
            console=console,
            upx_options=upx_options
        )

        # Build COLLECT (for onedir mode)
        if mode == 'onedir':
            spec += '\n' + self._build_collect(exe_name=exe_name)

        return spec

    def _build_analysis(
        self,
        hidden_imports: List[str],
        data_files: List[tuple],
        excluded_modules: List[str]
    ) -> str:
        """Build the Analysis block"""
        spec = 'a = Analysis(\n'
        spec += '    ["main.py"],\n'
        spec += '    pathex=[],\n'
        spec += '    binaries=[],\n'
        spec += '    datas=' + repr(data_files) + ',\n'
        spec += '    hiddenimports=' + repr(hidden_imports) + ',\n'
        spec += '    hookspath=[],\n'
        spec += '    hooksconfig={},\n'
        spec += '    runtime_hooks=[],\n'
        spec += '    excludes=' + repr(excluded_modules) + ',\n'
        spec += '    win_no_prefer_redirects=False,\n'
        spec += '    win_private_assemblies=False,\n'
        spec += '    cipher=None,\n'
        spec += '    noarchive=False,\n'
        spec += ')\n\n'

        return spec

    def _build_exe(
        self,
        mode: str,
        exe_name: str,
        app_name: str,
        icon: Optional[str],
        console: bool,
        upx_options: List[str]
    ) -> str:
        """Build the EXE block"""
        spec = 'exe = EXE(\n'
        spec += '    pyz,\n'
        spec += '    a.scripts,\n'

        if mode == 'onefile':
            spec += '    a.binaries,\n'
            spec += '    a.datas,\n'
        else:
            spec += '    [],\n'
            spec += '    [],\n'

        spec += '    [],\n'
        spec += f'    name="{exe_name}",\n'
        spec += f'    debug=False,\n'
        spec += f'    bootloader_ignore_signals=False,\n'
        spec += f'    strip={str(self.pyinstaller_config.get("options", {}).get("strip", True))},\n'
        spec += f'    upx={str(self.upx_config.get("enabled", False))},\n'

        spec += '    runtime_tmpdir=None,\n'

        if icon:
            spec += f'    icon="{icon}",\n'

        spec += '    disable_windowed_traceback=False,\n'
        spec += f'    argv_emulation=False,\n'
        spec += f'    target_arch=None,\n'
        spec += f'    codesign_identity=None,\n'
        spec += f'    entitlements_file=None,\n'
        spec += f'    console={str(console)},\n'
        spec += ')\n'

        return spec

    def _build_collect(self, exe_name: str) -> str:
        """Build the COLLECT block (for onedir mode)"""
        spec = 'coll = COLLECT(\n'
        spec += '    exe,\n'
        spec += '    a.binaries,\n'
        spec += '    a.datas,\n'
        spec += '    strip=False,\n'
        spec += '    upx=False,\n'
        # exe_name already includes version number
        spec += '    name="{exe_name}",\n'.format(exe_name=exe_name)
        spec += ')\n'

        return spec


if __name__ == "__main__":
    # Test spec generator
    test_config = {
        'app': {
            'name': 'ZX Answering Assistant',
            'exe_name': 'ZX-Answering-Assistant',
            'icon': None
        },
        'pyinstaller': {
            'options': {
                'console': True,
                'strip': True,
                'exclude_modules': ['tkinter', 'matplotlib']
            }
        },
        'upx': {
            'enabled': False
        },
        'hidden_imports': ['playwright.sync_api', 'flet', 'requests'],
        'compilation': {
            'enabled': False
        },
        'playwright': {
            'enabled': True
        },
        'build': {
            'mode': 'both'
        }
    }

    generator = SpecGenerator(test_config)

    # Generate both modes
    for mode in ['onedir', 'onefile']:
        spec_path = generator.generate_spec(mode=mode)
        print(f"Generated: {spec_path}")
