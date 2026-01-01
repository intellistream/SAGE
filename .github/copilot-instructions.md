# SAGE Copilot Instructions

## Overview

**SAGE** is a Python 3.10+ framework for building AI/LLM data processing pipelines with declarative
dataflow. 11 functional packages + 1 meta-package, ~400MB dev install, uses C++ extensions (CMake).

## 🚨 CRITICAL Architectural Constraints

### ❌ NEVER BYPASS CONTROL PLANE - ABSOLUTE RULE

**ALL LLM engine operations MUST go through Control Plane. Direct engine startup is FORBIDDEN.**

This is a **non-negotiable architectural constraint**. Violating this breaks resource management, scheduling, and monitoring.

#### ❌ FORBIDDEN Operations:

**1. Direct LLM service startup:**
```bash
sage llm serve -m Qwen/Qwen2.5-7B-Instruct        # ❌ FORBIDDEN
python -m vllm.entrypoints.openai.api_server      # ❌ FORBIDDEN
python -m sage.common.components.sage_embedding   # ❌ FORBIDDEN
```

**2. Direct vLLM/HF imports in user code:**
```python
from vllm import LLM  # ❌ FORBIDDEN - use UnifiedInferenceClient
engine = LLM(model="...")  # ❌ FORBIDDEN
```

**3. Bypassing Gateway:**
```python
# ❌ FORBIDDEN - direct endpoint access
requests.post("http://localhost:8001/v1/chat/completions", ...)  # allow-control-plane-bypass: example only
```

#### ✅ CORRECT Operations (Control Plane):

**1. Engine management through Control Plane:**
```bash
# ✅ CORRECT - managed by Control Plane
sage llm engine start Qwen/Qwen2.5-7B-Instruct --engine-kind llm
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu
sage llm engine list
sage llm engine stop <engine-id>
```

**2. Unified client (auto-routes through Control Plane):**
```python
# ✅ CORRECT - uses Control Plane routing
from sage.llm import UnifiedInferenceClient
client = UnifiedInferenceClient.create()
response = client.chat([{"role": "user", "content": "Hello"}])
```

**3. Gateway API (Control Plane frontend):**
```python
# ✅ CORRECT - goes through Gateway → Control Plane
import requests
resp = requests.post("http://localhost:8888/v1/chat/completions", ...)  # allow-control-plane-bypass: Gateway port
```

#### Why This Matters:

- **Resource Management**: Control Plane tracks GPU memory, prevents OOM
- **Load Balancing**: Distributes requests across multiple engines
- **Fault Tolerance**: Automatic failover and retry
- **Monitoring**: Centralized metrics and logging
- **Scheduling**: SLO-aware request routing

#### Enforcement:

- **Pre-commit hooks**: Block commits with `sage llm serve`, `sage llm run`, or direct vLLM calls
- **CI/CD**: All workflows use Control Plane APIs
- **Code review**: Reject PRs with direct engine startup
- **Commands removed**: `sage llm serve/run/stop/restart/status/logs` have been completely deleted

## CRITICAL Coding Principles

### ❌ NO FALLBACK LOGIC - PROJECT-WIDE RULE
**NEVER use try-except fallback patterns anywhere in the codebase.**

This is a **project-wide principle**, not just for version management. Fallbacks hide problems and make debugging harder.

#### ❌ BAD Examples (Do NOT do this):

**1. Version imports:**
```python
try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"  # ❌ NO
```

**2. Configuration loading:**
```python
try:
    config = load_config("config.yaml")
except FileNotFoundError:
    config = {}  # ❌ NO - hides missing config file
```

**3. Module imports:**
```python
try:
    import optional_module
except ImportError:
    optional_module = None  # ❌ NO - use explicit dependency checking instead
```

**4. Environment variables:**
```python
api_key = os.getenv("API_KEY") or "default_key"  # ❌ NO - hides missing env var
```

**5. File operations:**
```python
try:
    with open("file.txt") as f:
        data = f.read()
except FileNotFoundError:
    data = ""  # ❌ NO - hides missing file
```

#### ✅ GOOD Examples (Do this instead):

**1. Version imports (namespace packages):**
```python
# Direct file reading - will raise FileNotFoundError if missing
import os
_current_dir = os.path.dirname(os.path.abspath(__file__))
_version_file = os.path.join(_current_dir, "_version.py")
_version_globals = {}
with open(_version_file) as f:
    exec(f.read(), _version_globals)
__version__ = _version_globals["__version__"]  # Will raise KeyError if missing
```

