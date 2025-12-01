# D1: Memory Service 开发 TODO

## 📌 任务交接说明

**负责人**: _待分配_\
**预估工时**: 15 人天\
**依赖**: 无（可独立开发）\
**交付物**: `services/` 目录下的新 Memory Service 实现

本维度负责**记忆数据的底层存储结构**，是整个记忆系统的基础。你需要实现 4 种新的存储后端：图存储、分层存储、混合存储、键值存储。每种存储都需要提供统一的
`insert(entry, vector, metadata)` 和 `retrieve(query, vector, metadata)` 接口，以便与上层算子无缝对接。

**开发前请阅读**:

- 现有实现参考: `short_term_memory_service.py`, `vector_hash_memory_service.py`, `neuromem_vdb_service.py`
- 接口规范: 所有 service 需继承统一基类，实现 `insert` 和 `retrieve` 方法
- 配置方式: 通过 `services.register_memory_service` 指定使用哪个后端

**验收标准**:

- [ ] 通过单元测试
- [ ] 与现有 Pipeline 集成测试通过
- [ ] 性能基准测试（插入/检索延迟、内存占用）

______________________________________________________________________

> **代码位置**: `services/` 目录 **配置键**: `services.register_memory_service` **职责**: 记忆数据的底层存储与检索

______________________________________________________________________

## 📊 Action 总览

| Action                | 状态      | 小类参数                   | 参考工作                     |
| --------------------- | --------- | -------------------------- | ---------------------------- |
| `short_term_memory`   | ✅ 已实现 | `maxlen`                   | SCM4LLMs                     |
| `vector_hash_memory`  | ✅ 已实现 | `lsh_nbits`, `k_nearest`   | -                            |
| `neuromem_vdb`        | ✅ 已实现 | `collection_name`, `top_k` | -                            |
| `graph_memory`        | ✅ 已实现 | 见下文                     | HippoRAG, A-mem              |
| `hierarchical_memory` | ✅ 已实现 | 见下文                     | MemoryOS, MemGPT, MemoryBank |
| `hybrid_memory`       | ✅ 已实现 | 见下文                     | EmotionalRAG                 |
| `key_value_memory`    | ✅ 已实现 | 见下文                     | LAPS                         |

______________________________________________________________________

## ✅ DONE-D1-1: `graph_memory`

> **实现位置**:
> `sage-middleware/src/sage/middleware/components/sage_mem/services/graph_memory_service.py` (583行)

### 概述

基于图结构的记忆存储，支持知识图谱和链接图两种模式。

### 小类参数

```yaml
services:
  graph_memory:
    # 图类型
    graph_type: "knowledge_graph"  # knowledge_graph | link_graph

    # 知识图谱专用 (HippoRAG)
    triple_store: "igraph"         # igraph | networkx | neo4j
    node_embedding_dim: 768
    edge_types: ["relation", "synonym", "temporal"]

    # 链接图专用 (A-mem / Zettelkasten)
    link_policy: "bidirectional"   # bidirectional | directed
    max_links_per_node: 50
    link_weight_init: 1.0
```

### 参考实现分析

#### HippoRAG (knowledge_graph)

- **代码位置**: `/home/zrc/develop_item/HippoRAG/src/`
- **核心结构**:
  - iGraph 存储三元组节点
  - 三类 Embedding: passage_node_emb, entity_node_emb, fact_node_emb
  - 同义边 (synonym edge) 基于 KNN 相似度
- **关键接口**:
  ```python
  # 插入
  add_node(entity, embedding, metadata)
  add_edge(src, dst, relation, weight)

  # 检索
  get_neighbors(node_id, edge_type)
  personalized_pagerank(query_nodes, damping=0.5)
  ```

#### A-mem (link_graph)

- **代码位置**: `/home/zrc/develop_item/A-mem/`
- **核心结构**:
  - Zettelkasten 风格链接图
  - 每个记忆节点包含: content, keywords, context, links
  - 链接动态演化: activate, strengthen, update_neighbor
- **关键接口**:
  ```python
  # 插入
  add_memory(content, keywords, context)
  create_link(src_id, dst_id, weight)

  # 检索
  retrieve(query, top_k)
  expand_links(node_id, depth=1)
  ```

### 开发任务

- [ ] 定义统一的图存储接口 `GraphMemoryService`
- [ ] 实现 `knowledge_graph` 模式 (参考 HippoRAG)
  - [ ] 三元组节点存储
  - [ ] 多类型边支持
  - [ ] PPR 检索
- [ ] 实现 `link_graph` 模式 (参考 A-mem)
  - [ ] 记忆节点链接
  - [ ] 链接权重管理
  - [ ] 邻居扩展检索
- [ ] 统一 insert/retrieve 接口适配

### 预估工时: 5 天

______________________________________________________________________

## ✅ DONE-D1-2: `hierarchical_memory`

> **实现位置**:
> `sage-middleware/src/sage/middleware/components/sage_mem/services/hierarchical_memory_service.py`
> (586行)

### 概述

分层记忆存储，支持 2 层、3 层和功能分层模式。

### 小类参数

```yaml
services:
  hierarchical_memory:
    # 层级配置
    tier_count: 3                    # 2 | 3
    tier_names: ["stm", "mtm", "ltm"]  # 层名称

    # 各层存储后端
    tier_backends:
      stm: "deque"                   # deque | list
      mtm: "faiss"                   # faiss | chroma
      ltm: "profile"                 # profile | summary | archive

    # 各层容量
    tier_capacities:
      stm: 100
      mtm: 1000
      ltm: -1                        # -1 表示无限

    # 迁移策略
    migration_policy: "heat"         # time | heat | manual | overflow
    migration_threshold: 0.7         # heat 模式阈值
    migration_interval: 3600         # time 模式间隔(秒)
```

