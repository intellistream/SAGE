# NeuroMem 重构任务总览

## 核心设计原则

### ⭐ Service : Collection = 1 : 1

```
Service 决定策略（如何插入、删除、检索）
Collection 提供能力（数据存储 + 多索引）
```

- 一个 Service 只持有一个 Collection
- 如果需要多层/混合能力，使用 **组合型 Collection**（HierarchicalCollection / HybridCollection）

### Collection 持有数据 + 多索引

```
Collection = 数据存储 (text_storage + metadata_storage) + 多个索引 (indexes)
```

______________________________________________________________________

## 项目背景

NeuroMem 是 SAGE Memory Pipeline 的底层记忆数据结构。

当前只有 `VDBMemoryCollection` 完成度较高（1142 行），其他 Collection 需要对齐接口。

______________________________________________________________________

## 任务拆分

| Part       | 任务                                 | 预估工时 | 依赖        | 优先级 | 状态    |
| ---------- | ------------------------------------ | -------- | ----------- | ------ | ------- |
| **Part 1** | Collection 层接口统一                | 19h      | 无          | P0     | ✅ 完成 |
| **Part 2** | 索引层 (Search Engine) 重构          | 13h      | 无          | P0     | ✅ 完成 |
| **Part 3** | MemoryManager 优化                   | 8h       | Part 1      | P1     | ✅ 完成 |
| **Part 4** | Service 层适配                       | 12h      | Part 1-3, 6 | P1     | ✅ 完成 |
| **Part 5** | 论文特性支持                         | 22h      | Part 1-4    | P2     | ✅ 完成 |
| **Part 6** | 组合型 Collection (HybridCollection) | 18h      | Part 1-2    | P0     | ✅ 完成 |

**总预估工时**：92h（约 11-12 人天）

### 进度总结

- ✅ **Part 1 & Part 2 已完成** (2024-12)
- ✅ **Part 6 已完成** (2024-12) - HybridCollection 实现
- ✅ **Part 3 已完成** (2024-12) - MemoryManager 注册表 + 工厂模式
- ✅ **Part 4 已完成** (2024-12) - Service 层适配，移除 isinstance 检查
- ✅ **Part 5 已完成** (2024-12) - 论文特性支持（TiM/A-Mem/MemoryBank/MemoryOS/SCM/Mem0）

______________________________________________________________________

## 依赖关系图

```
Part 1 (Collection) ──┬──> Part 3 (Manager) ──┐
                      │                        │
Part 2 (SearchEngine)─┼──> Part 6 (Composite) ─┼──> Part 4 (Service) ──> Part 5 (Features)
                      │                        │
                      └────────────────────────┘
```

- Part 1 和 Part 2 可以并行开发
- Part 6 依赖 Part 1-2（组合型 Collection 需要基础 Collection）
- Part 3 依赖 Part 1
- Part 4 依赖 Part 1-3 + Part 6（Service 需要所有 Collection 就绪）
- Part 5 依赖所有

______________________________________________________________________

## 核心设计原则

### 1. Service : Collection = 1 : 1

```python
# ✅ 正确
class SomeService(BaseService):
    collection: SomeCollection  # 只有一个

# ❌ 错误
class SomeService(BaseService):
    collection_a: VDBCollection
    collection_b: KVCollection   # 不应持有多个
```

### 2. Collection = 一份数据 + 多个索引

```python
class HybridCollection(BaseMemoryCollection):
    # 数据只存一份
    text_storage = TextStorage()
    metadata_storage = MetadataStorage()

    # 多种类型的索引（在同一份数据上）
    vdb_indexes: dict[str, BaseVDBIndex]     # 向量索引
    kv_indexes: dict[str, BaseKVIndex]       # 文本索引 (BM25, FIFO, 排序)
    graph_indexes: dict[str, BaseGraphIndex] # 图索引
```

### 3. 索引可以独立增删

```python
# 插入数据到多个索引
collection.insert(content, index_names=["fifo", "segment_vdb"])

# 从某个索引移除（数据保留）
collection.remove_from_index(item_id, "fifo")

# 将已有数据加到新索引
collection.insert_to_index(item_id, "segment_vdb", vector=vec)

# 完全删除（数据 + 所有索引）
collection.delete(item_id)
```

### 4. MemoryOS 示例

```
数据流：
1. insert → 存数据 + 加入 FIFO 索引
2. FIFO 满 → Service 决定迁移：
   - remove_from_index("fifo")
   - insert_to_index("segment_vdb")
3. 检索 → 先查 FIFO，再查 VDB
```

______________________________________________________________________

## 文件结构

```
neuromem/
├── memory_collection/
│   ├── base_collection.py         # 统一抽象接口
│   ├── vdb_collection.py          # 向量 Collection
│   ├── kv_collection.py           # 文本 Collection
│   ├── graph_collection.py        # 图 Collection
│   ├── hierarchical_collection.py # 分层 Collection (新增)
│   └── hybrid_collection.py       # 混合 Collection (新增)
├── search_engine/
│   ├── vdb_index/                 # 向量索引 (FAISS)
│   ├── kv_index/                  # 文本索引 (BM25)
│   ├── graph_index/               # 图索引 (邻接表)
│   └── index_factory.py           # 统一工厂
├── storage_engine/
│   ├── text_storage.py            # 文本存储
│   ├── metadata_storage.py        # 元数据存储
│   └── kv_backend/                # 存储后端
└── memory_manager.py              # Collection 管理器
```

______________________________________________________________________

## 各 Part 详细文档

1. [Part 1: Collection 层重构](./TODO_NeuroMem_Refactor_Part1_Collection.md)
1. [Part 2: 索引层重构](./TODO_NeuroMem_Refactor_Part2_SearchEngine.md)
1. [Part 3: MemoryManager 重构](./TODO_NeuroMem_Refactor_Part3_MemoryManager.md)
1. [Part 4: Service 层适配](./TODO_NeuroMem_Refactor_Part4_Service.md)
1. [Part 5: 论文特性支持](./TODO_NeuroMem_Refactor_Part5_PaperFeatures.md)
1. [Part 6: 组合型 Collection](./TODO_NeuroMem_Refactor_Part6_CompositeCollection.md)

______________________________________________________________________

## 验收标准

### 代码质量

- [x] 所有 Collection 接口统一 ✅ Part 1 完成
- [x] 无 `isinstance()` 类型检查 ✅ Part 4 完成
- [x] 持久化路径统一 ✅ Part 3 完成
- [ ] 测试覆盖率 > 80%

### 功能完整

- [x] VDB/KV/Graph 三种 Collection 可用 ✅ Part 1 完成
- [x] 支持 PPR 图检索 ✅ Part 2 完成
- [x] 支持论文核心特性（遗忘、热度、冲突检测等） ✅ Part 5 完成

### 性能要求

- [ ] 100 万条记忆，检索 < 100ms
- [ ] 持久化/加载 < 5s

______________________________________________________________________

## 联系人

- 架构设计：[待填写]
- 代码 Review：[待填写]
