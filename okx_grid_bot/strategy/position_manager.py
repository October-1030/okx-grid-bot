"""
仓位管理模块
根据市场环境动态调整仓位
"""
from typing import Dict, Optional
from enum import Enum

from okx_grid_bot.utils.logger import logger


class PositionMode(Enum):
    """仓位模式"""
    AGGRESSIVE = "激进"     # 满仓位
    NORMAL = "正常"         # 标准仓位
    CONSERVATIVE = "保守"   # 低仓位
    DEFENSIVE = "防守"      # 极低仓位
    STOPPED = "停止"        # 不持仓


class PositionManager:
    """
    仓位管理器
    根据市场环境和风险评估动态调整仓位
    """

    def __init__(self, total_capital: float = 500):
        """
        初始化仓位管理器

        Args:
            total_capital: 总资本
        """
        self.total_capital = total_capital
        self.current_mode = PositionMode.NORMAL
        self.position_ratio = 0.5  # 当前仓位比例 (0-1)
        self.max_position_ratio = 0.8  # 最大仓位比例
        self.min_position_ratio = 0.1  # 最小仓位比例

    def set_total_capital(self, capital: float):
        """设置总资本"""
        self.total_capital = capital
        logger.info(f"总资本设置为: {capital} USDT")

    def calculate_position(self, environment_score: int, recommended_position: int,
                          risk_score: int = 0) -> Dict:
        """
        计算建议仓位

        Args:
            environment_score: 环境评分 (0-100)
            recommended_position: 建议仓位百分比 (0-100)
            risk_score: 风险评分 (0-100)

        Returns:
            仓位建议
        """
        # 基础仓位 = 建议仓位
        base_ratio = recommended_position / 100

        # 根据环境调整
        if environment_score >= 75:
            env_multiplier = 1.2
            self.current_mode = PositionMode.AGGRESSIVE
        elif environment_score >= 60:
            env_multiplier = 1.0
            self.current_mode = PositionMode.NORMAL
        elif environment_score >= 45:
            env_multiplier = 0.7
            self.current_mode = PositionMode.CONSERVATIVE
        elif environment_score >= 30:
            env_multiplier = 0.4
            self.current_mode = PositionMode.DEFENSIVE
        else:
            env_multiplier = 0
            self.current_mode = PositionMode.STOPPED

        # 根据风险评分调整
        if risk_score >= 60:
            risk_multiplier = 0.3
        elif risk_score >= 40:
            risk_multiplier = 0.6
        elif risk_score >= 20:
            risk_multiplier = 0.8
        else:
            risk_multiplier = 1.0

        # 计算最终仓位比例
        final_ratio = base_ratio * env_multiplier * risk_multiplier

        # 限制在范围内
        final_ratio = max(self.min_position_ratio, min(self.max_position_ratio, final_ratio))

        # 如果模式是停止，强制为0
        if self.current_mode == PositionMode.STOPPED:
            final_ratio = 0

        self.position_ratio = final_ratio

        # 计算实际金额
        position_amount = self.total_capital * final_ratio

        return {
            'mode': self.current_mode.value,
            'ratio': round(final_ratio * 100, 1),
            'amount': round(position_amount, 2),
            'per_grid_amount': None,  # 需要知道网格数才能计算
            'factors': {
                'base_ratio': round(base_ratio * 100, 1),
                'env_multiplier': env_multiplier,
                'risk_multiplier': risk_multiplier
            }
        }

    def calculate_grid_amount(self, total_amount: float, grid_count: int) -> Dict:
        """
        计算每个网格的投入金额

        Args:
            total_amount: 总投入金额
            grid_count: 网格数量

        Returns:
            网格金额分配
        """
        # 基础平均分配
        base_per_grid = total_amount / grid_count

        # 可以实现更复杂的分配策略
        # 例如：金字塔式、倒金字塔式等

        return {
            'per_grid': round(base_per_grid, 2),
            'total': round(total_amount, 2),
            'grid_count': grid_count,
            'strategy': 'equal'  # 平均分配
        }

    def calculate_pyramid_allocation(self, total_amount: float, grid_count: int,
                                    current_price_position: float) -> Dict:
        """
        金字塔式仓位分配
        价格越低，每格投入越多

        Args:
            total_amount: 总投入金额
            grid_count: 网格数量
            current_price_position: 当前价格在区间中的位置 (0-100)

        Returns:
            金字塔分配方案
        """
        allocations = []

        # 根据当前价格位置调整金字塔方向
        if current_price_position > 50:
            # 价格偏高，倒金字塔（上面格子投入多）
            weights = list(range(1, grid_count + 1))
        else:
            # 价格偏低，正金字塔（下面格子投入多）
            weights = list(range(grid_count, 0, -1))

        total_weight = sum(weights)

        for i, weight in enumerate(weights):
            allocation = (weight / total_weight) * total_amount
            allocations.append(round(allocation, 2))

        return {
            'allocations': allocations,
            'total': round(sum(allocations), 2),
            'grid_count': grid_count,
            'strategy': 'pyramid',
            'direction': 'inverse' if current_price_position > 50 else 'normal'
        }

    def should_add_position(self, current_ratio: float, target_ratio: float,
                           threshold: float = 0.1) -> Dict:
        """
        判断是否应该加仓

        Args:
            current_ratio: 当前仓位比例
            target_ratio: 目标仓位比例
            threshold: 触发阈值

        Returns:
            加仓建议
        """
        diff = target_ratio - current_ratio

        if diff > threshold:
            return {
                'should_add': True,
                'amount_ratio': round(diff, 2),
                'reason': f"当前仓位{current_ratio*100:.1f}%低于目标{target_ratio*100:.1f}%"
            }

        return {
            'should_add': False,
            'amount_ratio': 0,
            'reason': "仓位在目标范围内"
        }

    def should_reduce_position(self, current_ratio: float, target_ratio: float,
                              threshold: float = 0.1) -> Dict:
        """
        判断是否应该减仓

        Args:
            current_ratio: 当前仓位比例
            target_ratio: 目标仓位比例
            threshold: 触发阈值

        Returns:
            减仓建议
        """
        diff = current_ratio - target_ratio

        if diff > threshold:
            return {
                'should_reduce': True,
                'amount_ratio': round(diff, 2),
                'reason': f"当前仓位{current_ratio*100:.1f}%高于目标{target_ratio*100:.1f}%"
            }

        return {
            'should_reduce': False,
            'amount_ratio': 0,
            'reason': "仓位在目标范围内"
        }

    def get_position_summary(self, current_position_value: float) -> Dict:
        """
        获取仓位概要

        Args:
            current_position_value: 当前持仓价值

        Returns:
            仓位概要
        """
        current_ratio = current_position_value / self.total_capital if self.total_capital > 0 else 0
        target_ratio = self.position_ratio

        return {
            'mode': self.current_mode.value,
            'total_capital': self.total_capital,
            'current_position': round(current_position_value, 2),
            'current_ratio': round(current_ratio * 100, 1),
            'target_ratio': round(target_ratio * 100, 1),
            'available_capital': round(self.total_capital - current_position_value, 2),
            'max_ratio': round(self.max_position_ratio * 100, 1),
            'min_ratio': round(self.min_position_ratio * 100, 1)
        }


