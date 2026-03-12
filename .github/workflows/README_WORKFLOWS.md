# SAGE CI/CD Workflows 说明

本文档说明 SAGE 项目的各个 CI/CD workflow 的职责和测试覆盖范围。

## 📋 Workflow 职责划分

| Workflow                      | 触发条件                 | 职责              | 安装方式                   | 运行时间 | 必须通过 |
| ----------------------------- | ------------------------ | ----------------- | -------------------------- | -------- | -------- |
| **ci-build-test.yml**         | PR/Push (packages/)      | 构建测试覆盖率    | `quickstart.sh --dev`      | ~45分钟  | ✅       |
| **ci-sagellm-test.yml**       | PR/Push (packages/)      | SageLLM mock/CUDA | pip install packages       | ~30分钟  | ✅ (mock)|
| **ci-code-quality.yml**       | PR/Push (\*.py)          | 代码质量检查      | pip install tools only     | ~10分钟  | ✅       |
| **ci-deployment-check.yml**   | PR/Push                  | 部署就绪检查      | `quickstart.sh --dev`      | ~15分钟  | -        |
| **ci-examples-test.yml**      | PR/Push (examples/)      | 示例功能测试      | `quickstart.sh --dev`      | ~30分钟  | -        |
| **ci-pr-install.yml**         | PR/Push (pyproject.toml) | 用户安装测试      | 构建 wheel + pip install   | ~20分钟  | -        |

## 🚀 SageLLM 测试 (ci-sagellm-test.yml) - 新增

专门测试 SageLLM 推理引擎集成。

### Job 1: SageLLM Mock Backend (必须通过)

**所有 PR 必须通过此测试**，验证：

- ✅ `isagellm` 包安装正常
- ✅ `SageLLMGenerator` 与 mock backend 集成
- ✅ Agentic operators 与 mock backend 兼容
  - `PlanningOperator`
  - `TimingOperator`
  - `ToolSelectionOperator`

```bash
# 测试命令
pytest -v -k "sagellm or mock or SageLLM or Mock" packages/
```

### Job 2: SageLLM CUDA Backend (可选)

需要 GPU runner，仅在以下情况运行：

- 手动触发 workflow 并选择 `run_cuda_tests: true`
- Push 到 `main` 分支

**Runner 要求**: `[self-hosted, gpu, cuda]` labels

**环境变量** (适用于中国 self-hosted runner):

```yaml
env:
  SAGE_FORCE_CHINA_MIRROR: true
  HF_ENDPOINT: https://hf-mirror.com
  PIP_INDEX_URL: https://pypi.tuna.tsinghua.edu.cn/simple
```

### 手动触发 CUDA 测试

```bash
# GitHub CLI
gh workflow run ci-sagellm-test.yml -f run_cuda_tests=true

# 或 GitHub UI:
# Actions → SageLLM Mock & CUDA Tests → Run workflow → ✅ Run CUDA tests
```

### Branch Protection 配置

在 Repository Settings → Branches → Branch protection rules 中，添加 required status check:

- `SageLLM Mock Backend`

这确保所有 PR 必须通过 sagellm mock 测试。

## 🎯 安装模式对照表

### quickstart.sh 模式

| quickstart.sh | pip install | 包含内容 | 用途 | 包数量 |
| ------------- | ----------- | -------- | ---- | ------ |
| `--minimal` | `isage` | 主仓核心表面 (foundation/stream/runtime/serving/cli) | 容器部署、生产环境 | ~80 |
| `--dev` | `isage` + dev tools | minimal + pytest, ruff, mypy | 框架开发、贡献代码 | ~120 |
| `--full` | `isage` + all extras | dev + 科学库 + 可选依赖 | 完整功能、学习示例 | ~200+ |

**默认模式**: `--full` (推荐新用户使用)

### 模式详细说明

#### `minimal` (最小安装)

- **包含包**：isage（核心表面）+ 可选外部引擎/适配器按需安装
- **核心功能**：Foundation, DataStream API, Runtime, Serving integration, CLI
- **适用场景**：
  - Docker 容器部署
  - 生产环境最小化安装
  - 仅需要流处理核心功能
  - CI/CD 快速测试
- **提示**：如需使用 ML、向量数据库等功能，可手动安装:

  ```bash
  pip install 'isage[capability-adapters]'
  ```

