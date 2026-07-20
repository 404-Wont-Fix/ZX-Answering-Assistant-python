"""
WeBan Module Adapter

This module provides an isolated adapter for the WeBan submodule,
ensuring code separation and independent functionality.
"""

import sys
import os
import importlib
from pathlib import Path
import json
import threading
from typing import Optional, Callable, List, Dict, Any

# 日志级别对应的 emoji 前缀
LEVEL_EMOJI = {
    "info": "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
}

def _find_weban_path() -> Optional[Path]:
    """
    查找 WeBan 模块路径

    按优先级查找以下位置：
    1. 插件 modules 目录：plugins/weban_plugin/modules/WeBan/
    2. 插件目录：plugins/weban_plugin/WeBan/
    3. 项目根目录：WeBan/
    4. Submodules 目录：submodules/WeBan/

    Returns:
        找到的 WeBan 路径，如果未找到返回 None
    """
    # 当前文件所在目录（插件根目录）
    current_dir = Path(__file__).parent

    # 可能的 WeBan 位置
    possible_paths = [
        # 1. 插件 modules 目录（推荐位置）
        current_dir / "modules" / "WeBan",
        # 2. 插件目录（兼容旧部署）
        current_dir / "WeBan",
        # 3. 项目根目录（开发环境）
        current_dir.parent.parent / "WeBan",
        # 4. 作为 git submodule
        current_dir.parent.parent / "submodules" / "WeBan",
        # 5. 上一级目录
        current_dir.parent.parent.parent / "WeBan",
    ]

    for path in possible_paths:
        if path.exists() and (path / "api.py").exists():
            return path

    return None


# 只在模块导入时定位路径；外部 WeBan 代码在真正使用时再懒加载。
weban_path = _find_weban_path()
WEBAN_AVAILABLE = False
WEBAN_IMPORT_ERROR: Optional[Exception] = None
WeBanClient = None
WeBanAPI = None


def _load_weban_classes() -> bool:
    """懒加载外部 WeBan 类，避免插件入口导入被可选依赖拖垮。"""
    global weban_path, WEBAN_AVAILABLE, WEBAN_IMPORT_ERROR, WeBanClient, WeBanAPI

    if WEBAN_AVAILABLE and WeBanClient is not None and WeBanAPI is not None:
        return True

    weban_path = _find_weban_path()
    if not weban_path:
        WEBAN_AVAILABLE = False
        WEBAN_IMPORT_ERROR = None
        WeBanClient = None
        WeBanAPI = None
        return False

    if str(weban_path) not in sys.path:
        sys.path.insert(0, str(weban_path))

    try:
        client_module = importlib.import_module("client")
        api_module = importlib.import_module("api")
        WeBanClient = client_module.WeBanClient
        WeBanAPI = api_module.WeBanAPI
        WEBAN_AVAILABLE = True
        WEBAN_IMPORT_ERROR = None
        return True
    except Exception as e:
        WEBAN_AVAILABLE = False
        WeBanClient = None
        WeBanAPI = None
        WEBAN_IMPORT_ERROR = e
        return False


