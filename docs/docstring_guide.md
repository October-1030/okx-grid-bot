# Python 文档字符串规范

本项目使用 **Google Style** 文档字符串格式。

## 模块文档

每个 `.py` 文件顶部应有模块文档：

```python
"""
模块简短描述

详细描述（可选）：
- 功能点1
- 功能点2

使用方法:
    from module import function
    result = function()

Author: October-1030
"""
```

## 类文档

```python
class MyClass:
    """
    类的简短描述

    详细描述...

    Attributes:
        attr1: 属性1描述
        attr2: 属性2描述

    Example:
        >>> obj = MyClass()
        >>> obj.method()
    """

    def __init__(self, param1: str):
        """
        初始化方法

        Args:
            param1: 参数描述
        """
        self.attr1 = param1
```

## 函数/方法文档

```python
def calculate_profit(
    buy_price: float,
    sell_price: float,
    amount: float,
    fee_rate: float = 0.001
) -> float:
    """
    计算交易利润

    根据买入价、卖出价和数量计算净利润，扣除手续费。

    Args:
        buy_price: 买入价格
        sell_price: 卖出价格
        amount: 交易数量
        fee_rate: 手续费率，默认 0.1%

    Returns:
        净利润（已扣除手续费）

    Raises:
        ValueError: 价格或数量为负数时

    Example:
        >>> calculate_profit(100, 110, 1.0)
        9.78  # 10 - 0.22 (手续费)

    Note:
        手续费按买卖双边计算
    """
    if buy_price <= 0 or sell_price <= 0 or amount <= 0:
        raise ValueError("价格和数量必须为正数")

    gross_profit = (sell_price - buy_price) * amount
    fee = (buy_price + sell_price) * amount * fee_rate
    return gross_profit - fee
```

## 常用标签

| 标签 | 用途 |
|------|------|
| `Args:` | 参数描述 |
| `Returns:` | 返回值描述 |
| `Raises:` | 可能抛出的异常 |
| `Example:` | 使用示例 |
| `Note:` | 补充说明 |
| `Warning:` | 警告信息 |
| `Todo:` | 待完成事项 |
| `Deprecated:` | 废弃说明 |

## 类型注解

结合类型注解使用，文档更清晰：

```python
from typing import Optional, List, Dict

def process_orders(
    orders: List[Dict[str, float]],
    filter_symbol: Optional[str] = None
) -> List[Dict[str, float]]:
    """
    处理订单列表

    Args:
        orders: 订单列表，每个订单包含 price, amount 等字段
        filter_symbol: 可选，筛选指定交易对

    Returns:
        处理后的订单列表
    """
```

## 私有方法

私有方法（`_method`）也需要文档，但可以简化：

```python
def _calculate_grid_spacing(self) -> float:
    """计算网格间距"""
    return (self.upper - self.lower) / self.count
```

## 生成文档

使用 `pdoc` 自动生成 HTML 文档：

```bash
pip install pdoc
pdoc okx_grid_bot -o docs/api
```
