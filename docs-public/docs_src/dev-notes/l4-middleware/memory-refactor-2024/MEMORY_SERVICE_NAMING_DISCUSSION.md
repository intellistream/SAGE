# MemoryService 命名讨论文档

> **目标**：逐个讨论13个配置文件中的记忆体实现，确定其最终命名
>
> **命名原则**：`类别.修饰前缀_索引结构`
>
> - **索引结构**：核心部分（queue, hash, inverted, graph, tier等）
> - **修饰前缀**：可选，说明具体实现（fifo, lsh, bm25, ppr等）
>
> **更新时间**：2025-12-25

______________________________________________________________________

## 一、配置文件清单

### 表格1：原有配置文件映射关系（现状）

| 序号 | 配置文件                               | 当前服务            | 论文/系统  | Collection类型        | 索引后端                 |
| ---- | -------------------------------------- | ------------------- | ---------- | --------------------- | ------------------------ |
| 1    | locomo_short_term_memory_pipeline.yaml | short_term_memory   | -          | VDBMemoryCollection   | FAISS单索引 + FIFO       |
| 2    | locomo_scm_pipeline.yaml               | short_term_memory   | SCM        | VDBMemoryCollection   | FAISS单索引 + FIFO       |
| 3    | locomo_tim_pipeline.yaml               | vector_memory       | TiM        | VDBMemoryCollection   | FAISS LSH索引            |
| 4    | locomo_hipporag_pipeline.yaml          | graph_memory        | HippoRAG   | GraphMemoryCollection | 图索引 + PPR             |
| 5    | locomo_hipporag2_pipeline.yaml         | graph_memory        | HippoRAG2  | GraphMemoryCollection | 图索引 + PPR增强         |
| 6    | locomo_amem_pipeline.yaml              | graph_memory        | A-Mem      | GraphMemoryCollection | 图索引 + 链接演化        |
| 7    | locomo_memorybank_pipeline.yaml        | hierarchical_memory | MemoryBank | HybridCollection      | 3个VDB索引 + 遗忘曲线    |
| 8    | locomo_memoryos_pipeline.yaml          | hierarchical_memory | MemoryOS   | HybridCollection      | 3个VDB索引 + Heat Score  |
| 9    | locomo_ldagent_pipeline.yaml           | hierarchical_memory | LDAgent    | HybridCollection      | 3个VDB索引               |
| 10   | locomo_secom_pipeline.yaml             | hierarchical_memory | SECOM      | HybridCollection      | 3个VDB索引 + 语义分类    |
| 11   | locomo_memgpt_pipeline.yaml            | hierarchical_memory | MemGPT     | HybridCollection      | 3个VDB索引 + Core/Recall |
| 12   | locomo_mem0_pipeline.yaml              | hybrid_memory       | Mem0       | HybridCollection      | VDB + KV混合             |
| 13   | locomo_mem0g_pipeline.yaml             | hybrid_memory       | Mem0ᵍ      | HybridCollection      | VDB + KV + Graph         |

### 表格2：讨论后的命名方案（目标）

