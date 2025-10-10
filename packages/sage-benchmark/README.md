# SAGE Benchmark

**Benchmarking and RAG Examples for SAGE Framework**

This package provides comprehensive benchmarking tools, RAG (Retrieval-Augmented Generation) examples, and experimental pipelines for the SAGE framework.

## 📦 Package Structure

```
sage-benchmark/
├── sage_benchmark/
│   ├── rag/                    # RAG examples and benchmarks
│   │   ├── config/             # RAG configuration files
│   │   ├── data/               # RAG test data
│   │   ├── qa_dense_retrieval_milvus.py
│   │   ├── qa_sparse_retrieval_milvus.py
│   │   ├── qa_hybrid_retrieval_milvus.py
│   │   ├── build_chroma_index.py
│   │   └── ...
│   └── experiments/            # Experimental pipelines
│       ├── config/             # Experiment configurations
│       ├── pipeline_experiment.py
│       ├── evaluate_results.py
│       └── README.md
├── pyproject.toml
└── README.md
```

## 🚀 Installation

Install the benchmark package:

```bash
pip install -e packages/sage-benchmark
```

Or with development dependencies:

```bash
pip install -e "packages/sage-benchmark[dev]"
```

## 📊 RAG Examples

The RAG module provides various retrieval-augmented generation examples:

### Vector Databases Supported
- **Milvus**: Dense, sparse, and hybrid retrieval
- **ChromaDB**: Local vector database with simple setup
- **FAISS**: Efficient similarity search

### Quick Start

1. **Dense Retrieval with Milvus**:
```bash
python -m sage_benchmark.rag.qa_dense_retrieval_milvus
```

2. **Build ChromaDB Index**:
```bash
python -m sage_benchmark.rag.build_chroma_index
```

3. **Hybrid Retrieval** (combining dense + sparse):
```bash
python -m sage_benchmark.rag.qa_hybrid_retrieval_milvus
```

### Configuration

All RAG examples use YAML configuration files located in `sage_benchmark/rag/config/`:

- `config_dense_milvus.yaml` - Dense retrieval configuration
- `config_sparse_milvus.yaml` - Sparse retrieval configuration
- `config_hybrid_milvus.yaml` - Hybrid retrieval configuration
- `config_qa_chroma.yaml` - ChromaDB configuration

## 🧪 Experiments

The experiments module provides tools for running and evaluating experimental pipelines:

```bash
# Run pipeline experiments
python -m sage_benchmark.experiments.pipeline_experiment

# Evaluate results
python -m sage_benchmark.experiments.evaluate_results
```

## 📖 Data

Test data is included in the package:

- **RAG Data** (`rag/data/`):
  - `queries.jsonl` - Sample queries for testing
  - `qa_knowledge_base.*` - Knowledge base in multiple formats
  - `sample/` - Additional sample documents

- **Experiment Config** (`experiments/config/`):
  - `experiment_config.yaml` - Experiment configurations

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

- See `sage_benchmark/rag/README.md` for RAG examples
- See `sage_benchmark/experiments/README.md` for experiment details

## 🤝 Contributing

This package follows the same contribution guidelines as the main SAGE project. See the main repository's `CONTRIBUTING.md`.

## 📄 License

MIT License - see the main SAGE repository for details.
