"""
事件系统模块

提供简单的事件发布/订阅机制，实现模块间解耦。

使用方法:
    from okx_grid_bot.utils.events import event_bus, Event

    # 订阅事件
    @event_bus.on('price_update')
    def handle_price(event):
        print(f"价格更新: {event.data['price']}")

    # 发布事件
    event_bus.emit('price_update', {'price': 3500.0})
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Any, Optional
from enum import Enum
import threading
from okx_grid_bot.utils.logger import logger


class EventType(str, Enum):
    """预定义的事件类型"""
    # 价格事件
    PRICE_UPDATE = "price_update"
    PRICE_ALERT = "price_alert"

    # 订单事件
    ORDER_CREATED = "order_created"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_FAILED = "order_failed"

    # 策略事件
    SIGNAL_GENERATED = "signal_generated"
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"

    # 风险事件
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    RISK_ALERT = "risk_alert"

    # 系统事件
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """
    事件对象

    携带事件类型和相关数据。
    """
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None  # 事件来源

    def __repr__(self) -> str:
        return f"<Event {self.type} at {self.timestamp.strftime('%H:%M:%S')}>"


# 事件处理函数类型
EventHandler = Callable[[Event], None]


class EventBus:
    """
    事件总线

    管理事件的发布和订阅。

    Example:
        bus = EventBus()

        # 方式1: 装饰器订阅
        @bus.on('price_update')
        def handle_price(event):
            print(event.data)

        # 方式2: 直接订阅
        bus.subscribe('order_filled', my_handler)

        # 发布事件
        bus.emit('price_update', {'price': 3500.0})
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.debug(f"订阅事件: {event_type} -> {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        取消订阅

        Args:
            event_type: 事件类型
            handler: 要移除的处理函数
        """
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type].remove(handler)
                logger.debug(f"取消订阅: {event_type} -> {handler.__name__}")

    def on(self, event_type: str) -> Callable:
        """
        装饰器方式订阅事件

        Example:
            @event_bus.on('price_update')
            def handle(event):
                ...
        """
        def decorator(handler: EventHandler) -> EventHandler:
            self.subscribe(event_type, handler)
            return handler
        return decorator

    def emit(self, event_type: str, data: Dict[str, Any] = None,
             source: str = None) -> None:
        """
        发布事件

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source
        )

        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"事件 {event_type} 无订阅者")
            return

        logger.debug(f"发布事件: {event} -> {len(handlers)} 个订阅者")

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"事件处理失败: {event_type} -> {handler.__name__}: {e}")
                # 发布错误事件（避免递归）
                if event_type != EventType.ERROR_OCCURRED:
                    self.emit(EventType.ERROR_OCCURRED, {
                        'original_event': event_type,
                        'handler': handler.__name__,
                        'error': str(e)
                    })

    def emit_async(self, event_type: str, data: Dict[str, Any] = None,
                   source: str = None) -> None:
        """
        异步发布事件（在新线程中处理）

        适用于不需要等待处理结果的场景。
        """
        thread = threading.Thread(
            target=self.emit,
            args=(event_type, data, source),
            daemon=True
        )
        thread.start()

    def clear(self, event_type: str = None) -> None:
        """
        清除订阅

        Args:
            event_type: 指定事件类型，None 则清除所有
        """
        with self._lock:
            if event_type:
                self._handlers.pop(event_type, None)
            else:
                self._handlers.clear()


# 全局事件总线实例
event_bus = EventBus()


# 便捷函数
def emit(event_type: str, data: Dict[str, Any] = None, source: str = None) -> None:
    """发布事件的便捷函数"""
    event_bus.emit(event_type, data, source)


def on(event_type: str) -> Callable:
    """订阅事件的装饰器"""
    return event_bus.on(event_type)
