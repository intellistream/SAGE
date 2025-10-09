# SAGE - Streaming-Augmented Generative Execution
> A declarative, composable framework for building transparent LLM-powered systems through dataflow abstractions.

[![CI](https://github.com/intellistream/SAGE/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![PyPI version](https://badge.fury.io/py/isage.svg)](https://badge.fury.io/py/isage)
[![GitHub Issues](https://img.shields.io/github/issues/intellistream/SAGE)](https://github.com/intellistream/SAGE/issues)
[![GitHub Stars](https://img.shields.io/github/stars/intellistream/SAGE?style=social)](https://github.com/intellistream/SAGE/stargazers)

[![WeChat Group](https://img.shields.io/badge/WeChat-加入微信群-brightgreen?style=flat&logo=wechat)](./docs/COMMUNITY.md)
[![QQ Group](https://img.shields.io/badge/【IntelliStream课题组讨论QQ群】-blue?style=flat&logo=tencentqq)](https://qm.qq.com/q/bcnuyQVcvm)
[![Slack](https://img.shields.io/badge/Slack-Join%20Slack-purple?style=flat&logo=slack)](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg)

**SAGE** is a high-performance streaming framework for building AI-powered data processing pipelines. Transform complex LLM reasoning workflows into transparent, scalable, and maintainable systems through declarative dataflow abstractions.

## Why Choose SAGE?

**Production-Ready**: Built for enterprise-scale applications with distributed processing, fault tolerance, and comprehensive monitoring out of the box.

**Developer Experience**: Write complex AI pipelines in just a few lines of code with intuitive declarative APIs that eliminate boilerplate.

**Performance**: Optimized for high-throughput streaming workloads with intelligent memory management and parallel execution capabilities.

**Transparency**: Built-in observability and debugging tools provide complete visibility into execution paths and performance characteristics.

## Quick Start

Transform rigid LLM applications into flexible, observable workflows. Traditional imperative approaches create brittle systems:

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
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.source import FileSource
from sage.libs.rag.retriever import DenseRetriever
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.io_utils.sink import TerminalSink

# Create execution environment  
env = LocalEnvironment("rag_pipeline")

# Build declarative pipeline
(env
    .from_source(FileSource, {"file_path": "questions.txt"})
    .map(DenseRetriever, {"model": "sentence-transformers/all-MiniLM-L6-v2"})
    .map(QAPromptor, {"template": "Answer based on context: {context}\nQ: {query}\nA:"})
    .map(OpenAIGenerator, {"model": "gpt-3.5-turbo"})
    .sink(TerminalSink)
)

# Execute pipeline
env.submit()
```

### Try It Now

Run a simple example to get started:

```bash
# Clone the repository
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# Switch to development branch
git checkout main-dev

# Initialize submodules (automatically switches to correct branch)
./tools/maintenance/sage-maintenance.sh submodule init

# Install with quickstart (recommended)
./quickstart.sh --dev --yes

# Run hello world example
python examples/tutorials/hello_world.py

# Check system status
sage doctor
```

### Why This Matters

**Flexibility**: Modify pipeline structure without touching execution logic. Swap components, add monitoring, or change deployment targets effortlessly.

**Transparency**: See exactly what's happening at each step with built-in observability and debugging tools.

**Performance**: Automatic optimization, parallelization, and resource management based on dataflow analysis.

**Reliability**: Built-in fault tolerance, checkpointing, and error recovery mechanisms.

## Architecture Excellence

### System Architecture

SAGE is built on a layered architecture that provides flexibility, scalability, and maintainability.
The architecture consists of five main layers:

1. **User Layer**: Applications built with SAGE (RAG, Agent, Memory, QA systems)
2. **API Layer**: LocalEnvironment and RemoteEnvironment for different execution contexts
3. **Core Layer**: Dispatcher, Job Manager, Service Manager, and Runtime execution engine
4. **Libraries Layer**: RAG pipeline, Agent framework, Memory & Storage, Middleware components
5. **Infrastructure Layer**: Compute backends (Ray, local), data storage, model services, monitoring

### Modular Design
SAGE follows a clean separation of concerns with pluggable components that work together seamlessly:

- **Core**: Stream processing engine with execution environments
- **Libraries**: Rich operators for AI, I/O, transformations, and utilities  
- **Kernel**: Distributed computing primitives and communication
- **Middleware**: Service discovery, monitoring, and management
- **Common**: Shared utilities, configuration, and logging

### Production-Ready Features
Built for real-world deployments with enterprise requirements:
- **Distributed Execution**: Scale across multiple nodes with automatic load balancing
- **Fault Tolerance**: Comprehensive error handling and recovery mechanisms
- **Observability**: Detailed metrics, logging, and performance monitoring
- **Security**: Authentication, authorization, and data encryption support
- **Integration**: Native connectors for popular databases, message queues, and AI services

## Installation

We offer an interactive installer and explicit command flags. Developer mode is recommended when contributing.

**Clone & Interactive Mode**
```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE
./quickstart.sh            # Opens interactive menu
```

**Common Non-Interactive Modes**
```bash
# Developer installation
./quickstart.sh --dev --yes

# Minimal core only
./quickstart.sh --minimal --yes

# Standard + vLLM support
./quickstart.sh --standard --vllm --yes

# Use system Python instead of conda
./quickstart.sh --minimal --pip --yes

# View all flags
./quickstart.sh --help
```

**Quick PyPI Install**
```bash
# Choose your installation mode:
pip install isage[minimal]   # Core functionality  
pip install isage[standard]  # Full features
pip install isage[dev]       # Everything + development tools
```

> Note: PyPI install may not include all system dependencies; use quickstart.sh for complete environment setup.

**Key Installation Features**
- 🎯 Interactive menu for first-time users
- 🤖 vLLM integration with `--vllm`
- 🐍 Supports conda or system Python via `--pip`
- ⚡ Three modes: minimal / standard / dev

## Environment Configuration

After installation, configure your API keys and environment settings:

**Quick Setup**
```bash
# Run the interactive environment setup
python -m sage.tools.cli.main config env setup
```

**Manual Setup**
```bash
# Copy the environment template
cp .env.template .env

# Edit .env and add your API keys
# Required for most examples:
OPENAI_API_KEY=your_openai_api_key_here
HF_TOKEN=your_huggingface_token_here
```

**Environment Variables**
- `OPENAI_API_KEY`: Required for GPT models and most LLM examples
- `HF_TOKEN`: Required for Hugging Face model downloads
- `SILICONCLOUD_API_KEY`: For alternative LLM services
- `JINA_API_KEY`: For embedding services
- `ALIBABA_API_KEY`: For DashScope models
- `SAGE_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `SAGE_TEST_MODE`: Enable test mode for examples

**API Key Sources**
- Get OpenAI API key: https://platform.openai.com/api-keys
- Get Hugging Face token: https://huggingface.co/settings/tokens

The `.env` file is automatically ignored by git to keep your keys secure.


## Use Cases

**RAG Applications**: Build production-ready retrieval-augmented generation systems with multi-modal support and advanced reasoning capabilities.

**Real-Time Analytics**: Process streaming data with AI-powered insights, anomaly detection, and automated decision making.

**Data Pipeline Orchestration**: Coordinate complex ETL workflows that seamlessly integrate AI components with traditional data processing.

**Multi-Modal Processing**: Handle text, images, audio, and structured data in unified pipelines with consistent APIs. **🆕 Advanced multimodal fusion** enables intelligent combination of different data modalities for enhanced AI understanding and generation.

**Distributed AI Inference**: Scale AI model serving across multiple nodes with automatic load balancing and fault tolerance.


> 本地代码质量/测试请使用 `sage dev quality` 或 `sage dev test`，CI/CD 由 GitHub Workflows 自动完成。

## Documentation & Resources

- **Documentation Site**: [https://intellistream.github.io/SAGE-Pub/](https://intellistream.github.io/SAGE-Pub/)
- **Examples**: [examples/](./examples/) (tutorials, rag, service, memory, etc.)
- **Configurations**: [examples/config/](./examples/config/) sample pipeline configs
- **Quick Reference**: [docs/QUICK_REFERENCE.md](./docs/QUICK_REFERENCE.md)
- **Contribution Guide**: [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Changelog (planned)**: Add a `CHANGELOG.md` (see suggestions below)

## Contributing

We welcome contributions! Please review the updated guidelines before opening a Pull Request.

**Essential Links**
- 🚀 Quick Reference: [docs/QUICK_REFERENCE.md](./docs/QUICK_REFERENCE.md)
- 📚 Contribution Guide: [CONTRIBUTING.md](./CONTRIBUTING.md)
- 🐛 Issues & Features: [GitHub Issues](https://github.com/intellistream/SAGE/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/intellistream/SAGE/discussions)

**Quick Contributor Flow**
```bash
git fetch origin
git checkout main-dev
git pull --ff-only origin main-dev
git checkout -b fix/<short-topic>
./quickstart.sh --dev --yes          # ensure dev deps installed
bash tools/tests/run_examples_tests.sh
pytest -k issues_manager -vv
git add <changed-files>
git commit -m "fix(sage-kernel): correct dispatcher edge case"
git push -u origin fix/<short-topic>
# Open PR: include background / solution / tests / impact
```

> See `CONTRIBUTING.md` for full commit conventions, branch naming, and test matrices.

## Developer Shortcuts

SAGE provides convenient Make-like commands for common development tasks:

```bash
# View all available commands
make help
# or
./dev.sh help

# Code quality
make lint          # Run code checks
make format        # Format code
make quality       # Full quality check

# Testing
make test          # Run all tests
make test-quick    # Quick tests only
make test-all      # Full test suite with coverage

# Build & Deploy
make build         # Build packages
make clean         # Clean build artifacts
make publish       # Publish to TestPyPI
make version       # Show current version

# Documentation
make docs          # Build documentation
make docs-serve    # Serve docs locally
```

**See [docs/dev-notes/DEV_COMMANDS.md](./docs/dev-notes/DEV_COMMANDS.md) for complete command reference and workflows.**

**Post-Install Diagnostics**
```bash
sage doctor          # Runs environment & module checks
python -c "import sage; print(sage.__version__)"
```

## 🤝 Join Our Community

Connect with other SAGE developers, get help, and stay updated on the latest developments:

**💬 [Join SAGE Community](./docs/COMMUNITY.md)** - Complete guide to all our communication channels

Quick links:
- **WeChat Group**: Scan QR codes for instant chat (Chinese/English)
- **QQ Group**: [IntelliStream课题组讨论群](https://qm.qq.com/q/bcnuyQVcvm)
- **Slack**: [Join our workspace](https://join.slack.com/t/intellistream/shared_invite/zt-2qayp8bs7-v4F71ge0RkO_rn34hBDWQg)
- **GitHub Discussions**: [Technical Q&A and feature requests](https://github.com/intellistream/SAGE/discussions)

We welcome questions, bug reports, feature requests, and contributions from developers worldwide!

## License

SAGE is licensed under the [MIT License](./LICENSE).
