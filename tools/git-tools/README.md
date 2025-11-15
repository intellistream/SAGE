# Git Submodule Tools

本目录包含用于管理 SAGE 项目中 Git 子模块的自动化工具。

## 🎯 目的

SAGE 项目使用多个 Git 子模块来组织代码。这些工具帮助：

1. **识别子模块** - 自动生成标记文件
1. **避免错误** - 检测并防止错误的子模块提交
1. **简化工作流** - 自动化常见的子模块操作

## 🤖 自动化集成

这些工具已集成到 SAGE 的自动化流程中，**通常不需要手动运行**：

### 首次安装时自动运行

运行 `./quickstart.sh --sync` 时会自动：

- 初始化所有子模块
- 生成 `SUBMODULE.md` 标记文件

### Git Hook 自动触发

开发模式下安装的 Git hooks 会自动：

- 在子模块更新后检查并生成缺失的标记文件
- 在提交前检测是否在子模块中误操作

要手动安装这些 hooks：

```bash
./tools/maintenance/setup_hooks.sh --all
```

## 📁 工具列表

### 1. `generate-submodule-markers.sh`

**作用**: 为所有子模块自动生成 `SUBMODULE.md` 标记文件

**自动调用**: ✅ 由 `quickstart.sh` 和 Git hooks 自动调用

**手动用法**:

```bash
# 正常模式（显示详细输出）
./tools/git-tools/generate-submodule-markers.sh

# 静默模式（用于脚本调用）
./tools/git-tools/generate-submodule-markers.sh --quiet
```

**功能**:

- 扫描 `.gitmodules` 中的所有子模块
- 为每个子模块生成详细的 `SUBMODULE.md` 文件
- 包含仓库信息、分支、提交指导等
- 自动计算相对路径

**输出**:

```
📝 处理子模块: sageData
   路径: packages/sage-benchmark/src/sage/data
   仓库: sageData
   分支: main-dev
   ✅ 创建: packages/sage-benchmark/src/sage/data/SUBMODULE.md
```

### 2. `commit-all-submodule-markers.sh`

**作用**: 批量提交所有子模块的 `SUBMODULE.md` 文件

**使用场景**: 首次设置或批量更新标记文件时手动运行

**用法**:

```bash
./tools/git-tools/commit-all-submodule-markers.sh
```

**功能**:

- 遍历所有子模块
- 检查是否有 `SUBMODULE.md` 更改
- 自动切换到正确的分支
- 提交并推送到远程
- 更新主仓库的子模块引用

**交互式**:

- 会询问是否继续（如果主仓库有未提交更改）
- 会询问是否提交主仓库的子模块引用更新

### 3. `check-submodule-commit.sh`

**作用**: 检查是否在子模块中提交，并给出正确指导

**用法**:

```bash
# 检查暂存的文件
./tools/git-tools/check-submodule-commit.sh

# 检查特定文件
./tools/git-tools/check-submodule-commit.sh path/to/file
```

**功能**:

- 检测文件是否在子模块中
- 如果是，显示警告和正确的提交步骤
- 退出代码 1 表示检测到子模块文件

**可以集成到 pre-commit hook**:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-submodule-commits
      name: Check submodule commits
      entry: tools/git-tools/check-submodule-commit.sh
      language: script
      pass_filenames: false
      always_run: true
```

## 🚀 快速开始

### 首次设置

1. **生成所有子模块标记文件**:

   ```bash
   ./tools/git-tools/generate-submodule-markers.sh
   ```

1. **提交这些标记文件**:

   ```bash
   ./tools/git-tools/commit-all-submodule-markers.sh
   ```

1. **（可选）添加 pre-commit hook**: 编辑 `.pre-commit-config.yaml` 添加子模块检查钩子

### 日常使用

**添加新子模块后**:

```bash
# 1. 添加子模块
git submodule add -b main-dev https://github.com/intellistream/NewRepo.git path/to/submodule

# 2. 生成标记文件
./tools/git-tools/generate-submodule-markers.sh

# 3. 提交标记文件
cd path/to/submodule
git add SUBMODULE.md
git commit -m "docs: add submodule marker"
git push origin main-dev

# 4. 更新主仓库引用
cd ../../..
git add path/to/submodule
git commit -m "chore: add NewRepo submodule with marker"
```

**更新子模块标记**:

```bash
# 如果更改了 .gitmodules（比如修改了 URL 或 branch）
./tools/git-tools/generate-submodule-markers.sh
./tools/git-tools/commit-all-submodule-markers.sh
```

## 📝 SUBMODULE.md 格式

生成的 `SUBMODULE.md` 文件包含:

- ⚠️ 明显的警告标识
- 📋 仓库信息（名称、URL、分支、路径）
- 📖 快速指南（两步提交流程）
- 🔄 更新指南
- ❌ 常见问题解决方案
- 📚 相关文档链接

## 🎯 为什么需要这些工具？

### 问题场景

1. **AI 助手无法识别子模块**

   - 文件系统中子模块目录看起来和普通目录一样
   - 导致 AI 使用错误的 git 命令

1. **开发者容易犯错**

   - 在主仓库尝试提交子模块文件
   - 忘记更新子模块引用
   - 子模块处于 detached HEAD 状态

1. **缺少文档**

   - 不清楚某个目录是子模块
   - 不知道如何正确提交更改

### 解决方案

✅ **SUBMODULE.md** 文件提供:

- 视觉标识（AI 和人都能看到）
- 清晰的操作指导
- 常见问题解决方案

✅ **自动化工具** 提供:

- 批量生成和更新标记
- 自动提交流程
- 错误检测和预防

## 🔧 维护

### 更新工具

如果修改了这些脚本，测试它们:

```bash
# 测试生成（不会创建文件，只显示会做什么）
# （在脚本中添加 --dry-run 选项）

# 在测试分支上测试
git checkout -b test-submodule-tools
./tools/git-tools/generate-submodule-markers.sh
# 检查生成的文件
git diff
```

### 子模块列表

当前 SAGE 项目的子模块:

1. `docs-public` - 公共文档
1. `packages/sage-common/src/sage/common/components/sage_vllm/sageLLM` - vLLM 组件
1. `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB` - 数据库组件
1. `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow` - 流处理组件
1. `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem` - 内存组件
1. `packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB` - 时序数据库
1. `packages/sage-benchmark/src/sage/data` - 数据集
1. `packages/sage-libs/src/sage/libs/libamm` - LibAMM 库

## 📚 相关文档

- [CONTRIBUTING.md](../../CONTRIBUTING.md) - 贡献指南（应该包含子模块工作流程）
- [.gitmodules](../../.gitmodules) - 子模块配置
- 各子模块的 `SUBMODULE.md` - 具体操作指南

## 🤝 贡献

如果你发现这些工具有问题或想要改进:

1. 创建 issue 描述问题
1. 提交 PR 修复或改进
1. 更新此 README 文档

______________________________________________________________________

💡 **提示**: 这些工具是为了让子模块管理更简单。如果遇到问题，先查看 `SUBMODULE.md` 文件！
