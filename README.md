# SAGE - Streaming-Augmented Generative Execution

> A declarative, composable framework for building transparent LLM-powered systems through dataflow
> abstractions.

## 🚀 Quick Start

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

## 2026 Focus Reset

SAGE is being refocused into a **stream-first inference service system** instead of a broad
collection of loosely coupled apps.

- **Keep the stream core**: `DataStream` + declarative pipeline composition remain the product
  identity
- **Keep the execution core**: `LocalEnvironment`, `JobManager`, scheduling, service runtime
- **Keep the serving integration plane**: OpenAI-compatible gateway access, model lifecycle entry,
  and control-plane integration contracts
- **Keep distributed execution optional**: `FlowNetEnvironment` remains the FlowNet-first optional
  distributed runtime entry, instead of falling back to new Ray-based paths
- **Keep the operating substrate**: centralized ports, XDG user paths, model registry, logs,
  health/status surfaces
- **De-emphasize apps**: UI-first repos are no longer the product center; optional apps should sit
  outside the core or be retired

This direction also makes SAGE easier to position as a **SAGE Zoo member**: a reusable
stream-oriented runtime + serving component that other systems can call through stable APIs instead
of embedding internal implementation details.

Important boundary: `isagellm` remains an **independent inference engine**. SAGE integrates with it
as an external engine/service capability; SAGE should not absorb `isagellm` internals into the main
repository.

Preferred in-tree surface during consolidation:

- `from sage.stream import DataStream`
- `from sage.runtime import LocalEnvironment, FlowNetEnvironment, JobManager`
- `from sage.foundation import SagePorts, SageUserPaths`
- `from sage.serving import SageServeConfig, build_sagellm_gateway_command, probe_gateway`

## Key Features

- **Stream-First**: Dataflow is the primary abstraction, not an afterthought
- **Production-Ready**: Local-first execution, optional distributed processing, fault tolerance,
  comprehensive monitoring
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
from sage.runtime import LocalEnvironment
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

### Current API quick reference

- `sage.libs.foundation.io.source`: `FileSource`, `TextFileSource`, `CSVFileSource`,
  `JSONFileSource`
- `sage.libs.foundation.io.sink`: `TerminalSink`, `FileSink`
- `sage.middleware.operators.rag`: `RAGDocument`, `RAGQuery`, `RAGResponse`
- `sage.middleware.operators.llm`: `SageLLMGenerator`

### Try it yourself

```bash
git clone https://github.com/intellistream/SAGE.git && cd SAGE
git checkout main
./quickstart.sh --dev --yes

# Tutorials are now in a separate repository
git clone https://github.com/intellistream/sage-tutorials.git
python sage-tutorials/L1-common/hello_world.py
```

### For CPU-only verification

```bash
# Verify the in-tree core surface
sage verify

# Run a real one-shot chat via sagellm (gateway or direct CLI)
sage chat --ask "Hello, SAGE!"

# Explore tutorials separately if needed
git clone https://github.com/intellistream/sage-tutorials.git
python sage-tutorials/L1-common/hello_world.py
```

## Architecture

Current baseline is a **4-tier workspace architecture (L1-L4)**:

```text
L4: application repos (optional)      # App / UI / benchmark
L3: sage.cli                          # CLI entrypoint        (in-tree)
L2: sage.runtime + sage.stream        # Runtime / scheduler   (in-tree)
L1: sage.foundation                   # Foundation            (in-tree)
```

Notes:

- Historical split packages may still exist as transitional published compatibility channels.
- The main repository now owns the preferred product surface directly: `sage.foundation` +
  `sage.stream` + `sage.runtime` + `sage.serving` + `sage.cli`.
- Historical split foundation/runtime/CLI repos are therefore no longer the desired long-term
  product boundary, even when some transitional imports still exist outside the main install
  contract.

Target product convergence is narrower than the historical workspace shape:

```text
SAGE Inference Service System
L3 Interface   : CLI + OpenAI-compatible service entry + external integration surface
L2 Runtime     : LocalEnvironment + DataStream + JobManager + scheduler + execution services
Optional Dist. : FlowNetEnvironment (FlowNet-backed distributed execution)
L1 Foundation  : config + ports + user paths + model registry + logging
Optional       : RAG / memory / tool-use / benchmark adapters
```

In other words, SAGE is moving toward a smaller, sharper center: **stream + runtime + serving +
operations**, with distributed execution available as an optional scale-out mode.

Repo-retirement gate: do not retire historical split repos solely based on packaging cleanup. The
main repo has now removed direct historical runtime split-package dependency pins and owns its local
runtime path in-tree, but ecosystem compatibility imports, external repos, and remaining
transitional release channels still need deliberate follow-up before those repos can be fully
retired.

