# SAGE Memory Pipeline 开发档案

> 本档案汇总 SAGE 记忆系统的完整设计与实现，包括：
>
> - Pipeline 算子层规范化重构（R1-R6）
> - NeuroMem 底层引擎重构（Part 1-6）
> - 论文特性映射矩阵
> - 论文复现优先级与 Action 配置
>
> 更新时间：2025-12-11

______________________________________________________________________

## 一、整体架构概览

### 1.1 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline 算子层 (sage-benchmark/libs)                          │
│  ├── PreInsert        → 写入前预处理（只能检索）                  │
│  ├── MemoryInsert     → 执行插入（支持多种插入方法）              │
│  ├── PostInsert       → 写入后优化（一次 检索→删除→插入）         │
│  ├── PreRetrieval     → 检索前预处理（不访问存储）                │
│  ├── MemoryRetrieval  → 执行检索                                 │
│  └── PostRetrieval    → 检索后处理（可多次查询）                  │
├─────────────────────────────────────────────────────────────────┤
│  MemoryService 服务层 (sage-middleware/services)                 │
│  ├── ShortTermMemoryService     → 会话短期记忆                   │
│  ├── KeyValueMemoryService      → 精确/模糊键值检索               │
│  ├── GraphMemoryService         → 知识图谱存储                   │
│  ├── HierarchicalMemoryService  → 分层记忆（STM/MTM/LTM）         │
│  ├── HybridMemoryService        → 多索引融合检索                  │
│  ├── VectorHashMemoryService    → 哈希桶近似检索                  │
│  └── NeuroMemVDBService         → 通用向量数据库服务               │
├─────────────────────────────────────────────────────────────────┤
│  NeuroMem 引擎层 (sage-middleware/neuromem)                      │
│  ├── MemoryManager              → Collection 统一管理器           │
│  ├── MemoryCollection 家族                                       │
│  │   ├── VDBMemoryCollection    → 向量集合                       │
│  │   ├── KVMemoryCollection     → 键值集合                       │
│  │   ├── GraphMemoryCollection  → 图集合                         │
│  │   └── HybridCollection       → 混合集合（一份数据+多种索引）    │
│  └── SearchEngine 索引层                                         │
│      ├── vdb_index/             → 向量索引 (FAISS)               │
│      ├── kv_index/              → 文本索引 (BM25S)               │
│      └── graph_index/           → 图索引 (邻接表+PPR)            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

#### ⭐ Service : Collection = 1 : 1

```python
# ✅ 正确：一个 Service 只持有一个 Collection
class SomeService(BaseService):
    collection: SomeCollection

# ❌ 错误：不应持有多个 Collection
class SomeService(BaseService):
    collection_a: VDBCollection
    collection_b: KVCollection
```

#### ⭐ Collection = 一份数据 + 多种索引

```python
class HybridCollection(BaseMemoryCollection):
    # 数据只存一份
    text_storage = TextStorage()
    metadata_storage = MetadataStorage()

    # 多种类型的索引（在同一份数据上）
    vdb_indexes: dict[str, BaseVDBIndex]     # 向量索引
    kv_indexes: dict[str, BaseKVIndex]       # 文本索引
    graph_indexes: dict[str, BaseGraphIndex] # 图索引
```

#### ⭐ 索引可以独立增删

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

### 1.3 操作约束

| 阶段            | 检索    | 插入    | 删除    | 说明                   |
| --------------- | ------- | ------- | ------- | ---------------------- |
| PreInsert       | ✅ 可选 | ❌      | ❌      | 预处理，决定插入方式   |
| MemoryInsert    | ❌      | ✅      | ❌      | 执行插入               |
| PostInsert      | ✅ 一次 | ✅ 一次 | ✅ 一次 | 检索→删除→插入（蒸馏） |
| PreRetrieval    | ❌      | ❌      | ❌      | 不访问存储             |
| MemoryRetrieval | ✅      | ❌      | ❌      | 执行检索               |
| PostRetrieval   | ✅ 多次 | ❌      | ❌      | 结果处理，可多次查询   |

______________________________________________________________________

## 二、Pipeline 算子层规范化重构（R1-R6）

> **状态：✅ 全部完成 (2025-12-11)**
>
> 代码位置：`sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/`

### 2.1 R1: MemoryService 统一接口规范

**目标**：统一所有 MemoryService 的接口签名，消除 `isinstance()` 检查

**统一接口**：

