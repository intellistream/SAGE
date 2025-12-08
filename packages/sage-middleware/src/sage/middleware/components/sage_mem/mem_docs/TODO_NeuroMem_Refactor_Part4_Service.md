# TODO Part 4: Service 层适配

## ✅ 完成状态 (2024-12-02)

**所有任务已完成**

| 任务                               | 状态 | 说明                                                    |
| ---------------------------------- | ---- | ------------------------------------------------------- |
| 4.1 移除类型检查                   | ✅   | 所有 Service 已移除 isinstance(\*, VDBMemoryCollection) |
| 4.2 GraphMemoryService 适配        | ✅   | 添加 ppr_retrieve, get_neighbors 方法                   |
| 4.3 HierarchicalMemoryService 适配 | ✅   | 重写为单 HybridCollection + tier-based index            |
| 4.4 HybridMemoryService 适配       | ✅   | 重写为单 HybridCollection + multi-index                 |
| 4.5 清理冗余代码                   | ✅   | 统一返回格式，移除重复代码                              |

**核心设计原则**：

- Service : Collection = 1:1
- Collection = 一份数据 + 多种类型索引（不是组合多个 Collection）

**修改的文件**：

- `memory_manager.py` - 添加 HybridCollection 注册
- `hybrid_memory_service.py` - 完全重写，使用单 HybridCollection
- `hierarchical_memory_service.py` - 完全重写，tier 作为 index 名称
- `graph_memory_service.py` - 移除 isinstance，添加 PPR
- `key_value_memory_service.py` - 移除 isinstance
- `short_term_memory_service.py` - 移除 isinstance
- `vector_hash_memory_service.py` - 移除 isinstance
- `neuromem_vdb_service.py` - 移除 isinstance

______________________________________________________________________

## 背景

Service 层是面向上层应用的接口，使用 NeuroMem (MemoryManager + Collection) 作为底层存储。

```
Service 层
├── ShortTermMemoryService      # 滑动窗口
├── VectorHashMemoryService     # 三元组 + LSH
├── KeyValueMemoryService       # 文本检索
├── GraphMemoryService          # 图记忆
├── HierarchicalMemoryService   # 分层记忆
├── HybridMemoryService         # 混合检索
├── NeuroMemVDBService          # VDB 封装
└── ParallelVDBService          # 并行 VDB
```

**统一接口**（定义在 `sage.platform.service.BaseService`）：

```python
def insert(
    self,
    entry: str,
    vector: np.ndarray | None = None,
    metadata: dict | None = None,
    *,
    insert_mode: Literal["active", "passive"] = "passive",
    insert_params: dict | None = None,
) -> str

def retrieve(
    self,
    query: str | None = None,
    vector: np.ndarray | None = None,
    metadata: dict | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]
```

______________________________________________________________________

## 任务概述

本任务负责适配 Service 层，使其能够正确调用重构后的 NeuroMem。

**涉及文件**：

- `services/short_term_memory_service.py`
- `services/vector_hash_memory_service.py`
- `services/key_value_memory_service.py`
- `services/graph_memory_service.py`
- `services/hierarchical_memory_service.py`
- `services/hybrid_memory_service.py`
- `services/neuromem_vdb_service.py`

______________________________________________________________________

## 4.1 移除类型检查，使用多态

**当前问题**：

```python
# 当前代码 - 需要检查具体类型
if isinstance(self.collection, VDBMemoryCollection):
    self.collection.insert(index_name=..., raw_data=..., vector=...)
elif isinstance(self.collection, GraphMemoryCollection):
    self.collection.add_node(...)
```

**改进**（Part 1 完成后可实现）：

```python
# 改进后 - 直接多态调用
result = self.collection.insert(
    content=entry,
    index_name=self.default_index,
    vector=vector,
    metadata=metadata
)
```

**需要修改的 Service**：

- [x] `GraphMemoryService` - 目前使用 `add_node()` / `add_edge()` ✅ 已完成
- [x] `HierarchicalMemoryService` - 需要适配多个 Collection ✅ 已重写为单 HybridCollection
- [x] `HybridMemoryService` - 使用多种类型 Collection ✅ 已重写为单 HybridCollection

**验收标准**：

