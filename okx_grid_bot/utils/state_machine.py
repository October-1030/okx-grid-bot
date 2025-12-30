"""
状态机模块

管理机器人运行状态，确保状态转换的正确性。

使用方法:
    from okx_grid_bot.utils.state_machine import BotStateMachine, BotState

    sm = BotStateMachine()
    sm.start()  # IDLE -> STARTING -> RUNNING
    sm.pause()  # RUNNING -> PAUSED
    sm.stop()   # ANY -> STOPPING -> STOPPED
"""
from enum import Enum
from typing import Optional, Callable, Dict, List, Set
from dataclasses import dataclass, field
from datetime import datetime

from okx_grid_bot.utils.logger import logger
from okx_grid_bot.utils.events import event_bus, EventType


class BotState(str, Enum):
    """机器人状态"""
    IDLE = "idle"           # 空闲（未启动）
    STARTING = "starting"   # 启动中
    RUNNING = "running"     # 运行中
    PAUSED = "paused"       # 暂停
    ERROR = "error"         # 错误状态
    STOPPING = "stopping"   # 停止中
    STOPPED = "stopped"     # 已停止


# 状态转换规则
TRANSITIONS: Dict[BotState, Set[BotState]] = {
    BotState.IDLE: {BotState.STARTING},
    BotState.STARTING: {BotState.RUNNING, BotState.ERROR, BotState.STOPPING},
    BotState.RUNNING: {BotState.PAUSED, BotState.ERROR, BotState.STOPPING},
    BotState.PAUSED: {BotState.RUNNING, BotState.STOPPING},
    BotState.ERROR: {BotState.RUNNING, BotState.STOPPING},  # 可以重试或停止
    BotState.STOPPING: {BotState.STOPPED},
    BotState.STOPPED: {BotState.IDLE},  # 可以重新启动
}


@dataclass
class StateChange:
    """状态变更记录"""
    from_state: BotState
    to_state: BotState
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


class InvalidTransitionError(Exception):
    """无效的状态转换"""
    pass


class BotStateMachine:
    """
    机器人状态机

    管理机器人的生命周期状态。

    Example:
        sm = BotStateMachine()

        # 注册状态变更回调
        sm.on_state_change(lambda old, new, reason: print(f"{old} -> {new}"))

        sm.start()   # 启动
        sm.pause()   # 暂停
        sm.resume()  # 恢复
        sm.stop()    # 停止
    """

    def __init__(self):
        self._state = BotState.IDLE
        self._history: List[StateChange] = []
        self._callbacks: List[Callable[[BotState, BotState, str], None]] = []
        self._error_message: Optional[str] = None

    @property
    def state(self) -> BotState:
        """当前状态"""
        return self._state

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._state == BotState.RUNNING

    @property
    def is_active(self) -> bool:
        """是否处于活动状态（运行或暂停）"""
        return self._state in {BotState.RUNNING, BotState.PAUSED}

    @property
    def can_trade(self) -> bool:
        """是否可以交易"""
        return self._state == BotState.RUNNING

    @property
    def error_message(self) -> Optional[str]:
        """错误信息（如果处于错误状态）"""
        return self._error_message if self._state == BotState.ERROR else None

    def _transition(self, to_state: BotState, reason: str = "") -> None:
        """
        执行状态转换

        Args:
            to_state: 目标状态
            reason: 转换原因

        Raises:
            InvalidTransitionError: 不允许的状态转换
        """
        allowed = TRANSITIONS.get(self._state, set())

        if to_state not in allowed:
            raise InvalidTransitionError(
                f"不允许从 {self._state.value} 转换到 {to_state.value}。"
                f"允许的目标状态: {[s.value for s in allowed]}"
            )

        old_state = self._state
        self._state = to_state

        # 记录历史
        change = StateChange(old_state, to_state, reason)
        self._history.append(change)

        # 日志
        logger.info(f"状态变更: {old_state.value} -> {to_state.value} ({reason})")

        # 发布事件
        event_bus.emit('state_changed', {
            'from': old_state.value,
            'to': to_state.value,
            'reason': reason,
        })

        # 执行回调
        for callback in self._callbacks:
            try:
                callback(old_state, to_state, reason)
            except Exception as e:
                logger.error(f"状态变更回调错误: {e}")

    def on_state_change(self, callback: Callable[[BotState, BotState, str], None]) -> None:
        """
        注册状态变更回调

        Args:
            callback: 回调函数，参数为 (old_state, new_state, reason)
        """
        self._callbacks.append(callback)

    # ============== 状态操作方法 ==============

    def start(self) -> None:
        """启动机器人"""
        self._transition(BotState.STARTING, "用户启动")
        # 启动成功后转为运行状态
        self._transition(BotState.RUNNING, "初始化完成")

    def pause(self) -> None:
        """暂停交易"""
        self._transition(BotState.PAUSED, "用户暂停")

    def resume(self) -> None:
        """恢复交易"""
        if self._state == BotState.PAUSED:
            self._transition(BotState.RUNNING, "用户恢复")
        elif self._state == BotState.ERROR:
            self._error_message = None
            self._transition(BotState.RUNNING, "错误恢复")

    def stop(self) -> None:
        """停止机器人"""
        if self._state != BotState.STOPPED:
            self._transition(BotState.STOPPING, "用户停止")
            self._transition(BotState.STOPPED, "停止完成")

    def error(self, message: str) -> None:
        """
        进入错误状态

        Args:
            message: 错误信息
        """
        self._error_message = message
        self._transition(BotState.ERROR, message)

    def reset(self) -> None:
        """重置到初始状态"""
        if self._state == BotState.STOPPED:
            self._transition(BotState.IDLE, "重置")
            self._error_message = None

    # ============== 查询方法 ==============

    def get_history(self, limit: int = 10) -> List[StateChange]:
        """
        获取状态变更历史

        Args:
            limit: 返回的最大记录数

        Returns:
            状态变更记录列表
        """
        return self._history[-limit:]

    def get_status(self) -> dict:
        """获取状态摘要"""
        return {
            'state': self._state.value,
            'is_running': self.is_running,
            'is_active': self.is_active,
            'can_trade': self.can_trade,
            'error_message': self.error_message,
            'history_count': len(self._history),
        }
