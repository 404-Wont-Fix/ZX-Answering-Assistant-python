"""
WeBan Plugin - 安全微伴插件

安全微伴自动学习答题插件
"""

import sys
import os
from pathlib import Path
import shutil
import logging

__version__ = "1.1.0"
__author__ = "TianJiaJi"

logger = logging.getLogger(__name__)


def _auto_setup_weban():
    """
    自动设置 WeBan 模块

    如果 WeBan 不存在，尝试从项目根目录复制或链接
    支持多个可能的位置，无需用户手动配置
    """
    try:
        # WeBan 可能的目标位置（插件目录下）
        plugin_dir = Path(__file__).parent
        plugin_weban_dir = plugin_dir / "WeBan"

        # 如果插件目录已有 WeBan，无需处理
        if plugin_weban_dir.exists() and (plugin_weban_dir / "api.py").exists():
            logger.debug("WeBan 模块已存在于插件目录")
            return True

        # 尝试查找项目根目录的 WeBan
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent

        possible_sources = [
            project_root / "WeBan",
            project_root / "submodules" / "WeBan",
            project_root.parent / "WeBan",
        ]

        source_dir = None
        for source in possible_sources:
            if source.exists() and (source / "api.py").exists():
                source_dir = source
                logger.info(f"找到 WeBan 源: {source_dir}")
                break

        if not source_dir:
            logger.warning("未找到 WeBan 源目录，插件将不可用")
            return False

        # 尝试创建符号链接（最快，占用空间最小）
        try:
            if plugin_weban_dir.exists():
                if plugin_weban_dir.is_dir() and not plugin_weban_dir.is_symlink():
                    shutil.rmtree(plugin_weban_dir)
                else:
                    plugin_weban_dir.unlink()

            # Windows 使用 junction，Unix 使用 symlink
            if sys.platform == 'win32':
                import subprocess
                result = subprocess.run(['mklink', '/J', str(plugin_weban_dir), str(source_dir)],
                             check=True, shell=True, capture_output=True)
            else:
                plugin_weban_dir.symlink_to(source_dir)

            logger.info(f"✓ 已创建 WeBan 符号链接: {plugin_weban_dir} -> {source_dir}")
            return True

        except Exception as link_error:
            # 符号链接失败，尝试复制
            logger.info(f"符号链接失败，尝试复制 WeBan 文件...")
            try:
                shutil.copytree(source_dir, plugin_weban_dir, dirs_exist_ok=True)
                logger.info(f"✓ 已复制 WeBan 到插件目录: {plugin_weban_dir}")
                return True
            except Exception as copy_error:
                logger.error(f"复制 WeBan 失败: {copy_error}")
                return False

    except Exception as e:
        logger.error(f"自动设置 WeBan 失败: {e}")
        return False


# 在插件导入时自动设置
_auto_setup_weban()
