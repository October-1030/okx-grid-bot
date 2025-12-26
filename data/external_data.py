"""
外部数据接入模块
获取恐惧贪婪指数、美元指数、宏观经济数据等
"""
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import time

import sys
sys.path.append('..')
from logger import logger, log_error, log_warning


class ExternalData:
    """
    外部数据获取器
    """

    def __init__(self):
        # 缓存数据，避免频繁请求
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = 300  # 缓存5分钟

    def _get_cached(self, key: str) -> Optional[Dict]:
        """获取缓存数据"""
        if key in self._cache:
            if time.time() - self._cache_time.get(key, 0) < self._cache_duration:
                return self._cache[key]
        return None

    def _set_cache(self, key: str, data: Dict):
        """设置缓存"""
        self._cache[key] = data
        self._cache_time[key] = time.time()

    def get_fear_greed_index(self) -> Optional[Dict]:
        """
        获取加密货币恐惧贪婪指数
        数据来源: alternative.me

        Returns:
            {
                'value': 指数值 (0-100),
                'classification': 分类 (Extreme Fear, Fear, Neutral, Greed, Extreme Greed),
                'timestamp': 时间戳,
                'interpretation': 解读
            }
        """
        cached = self._get_cached('fear_greed')
        if cached:
            return cached

        try:
            url = "https://api.alternative.me/fng/?limit=1"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('data'):
                item = data['data'][0]
                value = int(item['value'])

                # 添加解读
                if value <= 20:
                    interpretation = "极度恐惧 - 可能是买入机会"
                elif value <= 40:
                    interpretation = "恐惧 - 市场情绪偏空"
                elif value <= 60:
                    interpretation = "中性 - 观望为主"
                elif value <= 80:
                    interpretation = "贪婪 - 注意风险"
                else:
                    interpretation = "极度贪婪 - 高风险区域"

                result = {
                    'value': value,
                    'classification': item['value_classification'],
                    'timestamp': item['timestamp'],
                    'interpretation': interpretation
                }
                self._set_cache('fear_greed', result)
                return result

        except Exception as e:
            log_error(f"获取恐惧贪婪指数失败: {e}")

        return None

    def get_btc_dominance(self) -> Optional[float]:
        """
        获取比特币市值占比
        BTC.D 上升通常意味着资金流向BTC，山寨币可能走弱

        Returns:
            BTC市值占比 (0-100)
        """
        cached = self._get_cached('btc_dominance')
        if cached:
            return cached.get('value')

        try:
            url = "https://api.coingecko.com/api/v3/global"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('data'):
                dominance = data['data']['market_cap_percentage']['btc']
                result = {'value': round(dominance, 2)}
                self._set_cache('btc_dominance', result)
                return result['value']

        except Exception as e:
            log_error(f"获取BTC市值占比失败: {e}")

        return None

    def get_total_market_cap(self) -> Optional[Dict]:
        """
        获取加密货币总市值

        Returns:
            {
                'total_market_cap': 总市值(USD),
                'total_volume': 24h交易量,
                'market_cap_change_24h': 24h变化百分比
            }
        """
        cached = self._get_cached('market_cap')
        if cached:
            return cached

        try:
            url = "https://api.coingecko.com/api/v3/global"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('data'):
                result = {
                    'total_market_cap': data['data']['total_market_cap']['usd'],
                    'total_volume': data['data']['total_volume']['usd'],
                    'market_cap_change_24h': data['data']['market_cap_change_percentage_24h_usd']
                }
                self._set_cache('market_cap', result)
                return result

        except Exception as e:
            log_error(f"获取市值数据失败: {e}")

        return None

    def get_funding_rate(self, symbol: str = "ETH-USDT-SWAP") -> Optional[Dict]:
        """
        获取资金费率（来自OKX永续合约）
        正费率：多头付费给空头，市场偏多
        负费率：空头付费给多头，市场偏空

        Args:
            symbol: 合约交易对

        Returns:
            {
                'funding_rate': 当前资金费率,
                'next_funding_time': 下次结算时间,
                'interpretation': 解读
            }
        """
        cached = self._get_cached(f'funding_{symbol}')
        if cached:
            return cached

        try:
            url = f"https://www.okx.com/api/v5/public/funding-rate?instId={symbol}"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('code') == '0' and data.get('data'):
                item = data['data'][0]
                rate = float(item['fundingRate'])

                # 解读
                if rate > 0.001:
                    interpretation = "费率偏高 - 多头拥挤，可能回调"
                elif rate > 0:
                    interpretation = "费率正常偏多"
                elif rate > -0.001:
                    interpretation = "费率正常偏空"
                else:
                    interpretation = "费率负值较大 - 空头拥挤，可能反弹"

                result = {
                    'funding_rate': rate,
                    'funding_rate_percent': round(rate * 100, 4),
                    'next_funding_time': item['nextFundingTime'],
                    'interpretation': interpretation
                }
                self._set_cache(f'funding_{symbol}', result)
                return result

        except Exception as e:
            log_error(f"获取资金费率失败: {e}")

        return None

    def get_long_short_ratio(self, symbol: str = "ETH") -> Optional[Dict]:
        """
        获取多空持仓人数比（来自OKX）

        Returns:
            {
                'long_short_ratio': 多空比,
                'interpretation': 解读
            }
        """
        cached = self._get_cached(f'ls_ratio_{symbol}')
        if cached:
            return cached

        try:
            url = f"https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy={symbol}&period=1H"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('code') == '0' and data.get('data'):
                # 获取最新数据
                latest = data['data'][0]
                ratio = float(latest[1])

                if ratio > 2:
                    interpretation = "多头极度拥挤 - 高风险"
                elif ratio > 1.5:
                    interpretation = "多头占优"
                elif ratio > 1:
                    interpretation = "略偏多头"
                elif ratio > 0.67:
                    interpretation = "略偏空头"
                elif ratio > 0.5:
                    interpretation = "空头占优"
                else:
                    interpretation = "空头极度拥挤 - 可能反弹"

                result = {
                    'long_short_ratio': ratio,
                    'timestamp': latest[0],
                    'interpretation': interpretation
                }
                self._set_cache(f'ls_ratio_{symbol}', result)
                return result

        except Exception as e:
            log_error(f"获取多空比失败: {e}")

        return None

    def get_all_sentiment_data(self) -> Dict:
        """
        获取所有市场情绪数据

        Returns:
            综合情绪数据字典
        """
        logger.info("正在获取市场情绪数据...")

        result = {
            'timestamp': datetime.now().isoformat(),
            'fear_greed': None,
            'btc_dominance': None,
            'market_cap': None,
            'funding_rate': None,
            'long_short_ratio': None,
            'overall_sentiment': None,
            'sentiment_score': 50  # 默认中性
        }

        # 获取各项数据
        fear_greed = self.get_fear_greed_index()
        if fear_greed:
            result['fear_greed'] = fear_greed
            logger.info(f"  恐惧贪婪指数: {fear_greed['value']} ({fear_greed['classification']})")

        btc_dom = self.get_btc_dominance()
        if btc_dom:
            result['btc_dominance'] = btc_dom
            logger.info(f"  BTC市值占比: {btc_dom}%")

        market_cap = self.get_total_market_cap()
        if market_cap:
            result['market_cap'] = market_cap
            change = market_cap['market_cap_change_24h']
            logger.info(f"  市值24h变化: {change:.2f}%")

        funding = self.get_funding_rate()
        if funding:
            result['funding_rate'] = funding
            logger.info(f"  资金费率: {funding['funding_rate_percent']}%")

        ls_ratio = self.get_long_short_ratio()
        if ls_ratio:
            result['long_short_ratio'] = ls_ratio
            logger.info(f"  多空比: {ls_ratio['long_short_ratio']:.2f}")

        # 计算综合情绪分数 (0-100)
        scores = []

        if fear_greed:
            scores.append(fear_greed['value'])

        if funding:
            # 资金费率转换为情绪分数
            rate = funding['funding_rate']
            if rate > 0.001:
                scores.append(70)  # 偏贪婪
            elif rate > 0:
                scores.append(55)
            elif rate > -0.001:
                scores.append(45)
            else:
                scores.append(30)  # 偏恐惧

        if ls_ratio:
            ratio = ls_ratio['long_short_ratio']
            # 多空比转换为情绪分数
            ratio_score = min(100, max(0, (ratio - 0.5) / 1.5 * 50 + 50))
            scores.append(ratio_score)

        if market_cap:
            change = market_cap['market_cap_change_24h']
            # 市值变化转换为情绪分数
            change_score = min(100, max(0, change * 5 + 50))
            scores.append(change_score)

        if scores:
            result['sentiment_score'] = round(sum(scores) / len(scores), 1)

            if result['sentiment_score'] <= 25:
                result['overall_sentiment'] = "极度恐惧"
            elif result['sentiment_score'] <= 40:
                result['overall_sentiment'] = "恐惧"
            elif result['sentiment_score'] <= 60:
                result['overall_sentiment'] = "中性"
            elif result['sentiment_score'] <= 75:
                result['overall_sentiment'] = "贪婪"
            else:
                result['overall_sentiment'] = "极度贪婪"

            logger.info(f"  综合情绪: {result['overall_sentiment']} (分数: {result['sentiment_score']})")

        return result


# 创建全局实例
external_data = ExternalData()


if __name__ == '__main__':
    print("测试外部数据获取...\n")

    # 获取所有情绪数据
    data = external_data.get_all_sentiment_data()

    print("\n" + "=" * 50)
    print("市场情绪综合报告")
    print("=" * 50)

    if data['fear_greed']:
        fg = data['fear_greed']
        print(f"恐惧贪婪指数: {fg['value']} - {fg['classification']}")
        print(f"  解读: {fg['interpretation']}")

    if data['btc_dominance']:
        print(f"\nBTC市值占比: {data['btc_dominance']}%")

    if data['funding_rate']:
        fr = data['funding_rate']
        print(f"\n资金费率: {fr['funding_rate_percent']}%")
        print(f"  解读: {fr['interpretation']}")

    if data['long_short_ratio']:
        ls = data['long_short_ratio']
        print(f"\n多空持仓比: {ls['long_short_ratio']:.2f}")
        print(f"  解读: {ls['interpretation']}")

    print("\n" + "-" * 50)
    print(f"综合情绪评分: {data['sentiment_score']}")
    print(f"情绪判断: {data['overall_sentiment']}")
    print("=" * 50)
