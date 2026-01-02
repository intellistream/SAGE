# 文档存储使用指南

## 概述

SAGE的文档存储功能是RAG（检索增强生成）系统的核心组件，提供了原始文档的高效存储、检索、更新和管理能力。该功能集成在`neuromem`组件中，与向量检索无缝协作，实现完整的知识管理闭环。

## 核心特性

- ✅ **原始文档存储** - 保存文档的完整原文
- ✅ **元数据管理** - 灵活的文档属性标注（来源、标签、时间戳等）
- ✅ **向量检索** - 基于语义的文档检索
- ✅ **混合检索** - 结合向量相似度和元数据过滤
- ✅ **批量操作** - 支持大规模文档的高效导入
- ✅ **持久化存储** - 数据可保存到磁盘，支持重启后恢复
- ✅ **多集合管理** - 可创建多个独立的文档集合

## 快速开始

### 基础用法

```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

# 1. 创建内存管理器
manager = MemoryManager()

# 2. 创建文档集合
config = {
    "name": "my_documents",
    "backend_type": "VDB",  # 向量数据库类型
    "description": "我的文档集合"
}
collection = manager.create_collection(config)

# 3. 插入文档
documents = [
    "Python是一种广泛使用的高级编程语言",
    "机器学习是人工智能的核心技术之一",
    "深度学习通过多层神经网络学习数据表示"
]

metadatas = [
    {"source": "教材", "chapter": 1, "topic": "编程"},
    {"source": "论文", "year": 2020, "topic": "AI"},
    {"source": "教程", "level": "高级", "topic": "AI"}
]

collection.batch_insert_data(documents, metadatas)

# 4. 保存到磁盘
manager.store_collection("my_documents")
print("文档已保存！")
```

### 文档检索

```python
# 方式1: 基于元数据检索
results = collection.retrieve(
    with_metadata=True,
    source="教材"  # 只检索来源为"教材"的文档
)

for result in results:
    print(f"文本: {result['text']}")
    print(f"元数据: {result['metadata']}")
    print("---")

# 方式2: 使用自定义过滤函数
results = collection.retrieve(
    with_metadata=True,
    metadata_filter_func=lambda m: m.get("year", 0) > 2019
)

# 方式3: 多条件过滤
results = collection.retrieve(
    with_metadata=True,
    topic="AI",
    level="高级"
)
```

## 向量检索（语义搜索）

### 创建语义索引

```python
# 1. 配置向量索引
index_config = {
    "name": "semantic_index",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",  # 可选其他模型
    "dim": 384,  # 向量维度（取决于模型）
    "backend_type": "FAISS",  # 向量索引类型
    "description": "语义检索索引"
}

# 2. 创建索引
collection.create_index(index_config)

# 3. 初始化索引（为已有文档生成向量）
collection.init_index("semantic_index")
print("索引创建完成！")
```

### 语义检索

```python
# 使用自然语言查询
query = "如何使用神经网络进行学习？"

results = collection.retrieve(
    raw_data=query,
    index_name="semantic_index",
    topk=3,              # 返回最相关的3个结果
    threshold=0.3,       # 相似度阈值（0-1）
    with_metadata=True   # 包含元数据
)

for i, result in enumerate(results, 1):
    print(f"\n结果 {i}:")
    print(f"文本: {result['text']}")
    print(f"元数据: {result['metadata']}")
    print(f"相似度: {result.get('score', 'N/A')}")
```

### 混合检索（向量 + 元数据）

```python
# 同时使用语义检索和元数据过滤
results = collection.retrieve(
    raw_data="人工智能的应用",
    index_name="semantic_index",
    topk=5,
    with_metadata=True,
    metadata_filter_func=lambda m: m.get("topic") == "AI"
)
```

## 文档管理

### 单个文档插入

```python
# 插入带索引的单个文档
collection.insert(
    index_name="semantic_index",
    raw_data="Transformer是一种革命性的神经网络架构",
    metadata={"source": "论文", "year": 2017, "topic": "NLP"}
)
```

### 文档更新