# 创建全局实例
position_manager = PositionManager()


if __name__ == '__main__':
    print("仓位管理模块测试...")

    # 设置资本
    position_manager.set_total_capital(500)

    # 测试不同环境下的仓位计算
    test_cases = [
        {'env_score': 80, 'rec_position': 70, 'risk_score': 10, 'desc': '极佳环境'},
        {'env_score': 60, 'rec_position': 50, 'risk_score': 20, 'desc': '良好环境'},
        {'env_score': 45, 'rec_position': 40, 'risk_score': 40, 'desc': '中性环境'},
        {'env_score': 30, 'rec_position': 20, 'risk_score': 60, 'desc': '谨慎环境'},
        {'env_score': 20, 'rec_position': 10, 'risk_score': 80, 'desc': '危险环境'},
    ]

    print("\n" + "=" * 60)
    print("仓位计算测试")
    print("=" * 60)

    for case in test_cases:
        result = position_manager.calculate_position(
            case['env_score'],
            case['rec_position'],
            case['risk_score']
        )
        print(f"\n{case['desc']}:")
        print(f"  环境评分: {case['env_score']}, 风险评分: {case['risk_score']}")
        print(f"  仓位模式: {result['mode']}")
        print(f"  建议仓位: {result['ratio']}% ({result['amount']} USDT)")

    # 测试金字塔分配
    print("\n" + "-" * 60)
    print("金字塔分配测试 (10格, 200 USDT)")
    pyramid = position_manager.calculate_pyramid_allocation(200, 10, 30)
    print(f"策略: {pyramid['strategy']} ({pyramid['direction']})")
    print(f"分配: {pyramid['allocations']}")

    print("=" * 60)
