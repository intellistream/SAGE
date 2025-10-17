# Example Configuration Files

This directory contains YAML configuration files used by various SAGE examples.

## 📋 Configuration Files

### General Pipeline Configurations

#### `config.yaml`
General-purpose pipeline configuration.

**Used by:**
- Various RAG examples
- Basic pipeline examples

#### `config_source.yaml` & `config_source_local.yaml`
Data source configurations for pipelines.

**Used by:**
- `rag/loaders/document_loaders.py`
- Multiple RAG examples

---

### RAG Configurations

#### `config_qa_chroma.yaml`
QA pipeline with ChromaDB vector store.

**Used by:**
- `rag/qa_dense_retrieval_chroma.py`
- `rag/build_chroma_index.py`

#### `config_dense_milvus.yaml`
Dense retrieval with Milvus vector database.

**Used by:**
- `rag/qa_dense_retrieval_milvus.py`
- `rag/build_milvus_dense_index.py`

#### `config_sparse_milvus.yaml`
Sparse retrieval with Milvus (BM25/SPLADE).

**Used by:**
- `rag/qa_sparse_retrieval_milvus.py`
- `rag/build_milvus_sparse_index.py`

#### `config_bm25s.yaml`
BM25 sparse retrieval configuration.

**Used by:**
- `rag/qa_bm25_retrieval.py`

#### `config_mixed.yaml`
Hybrid dense + sparse retrieval.

**Used by:**
- `rag/qa_dense_retrieval_mixed.py`

#### `config_multiplex.yaml`
Multi-path retrieval pipeline.

**Used by:**
- `rag/qa_multiplex.py`

#### `config_rerank.yaml`
Retrieval with reranking.

**Used by:**
- `rag/qa_rerank.py`

#### `config_refiner.yaml`
Query refinement configuration.

**Used by:**
- `rag/qa_refiner.py`

#### `config_ray.yaml`
Ray-distributed RAG pipeline.

**Used by:**
- `rag/qa_dense_retrieval_ray.py`

#### `config_hf.yaml`
Hugging Face model configuration.

**Used by:**
- `rag/qa_hf_model.py`

---

### Agent Configurations

#### `config_agent_min.yaml`
Minimal agent configuration example.

**Used by:**
- `tutorials/agents/basic_agent.py`
- Agent examples

---

### Memory Configurations

#### `config_rag_memory_pipeline.yaml`
RAG pipeline with memory integration.

**Used by:**
- `tutorials/memory/rag_memory_pipeline.py`
- Memory service examples

---

## 🔧 Configuration Structure

Most configuration files follow this general structure:

```yaml
# Data Source
source:
  type: "directory" | "file" | "huggingface"
  path: "path/to/data"
  
# Embedding
embedding:
  model_name: "BAAI/bge-small-en-v1.5"
  dimension: 384
  
# Vector Store
vector_store:
  type: "chroma" | "milvus" | "faiss"
  collection_name: "my_collection"
  
# LLM
llm:
  provider: "openai" | "huggingface" | "vllm"
  model_name: "gpt-3.5-turbo"
  api_key: "${OPENAI_API_KEY}"  # From environment
  
# Retrieval
retrieval:
  top_k: 3
  similarity_threshold: 0.7
```

## 🔐 API Keys

**Never commit API keys!** Use environment variables:

```yaml
# Good ✅
api_key: "${OPENAI_API_KEY}"

# Bad ❌
api_key: "sk-abc123..."
```

Set keys in `.env` file:
```bash
cp .env.example .env
# Edit .env with your keys
```

## 📝 Creating Custom Configurations

1. **Copy an existing config**:
   ```bash
   cp examples/config/config_qa_chroma.yaml my_config.yaml
   ```

2. **Modify for your needs**:
   - Change model names
   - Adjust parameters
   - Update paths

3. **Use in your code**:
   ```python
   from sage.common.utils.config.loader import load_config
   config = load_config("my_config.yaml")
   ```

## 🗂️ Configuration Templates

### Minimal RAG Config
```yaml
source:
  type: "directory"
  path: "data/documents"

embedding:
  model_name: "BAAI/bge-small-en-v1.5"
  
vector_store:
  type: "chroma"
  collection_name: "my_docs"
  
llm:
  provider: "openai"
  model_name: "gpt-3.5-turbo"
  api_key: "${OPENAI_API_KEY}"
```

### Agent Config Template
```yaml
agent:
  name: "MyAgent"
  role: "assistant"
  
llm:
  provider: "openai"
  model_name: "gpt-4"
  temperature: 0.7
  
tools:
  - name: "web_search"
    enabled: true
```

## 📚 Related Documentation

- **Configuration Loader**: `packages/sage-common/src/sage/common/utils/config/`
- **RAG Configuration**: `docs/dev-notes/EMBEDDING_README.md`
- **Environment Setup**: `.env.example`

## ⚠️ Notes

- Configurations use YAML format
- Environment variables are interpolated: `${VAR_NAME}`
- Paths can be relative (to project root) or absolute
- Most examples work with default configurations
- Customize as needed for your use case