| 序号 | 配置文件                 | 新服务名称                                            | 命名规则拆解                                                          | 状态      |
| ---- | ------------------------ | ----------------------------------------------------- | --------------------------------------------------------------------- | --------- |
| 1    | locomo_short_term_memory | `partitional.fifo_queue`                              | partitional + fifo (修饰) + queue (索引)                              | ✅ 已确认 |
| 2    | locomo_scm               | `partitional.fifo_queue`                              | partitional + fifo (修饰) + queue (索引)                              | ✅ 已确认 |
| 3    | locomo_tim               | `partitional.lsh_hash`                                | partitional + lsh (修饰) + hash (索引)                                | ✅ 已确认 |
| 4    | locomo_hipporag          | `hierarchical.semantic_inverted_knowledge_graph`      | hierarchical + semantic_inverted (修饰) + knowledge_graph (索引)      | ✅ 已确认 |
| 5    | locomo_hipporag2         | `hierarchical.semantic_inverted_knowledge_graph`      | hierarchical + semantic_inverted (修饰) + knowledge_graph (索引)      | ✅ 已确认 |
| 6    | locomo_amem              | `hierarchical.linknote_graph`                         | hierarchical + linknote (修饰) + graph (索引)                         | ✅ 已确认 |
| 7    | locomo_memorybank        | `partitional.feature_summary_vectorstore_combination` | partitional + feature_summary_vectorstore (修饰) + combination (索引) | ✅ 已确认 |
| 8    | locomo_memoryos          | `partitional.feature_queue_segment_combination`       | partitional + feature_queue_segment (修饰) + combination (索引)       | ✅ 已确认 |
| 9    | locomo_ldagent           | `partitional.feature_queue_summary_combination`       | partitional + feature_queue_summary (修饰) + combination (索引)       | ✅ 已确认 |
| 10   | locomo_secom             | `partitional.segment`                                 | partitional + segment (索引)                                          | ✅ 已确认 |
| 11   | locomo_memgpt            | `partitional.feature_queue_vectorstore_combination`   | partitional + feature_queue_vectorstore (修饰) + combination (索引)   | ✅ 已确认 |
| 12   | locomo_mem0              | `partitional.inverted_vectorstore_combination`        | partitional + inverted_vectorstore (修饰) + combination (索引)        | ✅ 已确认 |
| 13   | locomo_mem0g             | `hierarchical.property_graph`                         | hierarchical + property (修饰) + graph (索引)                         | ✅ 已确认 |
| 13   | locomo_mem0g             | `hierarchical.property_graph`                         | hierarchical + property (修饰) + graph (索引)                         | ✅ 已确认 |

______________________________________________________________________

## 二、逐个记忆体讨论

### 📌 记忆体 #1-2: STM & SCM

**配置文件**：

- locomo_short_term_memory_pipeline.yaml
- locomo_scm_pipeline.yaml

**当前实现**：

```python
# Collection: VDBMemoryCollection
# 索引: FAISS单索引（IndexFlatL2）
# 特征: FIFO滑动窗口，max_dialog容量限制
# 淘汰策略: 最旧的记忆被挤出
```

**核心特征分析**：

- **索引结构**：队列（queue）
- **组织方式**：FIFO（First-In-First-Out）
- **差异点**：容量大小和是否使用 embedding

______________________________________________________________________

**✅ 已确认命名**：`partitional.fifo_queue`

**决策理由**：

1. ✅ **`queue` 作为索引结构**：队列是一种分区索引方式（按时间顺序分区）
1. ✅ **`fifo` 作为修饰**：明确淘汰策略（先进先出）
1. ✅ **统一实现 STM 和 SCM**：两者本质相同，都是 FIFO 队列，通过配置参数区分行为

**实现特点**：

- **类名**：`FifoQueueMemoryService`
- **实现文件**：`partitional/fifo_queue.py`
- **统一实现 STM 和 SCM**：通过参数区分

**关键差异分析**：

- **STM (Short-Term Memory)**：max_capacity=5，不使用 embedding
- **SCM (Semantic Cache Memory)**：max_capacity=1000，使用 embedding

**统一实现方案**：

```python
class FifoQueueMemoryService(BaseMemoryService):
    """FIFO queue-based partitional memory service.

    Supports both STM (short-term, no embedding) and SCM (semantic cache, with embedding).
    """

    @classmethod
    def from_config(cls, config: RuntimeConfig, config_path: str) -> "FifoQueueMemoryService":
        max_capacity = config.get(f"{config_path}.max_capacity", -1)  # -1 = unlimited
        use_embedding = config.get(f"{config_path}.use_embedding", False)  # false for STM

        if use_embedding:
            # SCM mode: Create embedding-enabled VDBMemoryCollection
            collection = VDBMemoryCollection(
                embedding_dim=config.get(f"{config_path}.embedding_dim", 1024),
                index_type="IndexFlatL2",
                max_capacity=max_capacity
            )
        else:
            # STM mode: Create simple VDBMemoryCollection without embedding pipeline
            collection = VDBMemoryCollection(
                embedding_dim=0,  # No embedding
                index_type="IndexFlatL2",
                max_capacity=max_capacity
            )

        return cls(collection=collection, max_capacity=max_capacity, use_embedding=use_embedding)
```

**配置示例**：

