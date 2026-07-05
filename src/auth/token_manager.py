"""
统一的Token管理器

提供线程安全的token缓存和管理功能，支持学生端、教师端和课程认证token。
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class _TokenSlot:
    """单个token存储槽，线程安全"""

    __slots__ = ('_name', '_token', '_expiry', '_lock')

    def __init__(self, name: str):
        self._name = name
        self._token: Optional[str] = None
        self._expiry: Optional[float] = None
        self._lock = threading.Lock()

    def set(self, token: str, expiry_seconds: int = 17400):
        """设置token"""
        with self._lock:
            self._token = token
            self._expiry = time.time() + expiry_seconds
        logger.info(f"{self._name}token已缓存")

    def get(self) -> Optional[str]:
        """获取token（自动检查过期）"""
        with self._lock:
            if self._token and self._expiry:
                if time.time() < self._expiry:
                    return self._token
                else:
                    logger.warning(f"{self._name}token已过期")
                    self._token = None
                    self._expiry = None
            return None

    def clear(self):
        """清除token"""
        with self._lock:
            self._token = None
            self._expiry = None
        logger.info(f"{self._name}token已清除")

    def is_valid(self) -> bool:
        """检查token是否有效"""
        with self._lock:
            if self._token and self._expiry:
                return time.time() < self._expiry
            return False


class TokenManager:
    """
    统一的Token管理器

    提供线程安全的token存储、获取和过期检查功能。
    支持三种类型的token：学生端、教师端和课程认证。
    """

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        self._student = _TokenSlot("学生端")
        self._teacher = _TokenSlot("教师端")
        self._certification = _TokenSlot("课程认证")

    # ========== 学生端token ==========

    def set_student_token(self, token: str, expiry_seconds: int = 17400):
        self._student.set(token, expiry_seconds)

    def get_student_token(self) -> Optional[str]:
        return self._student.get()

    def clear_student_token(self):
        self._student.clear()

    def is_student_token_valid(self) -> bool:
        return self._student.is_valid()

    # ========== 教师端token ==========

    def set_teacher_token(self, token: str, expiry_seconds: int = 17400):
        self._teacher.set(token, expiry_seconds)

    def get_teacher_token(self) -> Optional[str]:
        return self._teacher.get()

    def clear_teacher_token(self):
        self._teacher.clear()

    def is_teacher_token_valid(self) -> bool:
        return self._teacher.is_valid()

    # ========== 课程认证token ==========

    def set_certification_token(self, token: str, expiry_seconds: int = 17400):
        self._certification.set(token, expiry_seconds)

    def get_certification_token(self) -> Optional[str]:
        return self._certification.get()

    def clear_certification_token(self):
        self._certification.clear()

    def is_certification_token_valid(self) -> bool:
        return self._certification.is_valid()

    # ========== 通用方法 ==========

    def clear_all_tokens(self):
        """清除所有token"""
        self._student.clear()
        self._teacher.clear()
        self._certification.clear()
        logger.info("所有token已清除")

    def get_status(self) -> dict:
        """获取所有token的状态"""
        return {
            'student_token_valid': self._student.is_valid(),
            'teacher_token_valid': self._teacher.is_valid(),
            'certification_token_valid': self._certification.is_valid(),
        }


# ========== 便捷函数 ==========

_token_manager: Optional[TokenManager] = None
_manager_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    """获取TokenManager单例"""
    global _token_manager
    if _token_manager is None:
        with _manager_lock:
            if _token_manager is None:
                _token_manager = TokenManager()
    return _token_manager