- [x] 所有 Service 不再使用 `isinstance()` 检查 ✅ 已完成
- [x] 统一使用 `collection.insert()` / `collection.retrieve()` ✅ 已完成

______________________________________________________________________

## 4.2 适配 GraphMemoryService

**当前接口**：

```python
class GraphMemoryService(BaseService):
    def insert(self, entry, vector, metadata, ...):
        # 调用 collection.add_node()
        node_id = self.collection.add_node(...)

        # 处理边
        if metadata and "edges" in metadata:
            for target_id in metadata["edges"]:
                self.collection.add_edge(...)
```

**适配后**：

```python
class GraphMemoryService(BaseService):
    def insert(self, entry, vector, metadata, ...):
        # 统一调用（Graph 特有参数放 kwargs）
        node_id = self.collection.insert(
            content=entry,
            index_name=self.index_name,
            vector=vector,
            metadata=metadata,
            # Graph 特有参数
            edges=metadata.get("edges") if metadata else None
        )
        return node_id

    def retrieve(self, query, vector, metadata, top_k):
        # 可以使用图遍历或向量检索
        if metadata and "start_node" in metadata:
            # 图遍历模式
            return self.collection.retrieve(
                query=None,
                index_name=self.index_name,
                top_k=top_k,
                start_node=metadata["start_node"],
                max_depth=metadata.get("max_depth", 2)
            )
        else:
            # 向量检索模式（先找相似节点，再遍历）
            return self.collection.retrieve(
                query=vector,  # 向量查询
                index_name=self.index_name,
                top_k=top_k
            )
```

**新增图特有方法**（作为 Service 扩展）：

```python
def add_edge(self, from_node: str, to_node: str, weight: float = 1.0) -> bool:
    """添加边 - 委托给 Collection"""
    return self.collection.add_edge(from_node, to_node, weight, self.index_name)

def get_neighbors(self, node_id: str, k: int = 10) -> list[dict]:
    """获取邻居 - 委托给 Collection"""
    return self.collection.get_neighbors(node_id, k, self.index_name)

def ppr_retrieve(
    self,
    seed_nodes: list[str],
    alpha: float = 0.15,
    top_k: int = 10
) -> list[dict]:
    """PPR 检索 - 用于 HippoRAG"""
    if not hasattr(self.collection, 'ppr'):
        raise NotImplementedError("Collection doesn't support PPR")

    # 获取 graph index
    graph_index = self.collection.indexes.get(self.index_name)
    if not graph_index:
        return []

    # 执行 PPR
    ppr_results = graph_index.ppr(seed_nodes, alpha=alpha, top_k=top_k)

    # 组装返回结果
    return [
        {
            "id": node_id,
            "text": self.collection.text_storage.get(node_id),
            "metadata": self.collection.metadata_storage.get(node_id),
            "score": score
        }
        for node_id, score in ppr_results
    ]
```

**验收标准**：

- [x] `insert()` / `retrieve()` 使用统一接口 ✅ 已完成
- [x] 图特有方法作为扩展保留 ✅ add_edge, get_neighbors, ppr_retrieve
- [x] PPR 检索可用 ✅ 已实现

______________________________________________________________________

## 4.3 适配 HierarchicalMemoryService

**当前结构**：

```python
class HierarchicalMemoryService(BaseService):
    tier_collections: dict[str, VDBMemoryCollection]  # 每层一个 Collection
```

**需要适配**：

1. **使用统一的 insert/retrieve**：

```python
def insert(self, entry, vector, metadata, ...):
    # 确定目标层级
    target_tier = self._get_target_tier(insert_params)
    collection = self.tier_collections[target_tier]

    # 统一调用
    item_id = collection.insert(
        content=entry,
        index_name="global_index",
        vector=vector,
        metadata={
            **(metadata or {}),
            "tier": target_tier,
            "insert_time": time.time()
        }
    )

    # 检查溢出迁移
    self._check_overflow(target_tier)

    return item_id
```

2. **迁移逻辑保持不变**：

