# SAGE CI/CD Workflows 说明

本文档说明 SAGE 项目的各个 CI/CD workflow 的职责和测试覆盖范围。

## 📋 Workflow 职责划分

| Workflow                      | 触发条件                 | 职责         | 安装方式                   | 运行时间 |
| ----------------------------- | ------------------------ | ------------ | -------------------------- | -------- |
| **code-quality.yml**          | PR/Push (\*.py)          | 代码质量检查 | `quickstart.sh --dev`      | ~10分钟  |
| **deployment-check.yml**      | PR/Push                  | 部署就绪检查 | `quickstart.sh --dev`      | ~15分钟  |
| **examples-test.yml**         | PR/Push (examples/)      | 示例功能测试 | `quickstart.sh --standard` | ~30分钟  |
| **pip-installation-test.yml** | PR/Push (pyproject.toml) | 用户安装测试 | 构建 wheel + pip install   | ~20分钟  |
| **build-test.yml**            | PR/Push (C++ 代码)       | C++ 扩展构建 | cmake + 编译               | ~15分钟  |

## 🎯 安装模式对照表

### quickstart.sh 模式

| quickstart.sh | pip install       | 包含内容                              | 用途               | 大小   |
| ------------- | ----------------- | ------------------------------------- | ------------------ | ------ |
| `--core`      | `isage[core]`     | L1-L3 (common, platform, kernel)      | 容器部署、生产环境 | ~100MB |
| `--standard`  | `isage[standard]` | L1-L4+L6 (核心+CLI+Web UI+RAG/LLM)    | 应用开发、日常使用 | ~200MB |
| `--full`      | `isage[full]`     | standard + L5 (apps, benchmark)       | 学习示例、性能评估 | ~300MB |
| `--dev`       | `isage[dev]`      | full + 开发工具 (pytest, black, mypy) | 框架开发、贡献代码 | ~400MB |

### 模式详细说明

#### `core`

- **包含包**：sage-common, sage-platform, sage-kernel
- **核心功能**：Pipeline, Operators, DataStream API
- **适用场景**：
  - Docker 容器部署
  - 生产环境最小化安装
  - 仅需要流处理核心功能

#### `standard` (默认)

- **包含包**：core + sage-libs, sage-middleware, sage-tools[cli], sage-studio
- **额外功能**：
  - RAG/LLM operators
  - CLI 工具 (sage, sage-dev)
  - Web UI (SAGE Studio)
  - 数据科学库 (numpy, pandas, matplotlib, jupyter)
- **适用场景**：
  - 开发 SAGE 应用
  - 使用 RAG/LLM 功能
  - 日常开发和测试

#### `full`

- **包含包**：standard + sage-apps, sage-benchmark
- **额外功能**：
  - 示例应用（医疗、视频分析等）
  - 性能基准测试工具
- **适用场景**：
  - 学习 SAGE
  - 运行示例代码
  - 性能评估和优化

#### `dev`

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
    install-mode: ['core', 'standard', 'full', 'dev']
  fail-fast: false
```

**总共测试组合**：3 × 4 = 12 个组合

### 测试内容

对于每个 (Python版本, 安装模式) 组合，测试：

1. **本地 Wheel 构建安装**

   - 构建所有 SAGE 包为 wheel
   - 使用 `pip install --find-links dist "isage[mode]"` 安装
   - 验证基础导入和 CLI 可用性

1. **从源码安装**

   - 按依赖顺序使用 `pip install .` 安装
   - 模拟用户从 GitHub 克隆后安装
   - 根据模式验证特定功能

1. **模式特定验证**

   - **core**: Pipeline, Operators
   - **standard**: RAGPipeline, CLI tools
   - **full**: Apps, Benchmark
   - **dev**: pytest, black, mypy

### 额外测试 (独立 jobs)

- **导入路径测试** (test-import-paths)

  - 测试所有层级的导入路径
  - 验证包结构和 API 暴露

- **依赖解析测试** (test-dependency-resolution)

  - 测试干净环境下的依赖解析
  - 使用 `pip check` 检查依赖冲突
  - 确保 PyPI 上所有依赖都可用

## 🔄 模式对齐检查清单

### quickstart.sh vs pyproject.toml

- [x] `--core` ↔️ `isage[core]` ✅
- [x] `--standard` ↔️ `isage[standard]` ✅
- [x] `--full` ↔️ `isage[full]` ✅
- [x] `--dev` ↔️ `isage[dev]` ✅

### pip-installation-test.yml 测试覆盖

- [x] `core` 模式 ✅
- [x] `standard` 模式 ✅
- [x] `full` 模式 ✅
- [x] `dev` 模式 ✅
- [x] Python 3.10 ✅
- [x] Python 3.11 ✅
- [x] Python 3.12 ✅

## 🚀 使用示例

### 用户安装 (从 PyPI)

```bash
# 核心运行时
pip install isage[core]

# 标准安装（推荐）
pip install isage
# 或
pip install isage[standard]

# 完整功能
pip install isage[full]

# 开发模式
pip install isage[dev]
```

### 开发者安装 (从源码)

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 使用 quickstart.sh（推荐）
./quickstart.sh --dev          # 开发模式（默认）
./quickstart.sh --standard     # 标准模式
./quickstart.sh --full         # 完整功能
./quickstart.sh --core         # 核心运行时

# 或手动安装
pip install -e ".[dev]"        # 开发模式
pip install -e ".[standard]"   # 标准模式
```

## 📝 注意事项

1. **默认行为差异**：

   - `quickstart.sh` 默认使用 `--dev` 模式
   - `pip install isage` 默认等同于 `isage[standard]`

1. **安装方式差异**：

   - `quickstart.sh` 始终使用 `pip install -e`（可编辑模式）
   - `pip install isage` 使用标准安装（非可编辑）

1. **CI/CD 策略**：

   - 代码质量检查使用 `--dev`（需要开发工具）
   - 示例测试使用 `--standard`（模拟标准用户）
   - pip 安装测试覆盖所有 4 种模式

1. **测试覆盖**：

   - 每个模式在 3 个 Python 版本下测试
   - 总计 12 个测试组合
   - 允许部分失败（`fail-fast: false`）

## 🔗 相关文档

- [SAGE 架构文档](../../docs-public/docs_src/dev-notes/package-architecture.md)
- [包依赖关系](../../docs-public/docs_src/dev-notes/package-dependencies.md)
- [贡献指南](../../CONTRIBUTING.md)
