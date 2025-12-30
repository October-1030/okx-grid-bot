"""
日志模块

提供日志功能，包含敏感信息脱敏。
"""
import logging
import sys
import re
from datetime import datetime
from typing import List, Tuple
from okx_grid_bot.utils import config as config_module
# 注意：直接导入子模块，避免循环依赖


class SensitiveDataFilter(logging.Filter):
    """
    敏感数据过滤器

    自动将 API Key、Secret 等敏感信息脱敏，防止泄露。
    """

    # 需要脱敏的模式: (正则表达式, 替换文本)
    PATTERNS: List[Tuple[re.Pattern, str]] = [
        # API Key (通常是32-64位字母数字)
        (re.compile(r'(["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9-]{16,})', re.I),
         r'\1***MASKED***'),
        # Secret Key
        (re.compile(r'(["\']?(?:secret[_-]?key|secretkey|secret)["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9-]{16,})', re.I),
         r'\1***MASKED***'),
        # Passphrase
        (re.compile(r'(["\']?passphrase["\']?\s*[:=]\s*["\']?)([^\s"\']{4,})', re.I),
         r'\1***MASKED***'),
        # OK-ACCESS-KEY header
        (re.compile(r'(OK-ACCESS-KEY["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9-]{8,})', re.I),
         r'\1***MASKED***'),
        # OK-ACCESS-SIGN header
        (re.compile(r'(OK-ACCESS-SIGN["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9+/=]{20,})', re.I),
         r'\1***MASKED***'),
        # 通用的长字符串密钥模式（可能是token）
        (re.compile(r'(Bearer\s+)([a-zA-Z0-9._-]{40,})', re.I),
         r'\1***MASKED***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤并脱敏日志消息
        """
        if record.msg:
            original_msg = str(record.msg)
            masked_msg = original_msg

            for pattern, replacement in self.PATTERNS:
                masked_msg = pattern.sub(replacement, masked_msg)

            record.msg = masked_msg

        # 处理额外参数
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    masked_arg = arg
                    for pattern, replacement in self.PATTERNS:
                        masked_arg = pattern.sub(replacement, masked_arg)
                    new_args.append(masked_arg)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)

        return True  # 始终返回 True，不过滤掉任何日志


def setup_logger(name: str = "GridBot") -> logging.Logger:
    """
    设置并返回一个日志记录器

    特性:
    - 控制台输出 (INFO 级别)
    - 文件输出 (DEBUG 级别)
    - 自动脱敏敏感信息
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 添加敏感数据过滤器
    sensitive_filter = SensitiveDataFilter()
    logger.addFilter(sensitive_filter)

    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(config_module.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 创建全局 logger 实例
logger = setup_logger()

def log_trade(action: str, price: float, amount: float, grid_index: int):
    """
    记录交易日志
    """
    logger.info(f"[交易] {action} | 价格: {price} | 数量: {amount} | 网格: {grid_index}")

def log_status(current_price: float, position_count: int, profit: float):
    """
    记录状态日志
    """
    logger.info(f"[状态] 当前价格: {current_price} | 持仓格数: {position_count} | 累计盈亏: {profit:.2f} USDT")

def log_error(message: str):
    """
    记录错误日志
    """
    logger.error(f"[错误] {message}")

def log_warning(message: str):
    """
    记录警告日志
    """
    logger.warning(f"[警告] {message}")
