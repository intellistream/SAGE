# SAGE - Streaming-Augmented Generative Execution

> A declarative, composable framework for building transparent LLM-powered systems through dataflow
> abstractions.

## 🚀 Quick Start

### Try SAGE Studio

**Option 1: HUST Campus Network Access** 🎓

Our team maintains a live deployment accessible within HUST campus network:

```
🌐 Contact team for access URL
```

**Requirements**: HUST campus network or VPN connection

Experience SAGE's visual pipeline editor and AI-powered chat assistant with RAG capabilities!

**Option 2: Local Installation**

```bash
# 1. Install SAGE Studio (independent package)
pip install isage-studio

# 2. Start SAGE Studio
sage-studio start
# Visit http://localhost:4200
```

> 💡 **Note**: SAGE Studio is an independent package. For SAGE core framework installation, see
> [Installation](#installation) section below.

______________________________________________________________________

[![Build & Test](https://github.com/intellistream/SAGE/actions/workflows/build-test.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/build-test.yml)
[![codecov](https://codecov.io/gh/intellistream/SAGE/branch/main/graph/badge.svg)](https://codecov.io/gh/intellistream/SAGE)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![PyPI version](https://badge.fury.io/py/isage.svg)](https://badge.fury.io/py/isage)
[![GitHub Issues](https://img.shields.io/github/issues/intellistream/SAGE)](https://github.com/intellistream/SAGE/issues)
[![GitHub Stars](https://img.shields.io/github/stars/intellistream/SAGE?style=social)](https://github.com/intellistream/SAGE/stargazers)

[![WeChat Group](https://img.shields.io/badge/WeChat-%E5%8A%A0%E5%85%A5%E5%BE%AE%E4%BF%A1%E7%BE%A4-brightgreen?style=flat&logo=wechat)](./docs/COMMUNITY.md)
[![QQ Group](https://img.shields.io/badge/%E3%80%90IntelliStream%E8%AF%BE%E9%A2%98%E7%BB%84%E8%AE%A8%E8%AE%BAQQ%E7%BE%A4%E3%80%91-blue?style=flat&logo=tencentqq)](https://qm.qq.com/q/bcnuyQVcvm)
[![Slack](https://img.shields.io/badge/Slack-Join%20Slack-purple?style=flat&logo=slack)](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg)

**SAGE** is a high-performance streaming framework for building AI-powered data processing
pipelines. Transform complex LLM reasoning workflows into transparent, scalable, and maintainable
systems through declarative dataflow abstractions.

## Why Choose SAGE?

## Project Team & Collaboration

See `docs-public/docs_src/dev-notes/cross-layer/team-management.md` for the current team
coordination entrypoint (team management + incubation policy).

**Production-Ready**: Built for enterprise-scale applications with distributed processing, fault
tolerance, and comprehensive monitoring out of the box.

**Developer Experience**: Write complex AI pipelines in just a few lines of code with intuitive
declarative APIs that eliminate boilerplate.

**Performance**: Optimized for high-throughput streaming workloads with intelligent memory
management and parallel execution capabilities.

**Transparency**: Built-in observability and debugging tools provide complete visibility into
execution paths and performance characteristics.

**Flexible Deployment**: Full support for CPU-only compute nodes alongside GPU nodes, with
intelligent resource-aware scheduling for hybrid clusters.

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
from sage.libs.io.source import FileSource
from sage.middleware.operators.rag import DenseRetriever, QAPromptor
from sage.middleware.operators.llm import SageLLMGenerator  # ✅ Recommended
from sage.libs.io.sink import TerminalSink

# Create execution environment
env = LocalEnvironment("rag_pipeline")

# Build declarative pipeline with sageLLM (recommended)
(
    env.from_source(FileSource, {"file_path": "questions.txt"})
    .map(DenseRetriever, {"model": "sentence-transformers/all-MiniLM-L6-v2"})
    .map(QAPromptor, {"template": "Answer based on context: {context}\nQ: {query}\nA:"})
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
> use `OpenAIGenerator`. See
> [Migration Guide](./docs-public/docs_src/dev-notes/migration/VLLM_TO_SAGELLM_MIGRATION.md) if
> migrating from vLLM.

**Try it yourself:**

```bash
git clone https://github.com/intellistream/SAGE.git && cd SAGE
git checkout main-dev
./quickstart.sh --dev --yes

# Examples are now in a separate repository
git clone https://github.com/intellistream/sage-examples.git
python sage-examples/tutorials/hello_world.py
```

**For CPU-only deployment:**

```bash
# Start JobManager for distributed task execution
sage jobmanager start

# Run CPU node demo (no GPU required)
git clone https://github.com/intellistream/sage-examples.git
python sage-examples/tutorials/L3-kernel/cpu_node_demo.py
```

## Architecture Excellence

### System Architecture

SAGE is built on a **layered modular architecture** with 8 core packages organized across 5 layers:

```
L5: sage-cli, sage-tools                  # Interface Layer (CLI & Dev Tools)
L4: sage-middleware                       # Middleware Layer (Operators, C++ Extensions)
L3: sage-kernel, sage-libs                # Core Layer (Engine & Algorithm Library)
L2: sage-platform                         # Platform Layer (Queue, Storage)
L1: sage-common                           # Foundation Layer (Config, Types, Utilities)
```

**Independent Repositories** (not in SAGE core):

- **sage-benchmark**: https://github.com/intellistream/sage-benchmark (PyPI: `isage-benchmark`)
- **sage-examples**: https://github.com/intellistream/sage-examples (Tutorials & Applications)
- **sage-studio**: https://github.com/intellistream/sage-studio (PyPI: `isage-studio`)
- **sageLLM**: LLM inference engine (PyPI: `isagellm`)
- **SageEdge**: Edge aggregator for distributed deployment (PyPI: `isage-edge`)

**Optional Dependencies** (independent PyPI packages):

*sage-middleware optional dependencies:*

| Package      | PyPI             | Category      | Description                                 |
| ------------ | ---------------- | ------------- | ------------------------------------------- |
| **SageVDB**  | `isage-vdb`      | `[vdb]`       | High-performance C++ vector database        |
| **NeuroMem** | `isage-neuromem` | `[neuromem]`  | Brain-inspired memory system (VDB/KV/Graph) |
| **SageFlow** | `isage-flow`     | `[streaming]` | Vector-native stream processing engine      |
| **SageTSDB** | `isage-tsdb`     | `[streaming]` | Time-series database with C++ core          |

*sage-libs optional dependencies (L3 algorithm libraries):*

| Package         | PyPI            | Category   | Description                                                 |
| --------------- | --------------- | ---------- | ----------------------------------------------------------- |
| **SageANNS**    | `isage-anns`    | `[anns]`   | Approximate nearest neighbor search algorithms              |
| **SageAMMs**    | `isage-amms`    | `[amms]`   | Approximate matrix multiplication                           |
| **SageRefiner** | `isage-refiner` | `[libs]`\* | Context compression for RAG (LongRefiner, REFORM, Provence) |

> \* SageRefiner is an L3 algorithm library, also available via `isage-middleware[libs]`

```bash
# Install with specific optional dependencies
pip install isage-middleware[vdb]           # Vector database support
pip install isage-middleware[streaming]     # Stream processing + time-series
pip install isage-libs[anns]                # ANNS algorithms
pip install isage-libs[amms]                # AMM algorithms
```

**Key Architectural Principles:**

- **Unidirectional Dependencies**: Clean layer-to-layer dependencies (no upward dependencies)
- **Separation of Concerns**: Each package has a clear, focused responsibility
- **Pluggable Components**: Modular design allows easy component replacement
- **Production Ready**: Built-in fault tolerance, monitoring, and distributed execution

📖 **[Complete Architecture Guide](./docs-public/docs_src/dev-notes/package-architecture.md)** -
Detailed package descriptions, dependency rules, and design principles

### Modular Design

**8 Core Packages**, each with clear responsibilities:

- **sage** (meta): Meta-package that installs all SAGE components
- **sage-common** (L1): Foundation utilities, configuration, logging
- **sage-platform** (L2): Platform services - queue, storage abstractions
- **sage-kernel** (L3): Distributed execution engine and runtime
- **sage-libs** (L3): Algorithm library, RAG tools, Agent framework
- **sage-middleware** (L4): Domain operators and middleware components
- **sage-cli** (L5): Unified command-line interface (`sage` command)
- **sage-tools** (L5): Development tools and testing framework (`sage-dev` command)

**Independent Repositories:**

- **sage-examples**: Tutorials, examples, and production applications
  - Repository: [intellistream/sage-examples](https://github.com/intellistream/sage-examples)
  - Includes: tutorials, RAG examples, application demos
- **sage-benchmark**: Evaluation framework (PyPI: `isage-benchmark`)
  - Repository: [intellistream/sage-benchmark](https://github.com/intellistream/sage-benchmark)
- **sage-studio**: Visual workflow builder (PyPI: `isage-studio`)
  - Repository: [intellistream/sage-studio](https://github.com/intellistream/sage-studio)
- **sageLLM**: LLM inference engine (PyPI: `isagellm`)

> 💡 **Note**: All PyPI packages use `isage-` prefix (e.g., `pip install isage-vdb`) because `sage`
> is already taken on PyPI.

### Production Features

- **Distributed Execution** with automatic load balancing
- **Fault Tolerance** and error recovery
- **Observability** with metrics and monitoring
- **Extensible Integration** for databases, queues, and AI services

## Installation

**Quickstart (Recommended)**

```bash
git clone https://github.com/intellistream/SAGE.git && cd SAGE
./quickstart.sh --dev --yes    # Interactive mode: ./quickstart.sh
```

⚡ **Auto-Acceleration**: Network optimization is now **enabled by default**:

- 🌐 Auto-detects network location (China mainland → mirror sources)
- 🚀 Parallel downloads (8 threads) + pre-compiled packages
- ⏱️ **3-5x faster** installation: 12-18 min (vs 35-45 min)
- 🔧 Disable: `./quickstart.sh --no-mirror --dev --yes`

**PyPI Install**

```bash
pip install isage[standard]    # Recommended
pip install isage[core]        # Minimal runtime
pip install isage[full]        # Full features + Web UI
pip install isage[dev]         # Development tools
```

**Verification & Troubleshooting**

```bash
sage doctor                    # Check installation
./quickstart.sh --doctor       # Diagnose issues
```

📖 **Detailed guides**: [Installation Guide](docs/INSTALLATION_GUIDE.md) |
[Troubleshooting](docs/TROUBLESHOOTING.md) | [Validation](docs/INSTALLATION_VALIDATION.md) |
[Optimization Tips](tools/install/docs/INSTALLATION_OPTIMIZATION.md)

⚠️ **Known Issues**: If you encounter transformers version conflicts when installing multiple SAGE
packages, see [Dependency Fix Guide](docs-public/docs_src/getting-started/DEPENDENCY_FIX.md)

## Environment Configuration

```bash
cp .env.template .env    # Copy template
# Edit .env and add your API keys (OPENAI_API_KEY, HF_TOKEN, etc.)
```

📖 **API key setup**: See [.env.template](./.env.template) for all available options

## Use Cases

**RAG Applications**: Build production-ready retrieval-augmented generation systems with multi-modal
support and advanced reasoning capabilities.

**Real-Time Analytics**: Process streaming data with AI-powered insights, anomaly detection, and
automated decision making.

**Data Pipeline Orchestration**: Coordinate complex ETL workflows that seamlessly integrate AI
components with traditional data processing.

**Multi-Modal Processing**: Handle text, images, audio, and structured data in unified pipelines
with consistent APIs. **🆕 Advanced multimodal fusion** enables intelligent combination of different
data modalities for enhanced AI understanding and generation.

**Distributed AI Inference**: Scale AI model serving across multiple nodes with automatic load
balancing and fault tolerance.

## 📚 Tutorials

Complete tutorials covering all layers of SAGE (L1-L5):

```bash
# Clone repository
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# Start learning (30 seconds)
python tutorials/hello_world.py

# Follow the quick start guide
cat tutorials/QUICK_START.md
```

**Tutorial Structure**:

- `tutorials/L1-common/` - Foundation layer (config, logging, unified client)
- `tutorials/L2-platform/` - Platform services (scheduler, storage)
- `tutorials/L3-kernel/` - Execution engine (batch, stream, operators)
- `tutorials/L3-libs/` - RAG, Agents, Algorithms
- `tutorials/L4-middleware/` - Domain operators (vector DB, time-series)
- `tutorials/L5-cli/` - CLI and development tools

See `tutorials/README.md` for complete learning paths.

## Documentation & Resources

- **Documentation**:
  [https://intellistream.github.io/SAGE-Pub/](https://intellistream.github.io/SAGE-Pub/)
- **Examples & Applications**:
  [intellistream/sage-examples](https://github.com/intellistream/sage-examples)
  - Tutorials, RAG examples, and production applications
  - Will be published as `isage-examples` on PyPI
- **Architecture**:
  [docs-public/docs_src/dev-notes/package-architecture.md](./docs-public/docs_src/dev-notes/package-architecture.md)

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

📖 **Complete reference**: [docs/dev-notes/DEV_COMMANDS.md](./docs/dev-notes/DEV_COMMANDS.md)

## SAGE Ecosystem

SAGE has a growing ecosystem of independent projects:

- **[SAGE Studio](https://github.com/intellistream/sage-studio)** - Visual workflow builder and LLM
  playground for creating AI pipelines with drag-and-drop interface
- **[SAGE Benchmark](https://github.com/intellistream/sage-benchmark)** - Comprehensive evaluation
  framework for RAG, agents, control plane, and memory systems

These projects depend on SAGE core packages and can be installed separately via PyPI.

## Community

**💬 [Join SAGE Community](./docs/COMMUNITY.md)** - WeChat, QQ, Slack, GitHub Discussions

## License

SAGE is licensed under the [MIT License](./LICENSE).
