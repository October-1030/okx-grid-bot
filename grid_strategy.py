"""
网格交易策略模块
"""
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import config
from logger import logger, log_trade, log_error, log_warning
from okx_api import api


@dataclass
class GridLevel:
    """
    网格层级
    """
    index: int           # 网格索引（0 = 最低价，n = 最高价）
    price: float         # 该格的价格
    is_bought: bool      # 是否已在该格买入
    buy_price: float     # 实际买入价格
    buy_amount: float    # 买入的币数量
    buy_time: str        # 买入时间
    order_id: str        # 订单ID


class GridStrategy:
    """
    网格交易策略
    """

    def __init__(self):
        self.upper_price = config.GRID_UPPER_PRICE
        self.lower_price = config.GRID_LOWER_PRICE
        self.grid_count = config.GRID_COUNT
        self.amount_per_grid = config.AMOUNT_PER_GRID
        self.stop_loss_price = config.STOP_LOSS_PRICE

        # 计算网格间距
        self.grid_spacing = (self.upper_price - self.lower_price) / self.grid_count

        # 初始化网格
        self.grids: List[GridLevel] = []
        self._init_grids()

        # 加载历史订单记录
        self._load_orders()

        # 统计
        self.total_profit = 0.0
        self.trade_count = 0

        logger.info(f"网格策略初始化完成")
        logger.info(f"价格区间: {self.lower_price} - {self.upper_price}")
        logger.info(f"网格数量: {self.grid_count}, 间距: {self.grid_spacing:.2f}")
        logger.info(f"每格金额: {self.amount_per_grid} USDT")

    def _init_grids(self):
        """
        初始化网格层级
        """
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

    def _load_orders(self):
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
                            self.grids[idx].is_bought = grid_data.get('is_bought', False)
                            self.grids[idx].buy_price = grid_data.get('buy_price', 0.0)
                            self.grids[idx].buy_amount = grid_data.get('buy_amount', 0.0)
                            self.grids[idx].buy_time = grid_data.get('buy_time', "")
                            self.grids[idx].order_id = grid_data.get('order_id', "")
                    self.total_profit = data.get('total_profit', 0.0)
                    self.trade_count = data.get('trade_count', 0)
                    logger.info(f"已加载历史订单记录，累计盈亏: {self.total_profit:.2f} USDT")
            except Exception as e:
                log_error(f"加载订单记录失败: {e}")

    def _save_orders(self):
        """
        保存订单记录到文件
        """
        try:
            data = {
                'grids': [asdict(g) for g in self.grids],
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

    def check_and_trade(self, current_price: float) -> Dict:
        """
        根据当前价格检查并执行交易

        Returns:
            交易结果字典
        """
        result = {
            'action': None,
            'success': False,
            'message': ''
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
            grid.buy_time = datetime.now().isoformat()
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
            grid.buy_time = ""
            grid.order_id = ""

            # 保存订单记录
            self._save_orders()

            self.trade_count += 1
            return True

        return False

    def get_status(self) -> Dict:
        """
        获取策略状态
        """
        bought_grids = [g.index for g in self.grids if g.is_bought]
        return {
            'position_count': self.get_position_count(),
            'bought_grids': bought_grids,
            'total_profit': round(self.total_profit, 4),
            'trade_count': self.trade_count,
            'grid_count': self.grid_count,
            'upper_price': self.upper_price,
            'lower_price': self.lower_price
        }

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
