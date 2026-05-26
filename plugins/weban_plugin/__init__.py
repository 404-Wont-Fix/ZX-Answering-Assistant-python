"""
WeBan Plugin - 安全微伴插件

安全微伴自动学习答题插件
"""

import sys
from pathlib import Path
import logging

__version__ = "1.1.0"
__author__ = "TianJiaJi"

logger = logging.getLogger(__name__)


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
            logger.warning("1. 克隆外部 WeBan 模块：")
            logger.warning(f"   git clone <WeBan仓库URL> {weban_path}")
            logger.warning("")
            logger.warning("2. 维护者如需提交为 Git Submodule，请参阅 WEBAN_SUBMODULE_GUIDE.md")
            logger.warning("")
            logger.warning("3. 或复制现有的 WeBan 目录到：")
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
