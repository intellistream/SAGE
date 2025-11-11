# SAGE Benchmark

> Comprehensive benchmarking tools and RAG examples for the SAGE framework

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)

## 📋 Overview

**SAGE Benchmark** provides a comprehensive suite of benchmarking tools and RAG (Retrieval-Augmented
Generation) examples for evaluating SAGE framework performance. This package enables researchers and
developers to:

- **Benchmark RAG pipelines** with multiple retrieval strategies (dense, sparse, hybrid)
- **Compare vector databases** (Milvus, ChromaDB, FAISS) for RAG applications
- **Evaluate multimodal retrieval** with text, image, and video data
- **Run reproducible experiments** with standardized configurations and metrics

This package is designed for both research experiments and production system evaluation.

## ✨ Key Features

- **Multiple RAG Implementations**: Dense, sparse, hybrid, and multimodal retrieval
- **Vector Database Support**: Milvus, ChromaDB, FAISS integration
- **Experiment Framework**: Automated benchmarking with configurable experiments
- **Evaluation Metrics**: Comprehensive metrics for RAG performance
- **Sample Data**: Included test data for quick start
- **Extensible Design**: Easy to add new benchmarks and retrieval methods

## 📦 Package Structure

```
sage-benchmark/
├── src/
│   └── sage/
│       └── benchmark/
│           ├── __init__.py
│           └── benchmark_rag/           # RAG benchmarking
│               ├── __init__.py
│               ├── implementations/     # RAG implementations
│               │   ├── pipelines/      # RAG pipeline scripts
│               │   │   ├── qa_dense_retrieval_milvus.py
│               │   │   ├── qa_sparse_retrieval_milvus.py
│               │   │   ├── qa_multimodal_fusion.py
│               │   │   └── ...
│               │   └── tools/          # Supporting tools
│               │       ├── build_chroma_index.py
│               │       ├── build_milvus_dense_index.py
│               │       └── loaders/
│               ├── evaluation/          # Experiment framework
│               │   ├── pipeline_experiment.py
│               │   ├── evaluate_results.py
│               │   └── config/
│               ├── config/              # RAG configurations
│               └── data/                # Test data
│           # Future benchmarks:
│           # ├── benchmark_agent/      # Agent benchmarking
│           # └── benchmark_anns/       # ANNS benchmarking
├── tests/
├── pyproject.toml
└── README.md
```

## 🚀 Installation

### Prerequisites

The benchmark package depends on the `sage-data` package for datasets (including LibAMM datasets).
First install the data package:

```bash
# Install sage-data from the submodule
pip install -e packages/sage-benchmark/src/sage/data
```

### Install Benchmark Package

Then install the benchmark package:

```bash
pip install -e packages/sage-benchmark
```

Or with development dependencies:

```bash
pip install -e "packages/sage-benchmark[dev]"
```

**Note:** The `sage-data` package must be installed before using benchmarks that require datasets
(e.g., LibAMM benchmarks with `sage.data.locomo` imports).

## 📊 RAG Benchmarking

The benchmark_rag module provides comprehensive RAG benchmarking capabilities:

### RAG Implementations

Various RAG approaches for performance comparison:

**Vector Databases:**

- **Milvus**: Dense, sparse, and hybrid retrieval
- **ChromaDB**: Local vector database with simple setup
- **FAISS**: Efficient similarity search

**Retrieval Methods:**

- Dense retrieval (embeddings-based)
- Sparse retrieval (BM25, sparse vectors)
- Hybrid retrieval (combining dense + sparse)
- Multimodal fusion (text + image + video)

### Quick Start

#### 1. Build Vector Index

First, prepare your vector index:

```bash
# Build ChromaDB index (simplest)
python -m sage.benchmark.benchmark_rag.implementations.tools.build_chroma_index

# Or build Milvus dense index
python -m sage.benchmark.benchmark_rag.implementations.tools.build_milvus_dense_index
```

#### 2. Run a RAG Pipeline

Test individual RAG pipelines:

```bash
# Dense retrieval with Milvus
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval_milvus

# Sparse retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_sparse_retrieval_milvus

# Hybrid retrieval (dense + sparse)
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_hybrid_retrieval_milvus
```

#### 3. Run Benchmark Experiments

Execute full benchmark suite:

```bash
# Run comprehensive benchmark
python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment

# Evaluate and generate reports
python -m sage.benchmark.benchmark_rag.evaluation.evaluate_results
```

#### 4. View Results

Results are saved in `benchmark_results/`:

- `experiment_TIMESTAMP/` - Individual experiment runs
- `metrics.json` - Performance metrics
- `comparison_report.md` - Comparison report

## 📖 Quick Start

### Basic Example

```python
from sage.benchmark.benchmark_rag.implementations.pipelines import (
    qa_dense_retrieval_milvus,
)
from sage.benchmark.benchmark_rag.config import load_config

# Load configuration
config = load_config("config_dense_milvus.yaml")

# Run RAG pipeline
results = qa_dense_retrieval_milvus.run_pipeline(query="What is SAGE?", config=config)

# View results
print(f"Retrieved {len(results)} documents")
for doc in results:
    print(f"- {doc.content[:100]}...")
```

### Run Custom Benchmark

```python
from sage.benchmark.benchmark_rag.evaluation import PipelineExperiment

# Define experiment configuration
experiment = PipelineExperiment(
    name="custom_rag_benchmark",
    pipelines=["dense", "sparse", "hybrid"],
    queries=["query1.txt", "query2.txt"],
    metrics=["precision", "recall", "latency"],
)

# Run experiment
results = experiment.run()

# Generate report
experiment.generate_report(results)
```

### Configuration

Configuration files are located in `sage/benchmark/benchmark_rag/config/`:

- `config_dense_milvus.yaml` - Dense retrieval configuration
- `config_sparse_milvus.yaml` - Sparse retrieval configuration
- `config_hybrid_milvus.yaml` - Hybrid retrieval configuration
- `config_qa_chroma.yaml` - ChromaDB configuration

Experiment configurations in `sage/benchmark/benchmark_rag/evaluation/config/`:

- `experiment_config.yaml` - Benchmark experiment settings

## 📖 Data

Test data is included in the package:

- **Benchmark Data** (`benchmark_rag/data/`):

  - `queries.jsonl` - Sample queries for testing
  - `qa_knowledge_base.*` - Knowledge base in multiple formats (txt, md, pdf, docx)
  - `sample/` - Additional sample documents for testing
  - `sample/` - Additional sample documents

- **Benchmark Config** (`benchmark_rag/config/`):

  - `experiment_config.yaml` - RAG benchmark configurations

## 🔧 Development

### Running Tests

```bash
pytest packages/sage-benchmark/
```

### Code Formatting

```bash
# Format code
black packages/sage-benchmark/

# Lint code
ruff check packages/sage-benchmark/
```

## 📚 Documentation

For detailed documentation on each component:

- See `src/sage/benchmark/rag/README.md` for RAG examples
- See `src/sage/benchmark/benchmark_rag/README.md` for benchmark details

## 🔮 Future Components

- **benchmark_agent**: Agent system performance benchmarking
- **benchmark_anns**: Approximate Nearest Neighbor Search benchmarking
- **benchmark_llm**: LLM inference performance benchmarking

## 🤝 Contributing

This package follows the same contribution guidelines as the main SAGE project. See the main
repository's `CONTRIBUTING.md`.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🔗 Related Packages

- **sage-kernel**: Core computation engine for running benchmarks
- **sage-libs**: RAG components and utilities
- **sage-middleware**: Vector database services (Milvus, ChromaDB)
- **sage-common**: Common utilities and data types

## 📮 Support

- **Documentation**: https://intellistream.github.io/SAGE-Pub/guides/packages/sage-benchmark/
- **Issues**: https://github.com/intellistream/SAGE/issues
- **Discussions**: https://github.com/intellistream/SAGE/discussions

______________________________________________________________________

**Part of the SAGE Framework** | [Main Repository](https://github.com/intellistream/SAGE)
