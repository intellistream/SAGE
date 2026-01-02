# Document Storage Feature in SAGE

**Status**: ✅ **Fully Implemented**\
**Location**: `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/`\
**Related Issue**: #610 (Parent), Current issue (Document Storage Implementation)

## Executive Summary

SAGE已经完整实现了RAG系统的文档存储功能。该功能集成在`neuromem`组件中，提供了原始文档的高效存储、检索、更新和关联机制。

## Feature Overview

### Core Components

文档存储功能由以下核心组件构成：

#### 1. TextStorage（文本存储引擎）

**位置**: `storage_engine/text_storage.py`

**功能**:

- 存储原始文档文本
- 支持基于ID的快速检索
- 提供磁盘持久化（JSON格式）
- 支持批量操作

**API**:

```python
class TextStorage:
    def store(self, item_id: str, text: str)          # 存储文本
    def get(self, item_id: str) -> str                # 获取文本
    def has(self, item_id: str) -> bool               # 检查文本是否存在
    def delete(self, item_id: str)                    # 删除文本
    def clear()                                       # 清空所有文本
    def get_all_ids() -> List[str]                    # 获取所有ID
    def store_to_disk(self, path: str)                # 持久化到磁盘
    def load_from_disk(self, path: str)               # 从磁盘加载
```

#### 2. MetadataStorage（元数据存储引擎）

**位置**: `storage_engine/metadata_storage.py`

**功能**:

- 存储文档元数据（标题、来源、标签等）
- 支持动态字段注册
- 字段验证
- 元数据过滤查询

**API**:

```python
class MetadataStorage:
    def add_field(self, field_name: str)              # 注册字段
    def has_field(self, field_name: str) -> bool      # 检查字段
    def store(self, item_id: str, metadata: Dict)     # 存储元数据
    def get(self, item_id: str) -> Dict               # 获取元数据
    def delete(self, item_id: str)                    # 删除元数据
    def clear()                                       # 清空所有元数据
```

#### 3. VectorStorage（向量存储引擎）

**位置**: `storage_engine/vector_storage.py`

**功能**:

- 存储文档的向量嵌入
- 支持向量检索
- 与TextStorage和MetadataStorage协同工作

#### 4. BaseMemoryCollection（基础内存集合）

**位置**: `memory_collection/base_collection.py`

**功能**:

- 统一的文档CRUD接口
- 自动生成稳定ID（基于SHA256）
- 元数据过滤检索
- 组合TextStorage和MetadataStorage

**API**:

```python
class BaseMemoryCollection:
    def insert(self, raw_text: str, metadata: Optional[Dict] = None) -> str
    def retrieve(self, with_metadata: bool = False,
                 metadata_filter_func: Optional[Callable] = None,
                 **metadata_conditions) -> List
    def get_all_ids() -> List[str]
    def clear()
```

#### 5. VDBMemoryCollection（向量数据库集合）

**位置**: `memory_collection/vdb_collection.py`

**功能**:

- 完整的RAG支持
- 文本存储 + 向量索引 + 元数据管理
- 多索引支持
- 批量插入
- 向量检索与元数据过滤结合

**API**:

```python
class VDBMemoryCollection(BaseMemoryCollection):
    def create_index(self, config: Dict)              # 创建索引
    def batch_insert_data(self, data: List[str],      # 批量插入
                          metadatas: Optional[List[Dict]] = None)
    def insert(self, index_name: str,                 # 单条插入
               raw_data: str,
               metadata: Optional[Dict] = None)
    def retrieve(self, raw_data: str,                 # 向量检索
                 index_name: str,
                 topk: int = 5,
                 threshold: float = 0.0,
                 with_metadata: bool = False) -> List
    def delete_by_id(self, stable_id: str)            # 删除文档
```

#### 6. MemoryManager（内存管理器）

**位置**: `memory_manager.py`

**功能**:

- 管理多个MemoryCollection
- 集合的创建、加载、删除
- 集合持久化和懒加载
- 状态管理

**API**:

```python
class MemoryManager:
    def create_collection(self, config: Dict) -> BaseMemoryCollection
    def get_collection(self, name: str) -> Optional[BaseMemoryCollection]
    def has_collection(self, name: str) -> bool
    def delete_collection(self, name: str)
    def store_collection(self, name: Optional[str] = None)
    def load_collection(self, name: str) -> Optional[BaseMemoryCollection]
```

## Usage Examples

### Example 1: Basic Document Storage

```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

# 创建管理器
manager = MemoryManager()

# 创建文档集合
config = {
    "name": "documents",
    "backend_type": "VDB",
    "description": "Document storage collection"
}
collection = manager.create_collection(config)

# 批量插入文档
documents = [
    "Python是一种高级编程语言",
    "机器学习是人工智能的一个分支",
    "深度学习使用神经网络"
]

metadatas = [
    {"source": "textbook", "chapter": 1, "lang": "zh"},
    {"source": "paper", "year": 2020, "lang": "zh"},
    {"source": "tutorial", "level": "advanced", "lang": "zh"}
]

collection.batch_insert_data(documents, metadatas)

# 持久化到磁盘
manager.store_collection("documents")
```

### Example 2: Document Retrieval with Metadata Filtering

```python
# 基于元数据检索
results = collection.retrieve(
    with_metadata=True,
    source="textbook"
)

# 使用自定义过滤函数
results = collection.retrieve(
    with_metadata=True,
    metadata_filter_func=lambda m: m.get("year", 0) > 2019
)
```

### Example 3: RAG with Vector Search