### 参考实现分析

#### MemoryOS (三层: STM/MTM/LTM)

- **代码位置**: `/home/zrc/develop_item/MemoryOS/`
- **核心结构**:
  - STM: deque 滑动窗口
  - MTM: FAISS 向量索引
  - LTM: Profile JSON (User KG + Assistant KG)
- **迁移机制**: 热度驱动，超阈值更新 Profile

#### MemGPT (功能分层: Core/Archival/Recall)

- **代码位置**: `/home/zrc/develop_item/MemGPT/memgpt/`
- **核心结构**:
  - Core Memory: 系统提示词中的固定上下文
  - Archival Memory: 向量数据库长期存储
  - Recall Memory: 对话历史缓存
- **迁移机制**: Function calling 触发

#### MemoryBank (两层: History/Summary)

- **代码位置**: `/home/zrc/develop_item/MemoryBank-SiliconFriend/`
- **核心结构**:
  - History Memory: 原始对话
  - Summary Memory: 多层摘要 (日/周/全局)
  - Personality Memory: 用户画像
- **迁移机制**: 定时摘要 + Ebbinghaus 遗忘

#### LD-Agent (两层: STM/LTM)

- **代码位置**: `/home/zrc/develop_item/LD-Agent/`
- **核心结构**:
  - STM: 当前会话对话列表
  - LTM: ChromaDB 向量存储
- **迁移机制**: 会话间隔 > 1小时触发摘要转存

### 开发任务

- [ ] 定义统一的分层存储接口 `HierarchicalMemoryService`
- [ ] 实现 `two_tier` 模式
  - [ ] STM + LTM 双层结构 (MemoryBank, LD-Agent)
  - [ ] 时间/热度迁移
- [ ] 实现 `three_tier` 模式
  - [ ] STM + MTM + LTM 三层结构 (MemoryOS)
  - [ ] 层间迁移逻辑
- [ ] 实现 `functional` 模式
  - [ ] Core + Archival + Recall (MemGPT)
  - [ ] Function calling 触发
- [ ] 统一 insert/retrieve 接口适配

### 预估工时: 5 天

______________________________________________________________________

## ✅ DONE-D1-3: `hybrid_memory`

> **实现位置**:
> `sage-middleware/src/sage/middleware/components/sage_mem/services/hybrid_memory_service.py` (617行)

### 概述

多索引混合存储，支持多维向量和多路检索。

### 小类参数

```yaml
services:
  hybrid_memory:
    # 索引配置
    indexes:
      - name: "semantic"
        type: "vector"
        embedding_model: "text-embedding-3-small"
      - name: "emotion"
        type: "vector"
        embedding_model: "emotion-roberta"
      - name: "keyword"
        type: "bm25"

    # 融合策略
    fusion_strategy: "weighted"      # weighted | rrf | learned
    fusion_weights: [0.5, 0.3, 0.2]
```

### 参考实现分析

#### EmotionalRAG (双向量)

- **代码位置**: `/home/zrc/develop_item/EmotionalRAG/`
- **核心结构**:
  - 语义向量索引
  - 情感向量索引
- **融合策略**: C-A/C-M/S-C/S-S 四种策略

### 开发任务

- [ ] 定义混合存储接口 `HybridMemoryService`
- [ ] 多索引初始化
- [ ] 多路检索与融合
- [ ] 统一 insert/retrieve 接口适配

### 预估工时: 3 天

______________________________________________________________________

## ✅ DONE-D1-4: `key_value_memory`

> **实现位置**:
> `sage-middleware/src/sage/middleware/components/sage_mem/services/key_value_memory_service.py`
> (595行)

### 概述

键值对存储，支持精确匹配和模糊匹配。

### 小类参数

```yaml
services:
  key_value_memory:
    match_type: "exact"              # exact | fuzzy | semantic
    key_extractor: "entity"          # entity | keyword | custom
    fuzzy_threshold: 0.8             # fuzzy 模式阈值
```

### 参考实现分析

#### LAPS (实体键值)

- **代码位置**: `/home/zrc/develop_item/laps/`
- **核心结构**:
  - 实体名作为 key
  - 相关信息作为 value
- **检索方式**: 精确匹配 + 实体链接

### 开发任务

- [ ] 定义键值存储接口 `KeyValueMemoryService`
- [ ] 实现精确匹配
- [ ] 实现模糊匹配
- [ ] 实现语义匹配
- [ ] 统一 insert/retrieve 接口适配

### 预估工时: 2 天

______________________________________________________________________

## 📋 完成状态

| 优先级 | Action                | 参考工作                               | 状态      |
| ------ | --------------------- | -------------------------------------- | --------- |
| P0     | `graph_memory`        | HippoRAG, A-mem                        | ✅ 已实现 |
| P0     | `hierarchical_memory` | MemoryOS, MemGPT, MemoryBank, LD-Agent | ✅ 已实现 |
| P1     | `hybrid_memory`       | EmotionalRAG                           | ✅ 已实现 |
| P2     | `key_value_memory`    | LAPS                                   | ✅ 已实现 |

**全部完成**: 7/7 后端服务已实现

______________________________________________________________________

*文档创建时间: 2025-01-27*