#### `dev` (开发安装)

- **包含包**：minimal + 开发工具
- **额外功能**：
  - pytest, pytest-cov (测试)
  - ruff (格式化/lint)
  - mypy (类型检查)
  - pre-commit (Git hooks)
- **适用场景**：
  - 开发 SAGE 框架代码
  - 贡献代码到 SAGE
  - 运行测试和代码质量检查
- **提示**：如需 ML/科学计算功能:

  ```bash
  pip install 'isage[full]'
  ```

#### `full` (完整安装，默认)

- **包含包**：dev + 科学库 + 所有可选依赖
- **额外功能**：
  - 科学计算库 (numpy, pandas, matplotlib, jupyter)
  - ML 功能 (torch, transformers)
  - 向量数据库 (faiss-cpu)
  - 流处理扩展 (aiostream)
  - 压缩功能 (llmlingua)
  - 性能基准测试 (isage-benchmark)
- **适用场景**：
  - 学习 SAGE 完整功能
  - 运行所有示例代码
  - 使用 RAG/LLM 功能
  - 日常开发和测试

**Note**: Performance benchmarking is now available via separate package: `pip install isage-benchmark`

- **包含包**：full + sage-tools[dev]
- **额外功能**：
  - 完整开发工具套件：
    - pytest, pytest-cov, pytest-asyncio
    - black, isort, ruff
    - mypy, flake8
    - pre-commit
- **适用场景**：
  - 修改 SAGE 框架源码
  - 贡献代码到项目
  - 进行框架级别的研究

## 📊 pip-installation-test.yml 测试矩阵

### 当前测试配置

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
    install-mode: ['minimal', 'dev', 'full']
  fail-fast: false
```

**总共测试组合**：3 × 3 = 9 个组合

### 测试内容

对于每个 (Python版本, 安装模式) 组合，测试：

1. **本地 Wheel 构建安装**

   - 构建所有 SAGE 包为 wheel
   - 使用 `pip install --find-links dist isage` 安装
   - 验证基础导入和 CLI 可用性

1. **从源码安装**

   - 按依赖顺序使用 `pip install .` 安装
   - 模拟用户从 GitHub 克隆后安装
   - 根据模式验证特定功能

1. **模式特定验证**

   - **minimal**: Pipeline, Operators, CLI
   - **dev**: minimal + pytest, ruff, mypy
   - **full**: dev + torch, transformers, faiss, jupyter

### 额外测试 (独立 jobs)

- **导入路径测试** (test-import-paths)

  - 测试所有层级的导入路径
  - 验证包结构和 API 暴露

- **依赖解析测试** (test-dependency-resolution)

  - 测试干净环境下的依赖解析
  - 使用 `pip check` 检查依赖冲突
  - 确保 PyPI 上所有依赖都可用

## 🔄 模式对齐检查清单

### quickstart.sh vs pip install

- [x] `--minimal` ↔️ `pip install isage` ✅
- [x] `--dev` ↔️ `pip install isage` + dev tools ✅
- [x] `--full` ↔️ `pip install isage` + 所有可选依赖 ✅

### pip-installation-test.yml 测试覆盖

- [x] `minimal` 模式 ✅
- [x] `dev` 模式 ✅
- [x] `full` 模式 ✅
- [x] Python 3.10 ✅
- [x] Python 3.11 ✅
- [x] Python 3.12 ✅

## 🚀 使用示例

### 用户安装 (从 PyPI)

```bash
# 核心运行时（最小依赖）
pip install isage

# 添加核心可选适配器
pip install 'isage[capability-adapters]'

# 添加工具使用适配器
pip install 'isage[capability-tooluse]'

# 添加所有可选功能
pip install 'isage[full]'
```

### 开发者安装 (从源码)

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 使用 quickstart.sh
./quickstart.sh --full         # 完整功能（默认）
./quickstart.sh --dev          # 开发模式
./quickstart.sh --minimal      # 最小安装

# 或手动安装
pip install -e ".[dev]"        # 开发模式
pip install -e ".[standard]"   # 标准模式
```

## 📝 注意事项

1. **默认行为差异**：

   - `quickstart.sh` 默认使用 `--full` 模式
   - `pip install isage` 安装核心依赖，可选依赖通过 extras 安装