```yaml
# STM 配置（5条容量，无 embedding）
services:
  memory:
    service_name: "partitional.fifo_queue"
    max_capacity: 5
    use_embedding: false

# SCM 配置（1000条容量，有 embedding）
services:
  memory:
    service_name: "partitional.fifo_queue"
    max_capacity: 1000
    use_embedding: true
    embedding_dim: 1024
```

______________________________________________________________________

### 📌 记忆体 #3: TiM

**配置文件**：

- locomo_tim_pipeline.yaml

**当前实现**：

```python
# Collection: VDBMemoryCollection
# 索引: FAISS IndexLSH（局部敏感哈希）
# 特征: LSH哈希桶，快速近似检索
# 配置: nbits=128, rotate_data=True
```

**核心特征分析**：

- **索引结构**：哈希桶（hash bucket）
- **哈希算法**：LSH（Locality-Sensitive Hashing）
- **用途**：TiM论文的快速检索

______________________________________________________________________

**✅ 已确认命名**：`partitional.lsh_hash`

**决策理由**：

1. ✅ **`hash` 作为索引结构**：哈希桶是一种分区索引方式
1. ✅ **`lsh` 作为修饰**：明确使用 LSH（Locality-Sensitive Hashing）算法
1. ✅ **TiM 论文专用**：该实现专门用于 TiM 系统的快速近似检索

**实现特点**：

- **类名**：`LshHashMemoryService`
- **实现文件**：`partitional/lsh_hash.py`
- **FAISS 索引类型**：IndexLSH
- **关键参数**：nbits=128, rotate_data=True

**配置示例**：

```yaml
# TiM 配置
services:
  memory:
    service_name: "partitional.lsh_hash"
    index_type: "IndexLSH"
    nbits: 128
    rotate_data: true
    embedding_dim: 1024
```

______________________________________________________________________

### 📌 记忆体 #4-5: HippoRAG & HippoRAG2

**配置文件**：

- locomo_hipporag_pipeline.yaml (HippoRAG)
- locomo_hipporag2_pipeline.yaml (HippoRAG2)

**当前实现**：

```python
# Collection: GraphMemoryCollection
# 索引: 知识图谱（节点=实体 + 边=关系/同义边）
# 检索算法: PPR (Personalized PageRank)
# 特征:
#   - HippoRAG: 知识图谱 + 同义词边 (ppr_depth=2)
#   - HippoRAG2: 增强PPR (ppr_depth=3, enhanced_rerank=True)
```

**核心特征分析**：

- **索引结构**：知识图谱（knowledge graph）
- **节点**: 实体（entities）
- **边**: 关系（relations）或同义边（synonym edges）
- **特性**: 语义倒排索引（semantic inverted index）

______________________________________________________________________

**✅ 已确认命名**：`hierarchical.semantic_inverted_knowledge_graph`

**决策理由**：

1. ✅ **`knowledge_graph` 作为索引结构**：知识图谱是核心数据结构
1. ✅ **`semantic_inverted` 作为修饰**：
   - `semantic`：通过同义词边建立语义连接
   - `inverted`：实体到记忆的倒排索引
1. ✅ **准确反映图的本质**：区别于 A-Mem 的链接图

**实现特点**：

- **类名**：`SemanticInvertedKnowledgeGraphMemoryService`
- **实现文件**：`hierarchical/semantic_inverted_knowledge_graph.py`
- **统一实现 HippoRAG 和 HippoRAG2**：通过参数区分

**配置示例**：

```yaml
# HippoRAG 配置
services:
  memory:
    service_name: "hierarchical.semantic_inverted_knowledge_graph"
    ppr_depth: 2
    use_synonym_edges: true

# HippoRAG2 配置（增强版）
services:
  memory:
    service_name: "hierarchical.semantic_inverted_knowledge_graph"
    ppr_depth: 3
    enhanced_rerank: true
    use_synonym_edges: true
```

______________________________________________________________________

### 📌 记忆体 #6: A-Mem

**配置文件**：

- locomo_amem_pipeline.yaml (A-Mem)

**当前实现**：

```python
# Collection: GraphMemoryCollection
# 索引: 链接图（节点=记忆条目 + 边=链接演化）
# 检索算法: PPR (Personalized PageRank)
# 特征: 链接笔记图 + 记忆演化
```

