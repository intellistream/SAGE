# PreRetrieval 查询形塑实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，针对三个记忆体结构设计 PreRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估查询优化策略对检索准确率的影响
>
> 实验范围：PreRetrieval 阶段（难度★☆☆☆☆），固定其他阶段为 baseline 配置

______________________________________________________________________

## ⚠️ 重要架构约束

### PreRetrieval `action: "none"` vs `action: "embedding"`

**关键发现**: 并非所有记忆体都支持 `action: "none"` 作为 baseline。

| 记忆体结构                         | Baseline 配置         | 约束说明                                                                                                                             |
| ---------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **TiM** (vector_hash_memory)       | `action: "embedding"` | ❌ **不能** 使用 `none`。TiM 的 `VectorHashMemoryService.retrieve()` 必须接收 `query_embedding`，如果 `vector=None` 会直接返回空结果 |
| **MemoryOS** (hierarchical_memory) | `action: "none"`      | ✅ 可以使用 `none`。服务支持文本查询（FIFO检索）和向量查询（语义检索）                                                               |
| **Mem0ᵍ** (hybrid_memory)          | `action: "none"`      | ✅ 可以使用 `none`。图检索可以不依赖向量，使用文本匹配起始节点                                                                       |

**代码依据**:

```python
# VectorHashMemoryService.retrieve() - Line 216
if vector is None:
    return []  # TiM 必须有向量！
```

**实验影响**:

- TiM 的 baseline 必须使用 `action: "embedding"`，表示"仅做基础向量化，不做任何优化"
- MemoryOS 和 Mem0ᵍ 可以使用 `action: "none"`，表示"原样透传查询"

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

## 2. PreRetrieval 策略候选水平 (TiM 系列)

针对 TiM 记忆体结构，已实现以下 6 个 PreRetrieval 策略：

### 2.1 Baseline: `embedding`

- **配置文件**: `TiM_locomo_embedding_pre_retrieval_pipeline.yaml`
- **内存名称**: `TiM-embedding`
- **操作**: 基础向量化，无任何优化
- **说明**: TiM 必须生成 query_embedding，这是最基础的 baseline
- **配置**:

```yaml
pre_retrieval:
  action: "embedding"  # 基础向量化，无任何优化
```

### 2.2 查询验证: `validate`

- **配置文件**: `TiM_locomo_validate_pre_retrieval_pipeline.yaml`
- **内存名称**: `TiM-validate`
- **操作**: 验证查询合法性，过滤无效查询
- **配置**:

```yaml
pre_retrieval:
  action: "validate"
  validate:
    check_empty: true
    check_length: true
    min_length: 3
    max_length: 500
```

### 2.3 关键词提取: `optimize.keyword_extract`

- **配置文件**: `TiM_locomo_keyword_extract_pre_retrieval_pipeline.yaml`
- **内存名称**: `TiM-keyword_extract`
- **操作**: 提取关键词，配合三元组检索
- **配置**:

```yaml
pre_retrieval:
  action: "optimize.keyword_extract"
  max_keywords: 6
  min_keyword_length: 3
  extract_entities: true
  entity_types: ["PERSON", "ORG", "GPE", "EVENT", "CONCEPT"]
```

### 2.4 查询扩展: `optimize.expand`

- **配置文件**: `TiM_locomo_expand_pre_retrieval_pipeline.yaml`
- **内存名称**: `TiM-expand`
- **操作**: 扩展同义词和相关实体，增强三元组召回
- **配置**:

```yaml
pre_retrieval:
  action: "optimize.expand"
  max_keywords: 6
  expand_synonyms: true
  expand_related_entities: true
```

### 2.5 查询改写: `optimize.rewrite`

- **配置文件**: `TiM_locomo_rewrite_pre_retrieval_pipeline.yaml`
- **内存名称**: `TiM-rewrite`
- **操作**: 通过 LLM 重写查询，增强语义表达
- **配置**:

```yaml
pre_retrieval:
  action: "optimize.rewrite"
  rewrite_style: "semantic_enhance"
  max_rewrites: 1
```

### 2.6 查询分解: `enhancement.decompose`