```python
class BaseMemoryService:
    def insert(
        self,
        entry: str,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """
        统一插入接口

        Args:
            entry: 记忆文本内容
            vector: 可选的预计算向量
            metadata: 元数据（timestamp, source, importance, tier 等）
            insert_mode: active=主动学习, passive=被动存储
            insert_params: 扩展参数（target_tier, priority 等）

        Returns:
            entry_id: 插入后的唯一标识符
        """
        ...

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        统一检索接口

        Args:
            query: 查询文本
            vector: 可选的预计算查询向量
            metadata: 过滤条件
            top_k: 返回数量

        Returns:
            结果列表，每项包含 {id, content, score, metadata}
        """
        ...

    def delete(self, entry_id: str) -> bool:
        """删除指定记忆"""
        ...

    def optimize(
        self,
        trigger: str,
        config: dict | None = None,
        entries: list[dict] | None = None,
    ) -> dict:
        """
        统一优化接口（供 PostInsert 调用）

        Args:
            trigger: 触发类型（reflection/link_evolution/forgetting/summarize/migrate）
            config: 优化配置
            entries: 相关记忆条目

        Returns:
            优化结果
        """
        ...

    def get_status(self) -> dict:
        """
        查询服务状态（供 PostInsert 查询待处理项）

        Returns:
            Dict: {
                "pending_action": str | None,  # 待处理动作类型
                "pending_items": List[Dict],   # 待处理条目
                ...其他服务特定字段
            }

        说明：
            - insert() 内部自动检测溢出/冲突等，更新内部状态
            - PostInsert 通过 get_status() 查询状态
            - 根据状态调用 LLM 决策后，再次调用 insert() 执行主动插入
        """
        return {"pending_action": None, "pending_items": []}
```

**各服务特化扩展**：

| 服务                      | 特化方法                            | 说明             |
| ------------------------- | ----------------------------------- | ---------------- |
| GraphMemoryService        | `ppr_retrieve()`, `get_neighbors()` | PPR 检索、图邻居 |
| HierarchicalMemoryService | `get_tier_stats()`, `migrate()`     | 层级统计、迁移   |
| HybridMemoryService       | `multi_index_retrieve()`            | 多索引融合检索   |
| KeyValueMemoryService     | `get_by_key()`, `fuzzy_search()`    | 精确/模糊查询    |

**各服务的 get_status() 状态字段**：

| 服务                      | pending_action       | 特有字段                         | 触发场景           |
| ------------------------- | -------------------- | -------------------------------- | ------------------ |
| HierarchicalMemoryService | "migrate" / "forget" | source_tier, target_tier         | 容量溢出/遗忘触发  |
| HybridMemoryService       | "crud"               | pending_similar                  | 新事实与旧事实冲突 |
| GraphMemoryService        | "link" / "synonym"   | pending_node, pending_candidates | 新节点需建立链接   |

### 2.2 R2: PreInsert 算子重构 ✅

**完成时间**：2025-12-11

**核心改动**：

- 只保留大类方法（action 级别）
- 小类逻辑内联到大类方法
- 传递 `insert_method` 给 MemoryInsert

**支持的 Action**：

| Action      | 说明                        | 输出的 insert_method          |
| ----------- | --------------------------- | ----------------------------- |
| none        | 透传                        | default                       |
| tri_embed   | 三元组抽取 + 向量化         | triple_insert                 |
| transform   | 分块/分段/事实抽取/摘要     | chunk_insert / summary_insert |
| extract     | 关键词/实体/Persona 抽取    | default                       |
| score       | 重要性/情绪评分             | priority_insert               |
| multi_embed | 多路 embedding              | multi_index_insert            |
| validate    | 合法性检查                  | default                       |
| scm_embed   | SCM 样式摘要+原文+embedding | default                       |

**数据流示例**：

```python
# PreInsert 输出
data["memory_entries"] = [
    {
        "content": "processed text",
        "embedding": [...],
        "metadata": {"importance": 0.85},
        "insert_method": "priority_insert",  # 告诉 MemoryInsert 用什么方法
        "insert_params": {"target_tier": "mtm"},
    }
]
```

### 2.3 R3: PostInsert 算子重构 ✅

**完成时间**：2025-12-11

**核心改动**：

- 算子级操作：none, log, stats, distillation, mem0_crud
- 服务级操作：委托给 `service.optimize()`
- distillation 严格遵循"一次 检索→删除→插入"

**Action 分类**：

| 类型   | Action         | 说明                                     |
| ------ | -------------- | ---------------------------------------- |
| 算子级 | none           | 透传                                     |
| 算子级 | log            | 记录日志                                 |
| 算子级 | stats          | 统计插入数据                             |
| 算子级 | distillation   | 检索→删除→插入（一次循环）               |
| 算子级 | mem0_crud      | Mem0 CRUD 决策（ADD/UPDATE/DELETE/NOOP） |
| 服务级 | reflection     | 高阶反思生成                             |
| 服务级 | link_evolution | 链接演化                                 |
| 服务级 | forgetting     | 遗忘（Ebbinghaus/LRU/LFU/Heat）          |
| 服务级 | summarize      | 摘要（单层/分层/增量）                   |
| 服务级 | migrate        | 层间迁移（STM→MTM→LTM）                  |

**服务级调用示例**：

```python
def _trigger_service_optimize(self, data):
    result = self.call_service(
        self.service_name,
        method="optimize",
        params={
            "trigger": self.action,  # e.g. "link_evolution"
            "entries": data.get("memory_entries", []),
            "config": self._action_config,
        },
    )
```

### 2.4 R4: PreRetrieval 算子重构 ✅

**完成时间**：2025-12-11

**核心改动**：

- 只保留大类方法
- **严格不访问记忆数据结构**
- 输出 `retrieval_hints` 而非指定服务

**支持的 Action**：

| Action      | 说明                              |
| ----------- | --------------------------------- |
| none        | 透传                              |
| embedding   | 基础向量化                        |
| optimize    | 关键词提取/查询扩展/改写/指令增强 |
| multi_embed | 多路查询 embedding                |
| decompose   | 复杂查询分解                      |
| route       | 检索策略路由（输出 hints）        |
| validate    | 查询长度/语言/安全检查            |
| scm_gate    | SCM 记忆激活判断（是否需要检索）  |

