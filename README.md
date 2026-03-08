# SAGE - Streaming-Augmented Generative Execution

> A declarative, composable framework for building transparent LLM-powered systems through dataflow
> abstractions.

## 🚀 Quick Start

### Try SAGE Studio

```bash
pip install isage-studio
sage-studio start
```

______________________________________________________________________

[![Build & Test](https://github.com/intellistream/SAGE/actions/workflows/ci-build-test.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/ci-build-test.yml)
[![codecov](https://codecov.io/gh/intellistream/SAGE/branch/main/graph/badge.svg)](https://codecov.io/gh/intellistream/SAGE)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![PyPI version](https://badge.fury.io/py/isage.svg)](https://badge.fury.io/py/isage)
[![GitHub Issues](https://img.shields.io/github/issues/intellistream/SAGE)](https://github.com/intellistream/SAGE/issues)
[![GitHub Stars](https://img.shields.io/github/stars/intellistream/SAGE?style=social)](https://github.com/intellistream/SAGE/stargazers)

**SAGE** is a high-performance streaming framework for building AI-powered data processing
pipelines. Transform complex LLM reasoning workflows into transparent, scalable, and maintainable
systems through declarative dataflow abstractions.

## Key Features

- **Production-Ready**: Distributed processing, fault tolerance, comprehensive monitoring
- **Developer Experience**: Complex AI pipelines in just a few lines of code
- **High Performance**: Optimized streaming with intelligent memory management
- **Observable**: Built-in visibility into execution and performance
- **Flexible**: CPU-only or GPU nodes with intelligent resource scheduling

## Quick Start

Transform rigid LLM applications into flexible, observable workflows. Traditional imperative
approaches create brittle systems:

```python
# Traditional approach - rigid and hard to modify
def traditional_rag(query):
    docs = retriever.retrieve(query)
    if len(docs) < 3:
        docs = fallback_retriever.retrieve(query)
    prompt = build_prompt(query, docs)
    response = llm.generate(prompt)
    return response
```

SAGE transforms this into a **declarative, composable workflow**:

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.foundation.io.source import FileSource
from sage.middleware.operators.llm import SageLLMGenerator  # ✅ Recommended
from sage.libs.foundation.io.sink import TerminalSink

# Create execution environment
env = LocalEnvironment("rag_pipeline")

# Build declarative pipeline with sageLLM (recommended)
(
    env.from_source(FileSource, {"data_path": "questions.txt"})
    .map(SageLLMGenerator, {
        "model_path": "Qwen/Qwen2.5-7B-Instruct",
        "backend_type": "auto",  # auto/cuda/ascend/mock
    })
    .sink(TerminalSink)
)

# Execute pipeline
env.submit()
```

> 💡 **LLM Engine**: SAGE uses `sageLLM` as the default inference engine. For OpenAI-compatible APIs,
> use `OpenAIGenerator`. See [CHANGELOG](./CHANGELOG.md) for legacy migration notes.

**Current API quick reference**

- `sage.libs.foundation.io.source`: `FileSource`, `TextFileSource`, `CSVFileSource`,
  `JSONFileSource`
- `sage.libs.foundation.io.sink`: `TerminalSink`, `FileSink`
- `sage.middleware.operators.rag`: `RAGDocument`, `RAGQuery`, `RAGResponse`
- `sage.middleware.operators.llm`: `SageLLMGenerator`

**Try it yourself:**

```bash
git clone https://github.com/intellistream/SAGE.git && cd SAGE
git checkout main-dev
./quickstart.sh --dev --yes

# Tutorials are now in a separate repository
git clone https://github.com/intellistream/sage-tutorials.git
python sage-tutorials/L1-common/hello_world.py
```

**For CPU-only deployment:**

```bash
# Start JobManager for distributed task execution
sage jobmanager start

# Run CPU node demo (no GPU required)
git clone https://github.com/intellistream/sage-tutorials.git
python sage-tutorials/L3-kernel/cpu_node_demo.py
```

## Architecture

SAGE now uses a **4-tier workspace architecture (L1-L4)** centered on the actively maintained main
repositories:

```text
L4: sage-studio                       # Application / UI      (isage-studio)
L3: sage-cli                          # CLI entrypoint        (isage-cli)
L2: sage-kernel                       # Runtime / scheduler   (isage-kernel)
L1: sage-common                       # Foundation            (isage-common)
```

Notes:

- `isage-common` now carries the former platform / shared interface responsibilities.
- `isage-kernel` now carries the former middleware runtime responsibilities.
- `sage-studio` is intentionally above `sage-cli`, not the same layer, because it extends the CLI
  via plugin entry points.

See [SAGE Ecosystem](#sage-ecosystem) for all independent sub-repositories with CI status, PyPI
packages, and categorized listings.

📖 **[Architecture Guide](./docs/ARCHITECTURE_LAYER_OWNERSHIP_MATRIX_V1.md)** -
Canonical ownership boundaries and dependency rules for the meta repo

📌 **[Layer Ownership Matrix v1 (Wave A)](./ARCHITECTURE_LAYER_OWNERSHIP_MATRIX_V1.md)** - Canonical
L1-L4 workspace ownership, independent sub-repo coordination boundary (including `sagellm` capabilities),
forbidden directions, and boundary refactor review checklist

## Installation

**Quickstart (Recommended)**

```bash
git clone https://github.com/intellistream/SAGE.git && cd SAGE
./quickstart.sh --dev --yes         # 开发模式：尽量本地 editable
# 或
./quickstart.sh --standard --yes    # 标准模式：子包依赖默认从 PyPI 安装
```

⚡ **Auto-Acceleration**: Network optimization is now **enabled by default**:

- 🌐 Auto-detects network location (China mainland → mirror sources)
- 🚀 Parallel downloads (8 threads) + pre-compiled packages
- ⏱️ **3-5x faster** installation: 12-18 min (vs 35-45 min)
- 🔧 Disable: `./quickstart.sh --no-mirror --dev --yes`

**Install Mode Semantics**

- `standard`：本地安装仓库根目录下的 `isage` meta 包，子仓依赖按根 `pyproject.toml` 版本从 PyPI 解析。
- `dev`：先完成 `standard` 安装，再尽量将同级工作区中的本地 SAGE 子仓库切换为 editable (`-e`)。

**PyPI Install**

```bash
pip install isage              # Core framework
pip install isage[dev]         # Development tools (includes isage-dev-tools, pre-commit, pytest, etc.)
```

**What's included in `pip install isage`**

`isage` is a meta-package that bundles the current framework stack: `isage-common` (L1, includes
former platform/shared-interface responsibilities) · `isage-kernel` (L2, includes former
middleware runtime responsibilities) · `isage-cli` (L3) · `isagellm` (LLM gateway)

**Capability Packages (bundled with `isage`)** 🧩

For a standard `pip install isage`, these packages are installed transitively and do **not** require
extra manual installation:

| Feature            | Included Package | Notes                                   |
| ------------------ | ---------------- | --------------------------------------- |
| **Agents**         | `isage-agentic`  | ReAct, PlanExecute, complex reasoning   |
| **Vector DB**      | `isage-vdb`      | Fast vector search (SageVDB)            |
| **Memory Systems** | `isage-neuromem` | Persistent memory + sessions            |
| **Privacy**        | `isage-privacy`  | Differential privacy, PII handling      |
| **LLM Gateway**    | `isagellm`       | Control plane, unified inference client |

**Optional packages (not bundled — install separately)** 🦁

These packages were moved to independent repositories and are no longer part of the default `isage`
install. See **[SAGE Zoo guide](./docs/sage_zoo.md)** for the full list with
one-liner descriptions and install commands.

```bash
pip install isage-rag              # RAG 管道（文档加载 / 分块 / 检索 / 重排）
pip install isage-eval             # 评估框架（指标 / LLM 评判）
pip install isage-finetune         # LLM 微调 / Agent training（LoRA / SFT / RL / Reward Model）
pip install isage-agentic-tooluse  # Agent 工具选择（Hybrid/DFS/Gorilla）
pip install isage-intent           # 意图识别（关键词 + LLM）
pip install 'isage-tools[mcp]'     # 独立工具仓库；当前已注册到 sage-mcp
pip install 'isage-mcp[all]'       # 聚合 MCP Server（当前默认聚合 isage-tools）
```

Example: install full core SAGE stack

```bash
pip install isage
```

See [Dependency Management](./DEVELOPER.md#dependency-management) in DEVELOPER.md for detailed
guidance.

**Verification & Troubleshooting**

```bash
sage doctor                    # Check installation
./quickstart.sh --doctor       # Diagnose issues
```

📖 **Detailed guides**: [Installation Guide](docs/INSTALLATION_GUIDE.md) |
[Troubleshooting](docs/TROUBLESHOOTING.md) | [Validation](docs/INSTALLATION_VALIDATION.md) |
[Optimization Tips](tools/install/docs/INSTALLATION_OPTIMIZATION.md)

⚠️ **Known Issues**: If you encounter transformers version conflicts when installing multiple SAGE
packages, prefer checking [DEVELOPER.md](./DEVELOPER.md) and the package-specific READMEs first.

## Environment Configuration

```bash
cp .env.template .env    # Copy template
# Edit .env and add your API keys (OPENAI_API_KEY, HF_TOKEN, etc.)
```

📖 **API key setup**: See [.env.template](./.env.template) for all available options

## 📚 Tutorials

Complete tutorials covering the current workspace tiers of SAGE (L1-L4) plus historical capability topics:

```bash
# Clone tutorials repository
git clone https://github.com/intellistream/sage-tutorials.git
cd sage-tutorials

# Start learning (30 seconds)
python L1-common/hello_world.py

# Follow the quick start guide
cat QUICK_START.md
```

**Tutorial Structure**:

- `sage-tutorials/L1-common/` - Foundation layer (config, logging, unified client)
- `sage-tutorials/L2-platform/` - Platform services (scheduler, storage)
- `sage-tutorials/L3-kernel/` - Execution engine (batch, stream, operators)
- `sage-tutorials/L3-libs/` - RAG, Agents, Algorithms
- `sage-tutorials/L4-middleware/` - Domain operators (vector DB, time-series)
- `sage-tutorials/L5-apps/` - Applications and integration demos

See `sage-tutorials/README.md` for complete learning paths.

## Documentation & Resources

- **Documentation**:
  [https://intellistream.github.io/SAGE-Pub/](https://intellistream.github.io/SAGE-Pub/)
- **Examples & Applications**:
  [intellistream/sage-examples](https://github.com/intellistream/sage-examples)
  - RAG examples and production applications
  - Will be published as `isage-examples` on PyPI
- **Tutorials**: [intellistream/sage-tutorials](https://github.com/intellistream/sage-tutorials)
  - Layered tutorials from L1 to L5, quick-start learning paths
- **Architecture**: [docs/ARCHITECTURE_LAYER_OWNERSHIP_MATRIX_V1.md](./docs/ARCHITECTURE_LAYER_OWNERSHIP_MATRIX_V1.md)

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

```bash
git checkout -b feature/my-feature
./quickstart.sh --dev --yes
# Make changes, add tests
sage-dev quality && sage-dev test
git commit -m "feat(kernel): add new feature"
git push -u origin feature/my-feature
```

**Resources**: [Quick Reference](./docs/QUICK_REFERENCE.md) |
[GitHub Issues](https://github.com/intellistream/SAGE/issues) |
[Discussions](https://github.com/intellistream/SAGE/discussions)

## Team Information

**🔒 Team assignments and sensitive information** are maintained in a private repository to protect
member privacy.

- **Public**: Project-level information is available in this repository
- **Private**: Team member assignments, funding details, and contact information are accessible to
  authorized members only
- **Access**: Contact project management for access to the private repository

## Developer Tools

```bash
make help           # View all commands
sage-dev quality    # Format & lint
sage-dev test       # Run tests
make docs           # Build documentation
```

📖 **Complete reference**: [DEVELOPER.md](./DEVELOPER.md)

## SAGE Ecosystem

📦 **[SAGE Zoo guide](./docs/sage_zoo.md)** — 独立可选包（已 zoo 化，各自独立演进）

### 🧠 SAGE — Streaming AI Framework

[![CI](https://github.com/intellistream/SAGE/actions/workflows/ci-build-test.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/ci-build-test.yml)
[![PyPI](https://badge.fury.io/py/isage.svg)](https://pypi.org/project/isage/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Stars](https://img.shields.io/github/stars/intellistream/SAGE?style=social)](https://github.com/intellistream/SAGE/stargazers)

**SAGE** is a streaming AI framework centered on 4 main workspace tiers:

**Core Layers**

- **[sage-common](https://github.com/intellistream/sage-common)** (L1) — Foundation utilities,
  config, logging, and absorbed platform/shared-interface capabilities
  [![CI](https://github.com/intellistream/sage-common/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-common/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-common.svg)](https://pypi.org/project/isage-common/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-common?style=social)](https://github.com/intellistream/sage-common/stargazers)
- **[sage-kernel](https://github.com/intellistream/sage-kernel)** (L2) — Streaming runtime,
  scheduler, flow DSL, and absorbed middleware runtime capabilities
  [![CI](https://github.com/intellistream/sage-kernel/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-kernel/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-kernel.svg)](https://pypi.org/project/isage-kernel/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-kernel?style=social)](https://github.com/intellistream/sage-kernel/stargazers)
- **[sage-cli](https://github.com/intellistream/sage-cli)** (L3) — Unified CLI and developer tooling
  [![CI](https://github.com/intellistream/sage-cli/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-cli/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-cli.svg)](https://pypi.org/project/isage-cli/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-cli?style=social)](https://github.com/intellistream/sage-cli/stargazers)

Independent sub-repositories are organized by category:

**Application & UI**

- **[sage-studio](https://github.com/intellistream/sage-studio)** (L4) — Visual workflow builder
  and LLM playground
  [![CI](https://github.com/intellistream/sage-studio/actions/workflows/ci-test.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-studio/actions/workflows/ci-test.yml)
  [![PyPI](https://badge.fury.io/py/isage-studio.svg)](https://pypi.org/project/isage-studio/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-studio?style=social)](https://github.com/intellistream/sage-studio/stargazers)
- **[sage-examples](https://github.com/intellistream/sage-examples)** — Tutorials and application
  examples
  [![CI](https://github.com/intellistream/sage-examples/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-examples/actions/workflows/tests.yml)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-examples?style=social)](https://github.com/intellistream/sage-examples/stargazers)

**Algorithms & Libraries**

- **[sage-agentic](https://github.com/intellistream/sage-agentic)** — ReAct, PlanExecute agents and
  agentic workflows
  [![CI](https://github.com/intellistream/sage-agentic/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-agentic/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-agentic.svg)](https://pypi.org/project/isage-agentic/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-agentic?style=social)](https://github.com/intellistream/sage-agentic/stargazers)
- **[sage-rag](https://github.com/intellistream/sage-rag)** — Retrieval-augmented generation
  components
  [![CI](https://github.com/intellistream/sage-rag/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-rag/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-rag.svg)](https://pypi.org/project/isage-rag/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-rag?style=social)](https://github.com/intellistream/sage-rag/stargazers)
- **[sageVDB](https://github.com/intellistream/sageVDB)** — High-performance vector database
  (FAISS-compatible API)
  [![CI](https://github.com/intellistream/sageVDB/actions/workflows/ci-tests.yml/badge.svg?branch=main)](https://github.com/intellistream/sageVDB/actions/workflows/ci-tests.yml)
  [![PyPI](https://badge.fury.io/py/isage-vdb.svg)](https://pypi.org/project/isage-vdb/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sageVDB?style=social)](https://github.com/intellistream/sageVDB/stargazers)
- **[sageRefiner](https://github.com/intellistream/sageRefiner)** — Query and response refinement
  algorithms
  [![CI](https://github.com/intellistream/sageRefiner/actions/workflows/ci-tests.yml/badge.svg?branch=main)](https://github.com/intellistream/sageRefiner/actions/workflows/ci-tests.yml)
  [![PyPI](https://badge.fury.io/py/isage-refiner.svg)](https://pypi.org/project/isage-refiner/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sageRefiner?style=social)](https://github.com/intellistream/sageRefiner/stargazers)
- **[sage-amms](https://github.com/intellistream/sage-amms)** — Approximate matrix multiplication
  service
  [![CI](https://github.com/intellistream/sage-amms/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-amms/actions/workflows/build.yml)
  [![PyPI](https://badge.fury.io/py/isage-amms.svg)](https://pypi.org/project/isage-amms/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-amms?style=social)](https://github.com/intellistream/sage-amms/stargazers)
- **[sageFlownet](https://github.com/intellistream/sageFlownet)** — Streaming flownet execution
  engine 🔒 private
  [![CI](https://github.com/intellistream/sageFlownet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sageFlownet/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-flownet.svg)](https://pypi.org/project/isage-flownet/)

**Data & Benchmarks**

- **[sageData](https://github.com/intellistream/sageData)** — Unified dataset management for SAGE
  subsystems
  [![CI](https://github.com/intellistream/sageData/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sageData/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-data.svg)](https://pypi.org/project/isage-data/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sageData?style=social)](https://github.com/intellistream/sageData/stargazers)
- **[sage-benchmark](https://github.com/intellistream/sage-benchmark)** — Comprehensive evaluation
  framework for RAG, agents, memory, and control plane
  [![CI](https://github.com/intellistream/sage-benchmark/actions/workflows/ci-benchmarks.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-benchmark/actions/workflows/ci-benchmarks.yml)
  [![PyPI](https://badge.fury.io/py/isage-benchmark.svg)](https://pypi.org/project/isage-benchmark/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-benchmark?style=social)](https://github.com/intellistream/sage-benchmark/stargazers)
- **[sage-eval](https://github.com/intellistream/sage-eval)** — Evaluation metrics, profilers, and
  LLM judges
  [![CI](https://github.com/intellistream/sage-eval/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-eval/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-eval.svg)](https://pypi.org/project/isage-eval/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-eval?style=social)](https://github.com/intellistream/sage-eval/stargazers)

**Model Optimization & Safety**

- **[sage-finetune](https://github.com/intellistream/sage-finetune)** — Model fine-tuning, agent
  training, and adaptation
  [![CI](https://github.com/intellistream/sage-finetune/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-finetune/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-finetune.svg)](https://pypi.org/project/isage-finetune/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-finetune?style=social)](https://github.com/intellistream/sage-finetune/stargazers)
- **[sage-privacy](https://github.com/intellistream/sage-privacy)** — Differential privacy and PII
  handling
  [![CI](https://github.com/intellistream/sage-privacy/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-privacy/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-privacy.svg)](https://pypi.org/project/isage-privacy/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-privacy?style=social)](https://github.com/intellistream/sage-privacy/stargazers)
- **[sage-safety](https://github.com/intellistream/sage-safety)** — Safety filters and guardrails
  [![CI](https://github.com/intellistream/sage-safety/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-safety/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-safety.svg)](https://pypi.org/project/isage-safety/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-safety?style=social)](https://github.com/intellistream/sage-safety/stargazers)

**Developer Tooling**

- **[sage-dev-tools](https://github.com/intellistream/sage-dev-tools)** — Development CLI and
  quality tooling
  [![CI](https://github.com/intellistream/sage-dev-tools/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-dev-tools/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isage-dev-tools.svg)](https://pypi.org/project/isage-dev-tools/)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-dev-tools?style=social)](https://github.com/intellistream/sage-dev-tools/stargazers)
- **[sage-kernel](https://github.com/intellistream/sage-kernel)** — Extracted kernel modules
  (public)
  [![CI](https://github.com/intellistream/sage-kernel/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-kernel/actions/workflows/ci.yml)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-kernel?style=social)](https://github.com/intellistream/sage-kernel/stargazers)

______________________________________________________________________

### ⚡ sageLLM — LLM Inference Engine

[![CI](https://github.com/intellistream/sagellm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm/actions/workflows/ci.yml)
[![PyPI](https://badge.fury.io/py/isagellm.svg)](https://pypi.org/project/isagellm/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)

sageLLM is a modular, high-performance LLM inference engine. All repositories are 🔒 private and
published to PyPI.

**Core Engine**

- **[sagellm-core](https://github.com/intellistream/sagellm-core)** — Core inference engine
  [![CI](https://github.com/intellistream/sagellm-core/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-core/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-core.svg)](https://pypi.org/project/isagellm-core/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
- **[sagellm-backend](https://github.com/intellistream/sagellm-backend)** — Backend drivers (CUDA,
  Ascend)
  [![CI](https://github.com/intellistream/sagellm-backend/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-backend/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-backend.svg)](https://pypi.org/project/isagellm-backend/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
- **[sagellm-protocol](https://github.com/intellistream/sagellm-protocol)** — Wire protocol and
  serialization
  [![CI](https://github.com/intellistream/sagellm-protocol/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-protocol/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-protocol.svg)](https://pypi.org/project/isagellm-protocol/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)

**Gateway & Control**

- **[sagellm-gateway](https://github.com/intellistream/sagellm-gateway)** — OpenAI-compatible API
  gateway
  [![CI](https://github.com/intellistream/sagellm-gateway/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-gateway/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-gateway.svg)](https://pypi.org/project/isagellm-gateway/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
- **[sagellm-control-plane](https://github.com/intellistream/sagellm-control-plane)** — Scheduling
  and resource management
  [![CI](https://github.com/intellistream/sagellm-control-plane/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-control-plane/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-control-plane.svg)](https://pypi.org/project/isagellm-control-plane/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)

**Optimization**

- **[sagellm-kv-cache](https://github.com/intellistream/sagellm-kv-cache)** — KV cache management
  [![CI](https://github.com/intellistream/sagellm-kv-cache/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-kv-cache/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-kv-cache.svg)](https://pypi.org/project/isagellm-kv-cache/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
- **[sagellm-comm](https://github.com/intellistream/sagellm-comm)** — Communication layer
  [![CI](https://github.com/intellistream/sagellm-comm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-comm/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-comm.svg)](https://pypi.org/project/isagellm-comm/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
- **[sagellm-compression](https://github.com/intellistream/sagellm-compression)** — Compression
  algorithms
  [![CI](https://github.com/intellistream/sagellm-compression/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-compression/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-compression.svg)](https://pypi.org/project/isagellm-compression/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)

**Tooling & Benchmarks**

- **[sagellm-benchmark](https://github.com/intellistream/sagellm-benchmark)** — Performance
  benchmarks
  [![CI](https://github.com/intellistream/sagellm-benchmark/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-benchmark/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-benchmark.svg)](https://pypi.org/project/isagellm-benchmark/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
- **[sagellm-dev-tools](https://github.com/intellistream/sagellm-dev-tools)** — Development tooling
  [![CI](https://github.com/intellistream/sagellm-dev-tools/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm-dev-tools/actions/workflows/ci.yml)
  [![PyPI](https://badge.fury.io/py/isagellm-dev-tools.svg)](https://pypi.org/project/isagellm-dev-tools/)
  [![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)

## Community

**💬 [Join SAGE Community](./docs/COMMUNITY.md)** - WeChat, QQ, Slack, GitHub Discussions

## License

SAGE is licensed under the [MIT License](./LICENSE).
