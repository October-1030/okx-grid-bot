"""
技术指标计算模块
计算各种技术分析指标
"""
from typing import List, Dict, Optional
import math


class Indicators:
    """
    技术指标计算器
    """

    @staticmethod
    def sma(prices: List[float], period: int) -> List[Optional[float]]:
        """
        简单移动平均线 (Simple Moving Average)

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            SMA值列表
        """
        result = [None] * len(prices)
        for i in range(period - 1, len(prices)):
            result[i] = sum(prices[i - period + 1:i + 1]) / period
        return result

    @staticmethod
    def ema(prices: List[float], period: int) -> List[Optional[float]]:
        """
        指数移动平均线 (Exponential Moving Average)

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            EMA值列表
        """
        result = [None] * len(prices)
        multiplier = 2 / (period + 1)

        # 第一个EMA值使用SMA
        if len(prices) >= period:
            result[period - 1] = sum(prices[:period]) / period

            # 计算后续EMA
            for i in range(period, len(prices)):
                result[i] = (prices[i] - result[i - 1]) * multiplier + result[i - 1]

        return result

    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """
        相对强弱指数 (Relative Strength Index)

        Args:
            prices: 价格列表
            period: 周期，默认14

        Returns:
            RSI值列表 (0-100)
        """
        result = [None] * len(prices)

        if len(prices) < period + 1:
            return result

        # 计算价格变化
        changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        # 分离涨跌
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]

        # 计算初始平均涨跌
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # 计算第一个RSI
        if avg_loss == 0:
            result[period] = 100
        else:
            rs = avg_gain / avg_loss
            result[period] = 100 - (100 / (1 + rs))

        # 计算后续RSI（使用平滑方法）
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                result[i + 1] = 100
            else:
                rs = avg_gain / avg_loss
                result[i + 1] = 100 - (100 / (1 + rs))

        return result

    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[Optional[float]]]:
        """
        MACD指标 (Moving Average Convergence Divergence)

        Args:
            prices: 价格列表
            fast: 快线周期，默认12
            slow: 慢线周期，默认26
            signal: 信号线周期，默认9

        Returns:
            包含 macd, signal, histogram 的字典
        """
        ema_fast = Indicators.ema(prices, fast)
        ema_slow = Indicators.ema(prices, slow)

        # 计算MACD线
        macd_line = [None] * len(prices)
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]

        # 计算信号线（MACD的EMA）
        macd_values = [v for v in macd_line if v is not None]
        signal_line = [None] * len(prices)

        if len(macd_values) >= signal:
            # 找到MACD开始有效的位置
            start_idx = next(i for i, v in enumerate(macd_line) if v is not None)
            ema_signal = Indicators.ema(macd_values, signal)

            for i, val in enumerate(ema_signal):
                if val is not None:
                    signal_line[start_idx + i] = val

        # 计算柱状图
        histogram = [None] * len(prices)
        for i in range(len(prices)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram[i] = macd_line[i] - signal_line[i]

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, List[Optional[float]]]:
        """
        布林带 (Bollinger Bands)

        Args:
            prices: 价格列表
            period: 周期，默认20
            std_dev: 标准差倍数，默认2

        Returns:
            包含 upper, middle, lower 的字典
        """
        middle = Indicators.sma(prices, period)
        upper = [None] * len(prices)
        lower = [None] * len(prices)

        for i in range(period - 1, len(prices)):
            # 计算标准差
            window = prices[i - period + 1:i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = math.sqrt(variance)

            upper[i] = middle[i] + std_dev * std
            lower[i] = middle[i] - std_dev * std

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    @staticmethod
    def atr(klines: List[Dict], period: int = 14) -> List[Optional[float]]:
        """
        平均真实波幅 (Average True Range)
        用于衡量市场波动性

        Args:
            klines: K线数据列表
            period: 周期，默认14

        Returns:
            ATR值列表
        """
        if len(klines) < 2:
            return [None] * len(klines)

        # 计算真实波幅 (True Range)
        tr = [None]
        for i in range(1, len(klines)):
            high = klines[i]['high']
            low = klines[i]['low']
            prev_close = klines[i - 1]['close']

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)

            tr.append(max(tr1, tr2, tr3))

        # 计算ATR（TR的移动平均）
        result = [None] * len(klines)

        if len(tr) >= period + 1:
            # 第一个ATR使用简单平均
            first_atr = sum(tr[1:period + 1]) / period
            result[period] = first_atr

            # 后续使用平滑方法
            for i in range(period + 1, len(klines)):
                result[i] = (result[i - 1] * (period - 1) + tr[i]) / period

        return result

    @staticmethod
    def support_resistance(klines: List[Dict], lookback: int = 20) -> Dict[str, List[float]]:
        """
        计算支撑位和阻力位

        Args:
            klines: K线数据列表
            lookback: 回看周期

        Returns:
            包含 support 和 resistance 的字典
        """
        if len(klines) < lookback:
            return {'support': [], 'resistance': []}

        highs = [k['high'] for k in klines[-lookback:]]
        lows = [k['low'] for k in klines[-lookback:]]
        closes = [k['close'] for k in klines[-lookback:]]

        # 找局部高点和低点
        resistance_levels = []
        support_levels = []

        for i in range(2, len(highs) - 2):
            # 局部高点
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_levels.append(highs[i])

            # 局部低点
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_levels.append(lows[i])

        # 如果没找到，使用简单的高低点
        if not resistance_levels:
            resistance_levels = [max(highs)]
        if not support_levels:
            support_levels = [min(lows)]

        return {
            'support': sorted(set(support_levels)),
            'resistance': sorted(set(resistance_levels), reverse=True)
        }

    @staticmethod
    def get_current_indicators(klines: List[Dict]) -> Dict:
        """
        获取当前所有指标的最新值

        Args:
            klines: K线数据列表

        Returns:
            所有指标的当前值
        """
        if not klines or len(klines) < 30:
            return {}

        closes = [k['close'] for k in klines]
        current_price = closes[-1]

        # 计算各种指标
        sma20 = Indicators.sma(closes, 20)
        sma50 = Indicators.sma(closes, 50) if len(closes) >= 50 else [None] * len(closes)
        ema12 = Indicators.ema(closes, 12)
        ema26 = Indicators.ema(closes, 26)
        rsi = Indicators.rsi(closes, 14)
        macd = Indicators.macd(closes)
        bb = Indicators.bollinger_bands(closes, 20)
        atr = Indicators.atr(klines, 14)
        sr = Indicators.support_resistance(klines, 20)

        return {
            'price': current_price,
            'sma20': sma20[-1],
            'sma50': sma50[-1] if len(closes) >= 50 else None,
            'ema12': ema12[-1],
            'ema26': ema26[-1],
            'rsi': rsi[-1],
            'macd': macd['macd'][-1],
            'macd_signal': macd['signal'][-1],
            'macd_histogram': macd['histogram'][-1],
            'bb_upper': bb['upper'][-1],
            'bb_middle': bb['middle'][-1],
            'bb_lower': bb['lower'][-1],
            'atr': atr[-1],
            'support': sr['support'],
            'resistance': sr['resistance']
        }


# 创建全局实例
indicators = Indicators()


if __name__ == '__main__':
    # 测试代码
    print("技术指标计算测试...")

    # 模拟价格数据
    test_prices = [
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
        111, 110, 112, 114, 113, 115, 117, 116, 118, 120,
        119, 121, 123, 122, 124, 126, 125, 127, 129, 128
    ]

    print(f"\n测试数据: {len(test_prices)} 个价格点")

    # 测试SMA
    sma = Indicators.sma(test_prices, 10)
    print(f"SMA(10) 最新值: {sma[-1]:.2f}")

    # 测试RSI
    rsi = Indicators.rsi(test_prices, 14)
    print(f"RSI(14) 最新值: {rsi[-1]:.2f}")

    # 测试MACD
    macd = Indicators.macd(test_prices)
    print(f"MACD: {macd['macd'][-1]:.4f}, Signal: {macd['signal'][-1]:.4f}")

    print("\n指标计算测试完成!")
