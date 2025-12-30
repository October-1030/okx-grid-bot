"""
P1-1: 告警通知模块

支持 Webhook 方式发送告警通知
"""
import requests
import json
from typing import Dict, Optional
from enum import Enum

from okx_grid_bot.utils import config
from okx_grid_bot.utils.logger import logger, log_error, log_warning


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Notifier:
    """
    通知器 - 发送告警通知
    """

    def __init__(self):
        self.enabled = config.ENABLE_NOTIFICATION
        self.notification_type = config.NOTIFICATION_TYPE
        self.webhook_url = config.WEBHOOK_URL

    def send_alert(self, title: str, message: str, level: AlertLevel = AlertLevel.INFO,
                   extra_data: Optional[Dict] = None) -> bool:
        """
        发送告警通知

        Args:
            title: 告警标题
            message: 告警消息
            level: 告警级别
            extra_data: 额外数据

        Returns:
            是否发送成功
        """
        if not self.enabled:
            logger.debug(f"通知未启用，跳过: {title}")
            return False

        if self.notification_type == "webhook":
            return self._send_webhook(title, message, level, extra_data)
        else:
            log_warning(f"不支持的通知类型: {self.notification_type}")
            return False

    def _send_webhook(self, title: str, message: str, level: AlertLevel,
                      extra_data: Optional[Dict] = None) -> bool:
        """
        通过 Webhook 发送通知
        """
        if not self.webhook_url:
            log_warning("Webhook URL 未配置")
            return False

        # 构建通知数据
        payload = {
            "title": title,
            "message": message,
            "level": level.value,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

        if extra_data:
            payload["data"] = extra_data

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )

            if response.status_code == 200:
                logger.info(f"通知发送成功: {title}")
                return True
            else:
                log_error(f"通知发送失败: HTTP {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            log_error("通知发送超时")
            return False
        except requests.exceptions.RequestException as e:
            log_error(f"通知发送失败: {e}")
            return False

    def alert_stop_loss(self, price: float, consecutive_count: int):
        """止损告警"""
        self.send_alert(
            title="🛑 止损触发",
            message=f"价格跌破止损线: {price}，连续止损 {consecutive_count} 次",
            level=AlertLevel.ERROR,
            extra_data={"price": price, "consecutive_count": consecutive_count}
        )

    def alert_circuit_breaker(self, reason: str):
        """熔断告警"""
        self.send_alert(
            title="⚠️ 熔断暂停",
            message=f"触发熔断保护: {reason}",
            level=AlertLevel.CRITICAL,
            extra_data={"reason": reason}
        )

    def alert_risk_control(self, risk_level: str, action: str, details: Dict):
        """风控告警"""
        self.send_alert(
            title=f"⚠️ 风控警告 - {risk_level}",
            message=f"建议动作: {action}",
            level=AlertLevel.WARNING,
            extra_data=details
        )

    def alert_trade(self, action: str, price: float, amount: float, profit: float = None):
        """交易告警"""
        msg = f"{action} {amount:.6f} @ {price:.2f}"
        if profit is not None:
            msg += f"，盈亏: {profit:.4f} USDT"

        self.send_alert(
            title=f"💰 {action}成交",
            message=msg,
            level=AlertLevel.INFO,
            extra_data={"action": action, "price": price, "amount": amount, "profit": profit}
        )

    def alert_error(self, error_type: str, error_message: str):
        """错误告警"""
        self.send_alert(
            title=f"❌ 系统错误 - {error_type}",
            message=error_message,
            level=AlertLevel.ERROR,
            extra_data={"error_type": error_type, "error_message": error_message}
        )


# 创建全局实例
notifier = Notifier()


if __name__ == '__main__':
    # 测试通知
    print("测试通知功能...")

    if notifier.enabled:
        notifier.alert_trade("买入", 3500.0, 0.01)
        notifier.alert_stop_loss(3200.0, 1)
        notifier.alert_circuit_breaker("连续3次止损")
        print("测试通知已发送")
    else:
        print("通知功能未启用，请在 config.py 中配置 ENABLE_NOTIFICATION=True 和 WEBHOOK_URL")