```python
# 获取文档ID的两种方式：

# 方式1: 在插入时保存返回的ID
doc_id = collection.insert("文档内容", {"metadata": "value"})

# 方式2: 使用相同的文本重新计算ID (基于SHA256哈希)
# 注意：这要求文本内容完全相同
doc_text = "原始文档文本"
doc_id = collection._get_stable_id(doc_text)

# 更新文本内容
collection.text_storage.store(doc_id, "更新后的文档文本")

# 更新元数据
collection.metadata_storage.store(doc_id, {
    "source": "更新来源",
    "updated_at": "2024-01-01"
})

# 注意：建议在应用中维护文档ID的映射关系
# 例如：文档名称 -> 文档ID 的字典
doc_id_map = {}
doc_id_map["doc1"] = collection.insert("文档1内容", {"name": "doc1"})
# 后续可以通过doc_id_map["doc1"]获取ID进行更新
```

### 文档删除

```python
# 方式1: 直接使用delete方法（推荐）
collection.delete("要删除的文档文本")

# 方式2: 通过ID删除（需要先获取ID）
doc_id = collection._get_stable_id("要删除的文档文本")
collection.text_storage.delete(doc_id)
collection.metadata_storage.delete(doc_id)

# 方式3: 批量删除（通过元数据筛选）
# 先获取要删除的文档
docs_to_delete = collection.retrieve(
    with_metadata=True,
    metadata_filter_func=lambda m: m.get("source") == "过期来源"
)

# 逐个删除
for doc in docs_to_delete:
    collection.delete(doc['text'])
```

````

### 清空集合

```python
# 清空所有文档
collection.clear()
````

## 多集合管理

### 创建和管理多个集合

```python
manager = MemoryManager()

# 技术文档集合
tech_docs = manager.create_collection({
    "name": "tech_docs",
    "backend_type": "VDB",
    "description": "技术文档库"
})

# 业务文档集合
business_docs = manager.create_collection({
    "name": "business_docs",
    "backend_type": "VDB",
    "description": "业务文档库"
})

# 分别导入不同类型的文档
tech_docs.batch_insert_data(
    ["Python教程", "Git使用指南"],
    [{"type": "tech"}, {"type": "tech"}]
)

business_docs.batch_insert_data(
    ["产品需求文档", "市场分析报告"],
    [{"type": "business"}, {"type": "business"}]
)

# 保存所有集合
manager.store_collection()
```

### 集合的加载和删除

```python
# 检查集合是否存在
if manager.has_collection("tech_docs"):
    # 获取已存在的集合（会自动从磁盘加载）
    collection = manager.get_collection("tech_docs")

# 删除集合（内存+磁盘）
manager.delete_collection("old_collection")
```

## 持久化和恢复

### 保存到磁盘

```python
# 保存单个集合
manager.store_collection("my_documents")

# 保存所有集合
manager.store_collection()
```

### 从磁盘加载

```python
# 创建管理器时会自动加载已保存的集合元数据
manager = MemoryManager()

# 获取集合时会自动懒加载
collection = manager.get_collection("my_documents")

# 使用VDBMemoryCollection的类方法直接加载
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import VDBMemoryCollection

loaded_collection = VDBMemoryCollection.load(
    name="my_documents",
    load_path="/path/to/saved/collection"
)
```

### 自定义数据目录

```python
# 指定自定义存储路径
manager = MemoryManager(data_dir="/path/to/my/data")
```

## 高级用法

### 使用不同的Embedding模型

```python
# 方式1: 使用Sentence Transformers
index_config = {
    "name": "st_index",
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "dim": 384,
    "backend_type": "FAISS"
}

# 方式2: 使用OpenAI Embeddings（需要API密钥）
index_config = {
    "name": "openai_index",
    "embedding_model": "text-embedding-ada-002",
    "dim": 1536,
    "backend_type": "FAISS"
}
```

### 多索引支持

```python
# 在同一个集合上创建多个索引
collection.create_index({
    "name": "fast_index",
    "embedding_model": "mockembedder",  # 快速但精度较低
    "dim": 128,
    "backend_type": "FAISS"
})

collection.create_index({
    "name": "accurate_index",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",  # 更准确
    "dim": 384,
    "backend_type": "FAISS"
})

# 初始化两个索引
collection.init_index("fast_index")
collection.init_index("accurate_index")

# 使用不同的索引进行检索
fast_results = collection.retrieve(
    raw_data="查询文本",
    index_name="fast_index",
    topk=5
)

