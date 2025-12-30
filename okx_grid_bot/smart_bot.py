"""
智能量化交易机器人主程序
整合市场分析、风控、仓位管理的完整系统
"""
import time
import signal
import sys
import io
from datetime import datetime, timedelta
from typing import Dict

# 修复 Windows 终端中文编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from okx_grid_bot.utils import config
from okx_grid_bot.utils.logger import logger, log_error, log_status, log_warning
from okx_grid_bot.api.okx_client import api
from okx_grid_bot.strategy.smart_grid import SmartGridStrategy
from okx_grid_bot.analysis.macro_analysis import macro_analyzer
from okx_grid_bot.risk.risk_control import risk_controller
from okx_grid_bot.strategy.position_manager import position_manager


class SmartGridBot:
    """
    智能网格交易机器人
    """

    def __init__(self):
        self.running = False
        self.strategy = None
        self.last_analysis_time = None
        self.analysis_interval = 3600  # 每小时重新分析

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info("收到退出信号，正在安全停止...")
        self.running = False

    def _check_config(self) -> bool:
        """检查配置"""
        if not config.API_KEY or not config.SECRET_KEY or not config.PASSPHRASE:
            log_error("请先配置 OKX API Key!")
            log_error("请复制 .env.example 为 .env 并填入你的 API 信息")
            return False
        return True

    def _check_balance(self) -> float:
        """检查余额并返回"""
        balance = api.get_balance('USDT')
        if balance is None:
            log_error("无法获取账户余额，请检查 API 配置")
            return 0
        logger.info(f"USDT 余额: {balance:.2f}")
        return balance

    def _initial_analysis(self) -> bool:
        """
        启动前的初始分析
        """
        print("\n" + "=" * 60)
        print("      首次启动 - 执行全面市场分析")
        print("=" * 60)

        # 执行分析
        analysis_result = self.strategy.analyze_and_adjust()

        if not analysis_result.get('should_trade', False):
            print("\n" + "!" * 60)
            print("  警告: 当前市场环境不适合交易!")
            print("!" * 60)
            for warning in analysis_result.get('reason', []):
                print(f"  - {warning}")
            print("\n机器人将进入监控模式，等待市场好转...")
            return False

        # 显示建议参数
        suggested = analysis_result.get('suggested_params', {})
        if suggested:
            print("\n" + "-" * 60)
            print("系统建议的网格参数:")
            print(f"  价格区间: {suggested.get('lower_price')} - {suggested.get('upper_price')}")
            print(f"  网格数量: {suggested.get('grid_count')}")
            print(f"  每格金额: {suggested.get('amount_per_grid')} USDT")
            print(f"  总投入: {suggested.get('total_investment')} USDT")
            print("-" * 60)

            # 询问是否应用建议参数
            print("\n是否应用建议参数? (直接回车使用当前配置)")
            try:
                choice = input("输入 y 应用建议参数, 其他跳过: ").strip().lower()
                if choice == 'y':
                    self.strategy.apply_suggested_params(suggested)
                    print("已应用建议参数!")
            except:
                pass

        return True

    def _should_reanalyze(self) -> bool:
        """检查是否需要重新分析"""
        if self.last_analysis_time is None:
            return True

        elapsed = (datetime.now() - self.last_analysis_time).total_seconds()
        return elapsed >= self.analysis_interval

    def start(self):
        """启动机器人"""
        self._print_banner()

        # 检查配置
        if not self._check_config():
            return

        # 检查余额
        balance = self._check_balance()
        if balance <= 0:
            return

        # 获取当前价格
        current_price = api.get_current_price()
        if current_price is None:
            log_error("无法获取当前价格")
            return
        logger.info(f"当前 {config.SYMBOL} 价格: {current_price}")

        # 初始化策略
        self.strategy = SmartGridStrategy()

        # 初始化风控
        total_value = balance
        risk_controller.initialize(total_value)

        # 初始化仓位管理
        position_manager.set_total_capital(balance)

        # 执行初始分析
        can_trade = self._initial_analysis()
        self.last_analysis_time = datetime.now()

        # 开始运行
        self.running = True
        logger.info("\n" + "=" * 50)
        logger.info("机器人启动成功!")
        logger.info(f"检查间隔: {config.CHECK_INTERVAL} 秒")
        logger.info(f"分析间隔: {self.analysis_interval} 秒")
        logger.info("按 Ctrl+C 安全停止")
        logger.info("=" * 50 + "\n")

        self._run_loop()

    def _run_loop(self):
        """主循环"""
        error_count = 0
        max_errors = 5
        check_count = 0

        while self.running:
            try:
                check_count += 1

                # 定期重新分析市场
                if self._should_reanalyze():
                    logger.info("\n执行定期市场分析...")
                    analysis_result = self.strategy.analyze_and_adjust()
                    self.last_analysis_time = datetime.now()

                    if not analysis_result.get('should_trade', False):
                        log_warning("市场环境变化，暂停交易")
                        # 不退出，继续监控

                # 获取当前价格
                current_price = api.get_current_price()

                if current_price is None:
                    error_count += 1
                    log_error(f"获取价格失败 ({error_count}/{max_errors})")
                    if error_count >= max_errors:
                        log_error("连续失败，暂停 60 秒")
                        time.sleep(60)
                        error_count = 0
                    else:
                        time.sleep(config.CHECK_INTERVAL)
                    continue

                error_count = 0

                # 执行交易策略
                result = self.strategy.check_and_trade(current_price)

                # 输出状态
                status = self.strategy.get_status()

                # 每10次检查输出一次状态
                if check_count % 10 == 0:
                    self._print_status(current_price, status)

                # 如果有交易动作，立即输出
                if result.get('action'):
                    logger.info(f">>> 交易: {result.get('message')}")

                # 等待
                time.sleep(config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("用户中断")
                break
            except Exception as e:
                log_error(f"运行异常: {e}")
                import traceback
                traceback.print_exc()
                error_count += 1
                if error_count >= max_errors:
                    log_error("错误过多，暂停 60 秒")
                    time.sleep(60)
                    error_count = 0
                else:
                    time.sleep(config.CHECK_INTERVAL)

        self._shutdown()

    def _print_status(self, current_price: float, status: Dict):
        """打印状态"""
        position_value = self.strategy.get_position_value(current_price)
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
              f"价格: {current_price:.2f} | "
              f"持仓: {status['position_count']}/{status['grid_count']} | "
              f"持仓价值: {position_value:.2f} | "
              f"盈亏: {status['total_profit']:.2f} | "
              f"环境: {status.get('environment', 'N/A')}", end="")

    def _print_banner(self):
        """打印启动横幅"""
        print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║           智 能 网 格 量 化 交 易 系 统  v2.0                ║
    ║                                                               ║
    ║  功能特点:                                                    ║
    ║    ✓ 多维度市场分析 (趋势/波动/情绪)                         ║
    ║    ✓ 动态网格参数调整                                        ║
    ║    ✓ 智能风控保护                                            ║
    ║    ✓ 仓位动态管理                                            ║
    ║                                                               ║
    ║  注意: 量化交易有风险，请用可承受损失的资金进行测试          ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
        """)

    def _shutdown(self):
        """关闭"""
        print("\n")
        logger.info("=" * 50)
        logger.info("机器人安全停止")
        logger.info("=" * 50)

        if self.strategy:
            status = self.strategy.get_status()
            logger.info("最终状态:")
            logger.info(f"  持仓格数: {status['position_count']}")
            logger.info(f"  累计盈亏: {status['total_profit']:.4f} USDT")
            logger.info(f"  交易次数: {status['trade_count']}")

        risk_status = risk_controller.get_status()
        logger.info(f"  日内盈亏: {risk_status['daily_pnl']:.2f} USDT")

        logger.info("=" * 50)
        logger.info("订单记录已保存，下次启动将自动恢复")


def run_analysis_only():
    """只运行分析，不交易"""
    print("\n" + "=" * 60)
    print("         市 场 分 析 模 式")
    print("=" * 60 + "\n")

    result = macro_analyzer.analyze_market()
    macro_analyzer.print_analysis_report(result)


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--analyze':
            run_analysis_only()
            return
        elif sys.argv[1] == '--help':
            print("""
使用方法:
    python smart_bot.py           启动智能交易机器人
    python smart_bot.py --analyze 仅运行市场分析
    python smart_bot.py --help    显示帮助
            """)
            return

    bot = SmartGridBot()
    bot.start()


if __name__ == '__main__':
    main()
