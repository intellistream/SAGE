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
```

Tools: Ruff (format+lint, line 100), Mypy (types, warning mode), Shellcheck Config:
`tools/pre-commit-config.yaml`, `tools/ruff.toml`

**Make shortcuts**: `make help`, `make test`, `make format`, `make clean`, `make docs`

## CI/CD (.github/workflows/)

**Main workflows**: build-test.yml (45m), examples-test.yml (30m), code-quality.yml (10m),
installation-test.yml, publish-pypi.yml

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
.sage/                  # Build artifacts, cache, logs (gitignored)
manage.sh               # Submodule wrapper
quickstart.sh           # Installer
Makefile                # Shortcuts
```

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
gateway_port = SagePorts.GATEWAY_DEFAULT  # 8000

# ✅ WSL2 环境推荐用法
port = SagePorts.get_recommended_llm_port()  # 自动检测 WSL2 并选择合适端口

# ❌ 错误用法 - 禁止硬编码
port = 8001  # 不要这样写
```

**端口分配表**:
| 常量 | 端口 | 用途 |
|------|------|------|
| `GATEWAY_DEFAULT` | 8000 | sage-gateway (OpenAI 兼容 API Gateway) |
| `LLM_DEFAULT` | 8001 | vLLM 推理服务 |
| `LLM_WSL_FALLBACK` | 8901 | WSL2 备用 LLM 端口 |
| `STUDIO_BACKEND` | 8080 | sage-studio 后端 API |
| `STUDIO_FRONTEND` | 5173 | sage-studio 前端 (Vite) |
| `EMBEDDING_DEFAULT` | 8090 | Embedding 服务 |
| `BENCHMARK_LLM` | 8901 | Benchmark 专用 LLM 端口 |

**架构**: `User → Gateway (8000) → LLM (8001)`

**WSL2 已知问题**:
- 端口 8001 在 WSL2 上可能出现"端口监听但连接被拒绝"的问题
- 使用 `SagePorts.get_recommended_llm_port()` 自动选择合适端口
- 或直接使用 `SagePorts.BENCHMARK_LLM` (8901) 作为备用

**配置文件位置**: `packages/sage-common/src/sage/common/config/ports.py`

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

## LLM & Embedding Services

**设计原则**: 本地优先，云端回退。SAGE 提供两种 LLM 使用模式，根据场景选择。

### 模式对比

| 模式 | 类 | 适用场景 | 是否需要启动服务 |
|------|-----|---------|-----------------|
| **内嵌模式** | `VLLMService` | 批处理、训练、离线推理 | ❌ 无需，进程内加载 |
| **API 模式** | `IntelligentLLMClient` | 在线服务、多客户端共享、测试脚本 | ✅ 需要 API 端点 |

### 模式 1: 内嵌模式 (VLLMService) - 进程内加载

**直接在 Python 进程内加载 vLLM 引擎**，无需单独启动服务。适合批处理和离线任务。

```python
from sage.common.components.sage_llm import VLLMService

# 创建并加载模型（首次会自动下载）
service = VLLMService({
    "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
    "auto_download": True,
    "sampling": {"temperature": 0.7, "max_tokens": 512}
})
service.setup()  # 加载模型到 GPU（耗时操作）

# 生成文本
results = service.generate("Hello, world!")
print(results[0]["generations"][0]["text"])

# 清理资源
service.teardown()
```

**特点**:
- ✅ 无需启动外部服务
- ✅ 适合批处理、训练流水线
- ❌ 不支持多进程共享
- ❌ 每次 setup() 都要加载模型

### 模式 2: API 模式 (UnifiedInferenceClient) - 连接 API 端点 (推荐)

**连接 OpenAI 兼容的 API 端点**（本地 vLLM 或云端）。适合在线服务和测试脚本。

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 方式 A: 自动检测（推荐）- 本地优先，云端回退
client = UnifiedInferenceClient.create_auto()

# 方式 B: 指定端点
client = UnifiedInferenceClient(
    llm_base_url="http://localhost:8001/v1",
    llm_model="Qwen/Qwen2.5-7B-Instruct",
    llm_api_key=""  # 本地服务通常无需 key
)

# 聊天
response = client.chat([
    {"role": "user", "content": "Hello."}
])
print(response)  # 返回字符串

# 文本生成
text = client.generate("Once upon a time")

# 向量嵌入
vectors = client.embed(["text1", "text2"])
```

**`create_auto()` 检测顺序**:
1. `SAGE_UNIFIED_BASE_URL` 环境变量（用户显式配置）
2. 本地 LLM: `localhost:8001/v1`（推荐端口）
3. 本地 LLM: `localhost:8000/v1`（vLLM 默认端口）
4. 本地 Embedding: `localhost:8090`, `localhost:8080`
5. 云端 API: DashScope（需要 `SAGE_CHAT_API_KEY`）

**启动本地 vLLM API 服务**（可选，如果需要多进程共享）:
```bash
# 方式 1: SAGE CLI
sage apps llm start --model "Qwen/Qwen2.5-0.5B-Instruct" --port 8001

# 方式 2: SAGE Studio（完整服务栈）
sage studio start

# 方式 3: 直接 vLLM
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8001
```

**特点**:
- ✅ 支持多进程/多客户端共享
- ✅ 本地优先，自动回退云端
- ✅ 适合测试脚本"一键运行"
- ❌ 需要先启动服务（或有云端 API Key）

### 如何选择？

```
需要批处理/离线任务？ → VLLMService（内嵌模式）
需要在线服务/测试脚本？ → UnifiedInferenceClient（推荐）
同时需要 LLM 和 Embedding？ → UnifiedInferenceClient（推荐）
不确定？ → UnifiedInferenceClient.create_auto()（自动检测）
```

