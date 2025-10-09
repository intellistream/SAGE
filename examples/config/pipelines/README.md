# Pipeline Examples with EmbeddingService

This directory contains production-ready pipeline configurations demonstrating the integration of EmbeddingService.

## Quick Start

```bash
# Analyze which embedding method works best for your use case
sage pipeline analyze-embedding "your test query" -m hash -m openai -m hf

# Create a pipeline from template
sage pipeline create-embedding -t rag -e hf -m BAAI/bge-small-zh-v1.5

# Or use pre-built examples
sage pipeline run examples/config/pipelines/rag-embedding-service.yaml
```

## Available Examples

### 1. RAG with EmbeddingService (`rag-embedding-service.yaml`)

**Purpose**: Complete Retrieval-Augmented Generation pipeline

**Features**:
- HuggingFace BAAI/bge-small-zh-v1.5 embeddings
- Document loading → Chunking → Embedding → Indexing
- VLLMService for generation
- Caching and normalization enabled

**Usage**:
```bash
# Run the pipeline
sage pipeline run examples/config/pipelines/rag-embedding-service.yaml

# Customize for your data
cp examples/config/pipelines/rag-embedding-service.yaml my-rag.yaml
# Edit source.params.directory to point to your documents
sage pipeline run my-rag.yaml
```

**Performance**:
- Throughput: ~2,000 docs/min (32 batch size)
- Latency: ~30ms per batch
- Memory: ~4GB GPU

### 2. Knowledge Base Builder with vLLM (`knowledge-base-vllm.yaml`)

**Purpose**: High-throughput document indexing for large knowledge bases

**Features**:
- vLLM embedding backend (512 batch size)
- Optimized for 100k+ documents
- Parallel document loading (8 workers)
- IVF_FLAT index for fast search
- Cache disabled to save memory

**Usage**:
```bash
# Index large knowledge base
sage pipeline run examples/config/pipelines/knowledge-base-vllm.yaml

# Monitor progress
sage pipeline run examples/config/pipelines/knowledge-base-vllm.yaml --monitor
```

**Performance**:
- Throughput: ~10,000 docs/min (2x GPU)
- Batch size: 512 (vLLM optimized)
- Memory: ~16GB GPU
- Recommended for: Offline batch indexing

### 3. Hybrid Search (`hybrid-search.yaml`)

**Purpose**: Combine dense semantic and sparse keyword search

**Features**:
- Dense: OpenAI text-embedding-3-small (semantic)
- Sparse: BM25s (keyword matching)
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking
- Dual vector databases

**Usage**:
```bash
# Set OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run hybrid indexing
sage pipeline run examples/config/pipelines/hybrid-search.yaml

# Adjust fusion weights in the config
# dense_weight: 0.7, sparse_weight: 0.3
```

**Performance**:
- Dense latency: ~50ms per batch
- Sparse latency: ~5ms per batch
- Recall improvement: ~15-30% vs single method
- Best for: Legal docs, technical docs, code search

### 4. Multi-Strategy Embedding (`multi-strategy-embedding.yaml`)

**Purpose**: Intelligent routing to different embedding strategies

**Features**:
- Fast route: hash embedding (< 1ms for queries)
- Quality route: OpenAI (high-quality for docs)
- Batch route: vLLM (high-throughput for batches)
- Automatic routing based on input type
- Unified vector database

**Usage**:
```bash
# Run multi-strategy pipeline
sage pipeline run examples/config/pipelines/multi-strategy-embedding.yaml

# Input with type metadata
echo '{"text": "query", "type": "query"}' | sage pipeline run ...

# View routing statistics on dashboard
# Navigate to http://localhost:8080
```

**Performance**:
- Query route: < 1ms, 100k+ req/s
- Document route: ~50ms, 100 req/s
- Batch route: ~10ms/doc, 10k docs/min
- Best for: Production systems with mixed workloads

## Comparison Table

| Pipeline | Embedding Method | Use Case | Throughput | Latency | Quality | Cost |
|----------|-----------------|----------|------------|---------|---------|------|
| RAG | HuggingFace | General RAG | 2k docs/min | 30ms | ⭐⭐⭐⭐ | Free |
| Knowledge Base | vLLM | Batch indexing | 10k docs/min | 10ms | ⭐⭐⭐⭐ | Free |
| Hybrid Search | OpenAI + BM25s | Precision search | 1k docs/min | 50ms | ⭐⭐⭐⭐⭐ | $$ |
| Multi-Strategy | Hash/OpenAI/vLLM | Mixed workload | Variable | Variable | ⭐⭐⭐⭐ | $ |