**核心特征分析**：

- **索引结构**：链接笔记图（link note graph）
- **节点**: 记忆条目/笔记（memory entries/notes）
- **边**: 链接关系（link evolution）
- **特性**: 记忆演化（evolutionary memory）

______________________________________________________________________

**✅ 已确认命名**：`hierarchical.linknote_graph`

**决策理由**：

1. ✅ **`graph` 作为索引结构**：图索引是核心数据结构
1. ✅ **`linknote` 作为修饰**：强调链接笔记（linked notes）的概念
1. ✅ **区别于知识图谱**：A-Mem 是链接笔记图，不是实体关系图

**实现特点**：

- **类名**：`LinknoteGraphMemoryService`
- **实现文件**：`hierarchical/linknote_graph.py`
- **检索算法**：PPR (Personalized PageRank)
- **特性**：链接演化、记忆条目间的动态连接

**配置示例**：

```yaml
# A-Mem 配置
services:
  memory:
    service_name: "hierarchical.linknote_graph"
    ppr_depth: 2
    graph_type: "link_graph"
    enable_link_evolution: true
```

______________________________________________________________________

______________________________________________________________________

### 📌 记忆体 #7: MemoryBank

**配置文件**：

- locomo_memorybank_pipeline.yaml (MemoryBank - 遗忘曲线)

**当前实现**：

```python
# Collection: 多个 Partitional 组件组合
# 索引结构: 三层 partitional 组织
#   1. 摘要层（Summary Layer）：全局摘要 + 每日事件摘要
#   2. 全局画像层（Global Profile）：用户特征画像
#   3. 历史向量层（History Vector）：KNN 向量索引
# 特征: 特征-摘要-历史三层组合
```

**核心特征分析**：

- **类别**：partitional（三层都是分区索引）
- **索引结构**：combination（组合索引）
- **三层组织**：
  1. **Feature Layer**: 全局画像特征
  1. **Summary Layer**: 摘要（全局摘要 + 每日事件摘要）
  1. **History Layer**: KNN 向量索引
- **特性**：三层独立分区，组合查询

______________________________________________________________________

**✅ 已确认命名**：`partitional.feature_summary_history_combination`

**决策理由**：

1. ✅ **`combination` 作为索引结构**：多个分区索引的组合
1. ✅ **`feature_summary_history` 作为修饰**：准确描述三层结构
   - `feature`: 全局画像层
   - `summary`: 摘要层（全局+每日）
   - `history`: 历史向量层（KNN）
1. ✅ **partitional 类别**：每一层都是独立分区，不是真正的层级关系

**实现特点**：

- **类名**：`FeatureSummaryHistoryCombinationMemoryService`
- **实现文件**：`partitional/feature_summary_history_combination.py`
- **关键技术**：
  - 遗忘曲线：R = e^(-t/S)
  - 多分区组合查询
  - 特征、摘要、历史三维检索

**配置示例**：

```yaml
# MemoryBank 配置
services:
  memory:
    service_name: "partitional.feature_summary_vectorstore_combination"
    enable_global_summary: true
    enable_daily_summary: true
    enable_profile: true
    knn_index_type: "IndexFlatL2"
    forgetting_curve_enabled: true
```

______________________________________________________________________

### 📌 记忆体 #8: MemoryOS

**配置文件**：

- locomo_memoryos_pipeline.yaml (MemoryOS - Heat Score)

**当前实现**：

```python
# Collection: 多个 Partitional 组件组合
# 索引结构: 三层 partitional 组织
#   1. 用户特征层（Feature Layer）：用户画像特征
#   2. FIFO队列层（Queue Layer）：短期对话队列
#   3. 分段-原始对话层（Segment Layer）：对话分段 + 原始记录
# 特征: Heat Score 热度评分（访问次数+交互深度+时间衰减）
```

**核心特征分析**：

- **类别**：partitional（三层都是分区索引）
- **索引结构**：combination（组合索引）
- **三层组织**：
  1. **Feature Layer**: 用户特征画像
  1. **Queue Layer**: FIFO 队列
  1. **Segment Layer**: 分段-原始对话层
- **特性**：Heat Score 热度管理

______________________________________________________________________

