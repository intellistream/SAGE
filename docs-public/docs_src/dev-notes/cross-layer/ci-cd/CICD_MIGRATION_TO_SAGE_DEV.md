# CI/CD Migration to sage-dev Commands

**Date**: 2025-10-26\
**Author**: GitHub Copilot\
**Summary**: 将 CI/CD 工作流从独立 Python 脚本迁移到统一的 `sage-dev` CLI 命令

______________________________________________________________________

## 📋 概述

本文档记录了将 CI/CD 工作流从使用独立 Python 脚本迁移到使用统一的 `sage-dev` CLI 命令的过程。

## 🎯 迁移目标

1. **统一命令接口** - 所有质量检查使用统一的 `sage-dev` 命令
1. **简化维护** - 集中管理检查工具，避免重复代码
1. **改善用户体验** - 提供一致的命令行体验和错误提示
1. **增强功能** - 添加架构信息查询等新功能

## 📊 迁移对比

### 更新前

CI/CD 工作流使用独立的 Python 脚本：

```yaml
# 架构检查
- run: python tools/architecture_checker.py --changed-only

# 文档检查
- run: python tools/devnotes_checker.py --changed-only

# README 检查
- run: python tools/package_readme_checker.py
```

### 更新后

统一使用 `sage-dev` 命令：

```yaml
# 架构检查
- run: sage-dev check-architecture --changed-only

# 文档检查
- run: sage-dev check-devnotes --changed-only

# README 检查
- run: sage-dev check-readme

# 综合检查
- run: sage-dev check-all --changed-only
```

## 🔧 修改的文件

### 1. CI/CD 工作流

#### `.github/workflows/code-quality.yml`

```yaml
# 架构检查步骤 (Lines 160-175)
- name: Architecture Compliance Check
  if: github.event_name == 'pull_request'
  run: |
    echo "🏗️  运行架构合规性检查..."
    sage-dev check-architecture --changed-only || {
      echo "💡 请查看 SAGE 架构规范文档："
      echo "   docs/PACKAGE_ARCHITECTURE.md"
      echo "💡 或运行以下命令获取详细信息："
      echo "   sage-dev check-architecture --verbose"
      exit 1
    }

# 文档检查步骤 (Lines 191-210)
- name: Documentation Standards Check
  if: github.event_name == 'pull_request'
  continue-on-error: true
  run: |
    echo "📚 运行 dev-notes 文档规范检查..."
    sage-dev check-devnotes --changed-only || {
      echo "⚠️  文档规范检查发现问题"
      echo "💡 请确保文档包含必需的元数据"
      echo "💡 查看文档模板："
      echo "   docs/dev-notes/TEMPLATE.md"
    }
```

#### `.github/workflows/deployment-check.yml`

```yaml
# Dev-notes 检查 (Lines 66-90)
- name: Dev-notes Documentation Check
  run: |
    if [ "${{ github.event_name }}" = "pull_request" ]; then
      sage-dev check-devnotes --changed-only || {
        echo "❌ Dev-notes 文档不符合规范！"
        exit 1
      }
    fi

# 架构检查 (Lines 96-135)
- name: Architecture Compliance Check
  run: |
    if [ "${{ github.event_name }}" = "pull_request" ]; then
      sage-dev check-architecture --changed-only || {
        echo "❌ 架构合规性检查失败！"
        echo "3. 查看架构信息: sage-dev architecture"
        exit 1
      }
    fi

# README 检查 (Lines 168-188)
- name: Package README Check
  run: |
    if sage-dev check-readme; then
      echo "✅ 所有包的 README 文档完整"
    else
      echo "4. 查看详细报告: sage-dev check-readme --report"
      exit 1
    fi
```

### 2. 核心功能改进

#### 添加了 `sage-dev architecture` 命令

新增命令用于查看和查询 SAGE 架构信息：

```bash
# 查看完整架构
sage-dev architecture

# 查看特定包信息
sage-dev architecture --package sage-kernel

# JSON 格式输出
sage-dev architecture --format json

# Markdown 格式输出
sage-dev architecture --format markdown
```

**功能特性**：

- 显示 L1-L6 分层架构定义
- 显示每个包的依赖关系（按层级顺序）
- 支持查询特定包的信息
- 支持多种输出格式（text/json/markdown）

#### 修正架构依赖定义

修正了 `sage-kernel` 和 `sage-libs` 的依赖关系：

**修改前**：

```python
"sage-kernel": {"sage-common", "sage-platform", "sage-libs"},  # ❌ 错误
"sage-libs": {"sage-common", "sage-platform"},
```

**修改后**：

```python
"sage-kernel": {"sage-common", "sage-platform"},  # ✅ 正确
"sage-libs": {"sage-common", "sage-platform"},    # ✅ 正确
```

