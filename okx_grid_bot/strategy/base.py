"""
策略基类模块

定义所有交易策略必须实现的接口。
这是策略模式的核心 - 所有策略继承此基类。

使用方法:
    class MyStrategy(BaseStrategy):
        def analyze(self, price, ...) -> Signal:
            # 你的策略逻辑
            return Signal(action='buy', ...)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class SignalAction(str, Enum):
    """交易信号动作"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"      # 持有，不操作
    STOP_LOSS = "stop_loss"  # 止损


@dataclass
class Signal:
    """
    交易信号

    策略分析后返回的结果，告诉机器人该做什么。
    """
    action: SignalAction
    price: float
    amount: Optional[float] = None
    reason: str = ""
    confidence: float = 1.0  # 信心度 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def should_execute(self, min_confidence: float = 0.5) -> bool:
        """是否应该执行此信号"""
        return (
            self.action != SignalAction.HOLD and
            self.confidence >= min_confidence
        )


@dataclass
class MarketData:
    """
    市场数据

    传递给策略的标准化市场信息。
    """
    symbol: str
    current_price: float
    bid_price: float  # 买一价
    ask_price: float  # 卖一价
    volume_24h: float
    timestamp: datetime = field(default_factory=datetime.now)

    # 可选的历史数据
    price_history: List[float] = field(default_factory=list)
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None


class BaseStrategy(ABC):
    """
    策略基类

    所有交易策略必须继承此类并实现 analyze 方法。

    Example:
        class GridStrategy(BaseStrategy):
            name = "网格策略"

            def analyze(self, market_data: MarketData) -> Signal:
                if market_data.current_price < self.lower_bound:
                    return Signal(action=SignalAction.BUY, ...)
                return Signal(action=SignalAction.HOLD, ...)
    """

    # 子类应该覆盖这些属性
    name: str = "BaseStrategy"
    version: str = "1.0.0"
    description: str = "策略基类"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化策略

        Args:
            config: 策略配置参数
        """
        self.config = config or {}
        self._is_initialized = False
        self.setup()
        self._is_initialized = True

    def setup(self) -> None:
        """
        策略初始化

        子类可以覆盖此方法进行初始化设置。
        在 __init__ 中自动调用。
        """
        pass

    @abstractmethod
    def analyze(self, market_data: MarketData) -> Signal:
        """
        分析市场数据并生成交易信号

        这是策略的核心方法，必须实现。

        Args:
            market_data: 市场数据

        Returns:
            Signal: 交易信号
        """
        pass

    def on_order_filled(self, order_id: str, price: float, amount: float) -> None:
        """
        订单成交回调

        当订单成交时调用，子类可以覆盖以更新内部状态。

        Args:
            order_id: 订单ID
            price: 成交价格
            amount: 成交数量
        """
        pass

    def on_order_cancelled(self, order_id: str) -> None:
        """
        订单取消回调

        Args:
            order_id: 订单ID
        """
        pass

    def reset(self) -> None:
        """
        重置策略状态

        用于回测或重新开始时。
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        获取策略状态

        Returns:
            策略当前状态信息
        """
        return {
            "name": self.name,
            "version": self.version,
            "is_initialized": self._is_initialized,
        }

    def __repr__(self) -> str:
        return f"<{self.name} v{self.version}>"