**✅ 已确认命名**：`partitional.feature_queue_segment_combination`

**决策理由**：

1. ✅ **`combination` 作为索引结构**：多个分区索引的组合
1. ✅ **`feature_queue_segment` 作为修饰**：准确描述三层结构
   - `feature`: 用户特征层
   - `queue`: FIFO 队列层
   - `segment`: 分段-原始对话层
1. ✅ **partitional 类别**：每一层都是独立分区，不是真正的层级关系

**实现特点**：

- **类名**：`FeatureQueueSegmentCombinationMemoryService`
- **实现文件**：`partitional/feature_queue_segment_combination.py`
- **关键技术**：
  - Heat Score 热度评分
  - 访问次数 + 交互深度 + 时间衰减
  - 多分区组合查询

**配置示例**：

```yaml
# MemoryOS 配置
services:
  memory:
    service_name: "partitional.feature_queue_segment_combination"
    enable_feature_layer: true
    queue_max_capacity: 100
    enable_segment_layer: true
    heat_score_enabled: true
```

______________________________________________________________________

### ✅ 记忆体 #9: LDAgent

**配置文件**: `locomo_ldagent_pipeline.yaml`

**原始实现**:

```python
# Service: HierarchicalMemoryService
# Collection: HybridCollection（三层）
# 特点: 用户特征 + FIFO队列 + 信息摘要
# 所有信息都会进行摘要
```

**✅ 确认命名**: `partitional.feature_queue_summary_combination`

**新实现方案**:

- **文件**:
  `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_services/partitional/feature_queue_summary_combination.py`
- **类名**: `FeatureQueueSummaryCombinationMemoryService`
- **继承**: `BaseMemoryService`
- **核心特性**:
  - 3个独立分区: feature layer + FIFO queue + summary layer
  - 所有记忆信息都会进行摘要处理
  - Partitional combination 模式

**注册示例**:

```python
registry.register(
    "partitional.feature_queue_summary_combination",
    FeatureQueueSummaryCombinationMemoryService
)
```

**配置示例**:

```yaml
# LDAgent 配置
services:
  memory:
    service_name: "partitional.feature_queue_summary_combination"
    enable_feature_layer: true
    queue_max_capacity: 100
    enable_summary_layer: true
    auto_summarize: true
```

______________________________________________________________________

### ✅ 记忆体 #10: SeCom

**配置文件**: `locomo_secom_pipeline.yaml`

**原始实现**:

```python
# Service: HierarchicalMemoryService
# Collection: HybridCollection（三层）
# 特点: 语义段（segment）为基本单元的集合式记忆库
# 每个记忆单元是一个经过压缩去噪、语义连贯、主题一致的对话片段
```

**✅ 确认命名**: `partitional.segment`

**新实现方案**:

- **文件**:
  `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_services/partitional/segment.py`
- **类名**: `SegmentMemoryService`
- **继承**: `BaseMemoryService`
- **核心特性**:
  - 以语义段（segment）为基本单元
  - 每个 segment 是语义连贯、主题一致的对话片段
  - 压缩去噪处理
  - 集合式记忆库（partitional 模式）

**注册示例**:

```python
registry.register(
    "partitional.segment",
    SegmentMemoryService
)
```

**配置示例**:

```yaml
# SeCom 配置
services:
  memory:
    service_name: "partitional.segment"
    enable_compression: true
    enable_denoising: true
    semantic_coherence_threshold: 0.8
    topic_consistency_check: true
```

______________________________________________________________________

### 📌 记忆体 #11: MemGPT

**配置文件**: `locomo_memgpt_pipeline.yaml`

**当前实现**：

```python
# Collection: HybridCollection（单一Collection）
# 索引: 3个VDB索引（stm_index, mtm_index, ltm_index）
# 特征:
#   - Core Memory固定 + Recall Memory淘汰
#   - 层间迁移（remove_from_index + insert_to_index）
```

**核心特征分析**：

- **索引结构**：三层分层（tier）
- **底层技术**：3个VDB索引
- **组织方式**：Core Memory (固定) + Recall Memory (可淘汰)
- **特点**：Core Memory 不会被淘汰，Recall Memory 根据策略淘汰

______________________________________________________________________

