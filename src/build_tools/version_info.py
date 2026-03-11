"""
Windows Version Information Generator

Generates version information for Windows executables using PyInstaller's
--version-file feature.
"""

import sys
import struct
from pathlib import Path
from typing import Dict, Any, Optional
from .utils import print_step, print_success, print_error, print_info


def generate_version_info(
    version: str,
    file_description: str,
    company_name: str,
    product_name: str,
    copyright: str,
    output_file: Optional[Path] = None
) -> Path:
    """
    Generate a Windows version information file

    Args:
        version: Version string (e.g., "2.7.2")
        file_description: File description
        company_name: Company name
        product_name: Product name
        copyright: Copyright string
        output_file: Output file path (auto-generate if None)

    Returns:
        Path to generated version file
    """
    print_step("Generating Windows version information...")

    # Parse version string
    version_parts = version.split(".")
    major = int(version_parts[0]) if len(version_parts) > 0 else 2
    minor = int(version_parts[1]) if len(version_parts) > 1 else 7
    micro = int(version_parts[2]) if len(version_parts) > 2 else 0
    build = int(version_parts[3]) if len(version_parts) > 3 else 0

    # Version info as binary data
    version_info = create_version_info_struct(
        major=major,
        minor=minor,
        micro=micro,
        build=build,
        file_description=file_description,
        company_name=company_name,
        product_name=product_name,
        copyright=copyright
    )

    # Determine output file path
    if output_file is None:
        project_root = Path(__file__).parent.parent.parent
        output_file = project_root / "file_version_info.txt"

    # Write version info to file
    with open(output_file, 'wb') as f:
        f.write(version_info)

    print_success(f"Version info written to: {output_file}")
    print_info(f"Version: {major}.{minor}.{micro}.{build}")
    print_info(f"Description: {file_description}")

    return output_file


def create_version_info_struct(
    major: int,
    minor: int,
    micro: int,
    build: int,
    file_description: str,
    company_name: str,
    product_name: str,
    copyright: str
) -> bytes:
    """
    Create version information structure

    Returns:
        Binary data for version file
    """
    # For simplicity, use PyInstaller's built-in version info generation
    # Return a simple text-based version file instead
    version_text = f"""# UTF-8
#
# For more details about fixed file info:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {micro}, {build}),
    prodvers=({major}, {minor}, {micro}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{company_name}'),
        StringStruct(u'FileDescription', u'{file_description}'),
        StringStruct(u'FileVersion', u'{major}.{minor}.{micro}.{build}'),
        StringStruct(u'InternalName', u'{product_name}'),
        StringStruct(u'LegalCopyright', u'{copyright}'),
        StringStruct(u'OriginalFilename', u'{product_name}.exe'),
        StringStruct(u'ProductName', u'{product_name}'),
        StringStruct(u'ProductVersion', u'{major}.{minor}.{micro}.{build}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    return version_text.encode('utf-8')


def load_version_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load version information from build config

    Args:
        config: Build configuration dictionary

    Returns:
        Dictionary with version information
    """
    app_config = config.get('app', {})
    version_config = app_config.get('version', {})

    return {
        'version': f"{version_config.get('major', 2)}.{version_config.get('minor', 7)}.{version_config.get('micro', 2)}.{version_config.get('build', 0)}",
        'file_description': app_config.get('name', 'ZX Answering Assistant'),
        'company_name': app_config.get('company', 'ZX Project'),
        'product_name': app_config.get('name', 'ZX Answering Assistant'),
        'copyright': app_config.get('copyright', 'Copyright (C) 2024-2026')
    }


if __name__ == "__main__":
    # Test version info generation
    version_info = {
        'version': '2.7.2',
        'file_description': '智能答题助手 - 自动化答题系统',
        'company_name': 'ZX Project',
        'product_name': 'ZX Answering Assistant',
        'copyright': 'Copyright (C) 2024-2026'
    }

    output_file = generate_version_info(**version_info)
    print_success(f"Test version info file created: {output_file}")
