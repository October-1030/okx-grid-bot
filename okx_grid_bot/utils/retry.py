"""
重试机制模块

提供自动重试功能，用于处理网络请求等可能失败的操作。

使用方法:
    from okx_grid_bot.utils.retry import retry

    @retry(max_attempts=3, delay=1.0)
    def call_api():
        ...
"""
import time
import functools
from typing import Tuple, Type, Callable, Any, Optional

from okx_grid_bot.utils.logger import logger
from okx_grid_bot.api.exceptions import (
    OKXNetworkError,
    OKXRateLimitError,
    OKXAPIError,
)


# 默认可重试的异常类型
DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    OKXNetworkError,
    OKXRateLimitError,
)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数（包括首次）
        delay: 首次重试延迟（秒）
        backoff: 延迟倍增系数（指数退避）
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数，参数为 (exception, attempt_number)

    Returns:
        装饰器函数

    Example:
        @retry(max_attempts=3, delay=1.0)
        def fetch_price():
            return api.get_current_price()

        @retry(max_attempts=5, delay=2.0, backoff=2.0)
        def place_order():
            return api.place_order(...)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # 对于限流错误，使用更长的等待时间
                        if isinstance(e, OKXRateLimitError):
                            wait_time = max(current_delay, e.retry_after)
                        else:
                            wait_time = current_delay

                        logger.warning(
                            f"[重试] {func.__name__} 第 {attempt}/{max_attempts} 次失败: {e}，"
                            f"{wait_time:.1f}秒后重试..."
                        )

                        # 执行重试回调
                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(wait_time)
                        current_delay *= backoff  # 指数退避
                    else:
                        logger.error(
                            f"[重试] {func.__name__} 已达到最大重试次数 {max_attempts}，放弃"
                        )

            # 所有重试都失败，抛出最后一个异常
            raise last_exception

        return wrapper
    return decorator


def retry_on_network_error(func: Callable) -> Callable:
    """
    简化版重试装饰器，仅重试网络错误

    Example:
        @retry_on_network_error
        def get_price():
            return api.get_current_price()
    """
    return retry(max_attempts=3, delay=1.0, exceptions=(OKXNetworkError,))(func)


class RetryContext:
    """
    重试上下文管理器，用于需要更复杂控制的场景

    Example:
        with RetryContext(max_attempts=3) as ctx:
            while ctx.should_retry():
                try:
                    result = api.place_order(...)
                    break
                except OKXNetworkError as e:
                    ctx.record_failure(e)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.current_delay = delay

    def __enter__(self) -> "RetryContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def should_retry(self) -> bool:
        """检查是否应该继续重试"""
        return self.attempt < self.max_attempts

    def record_failure(self, exception: Exception) -> None:
        """记录失败并等待"""
        self.attempt += 1
        self.last_exception = exception

        if self.attempt < self.max_attempts:
            if isinstance(exception, OKXRateLimitError):
                wait_time = max(self.current_delay, exception.retry_after)
            else:
                wait_time = self.current_delay

            logger.warning(
                f"[重试] 第 {self.attempt}/{self.max_attempts} 次失败: {exception}，"
                f"{wait_time:.1f}秒后重试..."
            )
            time.sleep(wait_time)
            self.current_delay *= self.backoff
        else:
            logger.error(f"[重试] 已达到最大重试次数 {self.max_attempts}")
            raise exception