**route 输出 hints 示例**：

```python
data["retrieval_hints"] = {
    "strategies": ["semantic", "temporal"],
    "route_strategy": "keyword",
    "params": {"time_decay": 0.95}
}
```

### 2.5 R5: PostRetrieval 算子重构 ✅

**完成时间**：2025-12-11

**核心改动**：

- 只保留大类方法
- **不自己计算 embedding**
- 允许多次查询服务

**支持的 Action**：

| Action        | 说明                                          |
| ------------- | --------------------------------------------- |
| none          | 基础格式化                                    |
| rerank        | 重排序（semantic/time_weighted/ppr/weighted） |
| filter        | 过滤（token_budget/threshold/top_k）          |
| merge         | 多次查询合并（link_expand/multi_query）       |
| augment       | 补充上下文（persona/traits/events）           |
| compress      | 压缩/摘要                                     |
| format        | 格式化输出（template/structured/chat/xml）    |
| scm_three_way | SCM 三元决策（drop/summary/raw）              |

### 2.6 R6: MemoryInsert 插入方法扩展 ✅

**完成时间**：2025-12-11

**核心改动**：

- 支持 `insert_method` 参数
- 根据 `insert_mode` 和 `insert_params` 调用服务

**插入方法映射**：

| insert_method      | 说明       | 特殊处理                       |
| ------------------ | ---------- | ------------------------------ |
| default            | 默认插入   | -                              |
| triple_insert      | 三元组插入 | 添加 triples 到 metadata       |
| chunk_insert       | 分块插入   | 添加 chunk_index/total_chunks  |
| summary_insert     | 摘要插入   | 设置 target_tier=ltm           |
| priority_insert    | 优先级插入 | 根据 importance 决定层级       |
| multi_index_insert | 多索引插入 | 添加 vectors 和 target_indexes |

______________________________________________________________________

## 三、NeuroMem 引擎层重构（Part 1-6）

> **状态：✅ 全部完成 (2024-12)** **总工时：92h（约 11-12 人天）**
>
> 代码位置：`sage-middleware/src/sage/middleware/components/sage_mem/mem_docs/`

### 3.1 Part 1: Collection 层接口统一 ✅

**工时**：19h | **完成时间**：2024-12

**核心成果**：

- 新增 `IndexType` 枚举（VDB/KV/GRAPH）
- 统一 `insert()`, `retrieve()`, `delete()`, `update()` 签名
- 新增 `insert_to_index()`, `remove_from_index()` 支持跨索引迁移
- 所有 Collection 使用 `config: dict` 初始化

**统一接口**：

```python
class BaseMemoryCollection(ABC):
    supported_index_types: ClassVar[set[IndexType]]

    # 索引管理
    def create_index(self, index_name, index_type, config) -> bool
    def delete_index(self, index_name) -> bool
    def list_indexes(self) -> list[dict]

    # 数据操作
    def insert(self, content, index_names, vector, metadata) -> str
    def insert_to_index(self, item_id, index_name, vector) -> bool
    def remove_from_index(self, item_id, index_name) -> bool

    # 检索操作
    def retrieve(self, query, index_name, top_k, with_metadata) -> list[dict]
    def delete(self, item_id) -> bool
    def update(self, item_id, content, vector, metadata) -> bool

    # 持久化
    def store(self, path) -> dict
    def load(cls, name, path) -> BaseMemoryCollection
```

### 3.2 Part 2: 索引层重构 ✅

**工时**：13h | **完成时间**：2024-12

**核心成果**：

- GraphIndex 独立模块化
- KVIndex 补全（search_with_scores, search_with_sort, search_range）
- IndexFactory 统一工厂
- PPR 算法实现（power iteration）

**文件结构**：

```
search_engine/
├── vdb_index/
│   ├── base_vdb_index.py
│   └── faiss_index.py
├── kv_index/
│   ├── base_kv_index.py
│   └── bm25s_index.py
├── graph_index/
│   ├── base_graph_index.py
│   └── simple_graph_index.py    # 支持 PPR
└── index_factory.py              # 统一创建入口
```

### 3.3 Part 3: MemoryManager 优化 ✅

**工时**：8h | **完成时间**：2024-12

**核心成果**：

- 注册表 + 工厂模式替代 if-elif 链
- 支持 `register_collection_type()` 扩展
- 懒加载优化
- 持久化路径统一

```python
class MemoryManager:
    _collection_registry = {
        "vdb": VDBMemoryCollection,
        "kv": KVMemoryCollection,
        "graph": GraphMemoryCollection,
        "hybrid": HybridCollection,
        "hierarchical": HierarchicalCollection,
    }

    @classmethod
    def register_collection_type(cls, type_name, collection_class):
        """注册自定义 Collection 类型"""
        cls._collection_registry[type_name] = collection_class
```

### 3.4 Part 4: Service 层适配 ✅

**工时**：12h | **完成时间**：2024-12

**核心成果**：

- 移除所有 `isinstance()` 类型检查
- Service 只持有一个 Collection
- 统一调用 `collection.insert()` / `collection.retrieve()`