```python
# 创建向量索引
index_config = {
    "name": "semantic_index",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "dim": 384,
    "backend_type": "FAISS",
    "description": "Semantic search index"
}
collection.create_index(index_config)

# 初始化索引（为所有文档生成向量）
collection.init_index("semantic_index")

# 向量检索
query = "什么是人工智能"
results = collection.retrieve(
    raw_data=query,
    index_name="semantic_index",
    topk=3,
    threshold=0.3,
    with_metadata=True
)

for result in results:
    print(f"Text: {result['text']}")
    print(f"Metadata: {result['metadata']}")
    print(f"Score: {result.get('score', 'N/A')}")
    print("---")
```

### Example 4: Document Updates

```python
# 更新文档（通过重新插入相同ID）
doc_id = collection._get_stable_id("原始文档文本")
collection.text_storage.store(doc_id, "更新后的文档文本")
collection.metadata_storage.store(doc_id, {"updated": True})

# 删除文档
collection.delete_by_id(doc_id)
```

### Example 5: Cross-Collection Operations

```python
# 创建多个集合
manager = MemoryManager()

# 技术文档集合
tech_docs = manager.create_collection({
    "name": "tech_docs",
    "backend_type": "VDB",
    "description": "Technical documentation"
})

# 业务文档集合
business_docs = manager.create_collection({
    "name": "business_docs",
    "backend_type": "VDB",
    "description": "Business documentation"
})

# 分别存储不同类型的文档
tech_docs.batch_insert_data(tech_documents, tech_metadatas)
business_docs.batch_insert_data(biz_documents, biz_metadatas)

# 持久化所有集合
manager.store_collection()
```

## Architecture Integration

### RAG Pipeline Integration

文档存储与RAG pipeline的集成：

```
Query → Retriever → [VDBMemoryCollection]
                      ├── TextStorage (原文)
                      ├── VectorStorage (向量)
                      └── MetadataStorage (元数据)
                            ↓
                      Retrieved Docs
                            ↓
         Generator → Answer
```

### Layer Architecture

```
L6: sage-cli, sage-tools        # CLI工具
L5: sage-apps                   # 应用层
L4: sage-middleware             # 中间件层
    └── components/
        └── sage_mem/
            └── neuromem/       # ← 文档存储在这里
L3: sage-kernel, sage-libs      # 核心算法
L2: sage-platform               # 平台服务
L1: sage-common                 # 基础组件
```

## Tests and Examples

### Unit Tests

- `packages/sage-middleware/tests/components/sage_mem/test_vdb.py`
- `packages/sage-middleware/tests/components/sage_mem/test_manager.py`

### Integration Examples

- `examples/tutorials/L4-middleware/memory_service/rag_memory_manager.py`
- `examples/tutorials/L3-libs/rag/usage_4_complete_rag.py`
- `examples/tutorials/L3-libs/rag/usage_3_memory_service.py`

### Running Tests

```bash
# 运行VDB集合测试
python -m pytest packages/sage-middleware/tests/components/sage_mem/test_vdb.py -v

# 运行内存管理器测试
python -m pytest packages/sage-middleware/tests/components/sage_mem/test_manager.py -v

# 运行示例
python examples/tutorials/L4-middleware/memory_service/rag_memory_manager.py
```

## Documentation

### Developer Documentation

- **Architecture Analysis**:
  `docs/dev-notes/cross-layer/architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md`
- **This Document**: `docs/dev-notes/l4-middleware/DOCUMENT_STORAGE_FEATURE.md`

### Public Documentation

- **Neuromem Guide**: `docs-public/docs_src/guides/packages/sage-middleware/components/neuromem.md`
- **Memory Service**:
  `docs-public/docs_src/guides/packages/sage-middleware/service/memory/memory_service.md`
- **API Reference**: `docs-public/docs_src/api-reference/`

## Performance Considerations

### Storage Backend Options

1. **In-Memory (Default - DictKVBackend)**

   - Fast read/write
   - Limited by RAM
   - Best for: Small to medium datasets, development

1. **Disk (JSON)**

   - Persistent storage
   - Slower than in-memory
   - Best for: Production use, long-term storage

1. **HDFS (Optional)**

   - Distributed storage
   - Requires pyarrow
   - Best for: Large-scale deployments

### Vector Index Options

1. **FAISS**

   - Fast approximate nearest neighbor search
   - Multiple index types (Flat, IVF, HNSW)
   - Best for: Large-scale vector search

1. **BM25s**

   - Keyword-based search
   - Sparse vectors
   - Best for: Text matching

## Future Enhancements

Potential improvements (from issue #610 parent):

1. **Graph-based Document Relations**

   - Currently TODO in `graph_collection.py`
   - Would enable document dependency tracking

1. **Advanced Metadata Indexing**

   - Secondary indexes on metadata fields
   - Range queries, full-text search on metadata

1. **Version Control**

   - Document history tracking
   - Rollback capabilities

1. **Compression**

   - Text compression for storage efficiency
   - Vector quantization

1. **Distributed Storage**

   - Multi-node deployment
   - Sharding support

## Related Issues

- Parent Issue: #610 (RAG System Enhancement)
- This Issue: Document Storage Implementation (Status: ✅ Implemented)

## Conclusion

文档存储功能已经完整实现并集成到SAGE的neuromem组件中。该实现提供了：

✅ **高效存储** - TextStorage提供原始文本的高效存储\
✅ **灵活检索** - 支持向量检索、元数据过滤、混合检索\
✅ **完整管理** - 支持增删改查、批量操作、持久化\
✅ **关联机制** - MetadataStorage提供灵活的文档关联\
✅ **生产就绪** - 已有测试覆盖和实际应用案例

用户可以直接使用现有的API进行文档存储和检索操作。
