"""
WeBan Module Adapter

This module provides an isolated adapter for the WeBan submodule,
ensuring code separation and independent functionality.
"""

import sys
import os
from pathlib import Path
import json
import threading
from typing import Optional, Callable, List, Dict, Any

# 添加 WeBan 模块路径
weban_path = Path(__file__).parent / "WeBan"
if str(weban_path) not in sys.path:
    sys.path.insert(0, str(weban_path))

try:
    from client import WeBanClient
    from api import WeBanAPI
    WEBAN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ WeBan 模块导入失败: {e}")
    WEBAN_AVAILABLE = False
    WeBanClient = None
    WeBanAPI = None


class WeBanAdapter:
    """
    WeBan 模块适配器

    提供与主项目隔离的 WeBan 功能接口
    """

    def __init__(self, progress_callback: Optional[Callable[[str, str], None]] = None):
        """
        初始化适配器

        Args:
            progress_callback: 进度回调函数，参数 (message: str, level: str)
                level 可选值: "info", "success", "warning", "error"
        """
        self.progress_callback = progress_callback or self._default_callback
        self.is_running = False
        self._stop_event = threading.Event()
        self._config: List[Dict[str, Any]] = []

    def _default_callback(self, message: str, level: str = "info"):
        """默认进度回调"""
        prefix_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        print(f"{prefix_map.get(level, 'ℹ️')} {message}")

    def _log(self, message: str, level: str = "info"):
        """发送日志到回调"""
        try:
            self.progress_callback(message, level)
        except Exception as e:
            print(f"回调函数执行失败: {e}")
            self._default_callback(message, level)

    def check_available(self) -> bool:
        """检查 WeBan 模块是否可用"""
        return WEBAN_AVAILABLE

    def get_dependencies(self) -> List[str]:
        """获取 WeBan 模块依赖"""
        return [
            "ddddocr==1.6.1",
            "loguru==0.7.3",
            "pycryptodome==3.23.0",
            "requests==2.32.5",
        ]

    def load_config(self, config: List[Dict[str, Any]]) -> bool:
        """
        加载配置

        Args:
            config: WeBan 配置列表，格式参考 WeBan 的 config.json

        Returns:
            是否加载成功
        """
        if not config:
            self._log("配置为空", "error")
            return False

        # 验证配置格式
        required_fields = ["tenant_name"]
        for i, account_config in enumerate(config):
            for field in required_fields:
                if field not in account_config:
                    self._log(f"账号 {i+1} 缺少必要字段: {field}", "error")
                    return False

            # 检查是否有有效的登录信息
            has_password = all([
                account_config.get("account"),
                account_config.get("password"),
            ])
            has_token = all([
                account_config.get("user", {}).get("userId"),
                account_config.get("user", {}).get("token"),
            ])

            if not (has_password or has_token):
                self._log(f"账号 {i+1} 缺少登录信息（账号密码或 Token）", "error")
                return False

        self._config = config
        self._log(f"已加载 {len(config)} 个账号配置", "success")
        return True

    def validate_tenant(self, tenant_name: str) -> Dict[str, Any]:
        """
        验证学校名称

        Args:
            tenant_name: 学校名称

        Returns:
            验证结果，格式: {"success": bool, "message": str, "data": dict}
        """
        if not WEBAN_AVAILABLE:
            return {
                "success": False,
                "message": "WeBan 模块不可用，请检查依赖是否安装",
                "data": {}
            }

        try:
            client = WeBanClient(tenant_name=tenant_name, log=self)
            # WeBanClient 在初始化时会自动获取学校代码
            # 如果成功，tenant_code 会被设置
            if client.tenant_code:
                return {
                    "success": True,
                    "message": f"学校验证成功: {tenant_name} ({client.tenant_code})",
                    "data": {"tenant_code": client.tenant_code}
                }
            else:
                return {
                    "success": False,
                    "message": f"未找到学校: {tenant_name}",
                    "data": {}
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"验证失败: {str(e)}",
                "data": {}
            }

    def run_account(self, config: Dict[str, Any], account_index: int) -> bool:
        """
        运行单个账号的任务

        Args:
            config: 账号配置
            account_index: 账号索引

        Returns:
            是否执行成功
        """
        if self._stop_event.is_set():
            self._log(f"账号 {account_index+1}: 用户中断", "warning")
            return False

        if not WEBAN_AVAILABLE:
            self._log("WeBan 模块不可用", "error")
            return False

        tenant_name = config.get("tenant_name", "").strip()
        account = config.get("account", "").strip()
        password = config.get("password", "").strip()
        user = config.get("user", {})
        study = config.get("study", True)
        study_time = int(config.get("study_time", 20))
        restudy_time = int(config.get("restudy_time", 0))
        exam = config.get("exam", True)
        exam_use_time = int(config.get("exam_use_time", 250))

        if user.get("tenantName"):
            tenant_name = user["tenantName"]

        try:
            self._log(f"[账号 {account_index+1}] 开始执行", "info")

            if all([tenant_name, user.get("userId"), user.get("token")]):
                self._log(f"[账号 {account_index+1}] 使用 Token 登录", "info")
                client = WeBanClient(tenant_name, user=user, log=self)
            elif all([tenant_name, account, password]):
                self._log(f"[账号 {account_index+1}] 使用密码登录", "info")
                client = WeBanClient(tenant_name, account, password, log=self)
            else:
                self._log(f"[账号 {account_index+1}] 缺少必要的配置信息", "error")
                return False

            if not client.login():
                self._log(f"[账号 {account_index+1}] 登录失败", "error")
                return False

            self._log(f"[账号 {account_index+1}] 登录成功，开始同步答案", "info")
            client.sync_answers()

            if study:
                self._log(f"[账号 {account_index+1}] 开始学习 (每个任务时长: {study_time}秒)", "info")
                client.run_study(study_time, restudy_time)

            if exam:
                self._log(f"[账号 {account_index+1}] 开始考试 (总时长: {exam_use_time}秒)", "info")
                client.run_exam(exam_use_time)

            self._log(f"[账号 {account_index+1}] 最终同步答案", "info")
            client.sync_answers()

            self._log(f"[账号 {account_index+1}] 执行完成", "success")
            return True

        except PermissionError as e:
            self._log(f"[账号 {account_index+1}] 权限错误: {e}", "error")
            return False
        except RuntimeError as e:
            self._log(f"[账号 {account_index+1}] 运行时错误: {e}", "error")
            return False
        except ValueError as e:
            self._log(f"[账号 {account_index+1}] 参数错误: {e}", "error")
            return False
        except Exception as e:
            self._log(f"[账号 {account_index+1}] 运行失败: {e}", "error")
            return False

    def start(self, use_multithread: bool = True) -> Dict[str, int]:
        """
        开始执行所有账号任务

        Args:
            use_multithread: 是否使用多线程（仅在有多个账号时生效）

        Returns:
            执行结果统计，格式: {"success": int, "failed": int}
        """
        if not self._config:
            self._log("没有可执行的账号配置", "error")
            return {"success": 0, "failed": 0}

        self.is_running = True
        self._stop_event.clear()

        self._log(f"开始执行，共 {len(self._config)} 个账号", "info")

        success_count = 0
        failed_count = 0

        if use_multithread and len(self._config) > 1:
            # 多线程执行
            from concurrent.futures import as_completed, ThreadPoolExecutor

            max_workers = min(len(self._config), 5)  # 限制最大线程数为5
            self._log(f"使用多线程模式，最大并发数: {max_workers}", "info")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_account = {
                    executor.submit(self.run_account, config, i): (config, i)
                    for i, config in enumerate(self._config)
                }

                for future in as_completed(future_to_account):
                    config, account_index = future_to_account[future]
                    try:
                        success = future.result()
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self._log(f"[账号 {account_index+1}] 线程执行异常: {e}", "error")
                        failed_count += 1

        else:
            # 单线程执行
            self._log("使用单线程模式，逐个执行", "info")
            for i, config in enumerate(self._config):
                if self._stop_event.is_set():
                    break
                success = self.run_account(config, i)
                if success:
                    success_count += 1
                else:
                    failed_count += 1

        self.is_running = False
        self._log(f"所有账号执行完成！成功: {success_count}，失败: {failed_count}",
                  "success" if failed_count == 0 else "warning")

        return {"success": success_count, "failed": failed_count}

    def stop(self):
        """停止执行"""
        if self.is_running:
            self._log("正在停止执行...", "warning")
            self._stop_event.set()
            self.is_running = False

    # 实现 loguru logger 的接口，使 WeBanClient 可以使用
    def info(self, msg: str, *args, **kwargs):
        """info 日志"""
        self._log(msg, "info")

    def success(self, msg: str, *args, **kwargs):
        """success 日志"""
        self._log(msg, "success")

    def warning(self, msg: str, *args, **kwargs):
        """warning 日志"""
        self._log(msg, "warning")

    def error(self, msg: str, *args, **kwargs):
        """error 日志"""
        self._log(msg, "error")

    def debug(self, msg: str, *args, **kwargs):
        """debug 日志"""
        # 不显示 debug 日志
        pass

    def bind(self, **kwargs):
        """bind 方法（用于 loguru 的 extra 参数）"""
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def get_weban_adapter(progress_callback: Optional[Callable[[str, str], None]] = None) -> WeBanAdapter:
    """
    获取 WeBan 适配器实例

    Args:
        progress_callback: 进度回调函数

    Returns:
        WeBanAdapter 实例
    """
    return WeBanAdapter(progress_callback=progress_callback)
