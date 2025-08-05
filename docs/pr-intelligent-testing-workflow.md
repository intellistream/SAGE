# PR 智能测试 Workflow

## 概述

新的 `PR Intelligence Testing` workflow 已经添加到项目中，它使用 `scripts/test_runner.py --diff` 功能为 Pull Request 提供智能、高效的测试。

## 功能特性

### 🎯 智能测试选择
- **基于 git diff**: 自动分析 PR 中的变化文件
- **递归测试发现**: 查找变化文件的父目录中的测试
- **只运行相关测试**: 避免运行不相关的测试，节省时间

### ⚡ 并行执行
- **多进程运行**: 使用 2 个并行 worker 执行测试
- **实时进度**: 显示测试执行进度
- **结构化日志**: 每个测试目录生成独立的日志文件

### 📊 智能报告
- **PR 评论**: 自动在 PR 中发布测试结果评论
- **状态更新**: 评论会随着新的测试运行自动更新
- **详细摘要**: 显示测试数量、成功/失败状态等

## 触发条件

该 workflow 在以下情况下自动运行：

```yaml
on:
  pull_request:
    branches: [ main, develop, v*.*.* ]
    types: [opened, synchronize, reopened, ready_for_review]
```

- ✅ 新建 PR
- ✅ PR 有新的提交
- ✅ PR 重新打开
- ✅ 草稿 PR 标记为可审核
- ❌ 草稿 PR（自动跳过）

## 工作流程

1. **检出代码**: 获取 PR 代码和完整 git 历史
2. **环境设置**: 安装 Python 3.11 和依赖
3. **智能分析**: 使用 `test_runner.py --diff` 分析变化
4. **执行测试**: 并行运行相关测试
5. **收集结果**: 上传测试日志和生成报告
6. **更新 PR**: 在 PR 中发布/更新测试结果评论

## 测试输出示例

### 成功情况
```
## ✅ Intelligent Testing Results

**Status: PASSED**

### 📊 Test Summary
- **Changed files analyzed**: 3
- **Testing strategy**: Diff-based intelligent selection
- **Base comparison**: `main`
- **Parallel workers**: 2
- **Tool**: `scripts/test_runner.py --diff`

### 🎉 Ready for review!
All tests affected by your changes have passed successfully!
```

### 失败情况
```
## ❌ Intelligent Testing Results

**Status: FAILED**

### ⚠️ Needs attention
Some tests failed. Please check the workflow logs and fix the issues.
```

### 无变化情况
```
## ℹ️ Intelligent Testing Results

**Status: SKIPPED**

### ✅ Result
No tests needed to run - your PR appears to have no functional changes.
```

## 测试日志

- **工件保留**: 测试日志作为 GitHub Actions 工件保存 14 天
- **文件命名**: `intelligent-test-logs-{PR-number}`
- **结构化日志**: 每个测试目录一个 `.log` 文件

## 与现有 Workflow 的关系

这个新的 workflow 专门针对 PR 场景，与现有的测试 workflow 形成互补：

- `pr-intelligent-testing.yml`: PR 专用，使用 `test_runner.py --diff`
- `smart-testing.yml`: 通用智能测试，使用内置逻辑
- `ci.yml`: 完整 CI 流程（当前已注释）

## 配置说明

### 环境变量
workflow 继承了项目的标准环境变量：
- `HF_TOKEN`, `OPENAI_API_KEY` 等 API 密钥
- `CI=true` 标志 CI 环境
- `PYTHONPATH` 设置为工作区路径

### 超时设置
- **总超时**: 45 分钟
- **测试超时**: `test_runner.py` 内置 10 分钟单测试超时

### 依赖处理
- 优雅处理 `requirements.txt` 安装失败
- 容忍项目 `pip install -e .` 失败
- 确保核心测试工具（pytest, tqdm）始终可用

## 使用建议

1. **确保测试文件存在**: workflow 会检查 `scripts/test_runner.py` 存在
2. **合理组织测试**: 将测试文件放在源码附近的 `test/` 或 `tests/` 目录
3. **关注 PR 评论**: 测试结果会自动更新在 PR 评论中
4. **查看工件日志**: 失败时可下载测试日志进行详细分析

## 故障排除

### 常见问题

1. **test_runner.py 不存在**
   - 确保 `scripts/test_runner.py` 文件已提交
   - 检查文件路径和权限

2. **没有发现测试**
   - 确保变化的文件附近有 `test/` 或 `tests/` 目录
   - 检查测试文件命名符合 `test_*.py` 或 `*_test.py`

3. **依赖安装失败**
   - 检查 `requirements.txt` 格式
   - 某些依赖失败不会阻止测试运行

4. **超时问题**
   - 单个测试目录超时时间: 10 分钟
   - 整个 workflow 超时: 45 分钟
   - 考虑减少 `--workers` 数量或优化测试

### 调试建议

1. 查看 GitHub Actions 日志中的详细输出
2. 下载测试工件查看具体的测试日志
3. 本地运行 `python scripts/test_runner.py --diff --base origin/main` 重现问题
4. 使用 `python scripts/test_runner.py --list` 查看所有可用测试目录
