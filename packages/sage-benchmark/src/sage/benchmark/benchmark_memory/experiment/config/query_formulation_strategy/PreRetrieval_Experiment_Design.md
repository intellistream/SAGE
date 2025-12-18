# PreRetrieval 查询形塑实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，针对三个记忆体结构设计 PreRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估查询优化策略对检索准确率的影响
>
> 实验范围：PreRetrieval 阶段（难度★☆☆☆☆），固定其他阶段为 baseline 配置

______________________________________________________________________

## 1. 三个代表性记忆体结构选取

基于 Dev_Archive.md 中已复现的工作，选取以下代表性配置：

### 1.1 向量数据库结构 - TiM (Temporal-Induced Memory)

**代表工作**: `locomo_tim_pipeline.yaml`\
**架构特点**: LSH哈希桶 + 向量检索 + 三元组提取\
**服务配置**: `vector_hash_memory`\
**底层引擎**: `VectorHashMemoryService` + LSH索引 + FAISS向量索引

```yaml
services:
  register_memory_service: "vector_hash_memory"
  vector_hash_memory:
    lsh_nbits: 8
    k_nearest: 10
    embedding_dim: 1024
```

**选择理由**: TiM 使用 LSH 哈希桶加速向量相似度检索，是向量数据库的经典实现，便于评估 PreRetrieval 策略对向量检索的优化效果

### 1.2 多层结构 - MemoryOS 分层记忆

**代表工作**: `locomo_memoryos_pipeline.yaml`\
**架构特点**: STM/MTM/LTM 三层 + 热度评分 + 主动迁移\
**服务配置**: `hierarchical_memory`\
**底层引擎**: `HybridCollection` 多层向量集合

```yaml
services:
  register_memory_service: "hierarchical_memory"
  hierarchical_memory:
    tier_mode: "three_tier"
    tier_names: ["stm", "mtm", "ltm"]
    tier_capacities:
      stm: 50
      mtm: 500
      ltm: -1
    migration_policy: "heat"
```

**选择理由**: MemoryOS 是现代化的分层记忆架构，支持基于热度的主动迁移和多维度增强，可验证 PreRetrieval 在复杂分层场景下的优化效果

### 1.3 图结构 - Mem0ᵍ 图记忆版

**代表工作**: `locomo_mem0g_pipeline.yaml`\
**架构特点**: 向量 + 知识图谱 + 实体链接\
**服务配置**: `HybridMemoryService` (图模式)\
**底层引擎**: `GraphMemoryCollection` + 图索引

```yaml
services:
  register_memory_service: "hybrid_memory"
  hybrid_memory:
    graph_enabled: true
    entity_extraction: true
    relation_extraction: true
```

**选择理由**: Mem0ᵍ 结合了语义检索和结构化图检索，可验证 PreRetrieval 在图场景下的实体/关系优化效果

______________________________________________________________________

## 2. PreRetrieval 策略候选水平

基于 Experiment_Design.md 中的五个候选水平，结合三个记忆体结构的特点：

### 2.1 Baseline: `none`

- **操作**: 直接使用原始问题，不做任何优化
- **适用结构**: 全部
- **用途**: 对照基线，验证优化策略的有效性

### 2.2 语义优化: `optimize.rewrite`

- **操作**: 通过 LLM 重写查询，增强语义表达
- **适用结构**: 向量数据库 (STM)、多层结构 (MemoryBank)
- **配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "optimize"
    optimize:
      type: "rewrite"
      rewrite_prompt: "Rewrite the following question to be more specific and detailed for memory retrieval: {question}"
```

### 2.3 关键词扩展: `optimize.expand_keywords`

- **操作**: 提取关键词并扩展同义词，增强召回
- **适用结构**: 图结构 (Mem0ᵍ)、多层结构 (MemoryBank)
- **配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "optimize"
    optimize:
      type: "expand_keywords"
      max_keywords: 5
      expand_synonyms: true
```

### 2.4 纯向量优化: `optimize.embed_only`

- **操作**: 仅优化 embedding，不改变文本查询
- **适用结构**: 向量数据库 (STM)
- **配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "optimize"
    optimize:
      type: "embed_only"
      embedding_enhancement: "normalize_l2"
```

### 2.5 混合提示: `hybrid_hints`

- **操作**: 生成 retrieve_mode/retrieve_params，指导服务层检索策略
- **适用结构**: 多层结构 (MemoryBank)、图结构 (Mem0ᵍ)
- **配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "hybrid_hints"
    hint_types: ["tier_routing", "search_scope", "result_fusion"]
    tier_routing_prompt: "Determine which memory tier(s) to search: STM for recent context, MTM for session memory, LTM for long-term knowledge."
```

______________________________________________________________________

## 3. 实验设计矩阵

### 3.1 实验组合 (3×5=15 个配置)

