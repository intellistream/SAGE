# 检索组件 (Retrieval Components)

本文档详细介绍SAGE框架中检索组件的使用方法。检索组件是RAG系统的核心查询引擎，负责从构建好的向量索引中快速准确地检索与用户查询相关的文档内容。

## 组件概述

### 核心功能
检索组件在RAG系统中承担以下关键职责：

- **语义检索**：基于向量相似度进行语义级别的文档检索
- **多源整合**：支持多种向量数据库和检索算法
- **结果排序**：按相关性对检索结果进行排序和筛选
- **性能优化**：提供高效的大规模文档检索能力

### 技术架构
检索组件采用模块化设计，支持多种后端实现：

```
用户查询 → 查询向量化 → 相似度计算 → 结果排序 → 文档返回
   ↓         ↓           ↓           ↓         ↓
 文本处理 → 嵌入模型    → 向量数据库  → TopK选择 → 标准化输出
```

## ChromaRetriever

### 组件描述
`ChromaRetriever`是基于ChromaDB向量数据库的检索器，支持高效的向量相似度检索和完整的文档生命周期管理。

### 技术规格

**支持特性**：
- 向量相似度检索（余弦、欧氏距离等）
- 元数据过滤
- 混合检索（向量+关键词）
- 增量索引更新
- 分布式存储支持

**配置参数**：

| 参数组 | 参数名 | 类型 | 默认值 | 说明 |
|--------|--------|------|--------|------|
| **基础配置** | `dimension` | int | 384 | 向量维度 |
| | `top_k` | int | 5 | 返回文档数量 |
| **嵌入配置** | `embedding.method` | str | "default" | 嵌入方法 |
| | `embedding.model` | str | "all-MiniLM-L6-v2" | 嵌入模型名称 |
| **数据库配置** | `chroma.persist_path` | str | - | 数据库存储路径 |
| | `chroma.collection_name` | str | - | 集合名称 |
| | `chroma.knowledge_file` | str | - | 知识库文件路径 |

### 实现示例

#### 基础检索配置
```python
from sage.libs.rag.retriever import ChromaRetriever

# 标准检索器配置
config = {
    "dimension": 384,
    "top_k": 5,
    "embedding": {
        "method": "default",
        "model": "sentence-transformers/all-MiniLM-L6-v2"
    },
    "chroma": {
        "persist_path": "./vector_database",
        "collection_name": "knowledge_base",
        "knowledge_file": "data/documents.txt"
    }
}

# 初始化检索器
retriever = ChromaRetriever(config)
```

#### 单次查询检索
```python
# 字符串查询
query = "向量数据库的优势是什么？"
results = retriever.execute(query)

print("检索结果:")
for i, doc in enumerate(results["results"], 1):
    print(f"{i}. {doc}")
```

#### 字典格式查询
```python
# 字典查询（支持更多参数）
query_dict = {
    "query": "机器学习算法分类",
    "top_k": 8,  # 覆盖默认配置
    "filter": {"category": "ai"}  # 元数据过滤
}

results = retriever.execute(query_dict)
print(f"找到 {len(results['results'])} 个相关文档")
```

#### 批量查询处理
```python
# 批量查询
queries = [
    "什么是深度学习？",
    "神经网络的基本结构",
    "反向传播算法原理"
]

batch_results = []
for query in queries:
    result = retriever.execute(query)
    batch_results.append(result["results"])

print(f"批量处理完成，共处理 {len(queries)} 个查询")
```

### 文档管理功能

#### 添加新文档
```python
# 单个文档添加
new_document = "SAGE是一个先进的RAG框架，支持多种向量检索方法。"
doc_id = "sage_intro_001"

retriever.add_documents([new_document], [doc_id])
print(f"文档 {doc_id} 添加成功")

# 批量文档添加
new_docs = [
    "ChromaDB是一个开源向量数据库。",
    "向量检索在信息检索中应用广泛。",
    "语义搜索比关键词搜索更智能。"
]
doc_ids = ["chroma_001", "vector_001", "semantic_001"]

retriever.add_documents(new_docs, doc_ids)
print(f"批量添加 {len(new_docs)} 个文档成功")
```

#### 文档更新与删除
```python
# 更新现有文档
updated_content = "SAGE框架已升级到2.0版本，新增多项高级功能。"
retriever.update_document("sage_intro_001", updated_content)

# 删除文档
retriever.delete_documents(["outdated_doc_001", "deprecated_doc_002"])
print("过期文档删除完成")
```

## 高级检索功能

### 混合检索
```python
# 配置混合检索（向量+BM25）
hybrid_config = {
    **config,  # 继承基础配置
    "hybrid_search": {
        "enabled": True,
        "vector_weight": 0.7,    # 向量检索权重
        "keyword_weight": 0.3,   # 关键词检索权重
        "keyword_method": "bm25" # 关键词检索算法
    }
}

hybrid_retriever = ChromaRetriever(hybrid_config)

# 执行混合检索
query = "深度学习在自然语言处理中的应用"
hybrid_results = hybrid_retriever.execute(query)
```

### 元数据过滤检索
```python
# 带元数据过滤的检索
filtered_query = {
    "query": "机器学习模型评估",
    "filter": {
        "category": "machine_learning",
        "difficulty": "intermediate",
        "language": "chinese"
    },
    "top_k": 3
}

filtered_results = retriever.execute(filtered_query)
print("过滤检索完成")
```

