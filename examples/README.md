# SAGE Examples Collection

Complete examples and tutorials demonstrating SAGE's capabilities.

## 🚀 Quick Start

**New to SAGE?** Start with tutorials:

```bash
# Your first SAGE program (30 seconds)
python examples/tutorials/hello_world.py

# Learn embeddings (2 minutes)
python examples/tutorials/embedding_demo.py

# Build an agent (5 minutes)
python examples/tutorials/agents/basic_agent.py
```

## 📁 Directory Structure

```
examples/
├── tutorials/          # 📚 Learning tutorials (START HERE!)
│   ├── hello_world.py
│   ├── agents/        # Agent tutorials
│   │   ├── config/   # Agent configurations
│   │   └── data/     # Agent test data
│   ├── multimodal/    # Text+Image+Video
│   ├── memory/        # Memory systems
│   │   ├── config/   # Memory configurations
│   │   └── data/     # Memory test data
│   ├── service/       # Service integration
│   ├── scheduler/     # Task scheduling
│   ├── sage_db/       # Vector database
│   ├── config/        # General configurations
│   ├── data/          # General data utilities
│   └── ...
│
├── apps/              # 🎯 Production applications
│   ├── run_video_intelligence.py
│   └── run_medical_diagnosis.py
│
└── memory/            # � Advanced memory examples (DEPRECATED - use tutorials/memory)
```

**Note**: RAG examples and experiments have been moved to `packages/sage-benchmark/`. See `packages/sage-benchmark/README.md` for details.

## 📚 Examples by Level

### 🟢 Beginner (< 30 minutes)
Simple, focused tutorials to learn SAGE basics.

**Location**: `examples/tutorials/`

- **Hello World**: Your first pipeline
- **Embeddings**: Text embeddings basics
- **Basic Agent**: Create an AI agent
- **Simple RAG**: Question answering
- **Service Basics**: Embedding service, pipeline service

**Run**: See `examples/tutorials/README.md`

### 🟡 Intermediate (30 min - 2 hours)
Production-ready patterns and integrations.

**Location**: `packages/sage-benchmark/`, `examples/memory/`

- **Advanced RAG**: Dense/sparse retrieval, reranking, multimodal fusion (see `sage-benchmark`)
- **Benchmarking**: Pipeline experiments and evaluation (see `sage-benchmark`)
- **Memory Systems**: RAG with memory, persistence patterns
- **Vector Databases**: Milvus, ChromaDB, FAISS integration (see `sage-benchmark`)
- **Distributed RAG**: Ray-based parallel processing (see `sage-benchmark`)

**See**: `packages/sage-benchmark/README.md` for RAG and benchmark examples

### 🔴 Advanced (2+ hours)
Complete applications and complex workflows.

**Location**: `examples/apps/`

- **Video Intelligence**: Multi-model video analysis
- **Medical Diagnosis**: AI medical imaging
- **Multi-agent Systems**: Coordinated AI agents

## 📦 Installation

### Minimal (Tutorials only)
```bash
pip install -e packages/sage-libs
```

### Full (All examples)
```bash
# All applications
pip install -e packages/sage-apps[all]

# RAG and benchmarking
pip install -e packages/sage-benchmark

# Or specific apps
pip install -e packages/sage-apps[video]
pip install -e packages/sage-apps[medical]

# All examples dependencies
pip install -r examples/requirements.txt
```

## ⚠️ Examples vs Tests

**This directory contains examples and demos, NOT tests.**

- **Examples** (`examples/`): How to use SAGE features
- **Unit Tests** (`packages/*/tests/`): Verify code correctness  
- **Integration Tests** (`tools/tests/`): Test example execution

## 🎯 Learning Paths

### Path 1: RAG Developer
1. `packages/sage-benchmark/sage_benchmark/rag/rag_simple.py` - Learn basics
2. `packages/sage-benchmark/sage_benchmark/rag/qa_dense_retrieval_milvus.py` - Add vector search
3. `packages/sage-benchmark/sage_benchmark/rag/qa_rerank.py` - Improve results
4. `packages/sage-benchmark/sage_benchmark/rag/qa_multimodal_fusion.py` - Add multimodal
5. `tutorials/memory/rag_memory_pipeline.py` - Add memory

