"""
网格交易机器人主程序

使用事件驱动架构，主要事件：
- BOT_STARTED: 机器人启动
- PRICE_UPDATE: 价格更新
- SIGNAL_GENERATED: 策略生成信号
- ORDER_FILLED: 订单成交
- BOT_STOPPED: 机器人停止
"""
import time
import signal
import sys

from okx_grid_bot.utils import config
from okx_grid_bot.utils.logger import logger, log_error, log_status
from okx_grid_bot.utils.events import event_bus, EventType, Event
from okx_grid_bot.utils.state_machine import BotStateMachine, BotState
from okx_grid_bot.api.okx_client import api
from okx_grid_bot.strategy.grid import GridStrategy
from okx_grid_bot.strategy.base import MarketData, SignalAction


class GridBot:
    """
    网格交易机器人

    使用策略模式和事件驱动架构。
    """

    def __init__(self):
        self.strategy = None
        self.state_machine = BotStateMachine()  # 状态机管理

        # 注册信号处理（用于优雅退出）
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # 注册事件处理
        self._setup_event_handlers()

    @property
    def running(self) -> bool:
        """是否正在运行（从状态机获取）"""
        return self.state_machine.is_active

    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 订阅错误事件进行日志记录
        @event_bus.on(EventType.ERROR_OCCURRED)
        def on_error(event: Event):
            log_error(f"事件处理错误: {event.data}")

        # 订阅信号事件
        @event_bus.on(EventType.SIGNAL_GENERATED)
        def on_signal(event: Event):
            signal_data = event.data
            logger.debug(f"信号生成: {signal_data['action']} - {signal_data['reason']}")

    def _signal_handler(self, signum, frame):
        """
        处理退出信号
        """
        logger.info("收到退出信号，正在停止...")
        self.state_machine.stop()
        event_bus.emit(EventType.BOT_STOPPED, {'reason': 'user_interrupt'})

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

        # 使用状态机管理启动流程
        self.state_machine.start()

        logger.info(f"开始运行，每 {config.CHECK_INTERVAL} 秒检查一次价格")
        logger.info("按 Ctrl+C 可以安全停止")
        logger.info("-" * 50)

        # 发布启动事件
        event_bus.emit(EventType.BOT_STARTED, {
            'strategy': self.strategy.name,
            'symbol': config.SYMBOL,
            'state': self.state_machine.state.value,
        })

        self._run_loop()

    def _run_loop(self):
        """
        主循环 - 使用策略模式和事件驱动
        """
        error_count = 0
        max_errors = 5

        while self.running:
            try:
                # 获取当前价格
                ticker = api.get_ticker()

                if ticker is None:
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

                # 构建市场数据
                market_data = MarketData(
                    symbol=config.SYMBOL,
                    current_price=float(ticker['last']),
                    bid_price=float(ticker['bidPx']),
                    ask_price=float(ticker['askPx']),
                    volume_24h=float(ticker.get('vol24h', 0)),
                )

                # 发布价格更新事件
                event_bus.emit(EventType.PRICE_UPDATE, {
                    'price': market_data.current_price,
                    'symbol': market_data.symbol,
                })

                # 策略分析（策略模式）
                signal = self.strategy.analyze(market_data)

                # 发布信号事件
                event_bus.emit(EventType.SIGNAL_GENERATED, {
                    'action': signal.action.value,
                    'price': signal.price,
                    'reason': signal.reason,
                    'confidence': signal.confidence,
                })

                # 只有在可交易状态才执行交易
                if self.state_machine.can_trade:
                    if signal.action == SignalAction.BUY:
                        self._execute_buy(signal)
                    elif signal.action == SignalAction.SELL:
                        self._execute_sell(signal)
                    elif signal.action == SignalAction.STOP_LOSS:
                        logger.warning(f"止损触发: {signal.reason}")
                        event_bus.emit(EventType.STOP_LOSS_TRIGGERED, {
                            'price': signal.price,
                            'reason': signal.reason,
                        })

                # 输出状态
                status = self.strategy.get_status()
                log_status(
                    market_data.current_price,
                    status['position_count'],
                    status['total_profit']
                )

                # 等待下次检查
                time.sleep(config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("用户中断")
                break
            except Exception as e:
                log_error(f"运行异常: {e}")
                event_bus.emit(EventType.ERROR_OCCURRED, {
                    'error': str(e),
                    'context': 'run_loop'
                })
                error_count += 1
                if error_count >= max_errors:
                    log_error("错误过多，进入错误状态")
                    self.state_machine.error(f"连续 {max_errors} 次错误: {e}")
                    time.sleep(60)
                    # 尝试恢复
                    self.state_machine.resume()
                    error_count = 0
                else:
                    time.sleep(config.CHECK_INTERVAL)

        self._shutdown()

    def _execute_buy(self, signal):
        """执行买入"""
        grid_index = signal.metadata.get('grid_index')
        if grid_index is not None:
            grid = self.strategy.grids[grid_index]
            success = self.strategy._execute_buy(grid, signal.price)
            if success:
                event_bus.emit(EventType.ORDER_FILLED, {
                    'action': 'buy',
                    'price': signal.price,
                    'grid_index': grid_index,
                })

    def _execute_sell(self, signal):
        """执行卖出"""
        grid_index = signal.metadata.get('grid_index')
        if grid_index is not None:
            grid = self.strategy.grids[grid_index]
            success = self.strategy._execute_sell(grid, signal.price)
            if success:
                event_bus.emit(EventType.ORDER_FILLED, {
                    'action': 'sell',
                    'price': signal.price,
                    'grid_index': grid_index,
                    'profit': signal.price - signal.metadata.get('buy_price', 0),
                })

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