```python
def _migrate(self, from_tier: str, to_tier: str, item_id: str):
    """层间迁移"""
    from_collection = self.tier_collections[from_tier]
    to_collection = self.tier_collections[to_tier]

    # 获取数据
    items = from_collection.retrieve(
        query=None,
        index_name="global_index",
        top_k=1,
        metadata_filter=lambda m: m.get("id") == item_id
    )

    if not items:
        return False

    item = items[0]

    # 插入目标层
    to_collection.insert(
        content=item["text"],
        index_name="global_index",
        vector=item.get("vector"),
        metadata={**item["metadata"], "tier": to_tier}
    )

    # 从源层删除
    from_collection.delete(item_id)

    return True
```

**验收标准**：

- [x] 多层 Collection 正确管理 ✅ 改为单 HybridCollection + tier-based index
- [x] 迁移逻辑正常工作 ✅ 使用 remove_from_index + insert_to_index
- [x] 溢出检测正常 ✅ 保留原有逻辑

______________________________________________________________________

## 4.4 适配 HybridMemoryService

**当前结构**：

```python
class HybridMemoryService(BaseService):
    # 使用多种类型的 Collection
    vdb_collection: VDBMemoryCollection  # 向量检索
    kv_collection: KVMemoryCollection    # 文本检索
```

**需要适配**：

```python
def insert(self, entry, vector, metadata, ...):
    """同时插入到多个 Collection"""
    # VDB
    vdb_id = self.vdb_collection.insert(
        content=entry,
        index_name=self.vdb_index_name,
        vector=vector,
        metadata=metadata
    )

    # KV（不需要 vector）
    kv_id = self.kv_collection.insert(
        content=entry,
        index_name=self.kv_index_name,
        metadata=metadata
    )

    return vdb_id  # 返回主键

def retrieve(self, query, vector, metadata, top_k):
    """混合检索 + 融合"""
    # 向量检索
    vdb_results = self.vdb_collection.retrieve(
        query=vector,
        index_name=self.vdb_index_name,
        top_k=top_k * 2  # 取更多用于融合
    )

    # 文本检索
    kv_results = self.kv_collection.retrieve(
        query=query,  # 文本查询
        index_name=self.kv_index_name,
        top_k=top_k * 2
    )

    # 融合
    return self._fuse_results(vdb_results, kv_results, top_k)

def _fuse_results(self, vdb_results, kv_results, top_k):
    """RRF 融合"""
    from collections import defaultdict

    scores = defaultdict(float)
    k = 60  # RRF 参数

    for rank, item in enumerate(vdb_results):
        scores[item["id"]] += 1 / (k + rank + 1)

    for rank, item in enumerate(kv_results):
        scores[item["id"]] += 1 / (k + rank + 1)

    # 按融合分数排序
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # 组装结果
    result_map = {r["id"]: r for r in vdb_results + kv_results}
    return [result_map[id_] for id_ in sorted_ids[:top_k] if id_ in result_map]
```

**验收标准**：

- [x] 多路检索正常 ✅ 使用 retrieve_multi
- [x] 融合逻辑正确 ✅ 支持 rrf, weighted, union
- [x] 返回格式统一 ✅ 统一 MemoryItem dict 格式

______________________________________________________________________

## 4.5 清理冗余代码 ✅ 已完成

完成以上适配后，清理：

1. **移除 `isinstance()` 检查** ✅ 所有 Service 已清理
1. **统一返回格式处理** ✅ 使用 MemoryItem dict
1. **移除重复的向量归一化代码**（应在 Collection 层处理） ✅
1. **统一错误处理** ✅

______________________________________________________________________

## 依赖关系

- 依赖 Part 1（Collection 接口统一）
- 依赖 Part 2（PPR 等索引功能）
- 依赖 Part 3（MemoryManager 优化）

______________________________________________________________________

## 预估工时

| 子任务                             | 预估时间 |
| ---------------------------------- | -------- |
| 4.1 移除类型检查                   | 2h       |
| 4.2 GraphMemoryService 适配        | 3h       |
| 4.3 HierarchicalMemoryService 适配 | 2h       |
| 4.4 HybridMemoryService 适配       | 2h       |
| 4.5 清理冗余代码                   | 1h       |
| 测试 & 验证                        | 2h       |
| **总计**                           | **12h**  |

______________________________________________________________________

## 参考资料

- 现有 Service 实现
- `sage.platform.service.BaseService` 接口定义
