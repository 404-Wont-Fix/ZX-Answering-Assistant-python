"""
构建模块
包含项目打包相关的所有功能
"""

from .browser_handler import (
    copy_browser_to_project,
    verify_browser,
    get_browser_size,
    ensure_browser_ready
)

from .flet_handler import (
    copy_flet_to_project,
    verify_flet,
    get_flet_size,
    ensure_flet_ready,
    setup_flet_env,
    copy_flet_to_temp_on_startup
)

from .common import (
    get_platform_info,
    update_version_info,
    get_dist_name,
    format_size,
    calculate_directory_size
)

from .validator import (
    validate_build,
    validate_build_artifact,
    print_validation_report,
    save_validation_report,
    generate_checksums_file,
    check_disk_space,
    verify_build_dependencies
)

from .minimal_build import (
    get_platform_info as minimal_get_platform_info,
    get_dist_name as minimal_get_dist_name,
    update_version_info as minimal_update_version_info,
    generate_exe_version_file as minimal_generate_exe_version_file,
    build_project_minimal,
    build_all_minimal_variants
)

__all__ = [
    # Common utilities
    "get_platform_info",
    "update_version_info",
    "get_dist_name",
    "format_size",
    "calculate_directory_size",
    # Build validators
    "validate_build",
    "validate_build_artifact",
    "print_validation_report",
    "save_validation_report",
    "generate_checksums_file",
    "check_disk_space",
    "verify_build_dependencies",
    # Browser handlers
    "copy_browser_to_project",
    "verify_browser",
    "get_browser_size",
    "ensure_browser_ready",
    # Flet handlers
    "copy_flet_to_project",
    "verify_flet",
    "get_flet_size",
    "ensure_flet_ready",
    "setup_flet_env",
    "copy_flet_to_temp_on_startup",
    # Minimal build handlers (deprecated, use common functions instead)
    "minimal_get_platform_info",
    "minimal_get_dist_name",
    "minimal_update_version_info",
    "minimal_generate_exe_version_file",
    "build_project_minimal",
    "build_all_minimal_variants"
]
