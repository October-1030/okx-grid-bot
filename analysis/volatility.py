"""
波动率分析模块
分析市场波动性，用于调整网格参数
"""
from typing import List, Dict, Optional
from enum import Enum
import math

import sys
sys.path.append('..')
from data.indicators import Indicators
from logger import logger


class VolatilityLevel(Enum):
    """波动率级别"""
    VERY_LOW = "极低波动"
    LOW = "低波动"
    NORMAL = "正常波动"
    HIGH = "高波动"
    EXTREME = "极端波动"


class VolatilityAnalyzer:
    """
    波动率分析器
    """

    def __init__(self):
        self.indicators = Indicators()

    def calculate_historical_volatility(self, closes: List[float], period: int = 20) -> Optional[float]:
        """
        计算历史波动率（年化）

        使用对数收益率的标准差

        Args:
            closes: 收盘价列表
            period: 计算周期

        Returns:
            年化波动率百分比
        """
        if len(closes) < period + 1:
            return None

        # 计算对数收益率
        log_returns = []
        for i in range(1, len(closes)):
            if closes[i] > 0 and closes[i-1] > 0:
                log_returns.append(math.log(closes[i] / closes[i-1]))

        if len(log_returns) < period:
            return None

        # 取最近period个数据
        recent_returns = log_returns[-period:]

        # 计算标准差
        mean = sum(recent_returns) / len(recent_returns)
        variance = sum((r - mean) ** 2 for r in recent_returns) / len(recent_returns)
        std = math.sqrt(variance)

        # 年化（假设日线数据，一年约365天）
        annualized = std * math.sqrt(365) * 100

        return round(annualized, 2)

    def calculate_atr_percent(self, klines: List[Dict], period: int = 14) -> Optional[float]:
        """
        计算ATR百分比（ATR / 当前价格）

        用于衡量相对波动性

        Args:
            klines: K线数据
            period: ATR周期

        Returns:
            ATR占价格的百分比
        """
        if len(klines) < period + 1:
            return None

        atr_values = self.indicators.atr(klines, period)
        atr = atr_values[-1]

        if atr is None:
            return None

        current_price = klines[-1]['close']
        atr_percent = (atr / current_price) * 100

        return round(atr_percent, 2)

    def calculate_range_percent(self, klines: List[Dict], period: int = 20) -> Dict:
        """
        计算价格范围百分比

        Args:
            klines: K线数据
            period: 回看周期

        Returns:
            价格范围分析
        """
        if len(klines) < period:
            return {}

        recent = klines[-period:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]

        highest = max(highs)
        lowest = min(lows)
        current = closes[-1]
        avg = sum(closes) / len(closes)

        range_value = highest - lowest
        range_percent = (range_value / avg) * 100

        return {
            'highest': highest,
            'lowest': lowest,
            'range': range_value,
            'range_percent': round(range_percent, 2),
            'current_position': round((current - lowest) / range_value * 100, 1) if range_value > 0 else 50
        }

    def get_volatility_level(self, volatility_percent: float) -> VolatilityLevel:
        """
        根据波动率百分比判断级别

        Args:
            volatility_percent: 波动率百分比

        Returns:
            波动率级别
        """
        if volatility_percent < 20:
            return VolatilityLevel.VERY_LOW
        elif volatility_percent < 40:
            return VolatilityLevel.LOW
        elif volatility_percent < 80:
            return VolatilityLevel.NORMAL
        elif volatility_percent < 120:
            return VolatilityLevel.HIGH
        else:
            return VolatilityLevel.EXTREME

    def suggest_grid_spacing(self, klines: List[Dict]) -> Dict:
        """
        根据波动率建议网格间距

        Args:
            klines: K线数据

        Returns:
            网格间距建议
        """
        if len(klines) < 20:
            return {'error': '数据不足'}

        # 计算ATR百分比
        atr_percent = self.calculate_atr_percent(klines, 14)

        # 计算历史波动率
        closes = [k['close'] for k in klines]
        hist_volatility = self.calculate_historical_volatility(closes, 20)

        # 计算范围
        range_info = self.calculate_range_percent(klines, 20)

        if atr_percent is None:
            return {'error': '无法计算波动率'}

        current_price = klines[-1]['close']

        # 网格间距建议：基于ATR
        # 一般建议网格间距为 1-2 倍 ATR
        suggested_spacing_min = current_price * atr_percent / 100 * 0.8
        suggested_spacing_max = current_price * atr_percent / 100 * 1.5

        # 建议网格数量：基于价格范围和间距
        if range_info.get('range'):
            suggested_grids_min = int(range_info['range'] / suggested_spacing_max)
            suggested_grids_max = int(range_info['range'] / suggested_spacing_min)
        else:
            suggested_grids_min = 5
            suggested_grids_max = 20

        # 确定波动级别
        volatility_level = self.get_volatility_level(hist_volatility or atr_percent * 10)

        # 根据波动级别调整建议
        if volatility_level == VolatilityLevel.EXTREME:
            advice = "极端波动，建议暂停网格或使用极宽间距"
            position_advice = "仓位降至20%以下"
        elif volatility_level == VolatilityLevel.HIGH:
            advice = "高波动，适当放宽网格间距"
            position_advice = "仓位控制在50%以内"
        elif volatility_level == VolatilityLevel.NORMAL:
            advice = "波动正常，标准网格配置"
            position_advice = "正常仓位"
        elif volatility_level == VolatilityLevel.LOW:
            advice = "低波动，可以适当缩小网格间距"
            position_advice = "可适当提高仓位"
        else:
            advice = "波动极低，网格利润空间有限"
            position_advice = "利润有限，注意手续费损耗"

        return {
            'atr_percent': atr_percent,
            'historical_volatility': hist_volatility,
            'volatility_level': volatility_level.value,
            'price_range': range_info,
            'suggested_spacing': {
                'min': round(suggested_spacing_min, 2),
                'max': round(suggested_spacing_max, 2),
                'percent_min': round(suggested_spacing_min / current_price * 100, 2),
                'percent_max': round(suggested_spacing_max / current_price * 100, 2)
            },
            'suggested_grids': {
                'min': max(3, suggested_grids_min),
                'max': min(30, suggested_grids_max)
            },
            'advice': advice,
            'position_advice': position_advice
        }

    def detect_volatility_spike(self, klines: List[Dict], threshold: float = 2.0) -> Dict:
        """
        检测波动率突变（异常波动）

        Args:
            klines: K线数据
            threshold: 异常阈值（当前ATR / 历史平均ATR）

        Returns:
            波动突变检测结果
        """
        if len(klines) < 30:
            return {'spike_detected': False, 'reason': '数据不足'}

        # 计算历史ATR
        atr_values = self.indicators.atr(klines, 14)
        valid_atr = [v for v in atr_values if v is not None]

        if len(valid_atr) < 10:
            return {'spike_detected': False, 'reason': 'ATR数据不足'}

        current_atr = valid_atr[-1]
        historical_avg = sum(valid_atr[:-5]) / len(valid_atr[:-5])

        ratio = current_atr / historical_avg if historical_avg > 0 else 1

        spike_detected = ratio > threshold

        return {
            'spike_detected': spike_detected,
            'current_atr': round(current_atr, 2),
            'historical_avg_atr': round(historical_avg, 2),
            'ratio': round(ratio, 2),
            'threshold': threshold,
            'message': "检测到异常波动！" if spike_detected else "波动正常"
        }

    def get_comprehensive_volatility(self, klines: List[Dict]) -> Dict:
        """
        综合波动率分析

        Args:
            klines: K线数据

        Returns:
            综合波动率分析结果
        """
        if not klines or len(klines) < 30:
            return {
                'error': '数据不足',
                'volatility_level': VolatilityLevel.NORMAL.value,
                'grid_suitable': True
            }

        closes = [k['close'] for k in klines]
        current_price = closes[-1]

        # 各项分析
        atr_percent = self.calculate_atr_percent(klines, 14)
        hist_vol = self.calculate_historical_volatility(closes, 20)
        range_info = self.calculate_range_percent(klines, 20)
        spacing_suggestion = self.suggest_grid_spacing(klines)
        spike_detection = self.detect_volatility_spike(klines)

        # 综合评分
        volatility_score = 50  # 默认中等

        if atr_percent:
            if atr_percent < 1:
                volatility_score -= 20
            elif atr_percent < 2:
                volatility_score -= 10
            elif atr_percent > 5:
                volatility_score += 20
            elif atr_percent > 3:
                volatility_score += 10

        if spike_detection['spike_detected']:
            volatility_score += 30

        # 确定是否适合网格
        if volatility_score > 80:
            grid_suitable = False
            grid_message = "波动过大，不建议运行网格"
        elif volatility_score < 20:
            grid_suitable = True
            grid_message = "波动较小，网格利润有限"
        else:
            grid_suitable = True
            grid_message = "波动适中，适合网格策略"

        return {
            'current_price': current_price,
            'atr_percent': atr_percent,
            'historical_volatility': hist_vol,
            'volatility_score': volatility_score,
            'volatility_level': spacing_suggestion.get('volatility_level', 'unknown'),
            'range': range_info,
            'spike_detection': spike_detection,
            'grid_suitable': grid_suitable,
            'grid_message': grid_message,
            'suggested_spacing': spacing_suggestion.get('suggested_spacing'),
            'suggested_grids': spacing_suggestion.get('suggested_grids'),
            'position_advice': spacing_suggestion.get('position_advice')
        }


