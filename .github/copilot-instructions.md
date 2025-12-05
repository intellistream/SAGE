# SAGE Copilot Instructions

## Overview

**SAGE** is a Python 3.10+ framework for building AI/LLM data processing pipelines with declarative
dataflow. 11 functional packages + 1 meta-package, ~400MB dev install, uses C++ extensions (CMake).

**Architecture (L1-L6)** - CRITICAL: No upward dependencies

```
L6: sage-cli, sage-studio, sage-tools, sage-gateway  # Interfaces, Dev Tools & API Gateway
L5: sage-apps, sage-benchmark          # Apps & Benchmarks  
L4: sage-middleware                    # Operators (C++ extensions)
L3: sage-kernel, sage-libs             # Core & Algorithms
L2: sage-platform                      # Platform Services
L1: sage-common                        # Foundation
```

Note: `sage-gateway` is published to PyPI as `isage-gateway` (OpenAI/Anthropic compatible API Gateway).

All in `/packages/<name>/`. L6 imports L1-L5, L5 imports L1-L4, etc.

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
docs/dev-notes/         # Dev docs (by layer: l0-l6, cross-layer)
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
gateway_port = SagePorts.GATEWAY_DEFAULT  # 8080

# ✅ WSL2 环境推荐用法
port = SagePorts.get_recommended_llm_port()  # 自动检测 WSL2 并选择合适端口

# ❌ 错误用法 - 禁止硬编码
port = 8001  # 不要这样写
```

**端口分配表**:
| 常量 | 端口 | 用途 |
|------|------|------|
| `GATEWAY_DEFAULT` | 8080 | sage-gateway (OpenAI 兼容 API Gateway) |
| `LLM_DEFAULT` | 8001 | vLLM 推理服务 |
| `LLM_WSL_FALLBACK` | 8901 | WSL2 备用 LLM 端口 |
| `STUDIO_BACKEND` | 8080 | sage-studio 后端 API |
| `STUDIO_FRONTEND` | 5173 | sage-studio 前端 (Vite) |
| `EMBEDDING_DEFAULT` | 8090 | Embedding 服务 |
| `BENCHMARK_LLM` | 8901 | Benchmark 专用 LLM 端口 |

**架构**: `User → Gateway (8080) → LLM (8001)`

**WSL2 已知问题**:
- 端口 8001 在 WSL2 上可能出现"端口监听但连接被拒绝"的问题
- 使用 `SagePorts.get_recommended_llm_port()` 自动选择合适端口
- 或直接使用 `SagePorts.BENCHMARK_LLM` (8901) 作为备用

**配置文件位置**: `packages/sage-common/src/sage/common/config/ports.py`

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
│        ┌─────────────────────┬─────────────────────┐                    │
│        │   Simple Mode       │  Control Plane Mode │                    │
│        │  (直连后端 API)      │  (通过调度器路由)    │  ← 推荐           │
│        └─────────────────────┴─────────────────────┘                    │
├─────────────────────────────────────────────────────────────────────────┤
│                       sage-gateway (统一 Gateway)                          │
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

### 推荐用法：Control Plane 模式

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 方式 1: Control Plane 模式（推荐 - 支持智能调度）
client = UnifiedInferenceClient.create_with_control_plane(
    llm_base_url="http://localhost:8901/v1",      # vLLM 服务
    llm_model="Qwen/Qwen2.5-7B-Instruct",
    embedding_base_url="http://localhost:8090/v1", # Embedding 服务
    embedding_model="BAAI/bge-m3",
)

# 方式 2: 自动检测（Simple 模式，适合简单场景）
client = UnifiedInferenceClient.create()

### 启动服务栈

> ⚠️ `sage llm run` 与 `VLLMService` 依赖 `isage-common[vllm]`（带 vLLM 0.10.x 与 torch 2.4+）。如需本地阻塞式服务，请先运行 `pip install isage-common[vllm]`。

```bash
# 推荐：启动 Gateway（包含 Control Plane）
sage gateway start                                 # 启动 Gateway（端口 8080）
sage gateway status                                # 查看 Gateway 状态
sage gateway stop                                  # 停止 Gateway
sage gateway logs --follow                         # 查看日志

# LLM 服务管理
sage llm serve                                     # 启动 LLM + Embedding 服务（默认）
sage llm serve --no-embedding                      # 仅启动 LLM，不启动 Embedding
sage llm status                                    # 查看状态
sage llm stop                                      # 停止服务
sage llm logs --follow                             # 查看日志

# 阻塞式交互模式（开发调试用）
sage llm run --model "Qwen/Qwen2.5-0.5B-Instruct"

# 引擎管理（通过 Gateway Control Plane）
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
| `ControlPlaneManager` | `sageLLM/control_plane/manager.py` | 核心调度管理器 |
| `RequestClassifier` | `sageLLM/control_plane/request_classifier.py` | 请求类型分类 |
| `HybridSchedulingPolicy` | `sageLLM/control_plane/strategies/hybrid_policy.py` | 混合调度策略 |
| `EmbeddingExecutor` | `sageLLM/control_plane/executors/embedding_executor.py` | Embedding 批处理 |
| `ControlPlaneVLLMService` | `sage_llm/control_plane_service.py` | SAGE 封装层 |

### 关键文件位置

```
packages/sage-common/src/sage/common/components/
  sage_llm/
    unified_client.py         # UnifiedInferenceClient (统一客户端)
    control_plane_service.py  # Control Plane SAGE 封装
    service.py                # VLLMService (内嵌模式，批处理用)
    sageLLM/control_plane/    # ← Control Plane 核心实现
      manager.py              # 调度管理器
      request_classifier.py   # 请求分类器
      strategies/             # 调度策略
        hybrid_policy.py      # LLM + Embedding 混合调度
      executors/              # 执行器
        embedding_executor.py # Embedding 批处理执行
  sage_embedding/
    embedding_server.py       # OpenAI 兼容 Embedding 服务器
    factory.py                # EmbeddingFactory (本地模型)

packages/sage-gateway/src/sage/gateway/
  app.py                      # FastAPI 应用入口
  routes/
    control_plane.py          # Control Plane 管理 API
    llm.py                    # LLM 代理
    embedding.py              # Embedding 代理
    sessions.py               # 会话管理
```

### 两种模式对比

| 特性 | Simple 模式 | Control Plane 模式 |
|------|-------------|-------------------|
| 创建方式 | `create_auto()` | `create_with_control_plane()` |
| 调度 | 直连后端 | 智能路由 + 负载均衡 |
| 多实例 | ❌ | ✅ 支持 |
| 批处理聚合 | ❌ | ✅ Embedding 自动聚合 |
| 优先级调度 | ❌ | ✅ 支持 |
| 适用场景 | 开发测试、简单部署 | 生产环境、高并发 |

### 内嵌模式 (VLLMService) - 批处理专用

```python
from sage.common.components.sage_llm import VLLMService

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
# === 本地服务（推荐）===
# 无需配置，使用 SagePorts 默认端口

# === 云端 API（回退）===
SAGE_CHAT_API_KEY=sk-xxx              # DashScope API Key
SAGE_CHAT_MODEL=qwen-turbo-2025-02-11
SAGE_CHAT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# === HuggingFace ===
HF_TOKEN=hf_xxx
# HF_ENDPOINT 无需手动设置，SAGE 会自动检测网络并配置镜像
```

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
- `sage llm run` - 运行 vLLM 服务
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

**Trust these instructions** - search only if incomplete, errors occur, or deep architecture needed.
