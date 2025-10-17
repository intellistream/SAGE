# Memory System Tutorials

Examples demonstrating SAGE's memory and persistence capabilities.

## Examples

### 1. RAG Memory Manager (`rag_memory_manager.py`)
Basic memory management for RAG systems.

```bash
python examples/tutorials/memory/rag_memory_manager.py
```

### 2. RAG Memory Service (`rag_memory_service.py`)
Memory as a service pattern.

```bash
python examples/tutorials/memory/rag_memory_service.py
```

### 3. RAG Memory Pipeline (`rag_memory_pipeline.py`)
Complete RAG pipeline with memory integration.

```bash
python examples/tutorials/memory/rag_memory_pipeline.py
```

**Requirements**: 
- Configuration file (see `examples/config/config_rag_memory_pipeline.yaml`)
- API keys (set in `.env`)

## More Information

See the detailed memory service documentation in this directory:
- `README_memory_service.md`
- `README_memory_service_demo.md`

## Next Steps

- **NeuroMem**: Advanced memory system in `packages/sage-middleware/`
- **Memory middleware**: `packages/sage-middleware/src/sage/middleware/components/neuromem/`