### ✅ 记忆体 #11: MemGPT

**配置文件**: `locomo_memgpt_pipeline.yaml`

**原始实现**:

```python
# Service: HierarchicalMemoryService
# Collection: HybridCollection（三层）
# 特点: Core Memory (用户长期事实) + 短期记忆队列 + KNN向量索引
# Core Memory 固定不淘汰，Recall Memory 根据策略淘汰
```

**✅ 确认命名**: `partitional.feature_summary_vectorstore_combination`

**新实现方案**:

- **文件**:
  `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_services/partitional/feature_summary_vectorstore_combination.py`
- **类名**: `FeatureSummaryVectorstoreCombinationMemoryService`
- **继承**: `BaseMemoryService`
- **核心特性**:
  - 3个独立分区: feature layer (用户长期事实) + queue (短期记忆) + vectorstore layer (KNN向量索引,原文+embedding)
  - Core Memory 固定不淘汰
  - Recall Memory 可淘汰
  - Partitional combination 模式

**注册示例**:

```python
registry.register(
    "partitional.feature_queue_vectorstore_combination",
    FeatureQueueVectorstoreCombinationMemoryService
)
```

**配置示例**:

```yaml
# MemGPT 配置
services:
  memory:
    service_name: "partitional.feature_queue_vectorstore_combination"
    enable_feature_layer: true  # Core Memory (用户长期事实)
    queue_max_capacity: 100     # 短期记忆队列
    enable_vectorstore_layer: true  # KNN向量索引(原文+embedding)
    core_memory_fixed: true     # Core Memory 不淘汰
```

______________________________________________________________________

### ✅ 记忆体 #12: Mem0

**配置文件**: `locomo_mem0_pipeline.yaml`

**原始实现**:

```python
# Service: HybridMemoryService
# Collection: HybridCollection
# 特点: 双路索引 - 向量索引 + 倒排索引
# 索引: VDB索引 + KV索引（BM25倒排）
# 融合策略: RRF (Reciprocal Rank Fusion)
```

**✅ 确认命名**: `partitional.inverted_vectorstore_combination`

**新实现方案**:

- **文件**:
  `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_services/partitional/inverted_vectorstore_combination.py`
- **类名**: `InvertedVectorstoreCombinationMemoryService`
- **继承**: `BaseMemoryService`
- **核心特性**:
  - 2个独立分区: inverted index (倒排索引,BM25) + vectorstore layer (向量索引,原文+embedding)
  - 双路索引结构
  - Partitional combination 模式

**注册示例**:

```python
registry.register(
    "partitional.inverted_vectorstore_combination",
    InvertedVectorstoreCombinationMemoryService
)
```

**配置示例**:

```yaml
# Mem0 配置
services:
  memory:
    service_name: "partitional.inverted_vectorstore_combination"
    enable_inverted_index: true  # BM25倒排索引
    enable_vectorstore_layer: true   # 向量索引(原文+embedding)
    fusion_strategy: "rrf"       # Reciprocal Rank Fusion
```

______________________________________________________________________

### ✅ 记忆体 #13: Mem0ᵍ

**配置文件**: `locomo_mem0_graph_pipeline.yaml`

**原始实现**:

```python
# Service: HybridMemoryService
# Collection: HybridCollection
# 特点: 属性图（Property Graph）
# 索引: VDB索引 + KV索引 + Graph索引
# 融合策略: RRF (Reciprocal Rank Fusion)
```

**✅ 确认命名**: `hierarchical.property_graph`

**新实现方案**:

- **文件**:
  `packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_services/hierarchical/property_graph.py`
- **类名**: `PropertyGraphMemoryService`
- **继承**: `BaseMemoryService`
- **核心特性**:
  - 属性图（Property Graph）结构
  - 节点（Nodes）和边（Edges）都可以携带属性（key-value metadata）
  - 边是有向的（A → B ≠ B → A）
  - 边带有标签（关系类型，如 lives_in, prefers）
  - Schema-free 或 weak-schema
  - Hierarchical 模式

**注册示例**:

```python
registry.register(
    "hierarchical.property_graph",
    PropertyGraphMemoryService
)
```

**配置示例**:

