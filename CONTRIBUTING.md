# 贡献指南

感谢你有兴趣为本项目做出贡献！

## 如何贡献

### 报告 Bug

1. 确认 Bug 尚未被报告（搜索现有 Issues）
2. 创建新 Issue，包含以下信息：
   - 清晰的标题和描述
   - 复现步骤
   - 期望行为 vs 实际行为
   - Python 版本和操作系统
   - 相关日志（注意脱敏敏感信息）

### 功能建议

1. 创建 Issue 描述你的想法
2. 说明使用场景和预期效果
3. 等待讨论确认后再开始开发

### 提交代码

1. **Fork** 本仓库

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **编写代码**
   - 遵循现有代码风格
   - 添加必要的文档字符串
   - 添加单元测试

4. **运行测试**
   ```bash
   pytest tests/
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加 XXX 功能"
   ```

6. **推送并创建 PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 代码规范

### Python 风格

- 遵循 PEP 8
- 使用类型注解
- 使用 Google Style 文档字符串

### 提交信息

使用约定式提交 (Conventional Commits)：

```
<type>(<scope>): <description>

[optional body]
```

类型：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响逻辑）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：
```
feat(strategy): 添加均线交叉策略
fix(api): 修复超时重试逻辑
docs(readme): 更新安装说明
```

### 分支命名

- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 重构

## 开发环境

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 代码检查
flake8 okx_grid_bot/
mypy okx_grid_bot/

# 运行测试
pytest tests/ -v
```

## 问题？

如有任何问题，请创建 Issue 或联系维护者。
