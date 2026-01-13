# SAGE Copilot Instructions

## Overview

**SAGE** is a Python 3.10+ framework for building AI/LLM data processing pipelines with declarative
dataflow. 8 core packages + 1 meta-package, ~300MB dev install, uses C++ extensions (CMake).

LLM inference components (sage-llm-core, sage-llm-gateway) have been moved to independent repositories.

## 🚨 CRITICAL Architectural Constraints

### ✅ Libs vs Middleware Rule (NEW, ENFORCED)

**If code needs to call “upward” capabilities (Vector DB, Memory system, Refiner, external services, heavy runtime backends), it is NOT a library. It MUST live in `sage-middleware` (components/operators).**

This rule exists to prevent长期反复出现的“L3 libs → L4 middleware”依赖倒挂问题。

#### ✅ What stays in `sage-libs`

- Pure algorithms / policies / utilities
- Data types and interfaces (ABC/Protocol)
- Code that depends only on `sage-common` / `sage-platform` / Python stdlib / lightweight deps
- Must be runnable and testable without external services

#### ✅ What MUST be in `sage-middleware`

- Anything that touches or depends on:
  - Vector stores / indices: SageVDB (`isage-vdb`), FAISS, Milvus, etc.
  - Memory backends: Neuromem (`isage-neuromem`), Redis, RocksDB, etc.
  - Refiners / compressors (LLMLingua, LongRefiner adapters)
  - Network services (HTTP APIs), persistent storage, connection pools, background workers
- Any end-to-end orchestration that is strongly runtime-bound (operators, pipelines-as-a-service)

#### 🚫 No backwards compatibility during refactors

When we move code from `sage-libs` to `sage-middleware`, **do NOT keep re-export shims** (no legacy imports). Update all call sites in the repo and let broken imports fail fast.

Rationale: keep the codebase clean; avoid长期兼容层造成的隐式依赖和维护成本。

#### 🛡️ Enforcement

- **Pre-commit hook**: `libs-middleware-import-check` - Blocks commits if `sage-libs` imports `sage.middleware`
- **Script**: `tools/hooks/check_libs_middleware_import.sh --all-files`
- **Policy doc**: `docs-public/docs_src/dev-notes/cross-layer/MIDDLEWARE_COMPONENT_PROMOTION_POLICY.md`

### ❌ NEVER BYPASS CONTROL PLANE - ABSOLUTE RULE

**ALL LLM engine operations MUST go through Control Plane. Direct engine startup is FORBIDDEN.**

This is a **non-negotiable architectural constraint**. Violating this breaks resource management, scheduling, and monitoring.

#### ❌ FORBIDDEN Operations:

```bash
sage llm serve -m <model>              # ❌ Command removed
python -m vllm.entrypoints.openai      # ❌ Direct vLLM
requests.post("http://localhost:8001/v1/...")  # ❌ Direct endpoint
```

```python
from vllm import LLM  # ❌ Direct import
engine = LLM(model="...")  # ❌ Direct instantiation
```

#### ✅ CORRECT Operations:

```bash
sage llm engine start <model> --engine-kind llm    # ✅ Control Plane
sage llm engine list                               # ✅ Managed
sage llm engine stop <id>                          # ✅ Controlled
```

```python
from sage.llm import UnifiedInferenceClient
client = UnifiedInferenceClient.create()  # ✅ Auto-routes through Control Plane
response = client.chat([{"role": "user", "content": "Hello"}])
```

**Why**: Resource management, load balancing, fault tolerance, monitoring, SLO-aware scheduling.

**Enforcement**: Pre-commit hooks, CI/CD checks, code review. Commands `sage llm serve/run/stop/restart/status/logs` have been completely deleted.

## CRITICAL Coding Principles

### ❌ NEVER MANUAL PIP INSTALL - ALWAYS USE pyproject.toml
**ALL dependencies MUST be declared in pyproject.toml. NEVER use manual `pip install` commands.**

This is a **project-wide principle** to ensure reproducibility and consistency.

#### ❌ FORBIDDEN Operations:

```bash
pip install transformers              # ❌ Manual install
pip install torch==2.7.0              # ❌ Manual version
pip install vllm                      # ❌ Manual dependency
```

#### ✅ CORRECT Operations:

```toml
# In packages/*/pyproject.toml
dependencies = [
    "transformers>=4.52.0,<4.54.0",  # ✅ Declared in pyproject.toml
    "torch>=2.7.0,<3.0.0",           # ✅ Version constraints
    "vllm>=0.9.2,<0.10",             # ✅ Optional dependencies
]
```

```bash
# Then reinstall packages
pip install -e packages/sage-middleware -e packages/sage-libs
```

**Why**: Ensures reproducibility, tracks dependency changes in git, prevents version conflicts, maintains single source of truth.

**Enforcement**: Code review, CI/CD checks. Any manual pip install should trigger immediate refactoring to pyproject.toml.

### ❌ NO FALLBACK LOGIC - PROJECT-WIDE RULE
**NEVER use try-except fallback patterns anywhere in the codebase.**

This is a **project-wide principle**, not just for version management. Fallbacks hide problems and make debugging harder.

#### ❌ BAD Examples (Do NOT do this):

```python
# Version imports
try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"  # ❌ NO - hides missing file

# Configuration loading
try:
    config = load_config("config.yaml")
except FileNotFoundError:
    config = {}  # ❌ NO - hides missing config

# Environment variables
api_key = os.getenv("API_KEY") or "default_key"  # ❌ NO - hides missing var
```

#### ✅ GOOD Examples (Do this instead):

```python
# Let exceptions propagate with clear error messages
config = load_config("config.yaml")  # FileNotFoundError if missing
api_key = os.environ["API_KEY"]  # KeyError if missing

# Or provide helpful error messages
if not os.path.exists("config.yaml"):
    raise FileNotFoundError(
        "config.yaml not found. Please create it from config.yaml.template"
    )
```

#### When Fallbacks ARE Acceptable (Rare):

1. **Feature detection**: `HAS_CUDA = torch.cuda.is_available()`
2. **Explicit optional behavior**: `use_gpu = config.get("use_gpu", False)`  
3. **Graceful degradation with logging**: Log warning and use alternative

**Rationale**: Fail fast, fail loud. Silent fallbacks hide bugs, make debugging harder, and are unacceptable in production.

### Version Management

Each package manages its own version independently via `_version.py`:
```python
"""Version information for <package-name>."""
__version__ = "0.2.0"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"
```

**Architecture (L1-L5)** - CRITICAL: No upward dependencies

```
L5: sage-cli, sage-tools               # CLI & Development Tools
L4: sage-middleware                    # Operators (C++ extensions)
L3: sage-kernel, sage-libs             # Core & Algorithms
L2: sage-platform                      # Platform Services
L1: sage-common                        # Foundation
```

**独立 LLM 仓库** (已从 SAGE 核心分离):
- `sageLLM`: 统一 LLM 推理引擎，安装命令: `pip install isagellm`

**Independent Repositories** (不在 SAGE 核心仓库，独立维护):
- **sage-studio**: https://github.com/intellistream/sage-studio (Visual workflow builder)
- **sage-benchmark**: https://github.com/intellistream/sage-benchmark (Evaluation framework, 独立 PyPI: isage-benchmark)
- **sage-examples**: https://github.com/intellistream/sage-examples (Examples and applications, 原 sage-apps)

**Independent Algorithm Libraries** (L3, 从 sage-libs 拆分，独立 PyPI 包):

