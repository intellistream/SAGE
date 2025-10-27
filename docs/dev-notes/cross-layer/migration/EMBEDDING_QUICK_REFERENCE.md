# SAGE Embedding 系统快速参考 🚀

**Date**: 2024-09-26  
**Author**: SAGE Team  
**Summary**: Embedding 快速参考

---


一页纸速查表，包含最常用的命令和代码片段。

---

## 📋 CLI 命令速查

### Embedding 管理

```bash
# 列出所有可用方法
sage embedding list
sage embedding list --format json

# 检查方法可用性
sage embedding check hash
sage embedding check openai --verbose

# 测试方法
sage embedding test hash --text "测试文本"
sage embedding test openai --show-vector

# 性能对比
sage embedding benchmark hash mockembedder
sage embedding benchmark hash openai --count 100
```

### Pipeline Builder

```bash
# 使用默认 hash 方法
sage pipeline build --name "我的 Pipeline" --goal "构建 RAG"

# 使用 OpenAI embedding
sage pipeline build \
  --embedding-method openai \
  --embedding-model text-embedding-3-small

# 使用本地 HuggingFace 模型
sage pipeline build \
  --embedding-method hf \
  --embedding-model BAAI/bge-small-zh-v1.5

# 分析最佳 embedding 方法
sage pipeline analyze-embedding "如何构建 RAG pipeline"
sage pipeline analyze-embedding "查询" -m hash -m openai -m hf
```

---

## 💻 Python API 速查

### 基本使用

```python
from sage.common.components.sage_embedding import EmbeddingFactory

# 创建 embedder
embedder = EmbeddingFactory.create("hash", dimension=384)

# 单个文本
vector = embedder.embed("Hello, world!")

# 批量处理
texts = ["文本1", "文本2", "文本3"]
vectors = embedder.embed_batch(texts)
```

### 不同方法示例

```python
# Hash (本地、快速)
hash_emb = EmbeddingFactory.create("hash", dimension=384)

# HuggingFace (本地、高质量)
hf_emb = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")

# OpenAI (云端、最佳)
openai_emb = EmbeddingFactory.create(
    "openai",
    model="text-embedding-3-small",
    api_key="sk-xxx"
)

# Zhipu (云端、中文优化)
zhipu_emb = EmbeddingFactory.create(
    "zhipu",
    model="embedding-2",
    api_key="xxx"
)
```

### Pipeline Builder 集成

```python
from sage.tools.cli.commands.pipeline_knowledge import (
    PipelineKnowledgeBase,
    get_default_knowledge_base,
)

# 方式 1: 使用默认配置
kb = get_default_knowledge_base()

# 方式 2: 自定义 embedding 方法
kb = PipelineKnowledgeBase(
    embedding_method="openai",
    embedding_model="text-embedding-3-small",
    max_chunks=2000,
)

# 检索
results = kb.search("如何构建 RAG pipeline", top_k=5)
for chunk in results:
    print(f"[{chunk.score:.4f}] {chunk.text[:100]}")
```

---

## 🌍 环境变量

```bash
# Pipeline Builder 默认 embedding
export SAGE_PIPELINE_EMBEDDING_METHOD=openai
export SAGE_PIPELINE_EMBEDDING_MODEL=text-embedding-3-small

# API Keys
export OPENAI_API_KEY=sk-xxx
export ZHIPU_API_KEY=xxx
export COHERE_API_KEY=xxx
export JINA_API_KEY=jina_xxx

# HuggingFace 缓存
export HF_HOME=/path/to/cache
```

---

## 📊 方法选择指南

| 场景 | 推荐方法 | 命令示例 |
|------|----------|----------|
| **快速原型** | hash | `--embedding-method hash` |
| **离线高质量** | hf (bge-base) | `--embedding-method hf --embedding-model BAAI/bge-base-zh-v1.5` |
| **云端最优** | openai | `--embedding-method openai --embedding-model text-embedding-3-small` |
| **中文优化** | zhipu / hf | `--embedding-method zhipu --embedding-model embedding-2` |
| **英文优化** | openai / cohere | `--embedding-method openai` |
| **多语言** | cohere | `--embedding-method cohere` |
| **本地 LLM** | ollama | `--embedding-method ollama --embedding-model nomic-embed-text` |

---

## ⚡ 性能参考

| 方法 | 速度 | 质量 | 成本 | 离线 |
|------|------|------|------|------|
| hash | ⚡⚡⚡⚡⚡ | ⭐⭐ | 免费 | ✅ |
| mockembedder | ⚡⚡⚡⚡⚡ | ⭐ | 免费 | ✅ |
| hf (small) | ⚡⚡⚡ | ⭐⭐⭐⭐ | 免费 | ✅ |
| hf (base) | ⚡⚡ | ⭐⭐⭐⭐⭐ | 免费 | ✅ |
| openai | ⚡⚡ | ⭐⭐⭐⭐⭐ | $$ | ❌ |
| zhipu | ⚡⚡ | ⭐⭐⭐⭐ | $ | ❌ |

---

## 🔧 常见问题

### Q: 如何选择最佳方法？

```bash
# 先分析对比
sage pipeline analyze-embedding "你的典型查询" \
  -m hash -m hf -m openai

# 使用推荐的方法
sage pipeline build --embedding-method <推荐方法>
```

### Q: HuggingFace 模型下载太慢？

```bash
# 使用镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或手动下载后指定路径
--embedding-model /path/to/local/model
```

### Q: OpenAI API 调用失败？

```bash
# 检查 API key
echo $OPENAI_API_KEY

# 使用自定义 base_url（如使用代理）
export OPENAI_BASE_URL=https://your-proxy.com/v1
```

### Q: 如何使用自己的向量？

```python
# 直接使用 numpy 数组
import numpy as np
from sage.common.components.sage_embedding import BaseEmbedding

class CustomEmbedding(BaseEmbedding):
    def embed(self, text: str) -> list:
        # 你的实现
        return your_vector.tolist()
```

---

## 📚 更多资源

- **完整文档**: `docs/dev-notes/EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md`
- **Phase 1-3**: `docs/dev-notes/EMBEDDING_OPTIMIZATION_PHASE*.md`
- **Pipeline 集成**: `docs/dev-notes/PIPELINE_BUILDER_EMBEDDING_INTEGRATION.md`
- **示例代码**: `examples/tutorials/embedding_demo.py`

---

## 🎯 一分钟快速开始

```bash
# 1. 查看可用方法
sage embedding list

# 2. 测试一个方法
sage embedding test hash --text "Hello, SAGE!"

# 3. 对比性能
sage embedding benchmark hash mockembedder

# 4. 在 Pipeline Builder 中使用
sage pipeline build \
  --name "我的第一个 Pipeline" \
  --goal "构建智能问答系统" \
  --embedding-method hash  # 先用快速方法测试

# 5. 分析并选择最佳方法
sage pipeline analyze-embedding "你的查询"

# 6. 使用最佳方法重新构建
sage pipeline build \
  --embedding-method <最佳方法> \
  --name "优化后的 Pipeline"
```

---

**快速参考 v2.0** | 更新于 2024-10-06 | SAGE Embedding 系统
