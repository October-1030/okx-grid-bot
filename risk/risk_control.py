"""
风险控制模块
实现各种风控保护机制
"""
from typing import Dict, Optional, List
from enum import Enum
from datetime import datetime, timedelta
import json
import os

import sys
sys.path.append('..')
import config
from logger import logger, log_warning, log_error


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"


class RiskAction(Enum):
    """风控动作"""
    CONTINUE = "继续交易"
    REDUCE_POSITION = "减少仓位"
    PAUSE_BUY = "暂停买入"
    PAUSE_ALL = "暂停所有交易"
    CLOSE_ALL = "清仓止损"


class RiskController:
    """
    风险控制器
    """

    def __init__(self):
        # 风控参数
        self.max_drawdown_percent = 10.0      # 最大回撤百分比
        self.daily_loss_limit = 50.0          # 日亏损上限 (USDT)
        self.max_position_value = 500.0       # 最大持仓价值
        self.price_drop_alert = 5.0           # 价格下跌警报阈值 (%)
        self.price_spike_alert = 10.0         # 价格剧烈波动阈值 (%)
        self.consecutive_loss_limit = 3       # 连续亏损次数限制

        # 状态追踪
        self.initial_value = 0.0              # 初始资产价值
        self.peak_value = 0.0                 # 峰值资产价值
        self.daily_pnl = 0.0                  # 日内盈亏
        self.consecutive_losses = 0           # 连续亏损次数
        self.last_price = 0.0                 # 上次价格
        self.trading_paused = False           # 是否暂停交易
        self.pause_reason = ""                # 暂停原因

        # 价格历史（用于检测异常波动）
        self.price_history: List[Dict] = []
        self.max_price_history = 100

        # 加载状态
        self._load_state()

    def _load_state(self):
        """加载风控状态"""
        state_file = "risk_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.initial_value = state.get('initial_value', 0)
                    self.peak_value = state.get('peak_value', 0)
                    self.daily_pnl = state.get('daily_pnl', 0)
                    self.consecutive_losses = state.get('consecutive_losses', 0)
                    self.trading_paused = state.get('trading_paused', False)
                    self.pause_reason = state.get('pause_reason', "")

                    # 检查是否是新的一天，重置日内盈亏
                    last_date = state.get('last_date', '')
                    if last_date != datetime.now().strftime('%Y-%m-%d'):
                        self.daily_pnl = 0
            except Exception as e:
                log_error(f"加载风控状态失败: {e}")

    def _save_state(self):
        """保存风控状态"""
        state = {
            'initial_value': self.initial_value,
            'peak_value': self.peak_value,
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'trading_paused': self.trading_paused,
            'pause_reason': self.pause_reason,
            'last_date': datetime.now().strftime('%Y-%m-%d')
        }
        try:
            with open("risk_state.json", 'w') as f:
                json.dump(state, f)
        except Exception as e:
            log_error(f"保存风控状态失败: {e}")

    def initialize(self, initial_value: float):
        """
        初始化风控系统

        Args:
            initial_value: 初始资产价值
        """
        self.initial_value = initial_value
        self.peak_value = initial_value
        self.daily_pnl = 0
        self.consecutive_losses = 0
        self.trading_paused = False
        self.pause_reason = ""
        self._save_state()
        logger.info(f"风控系统初始化，初始价值: {initial_value} USDT")

    def update_value(self, current_value: float):
        """
        更新当前资产价值

        Args:
            current_value: 当前资产价值
        """
        # 更新峰值
        if current_value > self.peak_value:
            self.peak_value = current_value

        self._save_state()

    def record_trade(self, pnl: float):
        """
        记录交易盈亏

        Args:
            pnl: 本次交易盈亏
        """
        self.daily_pnl += pnl

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self._save_state()
        logger.info(f"记录交易盈亏: {pnl:.2f} USDT, 日内累计: {self.daily_pnl:.2f} USDT")

    def record_price(self, price: float, timestamp: datetime = None):
        """
        记录价格

        Args:
            price: 当前价格
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.price_history.append({
            'price': price,
            'timestamp': timestamp.isoformat()
        })

        # 保持历史记录在限制范围内
        if len(self.price_history) > self.max_price_history:
            self.price_history = self.price_history[-self.max_price_history:]

        self.last_price = price

    def check_drawdown(self, current_value: float) -> Dict:
        """
        检查回撤

        Args:
            current_value: 当前资产价值

        Returns:
            回撤检查结果
        """
        if self.peak_value <= 0:
            return {'exceeded': False, 'drawdown_percent': 0}

        drawdown = self.peak_value - current_value
        drawdown_percent = (drawdown / self.peak_value) * 100

        exceeded = drawdown_percent > self.max_drawdown_percent

        if exceeded:
            log_warning(f"回撤警告! 当前回撤: {drawdown_percent:.2f}% > 上限 {self.max_drawdown_percent}%")

        return {
            'exceeded': exceeded,
            'drawdown': round(drawdown, 2),
            'drawdown_percent': round(drawdown_percent, 2),
            'limit': self.max_drawdown_percent
        }

    def check_daily_loss(self) -> Dict:
        """
        检查日亏损

        Returns:
            日亏损检查结果
        """
        exceeded = self.daily_pnl < -self.daily_loss_limit

        if exceeded:
            log_warning(f"日亏损警告! 今日亏损: {abs(self.daily_pnl):.2f} > 上限 {self.daily_loss_limit}")

        return {
            'exceeded': exceeded,
            'daily_pnl': round(self.daily_pnl, 2),
            'limit': self.daily_loss_limit
        }

    def check_consecutive_losses(self) -> Dict:
        """
        检查连续亏损

        Returns:
            连续亏损检查结果
        """
        exceeded = self.consecutive_losses >= self.consecutive_loss_limit

        if exceeded:
            log_warning(f"连续亏损警告! 连续亏损次数: {self.consecutive_losses}")

        return {
            'exceeded': exceeded,
            'count': self.consecutive_losses,
            'limit': self.consecutive_loss_limit
        }

    def check_price_anomaly(self, current_price: float) -> Dict:
        """
        检查价格异常波动

        Args:
            current_price: 当前价格

        Returns:
            价格异常检查结果
        """
        result = {
            'anomaly_detected': False,
            'type': None,
            'change_percent': 0
        }

        if not self.price_history:
            return result

        # 检查与上一次价格的变化
        if self.last_price > 0:
            change_percent = ((current_price - self.last_price) / self.last_price) * 100

            if abs(change_percent) > self.price_spike_alert:
                result['anomaly_detected'] = True
                result['type'] = 'spike'
                result['change_percent'] = round(change_percent, 2)
                log_warning(f"价格异常波动! 变化: {change_percent:.2f}%")

        # 检查最近5分钟的变化（如果有足够数据）
        if len(self.price_history) >= 5:
            old_price = self.price_history[-5]['price']
            change_percent = ((current_price - old_price) / old_price) * 100

            if change_percent < -self.price_drop_alert:
                result['anomaly_detected'] = True
                result['type'] = 'rapid_drop'
                result['change_percent'] = round(change_percent, 2)
                log_warning(f"价格快速下跌! 5周期变化: {change_percent:.2f}%")

        return result

    def check_position_limit(self, position_value: float) -> Dict:
        """
        检查持仓限制

        Args:
            position_value: 当前持仓价值

        Returns:
            持仓限制检查结果
        """
        exceeded = position_value > self.max_position_value

        if exceeded:
            log_warning(f"持仓超限! 当前持仓: {position_value:.2f} > 上限 {self.max_position_value}")

        return {
            'exceeded': exceeded,
            'position_value': round(position_value, 2),
            'limit': self.max_position_value
        }

    def get_risk_assessment(self, current_value: float, current_price: float,
                           position_value: float) -> Dict:
        """
        综合风险评估

        Args:
            current_value: 当前资产价值
            current_price: 当前价格
            position_value: 持仓价值

        Returns:
            风险评估结果
        """
        # 执行各项检查
        drawdown_check = self.check_drawdown(current_value)
        daily_loss_check = self.check_daily_loss()
        consecutive_check = self.check_consecutive_losses()
        price_check = self.check_price_anomaly(current_price)
        position_check = self.check_position_limit(position_value)

        # 记录价格
        self.record_price(current_price)

        # 计算风险等级
        risk_score = 0

        if drawdown_check['exceeded']:
            risk_score += 30
        elif drawdown_check['drawdown_percent'] > self.max_drawdown_percent * 0.7:
            risk_score += 15

        if daily_loss_check['exceeded']:
            risk_score += 25
        elif self.daily_pnl < -self.daily_loss_limit * 0.7:
            risk_score += 10

        if consecutive_check['exceeded']:
            risk_score += 20

        if price_check['anomaly_detected']:
            risk_score += 25

        if position_check['exceeded']:
            risk_score += 15

        # 确定风险等级和建议动作
        if risk_score >= 60:
            risk_level = RiskLevel.CRITICAL
            action = RiskAction.PAUSE_ALL
        elif risk_score >= 40:
            risk_level = RiskLevel.HIGH
            action = RiskAction.PAUSE_BUY
        elif risk_score >= 20:
            risk_level = RiskLevel.MEDIUM
            action = RiskAction.REDUCE_POSITION
        else:
            risk_level = RiskLevel.LOW
            action = RiskAction.CONTINUE

        result = {
            'risk_level': risk_level.value,
            'risk_score': risk_score,
            'action': action.value,
            'should_trade': risk_score < 40,
            'checks': {
                'drawdown': drawdown_check,
                'daily_loss': daily_loss_check,
                'consecutive_losses': consecutive_check,
                'price_anomaly': price_check,
                'position_limit': position_check
            }
        }

        # 如果需要暂停
        if risk_score >= 40:
            self.trading_paused = True
            reasons = []
            if drawdown_check['exceeded']:
                reasons.append(f"回撤超限({drawdown_check['drawdown_percent']}%)")
            if daily_loss_check['exceeded']:
                reasons.append(f"日亏损超限({abs(daily_loss_check['daily_pnl'])} USDT)")
            if consecutive_check['exceeded']:
                reasons.append(f"连续亏损{consecutive_check['count']}次")
            if price_check['anomaly_detected']:
                reasons.append(f"价格异常波动({price_check['change_percent']}%)")

            self.pause_reason = "; ".join(reasons)
            result['pause_reason'] = self.pause_reason
            self._save_state()

        return result

    def resume_trading(self):
        """
        恢复交易
        """
        self.trading_paused = False
        self.pause_reason = ""
        self.consecutive_losses = 0
        self._save_state()
        logger.info("风控解除，恢复交易")

    def reset_daily(self):
        """
        重置日内数据（每日开始时调用）
        """
        self.daily_pnl = 0
        self._save_state()
        logger.info("日内数据已重置")

    def get_status(self) -> Dict:
        """
        获取风控状态

        Returns:
            风控状态字典
        """
        return {
            'trading_paused': self.trading_paused,
            'pause_reason': self.pause_reason,
            'initial_value': self.initial_value,
            'peak_value': self.peak_value,
            'daily_pnl': round(self.daily_pnl, 2),
            'consecutive_losses': self.consecutive_losses,
            'last_price': self.last_price
        }


# 创建全局实例
risk_controller = RiskController()


if __name__ == '__main__':
    print("风控模块测试...")

    # 初始化
    risk_controller.initialize(1000)

    # 模拟几次交易
    risk_controller.record_trade(-20)  # 亏损
    risk_controller.record_trade(-15)  # 亏损
    risk_controller.record_trade(10)   # 盈利

    # 模拟价格
    risk_controller.record_price(3500)
    risk_controller.record_price(3480)
    risk_controller.record_price(3300)  # 突然下跌

    # 进行风险评估
    assessment = risk_controller.get_risk_assessment(
        current_value=950,
        current_price=3300,
        position_value=200
    )

    print("\n" + "=" * 50)
    print("风险评估结果")
    print("=" * 50)
    print(f"风险等级: {assessment['risk_level']}")
    print(f"风险分数: {assessment['risk_score']}")
    print(f"建议动作: {assessment['action']}")
    print(f"是否可交易: {'是' if assessment['should_trade'] else '否'}")

    if not assessment['should_trade']:
        print(f"暂停原因: {assessment.get('pause_reason', 'N/A')}")

    print("\n详细检查:")
    for check_name, check_result in assessment['checks'].items():
        status = "⚠️ 异常" if check_result.get('exceeded') or check_result.get('anomaly_detected') else "✓ 正常"
        print(f"  {check_name}: {status}")

    print("=" * 50)
