# VDBMemoryCollection 使用指南

`VDBMemoryCollection` 是 Neuromem 记忆栈中功能最完整的集合实现，负责管理文本、元数据以及向量索引。当前仓库的实现完全基于 Python，索引后端默认通过
`index_factory` 创建 FAISS 索引。

- 模块位置：`packages/sage-middleware/src/sage/middleware/components/neuromem/memory_collection/vdb_collection.py`
- 依赖组件：`TextStorage`、`MetadataStorage`、`index_factory`（FAISS 等）
- 典型入口：通过 `MemoryManager.create_collection(backend_type="VDB")` 获取实例，或直接构造

______________________________________________________________________

## 一、快速开始

```python
from sage.middleware.components.neuromem.memory_manager import MemoryManager

# 1. 创建集合（若集合已存在可直接通过 manager.get_collection 加载）
manager = MemoryManager()
collection = manager.create_collection(
    {"name": "kb", "backend_type": "VDB", "description": "知识库"}
)

# 2. 批量写入文本与元数据（仅存储，不自动建索引）
collection.batch_insert_data(
    [
        "Python 是一种高级编程语言",
        "FAISS 可以用于高维向量检索",
    ],
    [
        {"tag": "intro"},
        {"tag": "retrieval"},
    ],
)

# 3. 创建并初始化索引
collection.create_index(
    {
        "name": "global_index",
        "description": "默认检索索引",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "dim": 384,
        "backend_type": "FAISS",
    }
)
collection.init_index("global_index")

# 4. 检索
results = collection.retrieve(
    "向量数据库是什么？",
    index_name="global_index",
    topk=3,
    with_metadata=True,
)
print(results)

# 5. 序列化
collection.store()
```

______________________________________________________________________

## 二、初始化与配置

构造函数接收一个包含至少 `name` 的配置字典：

```python
VDBMemoryCollection({"name": "kb"})
```

通过 `MemoryManager` 创建时，需同时提供 `backend_type="VDB"`。`description` 等其他字段会被记录在 `manager.json` 中，便于后续查询。

索引配置示例：

| 键                | 必填 | 说明                                     |
| ----------------- | ---- | ---------------------------------------- |
| `name`            | 是   | 索引名称（如 `global_index`）。          |
| `embedding_model` | 是   | 嵌入模型标识，传递给 `EmbeddingModel`。  |
| `dim`             | 是   | 嵌入向量维度，需与模型匹配。             |
| `backend_type`    | 是   | 索引后端类型，当前实现建议使用 `FAISS`。 |
| `description`     | 否   | 备注信息。                               |
| `index_parameter` | 否   | 传递给 `index_factory` 的后端特定配置。  |

______________________________________________________________________

## 三、核心 API

### 数据写入

| 方法                                                                                  | 说明                                           |
| ------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `batch_insert_data(data: List[str], metadatas: Optional[List[Dict]] = None)`          | 批量写入文本与可选元数据，不触发索引。         |
| `insert(index_name: str, raw_data: str, metadata: Optional[Dict])`                    | 将文本写入指定索引，同时存储文本与元数据。     |
| `update(former_data: str, new_data: str, new_metadata: Optional[Dict], *index_names)` | 用新文本替换旧文本并更新索引。                 |
| `delete(raw_text: str)`                                                               | 移除文本及元数据，并在所有索引中删除对应向量。 |

### 检索与索引

| 方法                                                                                                                                                                                   | 说明                                               |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `create_index(config: dict)`                                                                                                                                                           | 创建索引但不导入数据。                             |
| `init_index(index_name: str, metadata_filter_func: Optional[Callable] = None, **metadata)`                                                                                             | 按条件批量导入现有数据，避免手动遍历。             |
| `update_index(index_name: str, metadata_filter_func=None, **metadata)`                                                                                                                 | 重建索引：删除并使用原配置重新创建后导入数据。     |
| `list_index(*index_names)`                                                                                                                                                             | 列出全部或指定索引的描述信息。                     |
| `retrieve(raw_data: str, index_name: str, topk: int = 5, threshold: Optional[float] = None, with_metadata: bool = False, metadata_filter_func: Optional[Callable] = None, **metadata)` | 生成查询向量并检索结果，可返回元数据并按条件过滤。 |

### 持久化

| 方法                                                              | 说明                   |
| ----------------------------------------------------------------- | ---------------------- |
| `store(store_path: Optional[str] = None)`                         | 将集合及索引写入磁盘。 |
| `load(name: str, vdb_path: Optional[str] = None)` *(类方法)*      | 从磁盘恢复集合。       |
| `clear(name: str, clear_path: Optional[str] = None)` *(静态方法)* | 删除磁盘上的集合目录。 |

______________________________________________________________________

## 四、与 MemoryManager 协作

- `MemoryManager` 会在 `manager.json` 中记录集合元信息（描述、后端类型、状态）。
- `get_collection(name)` 可懒加载磁盘上的集合；重新载入后会将集合放入内存缓存。
- `store_collection(name=None)` 会调用集合的 `store()` 方法，并写回最新元信息。

______________________________________________________________________

## 五、常见问题

- **没有索引如何检索？** 必须先调用 `create_index` + `init_index`，否则 `retrieve` 会提示索引不存在。
- **嵌入模型加载失败？** 默认通过 `EmbeddingModel` 使用 HuggingFace 模型；在无网络环境可改为 `method="mockembedder"` 并设置
  `fixed_dim`。
- **批量写入后索引未更新？** `batch_insert_data` 只写存储不更新索引，需显式调用 `init_index` 或 `update_index`。
- **如何筛选特定元数据？** 使用 `metadata_filter_func`（函数形式）或直接传入关键字参数进行精确匹配。

______________________________________________________________________

更多细节请参考源码：`memory_collection/vdb_collection.py` 与 `search_engine/vdb_index/`。
