# RAG Tools and Utilities

Supporting tools for building and preparing RAG systems.

## 📁 Structure

```
tools/
├── Index Building
│   ├── build_chroma_index.py          # Build ChromaDB index
│   ├── build_milvus_index.py          # Build basic Milvus index
│   ├── build_milvus_dense_index.py    # Build Milvus dense index
│   └── build_milvus_sparse_index.py   # Build Milvus sparse index
│
└── Document Loaders
    └── loaders/
        └── document_loaders.py         # Load various document formats
```

## 🚀 Usage

### Building Vector Indices

**ChromaDB:**
```bash
python -m sage.benchmark.benchmark_rag.implementations.tools.build_chroma_index
```

**Milvus Dense:**
```bash
python -m sage.benchmark.benchmark_rag.implementations.tools.build_milvus_dense_index
```

**Milvus Sparse:**
```bash
python -m sage.benchmark.benchmark_rag.implementations.tools.build_milvus_sparse_index
```

### Using Document Loaders

```python
from sage.benchmark.benchmark_rag.implementations.tools.loaders.document_loaders import load_documents

# Load documents from various formats
docs = load_documents("path/to/documents")
```

## 📊 Workflow

Typical workflow for RAG benchmarking:

1. **Prepare Data**: Use document loaders to load your corpus
2. **Build Index**: Use build_*_index.py scripts to create vector indices
3. **Run Pipelines**: Execute RAG pipelines from `../pipelines/`
4. **Evaluate**: Use evaluation framework in `../../evaluation/`

## ⚙️ Configuration

Index building scripts use configurations from `../../config/`:
- Data paths
- Embedding models
- Index parameters
- Collection names

## 📖 Notes

- Run index building scripts before running RAG pipelines
- Indices are typically stored in local directories or remote vector databases
- Make sure vector database services (Milvus, ChromaDB) are running if needed