class WeBanAdapter:
    """
    WeBan 模块适配器

    提供与主项目隔离的 WeBan 功能接口
    """

    def __init__(self, progress_callback: Optional[Callable[[str, str], None]] = None, input_callback: Optional[Callable[[str], str]] = None):
        """
        初始化适配器

        Args:
            progress_callback: 进度回调函数，参数 (message: str, level: str)
                level 可选值: "info", "success", "warning", "error"
            input_callback: 用户输入回调函数，参数 (prompt: str)，返回用户输入的字符串
                用于 GUI 模式下的验证码输入、手动答题等场景
        """
        self.progress_callback = progress_callback or self._default_callback
        self.input_callback = input_callback or self._default_input
        self.is_running = False
        self._stop_event = threading.Event()
        self._config: List[Dict[str, Any]] = []

        # 检查 WeBan 是否可用
        if not self._ensure_weban_available():
            self._log("WeBan 模块不可用，插件功能受限", "warning")
            return

        # 应用 Monkey Patch 添加停止功能
        self._apply_stop_patch()
        # 应用 Monkey Patch 添加 GUI 输入支持
        self._apply_input_patch()

        # 保存 input_callback 的引用，供 monkey patch 使用
        try:
            WeBanClient._weban_adapter_input = self.input_callback
        except AttributeError as e:
            self._log(f"无法设置 WeBanClient 回调: {e}", "warning")

    def _ensure_weban_available(self) -> bool:
        """确保外部 WeBan 模块已经成功加载。"""
        if _load_weban_classes():
            return True

        if weban_path:
            self._log(f"WeBan 模块导入失败: {WEBAN_IMPORT_ERROR}", "warning")
            self._log(f"WeBan路径: {weban_path}", "warning")
            self._log("请确保WeBan依赖包已安装: pip install ddddocr loguru pycryptodome requests", "warning")
        else:
            self._log("未找到 WeBan 模块，插件将不可用", "warning")
            self._log("如需使用此插件，请确保 WeBan 项目存在", "warning")
        return False

    def _default_callback(self, message: str, level: str = "info"):
        """默认进度回调"""
        print(f"{LEVEL_EMOJI.get(level, 'ℹ️')} {message}")

    def _default_input(self, prompt: str) -> str:
        """默认输入回调（CLI 模式）"""
        return input(prompt)

    def _log(self, message: str, level: str = "info"):
        """发送日志到回调"""
        try:
            self.progress_callback(message, level)
        except Exception as e:
            print(f"回调函数执行失败: {e}")
            self._default_callback(message, level)

    def check_available(self) -> bool:
        """检查 WeBan 模块是否可用"""
        return _load_weban_classes()

    def get_dependencies(self) -> List[str]:
        """获取 WeBan 模块依赖"""
        return [
            "ddddocr==1.6.1",
            "loguru==0.7.3",
            "pycryptodome==3.23.0",
            "requests==2.32.5",
        ]

    def _apply_stop_patch(self):
        """
        应用 Monkey Patch 添加停止功能

        通过动态替换 WeBanClient 的方法，在关键循环点注入停止检查
        """
        if not _load_weban_classes():
            return

        # 使用类级别标志确保 Monkey Patch 只应用一次
        if not hasattr(WeBanClient, '_weban_patch_applied'):
            # 保存原始方法（只保存一次）
            WeBanClient._original_run_study = WeBanClient.run_study
            WeBanClient._original_run_exam = WeBanClient.run_exam

            # 创建带停止检查的薄包装（*args/**kwargs 转发给原始实现，版本无关）
            def run_study_with_stop(self, *args, **kwargs):
                """带停止检查的 run_study（入口检查 + 委托原始实现）"""
                if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                    if self._adapter._stop_event.is_set():
                        self._adapter._log("用户中断：学习阶段", "warning")
                        return
                return WeBanClient._original_run_study(self, *args, **kwargs)

            def run_exam_with_stop(self, *args, **kwargs):
                """带停止检查的 run_exam（入口检查 + 委托原始实现）"""
                if hasattr(self, '_adapter') and hasattr(self._adapter, '_stop_event'):
                    if self._adapter._stop_event.is_set():
                        self._adapter._log("用户中断：考试阶段", "warning")
                        return
                return WeBanClient._original_run_exam(self, *args, **kwargs)

            # 替换方法
            WeBanClient.run_study = run_study_with_stop
            WeBanClient.run_exam = run_exam_with_stop

            # 标记已应用
            WeBanClient._weban_patch_applied = True

    def _apply_input_patch(self):
        """
        应用 Monkey Patch 添加 GUI 输入支持

        将 WeBan 模块中的 input() 调用和 _prompt() 方法替换为回调函数
        """
        if not _load_weban_classes():
            return

        # 使用类级别标志确保 Monkey Patch 只应用一次
        if not hasattr(WeBanClient, '_weban_input_patch_applied'):
            # 保存原始 _prompt 方法
            WeBanClient._original_prompt = WeBanClient._prompt

            # 创建支持 GUI 的 _prompt 方法
            def _prompt_with_gui(self, message: str) -> str:
                """支持 GUI 输入的 _prompt 方法"""
                if hasattr(self, '_adapter') and hasattr(self._adapter, 'input_callback'):
                    return self._adapter.input_callback(message).strip()
                else:
                    return self._original_prompt(message)

            # 替换 _prompt 方法
            WeBanClient._prompt = _prompt_with_gui
            def login_with_gui_input(self) -> Dict | None:
                """支持 GUI 输入的登录方法"""
                if self.api.user.get("userId"):
                    return self.api.user
                retry_limit = 10
                # 前 10 次 OCR 自动识别，后 3 次手动输入
                for i in range(retry_limit + 3):
                    if i > 0:
                        self.log.warning(f"登录失败，正在重试 {i}/{retry_limit + 2} 次")
                    verify_time = self.api.get_timestamp(13, 0)
                    verify_image = self.api.rand_letter_image(verify_time)
                    if i < retry_limit:
                        # 使用新版 WeBan 的 LoginCaptchaSolver
                        try:
                            from captcha import LoginCaptchaSolver
                            verify_code = LoginCaptchaSolver.recognize(verify_image, self.log)
                            if not verify_code:
                                continue
                            self.log.info(f"自动验证码识别结果: {verify_code}")
                        except Exception as e:
                            self.log.error(f"验证码识别异常: {e}")
                            continue
                    else:
                        import time
                        import threading
                        account_id = self.api.account or self.api.user.get("userId") or "unknown"
                        # 添加时间戳和线程ID，避免多账号同时运行时的文件覆盖
                        timestamp = int(time.time() * 1000)
                        thread_id = threading.get_ident()
                        captcha_filename = f"verify_code_{account_id}_{timestamp}_{thread_id}.png"
                        captcha_path = os.path.abspath(captcha_filename)
                        with self._stdin_lock:
                            open(captcha_path, "wb").write(verify_image)
                            webbrowser.open(f"file://{captcha_path}")

                            # 使用回调函数获取输入（支持 GUI）
                            if hasattr(self, '_adapter') and hasattr(self._adapter, 'input_callback'):
                                verify_code = self._adapter.input_callback(
                                    f"请查看 {captcha_filename} 输入验证码："
                                )
                            else:
                                verify_code = input(f"[{account_id}] 请查看 {captcha_filename} 输入验证码：")

                        # 尝试删除临时验证码图片
                        try:
                            os.remove(captcha_path)
                        except Exception:
                            pass

                    res = self.api.login(verify_code, int(verify_time))
                    if res.get("detailCode") == "67":
                        self.log.warning(f"验证码识别失败，正在重试")
                        continue
                    if self.api.user.get("userId"):
                        return self.api.user
                    self.log.error(f"登录出错，请检查 config.json 内账号密码，或删除文件后重试: {res}")
                    break
                return None

            # 替换方法
            WeBanClient.login = login_with_gui_input

            # 标记已应用
            WeBanClient._weban_input_patch_applied = True

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
        if not self._ensure_weban_available():
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

    def _should_stop(self, account_index: int) -> bool:
        """检查用户是否请求停止，若停止则记录日志"""
        if self._stop_event.is_set():
            self._log(f"[账号 {account_index+1}]: 用户中断", "warning")
            return True
        return False

    def run_account(self, config: Dict[str, Any], account_index: int) -> bool:
        """
        运行单个账号的任务

        Args:
            config: 账号配置
            account_index: 账号索引

        Returns:
            是否执行成功
        """
        if self._should_stop(account_index):
            return False

        if not self._ensure_weban_available():
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

            # 绑定 adapter 到 client，用于停止检查
            client._adapter = self

            # 登录前检查停止标志
            if self._should_stop(account_index):
                return False

            if not client.login():
                self._log(f"[账号 {account_index+1}] 登录失败", "error")
                return False

            self._log(f"[账号 {account_index+1}] 登录成功，开始同步答案", "info")

            # 同步答案前检查停止标志
            if self._should_stop(account_index):
                return False
            client.sync_answers()

            if study:
                # 学习前检查停止标志
                if self._should_stop(account_index):
                    return False
                self._log(f"[账号 {account_index+1}] 开始学习 (每个任务时长: {study_time}秒)", "info")
                client.run_study(study_time, restudy_time)

            if exam:
                # 考试前检查停止标志
                if self._should_stop(account_index):
                    return False
                self._log(f"[账号 {account_index+1}] 开始考试 (总时长: {exam_use_time}秒)", "info")
                client.run_exam(exam_use_time)

            # 最终同步前检查停止标志
            if self._should_stop(account_index):
                return False
            self._log(f"[账号 {account_index+1}] 最终同步答案", "info")
            client.sync_answers()

            self._log(f"[账号 {account_index+1}] 执行完成", "success")
            return True

        except PermissionError as e:
            self._log(f"[账号 {account_index+1}] 权限错误: {e}", "error")
            self._log(f"💡 提示：请检查文件权限，或以管理员身份运行", "info")
            return False
        except RuntimeError as e:
            self._log(f"[账号 {account_index+1}] 运行时错误: {e}", "error")
            # 判断是否是用户主动停止
            if "用户中断" in str(e) or self._stop_event.is_set():
                self._log(f"[账号 {account_index+1}] 用户主动停止任务", "warning")
            return False
        except ValueError as e:
            self._log(f"[账号 {account_index+1}] 参数错误: {e}", "error")
            self._log(f"💡 提示：请检查配置参数是否正确", "info")
            return False
        except ConnectionError as e:
            self._log(f"[账号 {account_index+1}] 网络连接错误: {e}", "error")
            self._log(f"💡 提示：请检查网络连接", "info")
            return False
        except TimeoutError as e:
            self._log(f"[账号 {account_index+1}] 请求超时: {e}", "error")
            self._log(f"💡 提示：网络响应过慢，请稍后重试", "info")
            return False
        except KeyboardInterrupt:
            self._log(f"[账号 {account_index+1}] 用户中断执行", "warning")
            raise
        except Exception as e:
            self._log(f"[账号 {account_index+1}] 未知错误: {type(e).__name__}: {e}", "error")
            import traceback
            self._log(f"错误详情: {traceback.format_exc()}", "error")
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
        """优雅停止执行"""
        if self.is_running:
            self._log("正在停止执行...", "warning")
            self._stop_event.set()
            self.is_running = False

    def force_stop(self):
        """强行停止执行"""
        self._log("⚠️ 正在强行停止...", "warning")

        # 设置停止标志
        self._stop_event.set()
        self.is_running = False

        self._log("✅ 已强行停止任务", "success")

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


def get_weban_adapter(
    progress_callback: Optional[Callable[[str, str], None]] = None,
    input_callback: Optional[Callable[[str], str]] = None
) -> WeBanAdapter:
    """
    获取 WeBan 适配器实例

    Args:
        progress_callback: 进度回调函数
        input_callback: 用户输入回调函数

    Returns:
        WeBanAdapter 实例
    """
    return WeBanAdapter(
        progress_callback=progress_callback,
        input_callback=input_callback
    )
