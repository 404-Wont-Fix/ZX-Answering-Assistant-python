"""
CLI设置管理模块
负责管理CLI模式的配置，包括账号密码、API请求参数等
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class APIRateLevel(Enum):
    """API请求速率级别"""
    ONE_SECOND = "one_second"      # 1秒延迟
    TWO_SECONDS = "two_seconds"    # 2秒延迟
    THREE_SECONDS = "three_seconds" # 3秒延迟
    FOUR_SECONDS = "four_seconds"   # 4秒延迟

    @classmethod
    def from_name(cls, name: str) -> 'APIRateLevel':
        """从名称获取速率级别"""
        for level in cls:
            if level.value == name.lower():
                return level
        return cls.FOUR_SECONDS  # 默认4秒

    def get_delay_ms(self) -> int:
        """获取延迟毫秒数"""
        delays = {
            APIRateLevel.ONE_SECOND: 1000,
            APIRateLevel.TWO_SECONDS: 2000,
            APIRateLevel.THREE_SECONDS: 3000,
            APIRateLevel.FOUR_SECONDS: 4000
        }
        return delays[self]

    def get_display_name(self) -> str:
        """获取显示名称"""
        names = {
            APIRateLevel.ONE_SECOND: "1秒",
            APIRateLevel.TWO_SECONDS: "2秒",
            APIRateLevel.THREE_SECONDS: "3秒",
            APIRateLevel.FOUR_SECONDS: "4秒"
        }
        return names[self]


class SettingsManager:
    """设置管理器"""

    def __init__(self, config_file: str = None):
        """
        初始化设置管理器

        Args:
            config_file: 配置文件路径，默认为项目根目录下的 cli_config.json
        """
        if config_file is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            config_file = project_root / "cli_config.json"

        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}")
                return self._get_default_config()
        else:
            # 创建默认配置文件
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "credentials": {
                "student": {
                    "username": "",
                    "password": ""
                },
                "teacher": {
                    "username": "",
                    "password": ""
                }
            },
            "api_settings": {
                "max_retries": 3,
                "rate_level": "four_seconds"
            }
        }

    def get_student_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        获取学生端凭据

        Returns:
            tuple: (username, password)，如果未设置则返回 (None, None)
        """
        username = self.config.get("credentials", {}).get("student", {}).get("username", "")
        password = self.config.get("credentials", {}).get("student", {}).get("password", "")
        return (username if username else None, password if password else None)

    def set_student_credentials(self, username: str, password: str) -> bool:
        """
        设置学生端凭据

        Args:
            username: 用户名
            password: 密码

        Returns:
            bool: 是否保存成功
        """
        if "credentials" not in self.config:
            self.config["credentials"] = {}
        if "student" not in self.config["credentials"]:
            self.config["credentials"]["student"] = {}

        self.config["credentials"]["student"]["username"] = username
        self.config["credentials"]["student"]["password"] = password

        return self._save_config(self.config)

    def clear_student_credentials(self) -> bool:
        """
        清除学生端凭据

        Returns:
            bool: 是否清除成功
        """
        if "credentials" not in self.config:
            self.config["credentials"] = {}
        if "student" not in self.config["credentials"]:
            self.config["credentials"]["student"] = {}

        self.config["credentials"]["student"]["username"] = ""
        self.config["credentials"]["student"]["password"] = ""

        return self._save_config(self.config)

    def get_teacher_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        获取教师端凭据

        Returns:
            tuple: (username, password)，如果未设置则返回 (None, None)
        """
        username = self.config.get("credentials", {}).get("teacher", {}).get("username", "")
        password = self.config.get("credentials", {}).get("teacher", {}).get("password", "")
        return (username if username else None, password if password else None)

    def set_teacher_credentials(self, username: str, password: str) -> bool:
        """
        设置教师端凭据

        Args:
            username: 用户名
            password: 密码

        Returns:
            bool: 是否保存成功
        """
        if "credentials" not in self.config:
            self.config["credentials"] = {}
        if "teacher" not in self.config["credentials"]:
            self.config["credentials"]["teacher"] = {}

        self.config["credentials"]["teacher"]["username"] = username
        self.config["credentials"]["teacher"]["password"] = password

        return self._save_config(self.config)

    def clear_teacher_credentials(self) -> bool:
        """
        清除教师端凭据

        Returns:
            bool: 是否清除成功
        """
        if "credentials" not in self.config:
            self.config["credentials"] = {}
        if "teacher" not in self.config["credentials"]:
            self.config["credentials"]["teacher"] = {}

        self.config["credentials"]["teacher"]["username"] = ""
        self.config["credentials"]["teacher"]["password"] = ""

        return self._save_config(self.config)

    def get_max_retries(self) -> int:
        """
        获取API请求最大重试次数

        Returns:
            int: 最大重试次数
        """
        return self.config.get("api_settings", {}).get("max_retries", 3)

    def set_max_retries(self, max_retries: int) -> bool:
        """
        设置API请求最大重试次数

        Args:
            max_retries: 最大重试次数

        Returns:
            bool: 是否设置成功
        """
        if not isinstance(max_retries, int) or max_retries < 0:
            print("❌ 重试次数必须是非负整数")
            return False

        if "api_settings" not in self.config:
            self.config["api_settings"] = {}

        self.config["api_settings"]["max_retries"] = max_retries

        return self._save_config(self.config)

    def get_rate_level(self) -> APIRateLevel:
        """
        获取API请求速率级别

        Returns:
            APIRateLevel: 速率级别
        """
        rate_level_name = self.config.get("api_settings", {}).get("rate_level", "medium")
        return APIRateLevel.from_name(rate_level_name)

    def set_rate_level(self, rate_level: APIRateLevel) -> bool:
        """
        设置API请求速率级别

        Args:
            rate_level: 速率级别

        Returns:
            bool: 是否设置成功
        """
        if not isinstance(rate_level, APIRateLevel):
            print("❌ 无效的速率级别")
            return False

        if "api_settings" not in self.config:
            self.config["api_settings"] = {}

        self.config["api_settings"]["rate_level"] = rate_level.value

        return self._save_config(self.config)

    def display_current_settings(self):
        """显示当前设置"""
        print("\n" + "=" * 50)
        print("📋 当前设置")
        print("=" * 50)

        # 学生端凭据
        student_username, student_password = self.get_student_credentials()
        print(f"\n👤 学生端账号:")
        if student_username:
            masked_user = student_username[:3] + "****" if len(student_username) > 3 else "****"
            masked_pass = "****" if student_password else "(空)"
            print(f"   用户名: {masked_user}")
            print(f"   密码: {masked_pass}")
            print(f"   状态: ✅ 已设置")
        else:
            print(f"   状态: ❌ 未设置")

        # 教师端凭据
        teacher_username, teacher_password = self.get_teacher_credentials()
        print(f"\n👨‍🏫 教师端账号:")
        if teacher_username:
            masked_user = teacher_username[:3] + "****" if len(teacher_username) > 3 else "****"
            masked_pass = "****" if teacher_password else "(空)"
            print(f"   用户名: {masked_user}")
            print(f"   密码: {masked_pass}")
            print(f"   状态: ✅ 已设置")
        else:
            print(f"   状态: ❌ 未设置")

        # API设置
        rate_level = self.get_rate_level()
        max_retries = self.get_max_retries()
        print(f"\n⚙️ API设置:")
        print(f"   请求速率: {rate_level.get_display_name()}")
        print(f"   最大重试次数: {max_retries}")

        print("\n" + "=" * 50)


# 创建全局设置管理器实例
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """获取全局设置管理器实例"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager
