"""
类型定义模块

集中定义项目中使用的类型，包括：
- TypedDict: 字典的类型提示
- Enum: 枚举类型
- 类型别名
"""
from typing import TypedDict, Optional, List, Literal
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


# ==================== 枚举类型 ====================

class OrderSide(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"


class TrendType(str, Enum):
    """趋势类型"""
    STRONG_UP = "strong_up"
    UP = "up"
    SIDEWAYS = "sideways"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== TypedDict (字典类型) ====================

class TickerData(TypedDict):
    """行情数据"""
    instId: str        # 交易对
    last: str          # 最新价
    askPx: str         # 卖一价
    bidPx: str         # 买一价
    vol24h: str        # 24小时成交量


class OrderResult(TypedDict):
    """下单结果"""
    ordId: str         # 订单ID
    clOrdId: str       # 客户订单ID
    sCode: str         # 状态码
    sMsg: str          # 状态信息


class TradeResult(TypedDict):
    """交易结果"""
    action: Optional[Literal["buy", "sell", "hold"]]
    success: bool
    message: str
    order_id: Optional[str]
    price: Optional[float]
    amount: Optional[float]


class RiskAssessment(TypedDict):
    """风险评估结果"""
    risk_level: str
    risk_score: int
    should_trade: bool
    action: str
    reasons: List[str]


class GridParams(TypedDict):
    """网格参数"""
    upper_price: float
    lower_price: float
    grid_count: int
    amount_per_grid: float
    total_investment: float


# ==================== 数据类 ====================

@dataclass
class GridLevel:
    """
    网格层级

    Attributes:
        index: 网格索引（0 = 最低价）
        price: 该格的触发价格
        is_bought: 是否已在该格买入
        buy_price: 实际买入价格
        buy_amount: 买入的币数量
        buy_time: 买入时间
        order_id: 订单ID
    """
    index: int
    price: float
    is_bought: bool = False
    buy_price: float = 0.0
    buy_amount: float = 0.0
    buy_time: Optional[datetime] = None
    order_id: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "index": self.index,
            "price": self.price,
            "is_bought": self.is_bought,
            "buy_price": self.buy_price,
            "buy_amount": self.buy_amount,
            "buy_time": self.buy_time.isoformat() if self.buy_time else None,
            "order_id": self.order_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GridLevel":
        """从字典创建实例"""
        buy_time = None
        if data.get("buy_time"):
            buy_time = datetime.fromisoformat(data["buy_time"])

        return cls(
            index=data["index"],
            price=data["price"],
            is_bought=data.get("is_bought", False),
            buy_price=data.get("buy_price", 0.0),
            buy_amount=data.get("buy_amount", 0.0),
            buy_time=buy_time,
            order_id=data.get("order_id"),
        )


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    side: OrderSide
    size: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def pnl_percent(self) -> float:
        """盈亏百分比"""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100


# ==================== 类型别名 ====================

# 价格类型（始终用 float）
Price = float

# 数量类型
Amount = float

# 百分比（0-100）
Percent = float

# 时间戳（毫秒）
Timestamp = int