| 内部包名 | PyPI 包名 | Import 名 | 版本格式 | 描述 | 层级 |
|---------|----------|-----------|---------|------|------|
| sage-agentic | `isage-agentic` | `sage_libs.sage_agentic` | 0.1.x.y | Agent 实现 (ReAct, PlanExecute, Reflex) | L3 |
| sage-rag | `isage-rag` | `sage_libs.sage_rag` | 0.1.x.y | RAG 实现 (Loaders, Chunkers, Retrievers) | L3 |
| sage-privacy | `isage-privacy` | `sage_libs.sage_privacy` | 0.1.x.y | 隐私保护 (DP, 联邦学习, 机器遗忘, PII) | L3 |
| sage-eval | `isage-eval` | `sage_libs.sage_eval` | 0.1.x.y | 评估指标/Profiler/Judge | L3 |
| sage-finetune | `isage-finetune` | `sage_libs.sage_finetune` | 0.1.x.y | 微调训练器和数据加载器 | L3 |
| sage-safety | `isage-safety` | `sage_libs.sage_safety` | 0.1.x.y | 安全护栏和检测器 | L3 |
| sage-refiner | `isage-refiner` | `sage_libs.sage_refiner` | 0.1.x.y | 上下文压缩 (LongRefiner, REFORM, Provence) | L3 |

**命名规范**：
- PyPI 名称：`isage-xxx`（带 'i' 前缀，因为 'sage' 在 PyPI 已被占用）
- Import 名称：`sage_libs.sage_xxx`（使用 `sage_libs` 命名空间包，表明属于 L3 层）
- 版本格式：四段式 `0.1.0.0`，递增规则见下

**独立库与 SAGE 的关系**：
- **SAGE 侧** (`sage.libs.xxx`): 提供**接口层**（抽象基类、工厂函数、类型定义）
- **独立库** (`sage_libs.sage_xxx`): 提供**具体实现**，通过 `_register.py` 自动注册到 SAGE 工厂
- 每个独立库有 `COPILOT_INSTRUCTIONS.md` 详细说明其架构和使用方式
- 所有 L3 独立库共享 `sage_libs` 命名空间包（通过 `pkgutil.extend_path`）

**SAGE 集成**：这些库在 import 时自动注册到 SAGE interface（通过 `_register.py`）。
如果 SAGE 未安装，则作为独立库使用。

Notes:
- `sageLLM` (LLM 推理引擎) 已独立。安装: `pip install isagellm`
- `sage-edge` (optional) is an independent PyPI package `isage-edge>=0.2.4.0`. Install separately if needed.
- `sage-apps` 已迁移到 sage-examples 仓库，不再是可安装的包。
- Legacy `sage-gateway` has been superseded; do not add new code under that namespace.

**⚠️ SAGE 核心仓库不再包含 LLM 推理相关代码**。如需 LLM 功能，请安装 `pip install isagellm`。

### 🚨 sageLLM 独立仓库 - CRITICAL

**sageLLM 推理引擎已独立为私有仓库，不再作为 SAGE 子模块存在。**

- **仓库地址**：`git@github.com:intellistream/sageLLM.git`（私有仓库）
- **文档位置**：`sageLLM/docs/` 目录
- **人员分工**：`sageLLM/docs/TEAM_ASSIGNMENT.md`（私有仓库内）

**⚠️ 常见错误**：
- ❌ 不要引用 `packages/sage-llm-core/src/sage/llm/engines/sagellm`（该路径已不存在）
- ❌ 不要引用 `docs-public/docs_src/dev-notes/research_work/domestic-llm-engine/`（已迁移至 sageLLM 仓库）
- ✅ sageLLM 相关文档请引用 `sageLLM/docs/` 或说明需要访问私有仓库

**SAGE 主项目人员信息**：已迁移到私有仓库 `intellistream/sage-team-info`，不再在主仓库中维护。

**关系说明**：
- sageLLM 是 SAGE 生态的推理引擎实现，但代码独立维护
- sageLLM 仍需遵循 SAGE Control Plane 的调度协议
- SAGE 通过引擎抽象层（与 vLLM/LMDeploy 对齐）集成 sageLLM

All in `/packages/<name>/`. L5 imports L1-L4, L4 imports L1-L3, etc.

## How Copilot Should Learn SAGE (Readme-First)

When answering questions or making code changes in this repo, the assistant **must first rely on the project docs/READMEs instead of guessing**.

**Before doing any non-trivial work, Copilot should at least skim:**

- Root overview: `README.md` (features, quick start)  
- Dev workflow: `DEVELOPER.md`, `CONTRIBUTING.md`  
- Architecture: `docs-public/docs_src/dev-notes/package-architecture.md`  
- Cross-layer index: `docs-public/docs_src/dev-notes/cross-layer/README.md`

**When working on a specific layer/package, Copilot should additionally read:**

- The corresponding dev-notes README, e.g.  
  - `docs-public/docs_src/dev-notes/l1-common/README.md`  
  - `docs-public/docs_src/dev-notes/l2-platform/README.md`  
  - `docs-public/docs_src/dev-notes/l3-kernel/README.md` / `l3-libs/README.md`  
  - `docs-public/docs_src/dev-notes/l4-middleware/README.md`  
  - `docs-public/docs_src/dev-notes/l5-cli/README.md`

**🔍 When encountering difficulties or uncertainties:**

- **ALWAYS read relevant documentation in `docs-public/` first** before making assumptions
- Look for topic-specific guides in `docs-public/docs_src/dev-notes/cross-layer/` (e.g., `documentation-policy.md`, `ci-cd.md`)
- Check package-specific docs in `packages/<package-name>/README.md` or `packages/<package-name>/docs/`
- If the issue involves installation, testing, or CI/CD, consult `DEVELOPER.md` or `CONTRIBUTING.md`
- Use `grep_search` or `semantic_search` to find relevant documentation before implementing solutions

**Rule:** Don't guess architectural decisions or policies. Read the docs. They exist for this reason.

Only after consulting these READMEs should the assistant propose designs, refactors, or architectural explanations. If documentation and code appear inconsistent, Copilot should **call it out explicitly** in the answer and, when in doubt, ask the user which source of truth to follow.

## Documentation Location Policy - CRITICAL

**The root `docs/` directory is STRICTLY FORBIDDEN for committed documentation.**

### ❌ NEVER Create Files in Root `docs/`

- Root `docs/` is gitignored and must not contain committed files
- Pre-commit hooks will REJECT any commits with files in root `docs/`
- This directory should not exist in the repository
- ✅ **Exception:** Package and submodule `docs/` directories ARE ALLOWED

### ✅ CORRECT Documentation Locations

**All documentation must go to these approved locations:**

1. **User-facing docs:** `docs-public/docs_src/` (guides, tutorials, concepts)
2. **Developer notes:** `docs-public/docs_src/dev-notes/<layer>/` (architecture, design)
3. **Package docs:** `packages/<package-name>/README.md` or `packages/<package-name>/docs/`
4. **Independent repo docs:** See respective repositories (sageVDB, sageFlow, sageRefiner, sageTSDB, NeuroMem, etc.)
5. **Tool docs:** `tools/<tool-name>/README.md` or `tools/<tool-name>/docs/`
6. **Examples:** `examples/<name>/README.md`
7. **Root files:** Only `README.md`, `CONTRIBUTING.md`, `DEVELOPER.md`, `LICENSE`, `CHANGELOG.md`
8. **sageLLM docs:** 独立私有仓库 `sageLLM/docs/`（不在 SAGE 仓库内）