**重写的 Service**：

| 服务                      | 改动                                   |
| ------------------------- | -------------------------------------- |
| HierarchicalMemoryService | 单 HybridCollection + tier-based index |
| HybridMemoryService       | 单 HybridCollection + multi-index      |
| GraphMemoryService        | 添加 ppr_retrieve, get_neighbors       |

### 3.5 Part 5: 论文特性支持 ✅

**工时**：22h | **完成时间**：2024-12

**使用 Mixin 模式实现**：

| 特性            | 论文       | 实现方式                                 |
| --------------- | ---------- | ---------------------------------------- |
| 三元组存储      | TiM        | `insert_triple()`, `retrieve_by_query()` |
| 链接演化        | A-Mem      | `evolve_links()`, `batch_evolve()`       |
| Ebbinghaus 遗忘 | MemoryBank | `EbbinghausForgetting` 类                |
| Heat Score 迁移 | MemoryOS   | `HeatScoreManager` 类                    |
| Token Budget    | SCM        | `TokenBudgetFilter` 类                   |
| 冲突检测        | Mem0       | `ConflictDetector` 类                    |

**使用示例**：

```python
from neuromem.memory_collection import VDBMemoryCollectionWithFeatures

collection = VDBMemoryCollectionWithFeatures({"name": "my_collection"})

# 三元组插入 (TiM)
collection.insert_triple(query, passage, answer, vector)

# 冲突检测插入 (Mem0)
result = collection.insert_with_conflict_check(content, vector, index_name)

# Token 预算检索 (SCM)
results = collection.retrieve_with_budget(query_vector, index_name, token_budget=2000)
```

### 3.6 Part 6: HybridCollection 实现 ✅

**工时**：18h | **完成时间**：2024-12

**核心设计**：一份数据 + 多种类型索引

```python
class HybridCollection(BaseMemoryCollection):
    def __init__(self, config):
        self.text_storage = TextStorage()      # 数据只存一份
        self.metadata_storage = MetadataStorage()

        # 多种类型的索引
        self.vdb_indexes: dict[str, BaseVDBIndex] = {}
        self.kv_indexes: dict[str, BaseKVIndex] = {}
        self.graph_indexes: dict[str, BaseGraphIndex] = {}
        self.index_meta: dict[str, dict] = {}  # 索引元信息

    def create_index(self, config: dict) -> bool:
        """创建任意类型的索引"""
        index_type = config.get("type")  # "vdb" | "kv" | "graph"
        index_name = config.get("name")

        if index_type == "vdb":
            self.vdb_indexes[index_name] = IndexFactory.create_vdb_index(config)
        elif index_type == "kv":
            self.kv_indexes[index_name] = IndexFactory.create_kv_index(config)
        elif index_type == "graph":
            self.graph_indexes[index_name] = IndexFactory.create_graph_index(config)

        self.index_meta[index_name] = {"type": index_type, **config}
        return True

    def insert(self, content, index_names, vector=None, metadata=None) -> str:
        """插入数据到指定索引"""
        item_id = self._store_content(content, metadata)

        for idx_name in index_names:
            self.insert_to_index(item_id, idx_name, vector)

        return item_id

    def retrieve_multi(self, queries: list[dict], top_k: int,
                       fusion_strategy: str = "rrf") -> list[dict]:
        """多索引检索 + 融合"""
        all_results = []
        for q in queries:
            idx_name = q["index_name"]
            results = self.retrieve(q["query"], idx_name, top_k, q.get("vector"))
            all_results.append(results)

        return self._fuse_results(all_results, fusion_strategy)
```

**MemoryOS 示例（STM→MTM 迁移）**：

```python
class MemoryOSService(BaseService):
    def __init__(self, stm_capacity=10):
        self.collection = HybridCollection({"name": "memory_os"})

        # STM: FIFO 队列索引
        self.collection.create_index({
            "name": "stm_fifo", "type": "kv", "index_type": "fifo"
        })

        # MTM: 向量检索索引
        self.collection.create_index({
            "name": "mtm_segment", "type": "vdb", "dim": 768
        })

    def _migrate_to_mtm(self, item_id: str, vector: np.ndarray):
        """将记忆从 STM 迁移到 MTM（数据不动，只调整索引）"""
        # 从 FIFO 索引移除
        self.collection.remove_from_index(item_id, "stm_fifo")
        # 添加到 VDB 索引
        self.collection.insert_to_index(item_id, "mtm_segment", vector=vector)
```

______________________________________________________________________

## 四、两套重构的关系

```
Pipeline 算子层 (R1-R6)              NeuroMem 底层 (Part 1-6)
├── R1: 服务接口统一         ←→      Part 4: Service 层适配
├── R2: PreInsert 重构       →       使用统一 insert 接口
├── R3: PostInsert 重构      →       使用 optimize 接口
├── R4: PreRetrieval 重构    →       不访问存储
├── R5: PostRetrieval 重构   →       使用 retrieve 接口
└── R6: MemoryInsert 扩展    →       使用 insert_mode/insert_params
                                      ↓
                              Part 1: Collection 接口
                              Part 2: 索引层
                              Part 3: MemoryManager
                              Part 6: HybridCollection
                              Part 5: 论文特性
```

**层级调用关系**：