### UnifiedInferenceClient API 参考

**主要方法**:
| 方法 | 签名 | 说明 |
|------|------|------|
| `chat()` | `chat(messages: list[dict]) -> str` | 聊天对话 |
| `generate()` | `generate(prompt: str) -> str` | 文本生成 |
| `embed()` | `embed(texts: list[str]) -> list[list[float]]` | 向量嵌入 |

**工厂方法**:
| 方法 | 说明 |
|------|------|
| `create_auto()` | 自动检测端点（推荐） |
| `get_instance(instance_key)` | 单例模式，避免重复创建 |
| `create_with_control_plane()` | 高级调度模式 |

**Control Plane 模式**（高级调度）:
```python
client = UnifiedInferenceClient.create_with_control_plane(
    llm_base_url="http://localhost:8001/v1",
    llm_model="Qwen/Qwen2.5-7B-Instruct",
    embedding_base_url="http://localhost:8090/v1",
    embedding_model="BAAI/bge-m3",
)
```

### 向后兼容 (DEPRECATED)

以下类已弃用，但仍可使用（会发出 DeprecationWarning）：
- `IntelligentLLMClient` → 使用 `UnifiedInferenceClient`
- `IntelligentEmbeddingClient` → 使用 `UnifiedInferenceClient.embed()`
- `check_llm_service()` → 使用 `UnifiedInferenceClient._check_endpoint_health()`
- `get_llm_client()` → 使用 `UnifiedInferenceClient.create_auto()`

### EmbeddingFactory 和 EmbeddingProtocol (sage-common)

**架构**: Embedding 是**进程内加载模型**，无需启动单独服务（与 LLM 的 API 模式不同）。
每次调用 `EmbeddingFactory.create()` 都会在当前进程内加载模型到内存。

**重要**: `EmbeddingFactory.create()` 返回的是**单文本接口** (`embed(text: str)`)，
但很多组件（如 GorillaSelector）需要**批量接口** (`embed(texts: list[str])`)。

**正确用法** - 使用 `EmbeddingClientAdapter` 适配接口：

```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory,
    EmbeddingClientAdapter,  # 接口适配器
    adapt_embedding_client,   # 自动适配函数
)

# 方式 1: 手动适配
raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
client = EmbeddingClientAdapter(raw_embedder)
vectors = client.embed(["文本1", "文本2"])  # 批量接口

# 方式 2: 自动适配（推荐）
raw_embedder = EmbeddingFactory.create("hash", dim=64)
client = adapt_embedding_client(raw_embedder)  # 自动检测并适配
vectors = client.embed(["文本1", "文本2"])

# 支持的后端: hf, openai, jina, hash (测试用), mockembedder (单元测试)
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

### 环境变量 (.env)

```bash
# === 本地 LLM（优先，通常无需配置）===
# VLLM_API_KEY=             # 本地 vLLM 认证（通常留空）

# === 云端 API（回退，需要时配置）===
SAGE_CHAT_API_KEY=sk-xxx    # DashScope/阿里云 API Key
SAGE_CHAT_MODEL=qwen-turbo-2025-02-11
SAGE_CHAT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Embedding
HF_TOKEN=hf_xxx             # HuggingFace (模型下载)
HF_ENDPOINT=https://hf-mirror.com  # 中国镜像
```

### 关键组件位置

```
packages/sage-common/src/sage/common/components/
  sage_llm/
    unified_client.py      # UnifiedInferenceClient (统一客户端，推荐)
    unified_api_server.py  # UnifiedAPIServer (OpenAI 兼容 API 服务器)
    service.py             # VLLMService (内嵌 vLLM 封装)
    api_server.py          # LLMAPIServer (LLM API 服务器)
    control_plane_service.py  # 多实例调度
    client.py              # DEPRECATED: 向后兼容别名
    sageLLM/control_plane/ # Control Plane 调度框架
      strategies/hybrid_policy.py  # 混合调度策略
  sage_embedding/
    factory.py             # EmbeddingFactory (创建单文本embedder)
    protocols.py           # EmbeddingProtocol, EmbeddingClientAdapter (批量接口)
    embedding_server.py    # FastAPI embedding server (OpenAI 兼容)
    service.py             # EmbeddingService
    base.py                # BaseEmbedding (单文本接口基类)
    client.py              # DEPRECATED: 向后兼容别名
```

## sage-benchmark 组件

Agent 能力评测框架，位于 `packages/sage-benchmark/`：

### 核心模块

```
src/sage/benchmark/benchmark_agent/
  adapter_registry.py      # 策略注册表 (selector.*, planner.*, timing.*)
  experiments/
    base_experiment.py     # 实验基类 + 数据模型
    tool_selection_exp.py  # 工具选择评测
    planning_exp.py        # 任务规划评测
    timing_exp.py          # 时机决策评测
  evaluation/
    metrics.py             # 评测指标 (accuracy, precision, recall, etc.)
  data/                    # 评测数据 (JSONL)
scripts/
  test_tool_selection_e2e.py  # 工具选择端到端测试
  test_planning_e2e.py        # 规划端到端测试
```

### 使用示例

```python
from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry

registry = get_adapter_registry()

# 工具选择策略
selector = registry.create_adapter("selector.keyword")  # keyword, embedding, hybrid

# 任务规划策略 (使用 UnifiedInferenceClient)
planner = registry.create_adapter("planner.llm_based")  # simple, hierarchical, llm_based

# 时机决策策略
decider = registry.create_adapter("timing.threshold")   # threshold, embedding, llm
```

**Trust these instructions** - search only if incomplete, errors occur, or deep architecture needed.
