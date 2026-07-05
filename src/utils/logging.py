"""
日志工具函数

提供共享的 CallbackHandler 和日志设置/清理功能。
"""

import logging
from typing import Callable, Optional


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