**Rationale:**
- Prevents confusion between root `docs/` and `docs-public/`
- Maintains single source of truth for project-level documentation
- Allows packages and tools to maintain their own documentation
- Independent repositories (PyPI packages) have their own documentation
- Tools are independent components that may have complex documentation needs
- Avoids accidental gitignore of important documentation

**Enforcement:**
- Hook `markdown-files-location-check`: Rejects any `.md` files in root `docs/` ONLY
- Hook `root-directory-cleanup-check`: Flags root `docs/` directory as unauthorized
- Package/submodule `docs/` directories are explicitly allowed and encouraged

**See:** `docs-public/docs_src/dev-notes/cross-layer/documentation-policy.md` for full policy.

## Inference Components Map (Reality-First)

SAGE is an inference pipeline system, not just an LLM server. When writing docs, abstracts, design notes, or code changes, prefer describing/using these existing modules (and their correct layer placement) instead of inventing new components.

**⚠️ LLM 推理组件已独立**：LLM 推理已移至独立仓库 `sageLLM`，以下为参考架构。

Canonical namespaces (post-refactor):
- sageLLM 推理引擎: `isagellm.*` (PyPI: `pip install isagellm`)
- Optional edge aggregator: `sage.edge.*` (独立包: `isage-edge`) - Mounts entire Gateway application
- Avoid legacy `sage.gateway.*` and `sage.llm.*` imports; they have been superseded.

**Gateway (独立仓库, OpenAI/Anthropic-compatible + control plane + sessions)**

> **Note**: 以下路径指向独立仓库 `sageLLM`，不在 SAGE 核心仓库中。
> 安装: `pip install isagellm`

- Entry point: `isagellm/gateway/server.py`
- Control plane management API: `isagellm/gateway/routes/engine_control_plane.py`
- Studio backend routes (merged into gateway): `isagellm/gateway/routes/studio.py`
- OpenAI adapter (runs persistent RAG pipeline, can trigger agentic operators):
  `isagellm/gateway/adapters/openai.py`
- Pipeline-as-a-service for RAG: `isagellm/gateway/rag_pipeline.py`
- Session + memory backends (short-term + NeuroMem VDB/KV/Graph):
  `isagellm/gateway/session/manager.py`
- Edge aggregator (optional, independent package `isage-edge`):
  Repository: https://github.com/intellistream/sage-edge
  Note: Edge mounts the complete Gateway FastAPI application, not just LLM endpoints

**Control Plane + Unified Client (独立仓库, sageLLM integration)**

> **Note**: 以下路径指向独立仓库 `sageLLM`，不在 SAGE 核心仓库中。
> 安装: `pip install isagellm`

- Unified LLM+Embedding client (must use factory):
  `isagellm/unified_client.py`
- Control plane implementation lives under:
  `isagellm/control_plane/`
- Speculative Decoding strategies (engine optimization):
  `isagellm/engines/vllm/speculative.py`
  - `SpeculativeStrategy` - Abstract base class
  - `DraftModelStrategy` - Use separate draft model (e.g., Qwen-0.5B for Qwen-7B)
  - `NgramStrategy` - N-gram based (lightweight, no extra model)
  - `DynamicLookaheadStrategy` - Research-grade dynamic lookahead adjustment
  - Import: `from isagellm import DynamicLookaheadStrategy` (需先安装 isagellm)

**Middleware inference building blocks (L4, PyPI packages with C++ extensions)**

sage-middleware depends on the following independent PyPI packages:

- **SageVDB** (`isage-vdb`): Self-developed high-performance C++ vector database
  - PyPI: `pip install isage-vdb`
  - Repository: `intellistream/sageVDB`
  - NOT FAISS-based: Fully custom implementation with FAISS-compatible API
  - Python API: `from sagevdb import SageVDB`
  - SAGE wrapper: `sage.middleware.components.sage_db.SageVDB`
  - Supports: similarity search, metadata filtering, hybrid search, batch operations
  - Integration: Used by NeuroMem VDB backend

- **SageFlow** (`isage-flow`): Vector-native stream processing engine (C++)
  - PyPI: `pip install isage-flow`
  - Repository: `intellistream/sageFlow`
  - Features: Incremental semantic state snapshots, streaming vector operations
  - SAGE wrapper: `sage.middleware.components.sage_flow`

- **NeuroMem** (`isage-neuromem`): Brain-inspired memory system
  - PyPI: `pip install isage-neuromem`
  - Repository: `intellistream/NeuroMem`
  - Features: Store/recall; VDB/KV/Graph backends; memory services
  - SAGE wrapper: `sage.middleware.components.sage_mem`

- **SageRefiner** (`isage-refiner`): Context compression for RAG
  - PyPI: `pip install isage-refiner`
  - Repository: `intellistream/sageRefiner`
  - Features: LongRefiner/REFORM/Provence adapters
  - SAGE wrapper: `sage.middleware.components.sage_refiner`

- **SageTSDB** (`isage-tsdb`): Time-series database (C++ + pybind11)
  - PyPI: `pip install isage-tsdb`
  - Repository: `intellistream/sageTSDB`
  - Features: Window ops/join, out-of-order handling
  - SAGE wrapper: `sage.middleware.components.sage_tsdb`

- **SageSIAS** (内置组件): Streaming Importance-Aware Agent System
  - 位置: `sage.middleware.components.sage_sias`
  - 功能: 样本重要性选择、持续学习、经验回放
  - 组件: `CoresetSelector`, `OnlineContinualLearner`, `SelectionSummary`
  - 依赖: NeuroMem (内存系统)
  - 使用: `from sage.middleware.components.sage_sias import CoresetSelector`
  - 注意: 放在 L4 middleware 而非 L3 libs，因为依赖 NeuroMem

**Benchmarks (L5)**

- Control plane scheduling benchmark (throughput/TTFT/TBT/p99/SLO):
  `packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/README.md`
- Agent benchmarks (tool selection / planning / timing):
  `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/README.md`

**Kernel + Libs (L3)**

- Dataflow runtime, distributed execution, fault tolerance: `packages/sage-kernel/`
- Algorithms, RAG tools, agent framework/integrations: `packages/sage-libs/`
  - **ANN Interface**: `sage.libs.anns` - Unified ANN algorithm interface
    - Base classes: `AnnIndex`, `AnnIndexMeta` (in `sage.libs.anns.interface.base`)
    - Factory: `create()`, `register()`, `registered()` (in `sage.libs.anns.interface.factory`)
    - Implementations: External package `isage-anns` (faiss_HNSW, vsag_hnsw, diskann, candy_*, cufe, gti, puck, etc.)
    - Reusable by: benchmark_anns, SageVDB, SageFlow

**Rule of thumb**: if you mention a capability (retrieval, memory, refinement, vector DB, streaming semantic state, scheduling), ensure it maps to a real module/path above.

## Installation

**Prerequisites**: Python 3.10+, Git, build-essential, cmake, pkg-config, libopenblas-dev,
liblapack-dev

**Commands** (10-25 min install):

```bash
./quickstart.sh --dev --yes        # Development (REQUIRED for dev)
./quickstart.sh --core --yes       # Minimal production
./quickstart.sh --standard --yes   # Standard with CLI
./quickstart.sh --full --yes       # Full with examples
```

Options: `--pip` (current env), `--conda` (create env), `--sync-submodules` / `--no-sync-submodules`

**Submodules** - CRITICAL: ONLY `docs-public` (SAGE-Pub) remains a git submodule. NEVER use `git submodule update --init`.