```yaml
# Mem0ᵍ 配置
services:
  memory:
    service_name: "hierarchical.property_graph"
    enable_node_properties: true
    enable_edge_properties: true
    directed_edges: true
    schema_mode: "weak"  # weak-schema or schema-free
```

______________________________________________________________________

## 三、命名汇总（全部确认完成 ✅ 13/13）

| 记忆体        | 当前服务            | 确认命名                                                       | 状态      |
| ------------- | ------------------- | -------------------------------------------------------------- | --------- |
| #1-2 短期记忆 | short_term_memory   | ✅ 确认：`partitional.fifo_queue`                              | ✅ 已确认 |
| #3 TiM        | vector_memory       | ✅ 确认：`partitional.lsh_hash`                                | ✅ 已确认 |
| #4-5 HippoRAG | graph_memory        | ✅ 确认：`hierarchical.semantic_inverted_knowledge_graph`      | ✅ 已确认 |
| #6 A-Mem      | graph_memory        | ✅ 确认：`hierarchical.linknote_graph`                         | ✅ 已确认 |
| #7 MemoryBank | hierarchical_memory | ✅ 确认：`partitional.feature_summary_vectorstore_combination` | ✅ 已确认 |
| #8 MemoryOS   | hierarchical_memory | ✅ 确认：`partitional.feature_queue_segment_combination`       | ✅ 已确认 |
| #9 LDAgent    | hierarchical_memory | ✅ 确认：`partitional.feature_queue_summary_combination`       | ✅ 已确认 |
| #10 SeCom     | hierarchical_memory | ✅ 确认：`partitional.segment`                                 | ✅ 已确认 |
| #11 MemGPT    | hierarchical_memory | ✅ 确认：`partitional.feature_queue_vectorstore_combination`   | ✅ 已确认 |
| #12 Mem0      | hybrid_memory       | ✅ 确认：`partitional.inverted_vectorstore_combination`        | ✅ 已确认 |
| #13 Mem0ᵍ     | hybrid_memory       | ✅ 确认：`hierarchical.property_graph`                         | ✅ 已确认 |

______________________________________________________________________

## 四、讨论记录

### 讨论轮次 #1

**时间**：2025-12-25

**讨论内容**：

- 确认命名规则：`类别.修饰前缀_索引结构`
- 修饰前缀可选（如果索引结构本身就足够明确）
- 索引结构是核心，必须有

**已确认**：

1. ✅ **记忆体 #1-2 (ShortTermMemory)**: `partitional.fifo_queue`

   - **决策**：统一 STM 和 SCM 为一个服务，通过配置参数区分
   - **关键参数**：
     - `max_capacity`: 5 (STM) vs 1000 (SCM)
     - `use_embedding`: false (STM) vs true (SCM)
   - **实现文件**：`partitional/fifo_queue.py`
   - **类名**：`FifoQueueMemoryService`

1. ✅ **记忆体 #3 (TiM)**: `partitional.lsh_hash`

   - **决策**：使用 LSH 哈希作为索引结构
   - **关键参数**：
     - `index_type`: IndexLSH
     - `nbits`: 128
     - `rotate_data`: true
   - **实现文件**：`partitional/lsh_hash.py`
   - **类名**：`LshHashMemoryService`

1. ✅ **记忆体 #4-5 (HippoRAG & HippoRAG2)**: `hierarchical.semantic_inverted_knowledge_graph`

   - **决策**：分离出 A-Mem，HippoRAG系列共享一个服务
   - **关键参数**：
     - `ppr_depth`: 2 (HippoRAG) vs 3 (HippoRAG2)
     - `enhanced_rerank`: false (HippoRAG) vs true (HippoRAG2)
     - `use_synonym_edges`: true
   - **实现文件**：`hierarchical/semantic_inverted_knowledge_graph.py`
   - **类名**：`SemanticInvertedKnowledgeGraphMemoryService`

1. ✅ **记忆体 #6 (A-Mem)**: `hierarchical.linknote_graph`

   - **决策**：链接笔记图，区别于知识图谱
   - **关键参数**：
     - `ppr_depth`: 2
     - `graph_type`: link_graph
     - `enable_link_evolution`: true
   - **实现文件**：`hierarchical/linknote_graph.py`
   - **类名**：`LinknoteGraphMemoryService`

