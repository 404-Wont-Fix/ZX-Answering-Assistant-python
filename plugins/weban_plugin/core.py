"""
WeBan Plugin Core - 安全微伴插件核心功能

提供安全微伴插件的核心业务逻辑
"""

from typing import Optional, Dict, Any
import sys
from pathlib import Path

# 添加插件lib目录到Python路径
plugin_lib_path = Path(__file__).parent / "lib"
if str(plugin_lib_path) not in sys.path:
    sys.path.insert(0, str(plugin_lib_path))

from weban_adapter import get_weban_adapter


class WeBanPluginCore:
    """WeBan 插件核心类"""

    def __init__(self, context):
        """
        初始化插件核心

        Args:
            context: PluginContext 实例
        """
        self.context = context
        self.api_client = context.api_client
        self.browser_manager = context.browser_manager
        self.settings_manager = context.settings_manager

    def validate_tenant(self, tenant_name: str) -> Dict[str, Any]:
        """
        验证学校名称

        Args:
            tenant_name: 学校名称

        Returns:
            验证结果字典
        """
        adapter = get_weban_adapter()
        return adapter.validate_tenant(tenant_name)

    def get_dependencies(self) -> list:
        """
        获取插件依赖列表

        Returns:
            依赖包列表
        """
        return [
            "ddddocr==1.6.1",
            "loguru==0.7.3",
            "pycryptodome==3.23.0",
            "requests==2.32.5",
        ]

    def check_available(self) -> bool:
        """
        检查 WeBan 模块是否可用

        Returns:
            是否可用
        """
        try:
            # 使用 adapter 检查可用性
            adapter = get_weban_adapter()
            return adapter.check_available()
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        """
        获取插件信息

        Returns:
            插件信息字典
        """
        return {
            "id": "weban_plugin",
            "name": "安全微伴",
            "version": "1.0.0",
            "description": "安全微伴自动学习答题插件",
            "author": "TianJiaJi",
        }
