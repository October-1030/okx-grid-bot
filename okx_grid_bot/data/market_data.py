"""
市场数据获取模块
获取多周期K线数据用于分析
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests

from okx_grid_bot.utils import config
from okx_grid_bot.utils.logger import logger, log_error


class MarketData:
    """
    市场数据获取器
    """

    def __init__(self):
        self.base_url = config.BASE_URL

    def get_klines(self, symbol: str = None, bar: str = '1D', limit: int = 100) -> Optional[List[Dict]]:
        """
        获取K线数据

        Args:
            symbol: 交易对，如 ETH-USDT
            bar: K线周期
                - 1m, 5m, 15m, 30m, 1H, 4H (分钟/小时)
                - 1D, 1W, 1M (日/周/月)
            limit: 获取数量，最大100

        Returns:
            K线数据列表，每条包含:
            - timestamp: 时间戳
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
        """
        symbol = symbol or config.SYMBOL
        endpoint = f"{self.base_url}/api/v5/market/candles"

        params = {
            'instId': symbol,
            'bar': bar,
            'limit': str(limit)
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            data = response.json()

            if data.get('code') != '0':
                log_error(f"获取K线失败: {data.get('msg')}")
                return None

            klines = []
            for item in data.get('data', []):
                klines.append({
                    'timestamp': int(item[0]),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5]),
                    'volume_ccy': float(item[6]) if len(item) > 6 else 0,
                    'datetime': datetime.fromtimestamp(int(item[0]) / 1000).strftime('%Y-%m-%d %H:%M')
                })

            # OKX返回的是倒序（最新在前），我们反转为正序（最旧在前）
            klines.reverse()
            return klines

        except Exception as e:
            log_error(f"获取K线异常: {e}")
            return None

    def get_multi_period_data(self, symbol: str = None) -> Dict[str, List[Dict]]:
        """
        获取多周期K线数据

        Returns:
            包含多个周期数据的字典
        """
        symbol = symbol or config.SYMBOL
        result = {}

        periods = {
            '1H': 168,    # 7天的小时数据
            '4H': 180,    # 30天的4小时数据
            '1D': 90,     # 90天日线
            '1W': 52,     # 1年周线
        }

        for bar, limit in periods.items():
            logger.info(f"获取 {bar} K线数据...")
            klines = self.get_klines(symbol, bar, min(limit, 100))
            if klines:
                result[bar] = klines
                logger.info(f"  获取到 {len(klines)} 条数据")
            time.sleep(0.2)  # 避免请求过快

        return result

    def get_price_stats(self, klines: List[Dict]) -> Dict:
        """
        计算价格统计信息

        Args:
            klines: K线数据列表

        Returns:
            统计信息字典
        """
        if not klines:
            return {}

        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]

        current_price = closes[-1]
        highest = max(highs)
        lowest = min(lows)
        avg_price = sum(closes) / len(closes)

        # 计算波动范围
        price_range = highest - lowest
        range_percent = (price_range / avg_price) * 100

        return {
            'current': current_price,
            'highest': highest,
            'lowest': lowest,
            'average': round(avg_price, 2),
            'range': round(price_range, 2),
            'range_percent': round(range_percent, 2),
            'data_points': len(klines),
            'start_date': klines[0]['datetime'],
            'end_date': klines[-1]['datetime']
        }

    def suggest_grid_params(self, symbol: str = None) -> Dict:
        """
        根据历史数据建议网格参数

        Returns:
            建议的网格参数
        """
        symbol = symbol or config.SYMBOL
        logger.info("正在分析历史数据，计算建议参数...")

        # 获取多周期数据
        data = self.get_multi_period_data(symbol)

        if not data:
            log_error("无法获取历史数据")
            return {}

        # 使用日线数据（90天）作为主要参考
        daily_data = data.get('1D', [])
        if not daily_data:
            log_error("无法获取日线数据")
            return {}

        stats = self.get_price_stats(daily_data)

        # 计算建议的网格上下限
        # 使用历史最高最低价，并留出一定缓冲
        buffer = 0.05  # 5%缓冲
        suggested_upper = stats['highest'] * (1 + buffer)
        suggested_lower = stats['lowest'] * (1 - buffer)

        # 计算建议的网格数量（根据波动范围）
        # 波动越大，网格越多
        if stats['range_percent'] < 10:
            suggested_grids = 5
        elif stats['range_percent'] < 20:
            suggested_grids = 10
        elif stats['range_percent'] < 30:
            suggested_grids = 15
        else:
            suggested_grids = 20

        # 计算每格间距
        grid_spacing = (suggested_upper - suggested_lower) / suggested_grids

        # 计算建议的每格金额（确保能覆盖所有网格）
        # 假设用户有 300 USDT，建议分配到所有网格
        suggested_amount = round(300 / suggested_grids, 0)

        result = {
            'analysis_period': f"{stats['start_date']} ~ {stats['end_date']}",
            'current_price': stats['current'],
            'period_high': stats['highest'],
            'period_low': stats['lowest'],
            'volatility_percent': stats['range_percent'],
            'suggested_upper': round(suggested_upper, 2),
            'suggested_lower': round(suggested_lower, 2),
            'suggested_grids': suggested_grids,
            'grid_spacing': round(grid_spacing, 2),
            'suggested_amount_per_grid': suggested_amount,
            'total_investment': suggested_amount * suggested_grids,
            'multi_period_stats': {}
        }

        # 添加多周期统计
        for period, klines in data.items():
            if klines:
                result['multi_period_stats'][period] = self.get_price_stats(klines)

        return result


# 创建全局实例
market_data = MarketData()


if __name__ == '__main__':
    # 测试代码
    print("测试市场数据获取...")

    # 获取建议参数
    params = market_data.suggest_grid_params()

    if params:
        print("\n" + "=" * 60)
        print("历史数据分析结果")
        print("=" * 60)
        print(f"分析周期: {params['analysis_period']}")
        print(f"当前价格: {params['current_price']}")
        print(f"周期最高: {params['period_high']}")
        print(f"周期最低: {params['period_low']}")
        print(f"波动幅度: {params['volatility_percent']}%")
        print("-" * 60)
        print("建议参数:")
        print(f"  价格上限: {params['suggested_upper']}")
        print(f"  价格下限: {params['suggested_lower']}")
        print(f"  网格数量: {params['suggested_grids']}")
        print(f"  网格间距: {params['grid_spacing']}")
        print(f"  每格金额: {params['suggested_amount_per_grid']} USDT")
        print(f"  总投入:   {params['total_investment']} USDT")
        print("=" * 60)
