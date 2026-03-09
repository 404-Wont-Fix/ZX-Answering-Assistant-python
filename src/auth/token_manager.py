"""
统一的Token管理器

提供线程安全的token缓存和管理功能，支持学生端、教师端和课程认证token。
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TokenManager:
    """
    统一的Token管理器

    提供线程安全的token存储、获取和过期检查功能。
    支持三种类型的token：学生端、教师端和课程认证。
    """

    def __init__(self):
        """初始化TokenManager"""
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True

        # 学生端token
        self._student_token: Optional[str] = None
        self._student_token_expiry: Optional[float] = None
        self._student_lock = threading.Lock()

        # 教师端token
        self._teacher_token: Optional[str] = None
        self._teacher_token_expiry: Optional[float] = None
        self._teacher_lock = threading.Lock()

        # 课程认证token
        self._certification_token: Optional[str] = None
        self._certification_token_expiry: Optional[float] = None
        self._certification_lock = threading.Lock()

    # ========== 学生端token ==========

    def set_student_token(self, token: str, expiry_seconds: int = 17400):
        """
        设置学生端token

        Args:
            token: 访问令牌
            expiry_seconds: 有效期（秒），默认17400秒（约4.8小时）
        """
        with self._student_lock:
            self._student_token = token
            self._student_token_expiry = time.time() + expiry_seconds
        logger.info("学生端token已缓存")

    def get_student_token(self) -> Optional[str]:
        """
        获取学生端token（自动检查过期）

        Returns:
            有效的token字符串，如果不存在或已过期返回None
        """
        with self._student_lock:
            if self._student_token and self._student_token_expiry:
                if time.time() < self._student_token_expiry:
                    return self._student_token
                else:
                    # Token已过期
                    logger.warning("学生端token已过期")
                    self._student_token = None
                    self._student_token_expiry = None
            return None

    def clear_student_token(self):
        """清除学生端token"""
        with self._student_lock:
            self._student_token = None
            self._student_token_expiry = None
        logger.info("学生端token已清除")

    def is_student_token_valid(self) -> bool:
        """检查学生端token是否有效"""
        with self._student_lock:
            if self._student_token and self._student_token_expiry:
                return time.time() < self._student_token_expiry
            return False

    # ========== 教师端token ==========

    def set_teacher_token(self, token: str, expiry_seconds: int = 17400):
        """
        设置教师端token

        Args:
            token: 访问令牌
            expiry_seconds: 有效期（秒），默认17400秒（约4.8小时）
        """
        with self._teacher_lock:
            self._teacher_token = token
            self._teacher_token_expiry = time.time() + expiry_seconds
        logger.info("教师端token已缓存")

    def get_teacher_token(self) -> Optional[str]:
        """
        获取教师端token（自动检查过期）

        Returns:
            有效的token字符串，如果不存在或已过期返回None
        """
        with self._teacher_lock:
            if self._teacher_token and self._teacher_token_expiry:
                if time.time() < self._teacher_token_expiry:
                    return self._teacher_token
                else:
                    # Token已过期
                    logger.warning("教师端token已过期")
                    self._teacher_token = None
                    self._teacher_token_expiry = None
            return None

    def clear_teacher_token(self):
        """清除教师端token"""
        with self._teacher_lock:
            self._teacher_token = None
            self._teacher_token_expiry = None
        logger.info("教师端token已清除")

    def is_teacher_token_valid(self) -> bool:
        """检查教师端token是否有效"""
        with self._teacher_lock:
            if self._teacher_token and self._teacher_token_expiry:
                return time.time() < self._teacher_token_expiry
            return False

    # ========== 课程认证token ==========

    def set_certification_token(self, token: str, expiry_seconds: int = 17400):
        """
        设置课程认证token

        Args:
            token: 访问令牌
            expiry_seconds: 有效期（秒），默认17400秒（约4.8小时）
        """
        with self._certification_lock:
            self._certification_token = token
            self._certification_token_expiry = time.time() + expiry_seconds
        logger.info("课程认证token已缓存")

    def get_certification_token(self) -> Optional[str]:
        """
        获取课程认证token（自动检查过期）

        Returns:
            有效的token字符串，如果不存在或已过期返回None
        """
        with self._certification_lock:
            if self._certification_token and self._certification_token_expiry:
                if time.time() < self._certification_token_expiry:
                    return self._certification_token
                else:
                    # Token已过期
                    logger.warning("课程认证token已过期")
                    self._certification_token = None
                    self._certification_token_expiry = None
            return None

    def clear_certification_token(self):
        """清除课程认证token"""
        with self._certification_lock:
            self._certification_token = None
            self._certification_token_expiry = None
        logger.info("课程认证token已清除")

    def is_certification_token_valid(self) -> bool:
        """检查课程认证token是否有效"""
        with self._certification_lock:
            if self._certification_token and self._certification_token_expiry:
                return time.time() < self._certification_token_expiry
            return False

    # ========== 通用方法 ==========

    def clear_all_tokens(self):
        """清除所有token"""
        self.clear_student_token()
        self.clear_teacher_token()
        self.clear_certification_token()
        logger.info("所有token已清除")

    def get_status(self) -> dict:
        """
        获取所有token的状态

        Returns:
            包含各token状态信息的字典
        """
        return {
            'student_token_valid': self.is_student_token_valid(),
            'teacher_token_valid': self.is_teacher_token_valid(),
            'certification_token_valid': self.is_certification_token_valid(),
        }


# ========== 便捷函数 ==========

# 全局实例
_token_manager: Optional[TokenManager] = None
_manager_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    """
    获取TokenManager单例

    Returns:
        TokenManager实例
    """
    global _token_manager
    if _token_manager is None:
        with _manager_lock:
            if _token_manager is None:
                _token_manager = TokenManager()
    return _token_manager