See [SAGE Ecosystem](#sage-ecosystem) for all independent sub-repositories with CI status, PyPI
packages, and categorized listings.

📖 **[Architecture Guide](https://intellistream.github.io/sage-docs/architecture/)** - Canonical
ownership boundaries and dependency rules for the meta repo

📌
**[Layer Ownership Matrix v1 (Wave A)](https://intellistream.github.io/sage-docs/architecture/layer-ownership/)**
\- Canonical L1-L4 workspace ownership, independent sub-repo coordination boundary (including
`sagellm` capabilities), forbidden directions, and boundary refactor review checklist

## Installation

### Quickstart (Recommended)

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

### Install Mode Semantics

- `standard`：本地安装仓库根目录下的 `isage` meta 包，子仓依赖按根 `pyproject.toml` 版本从 PyPI 解析。
- `dev`：先完成 `standard` 安装，再尽量将同级工作区中的本地 SAGE 子仓库切换为 editable (`-e`)。

### PyPI Install

```bash
pip install isage              # Core framework
pip install isage[dev]         # Development tools (includes in-tree sage-dev, pre-commit, pytest, etc.)
```

**What's included in `pip install isage`**

`isage` now ships the main product surface directly from this repository: `sage.foundation` +
`sage.stream` + `sage.runtime` + `sage.serving` + `sage.cli`. The default local execution path no
longer requires a separate historical runtime split package as a direct dependency. `isagellm`
remains the external inference engine.

`pip install isage` now stays lightweight and does not auto-install `isagellm`.
If you need the external engine integration, install it explicitly via extras:

```bash
pip install 'isage[sagellm]'
```

On Python 3.13+, `isagellm` integration may still be unavailable until the related upstream wheels
are published. Core SAGE stream/runtime development installs and runs independently.

**Core + engine integration only** 🧩

For a standard `pip install isage`, the product center is intentionally narrow:

- **Foundation** → `isage`: in-tree config, ports, paths, contracts
- **Stream + Runtime** → `isage`: main public API and local runtime owned in-tree
- **Distributed scale-out** → in-tree `sage.runtime.flownet`: backend used through `FlowNetEnvironment`
- **CLI** → `isage`: in-tree `sage` command surface
- **Inference Engine** → `isagellm`: external engine; opt-in via `isage[sagellm]`

Compatibility note: transitional imports such as `sage.common`, `sage.platform`, `sage.middleware`,
or `sage.kernel` may still appear in older repos or environments, but they are not part of the root
package's direct dependency contract anymore.

Edge aggregation now also lives in-tree as `sage.edge`; install `isage[serving-edge]` or
`isage[full]` to use the `sage-edge` shell.

**Optional adapter packages** 🦁

These packages are no longer part of the default `isage` install. They remain independent optional
adapters and can be installed explicitly or via `isage[full]` when needed.

Policy note: optional adapters should justify their independence with real owned functionality. Thin
wrapper repos should be folded back into the main `SAGE` repository instead of expanding the default
dependency surface.

Current example: `sage.edge` has already been folded back into the main repo. The former `sage-edge`
split repo should be treated as retired rather than as an independent Zoo package.

```bash
pip install 'isage[serving-edge]'         # in-tree edge shell（sage.edge / sage-edge）
pip install 'isage[capability-adapters]'  # intent / rag / neuromem adapters
pip install 'isage[capability-tooluse]'   # SIAS tool-use adapter
pip install 'isage[full]'                 # all optional adapters + data package

sage-edge --port 8899            # 挂载外部 sagellm gateway 的 edge shell
pip install isage-rag              # RAG 管道（文档加载 / 分块 / 检索 / 重排）
pip install isage-neuromem         # 记忆 / 检索持久化
pip install isage-libs-intent      # 意图识别（关键词 + LLM）
pip install isage-eval             # 评估框架（指标 / LLM 评判）
pip install isage-finetune         # LLM 微调 / Agent training（LoRA / SFT / RL / Reward Model）
pip install isage-agentic-tooluse  # Agent 工具选择（Hybrid/DFS/Gorilla）
pip install 'isage-tools[mcp]'     # 独立工具仓库；当前已注册到 sage-mcp
pip install 'isage-mcp[all]'       # 聚合 MCP Server（当前默认聚合 isage-tools）
```

Example: install full core SAGE stack

```bash
pip install isage
```

See [Dependency Management](./DEVELOPER.md#dependency-management) in DEVELOPER.md for detailed
guidance.

### Verification & Troubleshooting

```bash
sage doctor                    # Check installation
sage verify                    # Verify in-tree core surface
sage chat --help               # Inspect chat entrypoints
sage index ingest --help       # Inspect lightweight index entrypoints
./quickstart.sh --doctor       # Diagnose issues
```

### CLI Command Reference

The current main-repo `sage` command surface is intentionally small and grouped around the core
product boundary:

| Command                                                | Purpose                                                                               |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `sage version`                                         | Print installed SAGE version                                                          |
| `sage status`                                          | Show local config/data/state paths and gateway summary                                |
| `sage doctor`                                          | Run lightweight environment diagnostics                                               |
| `sage verify`                                          | Smoke-check the in-tree core surface                                                  |
| `sage runtime nodes`                                   | List runtime-visible nodes                                                            |
| `sage serve gateway --json`                            | Print the external `sagellm` gateway launch contract                                  |
| `sage serve gateway --probe --json`                    | Probe the configured gateway health endpoint                                          |
| `sage chat`                                            | Start chat via `sagellm` gateway, direct CLI, or configured OpenAI-compatible backend |
| `sage chat --ask "..."`                                | Run one-shot chat                                                                     |
| `sage index ingest --source ./docs --index local-docs` | Record lightweight local index metadata                                               |

```bash
sage verify
sage runtime nodes
sage serve gateway --json
sage chat --ask "Hello, SAGE!"
sage index ingest --source ./docs --index local-docs
```

📖 **Detailed guides**:
[Installation Guide](https://intellistream.github.io/sage-docs/guides/installation/) |
[Troubleshooting](https://intellistream.github.io/sage-docs/guides/troubleshooting/) |
[Validation](https://intellistream.github.io/sage-docs/guides/validation/) |
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

Complete tutorials covering the current workspace tiers of SAGE (L1-L4) plus historical capability
topics:

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
  [https://intellistream.github.io/sage-docs/](https://intellistream.github.io/sage-docs/)
- **Examples & Applications**:
  [intellistream/sage-examples](https://github.com/intellistream/sage-examples)
  - RAG examples and production applications
  - Will be published as `isage-examples` on PyPI
- **Tutorials**: [intellistream/sage-tutorials](https://github.com/intellistream/sage-tutorials)
  - Layered tutorials from L1 to L5, quick-start learning paths
- **Architecture**:
  [sage-docs architecture guide](https://intellistream.github.io/sage-docs/architecture/)

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

**Resources**:
[Quick Reference](https://intellistream.github.io/sage-docs/reference/quick-reference/) |
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

📦 **[sage-docs package guide](https://intellistream.github.io/sage-docs/guides/packages/)** —
独立能力包与安装索引

### 🧠 SAGE — Streaming AI Framework

[![CI](https://github.com/intellistream/SAGE/actions/workflows/ci-build-test.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/ci-build-test.yml)
[![PyPI](https://badge.fury.io/py/isage.svg)](https://pypi.org/project/isage/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Stars](https://img.shields.io/github/stars/intellistream/SAGE?style=social)](https://github.com/intellistream/SAGE/stargazers)

**SAGE** is now centered on an in-tree core product surface rather than on a broad split-repo zoo.

### Core Product Surface (owned in-tree)

- **`sage.foundation`** — config, ports, paths, logging, and shared contracts
- **`sage.stream`** — `DataStream`, transformations, operators, and flow composition
- **`sage.runtime`** — environments, scheduling, job management, and execution lifecycle
- **`sage.serving` / `sage.edge`** — serving integration boundary and edge aggregation shell
- **`sage.cli`** — main `sage` command surface

Legacy split repos and duplicate stream surfaces should be treated as consolidation/retirement
targets rather than as Zoo members.

Independent sub-repositories that remain justified are organized by category:

### Application & UI

- **[sage-examples](https://github.com/intellistream/sage-examples)** — Tutorials and application
  examples
  [![CI](https://github.com/intellistream/sage-examples/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/intellistream/sage-examples/actions/workflows/tests.yml)
  [![Stars](https://img.shields.io/github/stars/intellistream/sage-examples?style=social)](https://github.com/intellistream/sage-examples/stargazers)

### Algorithms & Libraries

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
- **FlowNet (merged in-tree)** — Distributed execution backend now consolidated into this
  repository for SAGE stream runtime

### Data & Benchmarks

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

### Model Optimization & Safety

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

### Developer Tooling

- **In-tree `sage-dev`** — Development CLI and quality tooling now ship directly from this
  repository.
- Historical split repos remain retirement targets and are intentionally omitted from the
  recommended active ecosystem list.

______________________________________________________________________

### ⚡ sageLLM — LLM Inference Engine

[![CI](https://github.com/intellistream/sagellm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/sagellm/actions/workflows/ci.yml)
[![PyPI](https://badge.fury.io/py/isagellm.svg)](https://pypi.org/project/isagellm/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)

sageLLM is a modular, high-performance LLM inference engine. All repositories are 🔒 private and
published to PyPI.

### Core Engine

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

### Gateway & Control

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

### Optimization

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

### Tooling & Benchmarks

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
