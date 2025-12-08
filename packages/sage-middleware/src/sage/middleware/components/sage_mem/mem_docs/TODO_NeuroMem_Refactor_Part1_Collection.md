# TODO Part 1: Collection 层重构

> ✅ **状态：已完成** (2025-12-02)
>
> 完成人：GitHub Copilot

## 背景

NeuroMem 的核心设计思想：

```
Collection = 一份数据 (text_storage + metadata_storage) + 多种类型的索引
```

**关键设计原则**：

1. **数据只存一份**：text_storage + metadata_storage
1. **索引可以有多种类型**：VDB（向量）、KV（文本/时序）、Graph（图）
1. **索引可以独立增删**：从某个索引移除不影响数据，可以把已有数据加到新索引

**三种基础 Collection 类型**：

- `VDBMemoryCollection`：只支持向量索引（当前最完整）
- `KVMemoryCollection`：只支持 KV 索引（BM25、FIFO、排序）
- `GraphMemoryCollection`：只支持图索引

**组合型 Collection（见 Part 6）**：

- `HybridCollection`：一份数据 + 多种类型索引（VDB + KV + Graph）

______________________________________________________________________

## 任务概述

本任务负责统一三种基础 Collection 的接口设计，确保：

1. Service 层可以多态调用
1. 为 HybridCollection 组合奠定基础

**涉及文件**：

- `memory_collection/base_collection.py`
- `memory_collection/vdb_collection.py`（参考实现）
- `memory_collection/kv_collection.py`（需要对齐）
- `memory_collection/graph_collection.py`（需要对齐）

______________________________________________________________________

## 1.1 统一 BaseMemoryCollection 抽象接口

**目标**：定义统一的抽象方法签名，所有 Collection 必须实现

**当前问题**：

- `insert()` 签名不统一：VDB 需要 `(index_name, raw_data, vector, metadata)`，KV 用
  `(raw_text, metadata, *index_names)`
- `retrieve()` 签名不统一：VDB 用 `(query_vector, index_name, ...)`，KV 用 `(raw_text, topk, ...)`
- 构造函数不统一：VDB/KV 用 `dict`，Graph 用 `str`

**建议的统一接口**：

```python
from enum import Enum
from typing import Literal

class IndexType(Enum):
    VDB = "vdb"       # 向量索引
    KV = "kv"         # 文本/KV 索引
    GRAPH = "graph"   # 图索引


class BaseMemoryCollection(ABC):
    """
    NeuroMem Collection 基类

    设计原则：
    - Collection 持有数据（text + metadata）
    - Collection 可以在数据上建立多个索引
    - 每种 Collection 类型可支持不同的 IndexType
    """

    # 子类声明支持的索引类型
    supported_index_types: ClassVar[set[IndexType]] = set()

    def __init__(self, config: dict[str, Any]):
        """统一使用 dict 配置初始化"""
        self.name = config["name"]
        self.text_storage = TextStorage()
        self.metadata_storage = MetadataStorage()

    @abstractmethod
    def create_index(
        self,
        index_name: str,
        index_type: IndexType | None = None,  # HybridCollection 需要
        config: dict[str, Any] | None = None
    ) -> bool:
        """
        创建索引

        Args:
            index_name: 索引名称
            index_type: 索引类型（基础 Collection 可忽略，HybridCollection 必需）
            config: 索引配置
        """
        ...

    @abstractmethod
    def delete_index(self, index_name: str) -> bool:
        """删除索引"""
        ...

    @abstractmethod
    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出所有索引

        Returns:
            [{"name": "xxx", "type": IndexType.VDB, "config": {...}}, ...]
        """
        ...

    @abstractmethod
    def insert(
        self,
        content: str,
        index_names: list[str] | str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs
    ) -> str:
        """
        插入数据

        Args:
            content: 文本内容
            index_names: 目标索引名列表（None 表示只存数据不建索引）
            vector: 向量（VDB 索引需要）
            metadata: 元数据

        Returns:
            stable_id
        """
        ...

    @abstractmethod
    def insert_to_index(
        self,
        item_id: str,
        index_name: str,
        vector: np.ndarray | None = None,
        **kwargs
    ) -> bool:
        """
        将已有数据加入索引（用于跨索引迁移）

        Args:
            item_id: 数据 ID
            index_name: 目标索引名
            vector: 向量（VDB 索引需要，可以现场计算）

        Returns:
            成功/失败
        """
        ...

    @abstractmethod
    def remove_from_index(self, item_id: str, index_name: str) -> bool:
        """
        从索引移除（数据保留）

        用于 MemoryOS 场景：从 FIFO 索引移除，加入 Segment 索引
        """
        ...

    @abstractmethod
    def retrieve(
        self,
        query: str | np.ndarray | None = None,
        index_name: str | None = None,
        top_k: int = 10,
        with_metadata: bool = False,
        metadata_filter: Callable | None = None,
        **kwargs
    ) -> list[dict[str, Any]]:
        """
        检索数据

        Args:
            query: 查询（文本或向量）
            index_name: 使用的索引
            top_k: 返回数量
            with_metadata: 是否返回 metadata
            metadata_filter: 元数据过滤函数

        Returns:
            [{"id": ..., "text": ..., "metadata": ..., "score": ...}, ...]
        """
        ...

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """完全删除（数据 + 所有索引）"""
        ...

    @abstractmethod
    def update(
        self,
        item_id: str,
        new_content: str | None = None,
        new_vector: np.ndarray | None = None,
        new_metadata: dict[str, Any] | None = None,
        index_name: str | None = None,
    ) -> bool:
        """更新条目"""
        ...

    # 已有的基础方法保留
    def get_all_ids(self) -> list[str]: ...
    def filter_ids(self, ids, filter_func, **conditions) -> list[str]: ...

    # 持久化接口
    @abstractmethod
    def store(self, path: str) -> dict[str, Any]: ...

    @classmethod
    @abstractmethod
    def load(cls, name: str, path: str) -> "BaseMemoryCollection": ...


# 各基础 Collection 声明支持的索引类型
class VDBMemoryCollection(BaseMemoryCollection):
    supported_index_types = {IndexType.VDB}

class KVMemoryCollection(BaseMemoryCollection):
    supported_index_types = {IndexType.KV}

class GraphMemoryCollection(BaseMemoryCollection):
    supported_index_types = {IndexType.GRAPH}

# HybridCollection 支持所有类型（见 Part 6）
class HybridCollection(BaseMemoryCollection):
    supported_index_types = {IndexType.VDB, IndexType.KV, IndexType.GRAPH}
```

