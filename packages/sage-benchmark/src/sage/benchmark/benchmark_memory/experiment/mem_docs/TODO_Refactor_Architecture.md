# 记忆体架构重构任务书

> **创建时间**: 2025-12-01 **问题来源**: 代码审查发现架构偏离设计规范

______________________________________________________________________

## 一、问题诊断

### 1.1 设计规范（应遵循的原则）

```
记忆体 = 记忆操作 + 记忆数据结构

记忆操作（4种）：
├── 插入前操作 (PreInsert): 预处理记忆数据，决定插入方式，仅允许检索
├── 插入后操作 (PostInsert): 优化记忆数据结构，仅允许一次 检索→删除→插入
├── 检索前操作 (PreRetrieval): 预处理提问，不允许访问记忆数据结构
└── 检索后操作 (PostRetrieval): 处理返回结果，允许多次查询并拼接成 prompt

记忆数据结构：
├── 存储结构
└── 接口
    ├── 插入: 可提供多种方法（主动插入 / 被动插入）
    ├── 检索: 方法固定，外部不可干预
    └── 删除: 方法固定

插入方式：
├── 主动插入: 外部提供参数，指定记忆服务如何插入
└── 被动插入: 由服务内部决定如何插入（如 FIFO 自动出队）

约束：每个 pipeline 只能有一个记忆服务
```

### 1.2 当前代码问题清单

| 文件                  | 问题                                                                              | 严重程度 |
| --------------------- | --------------------------------------------------------------------------------- | -------- |
| `post_insert.py`      | 引用多个服务 (`service_name`, `graph_service_name`, `hierarchical_service_names`) | 🔴 严重  |
| `post_insert.py`      | 多次执行检索-删除-插入（违反"仅允许一次"约束）                                    | 🔴 严重  |
| `post_retrieval.py`   | 内部实现了去重、embedding 计算等应属于 MemoryService 的功能                       | 🟡 中等  |
| `post_retrieval.py`   | merge action 从 data 中读取多个来源，暗示多服务设计                               | 🟡 中等  |
| `pre_retrieval.py`    | 架构上正确（不访问记忆数据结构），但 route action 暗示多服务                      | 🟡 中等  |
| `memory_insert.py`    | 只支持被动插入，缺少主动插入接口                                                  | 🟡 中等  |
| `memory_retrieval.py` | 基本正确，但缺少对"方法固定"的强制约束                                            | 🟢 轻微  |

______________________________________________________________________

## 二、重构任务分解

为确保任务互不干扰，按模块拆分为以下独立任务：

### 任务概览

| 任务编号 | 任务名称                   | 依赖   | 优先级 | 预估工时 |
| -------- | -------------------------- | ------ | ------ | -------- |
| R1       | MemoryService 接口统一     | 无     | P0     | 3天      |
| R2       | PostInsert 单服务重构      | R1     | P0     | 2天      |
| R3       | PostRetrieval 职责边界修正 | R1     | P0     | 2天      |
| R4       | MemoryInsert 插入模式扩展  | R1     | P1     | 1天      |
| R5       | PreRetrieval 路由逻辑修正  | R1, R3 | P1     | 1天      |

______________________________________________________________________

## 三、任务详情（独立文件）

每个任务详情请参见独立的任务文件：

- `TODO_R1_ServiceInterface.md` - MemoryService 接口统一
- `TODO_R2_PostInsertRefactor.md` - PostInsert 单服务重构
- `TODO_R3_PostRetrievalRefactor.md` - PostRetrieval 职责边界修正
- `TODO_R4_InsertModeExtension.md` - MemoryInsert 插入模式扩展
- `TODO_R5_PreRetrievalRoute.md` - PreRetrieval 路由逻辑修正

______________________________________________________________________

## 四、重构原则

### 4.1 单服务原则

```yaml
# 正确配置示例
services:
  register_memory_service: "hierarchical_memory"  # 唯一的记忆服务

# 错误配置（应避免）
services:
  register_memory_service: "short_term_memory"
  graph_memory_service: "graph_memory"        # ❌ 不应有多个
  stm_service: "short_term_memory"            # ❌
  mtm_service: "mid_term_memory"              # ❌
  ltm_service: "long_term_memory"             # ❌
```

### 4.2 操作约束

| 操作阶段        | 允许的记忆结构访问          |
| --------------- | --------------------------- |
| PreInsert       | 仅检索（用于决策）          |
| MemoryInsert    | 插入（主动/被动）           |
| PostInsert      | 一次 检索→删除→插入         |
| PreRetrieval    | 禁止访问                    |
| MemoryRetrieval | 检索（固定方法）            |
| PostRetrieval   | 多次检索（用于拼接 prompt） |