**2. Configuration loading:**
```python
# Fail fast if config missing
config = load_config("config.yaml")  # Let FileNotFoundError propagate
# Or provide clear error message
if not os.path.exists("config.yaml"):
    raise FileNotFoundError(
        "config.yaml not found. Please create it from config.yaml.template"
    )
```

**3. Optional dependencies:**
```python
# Explicitly check and document the requirement
try:
    import vllm
except ImportError as e:
    raise ImportError(
        "vLLM is required for this feature. Install with: pip install vllm"
    ) from e
```

**4. Environment variables:**
```python
# Fail fast if required env var missing
api_key = os.environ["API_KEY"]  # Will raise KeyError if missing
# Or provide clear error message
if "API_KEY" not in os.environ:
    raise EnvironmentError(
        "API_KEY environment variable is required. Set it in .env file"
    )
```

**5. File operations:**
```python
# Let exceptions propagate - makes problems visible
with open("required_file.txt") as f:
    data = f.read()  # Will raise FileNotFoundError if missing
```

#### When Fallbacks ARE Acceptable (Rare Cases):

Only use fallbacks when:
1. **Feature detection** (check if optional feature is available):
   ```python
   HAS_CUDA = torch.cuda.is_available()  # ✓ OK - explicit feature check
   ```

2. **Explicit optional behavior** (documented and intentional):
   ```python
   # ✓ OK - clearly documented as optional
   use_gpu = config.get("use_gpu", False)  # Default to CPU if not specified
   ```

3. **Graceful degradation** (with clear logging):
   ```python
   # ✓ OK - logs the issue and provides alternative
   try:
       fast_impl = import_fast_implementation()
   except ImportError:
       logger.warning("Fast implementation not available, using slow fallback")
       fast_impl = slow_implementation
   ```

#### Rationale:

- **Fail fast, fail loud**: Problems should be visible immediately during development
- **No hidden bugs**: Silent fallbacks hide configuration errors, missing files, broken imports
- **Better error messages**: Explicit checks can provide helpful error messages
- **Easier debugging**: Stack traces point to the real problem
- **Production safety**: "unknown" versions, empty configs, or missing dependencies are unacceptable

#### What to do instead:

1. **Let exceptions propagate** - don't catch them unless you have a specific reason
2. **Validate early** - check requirements at startup, not during runtime
3. **Provide clear error messages** - tell users exactly what's wrong and how to fix it
4. **Document dependencies** - make optional dependencies explicit in docs
5. **Use assertions** - for internal invariants that should never fail

### Version Management

Each package manages its own version independently via `_version.py`:
```python
"""Version information for <package-name>."""
__version__ = "0.2.0"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"
```

**Architecture (L1-L6)** - CRITICAL: No upward dependencies

```
L6: sage-cli, sage-studio, sage-tools, sage-llm-gateway, sage-edge  # Interfaces & gateways
L5: sage-apps, sage-benchmark          # Apps & Benchmarks  
L4: sage-middleware                    # Operators (C++ extensions)
L3: sage-kernel, sage-libs             # Core & Algorithms
L2: sage-platform                      # Platform Services
L1: sage-common, sage-llm-core         # Foundation & LLM control plane/client
```

Notes:
- `sage-llm-gateway` is published to PyPI as `isage-llm-gateway` (OpenAI/Anthropic-compatible API Gateway).
- `sage-llm-core` is published to PyPI as `isage-llm-core` (Unified client + control plane).
- `sage-edge` is an opt-in aggregator shell that can mount the LLM gateway; behavior is unchanged unless it is explicitly started.
- Legacy `sage-gateway` has been superseded; do not add new code under that namespace.

All in `/packages/<name>/`. L6 imports L1-L5, L5 imports L1-L4, etc.

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
  - `docs-public/docs_src/dev-notes/l5-apps/README.md`, `l5-benchmark/README.md`  
  - `docs-public/docs_src/dev-notes/l6-cli/README.md`, `l6-studio/README.md`, `l6-gateway/README.md`

Only after consulting these READMEs should the assistant propose designs, refactors, or architectural explanations. If documentation and code appear inconsistent, Copilot should **call it out explicitly** in the answer and, when in doubt, ask the user which source of truth to follow.

## Inference Components Map (Reality-First)

