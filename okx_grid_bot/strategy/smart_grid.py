"""
智能网格策略模块
整合市场分析、风控、仓位管理的智能网格交易策略
"""
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from okx_grid_bot.utils import config
from okx_grid_bot.utils.logger import logger, log_trade, log_error, log_warning
from okx_grid_bot.api.okx_client import api
from okx_grid_bot.analysis.macro_analysis import macro_analyzer, MarketEnvironment
from okx_grid_bot.risk.risk_control import risk_controller
from okx_grid_bot.strategy.position_manager import position_manager


@dataclass
class GridLevel:
    """网格层级"""
    index: int
    price: float
    is_bought: bool
    buy_price: float
    buy_amount: float
    buy_time: str
    order_id: str


class SmartGridStrategy:
    """
    智能网格交易策略
    """

    def __init__(self):
        # 动态参数（会根据分析结果调整）
        self.upper_price = config.GRID_UPPER_PRICE
        self.lower_price = config.GRID_LOWER_PRICE
        self.grid_count = config.GRID_COUNT
        self.amount_per_grid = config.AMOUNT_PER_GRID
        self.stop_loss_price = config.STOP_LOSS_PRICE

        # 网格间距
        self.grid_spacing = 0

        # 网格列表
        self.grids: List[GridLevel] = []

        # 交易统计
        self.total_profit = 0.0
        self.trade_count = 0

        # P0-1: 连续止损暂停机制
        self.consecutive_stop_loss_count = 0
        self.max_consecutive_stop_loss = 3
        self.is_halted = False
        self.halt_reason = ""

        # 市场分析结果
        self.market_analysis = None
        self.last_analysis_time = None
        self.analysis_interval = 3600  # 每小时重新分析一次

        # 初始化
        self._init_grids()
        self._load_orders()

        logger.info("智能网格策略初始化完成")

    def _init_grids(self):
        """初始化网格"""
        if self.upper_price <= self.lower_price:
            log_error("价格上限必须大于下限")
            return

        self.grid_spacing = (self.upper_price - self.lower_price) / self.grid_count

        self.grids = []
        for i in range(self.grid_count + 1):
            price = self.lower_price + i * self.grid_spacing
            grid = GridLevel(
                index=i,
                price=round(price, 2),
                is_bought=False,
                buy_price=0.0,
                buy_amount=0.0,
                buy_time="",
                order_id=""
            )
            self.grids.append(grid)

        logger.info(f"网格初始化: {self.lower_price} - {self.upper_price}, {self.grid_count}格")

    def _load_orders(self):
        """加载历史订单"""
        if os.path.exists(config.ORDERS_FILE):
            try:
                with open(config.ORDERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for grid_data in data.get('grids', []):
                        idx = grid_data.get('index', 0)
                        if 0 <= idx < len(self.grids):
                            self.grids[idx].is_bought = grid_data.get('is_bought', False)
                            self.grids[idx].buy_price = grid_data.get('buy_price', 0.0)
                            self.grids[idx].buy_amount = grid_data.get('buy_amount', 0.0)
                            self.grids[idx].buy_time = grid_data.get('buy_time', "")
                            self.grids[idx].order_id = grid_data.get('order_id', "")
                    self.total_profit = data.get('total_profit', 0.0)
                    self.trade_count = data.get('trade_count', 0)
                    # P0-1: 加载暂停状态
                    self.consecutive_stop_loss_count = data.get('consecutive_stop_loss_count', 0)
                    self.is_halted = data.get('is_halted', False)
                    self.halt_reason = data.get('halt_reason', "")
                    logger.info(f"已加载历史记录，累计盈亏: {self.total_profit:.2f} USDT")
                    if self.is_halted:
                        log_warning(f"策略处于暂停状态: {self.halt_reason}")
            except Exception as e:
                log_error(f"加载订单记录失败: {e}")

    def _save_orders(self):
        """保存订单记录"""
        try:
            data = {
                'grids': [asdict(g) for g in self.grids],
                'total_profit': self.total_profit,
                'trade_count': self.trade_count,
                'params': {
                    'upper_price': self.upper_price,
                    'lower_price': self.lower_price,
                    'grid_count': self.grid_count,
                    'amount_per_grid': self.amount_per_grid
                },
                # P0-1: 保存暂停状态
                'consecutive_stop_loss_count': self.consecutive_stop_loss_count,
                'is_halted': self.is_halted,
                'halt_reason': self.halt_reason,
                'last_update': datetime.now().isoformat()
            }
            with open(config.ORDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(f"保存订单记录失败: {e}")

    def analyze_and_adjust(self) -> Dict:
        """
        分析市场并调整参数

        Returns:
            分析结果和调整建议
        """
        logger.info("\n" + "=" * 50)
        logger.info("执行智能分析...")
        logger.info("=" * 50)

        # 执行市场分析
        analysis = macro_analyzer.analyze_market(config.SYMBOL)
        self.market_analysis = analysis
        self.last_analysis_time = datetime.now()

        # 打印分析报告
        macro_analyzer.print_analysis_report(analysis)

        # 获取建议的网格参数
        suggested_params = analysis.get('grid_params', {})

        # 如果环境评分太低，建议暂停
        if not analysis.get('should_trade', True):
            log_warning("市场环境不佳，建议暂停交易")
            return {
                'should_trade': False,
                'reason': analysis.get('warnings', ['市场环境不佳']),
                'environment': analysis.get('environment', MarketEnvironment.CAUTION).value
            }

        # 不在这里更新总资本，应该在启动时设置一次（使用实际总资产）
        # position_manager.set_total_capital(config.AMOUNT_PER_GRID * config.GRID_COUNT)

        # 计算建议仓位
        position = position_manager.calculate_position(
            analysis.get('environment_score', 50),
            analysis.get('recommended_position', 50),
            0  # 初始风险评分
        )

        return {
            'should_trade': True,
            'environment': analysis.get('environment', MarketEnvironment.NEUTRAL).value,
            'environment_score': analysis.get('environment_score', 50),
            'suggested_params': suggested_params,
            'position': position,
            'warnings': analysis.get('warnings', [])
        }

    def apply_suggested_params(self, params: Dict):
        """
        应用建议的网格参数

        Args:
            params: 建议参数
        """
        if not params:
            return

        new_upper = params.get('upper_price')
        new_lower = params.get('lower_price')
        new_count = params.get('grid_count')
        new_amount = params.get('amount_per_grid')

        changes = []

        if new_upper and new_upper != self.upper_price:
            changes.append(f"上限: {self.upper_price} -> {new_upper}")
            self.upper_price = new_upper

        if new_lower and new_lower != self.lower_price:
            changes.append(f"下限: {self.lower_price} -> {new_lower}")
            self.lower_price = new_lower

        if new_count and new_count != self.grid_count:
            changes.append(f"网格数: {self.grid_count} -> {new_count}")
            self.grid_count = new_count

        if new_amount and new_amount != self.amount_per_grid:
            changes.append(f"每格金额: {self.amount_per_grid} -> {new_amount}")
            self.amount_per_grid = new_amount

        if changes:
            logger.info("应用新参数:")
            for change in changes:
                logger.info(f"  {change}")

            # 重新初始化网格（保留已有持仓）
            self._reinit_grids_preserve_positions()

    def _reinit_grids_preserve_positions(self):
        """重新初始化网格，保留已有持仓"""
        # 保存当前持仓
        old_positions = [(g.buy_price, g.buy_amount) for g in self.grids if g.is_bought]

        # 重新计算网格
        self.grid_spacing = (self.upper_price - self.lower_price) / self.grid_count

        new_grids = []
        for i in range(self.grid_count + 1):
            price = self.lower_price + i * self.grid_spacing
            grid = GridLevel(
                index=i,
                price=round(price, 2),
                is_bought=False,
                buy_price=0.0,
                buy_amount=0.0,
                buy_time="",
                order_id=""
            )
            new_grids.append(grid)

        # 尝试将旧持仓映射到新网格
        for buy_price, buy_amount in old_positions:
            # 找到最接近的网格
            closest_idx = 0
            min_diff = float('inf')
            for i, grid in enumerate(new_grids):
                diff = abs(grid.price - buy_price)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i

            if not new_grids[closest_idx].is_bought:
                new_grids[closest_idx].is_bought = True
                new_grids[closest_idx].buy_price = buy_price
                new_grids[closest_idx].buy_amount = buy_amount
                new_grids[closest_idx].buy_time = datetime.now().isoformat()

        self.grids = new_grids
        self._save_orders()
        logger.info("网格重新初始化完成，已保留持仓")

    def sync_with_exchange(self) -> bool:
        """
        P1-1: 启动时与交易所同步持仓状态
        """
        try:
            # 获取当前实际持仓
            position = api.get_position(config.SYMBOL)
            actual_amount = float(position.get('pos', 0)) if position else 0

            # 计算本地记录的持仓
            local_amount = sum(g.buy_amount for g in self.grids if g.is_bought)

            # 比较差异
            diff = abs(actual_amount - local_amount)
            if diff > 0.0001:  # 允许微小误差
                log_warning(f"持仓不一致! 本地: {local_amount:.6f}, 交易所: {actual_amount:.6f}")
                log_warning("建议手动检查后决定是否继续")
                return False

            logger.info(f"持仓同步验证通过: {actual_amount:.6f}")
            return True

        except Exception as e:
            log_error(f"同步持仓状态失败: {e}")
            return False

    def get_grid_index(self, price: float) -> int:
        """根据价格获取网格索引"""
        if price <= self.lower_price:
            return 0
        if price >= self.upper_price:
            return self.grid_count

        index = int((price - self.lower_price) / self.grid_spacing)
        return min(index, self.grid_count)

    def get_position_count(self) -> int:
        """获取持仓网格数"""
        return sum(1 for g in self.grids if g.is_bought)

    def get_position_value(self, current_price: float) -> float:
        """获取持仓价值"""
        total = 0.0
        for g in self.grids:
            if g.is_bought:
                total += g.buy_amount * current_price
        return total

    def check_and_trade(self, current_price: float) -> Dict:
        """
        检查并执行交易

        Args:
            current_price: 当前价格

        Returns:
            交易结果
        """
        result = {
            'action': None,
            'success': False,
            'message': ''
        }

        # P0-1: 检查是否已暂停
        if self.is_halted:
            result['message'] = f'策略已暂停: {self.halt_reason}'
            return result

        # 风控检查
        position_value = self.get_position_value(current_price)
        balance = api.get_balance('USDT') or 0
        total_value = position_value + balance

        risk_assessment = risk_controller.get_risk_assessment(
            current_value=total_value,
            current_price=current_price,
            position_value=position_value
        )

        if not risk_assessment['should_trade']:
            result['action'] = 'risk_stop'
            result['message'] = f"风控暂停: {risk_assessment['action']}"
            return result

        # 检查止损
        if current_price <= self.stop_loss_price:
            # P0-1: 连续止损计数
            self.consecutive_stop_loss_count += 1
            log_warning(f"触发止损! 连续止损次数: {self.consecutive_stop_loss_count}/{self.max_consecutive_stop_loss}")

            if self.consecutive_stop_loss_count >= self.max_consecutive_stop_loss:
                self.is_halted = True
                self.halt_reason = f"连续{self.max_consecutive_stop_loss}次止损，请检查市场环境"
                log_error(f"策略已暂停: {self.halt_reason}")

            result['action'] = 'stop_loss'
            result['message'] = f'触发止损 ({self.consecutive_stop_loss_count}/{self.max_consecutive_stop_loss})'
            return result

        # 检查是否超出范围
        if current_price > self.upper_price:
            result['message'] = f'价格 {current_price} 超出上限 {self.upper_price}'
            return result

        if current_price < self.lower_price:
            result['message'] = f'价格 {current_price} 低于下限 {self.lower_price}'
            return result

        current_grid_index = self.get_grid_index(current_price)

        # 检查买入
        for i in range(current_grid_index, -1, -1):
            grid = self.grids[i]
            if not grid.is_bought:
                if self.get_position_count() >= config.MAX_POSITION_GRIDS:
                    result['message'] = '已达到最大持仓数量'
                    return result

                success = self._execute_buy(grid, current_price)
                if success:
                    result['action'] = 'buy'
                    result['success'] = True
                    result['message'] = f'在网格 {i} 买入成功'
                    return result

        # 检查卖出
        for i in range(current_grid_index + 1, len(self.grids)):
            grid = self.grids[i]
            if grid.is_bought:
                # P2-2: 计算最小卖出价（基于实际买入价）
                min_sell_price = grid.buy_price * (1 + config.MIN_PROFIT_RATE)

                # 同时满足：高于网格价 AND 高于最小盈利价
                if current_price >= grid.price and current_price >= min_sell_price:
                    success = self._execute_sell(grid, current_price)
                    if success:
                        result['action'] = 'sell'
                        result['success'] = True
                        result['message'] = f'在网格 {i} 卖出成功'
                        return result
                elif current_price >= grid.price and current_price < min_sell_price:
                    logger.debug(f"网格 {i}: 价格达到网格线但未达最小利润 (当前:{current_price:.2f}, 需:{min_sell_price:.2f})")

        result['message'] = '无交易信号'
        return result

    def _execute_buy(self, grid: GridLevel, current_price: float) -> bool:
        """
        执行买入
        P1-2: 支持部分成交处理
        """
        logger.info(f"尝试买入: 网格 {grid.index}, 价格 {current_price}")

        order = api.buy_market(self.amount_per_grid)

        if order:
            order_id = order.get('ordId', '')

            # P1-2: 等待并查询实际成交情况
            import time
            time.sleep(1)  # 等待成交

            order_detail = api.get_order_detail(order_id)
            if order_detail:
                fill_sz = float(order_detail.get('fillSz', 0))  # 实际成交数量
                avg_px = float(order_detail.get('avgPx', current_price))  # 平均成交价
                state = order_detail.get('state', '')

                if state == 'filled':  # 完全成交
                    grid.is_bought = True
                    grid.buy_price = avg_px
                    grid.buy_amount = fill_sz
                    grid.buy_time = datetime.now().isoformat()
                    grid.order_id = order_id

                    log_trade("买入", avg_px, fill_sz, grid.index)
                    self._save_orders()
                    self.trade_count += 1
                    return True

                elif state == 'partially_filled':  # 部分成交
                    log_warning(f"订单部分成交: {fill_sz}/{self.amount_per_grid/current_price:.6f}")
                    # 部分成交也记录，避免遗漏
                    if fill_sz > 0:
                        grid.is_bought = True
                        grid.buy_price = avg_px
                        grid.buy_amount = fill_sz
                        grid.buy_time = datetime.now().isoformat()
                        grid.order_id = order_id
                        log_trade("买入(部分)", avg_px, fill_sz, grid.index)
                        self._save_orders()
                        self.trade_count += 1
                        return True
                    return False
                else:
                    log_warning(f"订单状态异常: {state}")
                    return False
            else:
                # 查询失败，使用估算值（降级处理）
                estimated_amount = self.amount_per_grid / current_price
                grid.is_bought = True
                grid.buy_price = current_price
                grid.buy_amount = estimated_amount
                grid.buy_time = datetime.now().isoformat()
                grid.order_id = order_id

                log_warning("无法获取订单详情，使用估算值")
                log_trade("买入(估算)", current_price, estimated_amount, grid.index)
                self._save_orders()
                self.trade_count += 1
                return True

        return False

    def _execute_sell(self, grid: GridLevel, current_price: float) -> bool:
        """
        执行卖出
        P2-1: 手续费计入盈亏计算
        """
        logger.info(f"尝试卖出: 网格 {grid.index}, 买入价 {grid.buy_price}, 当前价 {current_price}")

        order = api.sell_market(grid.buy_amount)

        if order:
            sell_value = grid.buy_amount * current_price
            buy_value = grid.buy_amount * grid.buy_price

            # P2-1: 扣除双边手续费
            buy_fee = buy_value * config.TRADING_FEE_RATE
            sell_fee = sell_value * config.TRADING_FEE_RATE

            gross_profit = sell_value - buy_value  # 毛利润
            net_profit = gross_profit - buy_fee - sell_fee  # 净利润

            self.total_profit += net_profit
            risk_controller.record_trade(net_profit)

            # P0-1: 盈利交易重置连续止损计数
            if net_profit > 0:
                self.consecutive_stop_loss_count = 0

            log_trade("卖出", current_price, grid.buy_amount, grid.index)
            logger.info(f"毛利润: {gross_profit:.4f}, 手续费: {buy_fee + sell_fee:.4f}, 净利润: {net_profit:.4f} USDT")
            logger.info(f"累计净盈亏: {self.total_profit:.4f} USDT")

            grid.is_bought = False
            grid.buy_price = 0.0
            grid.buy_amount = 0.0
            grid.buy_time = ""
            grid.order_id = ""

            self._save_orders()
            self.trade_count += 1
            return True

        return False

    def resume_trading(self):
        """
        P0-1: 手动恢复交易（需人工确认市场环境后调用）
        """
        self.is_halted = False
        self.halt_reason = ""
        self.consecutive_stop_loss_count = 0
        logger.info("策略已恢复交易")

    def get_status(self) -> Dict:
        """获取策略状态"""
        bought_grids = [g.index for g in self.grids if g.is_bought]
        return {
            'position_count': self.get_position_count(),
            'bought_grids': bought_grids,
            'total_profit': round(self.total_profit, 4),
            'trade_count': self.trade_count,
            'grid_count': self.grid_count,
            'upper_price': self.upper_price,
            'lower_price': self.lower_price,
            'amount_per_grid': self.amount_per_grid,
            'environment': self.market_analysis.get('environment', 'unknown').value if self.market_analysis else 'unknown',
            # P0-1: 新增暂停状态
            'is_halted': self.is_halted,
            'halt_reason': self.halt_reason,
            'consecutive_stop_loss': self.consecutive_stop_loss_count
        }

    def print_grid_status(self, current_price: float):
        """打印网格状态"""
        current_idx = self.get_grid_index(current_price)
        print("\n" + "=" * 50)
        print(f"当前价格: {current_price} (网格 {current_idx})")
        print("=" * 50)
        for g in reversed(self.grids):
            marker = "<<<" if g.index == current_idx else ""
            status = "[持仓]" if g.is_bought else "[空仓]"
            print(f"网格 {g.index:2d} | {g.price:8.2f} | {status} {marker}")
        print("=" * 50)
        print(f"持仓: {self.get_position_count()} | 盈亏: {self.total_profit:.4f} USDT")
        print("=" * 50)
