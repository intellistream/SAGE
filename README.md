# SAGE - Streaming-Augmented Generative Execution
> A declarative, composable framework for building transparent LLM-powered systems through dataflow abstractions.
[![CI](https://github.com/intellistream/SAGE/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/intellistream/SAGE/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![PyPI version](https://badge.fury.io/py/isage.svg)](https://badge.fury.io/py/isage)
[![GitHub Issues](https://img.shields.io/github/issues/intellistream/SAGE)](https://github.com/intellistream/SAGE/issues)
[![GitHub Stars](https://img.shields.io/github/stars/intellistream/SAGE?style=social)](https://github.com/intellistream/SAGE/stargazers)

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

### Why This Matters

**Flexibility**: Modify pipeline structure without touching execution logic. Swap components, add monitoring, or change deployment targets effortlessly.

**Transparency**: See exactly what's happening at each step with built-in observability and debugging tools.

**Performance**: Automatic optimization, parallelization, and resource management based on dataflow analysis.

**Reliability**: Built-in fault tolerance, checkpointing, and error recovery mechanisms.

## Architecture Excellence

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

We offer an interactive installer and explicit command flags. Developer (dev) mode is recommended when contributing.

**Clone & Interactive Mode (Recommended)**
```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE
./quickstart.sh            # Opens interactive menu
```

**Common Non-Interactive Modes**
```bash
# Developer installation (editable packages + dev tools: pytest, black, mypy, pre-commit)
./quickstart.sh --dev --yes

# Minimal core only (no scientific extras)
./quickstart.sh --minimal --yes

# Standard + vLLM support
./quickstart.sh --standard --vllm --yes

# Use system Python instead of conda (not isolated)
./quickstart.sh --minimal --pip --yes

# View all flags
./quickstart.sh --help
```

**Quick PyPI Install (Runtime Use Only)**
```bash
pip install isage
sage doctor   # Basic environment diagnostics (if CLI installed)
```

> Note: PyPI install may not include optional components (e.g., vLLM); use quickstart for full capability.

**Key Installation Features**
- 🎯 Interactive menu for first-time users
- 🤖 Optional vLLM integration with `--vllm`
- 🐍 Supports conda (default) or system Python via `--pip`
- ⚡ Three modes: minimal / standard / dev

## Environment Configuration

After installation, configure your API keys and environment settings:

**Quick Setup**
```bash
# Run the interactive environment setup
./tools/setup_env.sh
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

**Multi-Modal Processing**: Handle text, images, audio, and structured data in unified pipelines with consistent APIs.

**Distributed AI Inference**: Scale AI model serving across multiple nodes with automatic load balancing and fault tolerance.

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

**Post-Install Diagnostics**
```bash
sage doctor          # Runs environment & module checks
python -c "import sage; print(sage.__version__)"
```

**Common Make-Like Aliases (Optional)**
Consider adding wrapper scripts (future enhancement) for: `lint`, `format`, `test:quick`, `test:all`.

## Suggested Future Improvements (Documentation & Tooling)

- Add `CHANGELOG.md` with Keep a Changelog format.
- Introduce `pre-commit` config (black, isort, ruff/mypy, shellcheck).
- Provide `scripts/dev.sh` helper with common commands.
- Add architecture diagram (docs/images/architecture.svg) referenced here.
- Offer Dockerfile + reproducible container instructions.

## License

SAGE is licensed under the [MIT License](./LICENSE).
