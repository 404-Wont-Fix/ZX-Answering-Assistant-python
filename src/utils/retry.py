"""
重试机制模块

提供灵活的重试装饰器和配置类，支持指数退避和自定义异常处理。
"""

import logging
import time
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any, Union

logger = logging.getLogger(__name__)


class RetryConfig:
    """
    重试配置类

    定义重试行为的配置参数。
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大重试次数（不包括首次尝试）
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_base: 指数退避的底数
            jitter: 是否添加随机抖动（避免雷击效应）
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        计算第N次重试的延迟时间

        Args:
            attempt: 重试次数（从1开始）

        Returns:
            float: 延迟时间（秒）
        """
        # 指数退避计算
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )

        # 添加随机抖动
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


def retry(
    max_attempts: int = 3,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    raise_on_last: bool = True
):
    """
    重试装饰器

    Args:
        max_attempts: 最大重试次数（不包括首次尝试）
        exceptions: 需要重试的异常类型
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数退避的底数
        on_retry: 重试前的回调函数，接收 (异常, 重试次数)
        raise_on_last: 最后一次失败是否抛出异常

    Returns:
        装饰器函数

    Example:
        @retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            # 可能失败的代码
            pass
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=True
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # 计算延迟
                        delay = config.get_delay(attempt + 1)

                        # 调用重试回调
                        if on_retry:
                            try:
                                on_retry(e, attempt + 1)
                            except Exception as callback_error:
                                logger.warning(f"重试回调函数失败: {callback_error}")

                        # 记录日志
                        logger.warning(
                            f"函数 {func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts + 1}): {e}"
                        )
                        logger.info(f"等待 {delay:.2f} 秒后重试...")

                        # 等待后重试
                        time.sleep(delay)
                    else:
                        # 最后一次尝试失败
                        logger.error(
                            f"函数 {func.__name__} 在 {max_attempts + 1} 次尝试后仍然失败"
                        )

            # 所有重试都失败
            if raise_on_last and last_exception:
                raise last_exception

            return None

        return wrapper

    return decorator


def retry_on_exception(
    *exception_types: Type[Exception],
    max_attempts: int = 3
):
    """
    简化的重试装饰器（基于异常类型）

    Args:
        *exception_types: 需要重试的异常类型
        max_attempts: 最大重试次数

    Returns:
        装饰器函数

    Example:
        @retry_on_exception(ConnectionError, TimeoutError, max_attempts=3)
        def fetch_data():
            pass
    """
    return retry(
        max_attempts=max_attempts,
        exceptions=exception_types if exception_types else Exception
    )


class RetryContext:
    """
    重试上下文管理器

    用于在代码块中实现重试逻辑。

    Example:
        with RetryContext(max_attempts=3) as retry_ctx:
            # 可能失败的代码
            result = some_function()
            if result is None:
                raise ValueError("操作失败")
    """

    def __init__(
        self,
        max_attempts: int = 3,
        exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        初始化重试上下文

        Args:
            max_attempts: 最大重试次数
            exceptions: 需要捕获的异常类型
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
        """
        self.max_attempts = max_attempts
        self.exceptions = exceptions
        self.config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay
        )
        self._attempt = 0

    def __enter__(self):
        """进入上下文"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文

        处理重试逻辑
        """
        if exc_type is None:
            # 没有异常，直接返回
            return True

        # 检查是否是需要重试的异常类型
        if not isinstance(exc_val, self.exceptions):
            # 不是需要重试的异常，重新抛出
            return False

        # 增加尝试次数
        self._attempt += 1

        if self._attempt <= self.max_attempts:
            # 计算延迟
            delay = self.config.get_delay(self._attempt)

            # 记录日志
            logger.warning(
                f"操作失败 (尝试 {self._attempt}/{self.max_attempts}): {exc_val}"
            )
            logger.info(f"等待 {delay:.2f} 秒后重试...")

            # 等待
            time.sleep(delay)

            # 抑制异常，继续重试
            return True
        else:
            # 达到最大重试次数，不再抑制异常
            logger.error(f"操作在 {self.max_attempts} 次重试后仍然失败")
            return False
