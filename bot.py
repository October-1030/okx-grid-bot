"""
网格交易机器人主程序
"""
import time
import signal
import sys

import config
from logger import logger, log_error, log_status
from okx_api import api
from grid_strategy import GridStrategy


class GridBot:
    """
    网格交易机器人
    """

    def __init__(self):
        self.running = False
        self.strategy = None

        # 注册信号处理（用于优雅退出）
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """
        处理退出信号
        """
        logger.info("收到退出信号，正在停止...")
        self.running = False

    def _check_config(self) -> bool:
        """
        检查配置是否完整
        """
        if not config.API_KEY or not config.SECRET_KEY or not config.PASSPHRASE:
            log_error("请先配置 OKX API Key!")
            log_error("请复制 .env.example 为 .env 并填入你的 API 信息")
            return False

        if config.GRID_UPPER_PRICE <= config.GRID_LOWER_PRICE:
            log_error("网格上限必须大于下限!")
            return False

        if config.AMOUNT_PER_GRID <= 0:
            log_error("每格金额必须大于 0!")
            return False

        return True

    def _check_balance(self) -> bool:
        """
        检查账户余额
        """
        balance = api.get_balance('USDT')
        if balance is None:
            log_error("无法获取账户余额，请检查 API 配置")
            return False

        required = config.AMOUNT_PER_GRID * config.GRID_COUNT
        logger.info(f"USDT 余额: {balance:.2f}")
        logger.info(f"网格所需资金: {required:.2f} USDT")

        if balance < config.AMOUNT_PER_GRID:
            log_error(f"余额不足! 至少需要 {config.AMOUNT_PER_GRID} USDT")
            return False

        if balance < required:
            logger.warning(f"余额不足以填满所有网格，但可以开始运行")

        return True

    def _check_price(self) -> bool:
        """
        检查当前价格是否在网格范围内
        """
        price = api.get_current_price()
        if price is None:
            log_error("无法获取当前价格")
            return False

        logger.info(f"当前 {config.SYMBOL} 价格: {price}")

        if price < config.GRID_LOWER_PRICE or price > config.GRID_UPPER_PRICE:
            logger.warning(f"当前价格不在网格范围内 ({config.GRID_LOWER_PRICE} - {config.GRID_UPPER_PRICE})")
            logger.warning("机器人会等待价格进入范围后开始交易")

        return True

    def start(self):
        """
        启动机器人
        """
        logger.info("=" * 50)
        logger.info("OKX 网格交易机器人启动")
        logger.info("=" * 50)

        # 检查配置
        if not self._check_config():
            return

        # 检查余额
        if not self._check_balance():
            return

        # 检查价格
        if not self._check_price():
            return

        # 初始化策略
        self.strategy = GridStrategy()

        # 开始运行
        self.running = True
        logger.info(f"开始运行，每 {config.CHECK_INTERVAL} 秒检查一次价格")
        logger.info("按 Ctrl+C 可以安全停止")
        logger.info("-" * 50)

        self._run_loop()

    def _run_loop(self):
        """
        主循环
        """
        error_count = 0
        max_errors = 5

        while self.running:
            try:
                # 获取当前价格
                current_price = api.get_current_price()

                if current_price is None:
                    error_count += 1
                    log_error(f"获取价格失败 ({error_count}/{max_errors})")
                    if error_count >= max_errors:
                        log_error("连续获取价格失败，暂停 60 秒")
                        time.sleep(60)
                        error_count = 0
                    else:
                        time.sleep(config.CHECK_INTERVAL)
                    continue

                # 重置错误计数
                error_count = 0

                # 执行策略
                result = self.strategy.check_and_trade(current_price)

                # 输出状态
                status = self.strategy.get_status()
                log_status(
                    current_price,
                    status['position_count'],
                    status['total_profit']
                )

                if result['action']:
                    logger.info(f"交易动作: {result['message']}")

                # 等待下次检查
                time.sleep(config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("用户中断")
                break
            except Exception as e:
                log_error(f"运行异常: {e}")
                error_count += 1
                if error_count >= max_errors:
                    log_error("错误过多，暂停 60 秒")
                    time.sleep(60)
                    error_count = 0
                else:
                    time.sleep(config.CHECK_INTERVAL)

        self._shutdown()

    def _shutdown(self):
        """
        关闭机器人
        """
        logger.info("-" * 50)
        logger.info("机器人已停止")
        if self.strategy:
            status = self.strategy.get_status()
            logger.info(f"最终状态:")
            logger.info(f"  持仓格数: {status['position_count']}")
            logger.info(f"  累计盈亏: {status['total_profit']:.4f} USDT")
            logger.info(f"  交易次数: {status['trade_count']}")
        logger.info("=" * 50)


def main():
    """
    主函数
    """
    print("""
    ╔═══════════════════════════════════════════════╗
    ║       OKX 网格交易机器人 v1.0                 ║
    ║                                               ║
    ║  注意: 量化交易有风险，请用可承受损失的资金   ║
    ╚═══════════════════════════════════════════════╝
    """)

    bot = GridBot()
    bot.start()


if __name__ == '__main__':
    main()