```
PreInsert (R2)
    ↓ memory_entries + insert_method
MemoryInsert (R6)
    ↓ call_service(insert)
MemoryService (R1)
    ↓ collection.insert()
Collection (Part 1)
    ↓ index.add()
SearchEngine (Part 2)
```

______________________________________________________________________

## 五、配置与测试

### 5.1 配置驱动原则

- 所有 Prompt 模板和默认参数移出代码，统一放入 YAML 配置
- 运行时严禁依赖硬编码默认值，缺失配置应快速失败
- 配置本身即文档

### 5.2 测试覆盖

- **服务层**：插入模式扩展、NeuroMem 集成、层间迁移
- **算子层**：各 action 的参数分支、异常路径
- **集成层**：通过 SAGE benchmark 验证 end-to-end 行为

______________________________________________________________________

## 六、论文特性映射矩阵（Memory.md 对照）

### 6.1 维度说明

- **数据结构**：对应 MemoryService + NeuroMem Collection
- **插入前操作**：`PreInsert` 下的 action
- **插入后操作**：`PostInsert` 下的 action
- **检索前操作**：`PreRetrieval` 下的 action
- **检索后操作**：`PostRetrieval` 下的 action

### 6.2 TiM: Think-in-Memory

| 维度     | 论文设计                 | SAGE 实现                                      |
| -------- | ------------------------ | ---------------------------------------------- |
| 数据结构 | LSH 哈希桶 + thoughts    | `VectorHashMemoryService` + VDB Collection     |
| 插入前   | Q-R → inductive thoughts | `PreInsert.tri_embed / extract`                |
| 插入后   | 桶内 Forget / Merge      | `PostInsert.distillation + optimize.summarize` |
| 检索前   | query embedding          | `PreRetrieval.embedding / multi_embed`         |
| 检索后   | thoughts → prompt        | `PostRetrieval.merge + augment + format`       |

### 6.3 MemoryBank

| 维度     | 论文设计                                   | SAGE 实现                                  |
| -------- | ------------------------------------------ | ------------------------------------------ |
| 数据结构 | 原始对话 + daily/global summary + portrait | `HierarchicalMemoryService`（STM/MTM/LTM） |
| 插入前   | 检索已有 persona/summary                   | `PreInsert.transform.summarize + score`    |
| 插入后   | Ebbinghaus/heat 遗忘                       | `PostInsert.forgetting`                    |
| 检索前   | 直接 embedding                             | `PreRetrieval.embedding`                   |
| 检索后   | 检索 + 画像 + summary 拼接                 | `PostRetrieval.augment + format`           |

### 6.4 MemGPT

| 维度     | 论文设计                                    | SAGE 实现                                     |
| -------- | ------------------------------------------- | --------------------------------------------- |
| 数据结构 | Working Context + FIFO Queue + Recall Store | `KeyValueMemoryService + HierarchicalService` |
| 插入前   | 提取事实、决定 replace                      | `PreInsert.extract + score.importance`        |
| 插入后   | replace(old,new)                            | `PostInsert.distillation / optimize.migrate`  |
| 检索前   | 解析 query、提取关键词                      | `PreRetrieval.optimize.keyword_extract`       |
| 检索后   | 多次访问、拼接上下文                        | `PostRetrieval.merge + augment + format`      |

### 6.5 A-Mem

| 维度     | 论文设计                                   | SAGE 实现                                   |
| -------- | ------------------------------------------ | ------------------------------------------- |
| 数据结构 | note = {content, keywords, tags, links} 图 | `GraphMemoryService + HybridCollection`     |
| 插入前   | LLM 生成 Ki/Gi/Xi                          | `PreInsert.extract`                         |
| 插入后   | Link Generation + Memory Evolution         | `PostInsert.link_evolution`                 |
| 检索前   | query embedding                            | `PreRetrieval.embedding`                    |
| 检索后   | 链接扩展、多跳                             | `PostRetrieval.merge.link_expand + augment` |

### 6.6 MemoryOS

| 维度     | 论文设计                                     | SAGE 实现                                |
| -------- | -------------------------------------------- | ---------------------------------------- |
| 数据结构 | STM(FIFO) + MTM(segment/heat) + LPM(persona) | `HierarchicalService + HybridCollection` |
| 插入前   | 计算 Fscore/heat                             | `PreInsert.score`                        |
| 插入后   | 基于 heat 迁移与淘汰                         | `PostInsert.migrate + forgetting`        |
| 检索前   | embedding + 关键词                           | `PreRetrieval.embedding + optimize`      |
| 检索后   | STM + MTM + LPM 拼接                         | `PostRetrieval.merge + augment + format` |

### 6.7 HippoRAG / HippoRAG2

| 维度     | 论文设计                                | SAGE 实现                                |
| -------- | --------------------------------------- | ---------------------------------------- |
| 数据结构 | Open KG (Phrase/Passage/Relation nodes) | `GraphMemoryService + GraphCollection`   |
| 插入前   | NER + OpenIE 提取 triples               | `PreInsert.tri_embed / extract.entity`   |
| 插入后   | 建立同义词边                            | `PostInsert.link_evolution.synonym_edge` |
| 检索前   | NER / Query-to-Triple                   | `PreRetrieval.optimize.keyword_extract`  |
| 检索后   | PPR 图检索 + Passage 排序               | `PostRetrieval.rerank.ppr + format`      |

