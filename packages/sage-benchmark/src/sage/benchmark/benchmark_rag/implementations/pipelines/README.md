# RAG Pipeline Implementations

This directory contains various RAG pipeline implementations for benchmarking different retrieval strategies.

## 📁 Structure

```
pipelines/
├── Dense Retrieval
│   ├── qa_dense_retrieval.py           # Basic dense retrieval
│   ├── qa_dense_retrieval_milvus.py    # Milvus dense retrieval
│   ├── qa_dense_retrieval_chroma.py    # ChromaDB dense retrieval
│   └── qa_dense_retrieval_ray.py       # Distributed dense retrieval with Ray
│
├── Sparse Retrieval
│   ├── qa_bm25_retrieval.py            # BM25 sparse retrieval
│   └── qa_sparse_retrieval_milvus.py   # Milvus sparse retrieval
│
├── Hybrid & Advanced
│   ├── qa_dense_retrieval_mixed.py     # Mixed retrieval strategies
│   ├── qa_rerank.py                    # Retrieval with reranking
│   ├── qa_refiner.py                   # Query refinement
│   └── qa_multiplex.py                 # Multiplex retrieval
│
└── Multimodal
    ├── qa_multimodal_fusion.py         # Multimodal RAG (text+image+video)
    └── qa_hf_model.py                  # Hugging Face model integration
```

## 🚀 Quick Start

### Dense Retrieval

```bash
# Basic dense retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval

# Milvus dense retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval_milvus

# ChromaDB dense retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval_chroma

# Distributed with Ray
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval_ray
```

### Sparse Retrieval

```bash
# BM25 retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_bm25_retrieval

# Milvus sparse retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_sparse_retrieval_milvus
```

### Advanced Methods

```bash
# Reranking
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_rerank

# Query refinement
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_refiner

# Multimodal fusion
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_multimodal_fusion
```

## 📊 Performance Comparison

Use these implementations to compare:
- **Accuracy**: How well each method retrieves relevant documents
- **Latency**: Response time for different approaches
- **Scalability**: Performance with increasing data size
- **Resource Usage**: Memory and compute requirements

## 🔧 Configuration

Each pipeline uses configuration files from `../../config/`:
- `config_dense_milvus.yaml` - Milvus dense settings
- `config_sparse_milvus.yaml` - Milvus sparse settings
- `config_qa_chroma.yaml` - ChromaDB settings
- etc.

See `../../config/README.md` for configuration details.

## 📖 Documentation

For implementation details, see the docstrings in each pipeline file.
For benchmark results, run the evaluation framework in `../../evaluation/`.