### 4.3 职责边界

```
算子职责：
├── PreInsert: 数据预处理、决定插入方式
├── MemoryInsert: 调用服务执行插入
├── PostInsert: 触发服务内部优化（不自己实现）
├── PreRetrieval: 查询预处理
├── MemoryRetrieval: 调用服务执行检索
└── PostRetrieval: 结果后处理、格式化 prompt

记忆服务职责：
├── 存储管理
├── 插入方法实现（含 FIFO、分层迁移等）
├── 检索算法（含去重、排序）
├── 删除机制
├── 图操作（link_evolution 等）
└── 遗忘/淘汰机制
```

______________________________________________________________________

## 五、底层架构：NeuroMem 引擎

记忆服务 (MemoryService) 应基于 **NeuroMem** 底层引擎实现，而非自己维护数据结构。

### 5.1 NeuroMem 模块位置

```
sage-middleware/src/sage/middleware/components/sage_mem/neuromem/
├── memory_manager.py          # 管理所有 Collection 实例
├── memory_collection/
│   ├── base_collection.py     # 基础集合抽象
│   ├── vdb_collection.py      # 向量数据库集合 (FAISS 等)
│   ├── graph_collection.py    # 图结构集合
│   └── kv_collection.py       # 键值对集合 (BM25 等)
├── storage_engine/
│   ├── text_storage.py        # 文本存储
│   ├── metadata_storage.py    # 元数据存储
│   └── vector_storage.py      # 向量存储
└── search_engine/
    ├── vdb_index/             # 向量索引 (FAISS, etc.)
    ├── graph_index/           # 图索引
    ├── kv_index/              # KV 索引 (BM25S, etc.)
    └── hybrid_index/          # 混合索引
```

### 5.2 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                      Pipeline 算子层                         │
│  (pre_insert, memory_insert, post_insert, pre_retrieval,    │
│   memory_retrieval, post_retrieval)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     MemoryService 服务层                     │
│  (graph_memory_service, hierarchical_memory_service,        │
│   hybrid_memory_service, key_value_memory_service, etc.)    │
│                                                              │
│  职责：业务逻辑封装、统一接口、optimize() 触发              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     NeuroMem 引擎层                          │
│  (MemoryManager, VDBCollection, GraphCollection, etc.)      │
│                                                              │
│  职责：底层存储、索引管理、检索算法                          │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 服务层与底层的映射

| 服务层 (MemoryService)        | 底层 (NeuroMem Collection)                   |
| ----------------------------- | -------------------------------------------- |
| `graph_memory_service`        | `GraphMemoryCollection` + `GraphIndex`       |
| `hierarchical_memory_service` | 多个 `VDBMemoryCollection` (STM/MTM/LTM)     |
| `hybrid_memory_service`       | `VDBMemoryCollection` + `KVMemoryCollection` |
| `key_value_memory_service`    | `KVMemoryCollection`                         |
| `short_term_memory_service`   | `VDBMemoryCollection` (简单队列)             |
| `vector_hash_memory_service`  | `VDBMemoryCollection` (LSH 索引)             |

### 5.4 重构要点

1. **服务层不应自己实现数据结构**：

   - ❌ `graph_memory_service.py` 中的 `self.nodes`, `self.edges`, `self.adj_list`
   - ✅ 应改为调用 `GraphMemoryCollection`

1. **服务层负责业务逻辑**：

   - 统一接口 (insert/retrieve/delete)
   - optimize() 触发机制
   - 分层迁移策略
   - 遗忘策略选择

1. **NeuroMem 层负责存储和索引**：

   - 向量索引 (FAISS, HNSW)
   - 图索引 (邻接表, PPR)
   - 文本索引 (BM25S)
   - 持久化存储

______________________________________________________________________

## 六、验收标准

1. **配置文件**：每个 pipeline 配置只能指定一个 `register_memory_service`
1. **PostInsert**：不再持有多个服务引用，仅通过统一接口与单一服务交互
1. **PostRetrieval**：不再实现 embedding 计算、去重等应属于服务的功能
1. **MemoryInsert**：支持主动插入模式（通过 metadata 传递插入参数）
1. **服务层重构**：所有 MemoryService 基于 NeuroMem Collection 实现
1. **测试通过**：现有测试用例全部通过，新增架构约束测试

______________________________________________________________________

*文档创建时间: 2025-12-01*
