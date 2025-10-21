# RAG Examples - Configuration Files

This directory contains YAML configuration files for RAG (Retrieval-Augmented Generation) examples.

## Configuration Files

### Dense Retrieval
- **`config_dense_milvus.yaml`** - Dense retrieval with Milvus vector database
- **`config_qa_chroma.yaml`** - QA pipeline with ChromaDB

### Sparse Retrieval
- **`config_sparse_milvus.yaml`** - Sparse retrieval with Milvus (BM25/SPLADE)
- **`config_bm25s.yaml`** - BM25 sparse retrieval

### Hybrid & Advanced
- **`config_mixed.yaml`** - Hybrid dense + sparse retrieval
- **`config_multiplex.yaml`** - Multi-path retrieval pipeline
- **`config_rerank.yaml`** - Retrieval with reranking
- **`config_refiner.yaml`** - Query refinement

### Special Configurations
- **`config_ray.yaml`** - Ray-distributed RAG pipeline
- **`config_hf.yaml`** - Hugging Face model configuration
- **`config_source.yaml`** - Data source configuration
- **`config_source_local.yaml`** - Local data source configuration

## Usage

Reference these configs when running RAG examples:

```bash
# From project root
python packages/sage-benchmark/src/sage/benchmark/benchmark_rag/implementations/qa_dense_retrieval_milvus.py

# The script will automatically load config from:
# packages/sage-benchmark/src/sage/benchmark/benchmark_rag/config/config_dense_milvus.yaml
```

## Customization

Copy and modify any config file for your needs:

```bash
cp config_dense_milvus.yaml my_custom_config.yaml
# Edit my_custom_config.yaml
```

## Data Paths

All data paths in these configs use relative paths from the project root:
- Data files: `packages/sage-benchmark/src/sage/benchmark/benchmark_rag/data/`
- Persistence: `data/` (for vector databases and other runtime data)
