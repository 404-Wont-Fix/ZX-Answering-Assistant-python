"""
日志工具函数

提供共享的 CallbackHandler 和日志设置/清理功能，
以及应用级日志初始化（setup_app_logging）。
"""

import logging
import os
import sys
from pathlib import Path
from typing import Callable, Optional


def get_log_dir() -> Path:
    """返回应用日志目录（跨平台）。日志属用户运行数据，不写入源码目录。"""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "ZX-Answering-Assistant" / "Logs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "ZX-Answering-Assistant"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "ZX-Answering-Assistant" / "logs"


APP_LOG_FILE = "student_login.log"


class UTF8StreamHandler(logging.StreamHandler):
    """以 UTF-8 写入 stdout 的 StreamHandler，避免 Windows GBK 控制台编码错误。"""

    def emit(self, record):
        try:
            if not hasattr(self, 'stream') or self.stream is None:
                return
            msg = self.format(record)
            stream = self.stream
            try:
                if hasattr(stream, 'buffer') and not stream.buffer.closed:
                    stream.buffer.write(msg.encode('utf-8') + b'\n')
                elif hasattr(stream, 'closed') and not stream.closed:
                    stream.write(msg + self.terminator)
                else:
                    return
                self.flush()
            except (ValueError, OSError):
                return
        except Exception:
            try:
                self.handleError(record)
            except Exception:
                pass


def setup_app_logging() -> None:
    """应用级日志初始化（应在 main.py 启动期、任何 src 导入之前调用一次）。

    配置 root logger：FileHandler 写入日志目录 + UTF8StreamHandler 写 stdout。
    idempotent（basicConfig 仅在 root 无 handler 时生效）。
    """
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / APP_LOG_FILE, encoding='utf-8'),
            UTF8StreamHandler(sys.stdout),
        ],
    )


class CallbackHandler(logging.Handler):
    """
    自定义日志处理器，将日志消息转发到回调函数。

    格式解析：从 'timestamp - name - level - message' 中提取 message 部分。
    """

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # 格式：2026-01-20 20:06:11,730 - src.module - INFO - message
            parts = msg.split(" - ")
            if len(parts) >= 4:
                message = " - ".join(parts[3:])  # 取消息部分（保留消息中的 " - "）
            else:
                message = msg
            self.callback(message.rstrip())
        except Exception:
            self.handleError(record)


def setup_callback_logging(
    logger: logging.Logger,
    callback: Callable[[str], None],
) -> Optional[CallbackHandler]:
    """
    为 logger 添加 CallbackHandler，将日志转发到回调函数。

    Args:
        logger: 目标 logger
        callback: 日志回调函数，接收单个字符串参数

    Returns:
        创建的 handler，若 callback 为 None 则返回 None
    """
    if not callback:
        return None

    handler = CallbackHandler(callback)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    return handler


def cleanup_callback_logging(
    logger: logging.Logger,
    handler: Optional[CallbackHandler],
) -> None:
    """
    移除并关闭 CallbackHandler。

    Args:
        logger: 目标 logger
        handler: 要清理的 handler
    """
    if handler:
        logger.removeHandler(handler)
        handler.close()
