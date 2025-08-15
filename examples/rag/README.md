# RAG示例 (Retrieval-Augmented Generation Examples)

这个目录包含各种检索增强生成(RAG)的应用示例，展示不同的检索策略、生成方法和优化技术。

## 📁 文件分类

### 🔍 检索器示例
#### 稠密检索
- `qa_dense_retrieval.py` - 基础稠密向量检索
- `qa_dense_retrieval_mixed.py` - 混合检索策略
- `qa_dense_retrieval_ray.py` - 使用Ray的分布式检索

#### 稀疏检索  
- `qa_bm25_retrieval.py` - BM25稀疏检索
- `qa_bm25_retrieval_edit.py` - BM25检索的改进版本

### 🤖 生成器示例
- `qa_openai.py` - OpenAI生成器使用
- `qa_openai_chat_history.py` - 带对话历史的OpenAI生成
- `qa_hf.py` - HuggingFace生成器使用

### 🔄 完整RAG流水线
- `rag_simple.py` - 简化版RAG应用（推荐入门）
- `rag.py` - 完整的RAG系统
- `qa_source.py` - 问题源处理
- `qa_multiplex.py` - 多路复用RAG

### 🎯 高级优化
- `qa_refiner.py` - 答案精炼和优化
- `qa_rerank.py` - 检索结果重新排序

## 🚀 快速开始

### 1. 从简单RAG开始
```bash
python rag_simple.py
```

### 2. 尝试不同检索方法
```bash
# 稠密检索
python qa_dense_retrieval.py

# BM25检索  
python qa_bm25_retrieval.py
```

### 3. 探索高级功能
```bash
# 答案精炼
python qa_refiner.py

# 结果重排
python qa_rerank.py
```

## ⚙️ 相关配置文件

这些示例使用以下配置文件（在 `../../config/` 目录）：
- `config.yaml` - 基础RAG配置
- `config_bm25s.yaml` - BM25检索配置
- `config_mixed.yaml` - 混合检索配置
- `config_ray.yaml` - Ray分布式配置
- `config_refiner.yaml` - 答案精炼配置
- `config_rerank.yaml` - 重排序配置

## 📋 运行要求

### 环境变量
```bash
export OPENAI_API_KEY="your-openai-key"
```

### 配置文件
确保在运行前检查并更新相应的配置文件中的参数。

## 🎯 学习路径

1. **入门** → `rag_simple.py`
2. **检索探索** → `qa_dense_retrieval.py`, `qa_bm25_retrieval.py`  
3. **生成优化** → `qa_openai.py`, `qa_hf.py`
4. **系统优化** → `qa_refiner.py`, `qa_rerank.py`
5. **分布式处理** → `qa_dense_retrieval_ray.py`

## 🔗 相关资源

- [RAG模块文档](../../packages/sage-userspace/src/sage/lib/rag/README.md)
- [检索器API参考](../../packages/sage-userspace/src/sage/lib/rag/retriever.py)
- [生成器API参考](../../packages/sage-userspace/src/sage/lib/rag/generator.py)