**原因**：`sage-kernel` 和 `sage-libs` 都是 L3 层的独立模块，相互不应依赖。

### 3. 测试和文档

#### 测试覆盖

新增测试类 `TestArchitectureCommand`，包含 6 个测试用例：

- ✅ 帮助信息显示
- ✅ 基本架构显示
- ✅ 特定包查询
- ✅ 无效包错误处理
- ✅ JSON 格式输出
- ✅ 依赖关系选项

#### 文档更新

1. **packages/sage-tools/README.md**

   - 添加 `architecture` 命令使用示例
   - 更新架构检查命令说明

1. **docs-public/docs_src/dev-notes/package-architecture.md**

   - 添加 "🛠️ 架构相关命令" 部分
   - 包含命令示例和使用说明

1. **工具脚本**

   - 创建 `tools/tests/test_ci_commands.sh` - CI 命令测试脚本

## ✅ 验证结果

### 所有测试通过

```bash
# 单元测试
✅ 28/28 质量检查测试通过

# 架构检查
✅ 检查 552 个 Python 文件，0 违规

# 综合检查
✅ sage-dev check-all --changed-only 全部通过
```

### CI/CD 兼容性

所有修改后的命令都已在本地验证：

- ✅ `sage-dev check-architecture --changed-only`
- ✅ `sage-dev check-devnotes --changed-only`
- ✅ `sage-dev check-readme`
- ✅ `sage-dev check-all`
- ✅ `sage-dev architecture`

## 📦 依赖安装

CI/CD 工作流中确保安装了 `sage-tools`：

```yaml
- name: Install Dependencies
  run: |
    pip install --upgrade pip
    pip install -e packages/sage-tools
```

## 🎯 最佳实践

### 本地开发

```bash
# 提交前运行所有检查
sage-dev check-all

# 仅检查变更文件（更快）
sage-dev check-all --changed-only

# 查看架构定义
sage-dev architecture

# 查看特定包的架构信息
sage-dev architecture --package sage-kernel
```

### CI/CD 集成

```yaml
# PR 检查 - 仅检查变更文件
- name: Quality Checks
  if: github.event_name == 'pull_request'
  run: sage-dev check-all --changed-only

# Push 检查 - 允许失败但记录
- name: Quality Checks
  if: github.event_name != 'pull_request'
  continue-on-error: true
  run: sage-dev check-all
```

## 🔄 向后兼容性

**旧脚本保留**：

- `tools/architecture_checker.py` - ❌ 已移除（集成到 sage-tools）
- `tools/devnotes_checker.py` - ❌ 已移除（集成到 sage-tools）
- `tools/package_readme_checker.py` - ❌ 已移除（集成到 sage-tools）

**新位置**：

- `packages/sage-tools/src/sage/tools/dev/tools/architecture_checker.py`
- `packages/sage-tools/src/sage/tools/dev/tools/devnotes_checker.py`
- `packages/sage-tools/src/sage/tools/dev/tools/package_readme_checker.py`

**CLI 入口**：

- `packages/sage-tools/src/sage/tools/cli/commands/dev/main.py`

## 📝 其他改进

### 错误提示优化

更新后的 CI/CD 工作流提供更友好的错误提示：

```bash
# 架构检查失败时
❌ 架构合规性检查失败！
💡 常见问题修复：
1. 检查跨层级导入（如 app 导入 kernel）
2. 确保导入路径符合包架构
3. 查看架构信息: sage-dev architecture
4. 查看文档: docs-public/docs_src/dev-notes/package-architecture.md
```

### 架构显示顺序修正

修正了 `sage-dev architecture` 命令的显示顺序：

**修改前**：按字母顺序显示（sage-apps, sage-benchmark, sage-common, ...）\
**修改后**：按层级顺序显示（L1 → L6）

## 🚀 未来计划

1. **继续集成其他工具**

   - 考虑集成 `tools/maintenance/` 下的 shell 脚本
   - 提供 Python API 用于程序化调用

1. **增强功能**

   - 添加架构可视化（生成依赖图）
   - 提供交互式修复建议
   - 集成更多代码质量检查

1. **性能优化**

   - 缓存检查结果
   - 并行化检查流程
   - 增量检查优化

## 📚 参考文档

- [SAGE 架构文档](../package-architecture.md)
- [sage-tools README](../../../../packages/sage-tools/README.md)
- [开发者指南](../../../../DEVELOPER.md)
- [贡献指南](../../../../CONTRIBUTING.md)

______________________________________________________________________

**变更历史**：

- 2025-10-26: 初始版本 - CI/CD 迁移到 sage-dev 命令
- 2025-10-26: 修正 sage-kernel 架构依赖定义
- 2025-10-26: 添加 architecture 命令显示架构信息