SAGE is an inference pipeline system, not just an LLM server. When writing docs, abstracts, design notes, or code changes, prefer describing/using these existing modules (and their correct layer placement) instead of inventing new components.

Canonical namespaces (post-refactor):
- Gateway: `sage.llm.gateway.*` (package: `sage-llm-gateway`)
- Control plane + unified client: `sage.llm.*` (package: `sage-llm-core`)
- Optional edge aggregator: `sage.edge.*` (package: `sage-edge`)
- Avoid legacy `sage.gateway.*` imports; they have been superseded.

**Gateway (L6, OpenAI/Anthropic-compatible + control plane + sessions)**

- Entry point: `packages/sage-llm-gateway/src/sage/llm/gateway/server.py`
- Control plane management API: `packages/sage-llm-gateway/src/sage/llm/gateway/routes/engine_control_plane.py`
- Studio backend routes (merged into gateway): `packages/sage-llm-gateway/src/sage/llm/gateway/routes/studio.py`
- OpenAI adapter (runs persistent RAG pipeline, can trigger agentic operators):
  `packages/sage-llm-gateway/src/sage/llm/gateway/adapters/openai.py`
- Pipeline-as-a-service for RAG: `packages/sage-llm-gateway/src/sage/llm/gateway/rag_pipeline.py`
- Session + memory backends (short-term + NeuroMem VDB/KV/Graph):
  `packages/sage-llm-gateway/src/sage/llm/gateway/session/manager.py`
