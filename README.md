# OKX Grid Trading Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OKX](https://img.shields.io/badge/Exchange-OKX-orange.svg)](https://www.okx.com/)

智能网格量化交易机器人，支持自动化网格交易、市场分析和风险控制。

> **风险提示**: 量化交易有风险，请使用可承受损失的资金，建议先在模拟盘测试。

## 功能特性

| 功能 | 描述 |
|------|------|
| **网格交易** | 在设定价格区间内自动低买高卖 |
| **智能分析** | 多维度分析趋势、波动率和市场情绪 |
| **风险控制** | 止损、最大回撤、日亏损限制等多重保护 |
| **事件驱动** | 模块解耦，易于扩展和维护 |
| **状态管理** | 完整的状态机，防止异常操作 |
| **日志脱敏** | 自动隐藏 API Key 等敏感信息 |

## 快速开始

### 前置要求

- Python 3.8+
- OKX 交易所账户及 API Key

### 安装

```bash
# 克隆项目
git clone https://github.com/October-1030/okx-grid-bot.git
cd okx-grid-bot

# 安装依赖
pip install -r requirements.txt

# 配置 API（复制并编辑 .env 文件）
cp .env.example .env
```

### 配置 API Key

编辑 `.env` 文件：

```ini
# OKX API 配置
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase

# 模拟盘模式（建议先用模拟盘测试）
USE_SIMULATED=true
```

### 运行

```bash
# 智能版（默认，带市场分析和风控）
python run.py

# 基础版（简单网格策略）
python run.py --basic

# 仅运行市场分析
python run.py --analyze

# 非交互模式（适合后台运行）
python run.py --yes
python run.py --non-interactive  # 遇到异常直接退出
```

## 配置参数

在 `okx_grid_bot/utils/config.py` 中配置：

| 参数 | 说明 | 默认值 | 建议范围 |
|------|------|--------|----------|
| `SYMBOL` | 交易对 | `ETH-USDT` | - |
| `GRID_UPPER_PRICE` | 网格上限 | `4000.0` | 根据市场调整 |
| `GRID_LOWER_PRICE` | 网格下限 | `3000.0` | 根据市场调整 |
| `GRID_COUNT` | 网格数量 | `10` | 5-50 |
| `AMOUNT_PER_GRID` | 每格金额 (USDT) | `20.0` | >= 5 |
| `STOP_LOSS_PRICE` | 止损价格 | `2800.0` | < 网格下限 |
| `MAX_POSITION_GRIDS` | 最大持仓格数 | `5` | 1-网格数量 |
| `CHECK_INTERVAL` | 检查间隔 (秒) | `5` | 3-60 |

## 项目架构

```
okx-grid-bot/
├── okx_grid_bot/              # 主代码包
│   ├── api/                   # 交易所 API
│   │   ├── okx_client.py      # OKX API 封装
│   │   └── exceptions.py      # 自定义异常
│   ├── strategy/              # 交易策略
│   │   ├── base.py            # 策略基类
│   │   ├── grid.py            # 网格策略
│   │   └── smart_grid.py      # 智能网格
│   ├── risk/                  # 风险控制
│   ├── analysis/              # 市场分析
│   ├── utils/                 # 工具模块
│   │   ├── config.py          # 配置
│   │   ├── logger.py          # 日志（含脱敏）
│   │   ├── events.py          # 事件系统
│   │   ├── state_machine.py   # 状态机
│   │   ├── retry.py           # 重试机制
│   │   └── validators.py      # 参数验证
│   ├── types.py               # 类型定义
│   └── bot.py                 # 机器人主程序
├── tests/                     # 单元测试
├── run.py                     # 启动入口
├── requirements.txt           # 依赖
├── CHANGELOG.md               # 更新日志
└── LICENSE                    # MIT 许可证
```

## 核心设计

### 策略模式

```python
from okx_grid_bot.strategy import BaseStrategy, Signal, SignalAction

class MyStrategy(BaseStrategy):
    """自定义策略只需继承 BaseStrategy"""

    def analyze(self, market_data) -> Signal:
        if should_buy:
            return Signal(action=SignalAction.BUY, price=price)
        return Signal(action=SignalAction.HOLD, price=price)
```

### 事件系统

```python
from okx_grid_bot.utils import event_bus, EventType

# 订阅事件
@event_bus.on(EventType.ORDER_FILLED)
def on_order(event):
    print(f"订单成交: {event.data}")

# 发布事件
event_bus.emit(EventType.PRICE_UPDATE, {'price': 3500.0})
```

### 状态机

```python
from okx_grid_bot.utils import BotStateMachine

sm = BotStateMachine()
sm.start()   # IDLE -> RUNNING
sm.pause()   # RUNNING -> PAUSED
sm.resume()  # PAUSED -> RUNNING
sm.stop()    # -> STOPPED
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码风格

```bash
# 检查代码风格
flake8 okx_grid_bot/

# 类型检查
mypy okx_grid_bot/
```

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新历史。

## 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 免责声明

1. 本项目仅供学习和研究使用
2. 请使用可承受损失的资金进行测试
3. 建议先在模拟盘验证策略有效性
4. 作者不对任何投资损失负责
5. 加密货币交易存在高风险，请谨慎投资
