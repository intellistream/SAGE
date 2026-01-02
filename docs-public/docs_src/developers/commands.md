# 🚀 SAGE 开发工具快捷命令

本文档介绍 SAGE 项目提供的便捷开发命令，帮助开发者提高工作效率。

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

## `sage-dev` CLI 速查表

| 模块           | 常用命令                                                       | 作用                                                                                         |
| -------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 项目测试       | \`sage-dev project test \[--quick                              | --coverage                                                                                   |
| 示例测试       | `sage-dev examples test [--filter <name>]`                     | 运行 `examples/` 下的教程与应用脚本                                                          |
| 文档           | `sage-dev docs build` / `sage-dev docs serve`                  | 构建或本地预览 `docs-public`（使用 MkDocs）                                                  |
| 质量检查       | `sage-dev quality check --check-only` / `sage-dev quality fix` | 触发 Ruff/Mypy/架构合规；`--check-only` 不改文件                                             |
| Submodule 维护 | \`sage-dev maintain submodule (status                          | init                                                                                         |
| C++ 扩展       | `sage-dev extensions install all [--force]`                    | 在 `.sage/build/` 构建扩展，支持 `--force` 重编                                              |
| 打包/发布      | \`sage-dev package pypi (build                                 | check                                                                                        |
| 版本管理       | \`sage-dev package version (list                               | bump                                                                                         |
| 工具版本校验   | `./tools/install/check_tool_versions.sh [--fix]`               | 确保 `tools/pre-commit-config.yaml` 与 `packages/sage-tools/pyproject.toml` 的 Ruff 版本一致 |

> 所有 `make`、`dev.sh` 命令最终都会调用 `sage-dev`，因此在 CI/自动化脚本中直接使用 `sage-dev` 可减少封装层次数。

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
sage-dev quality check --check-only
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
sage-dev quality fix
```

#### `make quality` / `./dev.sh quality`

运行完整质量检查（检查 + 格式化）。

```bash
make quality
# 或
./dev.sh quality
```

等价于：

```bash
sage-dev quality check
```

#### 版本约束（Ruff / pre-commit）

- 配置文件：`tools/pre-commit-config.yaml`（Git 钩子）与 `tools/ruff.toml`（Ruff 格式 + lint 设置）。
- 版本来源：`packages/sage-tools/pyproject.toml` 中的 `ruff==x.y.z`，必须与 pre-commit 中的 `rev: vX.Y.Z` 一致。
- 校验流程：

```bash
# 1. 每次升级 Ruff / pre-commit 前先拉最新配置
git pull

# 2. 运行脚本自动比对版本号
./tools/install/check_tool_versions.sh

# 3. 发现不一致时执行 --fix 选项批量更新
./tools/install/check_tool_versions.sh --fix

# 4. 重新生成锁定结果 & 提交
git add tools/pre-commit-config.yaml packages/sage-tools/pyproject.toml
git commit -m "chore: bump ruff to v0.7.x"
```

> 只有在版本匹配的情况下，`sage-dev quality check` 才能保证本地与 CI 结果一致。

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
sage-dev project test
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
sage-dev project test --quick
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
sage-dev project test --coverage
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
sage-dev package pypi build
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
sage-dev package pypi clean
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
sage-dev package pypi check
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
sage-dev package pypi publish --dry-run
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
sage-dev package pypi publish
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
sage-dev package version list
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
sage-dev package version bump
```

#### `./dev.sh version:set <version>`

设置指定版本号。

```bash
./dev.sh version:set 0.2.0
```

等价于：

```bash
sage-dev package version set 0.2.0
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
sage-dev docs build
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
sage-dev docs serve
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
vim docs-public/docs_src/getting-started/quickstart.md

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

#### 详细文档

参见 [GitHub 仓库中的开发文档](https://github.com/intellistream/SAGE/tree/main/docs/dev-notes) 获取更多细节。

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
- [贡献指南](https://github.com/intellistream/SAGE/blob/main/CONTRIBUTING.md)
- [开发者文档](https://github.com/intellistream/SAGE/tree/main/docs/dev-notes)
- [CI/CD 文档](./ci-cd.md)

______________________________________________________________________

**💡 提示**: 这些快捷命令会随着项目发展持续更新。建议定期查看此文档以了解新功能。
