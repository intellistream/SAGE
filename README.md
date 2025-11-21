# SAGE - Streaming-Augmented Generative Execution

> A declarative, composable framework for building transparent LLM-powered systems through dataflow
> abstractions.

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

**Production-Ready**: Built for enterprise-scale applications with distributed processing, fault
tolerance, and comprehensive monitoring out of the box.

**Developer Experience**: Write complex AI pipelines in just a few lines of code with intuitive
declarative APIs that eliminate boilerplate.

**Performance**: Optimized for high-throughput streaming workloads with intelligent memory
management and parallel execution capabilities.

**Transparency**: Built-in observability and debugging tools provide complete visibility into
execution paths and performance characteristics.

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
from sage.middleware.operators.rag import DenseRetriever, QAPromptor, OpenAIGenerator
from sage.libs.io.sink import TerminalSink

# Create execution environment
env = LocalEnvironment("rag_pipeline")

# Build declarative pipeline
(
    env.from_source(FileSource, {"file_path": "questions.txt"})
    .map(DenseRetriever, {"model": "sentence-transformers/all-MiniLM-L6-v2"})
    .map(QAPromptor, {"template": "Answer based on context: {context}\nQ: {query}\nA:"})
    .map(OpenAIGenerator, {"model": "gpt-3.5-turbo"})
    .sink(TerminalSink)
)

# Execute pipeline
env.submit()
```

**Try it yourself:**

```bash
git clone https://github.com/intellistream/SAGE.git && cd SAGE
git checkout main-dev
./quickstart.sh --dev --yes
python examples/tutorials/hello_world.py
```

## Architecture Excellence

### System Architecture

SAGE is built on a **layered modular architecture** with 11 independent packages organized across 6
layers:

```
L6: sage-studio, sage-cli, sage-tools    # User Interfaces & Dev Tools
L5: sage-apps, sage-benchmark             # Applications & Benchmarks
L4: sage-middleware, sage-gateway         # Domain Operators & API Gateway
L3: sage-kernel, sage-libs                # Core Engine & Algorithm Library
L2: sage-platform                         # Platform Services (Queue, Storage)
L1: sage-common                           # Foundation & Utilities
```

**Key Architectural Principles:**

- **Unidirectional Dependencies**: Clean layer-to-layer dependencies (no upward dependencies)
- **Separation of Concerns**: Each package has a clear, focused responsibility
- **Pluggable Components**: Modular design allows easy component replacement
- **Production Ready**: Built-in fault tolerance, monitoring, and distributed execution

📖 **[Complete Architecture Guide](./docs-public/docs_src/dev-notes/package-architecture.md)** -
Detailed package descriptions, dependency rules, and design principles

### Modular Design

**11 Independent Packages**, each with clear responsibilities:

- **sage-common** (L1): Foundation utilities, configuration, logging
- **sage-platform** (L2): Platform services - queue, storage abstractions
- **sage-kernel** (L3): Distributed execution engine and runtime
- **sage-libs** (L3): Algorithm library, RAG tools, Agent framework
- **sage-middleware** (L4): Domain operators and middleware components
- **sage-gateway** (L4): API gateway and service mesh
- **sage-apps** (L5): Pre-built applications (video, medical diagnosis)
- **sage-benchmark** (L5): Performance benchmarks and examples
- **sage-studio** (L6): Web-based visualization interface
- **sage-cli** (L6): Unified command-line interface
- **sage-tools** (L6): Development tools and testing framework

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
[Troubleshooting](docs/TROUBLESHOOTING.md) | [Validation](docs/INSTALLATION_VALIDATION.md)

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

## Documentation & Resources

- **Documentation**:
  [https://intellistream.github.io/SAGE-Pub/](https://intellistream.github.io/SAGE-Pub/)
- **Examples**: [examples/](./examples/) - Tutorials, RAG, services, benchmarks
- **Quick Reference**: [docs/QUICK_REFERENCE.md](./docs/QUICK_REFERENCE.md)
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

## Developer Tools

```bash
make help           # View all commands
sage-dev quality    # Format & lint
sage-dev test       # Run tests
make docs           # Build documentation
```

📖 **Complete reference**: [docs/dev-notes/DEV_COMMANDS.md](./docs/dev-notes/DEV_COMMANDS.md)

## Community

**💬 [Join SAGE Community](./docs/COMMUNITY.md)** - WeChat, QQ, Slack, GitHub Discussions

## License

SAGE is licensed under the [MIT License](./LICENSE).