### 多轮对话检索
```python
class ConversationalRetriever:
    def __init__(self, base_retriever):
        self.retriever = base_retriever
        self.conversation_history = []
    
    def retrieve_with_context(self, current_query):
        # 构建上下文增强查询
        if self.conversation_history:
            context = " ".join(self.conversation_history[-3:])  # 最近3轮对话
            enhanced_query = f"上下文: {context} 当前问题: {current_query}"
        else:
            enhanced_query = current_query
        
        # 执行检索
        results = self.retriever.execute(enhanced_query)
        
        # 更新对话历史
        self.conversation_history.append(current_query)
        
        return results

# 使用对话式检索器
conv_retriever = ConversationalRetriever(retriever)

# 多轮对话示例
queries = [
    "什么是神经网络？",
    "它有哪些类型？",
    "在图像识别中如何应用？"
]

for query in queries:
    results = conv_retriever.retrieve_with_context(query)
    print(f"查询: {query}")
    print(f"最佳匹配: {results['results'][0][:100]}...")
    print()
```

## 性能优化策略

### 索引优化
```python
# 大规模数据集的索引优化配置
optimized_config = {
    "dimension": 768,  # 使用更高维度的嵌入
    "top_k": 10,
    "embedding": {
        "model": "sentence-transformers/all-mpnet-base-v2",
        "batch_size": 64,  # 批处理优化
        "normalize_embeddings": True
    },
    "chroma": {
        "persist_path": "./optimized_db",
        "collection_name": "large_knowledge_base",
        "index_params": {
            "hnsw:space": "cosine",
            "hnsw:construction_ef": 400,
            "hnsw:search_ef": 200,
            "hnsw:M": 32
        }
    }
}
```

### 缓存策略
```python
from functools import lru_cache
import hashlib

class CachedRetriever:
    def __init__(self, base_retriever, cache_size=1000):
        self.retriever = base_retriever
        self.cache_size = cache_size
    
    @lru_cache(maxsize=1000)
    def _cached_retrieve(self, query_hash):
        return self.retriever.execute(query_hash)
    
    def execute(self, query):
        # 生成查询哈希
        if isinstance(query, str):
            query_hash = hashlib.md5(query.encode()).hexdigest()
        else:
            query_str = str(sorted(query.items()))
            query_hash = hashlib.md5(query_str.encode()).hexdigest()
        
        return self._cached_retrieve(query_hash)

# 使用缓存检索器
cached_retriever = CachedRetriever(retriever)
```

### 并发处理
```python
import concurrent.futures
from typing import List

def parallel_retrieve(retriever, queries: List[str], max_workers=4):
    """并行处理多个检索查询"""
    
    def single_retrieve(query):
        return retriever.execute(query)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有查询
        future_to_query = {
            executor.submit(single_retrieve, query): query 
            for query in queries
        }
        
        # 收集结果
        results = {}
        for future in concurrent.futures.as_completed(future_to_query):
            query = future_to_query[future]
            try:
                result = future.result()
                results[query] = result
            except Exception as exc:
                print(f"查询 '{query}' 生成异常: {exc}")
                results[query] = None
    
    return results

# 并行检索示例
test_queries = [
    "什么是机器学习？",
    "深度学习的应用",
    "自然语言处理技术",
    "计算机视觉算法"
]

parallel_results = parallel_retrieve(retriever, test_queries)
for query, result in parallel_results.items():
    if result:
        print(f"查询: {query} -> 检索到 {len(result['results'])} 个文档")
```

## 最佳实践

### 查询优化技巧

1. **查询重写**：对用户查询进行语义扩展和规范化
2. **多策略融合**：结合向量检索和关键词检索
3. **动态Top-K**：根据查询复杂度调整返回文档数量
4. **结果去重**：避免返回高度相似的重复文档

### 质量监控

```python
class RetrievalQualityMonitor:
    def __init__(self, retriever):
        self.retriever = retriever
        self.metrics = {
            "queries_count": 0,
            "avg_relevance_score": 0.0,
            "zero_results_count": 0
        }
    
    def monitored_retrieve(self, query):
        results = self.retriever.execute(query)
        
        # 更新指标
        self.metrics["queries_count"] += 1
        if not results.get("results"):
            self.metrics["zero_results_count"] += 1
        
        return results
    
    def get_stats(self):
        if self.metrics["queries_count"] > 0:
            zero_rate = self.metrics["zero_results_count"] / self.metrics["queries_count"]
            return {
                "total_queries": self.metrics["queries_count"],
                "zero_results_rate": zero_rate,
                "coverage": 1 - zero_rate
            }
        return {"no_data": True}

# 使用质量监控
monitor = RetrievalQualityMonitor(retriever)
```

### 错误处理与容错

```python
class RobustRetriever:
    def __init__(self, primary_retriever, fallback_method=None):
        self.primary = primary_retriever
        self.fallback = fallback_method
    
    def execute(self, query, max_retries=3):
        for attempt in range(max_retries):
            try:
                results = self.primary.execute(query)
                if results and results.get("results"):
                    return results
            except Exception as e:
                print(f"检索尝试 {attempt + 1} 失败: {e}")
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，使用备用方法
                    if self.fallback:
                        return self.fallback(query)
                    else:
                        return {"results": [], "error": str(e)}
        
        return {"results": [], "error": "All retrieval attempts failed"}

# 创建健壮的检索器
robust_retriever = RobustRetriever(
    retriever, 
    fallback_method=lambda q: {"results": [f"未找到关于'{q}'的相关信息"]}
)
```

```python
query_dict = {"question": "SAGE有哪些检索方式？"}
result = retriever.execute(query_dict)
print(result["results"])
```

### 获取集合信息

```python
info = retriever.get_collection_info()
print(info)
```

### 索引保存与加载

```python
retriever.save_index("my_index_config.json")
retriever.load_index("my_index_config.json")
```

---