```bash
./manage.sh                        # Bootstrap docs-public + hooks
./tools/maintenance/sage-maintenance.sh submodule init    # Initialize docs-public
./tools/maintenance/sage-maintenance.sh submodule switch  # Fix detached HEAD for docs-public
```

All middleware/engine components are vendored or **pip-installed** (e.g., `isage-vdb`, `isage-benchmark`); there are no other git submodules.

**Environment**: Copy `.env.template` to `.env`, set `OPENAI_API_KEY`, `HF_TOKEN`

**Pre-commit Hooks**: `./quickstart.sh --dev` automatically installs pre-commit hooks. If missing, run:
```bash
pip install pre-commit
pre-commit install  # Install Git hooks
```

## Conda ToS Bypass - Unified Utils

**CRITICAL**: All Conda operations MUST use unified utils in `tools/lib/conda_install_utils.sh` to bypass Conda 25.x ToS restrictions.

**Core Functions**:
```bash
# Load utils (auto-loaded in most install scripts)
source "$SAGE_ROOT/tools/lib/conda_install_utils.sh"

# Install packages (auto-uses Tsinghua mirrors + --override-channels)
conda_install_bypass nodejs python=3.11 numpy

# Create environment
conda_create_bypass myenv python=3.11

# Install with progress indicator
conda_install_with_progress "安装 Node.js" nodejs

# Get mirror URL
mirror=$(get_conda_mirror "main")    # or "forge"
```

**Never use direct conda commands** without `--override-channels`:
```bash
# ❌ WRONG - will trigger ToS error
conda install -y nodejs
conda create -n myenv python=3.11 -y

# ✅ CORRECT - use unified utils
conda_install_bypass nodejs
conda_create_bypass myenv python=3.11
```

**Implementation**:
- Mirror: `https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main`
- Forge: `https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge`
- Auto-fallback: main → forge if package not found
- All install scripts pre-load these utils

## Progress Display - Unified Utils

**All long-running tasks MUST use progress indicators** from `tools/lib/progress_utils.sh`:

```bash
# Load utils
source "$SAGE_ROOT/tools/lib/progress_utils.sh"

# 1. Spinner (recommended for unknown duration)
long_command &
show_spinner $! "正在执行任务..."

# 2. Progress bar (known steps)
print_progress 50 100 "下载中..."

# 3. Long task with keepalive (30s intervals)
long_task_with_keepalive "安装系统依赖" 30 sudo apt-get install -y build-essential

# 4. Simplified wrapper (most common)
run_with_progress "安装 Node.js" conda install -y nodejs

# 5. Installation steps
show_installation_progress 2 5 "安装核心依赖"
```

**Why**: Prevents users thinking installation is frozen during long tasks (apt-get, conda install, C++ builds).

## Build, Test, Lint

**Build**: Happens during install. C++ extensions in `.sage/build/`, auto-built with `--dev`.

**Test** (ALWAYS from repo root):

```bash
sage-dev project test --coverage              # All tests
sage-dev project test --quick                 # Quick tests only
sage-dev examples test                        # Examples
pytest packages/sage-kernel/tests/unit/ -v   # Specific package
```

Config: `tools/pytest.ini`, cache: `.sage/cache/pytest/`, env: `SAGE_TEST_MODE=true`

**Lint & Format**:

```bash
sage-dev quality                              # Auto-fix
sage-dev quality --check-only                 # Check only
pre-commit run --all-files --config tools/pre-commit-config.yaml
./tools/install/check_tool_versions.sh        # Check version consistency
./tools/install/check_tool_versions.sh --fix  # Auto-fix version mismatch
```

Tools: Ruff (format+lint, line 100), Mypy (types, warning mode), Shellcheck Config:
`tools/pre-commit-config.yaml`, `tools/ruff.toml`

**Tool Version Consistency** - CRITICAL:
- `ruff` version is pinned in both `tools/pre-commit-config.yaml` (rev) and
  `packages/sage-tools/pyproject.toml` (==x.y.z) to ensure local and CI consistency.
- Run `./tools/install/check_tool_versions.sh` to verify versions match.

**Make shortcuts**: `make help`, `make test`, `make format`, `make clean`, `make docs`

## CI/CD (.github/workflows/)

**Main workflows**: build-test.yml (45m), examples-test.yml (30m), code-quality.yml (10m),
installation-test.yml, publish-pypi.yml, paper1-experiments.yml (GPU, manual)

**CI Installation Standards** - CRITICAL for new workflows:

| 场景 | 推荐安装方式 | 说明 |
|------|-------------|------|
| GitHub Actions (ubuntu-latest) | `./tools/install/core/ci_install_wrapper.sh --dev --yes` | 标准 CI，安装到 `~/.local` |
| GitHub Actions + Conda | `unset CI GITHUB_ACTIONS && ./quickstart.sh --dev --yes --pip` | 需取消 CI 变量，安装到 conda env |
| Self-hosted GPU runner (中国) | `unset CI GITHUB_ACTIONS && SAGE_FORCE_CHINA_MIRROR=true ./quickstart.sh --dev --yes --pip` | 强制使用中国镜像 |

**为什么需要 `unset CI GITHUB_ACTIONS`**：
- `quickstart.sh` 在检测到 CI 环境时会添加 `--user` 参数，安装到 `~/.local`
- 如果使用 conda 环境，需要取消这些变量让包安装到当前激活的环境

**`SAGE_FORCE_CHINA_MIRROR=true`**：
- 强制使用中国镜像（清华 PyPI + hf-mirror.com）
- 适用于位于中国的 self-hosted runner
- 会覆盖 CI 环境的默认官方源设置

**CI uses**: Ubuntu latest, Python 3.11, GitHub Secrets (OPENAI_API_KEY, HF_TOKEN), pip cache

**Replicate CI locally**:

```bash
./quickstart.sh --dev --yes
sage-dev project test --coverage --jobs 4 --timeout 300
pre-commit run --all-files --config tools/pre-commit-config.yaml
```

**CI debug**: Check job logs → Look for submodule/C++ build issues → Verify API keys → Run locally

## Key Locations

```
.github/workflows/      # CI/CD
docs-public/docs_src/dev-notes/ # Dev docs (by layer: l1-l5, cross-layer)
examples/               # apps/, tutorials/ (by layer)
packages/               # 11 packages + meta
  sage-*/src/sage/      # Source
  sage-*/tests/         # Tests (unit/, integration/)
tools/
  dev.sh                # Helper (→ sage-dev)
  maintenance/          # Submodule mgmt
  pytest.ini            # Test config
  pre-commit-config.yaml # Hooks
  ruff.toml             # Linter
.env.template           # API keys template
.pre-commit-config.yaml # → tools/pre-commit-config.yaml
.sage/                  # Build artifacts, cache, logs (gitignored, project-level)
manage.sh               # Submodule wrapper
quickstart.sh           # Installer
Makefile                # Shortcuts
```

## User Paths - XDG Standard

**CRITICAL**: User configuration and data follow [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/).

```python
from sage.common.config.user_paths import get_user_paths

paths = get_user_paths()
log_file = paths.logs_dir / "app.log"  # ~/.local/state/sage/logs/app.log
model_dir = paths.models_dir           # ~/.local/share/sage/models/
```

**Project Configuration**: Edit `config/config.yaml` and `config/cluster.yaml` directly in project root.

**Directory Structure**:
| Path | Purpose |
|------|---------|
| `config/config.yaml` | Main configuration (LLM, gateway, studio) |
| `config/cluster.yaml` | Cluster configuration (nodes, SSH, Ray) |
| `~/.local/share/sage/` | Persistent data (models, sessions, vector_db) |
| `~/.local/state/sage/` | Runtime state (logs) |
| `~/.cache/sage/` | Cached data (can be deleted) |

