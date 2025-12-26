"""
宏观环境分析模块
整合所有分析，给出综合市场评估
"""
from typing import Dict, Optional, List
from enum import Enum
from datetime import datetime

import sys
sys.path.append('..')
from data.market_data import market_data
from data.external_data import external_data
from analysis.trend import trend_analyzer, TrendType
from analysis.volatility import volatility_analyzer
from logger import logger


class MarketEnvironment(Enum):
    """市场环境评级"""
    EXCELLENT = "极佳"      # 震荡+低波动+情绪中性 -> 网格天堂
    GOOD = "良好"           # 适合网格
    NEUTRAL = "中性"        # 可以运行网格，但需注意风险
    CAUTION = "谨慎"        # 减仓或暂停
    DANGER = "危险"         # 强烈建议停止


class MacroAnalyzer:
    """
    宏观环境分析器
    综合技术面、情绪面、波动率等多维度分析
    """

    def __init__(self):
        pass

    def analyze_market(self, symbol: str = None) -> Dict:
        """
        进行全面的市场分析

        Args:
            symbol: 交易对

        Returns:
            综合分析结果
        """
        logger.info("=" * 50)
        logger.info("开始全面市场分析...")
        logger.info("=" * 50)

        result = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'environment': None,
            'environment_score': 50,
            'recommended_position': 50,
            'grid_params': {},
            'should_trade': True,
            'warnings': [],
            'analysis': {}
        }

        # 1. 获取K线数据
        logger.info("\n[1/4] 获取历史数据...")
        kline_data = market_data.get_multi_period_data(symbol)
        daily_klines = kline_data.get('1D', [])

        if not daily_klines or len(daily_klines) < 30:
            result['warnings'].append("历史数据不足，分析可能不准确")
            logger.warning("历史数据不足")

        # 2. 趋势分析
        logger.info("\n[2/4] 分析市场趋势...")
        if daily_klines:
            trend_result = trend_analyzer.get_comprehensive_trend(daily_klines)
            result['analysis']['trend'] = trend_result
            logger.info(f"  趋势判断: {trend_result['trend_name']}")
            logger.info(f"  置信度: {trend_result['confidence']}%")
        else:
            result['analysis']['trend'] = {'trend': TrendType.SIDEWAYS, 'confidence': 0}

        # 3. 波动率分析
        logger.info("\n[3/4] 分析波动率...")
        if daily_klines:
            volatility_result = volatility_analyzer.get_comprehensive_volatility(daily_klines)
            result['analysis']['volatility'] = volatility_result
            logger.info(f"  波动级别: {volatility_result.get('volatility_level', 'unknown')}")
            logger.info(f"  适合网格: {'是' if volatility_result.get('grid_suitable') else '否'}")
        else:
            result['analysis']['volatility'] = {'grid_suitable': True, 'volatility_score': 50}

        # 4. 市场情绪分析
        logger.info("\n[4/4] 分析市场情绪...")
        sentiment_result = external_data.get_all_sentiment_data()
        result['analysis']['sentiment'] = sentiment_result
        logger.info(f"  综合情绪: {sentiment_result.get('overall_sentiment', 'unknown')}")
        logger.info(f"  情绪分数: {sentiment_result.get('sentiment_score', 50)}")

        # 5. 综合评估
        logger.info("\n计算综合评估...")
        self._calculate_environment_score(result)

        # 6. 生成网格参数建议
        self._generate_grid_params(result, daily_klines)

        # 7. 生成警告信息
        self._generate_warnings(result)

        logger.info("\n" + "=" * 50)
        logger.info("市场分析完成")
        logger.info("=" * 50)

        return result

    def _calculate_environment_score(self, result: Dict):
        """
        计算环境评分和建议仓位
        """
        score = 50  # 基础分
        position = 50  # 基础仓位

        trend = result['analysis'].get('trend', {})
        volatility = result['analysis'].get('volatility', {})
        sentiment = result['analysis'].get('sentiment', {})

        # 趋势评分 (权重 30%)
        trend_type = trend.get('trend', TrendType.SIDEWAYS)
        if trend_type == TrendType.SIDEWAYS:
            score += 15  # 震荡市最适合网格
            position += 10
        elif trend_type == TrendType.UP:
            score += 5
            position += 5
        elif trend_type == TrendType.STRONG_UP:
            score -= 5  # 强趋势不太适合网格
            position -= 10
        elif trend_type == TrendType.DOWN:
            score -= 10
            position -= 15
        elif trend_type == TrendType.STRONG_DOWN:
            score -= 20
            position -= 30

        # 波动率评分 (权重 30%)
        vol_score = volatility.get('volatility_score', 50)
        if vol_score < 30:  # 低波动
            score += 10
            position += 5
        elif vol_score < 60:  # 适中波动
            score += 15
            position += 10
        elif vol_score < 80:  # 较高波动
            score -= 5
            position -= 10
        else:  # 极端波动
            score -= 20
            position -= 30

        # 检测波动突变
        if volatility.get('spike_detection', {}).get('spike_detected'):
            score -= 15
            position -= 20
            result['warnings'].append("检测到波动率异常突变")

        # 情绪评分 (权重 20%)
        sentiment_score = sentiment.get('sentiment_score', 50)
        if 40 <= sentiment_score <= 60:  # 中性情绪最佳
            score += 10
            position += 5
        elif sentiment_score < 25:  # 极度恐惧
            score -= 5
            position -= 10
            result['warnings'].append("市场极度恐惧，注意风险")
        elif sentiment_score > 75:  # 极度贪婪
            score -= 10
            position -= 15
            result['warnings'].append("市场极度贪婪，注意回调风险")

        # 资金费率检查 (权重 10%)
        funding = sentiment.get('funding_rate', {})
        if funding:
            rate = funding.get('funding_rate', 0)
            if abs(rate) > 0.001:  # 费率异常
                score -= 5
                position -= 10

        # 多空比检查 (权重 10%)
        ls_ratio = sentiment.get('long_short_ratio', {})
        if ls_ratio:
            ratio = ls_ratio.get('long_short_ratio', 1)
            if ratio > 2 or ratio < 0.5:  # 比例极端
                score -= 5
                position -= 10

        # 限制范围
        score = max(0, min(100, score))
        position = max(0, min(100, position))

        result['environment_score'] = round(score)
        result['recommended_position'] = round(position)

        # 确定环境等级
        if score >= 75:
            result['environment'] = MarketEnvironment.EXCELLENT
            result['should_trade'] = True
        elif score >= 60:
            result['environment'] = MarketEnvironment.GOOD
            result['should_trade'] = True
        elif score >= 45:
            result['environment'] = MarketEnvironment.NEUTRAL
            result['should_trade'] = True
        elif score >= 30:
            result['environment'] = MarketEnvironment.CAUTION
            result['should_trade'] = False  # 建议暂停
        else:
            result['environment'] = MarketEnvironment.DANGER
            result['should_trade'] = False

    def _generate_grid_params(self, result: Dict, klines: List[Dict]):
        """
        生成网格参数建议
        """
        if not klines:
            return

        volatility = result['analysis'].get('volatility', {})
        trend = result['analysis'].get('trend', {})

        current_price = klines[-1]['close'] if klines else 0

        # 获取波动率建议的间距
        suggested_spacing = volatility.get('suggested_spacing', {})
        suggested_grids = volatility.get('suggested_grids', {})

        # 获取价格范围
        price_range = volatility.get('range', {})

        # 基础参数
        if price_range:
            upper = price_range.get('highest', current_price * 1.1)
            lower = price_range.get('lowest', current_price * 0.9)
        else:
            upper = current_price * 1.1
            lower = current_price * 0.9

        # 根据趋势调整
        trend_type = trend.get('trend', TrendType.SIDEWAYS)
        if trend_type in [TrendType.UP, TrendType.STRONG_UP]:
            # 上涨趋势，上限可以适当提高
            upper = upper * 1.05
        elif trend_type in [TrendType.DOWN, TrendType.STRONG_DOWN]:
            # 下跌趋势，下限要更保守
            lower = lower * 0.95

        # 根据建议仓位调整每格金额
        base_amount = 20  # 基础每格金额
        position_ratio = result['recommended_position'] / 100
        adjusted_amount = base_amount * position_ratio

        grids = suggested_grids.get('min', 10) if suggested_grids else 10

        result['grid_params'] = {
            'upper_price': round(upper, 2),
            'lower_price': round(lower, 2),
            'grid_count': grids,
            'amount_per_grid': round(adjusted_amount, 2),
            'total_investment': round(adjusted_amount * grids, 2),
            'spacing': round((upper - lower) / grids, 2),
            'spacing_percent': round((upper - lower) / grids / current_price * 100, 2)
        }

    def _generate_warnings(self, result: Dict):
        """
        生成警告信息
        """
        trend = result['analysis'].get('trend', {})
        volatility = result['analysis'].get('volatility', {})

        # 强趋势警告
        trend_type = trend.get('trend', TrendType.SIDEWAYS)
        if trend_type in [TrendType.STRONG_UP, TrendType.STRONG_DOWN]:
            result['warnings'].append(f"当前处于{trend_type.value}，网格策略效果可能不佳")

        # 不适合网格警告
        if not volatility.get('grid_suitable', True):
            result['warnings'].append("当前波动率不适合网格交易")

        # RSI警告
        rsi = trend.get('details', {}).get('rsi', {})
        if rsi.get('signal') in ['strong_buy', 'strong_sell']:
            result['warnings'].append(f"RSI显示{rsi.get('status')}，可能出现反转")

    def print_analysis_report(self, result: Dict):
        """
        打印分析报告
        """
        print("\n" + "=" * 60)
        print("            智 能 量 化 系 统 - 市 场 分 析 报 告")
        print("=" * 60)
        print(f"分析时间: {result['timestamp']}")
        print(f"交易对: {result.get('symbol', 'ETH-USDT')}")
        print("-" * 60)

        # 环境评级
        env = result.get('environment', MarketEnvironment.NEUTRAL)
        score = result.get('environment_score', 50)
        print(f"\n【环境评级】{env.value} (评分: {score}/100)")
        print(f"【建议仓位】{result.get('recommended_position', 50)}%")
        print(f"【是否交易】{'✓ 可以交易' if result.get('should_trade') else '✗ 建议暂停'}")

        # 趋势分析
        trend = result['analysis'].get('trend', {})
        print(f"\n【趋势分析】")
        print(f"  趋势: {trend.get('trend_name', 'unknown')}")
        print(f"  置信度: {trend.get('confidence', 0)}%")
        if trend.get('grid_advice'):
            print(f"  建议: {trend.get('grid_advice')}")

        # 波动率
        vol = result['analysis'].get('volatility', {})
        print(f"\n【波动分析】")
        print(f"  波动级别: {vol.get('volatility_level', 'unknown')}")
        print(f"  ATR百分比: {vol.get('atr_percent', 'N/A')}%")
        print(f"  适合网格: {'是' if vol.get('grid_suitable') else '否'}")

        # 情绪分析
        sentiment = result['analysis'].get('sentiment', {})
        print(f"\n【情绪分析】")
        print(f"  综合情绪: {sentiment.get('overall_sentiment', 'unknown')}")
        print(f"  情绪分数: {sentiment.get('sentiment_score', 50)}")

        fg = sentiment.get('fear_greed', {})
        if fg:
            print(f"  恐惧贪婪: {fg.get('value', 'N/A')} ({fg.get('classification', 'N/A')})")

        # 网格参数建议
        params = result.get('grid_params', {})
        if params:
            print(f"\n【网格参数建议】")
            print(f"  价格上限: {params.get('upper_price')}")
            print(f"  价格下限: {params.get('lower_price')}")
            print(f"  网格数量: {params.get('grid_count')}")
            print(f"  网格间距: {params.get('spacing')} ({params.get('spacing_percent')}%)")
            print(f"  每格金额: {params.get('amount_per_grid')} USDT")
            print(f"  总投入: {params.get('total_investment')} USDT")

        # 警告
        warnings = result.get('warnings', [])
        if warnings:
            print(f"\n【⚠️ 警告】")
            for w in warnings:
                print(f"  • {w}")

        print("\n" + "=" * 60)


# 创建全局实例
macro_analyzer = MacroAnalyzer()


if __name__ == '__main__':
    print("测试宏观环境分析...")

    result = macro_analyzer.analyze_market()
    macro_analyzer.print_analysis_report(result)