### 6.8 LD-Agent

| 维度     | 论文设计                      | SAGE 实现                                 |
| -------- | ----------------------------- | ----------------------------------------- |
| 数据结构 | STM 对话缓存 + LTM 事件摘要库 | `ShortTermService + HierarchicalService`  |
| 插入前   | 判断是否构成"事件"            | `PreInsert.transform.summarize + score`   |
| 插入后   | Replace/更新旧摘要            | `PostInsert.distillation / forgetting`    |
| 检索前   | 提取关键词集合 V_q            | `PreRetrieval.optimize.keyword_extract`   |
| 检索后   | 语义 + 话题重叠 + 时间衰减    | `PostRetrieval.rerank.weighted + augment` |

### 6.9 SCM（Self-Controlled Memory）

| 维度     | 论文设计                                     | SAGE 实现                                      |
| -------- | -------------------------------------------- | ---------------------------------------------- |
| 数据结构 | Memory Stream (observation/response/summary) | `ShortTermService + PreInsert.summarize`       |
| 插入前   | 每轮交互生成 summary + embedding             | `PreInsert.transform.summarize + multi_embed`  |
| 插入后   | 无（不做 replace/merge）                     | 不启用 PostInsert                              |
| 检索前   | 判断是否激活记忆                             | `PreRetrieval.validate + optimize`             |
| 检索后   | Token budget 截断/压缩                       | `PostRetrieval.filter.token_budget + compress` |

### 6.10 Mem0 / Mem0ᵍ

| 维度     | 论文设计                     | SAGE 实现                                  |
| -------- | ---------------------------- | ------------------------------------------ |
| 数据结构 | 文本事实 + 全局摘要 / 图记忆 | `HierarchicalService + GraphService`       |
| 插入前   | 提取候选记忆 / 生成 triplets | `PreInsert.transform + extract.entity`     |
| 插入后   | ADD/UPDATE/DELETE/冲突检测   | `PostInsert.distillation / forgetting`     |
| 检索前   | 直接 embedding               | `PreRetrieval.embedding`                   |
| 检索后   | 图子图构建、多跳序列化       | `PostRetrieval.merge.link_expand + format` |

______________________________________________________________________

## 七、文档位置索引

| 文档                    | 路径                                                                          |
| ----------------------- | ----------------------------------------------------------------------------- |
| Pipeline 重构概览       | `benchmark/.../mem_docs/refactor/REFACTOR_OVERVIEW.md`                        |
| R1 服务接口统一         | `benchmark/.../mem_docs/refactor/REFACTOR_R1_SERVICE_INTERFACE.md`            |
| R2 PreInsert            | `benchmark/.../mem_docs/refactor/REFACTOR_R2_PRE_INSERT.md`                   |
| R3 PostInsert           | `benchmark/.../mem_docs/refactor/REFACTOR_R3_POST_INSERT.md`                  |
| R4 PreRetrieval         | `benchmark/.../mem_docs/refactor/REFACTOR_R4_PRE_RETRIEVAL.md`                |
| R5 PostRetrieval        | `benchmark/.../mem_docs/refactor/REFACTOR_R5_POST_RETRIEVAL.md`               |
| R6 MemoryInsert         | `benchmark/.../mem_docs/refactor/REFACTOR_R6_MEMORY_INSERT.md`                |
| NeuroMem 重构概览       | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Overview.md`                  |
| Part 1 Collection       | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Part1_Collection.md`          |
| Part 2 SearchEngine     | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Part2_SearchEngine.md`        |
| Part 3 MemoryManager    | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Part3_MemoryManager.md`       |
| Part 4 Service          | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Part4_Service.md`             |
| Part 5 PaperFeatures    | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Part5_PaperFeatures.md`       |
| Part 6 HybridCollection | `middleware/.../mem_docs/TODO_NeuroMem_Refactor_Part6_CompositeCollection.md` |

______________________________________________________________________

## 八、后续建议

### 8.1 新增 MemoryService

- 必须继承 `BaseService`
- 使用 `MemoryManager` + 适当的 `MemoryCollection`
- 对外仅暴露 insert/retrieve/delete/optimize 接口
- 不在服务外泄露内部数据结构

### 8.2 新增 Pipeline 算子

- 遵循本档案的职责边界与访问约束
- 所有行为通过配置驱动，避免硬编码
- 与单一记忆服务通过 `call_service` 交互

### 8.3 新增论文特性

- 优先使用 Mixin 模式
- 在 Part 5 文档中登记
- 更新论文特性映射矩阵

______________________________________________________________________

*本档案后续如有架构/实现变更，应同步更新，以保持文档与代码的一致性。*

______________________________________________________________________

## 九、论文复现优先级与 Action 配置

> 基于学术影响力、实现创新性和与 SAGE 框架的匹配度，给出复现优先级排序。
>
> **核心原则**：大类对应 action 参数，小类由配置参数控制，可模块化复现。

### 9.1 工作五维度 Action 配置总览