**Project-level** `.sage/` (gitignored): Build artifacts, pytest cache, temp files.

**DO NOT** use `~/.sage/` for new code. Use `get_user_paths()` for user data.

## Common Installation Issues

**Install hangs**: Check network, try `--resume` for checkpoint recovery (10-25min normal)
**C++ build fails**: Install deps: `build-essential cmake pkg-config libopenblas-dev liblapack-dev`
**Detached HEAD**: Use `./tools/maintenance/sage-maintenance.sh submodule switch`
**Tests fail CI not local**: Run `sage-dev project test --coverage` from repo root
**Import errors**: Must use `--dev` install, run from repo root
**Pre-commit fails**: Run `sage-dev quality` to auto-fix
**Old artifacts**: `make clean` or `rm -rf .sage/build/ build/ dist/ *.egg-info/`
**Bash exclamation mark**: NEVER use `!` in terminal commands (causes `bash: !': event not found`).
  Use period `.` instead: `print("Done.")` not `print("Done!")`

## Port Configuration - CRITICAL

**统一端口配置**: 所有端口号必须使用 `sage.common.config.ports.SagePorts`，禁止硬编码。

```python
from sage.common.config.ports import SagePorts

# ✅ 正确用法
port = SagePorts.LLM_DEFAULT           # 8001
gateway_port = SagePorts.GATEWAY_DEFAULT  # 8889

# ✅ WSL2 环境推荐用法
port = SagePorts.get_recommended_llm_port()  # 自动检测 WSL2 并选择合适端口

# ❌ 错误用法 - 禁止硬编码
port = 8001  # 不要这样写
```

**端口分配表**:
| 常量 | 端口 | 用途 |
|------|------|------|
| `GATEWAY_DEFAULT` | 8889 | isage-llm-gateway (OpenAI 兼容 API Gateway，独立包) |
| `EDGE_DEFAULT` | 8899 | isage-edge 聚合器（独立包，挂载整个 Gateway 应用） |
| `LLM_DEFAULT` | 8001 | vLLM 推理服务 |
| `LLM_WSL_FALLBACK` | 8901 | WSL2 备用 LLM 端口 |
| `STUDIO_BACKEND` | 8889| sage-studio 后端 API（独立仓库） |
| `STUDIO_FRONTEND` | 5173 | sage-studio 前端 (Vite，独立仓库) |
| `EMBEDDING_DEFAULT` | 8090 | Embedding 服务 |
| `BENCHMARK_LLM` | 8901 | Benchmark 专用 LLM 端口 |