# 创建全局实例
volatility_analyzer = VolatilityAnalyzer()


if __name__ == '__main__':
    print("波动率分析模块测试...")

    # 模拟K线数据
    import random
    klines = []
    price = 3500
    for i in range(60):
        change = random.uniform(-0.03, 0.03)
        price = price * (1 + change)
        high = price * (1 + abs(change) * 0.5)
        low = price * (1 - abs(change) * 0.5)
        klines.append({
            'open': price,
            'high': high,
            'low': low,
            'close': price,
            'volume': random.uniform(1000, 5000)
        })

    result = volatility_analyzer.get_comprehensive_volatility(klines)

    print("\n" + "=" * 50)
    print("波动率分析结果")
    print("=" * 50)
    print(f"当前价格: {result['current_price']:.2f}")
    print(f"ATR百分比: {result['atr_percent']}%")
    print(f"历史波动率: {result['historical_volatility']}%")
    print(f"波动级别: {result['volatility_level']}")
    print(f"波动评分: {result['volatility_score']}")
    print("-" * 50)
    print(f"是否适合网格: {'是' if result['grid_suitable'] else '否'}")
    print(f"建议: {result['grid_message']}")
    print(f"仓位建议: {result['position_advice']}")

    if result.get('suggested_spacing'):
        spacing = result['suggested_spacing']
        print(f"\n建议网格间距: {spacing['min']:.2f} - {spacing['max']:.2f}")
        print(f"间距百分比: {spacing['percent_min']}% - {spacing['percent_max']}%")

    if result['spike_detection']['spike_detected']:
        print(f"\n⚠️ 警告: {result['spike_detection']['message']}")

    print("=" * 50)
