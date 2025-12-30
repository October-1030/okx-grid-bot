"""
输入验证模块

提供参数验证功能，确保交易参数合法。

使用方法:
    from okx_grid_bot.utils.validators import validate_grid_params, ValidationError

    try:
        validate_grid_params(upper_price=3000, lower_price=4000, ...)  # 会抛出异常
    except ValidationError as e:
        print(f"参数错误: {e}")
"""
from typing import Optional
from okx_grid_bot.types import Price, Amount


class ValidationError(ValueError):
    """
    验证错误

    当参数不合法时抛出此异常。
    """
    pass


def validate_positive(value: float, name: str) -> None:
    """
    验证值为正数

    Args:
        value: 要验证的值
        name: 参数名称（用于错误信息）

    Raises:
        ValidationError: 值不是正数
    """
    if value <= 0:
        raise ValidationError(f"{name} 必须大于 0，当前值: {value}")


def validate_range(value: float, min_val: float, max_val: float, name: str) -> None:
    """
    验证值在指定范围内

    Args:
        value: 要验证的值
        min_val: 最小值
        max_val: 最大值
        name: 参数名称

    Raises:
        ValidationError: 值不在范围内
    """
    if not (min_val <= value <= max_val):
        raise ValidationError(
            f"{name} 必须在 {min_val} - {max_val} 之间，当前值: {value}"
        )


def validate_grid_params(
    upper_price: Price,
    lower_price: Price,
    grid_count: int,
    amount_per_grid: Amount,
    stop_loss_price: Optional[Price] = None,
) -> None:
    """
    验证网格交易参数

    Args:
        upper_price: 网格上限价格
        lower_price: 网格下限价格
        grid_count: 网格数量
        amount_per_grid: 每格投资金额
        stop_loss_price: 止损价格（可选）

    Raises:
        ValidationError: 参数不合法

    Example:
        validate_grid_params(
            upper_price=4000,
            lower_price=3000,
            grid_count=10,
            amount_per_grid=100
        )
    """
    # 价格验证
    validate_positive(upper_price, "上限价格 (upper_price)")
    validate_positive(lower_price, "下限价格 (lower_price)")

    if upper_price <= lower_price:
        raise ValidationError(
            f"上限价格 ({upper_price}) 必须大于下限价格 ({lower_price})"
        )

    # 网格数量验证
    if not isinstance(grid_count, int):
        raise ValidationError(f"网格数量必须是整数，当前类型: {type(grid_count).__name__}")

    if grid_count < 2:
        raise ValidationError(f"网格数量至少为 2，当前值: {grid_count}")

    if grid_count > 100:
        raise ValidationError(f"网格数量不能超过 100，当前值: {grid_count}")

    # 每格金额验证
    validate_positive(amount_per_grid, "每格金额 (amount_per_grid)")

    if amount_per_grid < 5:  # OKX 最小下单金额通常是 5 USDT
        raise ValidationError(
            f"每格金额至少为 5 USDT（交易所最小限制），当前值: {amount_per_grid}"
        )

    # 止损价格验证
    if stop_loss_price is not None:
        validate_positive(stop_loss_price, "止损价格 (stop_loss_price)")
        if stop_loss_price >= lower_price:
            raise ValidationError(
                f"止损价格 ({stop_loss_price}) 必须低于下限价格 ({lower_price})"
            )

    # 计算并警告网格间距
    grid_spacing = (upper_price - lower_price) / grid_count
    spacing_percent = (grid_spacing / lower_price) * 100

    if spacing_percent < 0.5:
        raise ValidationError(
            f"网格间距过小 ({spacing_percent:.2f}%)，手续费可能吃掉利润。"
            f"建议减少网格数量或扩大价格区间。"
        )


def validate_order_params(
    side: str,
    amount: Amount,
    price: Optional[Price] = None,
    order_type: str = "market",
) -> None:
    """
    验证下单参数

    Args:
        side: 订单方向 ('buy' 或 'sell')
        amount: 交易数量
        price: 价格（限价单需要）
        order_type: 订单类型 ('market' 或 'limit')

    Raises:
        ValidationError: 参数不合法
    """
    # 方向验证
    if side not in ('buy', 'sell'):
        raise ValidationError(f"订单方向必须是 'buy' 或 'sell'，当前值: {side}")

    # 数量验证
    validate_positive(amount, "交易数量 (amount)")

    # 订单类型验证
    if order_type not in ('market', 'limit'):
        raise ValidationError(
            f"订单类型必须是 'market' 或 'limit'，当前值: {order_type}"
        )

    # 限价单必须有价格
    if order_type == 'limit':
        if price is None:
            raise ValidationError("限价单必须指定价格")
        validate_positive(price, "价格 (price)")


def validate_symbol(symbol: str) -> None:
    """
    验证交易对格式

    Args:
        symbol: 交易对，如 'ETH-USDT'

    Raises:
        ValidationError: 格式不正确
    """
    if not symbol:
        raise ValidationError("交易对不能为空")

    if '-' not in symbol:
        raise ValidationError(
            f"交易对格式错误，应为 'XXX-YYY' 格式，如 'ETH-USDT'，当前值: {symbol}"
        )

    parts = symbol.split('-')
    if len(parts) != 2:
        raise ValidationError(
            f"交易对格式错误，应为 'XXX-YYY' 格式，当前值: {symbol}"
        )

    base, quote = parts
    if not base or not quote:
        raise ValidationError(f"交易对格式错误: {symbol}")