accurate_results = collection.retrieve(
    raw_data="查询文本",
    index_name="accurate_index",
    topk=5
)
```

### 元数据字段管理

```python
# 显式注册元数据字段（可选，batch_insert_data会自动注册）
collection.add_metadata_field("author")
collection.add_metadata_field("publish_date")
collection.add_metadata_field("category")

# 插入带有这些字段的文档
collection.insert(
    "文档内容",
    metadata={
        "author": "张三",
        "publish_date": "2024-01-15",
        "category": "技术"
    }
)
```

## 完整示例：构建知识库

```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
import json

# 1. 初始化管理器
manager = MemoryManager(data_dir="./my_knowledge_base")

# 2. 创建知识库集合
kb_config = {
    "name": "tech_kb",
    "backend_type": "VDB",
    "description": "技术知识库"
}
kb = manager.create_collection(kb_config)

# 3. 从文件加载文档
with open("documents.json", "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [item["content"] for item in data]
metadatas = [item["metadata"] for item in data]

# 4. 批量导入
kb.batch_insert_data(texts, metadatas)

# 5. 创建语义索引
kb.create_index({
    "name": "main_index",
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "dim": 384,
    "backend_type": "FAISS"
})

kb.init_index("main_index")

# 6. 保存
manager.store_collection("tech_kb")

# 7. 使用知识库
def search_knowledge(query, filters=None):
    """搜索知识库"""
    results = kb.retrieve(
        raw_data=query,
        index_name="main_index",
        topk=5,
        threshold=0.5,
        with_metadata=True,
        metadata_filter_func=filters
    )
    return results

# 示例查询
results = search_knowledge(
    "如何优化数据库性能",
    filters=lambda m: m.get("category") == "数据库"
)

for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['text'][:100]}...")
    print(f"   来源: {result['metadata'].get('source')}")
    print(f"   相似度: {result.get('score', 'N/A')}")
```

## 性能优化建议

### 批量操作

```python
# ✅ 推荐：使用批量插入
collection.batch_insert_data(large_text_list, large_metadata_list)

# ❌ 避免：逐个插入大量文档
for text, metadata in zip(large_text_list, large_metadata_list):
    collection.insert("index_name", text, metadata)  # 慢
```

### 索引策略

```python
# 对于大型数据集，先批量插入数据，再创建索引
collection.batch_insert_data(texts, metadatas)  # 快速导入
collection.create_index(index_config)            # 创建索引
collection.init_index("index_name")              # 一次性生成所有向量
```

### 内存管理

```python
# 使用完毕后清理
collection.clear()  # 清空内存中的数据

# 或者删除不需要的集合
manager.delete_collection("old_collection")
```

## 常见问题

### Q: 如何选择Embedding模型？

A:

- **小型模型**（推荐用于开发/测试）：`mockembedder`（测试用），`all-MiniLM-L6-v2`（384维）
- **中型模型**（推荐用于生产）：`paraphrase-multilingual-MiniLM-L12-v2`（384维，支持多语言）
- **大型模型**（高精度）：`text-embedding-ada-002`（OpenAI，1536维）

### Q: 向量维度如何确定？

A: 向量维度由Embedding模型决定：

- `all-MiniLM-L6-v2`: 384
- `text-embedding-ada-002`: 1536
- `mockembedder`: 128（测试用）

### Q: 如何处理大量文档？

A:

1. 使用`batch_insert_data`批量导入
1. 考虑分批处理（每批1000-10000条）
1. 创建索引后再导入新数据需要重新`init_index`

### Q: 元数据可以包含哪些类型？

A: 支持JSON可序列化的类型：

- 字符串、数字、布尔值
- 列表、字典（嵌套）
- None

### Q: 如何备份数据？

A:

```python
# 保存到磁盘
manager.store_collection()

# 数据存储在：data_dir/vdb_collection/collection_name/
# 包含：
# - text_storage.json（原文）
# - metadata_storage.json（元数据）
# - collection_data.json（配置和索引信息）
```

## 相关文档

- [Neuromem Architecture Analysis](../cross-layer/architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md)
- [Document Storage Feature Technical Guide](./DOCUMENT_STORAGE_FEATURE.md)
- [RAG Examples](../../../../examples/tutorials/L3-libs/rag/)
- [Memory Service Examples](../../../../examples/tutorials/L4-middleware/memory_service/)

## 支持

如有问题，请访问：

- GitHub Issues: https://github.com/intellistream/SAGE/issues
- 文档: https://sage.intellistream.com
