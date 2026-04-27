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

    目标位置（按优先级）：
    1. plugins/weban_plugin/modules/WeBan/ （推荐）
    2. plugins/weban_plugin/WeBan/ （兼容）
    """
    try:
        plugin_dir = Path(__file__).parent

        # WeBan 可能的目标位置
        possible_targets = [
            plugin_dir / "modules" / "WeBan",  # 推荐：modules 目录
            plugin_dir / "WeBan",               # 兼容：插件根目录
        ]

        # 检查是否已有 WeBan
        for target_dir in possible_targets:
            if target_dir.exists() and (target_dir / "api.py").exists():
                logger.debug(f"WeBan 模块已存在于: {target_dir}")
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

        # 优先使用 modules/WeBan 作为目标
        target_dir = plugin_dir / "modules" / "WeBan"
        target_dir.parent.mkdir(exist_ok=True)

        # 尝试创建符号链接（最快，占用空间最小）
        try:
            if target_dir.exists():
                if target_dir.is_dir() and not target_dir.is_symlink():
                    shutil.rmtree(target_dir)
                else:
                    target_dir.unlink()

            # Windows 使用 junction，Unix 使用 symlink
            if sys.platform == 'win32':
                import subprocess
                result = subprocess.run(['mklink', '/J', str(target_dir), str(source_dir)],
                             check=True, shell=True, capture_output=True)
            else:
                target_dir.symlink_to(source_dir)

            logger.info(f"✓ 已创建 WeBan 符号链接: {target_dir} -> {source_dir}")
            return True

        except Exception as link_error:
            # 符号链接失败，尝试复制
            logger.info(f"符号链接失败，尝试复制 WeBan 文件...")
            try:
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                logger.info(f"✓ 已复制 WeBan 到插件目录: {target_dir}")
                return True
            except Exception as copy_error:
                logger.error(f"复制 WeBan 失败: {copy_error}")
                return False

    except Exception as e:
        logger.error(f"自动设置 WeBan 失败: {e}")
        return False


# 在插件导入时自动设置
_auto_setup_weban()


def _setup_weban_import_path():
    """
    设置 WeBan 模块的导入路径

    由于 WeBan/main.py 使用了绝对导入（from client import WeBanClient），
    需要将 WeBan 目录临时添加到 sys.path 以便导入成功。
    """
    try:
        plugin_dir = Path(__file__).parent
        weban_path = plugin_dir / "modules" / "WeBan"

        if weban_path.exists() and (weban_path / "main.py").exists():
            # 将 WeBan 目录添加到 sys.path
            if str(weban_path) not in sys.path:
                sys.path.insert(0, str(weban_path))
                logger.info(f"✓ WeBan 模块路径已添加到 sys.path")
        else:
            # WeBan 不存在，给出详细提示
            logger.warning("=" * 60)
            logger.warning("⚠️  未找到 WeBan 项目代码")
            logger.warning("=" * 60)
            logger.warning("")
            logger.warning("安全微伴插件需要 WeBan 项目代码才能正常工作。")
            logger.warning("")
            logger.warning("请执行以下操作之一：")
            logger.warning("")
            logger.warning("1. 添加 WeBan 为 Git 子模块：")
            logger.warning(f"   cd {plugin_dir.parent.parent}")
            logger.warning(f"   git submodule add <WeBan仓库URL> plugins/weban_plugin/modules/WeBan")
            logger.warning("")
            logger.warning("2. 手动克隆 WeBan 项目：")
            logger.warning(f"   git clone <WeBan仓库URL> {weban_path}")
            logger.warning("")
            logger.warning("3. 复制现有的 WeBan 目录到：")
            logger.warning(f"   {weban_path}")
            logger.warning("")
            logger.warning("=" * 60)
            logger.warning("")
            logger.warning("💡 提示：如果您不需要使用安全微伴功能，可以忽略此警告。")
            logger.warning("")
    except Exception as e:
        logger.error(f"设置 WeBan 导入路径时发生错误: {e}")
        logger.debug(f"错误详情: ", exc_info=True)


# 设置 WeBan 导入路径
_setup_weban_import_path()