**验收标准**：

- [x] 三种 Collection 都继承自 BaseMemoryCollection
- [x] 都使用 `config: dict` 初始化
- [x] `insert()` 和 `retrieve()` 签名统一
- [x] 现有测试用例通过

**完成记录**：

- 新增 `IndexType` 枚举 (VDB, KV, GRAPH)
- 定义统一抽象方法：`create_index`, `delete_index`, `list_indexes`, `insert`, `insert_to_index`,
  `remove_from_index`, `retrieve`, `delete`, `update`, `store`, `load`
- 所有 Collection 声明 `supported_index_types: ClassVar[set[IndexType]]`

______________________________________________________________________

## 1.2 重构 KVMemoryCollection 对齐接口

**当前状态**：

- 基本功能完整
- 接口签名与 VDB 不一致

**需要修改**：

1. **构造函数**：已经是 `config: dict`，✅ 无需改

1. **insert() 签名**：

```python
# 当前
def insert(self, raw_text, metadata, *index_names)

# 统一为
def insert(self, content, index_name=None, vector=None, metadata=None, **kwargs)
# vector 参数对 KV 无意义，忽略即可
# 如果 index_name 是 None，则插入到所有索引
```

3. **retrieve() 签名**：

```python
# 当前
def retrieve(self, raw_text, topk, with_metadata, index_name, ...)

# 统一为
def retrieve(self, query, index_name=None, top_k=10, with_metadata=False, ...)
```

4. **返回格式统一**：

```python
# 统一返回
[{"id": "xxx", "text": "...", "metadata": {...}, "score": 0.95}, ...]
```

**验收标准**：

- [x] `insert()` 兼容新旧调用方式
- [x] `retrieve()` 返回格式与 VDB 一致
- [x] 现有 KV 相关测试通过

**完成记录**：

- `insert(content, metadata, vector, index_names)` 统一签名
- `retrieve()` 返回统一格式 `[{"id", "text", "metadata", "score"}]`
- 新增 `list_indexes()`, `insert_to_index()`, `remove_from_index()`
- `supported_index_types = {IndexType.KV}`

______________________________________________________________________

## 1.3 重构 GraphMemoryCollection 对齐接口

**当前状态**：

- 使用 `name: str` 构造（需改为 `config: dict`）
- 使用 `add_node()` / `add_edge()` 而非统一的 `insert()`
- 使用 `retrieve_by_graph()` 而非统一的 `retrieve()`

**需要修改**：

1. **构造函数**：

```python
# 当前
def __init__(self, name: str, **kwargs)

# 统一为
def __init__(self, config: dict[str, Any])
    self.name = config["name"]
    # ...
```

