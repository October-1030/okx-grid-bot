# Changelog

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- WebSocket 实时行情支持
- 多交易对同时运行
- Web 管理界面

---

## [2.0.0] - 2024-12-26

### 新增
- **策略模式**: 添加 `BaseStrategy` 基类，策略可插拔
- **事件系统**: 添加 `EventBus` 实现模块解耦
- **状态机**: 添加 `BotStateMachine` 管理机器人生命周期
- **重试机制**: 添加 `@retry` 装饰器，网络错误自动重试
- **参数验证**: 添加 `validators.py`，启动时验证配置
- **日志脱敏**: 自动隐藏 API Key 等敏感信息
- **类型定义**: 添加 `types.py` 集中管理类型

### 变更
- 重构项目结构为标准 Python 包格式
- `GridStrategy` 现在继承 `BaseStrategy`
- 机器人主循环使用 `MarketData` 和 `Signal` 对象
- 改进 README 文档结构

### 修复
- 修复网格状态保存时 datetime 序列化问题

### 安全
- API Key 等敏感信息不再出现在日志中

---

## [1.0.0] - 2024-12-01

### 新增
- 基础网格交易功能
- OKX API 封装
- 智能网格策略（带市场分析）
- 风险控制模块
- 仓位管理

---

## 版本说明

- **主版本号**: 不兼容的 API 修改
- **次版本号**: 向下兼容的功能新增
- **修订号**: 向下兼容的问题修复

### 变更类型

- `Added` - 新功能
- `Changed` - 现有功能的变更
- `Deprecated` - 即将废弃的功能
- `Removed` - 已移除的功能
- `Fixed` - Bug 修复
- `Security` - 安全相关
