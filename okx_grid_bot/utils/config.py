"""
OKX 智能网格交易机器人配置文件
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ============== OKX API 配置 ==============
# 请在 .env 文件中设置以下变量，或直接在这里填写（不推荐）
API_KEY = os.getenv("OKX_API_KEY", "")
SECRET_KEY = os.getenv("OKX_SECRET_KEY", "")
PASSPHRASE = os.getenv("OKX_PASSPHRASE", "")

# API 基础URL
BASE_URL = "https://www.okx.com"

# 是否使用模拟盘（True = 模拟盘，False = 实盘）
USE_SIMULATED = False

# 仅分析模式（True = 只分析不下单，False = 正常交易）
# 安全开关：启用后所有下单操作都会被阻止
ANALYZE_ONLY = os.getenv("ANALYZE_ONLY", "0") == "1"

# ============== 交易配置 ==============
# 交易对
SYMBOL = "ETH-USDT"

# 交易模式: cash = 现货
TRADE_MODE = "cash"

# ============== 网格参数 ==============
# 价格上限（当价格高于此值时不再买入）
# 注意：智能模式下会根据市场分析自动调整
GRID_UPPER_PRICE = 3200.0

# 价格下限（当价格低于此值时触发止损）
GRID_LOWER_PRICE = 2900.0

# 网格数量（在上下限之间分多少格）
GRID_COUNT = 10

# 每格投入的 USDT 金额（建议不超过总资金的2%）
AMOUNT_PER_GRID = 3.9

# ============== 风控配置 ==============
# 止损价格（价格跌破此值时停止交易并卖出）
STOP_LOSS_PRICE = 2800.0

# P0-2: 止损行为配置
# "pause"     = 仅暂停交易，保留持仓（适合短期波动）
# "liquidate" = 自动清仓止损，卖出所有持仓（适合趋势反转）
STOP_LOSS_ACTION = "pause"

# P2-1: 手续费率（根据你的VIP等级调整）
TRADING_FEE_RATE = 0.001  # 0.1% 手续费率

# P2-2: 最小利润率（需覆盖双边手续费）
MIN_PROFIT_RATE = 0.003  # 0.3% 最小利润率

# 最大持仓数量（最多持有多少格的仓位）
MAX_POSITION_GRIDS = 10

# 最大回撤百分比（超过此值暂停交易）
MAX_DRAWDOWN_PERCENT = 20.0  # 临时提高，避免误触发

# 日亏损上限（USDT）
DAILY_LOSS_LIMIT = 50.0

# 连续亏损次数限制
CONSECUTIVE_LOSS_LIMIT = 5

# ============== 智能分析配置 ==============
# 是否启用智能模式（自动分析市场调整参数）
SMART_MODE = True

# 市场分析间隔（秒）
ANALYSIS_INTERVAL = 3600  # 1小时

# 环境评分阈值（低于此值暂停交易）
MIN_ENVIRONMENT_SCORE = 30

# 是否根据分析自动调整网格参数
AUTO_ADJUST_PARAMS = True

# ============== 仓位管理配置 ==============
# 总资本（用于计算仓位比例）
TOTAL_CAPITAL = 500.0

# 最大仓位比例
MAX_POSITION_RATIO = 0.8

# 最小仓位比例
MIN_POSITION_RATIO = 0.1

# ============== 运行配置 ==============
# 价格检查间隔（秒）
CHECK_INTERVAL = 5

# 日志文件路径
LOG_FILE = "grid_bot.log"

# 订单记录文件
ORDERS_FILE = "orders.json"

# 风控状态文件
RISK_STATE_FILE = "risk_state.json"

# ============== 通知配置（可选）==============
# 是否启用通知
ENABLE_NOTIFICATION = False

# 通知方式: telegram, email, webhook
NOTIFICATION_TYPE = "webhook"

# Webhook URL（用于接收通知）
WEBHOOK_URL = ""