**架构**: `User → [Edge (8899, 可选) →] Gateway (8889) → Control Plane → LLM (8001)`（Edge 挂载整个 Gateway 应用，保持 /v1/* 路径；未启动 Edge 时直接访问 Gateway）

> **Note**: Gateway 和 Edge 现在是独立 PyPI 包，需单独安装。

**WSL2 已知问题**:
- 端口 8001 在 WSL2 上可能出现"端口监听但连接被拒绝"的问题
- 使用 `SagePorts.get_recommended_llm_port()` 自动选择合适端口
- 或直接使用 `SagePorts.BENCHMARK_LLM` (8901) 作为备用

**配置文件位置**: `packages/sage-common/src/sage/common/config/ports.py`

## API Client Usage - CRITICAL

**UnifiedInferenceClient must be created via the factory** (direct instantiation is intentionally blocked).

```python
from sage.llm import UnifiedInferenceClient

client = UnifiedInferenceClient.create()
```

If you see code attempting `UnifiedInferenceClient(...)`, treat it as a bug and refactor to `create()`.

## Dependency Management - CRITICAL

**Rule**: All dependency versions MUST be unified across packages to avoid [DEDUP] warnings.

**Single Source of Truth**: `dependencies-spec.yaml` at project root
- Defines unified versions for torch, transformers, fastapi, uvicorn, etc.
- Documents historical conflicts and resolution strategies
- Guides future updates

**Tools**:
- `tools/scripts/check_dependency_consistency.py` - Auto-check version consistency
- `tools/scripts/unify_dependencies.sh` - Batch update tool

**vLLM Dependencies** (重量级可选依赖):
- `vllm-minimal` - vLLM only (for users with existing torch >= 2.7.0)
- `vllm` - Full install (includes torch >= 2.7.0)
- `torch` - Standalone torch (for other components)

**Smart Installation**:
- Detects existing torch version
- Chooses `vllm-minimal` if torch >= 2.7.0 (reuse existing)
- Chooses `vllm` if torch missing or < 2.7.0 (install/upgrade)

**Conflict Resolution**:
- `environment_doctor.sh` detects conda/pip mixed management
- `fix_mixed_packages()` intelligently resolves version conflicts
- Preserves higher version, removes lower version

**Docs**: `docs-public/docs_src/dev-notes/cross-layer/vllm-dependency-management.md`

## Features

**CPU Node Support**: SAGE fully supports CPU-only compute nodes via JobManager + NodeSelector.
Tasks can specify `cpu_required`, `memory_required`, `gpu_required=0` for CPU-only execution. See
`examples/tutorials/L3-kernel/cpu_node_demo.py` and `docs/dev-notes/l3-kernel/cpu-node-setup.md`.

## Development Workflow

**Setup**: `./quickstart.sh --dev --yes` → `./manage.sh` (if C++ needed)
**During**: Run `sage-dev project test`, `sage-dev quality` frequently
**Before commit**: `sage-dev quality --check-only`, `sage-dev project test --coverage`
**Commits**: `<type>(<scope>): <summary>` (types: feat, fix, refactor, docs, test, ci, etc.)
**PR**: Local CI checks first, update CHANGELOG.md, reference issues

**Critical files** (review before modifying): quickstart.sh, manage.sh, .github/workflows/,
tools/pytest.ini, tools/pre-commit-config.yaml

## PyPI Publishing - CRITICAL: Use sage-pypi-publisher

**SAGE 有专用的独立 PyPI 发布工具仓库。NEVER 手动使用 twine 或 build。**

**Repository**: [intellistream/sage-pypi-publisher](https://github.com/intellistream/sage-pypi-publisher) (独立仓库)

### Publishing Commands

PyPI 发布功能已迁移到独立的 `sage-pypi-publisher` 仓库。使用方法：

```bash
# Clone 发布工具仓库
git clone https://github.com/intellistream/sage-pypi-publisher.git
cd sage-pypi-publisher

# 自动版本递增并发布（推荐）
./publish.sh <package-name> --auto-bump patch  # 递增 0.0.1
./publish.sh <package-name> --auto-bump minor  # 递增 0.1.0
./publish.sh <package-name> --auto-bump major  # 递增 1.0.0

# 指定版本发布
./publish.sh <package-name> --version 0.2.5

# 发布到 TestPyPI（测试）
./publish.sh <package-name> --test-pypi --auto-bump patch

# 查看帮助
./publish.sh --help
```

**Note**:
- 该工具自动处理版本递增、构建、上传全流程
- 支持批量发布多个包
- 集成 pre-commit hooks 自动化发布（见下文）

### Package Names

SAGE 的 PyPI 包名与内部包名不同：

| 内部包名 | PyPI 包名 | 用途 |
|---------|----------|------|
| `sage-common` | `isage-common` | L1 Foundation |
| `sage-libs` | `isage-libs` | L3 Algorithms & ANNS |

**已独立的 LLM 包** (不在 SAGE 核心仓库):
| 包名 | PyPI 包名 | 用途 |
|------|----------|------|
| `sageLLM` | `isagellm` | 统一 LLM 推理引擎 (含 Control Plane, Gateway) |

### Pre-publish Checklist

1. **Run tests**: `sage-dev project test --coverage` (在 SAGE 仓库)
2. **Run quality checks**: `sage-dev quality --check-only` (在 SAGE 仓库)
3. **Update CHANGELOG.md**: 记录本次发布的变更
4. **Clone publisher**: `git clone https://github.com/intellistream/sage-pypi-publisher.git`
5. **Test on TestPyPI**: `cd sage-pypi-publisher && ./publish.sh <package> --test-pypi --auto-bump patch`
6. **Verify installation**: `pip install -i https://test.pypi.org/simple/ isage-<package>`
7. **Publish to PyPI**: `./publish.sh <package> --auto-bump patch`

**Note**: `sage-pypi-publisher` 会自动：
- 检测当前版本并递增
- 更新 `_version.py` 文件
- 构建 wheel 包
- 上传到 PyPI/TestPyPI

### Configuration

PyPI tokens 应配置在 `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-xxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxx
```

### Automated Publishing via Git Hooks

**自动化发布** (推荐): 通过 post-commit hook 自动发布受影响的包

在 `.git/hooks/post-commit` 中添加：

```bash
#!/bImplementation Details

- **Repository**: [intellistream/sage-pypi-publisher](https://github.com/intellistream/sage-pypi-publisher)
- **Tool**: `publish.sh` - 统一发布脚本
- **Features**:
  - 自动版本递增 (patch/minor/major)
  - 智能包检测和依赖管理
  - TestPyPI 测试支持
  - 批量发布多个包
- **Safety**: 默认需要确认，可用 `--no-dry-run` 跳过

### PyPI Publishing Issues

**问题**: `ruamel.yaml.clib` 编译失败
- **原因**: 某些依赖（如 vllm）需要 ruamel.yaml，但 C 扩展编译可能失败
- **解决**: 通常可忽略，使用纯 Python fallback。如必须修复，检查编译器和 Python 头文件

**问题**: 版本号不一致
- **检查**: `./tools/install/check_tool_versions.sh` (在 SAGE 仓库)
- **修复**: `./tools/install/check_tool_versions.sh --fix`

**问题**: 发布工具找不到
- **原因**: `sage-pypi-publisher` 需要单独克隆
- **解决**: `git clone https://github.com/intellistream/sage-pypi-publisher.git
fi

# 检测修改的包
affected_packages=$(git diff HEAD~1 HEAD --name-only | \
    grep '^packages/' | \
    cut -d'/' -f2 | \
    sort -u)

if [ -z "$affected_packages" ]; then
    echo "✅ No packages affected"
    exit 0
fi

echo "📦 Affected packages: $affected_packages"
echo "🚀 Auto-publishing to PyPI..."

cd "$PUBLISHER_PATH"
for pkg in $affected_packages; do
    echo "Publishing $pkg..."
    ./publish.sh "$pkg" --auto-bump patch --no-dry-run
done
```

**Note**:
- 可配置为仅在特定分支（如 `main`）触发
- 可添加交互式确认避免误发布
- 建议先在 test-pypi 验证

### PyPI Publishing Issues

**问题**: `ruamel.yaml.clib` 编译失败
- **原因**: 某些依赖（如 vllm）需要 ruamel.yaml，但 C 扩展编译可能失败
- **解决**: 通常可忽略，使用纯 Python fallback。如必须修复，检查编译器和 Python 头文件

**问题**: 版本号不一致
- **检查**: `./tools/install/check_tool_versions.sh`
- **修复**: `./tools/install/check_tool_versions.sh --fix`

## Resources

- Architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
- Guides: `CONTRIBUTING.md` (CN), `DEVELOPER.md` (EN)
- Dev notes: `docs/dev-notes/` (l1-l5, cross-layer/ci-cd/)

## LLM & Embedding Services - sageLLM 架构

**设计原则**: 统一调度，资源共享。所有 LLM 和 Embedding 请求通过 **sageLLM Control Plane** 统一管理。

### 架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (Application Layer)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                      UnifiedInferenceClient                              │
│                 chat() | generate() | embed()                            │
│                    Control Plane Mode (唯一模式)                         │
│              （所有请求通过调度器统一路由）                               │
├─────────────────────────────────────────────────────────────────────────┤
│                 isagellm.gateway (独立仓库 Gateway)                         │
│              (OpenAI-Compatible REST API + Control Plane)               │
│   /v1/chat/completions | /v1/embeddings | /v1/management/* | /sessions │
├─────────────────────────────────────────────────────────────────────────┤
│                    sageLLM Control Plane (核心)                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  RequestClassifier (LLM_CHAT / LLM_GENERATE / EMBEDDING)        │   │
│   │  HybridSchedulingPolicy (请求分组、优先级、批处理聚合)            │   │
│   │  ExecutionCoordinator (LLM) | EmbeddingExecutor (Embedding)     │   │
│   └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                        统一资源池 (GPU Pool)                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│   │  vLLM Instance  │  │  vLLM Instance  │  │  Embedding Srv  │        │
│   │  (LLM Only)     │  │  (LLM+Embed)    │  │  (Embed Only)   │        │
│   │  Type: GENERAL  │  │  Type: MIXED    │  │  Type: EMBEDDING│        │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

*可选 Edge 层*: `isage-edge` (8899, 独立包) 挂载整个 `sage.llm.gateway` 应用（包含 Control Plane、RAG Pipeline、Session Management）。默认挂载在 `/`（保持 `/v1/*` 兼容），或使用 `--llm-prefix` 挂载在自定义前缀。未启动 edge 时，直接访问 Gateway 即可。安装: `pip install isage-edge`

### 推荐用法：Control Plane 模式

```python
from sage.llm import UnifiedInferenceClient

# 默认（推荐）: 自动检测本地/远端端点，优先本地
client = UnifiedInferenceClient.create()

# 外部 Control Plane: 指向已运行的 Control Plane/Gateway
client = UnifiedInferenceClient.create(
  control_plane_url="http://127.0.0.1:8888/v1",
  default_llm_model="Qwen/Qwen2.5-7B-Instruct",
  default_embedding_model="BAAI/bge-m3",
)

# 内嵌 Control Plane: 在当前进程启动调度器（实验性，适合离线批处理）
# embedded mode deprecated; use control_plane_url instead

### 启动服务栈

```bash
# 推荐：启动 Gateway（包含 Control Plane）
sage gateway start                                 # 启动 Gateway（端口 8888）
sage gateway status                                # 查看 Gateway 状态
sage gateway stop                                  # 停止 Gateway
sage gateway logs --follow                         # 查看日志

# 引擎管理（通过 Gateway Control Plane）
sage llm engine start Qwen/Qwen2.5-7B-Instruct --engine-kind llm    # 启动 LLM 引擎
sage llm engine start BAAI/bge-m3 --engine-kind embedding           # 默认 CPU
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu # 使用 GPU
sage llm engine list                                                 # 查看引擎列表
sage llm engine stop <engine-id>                                     # 停止引擎

# 查看运行状态
ps aux | grep -E "vllm|embedding_server"
```

### Embedding 引擎 GPU 支持

默认情况下，Embedding 引擎运行在 CPU 上。对于大型 Embedding 模型（如 BGE-M3），可以显式启用 GPU：

```python
# CLI 方式
# sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu

# 预设文件 (preset.yaml)
engines:
  - name: embed-gpu
    kind: embedding
    model: BAAI/bge-m3
    use_gpu: true  # 显式使用 GPU
```

**`use_gpu` 参数行为**：
- `use_gpu=None` (默认): LLM 使用 GPU，Embedding 不使用
- `use_gpu=True`: 强制使用 GPU
- `use_gpu=False`: 强制不使用 GPU（即使是 LLM）

### Control Plane 核心组件

| 组件 | 位置 | 功能 |
|------|------|------|
| `ControlPlaneManager` | `isagellm.control_plane.manager` | 核心调度管理器 |
| `RequestClassifier` | `isagellm.control_plane.request_classifier` | 请求类型分类 |
| `HybridSchedulingPolicy` | `isagellm.control_plane.strategies.hybrid_policy` | 混合调度策略 |
| `EmbeddingExecutor` | `isagellm.control_plane.executors.embedding_executor` | Embedding 批处理 |
| `ControlPlaneService` | `isagellm.control_plane_service` | Control Plane SAGE 封装 |

> **Note**: 以上组件来自独立仓库 `sageLLM`，需单独安装：`pip install isagellm`

### 关键文件位置

> **Note**: LLM 相关代码已移至独立仓库 `sageLLM`，以下路径仅供参考。

**sageLLM (独立仓库, PyPI: isagellm)**:
```
isagellm/
  unified_client.py         # UnifiedInferenceClient (factory-only construction)
  control_plane_service.py  # Control Plane facade
  control_plane/            # Control Plane core implementation
    manager.py              # 调度管理器
    request_classifier.py   # 请求分类器
    strategies/hybrid_policy.py  # LLM + Embedding 混合调度
    executors/embedding_executor.py # Embedding 批处理执行
  gateway/
    server.py               # FastAPI 应用入口 (OpenAI/Anthropic-compatible)
    routes/
      engine_control_plane.py # Control Plane 管理 API
      llm.py                # LLM 代理
      embedding.py          # Embedding 代理
      studio.py             # Studio backend routes (merged)
      sessions.py           # 会话管理
    adapters/openai.py      # OpenAI adapter
    rag_pipeline.py         # Pipeline-as-a-service
    session/manager.py      # Session + memory backends
```

**isage-edge (独立仓库)**:
```
Repository: https://github.com/intellistream/sage-edge
PyPI: https://pypi.org/project/isage-edge/
Install: pip install isage-edge
```

**SAGE Core (sage-common)**:
```
packages/sage-common/src/sage/common/components/
  sage_embedding/
    embedding_server.py     # OpenAI 兼容 Embedding 服务器
    factory.py              # EmbeddingFactory (本地模型)
```

### 客户端模式对比（统一 Control Plane）

> Simple 模式已移除；所有请求都经由 Control Plane。
> **Note**: 以下功能需要安装独立包 `isagellm`。

| 模式 | 创建方式 | 调度 | 适用场景 |
|------|----------|------|---------|
| 自动检测 | `UnifiedInferenceClient.create()` | 自动探测本地/远端端点，统一调度 | 默认推荐（本地开发、单机实验） |
| 外部 Control Plane | `UnifiedInferenceClient.create(control_plane_url=...)` | 通过已运行的 Control Plane/Gateway 路由 | 生产部署、网关统一入口 |
| 内嵌 Control Plane (deprecated) | 使用 control_plane_url 或本地 Gateway | 在进程内启动调度器 | 离线批处理/无外部服务时 |

### 内嵌模式 (VLLMService) - 批处理专用

```python
from sage.llm import VLLMService

# 进程内加载模型，适合批处理任务
service = VLLMService({
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "auto_download": True,
})
service.setup()  # 加载模型到 GPU
results = service.generate("Hello, world!")
service.teardown()
```

### 环境变量 (.env)

```bash
# === 本地服务（推荐，默认）===
# 无需配置，使用 SagePorts 默认端口
# UnifiedInferenceClient 会自动探测 localhost:8001, localhost:8901

# === 显式远端覆盖（仅当需要强制使用云端API时设置）===
# 警告：仅用于显式远端覆盖，不是默认行为
# 本地开发应始终使用本地端点，不要依赖云端 fallback
SAGE_CHAT_API_KEY=sk-xxx              # 云端 API Key (DashScope/OpenAI compatible)
SAGE_CHAT_MODEL=qwen-turbo-2025-02-11
SAGE_CHAT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# === HuggingFace ===
HF_TOKEN=hf_xxx
# HF_ENDPOINT 无需手动设置，SAGE 会自动检测网络并配置镜像
```

> **CRITICAL**: DashScope/云端变量**仅用于显式远端覆盖**，不是默认行为。
> - **本地优先**：默认探测 `localhost:8001` 和 `localhost:8901`
> - **无隐式 fallback**：如果本地端点不可达，会**快速失败**，不会自动切换到云端
> - **显式覆盖**：仅当设置了 `SAGE_CHAT_BASE_URL` 时才使用远端
> - **CI 环境**：GitHub Actions 在无本地服务时使用 DashScope fallback（CI only）

### 网络检测和 HuggingFace 镜像自动配置

SAGE 会在运行时自动检测网络区域，如果检测到中国大陆网络，会自动设置 `HF_ENDPOINT=https://hf-mirror.com`。

```python
from sage.common.config import (
    detect_china_mainland,      # 检测是否在中国大陆
    get_hf_endpoint,            # 获取推荐的 HF endpoint
    ensure_hf_mirror_configured,  # 自动配置 HF 镜像（推荐在 CLI 命令入口调用）
)

# 检测网络区域
is_china = detect_china_mainland()  # True/False

# 自动配置（如果在中国大陆，设置 HF_ENDPOINT 环境变量）
ensure_hf_mirror_configured()  # 只会在首次调用时检测，结果会缓存
```

**自动配置的命令**：
- `sage llm engine start` - 启动 LLM/Embedding 引擎
- `sage llm model download` - 下载模型
- `sage llm fine-tune` - 微调模型
- Embedding 相关服务

### EmbeddingFactory (本地模型，无需服务)

用于不想启动 Embedding 服务的场景：

```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory, EmbeddingClientAdapter
)

# 本地加载 HuggingFace 模型
raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
client = EmbeddingClientAdapter(raw_embedder)  # 适配为批量接口
vectors = client.embed(["文本1", "文本2"])
```

**接口对比**:
| 接口 | 签名 | 来源 |
|------|------|------|
| 单文本 (BaseEmbedding) | `embed(text: str) -> list[float]` | `EmbeddingFactory.create()` |
| 批量 (EmbeddingProtocol) | `embed(texts: list[str], model=None) -> list[list[float]]` | `EmbeddingClientAdapter` |

**错误示例** (会导致运行时错误):
```python
# 错误: EmbeddingFactory 返回的是单文本接口
embedder = EmbeddingFactory.create("hf", model="...")
embedder.embed(texts=["a", "b"])  # TypeError: embed() got unexpected keyword argument 'texts'
```

## sage-benchmark (独立仓库)

**sage-benchmark has been separated into an independent repository**: https://github.com/intellistream/sage-benchmark

Comprehensive evaluation framework for AI data processing pipelines, including:
- **benchmark_agent**: Agent capability evaluation (tool selection, task planning, timing judgment)
- **benchmark_control_plane**: Control Plane scheduling strategy evaluation
- **benchmark_memory**: Memory system evaluation
- **benchmark_rag**: RAG pipeline evaluation
- **benchmark_refiner**: Context compression evaluation
- **benchmark_anns**: ANNS algorithm evaluation
- **benchmark_amm**: Approximate matrix multiplication evaluation

To use sage-benchmark:
```bash
pip install isage-benchmark
```

For detailed documentation, see the [sage-benchmark repository](https://github.com/intellistream/sage-benchmark).

## SageVDB Vector Database Backend

### 🚨 SageVDB 已独立 - CRITICAL

**SageVDB 已独立为 `isage-vdb` PyPI 包，不再作为 SAGE 子模块存在。**

- **PyPI 包名**: `isage-vdb` (带连字符和 'i' 前缀，因为 'sage' 在 PyPI 已被占用)
- **Python 导入名**: `sagevdb` (不带 'i'，不带连字符)
- **安装方式**: `pip install isage-vdb`
- **仓库地址**: `https://github.com/intellistream/sageVDB`
- **迁移文档**: `docs-public/docs_src/dev-notes/cross-layer/sagedb-independence-migration.md`

**⚠️ 无向后兼容**: 迁移后子模块和 python/ 目录将被完全移除。

**导入方式**:
```python
# ✅ 推荐：直接从 isage-vdb 导入
from sagevdb import SageVDB, IndexType, DistanceMetric

# ✅ 或通过 SAGE 兼容层
from sage.middleware.components.sage_db import SageDB
```

### Overview

SageVDB is a **self-developed high-performance C++ vector database**, fully custom implementation (NOT based on FAISS), with FAISS-compatible API.

**Features**:
- ✅ Self-developed C++ core (independent implementation)
- ✅ **FAISS-compatible API** (drop-in replacement)
- ✅ High-performance similarity search (C++ optimized)
- ✅ Metadata filtering (`filtered_search`, `search_by_metadata`)
- ✅ Hybrid search (vector + text)
- ✅ Batch operations with numpy optimization
- ✅ Persistent storage (save/load)
- ✅ Multiple index types (AUTO, FLAT, IVF, HNSW)
- ✅ Distance metrics (L2, INNER_PRODUCT, COSINE)

### Location

**独立包**:
- PyPI: `pip install isage-vdb`
- 仓库: `https://github.com/intellistream/sageVDB`

**SAGE 兼容层** (保留):
- 重导出: `packages/sage-middleware/src/sage/middleware/components/sage_db/__init__.py`
- 适配器: `packages/sage-middleware/src/sage/middleware/components/sage_db/backend.py`
- NeuroMem 集成: `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/search_engine/vdb_index/sagedb_index.py`

### Usage in NeuroMem VDB Collections

**Creating a VDB collection with SageVDB backend**:

```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

manager = MemoryManager()

# Create collection
collection = manager.create_collection({
    "name": "my_collection",
    "backend_type": "VDB"
})

# Create SageVDB index
collection.create_index({
    "name": "my_index",
    "dim": 1024,
    "backend_type": "SageVDB",  # Use SageVDB instead of FAISS
    "description": "High-performance SageVDB index"
})

# Insert vectors
collection.insert("my_index", text="example text", vector=embedding_vector)

# Search
results = collection.search("my_index", query_vector, top_k=10)
```

**Gateway Session Storage Configuration**:

```python
# In packages/sage-llm-gateway/src/sage/llm/gateway/session/manager.py

# Default: FAISS backend
index_config = {
    "backend_type": "FAISS",  # Python FAISS
    ...
}

# Optimized: SageVDB backend (C++ performance)
index_config = {
    "backend_type": "SageVDB",  # C++ optimized
    ...
}
```

**Current Status** (2025-12-28):
- ✅ SageVDB backend registered in VDB index factory
- ✅ SageVDBIndex adapter implements all BaseVDBIndex methods
- ✅ Tests pass: insert, batch_insert, search, delete, update
- ⚠️ Gateway default remains FAISS (change to "SageVDB" to use C++ backend)

**Performance Characteristics** (5000 vectors, dim=128):
- ✅ **Insert**: SageVDB 10x faster (single), 1.14x faster (batch) - C++ optimized write path
- ⚠️ **Search**: FAISS 2.8-3x faster across all k values (Python wrapper overhead in current implementation)
- ➡️ **Memory**: Nearly identical (~945 MB)
- ✅ **ANNS Algorithms**: Now available in `sage-libs/anns/` for modularity

**When to use SageVDB**:
- Write-heavy workloads (frequent insertions/updates)
- Session storage with many new messages
- Real-time chat applications
- When insert latency is critical
- Custom C++ extensions and integrations

**When to use FAISS**:
- Read-heavy workloads (frequent similarity searches)
- Large-scale retrieval systems
- When search latency is critical
- Production RAG pipelines with high QPS

### Direct SageVDB API

**Important**: SageVDB is a self-developed C++ vector database with FAISS-compatible API.

```python
# 迁移后（推荐）
from sagevdb import SageVDB, IndexType, DistanceMetric

# 或通过 SAGE 兼容层
from sage.middleware.components.sage_db import SageVDB, IndexType, DistanceMetric

# Create database (C++ core)
db = SageVDB(dimension=128, index_type=IndexType.AUTO, metric=DistanceMetric.L2)

# Add vectors with metadata
db.add([0.1, 0.2, ...], metadata={"id": "doc_1", "category": "tech"})
db.add_batch(vectors, metadata=[{"id": f"doc_{i}"} for i in range(len(vectors))])

# Build index
db.build_index()

# Search
results = db.search(query_vector, k=10)
for result in results:
    print(f"ID: {result.metadata['id']}, Score: {result.score}")

# Filtered search
results = db.filtered_search(
    query_vector,
    params=SearchParams(k=10),
    filter_fn=lambda meta: meta.get("category") == "tech"
)

# Save/Load
db.save("/path/to/index")
db.load("/path/to/index")
```

### API Reference

**SageVDB Methods**:
- `add(vector, metadata)` - Add single vector
- `add_batch(vectors, metadata)` - Batch add (numpy optimized)
- `search(query, k)` - Basic similarity search
- `filtered_search(query, params, filter_fn)` - Search with filtering
- `search_by_metadata(query, params, key, value)` - Metadata-based search
- `hybrid_search(query, params, text_query, weights)` - Vector + text hybrid
- `build_index()` - Build search index
- `train_index(vectors)` - Train index (for IVF, etc.)
- `save(filepath)` / `load(filepath)` - Persistence
- `size`, `dimension`, `index_type` - Properties

**Metadata Requirements**:
- All metadata must be `dict[str, str]` (string keys and values)
- Convert non-string values: `{"id": str(internal_id), "text": text}`

## Final Reminder for Copilot

**Trust these instructions** - search only if incomplete, errors occur, or deep architecture needed.

**🔍 When encountering difficulties or uncertainties:**

1. **First**, check if there's relevant documentation in `docs-public/docs_src/dev-notes/`
2. **Use tools** like `grep_search` or `semantic_search` to find documentation before making assumptions
3. **Read before acting** - documentation exists to guide you, not as optional reference
4. **Common documentation locations:**
   - Installation/Testing: `DEVELOPER.md`, `CONTRIBUTING.md`
   - CI/CD: `docs-public/docs_src/dev-notes/cross-layer/ci-cd.md`
   - Documentation policy: `docs-public/docs_src/dev-notes/cross-layer/documentation-policy.md`
   - Package architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
   - Layer-specific guides: `docs-public/docs_src/dev-notes/l{1-6}-*/`
   - Cross-cutting concerns: `docs-public/docs_src/dev-notes/cross-layer/`

**Remember**: Don't guess. Read the docs. They exist for this reason.