1. ✅ **记忆体 #7 (MemoryBank)**: `partitional.feature_summary_vectorstore_combination`

   - **决策**：三层 partitional 组合（特征-摘要-向量存储）
   - **关键参数**：
     - `enable_global_summary`: true
     - `enable_daily_summary`: true
     - `enable_profile`: true
     - `forgetting_curve_enabled`: true
   - **实现文件**：`partitional/feature_summary_vectorstore_combination.py`
   - **类名**：`FeatureSummaryVectorstoreCombinationMemoryService`

1. ✅ **记忆体 #8 (MemoryOS)**: `partitional.feature_queue_segment_combination`

   - **决策**：三层 partitional 组合（特征-队列-分段）
   - **关键参数**：
     - `enable_feature_layer`: true
     - `queue_max_capacity`: 100
     - `enable_segment_layer`: true
     - `heat_score_enabled`: true
   - **实现文件**：`partitional/feature_queue_segment_combination.py`
   - **类名**：`FeatureQueueSegmentCombinationMemoryService`

1. ✅ **记忆体 #9 (LDAgent)**: `partitional.feature_queue_summary_combination`

   - **决策**：三层 partitional 组合（用户特征 + FIFO队列 + 信息摘要）
   - **关键参数**：
     - `enable_feature_layer`: true
     - `queue_max_capacity`: 100
     - `enable_summary_layer`: true
     - `auto_summarize`: true
   - **实现文件**：`partitional/feature_queue_summary_combination.py`
   - **类名**：`FeatureQueueSummaryCombinationMemoryService`

1. ✅ **记忆体 #10 (SeCom)**: `partitional.segment`

   - **决策**：语义段（segment）为基本单元的集合式记忆库
   - **关键参数**：
     - `enable_compression`: true
     - `enable_denoising`: true
     - `semantic_coherence_threshold`: 0.8
     - `topic_consistency_check`: true
   - **实现文件**：`partitional/segment.py`
   - **类名**：`SegmentMemoryService`

1. ✅ **记忆体 #11 (MemGPT)**: `partitional.feature_queue_vectorstore_combination`

   - **决策**：三层 partitional 组合（用户长期事实 + 短期记忆队列 + KNN向量存储）
   - **关键参数**：
     - `enable_feature_layer`: true # Core Memory (用户长期事实)
     - `queue_max_capacity`: 100 # 短期记忆队列
     - `enable_vectorstore_layer`: true # KNN向量存储(原文+embedding)
     - `core_memory_fixed`: true # Core Memory 不淘汰
   - **实现文件**：`partitional/feature_queue_vectorstore_combination.py`
   - **类名**：`FeatureQueueVectorstoreCombinationMemoryService`

1. ✅ **记忆体 #12 (Mem0)**: `partitional.inverted_vectorstore_combination`

- **决策**：双路索引组合（倒排索引 + 向量存储）
- **关键参数**：
  - `enable_inverted_index`: true # 倒排索引（BM25）
  - `enable_vectorstore_layer`: true # 向量存储(原文+embedding)
  - `fusion_strategy`: "rrf" # RRF 融合
- **实现文件**：`partitional/inverted_vectorstore_combination.py`
- **类名**：`InvertedVectorstoreCombinationMemoryService`

11. ✅ **记忆体 #13 (Mem0ᵍ)**: `hierarchical.property_graph`

- **决策**：属性图（Property Graph）结构
- **关键参数**：
  - `enable_node_properties`: true
  - `enable_edge_properties`: true
  - `directed_edges`: true
  - `schema_validation`: "weak" # weak-schema
  - `relation_types`: ["lives_in", "prefers", "knows"]
- **实现文件**：`hierarchical/property_graph.py`
- **类名**：`PropertyGraphMemoryService`

**✅ 全部完成**：13/13 记忆体服务命名已确认

**下一步**： 开始实现 Task 5 - Pipeline 适配和配置迁移

______________________________________________________________________

## 五、备注

- **vector_memory** 的其他用法（非LSH）暂不考虑，因为配置文件中只有TiM在用
- **key_value_memory** 目前没有配置文件在用，可能在后续补充
- 新增类别（如 `temporal`）需要慎重考虑
