"""
日志模块
"""
import logging
import sys
from datetime import datetime
import config

def setup_logger(name: str = "GridBot") -> logging.Logger:
    """
    设置并返回一个日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

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
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
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