| 记忆体结构   | Baseline | 语义优化 | 关键词扩展 | 纯向量优化  | 混合提示  |
| ------------ | -------- | -------- | ---------- | ----------- | --------- |
| **TiM**      | ✅       | ✅       | ✅         | ✅          | ❌ 不适用 |
| **MemoryOS** | ✅       | ✅       | ✅         | ✅          | ✅        |
| **Mem0ᵍ**    | ✅       | ✅       | ✅         | ⚠️ 部分适用 | ✅        |

**适用性说明**:

- ✅ **TiM + 关键词扩展**: 三元组提取与关键词扩展相辅相成，可以增强检索召回
- ❌ **TiM + 混合提示**: TiM 是单层哈希桶结构，无需层级路由提示
- ⚠️ **Mem0ᵍ + 纯向量优化**: Mem0ᵍ 主要依赖图检索，纯向量优化收益有限

### 3.2 核心对比组合 (推荐优先测试)

| 组合ID | 记忆体结构 | PreRetrieval 策略          | 预期假设                      |
| ------ | ---------- | -------------------------- | ----------------------------- |
| **V1** | TiM        | `none`                     | 向量哈希检索基线              |
| **V2** | TiM        | `optimize.rewrite`         | 语义重写提升向量匹配          |
| **V3** | TiM        | `optimize.expand_keywords` | 关键词扩展增强三元组检索      |
| **H1** | MemoryOS   | `none`                     | 分层记忆基线                  |
| **H2** | MemoryOS   | `optimize.rewrite`         | 重写查询提升跨层检索          |
| **H3** | MemoryOS   | `hybrid_hints`             | 层级路由+热度感知显著提升效率 |
| **G1** | Mem0ᵍ      | `none`                     | 图记忆基线                    |
| **G2** | Mem0ᵍ      | `optimize.expand_keywords` | 关键词扩展激活实体链接        |
| **G3** | Mem0ᵍ      | `hybrid_hints`             | 向量+图双模式检索             |

______________________________________________________________________

## 4. 实验固定配置

为确保对比公平性，固定以下配置：

### 4.1 其他阶段配置 (Baseline)

```yaml
operators:
  pre_insert:
    action: "none"
  post_insert:
    action: "none"
  post_retrieval:
    action: "none"
```

### 4.2 统一运行时配置

```yaml
runtime:
  dataset: "locomo"
  test_segments: 10
  memory_insert_verbose: false
  memory_test_verbose: true

  # LLM 配置 (统一)
  api_key: "token-abc123"
  base_url: "http://sage2:8000/v1"
  model_name: "/home/cyb/Llama-3.1-8B-Instruct"
  max_tokens: 512
  temperature: 0.3
  seed: 42

  # Embedding 配置 (统一)
  embedding_base_url: "http://localhost:8091/v1"
  embedding_model: "BAAI/bge-m3"
```

### 4.3 评估指标

- **主要指标**: Accuracy (准确率)
- **次要指标**: Retrieval Recall, Response Quality Score
- **效率指标**: Average Retrieval Time, LLM Call Count (for optimize strategies)

______________________________________________________________________

## 5. 配置文件命名规范

```
pre_retrieval_<memory_structure>_<strategy>.yaml

例如:
- pre_retrieval_tim_baseline.yaml
- pre_retrieval_tim_expand_keywords.yaml  
- pre_retrieval_memoryos_hybrid_hints.yaml
- pre_retrieval_mem0g_expand_keywords.yaml
```

______________________________________________________________________

## 6. 预期实验结果假设

### 6.1 结构特异性假设

- **TiM**: `optimize.expand_keywords` 效果最佳，因为关键词扩展可以与三元组提取协同，增强检索召回
- **MemoryOS**: `hybrid_hints` 效果最佳，因为热度感知的层级路由可以显著减少无效检索
- **Mem0ᵍ**: `optimize.expand_keywords` 效果最佳，因为关键词扩展可以激活更多实体关系

### 6.2 通用策略假设

- `optimize.rewrite` 在所有结构下都有稳定提升，因为语义重写是通用的查询优化方法
- 复杂策略的收益递减效应：简单结构下复杂策略收益有限，复杂结构下简单策略不足

### 6.3 效率与效果权衡

- LLM调用的策略 (`rewrite`, `hybrid_hints`) 在提升效果的同时增加延迟
- 需要在准确率提升和响应时间之间找到平衡点

______________________________________________________________________

## 7. 下一步实施计划

1. **Phase 1**: 实施 9 个核心对比组合 (V1-V3, H1-H3, G1-G3)
1. **Phase 2**: 基于 Phase 1 结果，扩展到完整的 15 个组合
1. **Phase 3**: 分析结果，撰写 PreRetrieval 策略效果报告
1. **Phase 4**: 基于最优 PreRetrieval 配置，进入下一阶段 PostRetrieval 实验

通过这个实验设计，我们可以系统地评估不同查询优化策略在不同记忆体结构下的效果，为后续的组合实验奠定基础。
