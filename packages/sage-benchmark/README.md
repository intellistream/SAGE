# SAGE Benchmark

**Benchmarking and RAG Examples for SAGE Framework**

This package provides comprehensive benchmarking tools, RAG (Re## 📚 Documentation

For detailed documentation on each component:

- See `src/sage/benchmark/benchmark_rag/implementations/README.md` for RAG implementation details
- See `src/sage/benchmark/benchmark_rag/evaluation/README.md` for benchmark experiment documentation
- See `src/sage/benchmark/benchmark_rag/config/README.md` for configuration guidel-Augmented Generation) examples, and experimental pipelines for the SAGE framework.

## 📦 Package Structure

```
sage-benchmark/
├── src/
│   └── sage/
│       └── benchmark/
│           ├── __init__.py
│           └── benchmark_rag/           # RAG benchmarking
│               ├── __init__.py
│               ├── implementations/     # Various RAG implementations
│               │   ├── qa_dense_retrieval_milvus.py
│               │   ├── qa_sparse_retrieval_milvus.py
│               │   ├── qa_hybrid_retrieval_milvus.py
│               │   ├── qa_multimodal_fusion.py
│               │   ├── build_chroma_index.py
│               │   └── loaders/
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

Install the benchmark package:

```bash
pip install -e packages/sage-benchmark
```

Or with development dependencies:

```bash
pip install -e "packages/sage-benchmark[dev]"
```

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

1. **Run a RAG implementation**:
```bash
python -m sage.benchmark.benchmark_rag.implementations.qa_dense_retrieval_milvus
```

2. **Build vector index**:
```bash
python -m sage.benchmark.benchmark_rag.implementations.build_chroma_index
```

3. **Run benchmark experiments**:
```bash
python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment
```

4. **Evaluate results**:
```bash
python -m sage.benchmark.benchmark_rag.evaluation.evaluate_results
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

This package follows the same contribution guidelines as the main SAGE project. See the main repository's `CONTRIBUTING.md`.

## 📄 License

MIT License - see the main SAGE repository for details.