1. **安装方式差异**：

   - `quickstart.sh` 始终使用 `pip install -e`（可编辑模式）
   - `pip install isage` 使用标准安装（非可编辑）

1. **CI/CD 策略**：

   - 代码质量检查使用 `--dev`（需要开发工具）
   - 示例测试使用 `--dev`（模拟开发者）
   - 清理工具使用 `--minimal`（最小依赖）
   - pip 安装测试覆盖所有 3 种模式

1. **测试覆盖**：

   - 每个模式在 3 个 Python 版本下测试
   - 总计 9 个测试组合
   - 允许部分失败（`fail-fast: false`）

## 🔗 相关文档

- [SAGE 架构文档](https://intellistream.github.io/sage-docs/architecture/)
- [包依赖关系](../../docs/dependency-audit-gate.md)
- [贡献指南](../../CONTRIBUTING.md)
- [CI/CD 分层与目录结构](https://intellistream.github.io/sage-docs/dev-notes/cross-layer/ci-cd/)

## ♻️ Workflow 命名规范

**前缀分类**:

| 前缀 | 含义 | 触发方式 |
| ---- | ---- | -------- |
| `ci-*` | 持续集成检查 | PR/Push 自动触发 |
| `cd-*` | 部署/发布 | Tag/Release/手动触发 |
| `util-*` | 辅助工具 | 定时/手动触发 |
| `exp-*` | 实验/研究 | 手动触发 |

**完整列表**:

```text
ci-build-test.yml        # 构建 + 单元测试 (packages 变更触发)
ci-code-quality.yml      # Lint & Format (*.py 变更触发, ~3min)
ci-pr-examples.yml       # Examples quick 测试 (examples 变更触发)
ci-pr-install.yml        # 安装冒烟测试 (pyproject 变更触发)
ci-release-examples.yml  # Examples full 测试 (main push/release)
ci-release-install.yml   # 全量安装验证 (main push/release)
ci-deployment-check.yml  # 部署就绪检查

cd-publish-pypi.yml      # PyPI 发布 (tag/release)
cd-deploy-studio.yml     # Studio 部署 (手动)

util-sync-branches.yml   # main → main-dev 同步
util-cleanup.yml         # 测试环境清理
util-todo-to-issue.yml   # TODO 转 Issue
util-weekly-report.yml   # 周报生成
util-branch-protection.yml # 分支保护检查

exp-paper1.yml           # Paper1 实验 (GPU, 手动)
```

______________________________________________________________________

## 🚀 新增：Self-Hosted 部署 Workflow

### `deploy-studio.yml` - 自动部署 SAGE Studio

**功能**：在 self-hosted GitHub Actions runner 上自动部署 SAGE Studio 并暴露服务。

**触发方式**：

1. **自动触发**：推送到 `main` 或 `feat/unified-chat-canvas-rebased` 分支
1. **手动触发**：GitHub Actions → "Deploy SAGE Studio" → Run workflow

**部署流程**：

1. 停止现有服务
1. 安装 SAGE (full 模式)
1. 构建 RAG 索引
1. 启动 Gateway (端口 8000)
1. 启动 Studio (端口 4200)
1. 配置防火墙
1. 输出访问地址

**访问方式**：

部署成功后，在 Actions Summary 中查看访问地址：

```text
Studio UI:   http://<服务器IP>:4200
Gateway API: http://<服务器IP>:8000
```

**详细文档**：

- [Self-Hosted 部署完整指南](../../docs/dev-notes/cross-layer/self-hosted-deployment.md)
- [部署脚本使用](../../deploy-self-hosted.sh)

**服务器管理**：

```bash
# SSH 到服务器后

# 查看服务
ps aux | grep -E "sage studio|sage-gateway"

# 查看日志
tail -f ~/.sage/gateway.log
tail -f ~/.sage/studio.log

# 重新部署
cd /path/to/SAGE
./deploy-self-hosted.sh 4200 8000
```

**所需 Secrets**：

在 GitHub Settings → Secrets 中配置：

- `SAGE_CHAT_API_KEY` / `OPENAI_API_KEY` - OpenAI 兼容 API Key（云端或自托管都可，例如阿里云 DashScope 兼容端点）
- `HF_TOKEN` - Hugging Face Token (可选)
