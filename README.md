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

**Quick Setup:**
```bash
# Install with guided setup
pip install isage && sage doctor
```

**From Source:**
```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE
./quickstart.sh
```

## Use Cases

**RAG Applications**: Build production-ready retrieval-augmented generation systems with multi-modal support and advanced reasoning capabilities.

**Real-Time Analytics**: Process streaming data with AI-powered insights, anomaly detection, and automated decision making.

**Data Pipeline Orchestration**: Coordinate complex ETL workflows that seamlessly integrate AI components with traditional data processing.

**Multi-Modal Processing**: Handle text, images, audio, and structured data in unified pipelines with consistent APIs.

**Distributed AI Inference**: Scale AI model serving across multiple nodes with automatic load balancing and fault tolerance.

## Documentation & Resources

- **Documentation**: [https://intellistream.github.io/SAGE-Pub/](https://intellistream.github.io/SAGE-Pub/)
- **Examples**: [examples/](./examples/) directory with tutorials and use cases
- **Configuration**: [config/](./config/) directory with sample configurations
- **Installation Guide**: [INSTALL_GUIDE.md](INSTALL_GUIDE.md)

## Contributing

**Bug Reports & Feature Requests**: [GitHub Issues](https://github.com/intellistream/SAGE/issues)  
**Code Contributions**: Submit pull requests  
**Community Support**: [GitHub Discussions](https://github.com/intellistream/SAGE/discussions)

## License

SAGE is licensed under the [MIT License](./LICENSE).
