# 🚀 SAGE 开发工具快捷命令

本文档介绍 SAGE 项目提供的便捷开发命令，帮助开发者提高工作效率。

## 📋 目录

- [快速开始](#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
- [使用方式](#%E4%BD%BF%E7%94%A8%E6%96%B9%E5%BC%8F)
- [命令参考](#%E5%91%BD%E4%BB%A4%E5%8F%82%E8%80%83)
- [工作流示例](#%E5%B7%A5%E4%BD%9C%E6%B5%81%E7%A4%BA%E4%BE%8B)
- [模型微调](#%E6%96%B0%E5%8A%9F%E8%83%BD%E6%A8%A1%E5%9E%8B%E5%BE%AE%E8%B0%83)

## 快速开始

SAGE 提供两种方式使用快捷命令：

### 方式 1: 使用 Makefile（推荐）

```bash
# 查看所有可用命令
make help

# 运行命令
make lint
make test
make build
```

### 方式 2: 使用 dev.sh 脚本

```bash
# 查看所有可用命令
./dev.sh help

# 运行命令
./dev.sh lint
./dev.sh test
./dev.sh build
```

## 使用方式

### 前置条件

这些快捷命令需要**源码安装模式**（开发模式）：

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 快速安装
./quickstart.sh

# 或者手动安装
pip install -e .
```

## 命令参考

### 📦 安装与设置

#### `make install` / `./dev.sh install`

快速安装 SAGE 到开发模式。

```bash
make install
# 或
./dev.sh install
```

等价于运行：

```bash
./quickstart.sh
```

______________________________________________________________________

### ✨ 代码质量

#### `make lint` / `./dev.sh lint`

运行代码检查（flake8），不修改代码。

```bash
make lint
# 或
./dev.sh lint
```

等价于：

```bash
sage-dev quality --check-only
```

#### `make format` / `./dev.sh format`

自动格式化代码（black + isort）。

```bash
make format
# 或
./dev.sh format
```

等价于：

```bash
sage-dev quality
```

#### `make quality` / `./dev.sh quality`

运行完整质量检查（检查 + 格式化）。

```bash
make quality
# 或
./dev.sh quality
```

______________________________________________________________________

### 🧪 测试

#### `make test` / `./dev.sh test`

运行所有测试。

```bash
make test
# 或
./dev.sh test

# 传递额外参数
./dev.sh test -v -k "test_environment"
```

等价于：

```bash
pytest
```

#### `make test-quick` / `./dev.sh test:quick`

运行快速测试（跳过标记为 slow 的测试）。

```bash
make test-quick
# 或
./dev.sh test:quick
```

等价于：

```bash
pytest -m "not slow" -v
```

#### `make test-all` / `./dev.sh test:all`

运行完整测试套件，包括代码覆盖率报告。

```bash
make test-all
# 或
./dev.sh test:all
```

等价于：

```bash
pytest -v --cov=packages --cov-report=html
```

______________________________________________________________________

### 📦 构建与发布

#### `make build` / `./dev.sh build`

构建所有包的分发文件。

```bash
make build
# 或
./dev.sh build
```

等价于：

```bash
sage-dev pypi build
```

#### `make clean` / `./dev.sh clean`

清理构建产物（dist、build 目录）。

```bash
make clean
# 或
./dev.sh clean
```

等价于：

```bash
sage-dev pypi clean
```

#### `make check` / `./dev.sh check`

检查包配置是否正确。

```bash
make check
# 或
./dev.sh check
```

等价于：

```bash
sage-dev pypi check
```

#### `make publish` / `./dev.sh publish`

发布到 TestPyPI（测试环境）。

```bash
make publish
# 或
./dev.sh publish
```

等价于：

```bash
sage-dev pypi publish --dry-run
```

#### `make publish-prod` / `./dev.sh publish:prod`

发布到生产 PyPI（需要确认）。

```bash
make publish-prod
# 或
./dev.sh publish:prod
# 会提示确认: 确认发布到生产环境? [y/N]
```

等价于：

```bash
sage-dev pypi publish
```

______________________________________________________________________

### 🔧 版本管理

#### `make version` / `./dev.sh version`

显示所有包的当前版本。

```bash
make version
# 或
./dev.sh version
```

等价于：

```bash
sage-dev version list
```

#### `make version-bump` / `./dev.sh version:bump`

交互式升级版本号。

```bash
make version-bump
# 或
./dev.sh version:bump
```

等价于：

```bash
sage-dev version bump
```

#### `./dev.sh version:set <version>`

设置指定版本号。

```bash
./dev.sh version:set 0.2.0
```

等价于：

```bash
sage-dev version set 0.2.0
```

______________________________________________________________________

### 📚 文档

#### `make docs` / `./dev.sh docs`

构建文档。

```bash
make docs
# 或
./dev.sh docs
```

等价于：

```bash
cd docs-public && ./build.sh
```

#### `make docs-serve` / `./dev.sh docs:serve`

启动本地文档服务器预览。

```bash
make docs-serve
# 或
./dev.sh docs:serve
# 访问 http://127.0.0.1:8000
```

等价于：

```bash
cd docs-public && mkdocs serve
```

______________________________________________________________________

## 工作流示例

### 日常开发工作流

```bash
# 1. 修改代码后，格式化
make format

# 2. 运行测试
make test-quick

# 3. 如果测试通过，运行完整质量检查
make quality

# 4. 提交代码
git add .
git commit -m "feat: 添加新功能"
git push
```

### 发布新版本工作流

```bash
# 1. 确保所有测试通过
make test-all

# 2. 运行代码质量检查
make quality

# 3. 升级版本号
make version-bump
# 选择: patch (0.1.5 -> 0.1.6)
#       minor (0.1.5 -> 0.2.0)
#       major (0.1.5 -> 1.0.0)

# 4. 检查包配置
make check

# 5. 清理旧的构建产物
make clean

# 6. 构建新版本
make build

# 7. 发布到 TestPyPI 测试
make publish

# 8. 在测试环境验证安装
conda create -n test_env python=3.11
conda activate test_env
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ isage

# 9. 如果测试通过，发布到生产环境
make publish-prod

# 10. 提交版本更新
git add .
git commit -m "chore: bump version to 0.1.6"
git push
git tag v0.1.6
git push --tags
```

### 文档更新工作流

```bash
# 1. 修改文档
vim docs-public/docs_src/get_start/quickstart.md

# 2. 本地预览
make docs-serve
# 在浏览器中访问 http://127.0.0.1:8000

# 3. 构建文档
make docs

# 4. 提交更新
git add docs-public/
git commit -m "docs: 更新快速开始指南"
git push
```

______________________________________________________________________

## 对比：Make vs dev.sh vs sage-dev

| 功能         | Make   | dev.sh | sage-dev | 说明                      |
| ------------ | ------ | ------ | -------- | ------------------------- |
| **简洁性**   | ⭐⭐⭐ | ⭐⭐   | ⭐       | Make 命令最短             |
| **可读性**   | ⭐⭐   | ⭐⭐⭐ | ⭐⭐⭐   | dev.sh 和 sage-dev 更明确 |
| **参数传递** | ⭐     | ⭐⭐⭐ | ⭐⭐⭐   | dev.sh 和 sage-dev 更灵活 |
| **跨平台**   | ⭐⭐   | ⭐⭐⭐ | ⭐⭐⭐   | dev.sh 不依赖 Make        |
| **集成度**   | -      | -      | ⭐⭐⭐   | sage-dev 是官方工具       |

### 推荐使用场景

- **快速开发**: 使用 `make` 命令（最简洁）
- **脚本自动化**: 使用 `./dev.sh` 命令（更可控）
- **CI/CD**: 使用 `sage-dev` 命令（最可靠）
- **学习/文档**: 使用 `sage-dev` 命令（最标准）

______________________________________________________________________

## 常见问题

### Q: 为什么运行命令时提示 "命令仅在开发模式下可用"？

A: 这些快捷命令调用 `sage-dev` 工具，需要源码安装：

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 安装为开发模式
pip install -e .
```

### Q: Make 和 dev.sh 有什么区别？

A: 两者功能相同，只是接口不同：

- `make` 使用 GNU Make，命令更简洁（如 `make test`）
- `./dev.sh` 是纯 Bash 脚本，不依赖 Make，使用冒号分隔子命令（如 `./dev.sh test:quick`）

### Q: 我应该使用哪个？

A: 根据个人喜好选择：

- 如果你熟悉 Make 工具链，使用 `make`
- 如果你不想安装 Make，使用 `./dev.sh`
- 如果你想要最大的灵活性，直接使用 `sage-dev`

### Q: 这些命令可以在 pip 安装的 SAGE 中使用吗？

A: 不可以。这些命令设计用于开发环境，需要访问源代码：

```bash
# ❌ pip 安装（用户模式）
pip install isage
make test  # 无法运行

# ✅ 源码安装（开发模式）
git clone https://github.com/intellistream/SAGE.git
cd SAGE
pip install -e .
make test  # 可以运行
```

______________________________________________________________________

## 扩展与定制

### 添加自定义命令

#### 1. 修改 Makefile

编辑 `Makefile`，添加新目标：

```makefile
# 添加到 .PHONY 行
.PHONY: ... my-command

# 添加新命令
my-command:
	@echo "🚀 运行自定义命令..."
	sage-dev my-tool --option value
```

#### 2. 修改 dev.sh

编辑 `dev.sh`，添加新的 case：

```bash
case "$1" in
    # ... 现有命令 ...

    my-command)
        echo -e "${BLUE}🚀 运行自定义命令...${NC}"
        sage-dev my-tool --option value "${@:2}"
        ;;

    # ... 其他命令 ...
esac
```

### 创建项目特定别名

在你的 shell 配置文件（`~/.bashrc` 或 `~/.zshrc`）中添加：

```bash
# SAGE 开发别名
alias sage-lint='cd /path/to/SAGE && make lint'
alias sage-test='cd /path/to/SAGE && make test'
alias sage-format='cd /path/to/SAGE && make format'
```

______________________________________________________________________

## 新功能：模型微调

### 🎓 `sage finetune` - 大模型微调工具

SAGE 提供了交互式的大模型微调功能，支持多种场景：

#### 快速开始

```bash
# 查看使用示例
sage finetune examples

# 微调模型理解 SAGE 代码库
sage finetune start --task code --auto

# 自定义问答对微调
sage finetune start --task qa --data my_qa.json

# 查看所有微调任务
sage finetune list
```

#### 主要功能

- ✅ **代码理解微调** - 让模型深度理解项目代码
- ✅ **问答对微调** - 基于QA数据训练专家模型
- ✅ **指令微调** - 增强指令遵循能力
- ✅ **对话微调** - 训练多轮对话能力
- ✅ **自定义数据** - 支持自己的数据集

#### 架构说明

**当前版本 (v1.0)**: 使用成熟框架 (LLaMA-Factory/Unsloth)

- 快速上手，利用工业级优化
- 自动检测并安装依赖
- 详细的训练监控

**未来计划 (v2.0)**: SAGE Pipeline 原生实现

- 完整的 dataflow 编排
- 统一的资源管理和监控
- 查看详细计划: [FINETUNE_PIPELINE_TODO.md](./FINETUNE_PIPELINE_TODO.md)

#### 详细文档

- [微调原理指南](./FINETUNE_GUIDE.md) - 深入理解Loss、LoRA、优化器等
- [Pipeline集成计划](./FINETUNE_PIPELINE_TODO.md) - v2.0路线图

#### 使用示例

```bash
# 1. 代码理解微调（默认）
sage finetune start --task code

# 2. 问答对微调
cat > qa_data.json <<EOF
[
  {
    "question": "SAGE是什么?",
    "answer": "SAGE是流式增强的生成执行框架...",
    "context": "可选的上下文信息"
  }
]
EOF
sage finetune start --task qa --data qa_data.json

# 3. 查看训练进度
sage finetune list

# 4. 清理旧的输出
sage finetune clean --before 7d
```

______________________________________________________________________

## 参考链接

- [SAGE 主仓库](https://github.com/intellistream/SAGE)
- [贡献指南](../CONTRIBUTING.md)
- [开发者文档](../docs/dev-notes/README.md)
- [CI/CD 文档](../docs/ci-cd/README.md)
- [微调指南](./FINETUNE_GUIDE.md) ⭐ 新增
- [微调Pipeline计划](./FINETUNE_PIPELINE_TODO.md) ⭐ 新增

______________________________________________________________________

**💡 提示**: 这些快捷命令会随着项目发展持续更新。建议定期查看此文档以了解新功能。
