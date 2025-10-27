# SAGE Tutorials

Welcome to SAGE tutorials! These are simple, focused examples to help you learn SAGE quickly.

## 🎯 Quick Start

New to SAGE? Start here:

1. **[Hello World](hello_world.py)** - Your first SAGE program (30 seconds)
1. **[Embedding Demo](embedding_demo.py)** - Text embeddings basics (2 minutes)
1. **[Basic Agent](agents/basic_agent.py)** - Create your first agent (5 minutes)

## 📚 Tutorial Categories

### Core API

Basic SAGE pipeline operations and data flow.

- **[core-api/](core-api/)** - Core pipeline operations
- **[transformation-api/](transformation-api/)** - Data transformation operators
- **[stream_mode/](stream_mode/)** - Streaming data processing
- **[io/](io/)** - Input/output utilities (renamed from io_utils)
- **[service-api/](service-api/)** - Service integration patterns

### Agents

Build intelligent agents that can use tools and reason.

- **[agents/](agents/)** - Agent creation and workflow patterns
  - `basic_agent.py` - Simple agent example
  - `workflow_demo.py` - Agent workflows
  - `arxiv_search_tool.py` - Custom tool example

### RAG (Retrieval-Augmented Generation)

Learn to build question-answering systems with retrieval.

- **[rag/](rag/)** - Basic RAG tutorials
  - `simple_rag.py` - Simple RAG pipeline
  - `qa_no_retrieval.py` - Direct QA
  - `qa_local_llm.py` - Use local models

### Memory Systems

Add persistence and memory to your AI applications.

- **[memory/](memory/)** - Memory management tutorials
  - `rag_memory_manager.py` - Basic memory
  - `rag_memory_service.py` - Memory as a service
  - `rag_memory_pipeline.py` - Full pipeline with memory

### Multimodal AI

Work with text, images, and video together.

- **[multimodal/](multimodal/)** - Multimodal AI tutorials
  - `quickstart.py` - Text+Image basics
  - `cross_modal_search.py` - Cross-modal search

### Scheduling & Parallelism

Distribute and parallelize your workloads.

- **[scheduler/](scheduler/)** - Task scheduling examples
  - `remote_env.py` - Remote execution
  - `scheduler_comparison.py` - Compare strategies

### Vector Databases

High-performance vector storage and search.

- **[sage_db/](sage_db/)** - SAGE DB tutorials
  - `workflow_demo.py` - Workflow patterns

### Service Integration

Build and deploy AI services.

- **[service/](service/)** - Service patterns ⭐ NEW
  - `embedding_service_demo.py` - Embedding service
  - `pipeline_as_service/` - Pipeline services
  - `sage_db/` - SAGE DB service
  - `sage_flow/` - SAGE Flow service

### Utilities

- **[fault_tolerance.py](fault_tolerance.py)** - Error handling and recovery

## 🎓 Learning Path

### Beginner (< 1 hour)

1. `hello_world.py` - Understand basic pipeline
1. `embedding_demo.py` - Learn embeddings
1. `core-api/` examples - Master core operations

### Intermediate (1-3 hours)

1. `agents/basic_agent.py` - Build an agent
1. `rag/simple_rag.py` - Create a RAG system
1. `multimodal/quickstart.py` - Multimodal basics
1. `service/embedding_service_demo.py` - Build a service

### Advanced (3+ hours)

1. `memory/` - Add memory to your systems
1. `scheduler/` - Parallelize your workloads
1. `service/` - Build production services

## 🚀 Beyond Tutorials

Once you've mastered the tutorials:

### Advanced Examples

- **RAG & Benchmarks**: See `packages/sage-benchmark/` for production-ready RAG pipelines
- **Memory Systems**: See `examples/tutorials/memory/` for advanced memory patterns

### Real Applications

Check out `examples/apps/` for complete applications:

- Video Intelligence
- Medical Diagnosis

### Build Your Own

Explore the full libraries in `packages/`:

- `sage-libs` - Core functionality
- `sage-apps` - Application templates
- `sage-middleware` - Infrastructure components

## 💡 Tips

- **Run from project root**: `python examples/tutorials/hello_world.py`
- **Check requirements**: Some examples need API keys (see `.env.example`)
- **Start simple**: Don't skip the basics!
- **Read the code**: Examples are well-commented

## 📖 Documentation

- **Main docs**: See `docs/` directory
- **API reference**: Check docstrings in `packages/sage-libs/`
- **Community**: See `docs/COMMUNITY.md`

Happy learning! 🎉