| 工作              | D1 Service            | D2 PreInsert | D3 PostInsert    | D4 PreRetrieval | D5 PostRetrieval | Stars |
| ----------------- | --------------------- | ------------ | ---------------- | --------------- | ---------------- | ----- |
| HippoRAG          | `graph_memory`        | `tri_embed`  | `link_evolution` | `embedding`     | `rerank`         | 3k+   |
| Generative Agents | `neuromem_vdb`        | `none`       | `reflection`     | `embedding`     | `rerank`         | 20k+  |
| MemGPT            | `hierarchical_memory` | `transform`  | `distillation`   | `none`          | `none`           | 19k+  |
| MemoryBank        | `hierarchical_memory` | `none`       | `forgetting`     | `embedding`     | `none`           | 500+  |
| A-mem             | `graph_memory`        | `tri_embed`  | `link_evolution` | `embedding`     | `merge`          | 200+  |
| MemoryOS          | `hierarchical_memory` | `none`       | `forgetting`     | `embedding`     | `merge`          | 300+  |
| SCM4LLMs          | `short_term_memory`   | `none`       | `distillation`   | `embedding`     | `filter`         | -     |
| SeCom             | `neuromem_vdb`        | `transform`  | `distillation`   | `none`          | `none`           | -     |
| EmotionalRAG      | `neuromem_vdb`        | `tri_embed`  | `none`           | `embedding`     | `merge`          | -     |
| LD-Agent          | `hierarchical_memory` | `tri_embed`  | `forgetting`     | `optimize`      | `rerank`         | -     |
| LoCoMo            | `neuromem_vdb`        | `transform`  | `reflection`     | `embedding`     | `summarize`      | -     |

### 9.2 复现优先级排序

#### Tier 1: 核心工作（必须复现）

| 优先级     | 工作              | Action 配置                                                  | 复现价值                      |
| ---------- | ----------------- | ------------------------------------------------------------ | ----------------------------- |
| ⭐⭐⭐⭐⭐ | HippoRAG          | `(graph_memory, tri_embed, link_evolution, embedding, ppr)`  | 知识图谱 + PPR，多跳推理 SOTA |
| ⭐⭐⭐⭐⭐ | Generative Agents | `(neuromem_vdb, none, reflection, embedding, weighted)`      | 记忆领域奠基性工作，反思机制  |
| ⭐⭐⭐⭐⭐ | MemGPT/Letta      | `(hierarchical_memory, transform, distillation, none, none)` | LLM OS 概念开创者，19k+ stars |

#### Tier 2: 重要工作（推荐复现）

| 优先级   | 工作       | Action 配置                                                   | 复现价值                |
| -------- | ---------- | ------------------------------------------------------------- | ----------------------- |
| ⭐⭐⭐⭐ | MemoryBank | `(hierarchical_memory, none, forgetting, embedding, none)`    | 心理学启发的遗忘机制    |
| ⭐⭐⭐⭐ | A-mem      | `(graph_memory, tri_embed, link_evolution, embedding, merge)` | Zettelkasten 原则应用   |
| ⭐⭐⭐⭐ | MemoryOS   | `(hierarchical_memory, none, forgetting, embedding, merge)`   | 完整三层架构 + 热度机制 |

#### Tier 3: 补充工作（选择复现）

| 优先级 | 工作         | Action 配置                                                      | 复现价值            |
| ------ | ------------ | ---------------------------------------------------------------- | ------------------- |
| ⭐⭐⭐ | SCM4LLMs     | `(short_term_memory, none, distillation, embedding, filter)`     | 自控制压缩机制      |
| ⭐⭐⭐ | SeCom        | `(neuromem_vdb, transform, distillation, none, none)`            | 分段 + 压缩组合     |
| ⭐⭐⭐ | EmotionalRAG | `(neuromem_vdb, tri_embed, none, embedding, merge)`              | 多维向量融合策略    |
| ⭐⭐⭐ | LD-Agent     | `(hierarchical_memory, tri_embed, forgetting, optimize, rerank)` | 时间感知的层级迁移  |
| ⭐⭐⭐ | LoCoMo       | `(neuromem_vdb, transform, reflection, embedding, summarize)`    | 事实提取 + 双向反思 |

### 9.3 Action 实现清单

#### D1 Memory Service Actions

| Action                | 实现状态  | 参考工作         | 核心参数                           |
| --------------------- | --------- | ---------------- | ---------------------------------- |
| `short_term_memory`   | ✅ 已实现 | SCM4LLMs         | `maxlen`                           |
| `vector_hash_memory`  | ✅ 已实现 | TiM              | `lsh_nbits`, `k_nearest`           |
| `neuromem_vdb`        | ✅ 已实现 | MemGPT, GA       | `collection_name`, `top_k`         |
| `graph_memory`        | ✅ 已实现 | HippoRAG, A-mem  | `graph_type`, `edge_policy`        |
| `hierarchical_memory` | ✅ 已实现 | MemoryOS, MemGPT | `tier_count`, `migration_policy`   |
| `hybrid_memory`       | ✅ 已实现 | Mem0, Mem0ᵍ      | `graph_enabled`, `fusion_strategy` |

#### D2 PreInsert Actions