- Edge aggregator (optional shell mounting the gateway, keeps /v1/* intact by default):
  `packages/sage-edge/src/sage/edge/app.py`

**Control Plane + Unified Client (L1, sageLLM integration)**

- Unified LLM+Embedding client (must use factory):
  `packages/sage-llm-core/src/sage/llm/unified_client.py`
- Control plane implementation lives under:
  `packages/sage-llm-core/src/sage/llm/control_plane/`
  (tests: `.../control_plane/tests/`)

**Middleware inference building blocks (L4, including C++ extensions)**

- Vector DB core (C++20, self-developed, pluggable ANNS, multimodal fusion):
  `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB/README.md`
  - **SageDB VDB Backend**: Self-developed high-performance C++ vector database
  - **NOT FAISS-based**: Fully custom implementation
  - **ANNS Algorithms**: Migrated to `sage-libs/anns/` (faiss_HNSW, vsag_hnsw, diskann, etc.)
  - Python API: `sage.middleware.components.sage_db.python.sage_db.SageDB`
  - Supports: similarity search, metadata filtering, hybrid search, batch operations
  - NeuroMem integration: `sage_mem/neuromem/search_engine/vdb_index/sagedb_index.py`
  - Available backends in NeuroMem: FAISS (Python wrapper), SageDB (C++ self-developed)
  - Configuration: Set `backend_type="SageDB"` in VDB index config to use C++ backend
- Vector-native stream processing engine for incremental semantic state snapshots (C++):
  `packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow/README.md`
- Memory system (NeuromMem: store/recall; VDB/KV/Graph; services wrapper):
  `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/README.md`
- Context compression for RAG (LongRefiner/REFORM/Provence adapters):
  `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/README.md`
- Time-series DB + window ops/join + out-of-order handling (C++ + pybind11):
  `packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB/README.md`

**Benchmarks (L5)**

- Control plane scheduling benchmark (throughput/TTFT/TBT/p99/SLO):
  `packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/README.md`
- Agent benchmarks (tool selection / planning / timing):
  `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/README.md`

**Kernel + Libs (L3)**

- Dataflow runtime, distributed execution, fault tolerance: `packages/sage-kernel/`
- Algorithms, RAG tools, agent framework/integrations: `packages/sage-libs/`
  - **ANN Interface**: `sage.libs.ann` - Unified ANN algorithm interface
    - Base classes: `AnnIndex`, `AnnIndexMeta` (in `sage.libs.ann.base`)
    - Factory: `create()`, `register()`, `registered()` (in `sage.libs.ann.factory`)
    - Implementations: `sage.libs.anns/` (faiss_HNSW, vsag_hnsw, diskann, candy_*, cufe, gti, puck, etc.)
    - Reusable by: benchmark_anns, SageDB, SageFlow

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

**Submodules** - CRITICAL: NEVER use `git submodule update --init`

```bash
./manage.sh                        # Bootstrap submodules + hooks
./tools/maintenance/sage-maintenance.sh submodule init    # Initialize
./tools/maintenance/sage-maintenance.sh submodule switch  # Fix detached HEAD
```

C++ extension submodules in `packages/sage-middleware/src/sage/middleware/components/`

**Environment**: Copy `.env.template` to `.env`, set `OPENAI_API_KEY`, `HF_TOKEN`

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
| GitHub Actions (ubuntu-latest) | `./tools/install/ci_install_wrapper.sh --dev --yes` | 标准 CI，安装到 `~/.local` |
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
docs-public/docs_src/dev-notes/ # Dev docs (by layer: l1-l6, cross-layer)
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

## Common Issues

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
| `GATEWAY_DEFAULT` | 8889 | sage-llm-gateway (OpenAI 兼容 API Gateway) |
| `EDGE_DEFAULT` | 8899 | sage-edge 聚合器（可选，默认挂载 gateway 保持 /v1/*） |
| `LLM_DEFAULT` | 8001 | vLLM 推理服务 |
| `LLM_WSL_FALLBACK` | 8901 | WSL2 备用 LLM 端口 |
| `STUDIO_BACKEND` | 8889| sage-studio 后端 API |
| `STUDIO_FRONTEND` | 5173 | sage-studio 前端 (Vite) |
| `EMBEDDING_DEFAULT` | 8090 | Embedding 服务 |
| `BENCHMARK_LLM` | 8901 | Benchmark 专用 LLM 端口 |

**架构**: `User → Edge (8899, 可选) → Gateway (8889) → LLM (8001)`（Edge 默认直通 Gateway，直接访问 Gateway 也有效）

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

## Resources

- Architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
- Guides: `CONTRIBUTING.md` (CN), `DEVELOPER.md` (EN)
- Dev notes: `docs/dev-notes/` (l1-l6, cross-layer/ci-cd/)

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
│                 sage.llm.gateway (L6 Gateway)                              │
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

*可选 Edge 层*: `sage-edge` (8899) 可以将 `sage.llm.gateway` 挂载在 `/`（保持 `/v1/*` 兼容），或在自定义前缀下提供多域聚合。未启动 edge 时，直接访问 Gateway 即可。

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
| `ControlPlaneManager` | `sage.llm.control_plane.manager` | 核心调度管理器 |
| `RequestClassifier` | `sage.llm.control_plane.request_classifier` | 请求类型分类 |
| `HybridSchedulingPolicy` | `sage.llm.control_plane.strategies.hybrid_policy` | 混合调度策略 |
| `EmbeddingExecutor` | `sage.llm.control_plane.executors.embedding_executor` | Embedding 批处理 |
| `ControlPlaneService` | `sage.llm.control_plane_service` | Control Plane SAGE 封装 |

### 关键文件位置

```
packages/sage-llm-core/src/sage/llm/
  unified_client.py         # UnifiedInferenceClient (factory-only construction)
  control_plane_service.py  # Control Plane facade
  control_plane/            # Control Plane core implementation
    manager.py              # 调度管理器
    request_classifier.py   # 请求分类器
    strategies/hybrid_policy.py  # LLM + Embedding 混合调度
    executors/embedding_executor.py # Embedding 批处理执行

packages/sage-llm-gateway/src/sage/llm/gateway/
  server.py                 # FastAPI 应用入口 (OpenAI/Anthropic-compatible)
  routes/
    engine_control_plane.py # Control Plane 管理 API
    llm.py                  # LLM 代理
    embedding.py            # Embedding 代理
    studio.py               # Studio backend routes (merged)
    sessions.py             # 会话管理
  adapters/openai.py        # OpenAI adapter
  rag_pipeline.py           # Pipeline-as-a-service
  session/manager.py        # Session + memory backends

packages/sage-edge/src/sage/edge/
  app.py                    # FastAPI aggregator shell (mounts gateway, keeps /v1/* by default)
  server.py                 # uvicorn entrypoint / CLI target

packages/sage-common/src/sage/common/components/
  sage_embedding/
    embedding_server.py     # OpenAI 兼容 Embedding 服务器
    factory.py              # EmbeddingFactory (本地模型)
```

### 客户端模式对比（统一 Control Plane）

> Simple 模式已移除；所有请求都经由 Control Plane。

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

## sage-benchmark 组件

Agent 能力和 Control Plane 评测框架，位于 `packages/sage-benchmark/`：

### benchmark_agent (Agent 能力评测)

评估 Agent 三个核心能力：工具选择、任务规划、时机判断。

**核心模块**:
```
src/sage/benchmark/benchmark_agent/
  adapter_registry.py      # 策略注册表 (selector.*, planner.*, timing.*)
  experiments/
    base_experiment.py     # 实验基类 + 数据模型
    tool_selection_exp.py  # 工具选择评测
    planning_exp.py        # 任务规划评测
    timing_detection_exp.py # 时机决策评测
  evaluation/
    metrics.py             # 评测指标 (accuracy, precision, recall, etc.)
  scripts/                 # 评测脚本
```

**使用示例**:
```python
from sage.benchmark.benchmark_agent import get_adapter_registry

registry = get_adapter_registry()

# 工具选择策略
selector = registry.get("selector.keyword")  # keyword, embedding, hybrid, gorilla, dfsdt

# 任务规划策略
planner = registry.get("planner.react")  # simple, hierarchical, llm_based, react, tot

# 时机决策策略
decider = registry.get("timing.rule_based")  # rule_based, llm_based, hybrid
```

### benchmark_control_plane (调度策略评测)

评估 sageLLM Control Plane 的调度策略性能（吞吐量、延迟、SLO 合规率）。

**CLI**:
```bash
# LLM 调度评测
sage-cp-bench run --mode llm --policy fifo --requests 100

# Hybrid (LLM + Embedding) 评测
sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7

# 策略对比
sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware
```

**详细文档**: `packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane/README.md`

## SageDB Vector Database Backend

### Overview

SageDB is a **self-developed high-performance C++ vector database**, fully custom implementation (NOT based on FAISS), integrated into SAGE's NeuroMem VDB system.

**Features**:
- ✅ Self-developed C++ core (independent implementation)
- ✅ High-performance similarity search (C++ optimized)
- ✅ Metadata filtering (`filtered_search`, `search_by_metadata`)
- ✅ Hybrid search (vector + text)
- ✅ Batch operations with numpy optimization
- ✅ Persistent storage (save/load)
- ✅ Multiple index types (AUTO, FLAT, IVF, HNSW)
- ✅ Distance metrics (L2, INNER_PRODUCT, COSINE)
- ✅ **ANNS Algorithms**: Available in `sage-libs/anns/` (faiss_HNSW, vsag_hnsw, diskann, candy_*, cufe, gti, puck, etc.)

### Location

**Core Implementation**:
- C++ Backend: `packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB/`
- Python API: `packages/sage-middleware/src/sage/middleware/components/sage_db/python/sage_db.py`
- NeuroMem Adapter: `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/search_engine/vdb_index/sagedb_index.py`

### Usage in NeuroMem VDB Collections

**Creating a VDB collection with SageDB backend**:

```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

manager = MemoryManager()

# Create collection
collection = manager.create_collection({
    "name": "my_collection",
    "backend_type": "VDB"
})

# Create SageDB index
collection.create_index({
    "name": "my_index",
    "dim": 1024,
    "backend_type": "SageDB",  # Use SageDB instead of FAISS
    "description": "High-performance SageDB index"
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

# Optimized: SageDB backend (C++ performance)
index_config = {
    "backend_type": "SageDB",  # C++ optimized
    ...
}
```

**Current Status** (2025-12-28):
- ✅ SageDB backend registered in VDB index factory
- ✅ SageDBIndex adapter implements all BaseVDBIndex methods
- ✅ Tests pass: insert, batch_insert, search, delete, update
- ⚠️ Gateway default remains FAISS (change to "SageDB" to use C++ backend)

**Performance Characteristics** (5000 vectors, dim=128):
- ✅ **Insert**: SageDB 10x faster (single), 1.14x faster (batch) - C++ optimized write path
- ⚠️ **Search**: FAISS 2.8-3x faster across all k values (Python wrapper overhead in current implementation)
- ➡️ **Memory**: Nearly identical (~945 MB)
- ✅ **ANNS Algorithms**: Now available in `sage-libs/anns/` for modularity

**When to use SageDB**:
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

### Direct SageDB API (without NeuroMem)

**Important**: SageDB is a self-developed C++ vector database, not based on FAISS.

```python
from sage.middleware.components.sage_db.python.sage_db import SageDB, IndexType, DistanceMetric

# Create database (C++ core)
db = SageDB(dimension=128, index_type=IndexType.AUTO, metric=DistanceMetric.L2)

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

**SageDB Methods**:
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

**Trust these instructions** - search only if incomplete, errors occur, or deep architecture needed.