- **配置文件**: `TiM_locomo_decompose_pre_retrieval_pipeline.yaml`
- **内存名称**: `TiM-decompose`
- **操作**: 将复杂查询分解为多个子查询，适合多跳三元组检索
- **配置**:

```yaml
pre_retrieval:
  action: "enhancement.decompose"
  decompose:
    max_sub_queries: 3
    strategy: "sequential"
```

______________________________________________________________________

## 3. TiM 实验设计矩阵

### 3.1 TiM 实验组合 (6 个配置)

| 配置ID | 配置文件                                                 | 内存名称              | PreRetrieval 策略          | 预期假设                                     |
| ------ | -------------------------------------------------------- | --------------------- | -------------------------- | -------------------------------------------- |
| **T1** | `TiM_locomo_embedding_pre_retrieval_pipeline.yaml`       | `TiM-embedding`       | `embedding`                | 向量哈希检索基线（必须生成 query_embedding） |
| **T2** | `TiM_locomo_validate_pre_retrieval_pipeline.yaml`        | `TiM-validate`        | `validate`                 | 过滤无效查询，提升检索质量                   |
| **T3** | `TiM_locomo_keyword_extract_pre_retrieval_pipeline.yaml` | `TiM-keyword_extract` | `optimize.keyword_extract` | 提取关键词，配合三元组检索                   |
| **T4** | `TiM_locomo_expand_pre_retrieval_pipeline.yaml`          | `TiM-expand`          | `optimize.expand`          | 扩展同义词，增强三元组召回                   |
| **T5** | `TiM_locomo_rewrite_pre_retrieval_pipeline.yaml`         | `TiM-rewrite`         | `optimize.rewrite`         | 语义重写，提升向量匹配                       |
| **T6** | `TiM_locomo_decompose_pre_retrieval_pipeline.yaml`       | `TiM-decompose`       | `enhancement.decompose`    | 查询分解，支持多跳三元组检索                 |

### 3.2 实验对比维度

#### 3.2.1 基础 vs 优化策略

- **T1 (embedding)** vs **T3/T4/T5** - 评估不同优化策略的效果
- 预期：T4 (expand) 和 T5 (rewrite) 在复杂查询上表现更好

#### 3.2.2 简单优化 vs 高级优化

- **T3 (keyword_extract)** vs **T4 (expand)** - 关键词提取 vs 扩展
- **T4 (expand)** vs **T5 (rewrite)** - 同义词扩展 vs 语义改写
- 预期：T5 (rewrite) 在需要理解上下文的查询上效果最好

#### 3.2.3 单查询 vs 多查询

- **T5 (rewrite)** vs **T6 (decompose)** - 改写单个查询 vs 分解为多个子查询
- 预期：T6 (decompose) 在多跳推理任务上表现更好

### 3.3 固定配置 (所有实验统一)

所有 TiM 实验共享以下固定配置，确保公平对比：

```yaml
# 服务配置
services:
  register_memory_service: "vector_memory"
  vector_memory:
    dim: 1024
    index_type: "IndexLSH"
    index_config:
      nbits: 128
      rotate_data: true

# Operator 配置
operators:
  # PreInsert: TiM 三元组提取
  pre_insert:
    action: "extract.triple"
    extraction_method: "llm"
    max_triplets: 10
    keep_original: false

  # PostInsert: TiM 蒸馏
  post_insert:
    action: "distillation"
    retrieve_count: 10
    min_merge_count: 5

  # PostRetrieval: TiM rerank
  post_retrieval:
    action: "rerank"
    rerank_type: "semantic"
    top_k: 5
```

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

## 7. Enhancement 高级策略 (扩展实验)

### 7.1 策略说明

Enhancement 类型是 PreRetrieval 的高级查询增强功能，与 `optimize` 类型并列，采用统一的配置方式：

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "decompose"  # decompose | route | multi_embed
```

### 7.2 三个 Enhancement 子类型

#### 7.2.1 Query Decompose - 复杂查询分解

**功能**: 将复杂查询分解为多个独立的子查询，每个子查询可独立检索

**适用场景**:

- 多步推理任务："What did I eat for breakfast and what was the weather?"
- 复杂问题拆解："Compare A and B" → ["Describe A", "Describe B"]

**配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "decompose"
    decompose_strategy: "llm"  # llm | rule | hybrid
    max_sub_queries: 3
    sub_query_action: "parallel"  # parallel | sequential
    embed_sub_queries: true
```