| Action      | 实现状态  | 参考工作      | 核心参数                            |
| ----------- | --------- | ------------- | ----------------------------------- |
| `none`      | ✅ 已实现 | -             | -                                   |
| `tri_embed` | ✅ 已实现 | HippoRAG, TiM | `triple_extraction_prompt`          |
| `transform` | ✅ 已实现 | MemGPT, SeCom | `transform_type`, `chunk_size`      |
| `extract`   | ✅ 已实现 | A-Mem, Mem0   | `extract_type: keyword/entity/noun` |
| `scm_embed` | ✅ 已实现 | SCM           | `embed_type: three_way`             |
| `validate`  | ✅ 已实现 | -             | `validation_rules`                  |

#### D3 PostInsert Actions

| Action           | 实现状态  | 参考工作          | 核心参数                              |
| ---------------- | --------- | ----------------- | ------------------------------------- |
| `none`           | ✅ 已实现 | -                 | -                                     |
| `distillation`   | ✅ 已实现 | SCM4LLMs, TiM     | `topk`, `threshold`, `prompt`         |
| `reflection`     | ✅ 已实现 | Generative Agents | `trigger_mode`, `threshold`, `prompt` |
| `link_evolution` | ✅ 已实现 | A-mem, HippoRAG   | `link_policy`, `strengthen_factor`    |
| `forgetting`     | ✅ 已实现 | MemoryBank        | `decay_type: ebbinghaus/lfu/heat`     |
| `migrate`        | ✅ 已实现 | MemoryOS          | `migrate_policy: heat`                |
| `mem0_crud`      | ✅ 已实现 | Mem0              | ADD/UPDATE/DELETE/NOOP 决策           |

#### D4 PreRetrieval Actions

| Action      | 实现状态  | 参考工作     | 核心参数                                        |
| ----------- | --------- | ------------ | ----------------------------------------------- |
| `none`      | ✅ 已实现 | -            | -                                               |
| `embedding` | ✅ 已实现 | HippoRAG, GA | `embedding_model`                               |
| `optimize`  | ✅ 已实现 | LD-Agent     | `optimize_type: keyword_extract/expand/rewrite` |
| `scm_gate`  | ✅ 已实现 | SCM          | 是否激活记忆检索判断                            |
| `validate`  | ✅ 已实现 | -            | `validation_rules`                              |

#### D5 PostRetrieval Actions

| Action          | 实现状态  | 参考工作     | 核心参数                                           |
| --------------- | --------- | ------------ | -------------------------------------------------- |
| `none`          | ✅ 已实现 | -            | `conversation_format_prompt`                       |
| `rerank`        | ✅ 已实现 | HippoRAG, GA | `rerank_type: semantic/time_weighted/ppr/weighted` |
| `filter`        | ✅ 已实现 | SCM4LLMs     | `filter_type: token_budget/threshold/top_k`        |
| `merge`         | ✅ 已实现 | MemoryOS     | `merge_strategy: link_expand/multi_query`          |
| `augment`       | ✅ 已实现 | -            | `augment_type: context/metadata/temporal`          |
| `compress`      | ✅ 已实现 | -            | `compress_type: extractive`                        |
| `format`        | ✅ 已实现 | -            | `format_type: template/structured/chat/xml`        |
| `scm_three_way` | ✅ 已实现 | SCM          | drop/summary/raw 三元决策                          |

### 9.4 推荐复现顺序

```
阶段1 (Week 1-2):  本地项目快速验证
  - SCM4LLMs: 验证 Token Budget Filtering
  - SeCom:    验证 Topic Segmentation + Compression

阶段2 (Week 3-4):  经典反思机制
  - Generative Agents: 重要性 + 反思 + 时间加权

阶段3 (Week 5-7):  知识图谱方向
  - HippoRAG: KG + OpenIE + PPR

阶段4 (Week 8-10): 分层记忆系统
  - MemGPT:   功能分层 + 摘要
  - MemoryOS: 三层 + 热度迁移

阶段5 (Week 11-12): 遗忘机制
  - MemoryBank: Ebbinghaus Forgetting

阶段6 (Week 13+): 按需补充
  - A-mem:       链接图 + 链接演化
  - EmotionalRAG: 多维向量
  - LD-Agent:    时间迁移 + 名词查询
```

### 9.5 论文变体配置清单

| 基础论文 | 变体             | 配置文件                            | 关键差异                              |
| -------- | ---------------- | ----------------------------------- | ------------------------------------- |
| Mem0     | Mem0 (基础版)    | `locomo_mem0_pipeline.yaml`         | 向量存储 + CRUD                       |
| Mem0     | Mem0ᵍ (图增强版) | `locomo_mem0g_pipeline.yaml`        | `graph_enabled: true`                 |
| HippoRAG | HippoRAG         | `locomo_hipporag_pipeline.yaml`     | `ppr_depth: 2`                        |
| HippoRAG | HippoRAG2        | `locomo_hipporag2_pipeline.yaml`    | `ppr_depth: 3, enhanced_rerank: true` |
| TiM      | TiM (带蒸馏)     | `locomo_tim_pipeline.yaml`          | `post_insert.action: distillation`    |
| TiM      | TiM (基础版)     | `locomo_tim_basic_pipeline.yaml`    | `post_insert.action: none`            |
| MemGPT   | MemGPT           | `locomo_memgpt_pipeline.yaml`       | `tool_use: false`                     |
| MemGPT   | MemGPT-agent     | `locomo_memgpt_agent_pipeline.yaml` | `tool_use: true`                      |