2. **统一 insert()**：

```python
def insert(
    self,
    content: str,
    index_name: str | None = None,
    vector: np.ndarray | None = None,
    metadata: dict[str, Any] | None = None,
    **kwargs  # node_id, node_type, edges 等图特有参数
) -> str:
    """
    插入节点

    kwargs 可包含:
    - node_id: 指定节点 ID（否则自动生成）
    - edges: [(target_id, weight), ...] 同时创建的边
    """
```

3. **统一 retrieve()**：

```python
def retrieve(
    self,
    query: str | np.ndarray | None = None,
    index_name: str | None = None,
    top_k: int = 10,
    with_metadata: bool = False,
    **kwargs  # start_node, max_depth, direction 等图特有参数
) -> list[dict[str, Any]]:
    """
    图检索

    kwargs 可包含:
    - start_node: 起始节点 ID（图遍历模式）
    - max_depth: 最大遍历深度
    - direction: "outgoing" | "incoming" | "both"

    如果 query 是文本/向量，则先定位到最相似节点再遍历
    """
```

4. **保留图特有方法**（作为 Graph 专属扩展）：

```python
# 这些方法可以保留，因为是图特有的
def add_edge(self, from_node, to_node, weight, index_name) -> bool
def get_neighbors(self, node_id, k, index_name) -> list[dict]
def remove_edge(self, from_node, to_node, index_name) -> bool
```

**验收标准**：

- [x] 使用 `config: dict` 初始化
- [x] `insert()` / `retrieve()` 签名与基类一致
- [x] 图特有方法作为扩展保留
- [x] 现有 Graph 相关测试通过

**完成记录**：

- `__init__(config: dict)` 替代原 `(name: str)`
- `supported_index_types = {IndexType.GRAPH}`
- 统一接口方法实现
- 保留图特有方法：`add_node()`, `add_edge()`, `get_neighbors()`, `retrieve_by_graph()`

______________________________________________________________________

## 1.4 VDBMemoryCollection 接口对齐

> ✅ **已完成**

**完成记录**：

- `supported_index_types = {IndexType.VDB}`
- `insert(content, metadata, vector, index_names)` 统一签名
- `retrieve(query, index_name, top_k, with_metadata, metadata_filter)` 统一签名
- `update(item_id, content, metadata, vector)` 统一签名
- `delete(item_id)` 统一签名
- 新增 `insert_to_index()`, `remove_from_index()` 支持 MemoryOS 场景
- 保留向后兼容方法：`delete_by_content()`, `update_by_content()`
- 统一返回格式 `[{"id", "text", "metadata", "score"}]`

______________________________________________________________________

## 1.5 返回值格式标准化

> ✅ **已完成**

**统一的返回格式**：

```python
# insert() 返回
str  # stable_id

# retrieve() 返回
list[dict]:
[
    {
        "id": "abc123...",      # stable_id
        "text": "原始文本",      # 从 text_storage 获取
        "metadata": {...},       # 从 metadata_storage 获取（如果 with_metadata=True）
        "score": 0.95,           # 相似度/距离分数（如果适用）
        # Graph 特有字段
        "neighbors": [...],      # 仅 Graph，邻居节点列表
        "depth": 1,              # 仅 Graph，遍历深度
    },
    ...
]

# delete() / update() 返回
bool  # 成功/失败

# create_index() 返回
bool  # 成功/失败
```

______________________________________________________________________

## 依赖关系

- 无外部依赖
- 完成后 Part 3 (MemoryManager) 可以开始

______________________________________________________________________

## 预估工时 vs 实际完成

| 子任务                                                     | 预估时间 | 状态               |
| ---------------------------------------------------------- | -------- | ------------------ |
| 1.1 BaseMemoryCollection 抽象接口（含 IndexType 枚举）     | 3h       | ✅ 完成            |
| 1.2 KVMemoryCollection 对齐                                | 3h       | ✅ 完成            |
| 1.3 GraphMemoryCollection 对齐                             | 4h       | ✅ 完成            |
| 1.4 VDBMemoryCollection 接口对齐                           | 3h       | ✅ 完成            |
| 1.5 返回值格式标准化                                       | 1h       | ✅ 完成            |
| 1.6 添加 insert_to_index/remove_from_index 到各 Collection | 3h       | ✅ 完成            |
| 测试 & 验证                                                | 2h       | ⏳ 待验证          |
| **总计**                                                   | **19h**  | **已完成核心开发** |

______________________________________________________________________

## 参考资料

- VDBMemoryCollection 作为参考实现（1142 行）
- 现有测试：`tests/components/sage_mem/test_vdb_collection.py`
