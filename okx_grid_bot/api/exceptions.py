"""
OKX API 异常定义模块

定义所有可能的 API 异常，让调用者可以精确处理不同类型的错误。
"""


class OKXAPIError(Exception):
    """
    OKX API 基础异常类

    所有 OKX 相关异常的父类，可以用于捕获所有 OKX 错误。

    Example:
        try:
            api.place_order(...)
        except OKXAPIError as e:
            print(f"OKX API 错误: {e}")
    """
    def __init__(self, message: str, code: str = None, raw_response: dict = None):
        self.message = message
        self.code = code
        self.raw_response = raw_response
        super().__init__(self.message)

    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class OKXAuthError(OKXAPIError):
    """
    认证错误

    API Key 无效、过期或权限不足时抛出。
    """
    pass


class OKXRateLimitError(OKXAPIError):
    """
    频率限制错误

    请求过于频繁，触发 API 限流时抛出。
    建议：捕获此异常后等待一段时间再重试。
    """
    def __init__(self, message: str = "请求过于频繁", retry_after: int = 60):
        super().__init__(message, code="429")
        self.retry_after = retry_after


class OKXNetworkError(OKXAPIError):
    """
    网络错误

    网络连接失败、超时等网络层面的错误。
    """
    pass


class OKXOrderError(OKXAPIError):
    """
    订单错误

    下单失败、撤单失败等订单相关错误。
    """
    pass


class OKXInsufficientBalanceError(OKXOrderError):
    """
    余额不足错误
    """
    pass


class OKXInvalidParameterError(OKXAPIError):
    """
    参数错误

    请求参数无效时抛出。
    """
    pass


# OKX 错误码映射
ERROR_CODE_MAP = {
    "50000": OKXAPIError,           # 通用错误
    "50001": OKXInvalidParameterError,  # 参数错误
    "50004": OKXAuthError,          # API Key 无效
    "50005": OKXAuthError,          # 签名错误
    "50011": OKXAuthError,          # IP 不在白名单
    "50013": OKXAuthError,          # 权限不足
    "50026": OKXRateLimitError,     # 频率限制
    "51008": OKXInsufficientBalanceError,  # 余额不足
}


def raise_for_error_code(code: str, message: str, raw_response: dict = None):
    """
    根据错误码抛出对应的异常

    Args:
        code: OKX 错误码
        message: 错误信息
        raw_response: 原始响应数据

    Raises:
        OKXAPIError 或其子类
    """
    exception_class = ERROR_CODE_MAP.get(code, OKXAPIError)
    raise exception_class(message, code=code, raw_response=raw_response)
