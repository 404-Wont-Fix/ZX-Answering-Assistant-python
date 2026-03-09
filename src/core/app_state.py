"""
应用状态管理器

提供线程安全的全局状态管理，替代分散的全局变量。
"""

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AppState:
    """
    应用状态管理器（线程安全单例）

    提供线程安全的get/set/clear方法来管理应用状态。
    用于替代分散在代码各处的全局变量。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化状态管理器"""
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self._data = {}
        self._data_lock = threading.Lock()

    def set(self, key: str, value: Any):
        """
        设置状态

        Args:
            key: 状态键名
            value: 状态值
        """
        with self._data_lock:
            self._data[key] = value
        logger.debug(f"状态已设置: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取状态

        Args:
            key: 状态键名
            default: 默认值（如果键不存在）

        Returns:
            状态值，如果不存在则返回默认值
        """
        with self._data_lock:
            return self._data.get(key, default)

    def clear(self, key: Optional[str] = None):
        """
        清除状态

        Args:
            key: 状态键名，如果为None则清除所有状态
        """
        with self._data_lock:
            if key:
                self._data.pop(key, None)
                logger.debug(f"状态已清除: {key}")
            else:
                self._data.clear()
                logger.debug("所有状态已清除")

    def has(self, key: str) -> bool:
        """
        检查状态是否存在

        Args:
            key: 状态键名

        Returns:
            bool: 状态是否存在
        """
        with self._data_lock:
            return key in self._data

    def get_all(self) -> dict:
        """
        获取所有状态（用于调试）

        Returns:
            dict: 所有状态的副本
        """
        with self._data_lock:
            return self._data.copy()


# ========== 便捷函数 ==========

# 全局实例
_app_state: Optional[AppState] = None
_state_lock = threading.Lock()


def get_app_state() -> AppState:
    """
    获取AppState单例

    Returns:
        AppState实例
    """
    global _app_state
    if _app_state is None:
        with _state_lock:
            if _app_state is None:
                _app_state = AppState()
    return _app_state