See `packages/sage-benchmark/README.md` for complete RAG documentation.

### Path 2: Agent Builder
1. `tutorials/agents/basic_agent.py` - Agent basics
2. `tutorials/agents/workflow_demo.py` - Workflows
3. `tutorials/agents/arxiv_search_tool.py` - Custom tools
4. `apps/run_medical_diagnosis.py` - Multi-agent app

### Path 3: Service Developer
1. `tutorials/service/embedding_service_demo.py` - Service basics
2. `tutorials/service/pipeline_as_service/` - Pipeline services
3. `tutorials/service/sage_db/` - Vector database service
4. `tutorials/service/sage_flow/` - Stream processing service

## 💡 Tips

**Running examples:**
```bash
# Always run from project root
cd /path/to/SAGE
python examples/tutorials/hello_world.py
```

**API Keys:**
```bash
# Copy and configure
cp .env.example .env
# Edit .env with your keys
```

**Configurations:**
```bash
# Tutorials have their own config directories
ls examples/tutorials/agents/config/*.yaml
ls examples/tutorials/memory/config/*.yaml

# RAG configs are in sage-benchmark
ls packages/sage-benchmark/sage_benchmark/rag/config/*.yaml

# See respective README files for details
cat packages/sage-benchmark/sage_benchmark/rag/config/README.md
```

**Troubleshooting:**
- Missing dependencies? Check `requirements.txt` in each category
- Import errors? Make sure you installed SAGE: `pip install -e packages/sage-libs`
- Need data? Check the `data/` subdirectory in each example category
- Need config? Check the `config/` subdirectory in each example category
- Need help? See `docs/COMMUNITY.md`

## 📖 Documentation

- **Tutorials README**: `examples/tutorials/README.md`
- **Apps README**: `examples/apps/README.md`
- **RAG & Benchmarks**: `packages/sage-benchmark/README.md`
- **Main Docs**: `docs/` and `docs-public/`
- **API Docs**: Docstrings in `packages/sage-libs/`

## 🔍 Quick Reference

### By Feature

- **Agents**: `tutorials/agents/`
- **RAG**: `packages/sage-benchmark/sage_benchmark/rag/`
- **Multimodal**: `tutorials/multimodal/`, `sage-benchmark/sage_benchmark/rag/qa_multimodal_fusion.py`
- **Memory**: `tutorials/memory/`
- **Services**: `tutorials/service/`
- **Streaming**: `tutorials/stream_mode/`
- **Distributed**: `sage-benchmark/sage_benchmark/rag/qa_dense_retrieval_ray.py`
- **Benchmarking**: `packages/sage-benchmark/sage_benchmark/experiments/`

### By Technology

- **ChromaDB**: `sage-benchmark/sage_benchmark/rag/config/config_qa_chroma.yaml`
- **Milvus**: `sage-benchmark/sage_benchmark/rag/config/config_*_milvus.yaml`
- **Ray**: `sage-benchmark/sage_benchmark/rag/config/config_ray.yaml`
- **OpenAI**: Most RAG examples in sage-benchmark
- **Hugging Face**: `sage-benchmark/sage_benchmark/rag/qa_hf_model.py`
- **Local LLMs**: Various examples in sage-benchmark

### By Use Case

- **Question Answering**: `sage-benchmark/sage_benchmark/rag/qa_*.py`
- **Document Search**: `sage-benchmark/sage_benchmark/rag/build_*_index.py`
- **Image Search**: `tutorials/multimodal/`
- **Video Analysis**: `apps/run_video_intelligence.py`
- **Medical AI**: `apps/run_medical_diagnosis.py`
- **Web Services**: `tutorials/service/pipeline_as_service/`
- **Experiments**: `sage-benchmark/sage_benchmark/experiments/`
