"""
网格交易策略模块

实现网格交易的核心逻辑，包括：
- 网格初始化和管理
- 买卖信号检测
- 订单执行和记录
"""
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from okx_grid_bot.utils import config
from okx_grid_bot.utils.logger import logger, log_trade, log_error, log_warning
from okx_grid_bot.utils.validators import validate_grid_params, ValidationError
from okx_grid_bot.api.okx_client import api
from okx_grid_bot.types import GridLevel, TradeResult
from okx_grid_bot.strategy.base import BaseStrategy, Signal, SignalAction, MarketData


class GridStrategy(BaseStrategy):
    """
    网格交易策略

    继承 BaseStrategy，实现网格交易逻辑。
    """

    # 策略元信息
    name = "网格交易策略"
    version = "2.0.0"
    description = "在价格区间内自动低买高卖"

    def __init__(self, strategy_config: Optional[Dict[str, Any]] = None):
        # 从配置或默认值获取参数
        cfg = strategy_config or {}
        self.upper_price = cfg.get('upper_price', config.GRID_UPPER_PRICE)
        self.lower_price = cfg.get('lower_price', config.GRID_LOWER_PRICE)
        self.grid_count = cfg.get('grid_count', config.GRID_COUNT)
        self.amount_per_grid = cfg.get('amount_per_grid', config.AMOUNT_PER_GRID)
        self.stop_loss_price = cfg.get('stop_loss_price', config.STOP_LOSS_PRICE)

        # 统计
        self.total_profit = 0.0
        self.trade_count = 0

        # 调用父类初始化（会调用 setup）
        super().__init__(strategy_config)

    def setup(self) -> None:
        """策略初始化"""
        # 验证参数
        validate_grid_params(
            upper_price=self.upper_price,
            lower_price=self.lower_price,
            grid_count=self.grid_count,
            amount_per_grid=self.amount_per_grid,
            stop_loss_price=self.stop_loss_price,
        )

        # 计算网格间距
        self.grid_spacing = (self.upper_price - self.lower_price) / self.grid_count

        # 初始化网格
        self.grids: List[GridLevel] = []
        self._init_grids()

        # 加载历史订单记录
        self._load_orders()

        logger.info(f"{self.name} 初始化完成")
        logger.info(f"价格区间: {self.lower_price} - {self.upper_price}")
        logger.info(f"网格数量: {self.grid_count}, 间距: {self.grid_spacing:.2f}")
        logger.info(f"每格金额: {self.amount_per_grid} USDT")

    def analyze(self, market_data: MarketData) -> Signal:
        """
        分析市场数据，返回交易信号

        这是 BaseStrategy 要求实现的核心方法。
        """
        current_price = market_data.current_price

        # 检查止损
        if current_price <= self.stop_loss_price:
            return Signal(
                action=SignalAction.STOP_LOSS,
                price=current_price,
                reason=f"触发止损: {current_price} <= {self.stop_loss_price}"
            )

        # 检查是否超出网格范围
        if current_price > self.upper_price:
            return Signal(
                action=SignalAction.HOLD,
                price=current_price,
                reason=f"价格 {current_price} 超出上限 {self.upper_price}"
            )

        if current_price < self.lower_price:
            return Signal(
                action=SignalAction.HOLD,
                price=current_price,
                reason=f"价格 {current_price} 低于下限 {self.lower_price}"
            )

        # 获取当前价格所在的网格
        current_grid_index = self.get_grid_index(current_price)

        # 检查是否需要买入
        for i in range(current_grid_index, -1, -1):
            grid = self.grids[i]
            if not grid.is_bought:
                if self.get_position_count() >= config.MAX_POSITION_GRIDS:
                    return Signal(
                        action=SignalAction.HOLD,
                        price=current_price,
                        reason="已达到最大持仓数量"
                    )
                return Signal(
                    action=SignalAction.BUY,
                    price=current_price,
                    amount=self.amount_per_grid,
                    reason=f"网格 {i} 触发买入",
                    metadata={'grid_index': i}
                )

        # 检查是否需要卖出
        for i in range(current_grid_index + 1, len(self.grids)):
            grid = self.grids[i]
            if grid.is_bought and current_price >= grid.price:
                return Signal(
                    action=SignalAction.SELL,
                    price=current_price,
                    amount=grid.buy_amount,
                    reason=f"网格 {i} 触发卖出",
                    metadata={'grid_index': i, 'buy_price': grid.buy_price}
                )

        return Signal(
            action=SignalAction.HOLD,
            price=current_price,
            reason="无交易信号"
        )

    def _init_grids(self) -> None:
        """
        初始化网格层级
        """
        self.grids = []
        for i in range(self.grid_count + 1):
            price = self.lower_price + i * self.grid_spacing
            # 使用 types.py 中的 GridLevel，它有默认值
            grid = GridLevel(
                index=i,
                price=round(price, 2)
            )
            self.grids.append(grid)

    def _load_orders(self) -> None:
        """
        从文件加载订单记录
        """
        if os.path.exists(config.ORDERS_FILE):
            try:
                with open(config.ORDERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for grid_data in data.get('grids', []):
                        idx = grid_data.get('index', 0)
                        if 0 <= idx < len(self.grids):
                            # 使用 GridLevel.from_dict 加载
                            self.grids[idx] = GridLevel.from_dict(grid_data)
                    self.total_profit = data.get('total_profit', 0.0)
                    self.trade_count = data.get('trade_count', 0)
                    logger.info(f"已加载历史订单记录，累计盈亏: {self.total_profit:.2f} USDT")
            except Exception as e:
                log_error(f"加载订单记录失败: {e}")

    def _save_orders(self) -> None:
        """
        保存订单记录到文件
        """
        try:
            data = {
                'grids': [g.to_dict() for g in self.grids],  # 使用 to_dict 方法
                'total_profit': self.total_profit,
                'trade_count': self.trade_count,
                'last_update': datetime.now().isoformat()
            }
            with open(config.ORDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(f"保存订单记录失败: {e}")

    def get_grid_index(self, price: float) -> int:
        """
        根据价格获取所在的网格索引
        """
        if price <= self.lower_price:
            return 0
        if price >= self.upper_price:
            return self.grid_count

        index = int((price - self.lower_price) / self.grid_spacing)
        return min(index, self.grid_count)

    def get_position_count(self) -> int:
        """
        获取当前持仓的网格数量
        """
        return sum(1 for g in self.grids if g.is_bought)

    def get_total_position_value(self, current_price: float) -> float:
        """
        计算当前持仓总价值
        """
        total = 0.0
        for g in self.grids:
            if g.is_bought:
                total += g.buy_amount * current_price
        return total

    def check_and_trade(self, current_price: float) -> TradeResult:
        """
        根据当前价格检查并执行交易

        Args:
            current_price: 当前市场价格

        Returns:
            TradeResult: 包含交易动作、是否成功、消息等信息
        """
        result: TradeResult = {
            'action': None,
            'success': False,
            'message': '',
            'order_id': None,
            'price': current_price,
            'amount': None
        }

        # 检查止损
        if current_price <= self.stop_loss_price:
            log_warning(f"触发止损! 当前价格 {current_price} <= 止损价 {self.stop_loss_price}")
            result['action'] = 'stop_loss'
            result['message'] = '触发止损'
            # 这里可以添加平仓逻辑
            return result

        # 检查是否超出网格范围
        if current_price > self.upper_price:
            result['message'] = f'价格 {current_price} 超出上限 {self.upper_price}，暂不交易'
            return result

        if current_price < self.lower_price:
            result['message'] = f'价格 {current_price} 低于下限 {self.lower_price}，暂不交易'
            return result

        # 获取当前价格所在的网格
        current_grid_index = self.get_grid_index(current_price)

        # 检查是否需要买入
        # 买入条件：当前格及以下的格子未持仓
        for i in range(current_grid_index, -1, -1):
            grid = self.grids[i]
            if not grid.is_bought:
                # 检查是否超过最大持仓
                if self.get_position_count() >= config.MAX_POSITION_GRIDS:
                    result['message'] = '已达到最大持仓数量'
                    return result

                # 执行买入
                success = self._execute_buy(grid, current_price)
                if success:
                    result['action'] = 'buy'
                    result['success'] = True
                    result['message'] = f'在网格 {i} 买入成功'
                    return result

        # 检查是否需要卖出
        # 卖出条件：当前格以上的格子有持仓，且当前价格高于买入价
        for i in range(current_grid_index + 1, len(self.grids)):
            grid = self.grids[i]
            if grid.is_bought and current_price >= grid.price:
                # 执行卖出
                success = self._execute_sell(grid, current_price)
                if success:
                    result['action'] = 'sell'
                    result['success'] = True
                    result['message'] = f'在网格 {i} 卖出成功'
                    return result

        result['message'] = '无交易信号'
        return result

    def _execute_buy(self, grid: GridLevel, current_price: float) -> bool:
        """
        执行买入
        """
        logger.info(f"尝试买入: 网格 {grid.index}, 目标价格 {grid.price}, 当前价格 {current_price}")

        # 调用 API 买入
        order = api.buy_market(self.amount_per_grid)

        if order:
            # 获取实际成交信息
            order_id = order.get('ordId', '')

            # 估算买入数量（实际应该查询订单详情）
            estimated_amount = self.amount_per_grid / current_price

            # 更新网格状态
            grid.is_bought = True
            grid.buy_price = current_price
            grid.buy_amount = estimated_amount
            grid.buy_time = datetime.now()  # 使用 datetime 对象
            grid.order_id = order_id

            # 记录日志
            log_trade("买入", current_price, estimated_amount, grid.index)

            # 保存订单记录
            self._save_orders()

            self.trade_count += 1
            return True

        return False

    def _execute_sell(self, grid: GridLevel, current_price: float) -> bool:
        """
        执行卖出
        """
        logger.info(f"尝试卖出: 网格 {grid.index}, 买入价 {grid.buy_price}, 当前价格 {current_price}")

        # 调用 API 卖出
        order = api.sell_market(grid.buy_amount)

        if order:
            # 计算盈亏
            sell_value = grid.buy_amount * current_price
            buy_value = grid.buy_amount * grid.buy_price
            profit = sell_value - buy_value

            self.total_profit += profit

            # 记录日志
            log_trade("卖出", current_price, grid.buy_amount, grid.index)
            logger.info(f"本次盈亏: {profit:.4f} USDT, 累计盈亏: {self.total_profit:.4f} USDT")

            # 重置网格状态
            grid.is_bought = False
            grid.buy_price = 0.0
            grid.buy_amount = 0.0
            grid.buy_time = None  # 使用 None
            grid.order_id = None

            # 保存订单记录
            self._save_orders()

            self.trade_count += 1
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """
        获取策略状态

        继承并扩展父类的状态信息。
        """
        # 获取父类状态
        status = super().get_status()

        # 添加网格策略特有的状态
        bought_grids = [g.index for g in self.grids if g.is_bought]
        status.update({
            'position_count': self.get_position_count(),
            'bought_grids': bought_grids,
            'total_profit': round(self.total_profit, 4),
            'trade_count': self.trade_count,
            'grid_count': self.grid_count,
            'upper_price': self.upper_price,
            'lower_price': self.lower_price,
            'grid_spacing': round(self.grid_spacing, 2),
        })
        return status

    def on_order_filled(self, order_id: str, price: float, amount: float) -> None:
        """
        订单成交回调

        当订单成交时更新网格状态。
        """
        # 查找对应的网格
        for grid in self.grids:
            if grid.order_id == order_id:
                logger.info(f"订单 {order_id} 成交: 价格={price}, 数量={amount}")
                # 更新实际成交信息
                grid.buy_price = price
                grid.buy_amount = amount
                self._save_orders()
                break

    def reset(self) -> None:
        """重置策略状态"""
        self.total_profit = 0.0
        self.trade_count = 0
        self._init_grids()
        logger.info(f"{self.name} 已重置")

    def print_grid_status(self, current_price: float):
        """
        打印网格状态（调试用）
        """
        current_idx = self.get_grid_index(current_price)
        print("\n" + "=" * 50)
        print(f"当前价格: {current_price} (网格 {current_idx})")
        print("=" * 50)
        for g in reversed(self.grids):
            marker = "<<<" if g.index == current_idx else ""
            status = "[已买入]" if g.is_bought else "[空仓]"
            print(f"网格 {g.index:2d} | {g.price:8.2f} | {status} {marker}")
        print("=" * 50)
        print(f"持仓格数: {self.get_position_count()} | 累计盈亏: {self.total_profit:.4f} USDT")
        print("=" * 50 + "\n")