## Customization Guide

### Change Embedding Method

Edit the `services` section:

```yaml
services:
  - name: embedding-service
    class: sage.middleware.components.sage_embedding.service.EmbeddingService
    params:
      method: openai  # Change to: hf, jina, zhipu, cohere, etc.
      model_name: text-embedding-3-small
```

### Adjust Batch Size

Edit the stage parameters:

```yaml
stages:
  - id: embed-chunks
    kind: service
    class: embedding-service
    params:
      batch_size: 64  # Increase for higher throughput
```

Recommended batch sizes:
- Real-time queries: 16-32
- Balanced: 64-128
- Batch indexing: 256-512 (vLLM)

### Enable/Disable Cache

Edit service parameters:

```yaml
services:
  - name: embedding-service
    params:
      cache_embeddings: true  # Enable for queries, disable for indexing
```

### Vector Normalization

```yaml
services:
  - name: embedding-service
    params:
      normalize: true  # Enable for cosine similarity
```

## Environment Variables

Set these before running pipelines:

```bash
# For OpenAI embedding
export OPENAI_API_KEY="sk-..."

# For Jina AI
export JINA_API_KEY="jina_..."

# For Zhipu AI
export ZHIPU_API_KEY="zhipu_..."

# For Cohere
export COHERE_API_KEY="co_..."

# Optional: Override default models
export SAGE_EMBEDDING_MODEL="BAAI/bge-large-zh-v1.5"
export SAGE_LLM_MODEL="Qwen/Qwen2.5-14B-Instruct"
```

## Monitoring and Debugging

### View Metrics

Most pipelines include monitoring:

```yaml
monitors:
  - type: metrics
    params:
      track_latency: true
      track_throughput: true
```

### Enable Debug Logging

```yaml
environment:
  config:
    log_level: DEBUG  # Change to DEBUG for detailed logs
```

### Check Embedding Statistics

Use the EmbeddingService info endpoint:

```python
from sage.components.sage_embedding.service import EmbeddingService

service = EmbeddingService(method="hf", model_name="BAAI/bge-small-zh-v1.5")
info = service.get_info()
print(info)  # {'method': 'hf', 'model': '...', 'dimension': 512, ...}
```

## Troubleshooting

### Issue: Out of Memory

**Solution**: Reduce batch size or disable cache

```yaml
params:
  batch_size: 16  # Reduce from 64
  cache_embeddings: false  # Disable cache
```

### Issue: Slow Embedding

**Solution**: Use vLLM or increase batch size

```yaml
params:
  method: vllm
  batch_size: 256
```

### Issue: Low Quality Results

**Solution**: Switch to higher-quality embedding

```yaml
params:
  method: openai
  model_name: text-embedding-3-large
```

### Issue: API Rate Limits

**Solution**: Use local models (HuggingFace or vLLM)

```yaml
params:
  method: hf  # or vllm
  model_name: BAAI/bge-large-zh-v1.5
```

## Best Practices

1. **Development**: Start with `hash` for quick prototyping
2. **Production Queries**: Use `hash` (fast) or `hf` (balanced)
3. **Production Indexing**: Use `vllm` (high throughput)
4. **High Quality**: Use `openai` text-embedding-3-large
5. **Multi-language**: Use `jina` or multilingual HF models
6. **Cost-sensitive**: Use `hf` or `vllm` (free, local)
7. **Hybrid Approach**: Combine methods for best results

## Next Steps

1. Analyze embedding methods for your data:
   ```bash
   sage pipeline analyze-embedding "your test query"
   ```

2. Create a custom pipeline:
   ```bash
   sage pipeline create-embedding -t rag -e <method> -o my-pipeline.yaml
   ```

3. Customize the generated config

4. Run and monitor:
   ```bash
   sage pipeline run my-pipeline.yaml
   ```

5. Optimize based on metrics

## Resources

- [Pipeline Builder Embedding Guide](../../docs/dev-notes/PIPELINE_EMBEDDING_GUIDE.md)
- [EmbeddingService Documentation](../../packages/sage-middleware/src/sage/middleware/components/sage_embedding/README.md)
- [SAGE Documentation](../../README.md)

## Contributing

To add new pipeline examples:

1. Create pipeline using templates
2. Test thoroughly
3. Add documentation
4. Submit PR

For questions and support, see [CONTRIBUTING.md](../../CONTRIBUTING.md).
