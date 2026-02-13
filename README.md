# SAGE - Streaming-Augmented Generative Execution

> A declarative, composable framework for building transparent LLM-powered systems through dataflow
> abstractions.

> 📚 **Documentation Note**: Links referencing `docs-public/` point to the
> [SAGE-Pub](https://github.com/intellistream/SAGE-Pub) repository, which contains comprehensive
> documentation. Clone it separately if needed:
> `git clone https://github.com/intellistream/SAGE-Pub.git`

## 🚀 Quick Start

### Try SAGE Studio

```bash
pip install isage-studio
sage-studio start         # Open http://localhost:4200
```

______________________________________________________________________

[![Build & Test](https://github.com/intellistream/SAGE/actions/workflows/build-test.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/build-test.yml)
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

## Architecture

SAGE is built on a **5-layer modular architecture** with 8 core packages:

```
L5: sage-cli, sage-tools              # CLI & Dev Tools
L4: sage-middleware                   # Operators with C++ extensions
L3: sage-kernel, sage-libs            # Dataflow engine & algorithms
L2: sage-platform                     # Platform services (queue, storage)
L1: sage-common                       # Foundation
```

**Independent Repositories** (not in core):

- **sage-examples**: Tutorials and applications
- **sage-benchmark**: Evaluation framework (PyPI: `isage-benchmark`)
- **sage-studio**: Visual workflow builder (PyPI: `isage-studio`)
- **sageLLM**: LLM inference engine (PyPI: `isagellm`)

📖 **[Architecture Guide](./docs-public/docs_src/dev-notes/package-architecture.md)** - Detailed
design principles and dependency rules

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

**Optional Feature Modules** 🧩

SAGE uses a modular architecture. Core package is minimal; advanced features available through
independent packages:

| Feature            | Package                      | Use Case                                |
| ------------------ | ---------------------------- | --------------------------------------- |
| **Agents**         | `pip install isage-agentic`  | ReAct, PlanExecute, complex reasoning   |
| **RAG**            | `pip install isage-rag`      | Retrieval-augmented generation          |
| **Vector DB**      | `pip install isage-vdb`      | Fast vector search (SageVDB)            |
| **Memory Systems** | `pip install isage-neuromem` | Persistent memory + sessions            |
| **Evaluation**     | `pip install isage-eval`     | Metrics, judges, benchmarking           |
| **Fine-tuning**    | `pip install isage-finetune` | Model adaptation + training             |
| **Privacy**        | `pip install isage-privacy`  | Differential privacy, PII handling      |
| **LLM Gateway**    | `pip install isagellm`       | Control plane, unified inference client |

Example: Build an agentic RAG system

```bash
pip install isage isage-agentic isage-rag isage-vdb isagellm
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
python tutorials/L1-common/hello_world.py

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
