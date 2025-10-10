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
│   ├── rag/           # RAG basics
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
├── rag/               # 🔍 Advanced RAG examples
│   ├── config/        # RAG configurations
│   ├── data/          # RAG test data
│   ├── qa_dense_retrieval*.py
│   ├── qa_multimodal_fusion.py
│   ├── build_*_index.py
│   └── loaders/
│
└── memory/            # 💾 Advanced memory examples (DEPRECATED - use tutorials/memory)
```

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

**Location**: `examples/rag/`, `examples/memory/`

- **Advanced RAG**: Dense/sparse retrieval, reranking, multimodal fusion
- **Memory Systems**: RAG with memory, persistence patterns
- **Vector Databases**: Milvus, ChromaDB, FAISS integration
- **Distributed RAG**: Ray-based parallel processing

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
1. `tutorials/rag/simple_rag.py` - Learn basics
2. `rag/qa_dense_retrieval.py` - Add vector search
3. `rag/qa_rerank.py` - Improve results
4. `rag/qa_multimodal_fusion.py` - Add multimodal
5. `memory/rag_memory_pipeline.py` - Add memory

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
# Each example category has its own config directory
ls examples/rag/config/*.yaml
ls examples/tutorials/agents/config/*.yaml
ls examples/tutorials/memory/config/*.yaml

# See respective README files for details
cat examples/rag/config/README.md
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
- **RAG Config**: `examples/rag/config/README.md`
- **Main Docs**: `docs/` and `docs-public/`
- **API Docs**: Docstrings in `packages/sage-libs/`

## 🔍 Quick Reference

### By Feature

- **Agents**: `tutorials/agents/`, agent examples
- **RAG**: `tutorials/rag/`, `rag/`
- **Multimodal**: `tutorials/multimodal/`, `rag/qa_multimodal_fusion.py`
- **Memory**: `tutorials/memory/`, `memory/`
- **Services**: `tutorials/service/`
- **Streaming**: `tutorials/stream_mode/`
- **Distributed**: `rag/qa_dense_retrieval_ray.py`

### By Technology

- **ChromaDB**: `rag/config/config_qa_chroma.yaml`, `rag/qa_dense_retrieval_chroma.py`
- **Milvus**: `rag/config/config_*_milvus.yaml`, `rag/*_milvus.py`
- **Ray**: `rag/config/config_ray.yaml`, `rag/qa_dense_retrieval_ray.py`
- **OpenAI**: Most RAG examples
- **Hugging Face**: `rag/qa_hf_model.py`
- **Local LLMs**: `tutorials/rag/qa_local_llm.py`

### By Use Case

- **Question Answering**: `rag/qa_*.py`
- **Document Search**: `rag/build_*_index.py`, `rag/qa_dense_retrieval.py`
- **Image Search**: `tutorials/multimodal/`
- **Video Analysis**: `apps/run_video_intelligence.py`
- **Medical AI**: `apps/run_medical_diagnosis.py`
- **Web Services**: `tutorials/service/pipeline_as_service/`