**策略类型**:

- `llm`: 使用 LLM 智能分解（高精度，高延迟）
- `rule`: 基于分隔符规则分解（低延迟，适合简单场景）
- `hybrid`: 先规则后 LLM fallback（平衡方案）

#### 7.2.2 Retrieval Route - 检索路由

**功能**: 根据查询内容生成检索策略提示 (hints)，指导服务层选择合适的检索方式

**适用场景**:

- 多源记忆系统：根据查询类型选择 STM/MTM/LTM
- 条件分支检索："remember" → LTM, "recently" → STM

**配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "route"
    route_strategy: "keyword"  # keyword | classifier | llm
    keyword_rules:
      - keywords: ["remember", "recall"]
        strategy: "long_term_memory"
        params: { tier: "ltm" }
      - keywords: ["recently", "just now"]
        strategy: "short_term_memory"
        params: { tier: "stm" }
    default_strategy: "semantic_search"
```

**策略类型**:

- `keyword`: 基于关键词规则路由（低延迟，规则可控）
- `classifier`: 基于分类器路由（需要训练，暂未实现）
- `llm`: 基于 LLM 智能路由（高灵活性，高延迟）

#### 7.2.3 Multi Embed - 多维向量化

**功能**: 使用多个 embedding 模型生成多维向量，综合多种相似度维度

**适用场景**:

- 精细化检索：语义 + 情感 + 代码特征
- 多模态检索：文本 + 图像 + 音频

**配置示例**:

```yaml
operators:
  pre_retrieval:
    action: "enhancement"
    enhancement_type: "multi_embed"
    embeddings:
      - name: "semantic"
        model: "BAAI/bge-m3"
        weight: 0.6
      - name: "emotion"
        model: "SamLowe/roberta-base-go_emotions"
        weight: 0.4
    output_format: "weighted"  # weighted | dict | concat
```

**输出格式**:

- `weighted`: 加权融合为单一向量（推荐）
- `dict`: 字典格式保留所有向量（供后续处理）
- `concat`: 拼接所有向量（维度倍增）

### 7.3 Enhancement vs Optimize

| 对比维度       | Optimize                         | Enhancement                   |
| -------------- | -------------------------------- | ----------------------------- |
| **定位**       | 查询优化（文本层面）             | 查询增强（结构层面）          |
| **子类型**     | keyword_extract, expand, rewrite | decompose, route, multi_embed |
| **复杂度**     | 中等（单次查询优化）             | 高（多查询/多路由/多向量）    |
| **适用场景**   | 基础查询优化                     | 高级检索增强                  |
| **实验优先级** | 高（核心对比实验）               | 中（扩展实验）                |

### 7.4 Demo 配置文件

Enhancement 类型已提供三个 Demo 配置文件：

| 配置文件                                          | Enhancement 类型 | 记忆体结构 | 说明                   |
| ------------------------------------------------- | ---------------- | ---------- | ---------------------- |
| `pre_retrieval_enhancement_decompose_demo.yaml`   | decompose        | TiM        | 复杂查询分解为子查询   |
| `pre_retrieval_enhancement_route_demo.yaml`       | route            | MemoryOS   | 基于关键词的层级路由   |
| `pre_retrieval_enhancement_multi_embed_demo.yaml` | multi_embed      | Mem0ᵍ      | 语义+代码+情感多维检索 |

**注意**: Enhancement 实验为高级功能演示，**不在核心对比实验范围内**。

______________________________________________________________________

## 8. 下一步实施计划

1. **Phase 1**: 实施 9 个核心对比组合 (V1-V3, H1-H3, G1-G3)
1. **Phase 2**: 基于 Phase 1 结果，扩展到完整的 15 个组合
1. **Phase 3**: （可选）运行 3 个 Enhancement Demo，评估高级策略效果
1. **Phase 4**: 分析结果，撰写 PreRetrieval 策略效果报告
1. **Phase 5**: 基于最优 PreRetrieval 配置，进入下一阶段 PostRetrieval 实验

通过这个实验设计，我们可以系统地评估不同查询优化策略在不同记忆体结构下的效果，为后续的组合实验奠定基础。
