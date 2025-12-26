"""
趋势分析模块
判断市场处于上涨、下跌还是震荡趋势
"""
from typing import List, Dict, Optional
from enum import Enum

import sys
sys.path.append('..')
from data.indicators import Indicators
from logger import logger


class TrendType(Enum):
    """趋势类型"""
    STRONG_UP = "强势上涨"
    UP = "上涨趋势"
    SIDEWAYS = "震荡盘整"
    DOWN = "下跌趋势"
    STRONG_DOWN = "强势下跌"


class TrendAnalyzer:
    """
    趋势分析器
    综合多个指标判断市场趋势
    """

    def __init__(self):
        self.indicators = Indicators()

    def analyze_ma_trend(self, closes: List[float]) -> Dict:
        """
        基于均线分析趋势

        规则:
        - 价格 > MA20 > MA50: 上涨趋势
        - 价格 < MA20 < MA50: 下跌趋势
        - 其他情况: 震荡

        Returns:
            {
                'trend': 趋势方向,
                'strength': 趋势强度 (0-100),
                'details': 详情
            }
        """
        if len(closes) < 50:
            return {'trend': 'unknown', 'strength': 0, 'details': '数据不足'}

        current_price = closes[-1]
        ma20 = self.indicators.sma(closes, 20)[-1]
        ma50 = self.indicators.sma(closes, 50)[-1]

        # 计算价格相对于均线的位置
        price_vs_ma20 = (current_price - ma20) / ma20 * 100
        price_vs_ma50 = (current_price - ma50) / ma50 * 100
        ma20_vs_ma50 = (ma20 - ma50) / ma50 * 100

        # 判断趋势
        if current_price > ma20 > ma50:
            if price_vs_ma20 > 5 and ma20_vs_ma50 > 3:
                trend = TrendType.STRONG_UP
                strength = min(100, 60 + price_vs_ma20)
            else:
                trend = TrendType.UP
                strength = 60
        elif current_price < ma20 < ma50:
            if price_vs_ma20 < -5 and ma20_vs_ma50 < -3:
                trend = TrendType.STRONG_DOWN
                strength = min(100, 60 + abs(price_vs_ma20))
            else:
                trend = TrendType.DOWN
                strength = 60
        else:
            trend = TrendType.SIDEWAYS
            strength = 30 + abs(price_vs_ma20)

        return {
            'trend': trend,
            'strength': round(strength, 1),
            'price': current_price,
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'price_vs_ma20': round(price_vs_ma20, 2),
            'price_vs_ma50': round(price_vs_ma50, 2)
        }

    def analyze_macd_trend(self, closes: List[float]) -> Dict:
        """
        基于MACD分析趋势

        规则:
        - MACD > 0 且 柱状图递增: 上涨
        - MACD < 0 且 柱状图递减: 下跌
        - 其他: 震荡或转折

        Returns:
            趋势分析结果
        """
        if len(closes) < 35:
            return {'trend': 'unknown', 'strength': 0}

        macd_data = self.indicators.macd(closes)
        macd = macd_data['macd'][-1]
        signal = macd_data['signal'][-1]
        histogram = macd_data['histogram'][-1]

        if macd is None or signal is None:
            return {'trend': 'unknown', 'strength': 0}

        # 检查柱状图趋势
        recent_hist = [h for h in macd_data['histogram'][-5:] if h is not None]
        hist_trend = 'up' if len(recent_hist) >= 2 and recent_hist[-1] > recent_hist[-2] else 'down'

        # 判断趋势
        if macd > 0 and macd > signal:
            if histogram > 0 and hist_trend == 'up':
                trend = TrendType.STRONG_UP
                strength = 80
            else:
                trend = TrendType.UP
                strength = 60
        elif macd < 0 and macd < signal:
            if histogram < 0 and hist_trend == 'down':
                trend = TrendType.STRONG_DOWN
                strength = 80
            else:
                trend = TrendType.DOWN
                strength = 60
        else:
            trend = TrendType.SIDEWAYS
            strength = 40

        return {
            'trend': trend,
            'strength': strength,
            'macd': round(macd, 4),
            'signal': round(signal, 4),
            'histogram': round(histogram, 4),
            'histogram_trend': hist_trend
        }

    def analyze_rsi_trend(self, closes: List[float]) -> Dict:
        """
        基于RSI分析超买超卖

        规则:
        - RSI > 70: 超买，可能回调
        - RSI < 30: 超卖，可能反弹
        - 30-70: 正常区间

        Returns:
            RSI分析结果
        """
        if len(closes) < 20:
            return {'status': 'unknown'}

        rsi_values = self.indicators.rsi(closes, 14)
        rsi = rsi_values[-1]

        if rsi is None:
            return {'status': 'unknown'}

        if rsi > 80:
            status = "极度超买"
            signal = "strong_sell"
        elif rsi > 70:
            status = "超买"
            signal = "sell"
        elif rsi > 60:
            status = "偏强"
            signal = "neutral_bullish"
        elif rsi > 40:
            status = "中性"
            signal = "neutral"
        elif rsi > 30:
            status = "偏弱"
            signal = "neutral_bearish"
        elif rsi > 20:
            status = "超卖"
            signal = "buy"
        else:
            status = "极度超卖"
            signal = "strong_buy"

        return {
            'rsi': round(rsi, 2),
            'status': status,
            'signal': signal
        }

    def analyze_bollinger_position(self, closes: List[float]) -> Dict:
        """
        分析价格在布林带中的位置

        Returns:
            布林带位置分析
        """
        if len(closes) < 25:
            return {'position': 'unknown'}

        bb = self.indicators.bollinger_bands(closes, 20, 2)
        upper = bb['upper'][-1]
        middle = bb['middle'][-1]
        lower = bb['lower'][-1]
        price = closes[-1]

        if upper is None:
            return {'position': 'unknown'}

        # 计算价格在布林带中的位置 (0-100)
        band_width = upper - lower
        position = (price - lower) / band_width * 100

        if position > 95:
            status = "触及上轨"
            signal = "overbought"
        elif position > 80:
            status = "接近上轨"
            signal = "high"
        elif position > 55:
            status = "中轨之上"
            signal = "above_middle"
        elif position > 45:
            status = "中轨附近"
            signal = "middle"
        elif position > 20:
            status = "中轨之下"
            signal = "below_middle"
        elif position > 5:
            status = "接近下轨"
            signal = "low"
        else:
            status = "触及下轨"
            signal = "oversold"

        return {
            'position': round(position, 1),
            'status': status,
            'signal': signal,
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2),
            'bandwidth': round((band_width / middle) * 100, 2)  # 带宽百分比
        }

    def get_comprehensive_trend(self, klines: List[Dict]) -> Dict:
        """
        综合分析趋势

        Args:
            klines: K线数据

        Returns:
            综合趋势分析结果
        """
        if not klines or len(klines) < 50:
            return {
                'trend': TrendType.SIDEWAYS,
                'confidence': 0,
                'recommendation': '数据不足，无法判断趋势'
            }

        closes = [k['close'] for k in klines]

        # 获取各项分析
        ma_analysis = self.analyze_ma_trend(closes)
        macd_analysis = self.analyze_macd_trend(closes)
        rsi_analysis = self.analyze_rsi_trend(closes)
        bb_analysis = self.analyze_bollinger_position(closes)

        # 计算趋势得分
        trend_scores = {
            TrendType.STRONG_UP: 0,
            TrendType.UP: 0,
            TrendType.SIDEWAYS: 0,
            TrendType.DOWN: 0,
            TrendType.STRONG_DOWN: 0
        }

        # MA趋势权重: 40%
        if ma_analysis.get('trend'):
            trend_scores[ma_analysis['trend']] += 40

        # MACD趋势权重: 30%
        if macd_analysis.get('trend'):
            trend_scores[macd_analysis['trend']] += 30

        # RSI调整权重: 15%
        rsi_signal = rsi_analysis.get('signal', 'neutral')
        if rsi_signal in ['strong_buy', 'buy']:
            trend_scores[TrendType.UP] += 15
        elif rsi_signal in ['strong_sell', 'sell']:
            trend_scores[TrendType.DOWN] += 15
        else:
            trend_scores[TrendType.SIDEWAYS] += 15

        # 布林带调整权重: 15%
        bb_signal = bb_analysis.get('signal', 'middle')
        if bb_signal in ['overbought', 'high']:
            trend_scores[TrendType.UP] += 10
            trend_scores[TrendType.SIDEWAYS] += 5
        elif bb_signal in ['oversold', 'low']:
            trend_scores[TrendType.DOWN] += 10
            trend_scores[TrendType.SIDEWAYS] += 5
        else:
            trend_scores[TrendType.SIDEWAYS] += 15

        # 确定最终趋势
        final_trend = max(trend_scores, key=trend_scores.get)
        confidence = trend_scores[final_trend]

        # 生成建议
        if final_trend in [TrendType.STRONG_UP, TrendType.UP]:
            if rsi_analysis.get('signal') in ['strong_sell', 'sell']:
                recommendation = "上涨趋势，但RSI超买，注意回调风险"
                grid_advice = "可以运行网格，但上限不宜追高"
            else:
                recommendation = "上涨趋势，适合持有"
                grid_advice = "网格偏多配置，可适当提高仓位"

        elif final_trend in [TrendType.STRONG_DOWN, TrendType.DOWN]:
            if rsi_analysis.get('signal') in ['strong_buy', 'buy']:
                recommendation = "下跌趋势，但RSI超卖，可能反弹"
                grid_advice = "谨慎运行网格，控制仓位"
            else:
                recommendation = "下跌趋势，建议观望或减仓"
                grid_advice = "建议暂停网格或极小仓位"

        else:  # SIDEWAYS
            recommendation = "震荡行情，适合网格策略"
            grid_advice = "网格策略最佳环境，正常仓位运行"

        return {
            'trend': final_trend,
            'trend_name': final_trend.value,
            'confidence': confidence,
            'recommendation': recommendation,
            'grid_advice': grid_advice,
            'details': {
                'ma': ma_analysis,
                'macd': macd_analysis,
                'rsi': rsi_analysis,
                'bollinger': bb_analysis
            }
        }


# 创建全局实例
trend_analyzer = TrendAnalyzer()


if __name__ == '__main__':
    print("趋势分析模块测试...")

    # 模拟上涨趋势的K线数据
    import random
    klines = []
    price = 3000
    for i in range(100):
        price = price * (1 + random.uniform(-0.02, 0.025))  # 略微上涨趋势
        klines.append({
            'open': price,
            'high': price * 1.01,
            'low': price * 0.99,
            'close': price,
            'volume': random.uniform(1000, 5000)
        })

    result = trend_analyzer.get_comprehensive_trend(klines)

    print("\n" + "=" * 50)
    print("趋势分析结果")
    print("=" * 50)
    print(f"趋势判断: {result['trend_name']}")
    print(f"置信度: {result['confidence']}%")
    print(f"建议: {result['recommendation']}")
    print(f"网格建议: {result['grid_advice']}")
    print("-" * 50)
    print("详细指标:")
    print(f"  RSI: {result['details']['rsi'].get('rsi', 'N/A')} ({result['details']['rsi'].get('status', 'N/A')})")
    print(f"  MA20: {result['details']['ma'].get('ma20', 'N/A')}")
    print(f"  布林带位置: {result['details']['bollinger'].get('position', 'N/A')}%")
    print("=" * 50)
