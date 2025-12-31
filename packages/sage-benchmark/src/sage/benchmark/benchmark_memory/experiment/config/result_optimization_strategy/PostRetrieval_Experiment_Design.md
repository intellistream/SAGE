# PostRetrieval 结果优化实验设计

> 基于 Dev_Archive.md 中已复现的代表性工作，针对三个记忆体结构设计 PostRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估结果优化策略对最终输出质量的影响
>
> 实验范围：PostRetrieval 阶段（难度★★☆☆☆），固定其他阶段为 baseline 配置

______________________________________________________________________

## 📋 PostRetrieval 策略分类体系

**简化描述（类比 PreRetrieval）**：

- **直接处理**: `none` - 透传检索结果，不做任何处理
- **结果优化**: `rerank.{semantic, time_weighted, ppr, weighted}` - 重新计算分数并精确排序
- **结果过滤**: `filter.{threshold, token_budget}` - 筛选高质量或成本可控的结果
- **结果合并**: `merge.{link_expand, multi_query, multi_tier}` - 融合多个来源的检索结果
- **结果增强**: `augment.{base, reinforce}` - 添加上下文信息或强化记忆

**详细分类表**：

本实验采用以下统一的策略分类标准，按功能类型分类：

| 类别                      | 策略名称               | 功能定位                                  | 适用场景                                    |
| ------------------------- | ---------------------- | ----------------------------------------- | ------------------------------------------- |
| **1. 直接处理**           | `none`                 | 原样透传检索结果，不做任何处理            | Baseline 对照组                             |
| **2. 结果优化 (Rerank)**  | `rerank.semantic`      | 使用 embedding 重新计算语义相似度         | 提升排序精度                                |
|                           | `rerank.time_weighted` | 结合时间衰减因子调整分数                  | 重视时间新鲜度（MemoryBank）                |
|                           | `rerank.ppr`           | 基于图结构的 PageRank 重排序              | 知识图谱场景（HippoRAG）                    |
|                           | `rerank.weighted`      | 多因子综合加权（相似度+时间+重要性+话题） | 复杂决策（LD-Agent）                        |
| **3. 结果过滤 (Filter)**  | `filter.threshold`     | 按相似度阈值过滤低质量结果                | 精准检索（Mem0）                            |
|                           | `filter.token_budget`  | 按 token 预算限制返回数量                 | 控制成本（SCM）                             |
|                           | `filter.top_k`         | 保留 Top-K 结果                           | 基础截断（冗余，已由 MemoryRetrieval 提供） |
| **4. 结果合并 (Merge)**   | `merge.link_expand`    | 扩展图节点的邻居节点                      | 图结构增强（A-Mem）                         |
|                           | `merge.multi_query`    | 融合多个查询的检索结果                    | 多查询场景（MemoryOS）                      |
|                           | `merge.multi_tier`     | 融合多层记忆（Core+Archival+Recall）      | 多层架构（MemGPT）                          |
|                           | `scm_three_way`        | 三路合并（User+Task+Conversation）        | 上下文感知（SCM）                           |
| **5. 结果增强 (Augment)** | `augment`              | 添加 persona/traits/summary 等上下文      | 个性化增强（MemoryBank/MemoryOS）           |
|                           | `augment.reinforce`    | 更新被检索记忆的强度（副作用）            | 记忆强化（MemoryBank）                      |

**分类设计原则**：

- **功能正交**：Rerank（重排序）→ Filter（过滤）→ Merge（合并）→ Augment（增强）四个阶段独立
- **组合友好**：理论上可以组合为 Pipeline（如 `rerank → filter → augment`），但当前 operator.py 只支持单一 action
- **实验友好**：每个类别可独立测试其对最终效果的贡献

**实验优先级**：

1. **核心实验**：直接处理 + 结果优化（Rerank）
1. **扩展实验**：结果过滤（Filter）+ 结果合并（Merge）
1. **高级实验**：结果增强（Augment）

______________________________________________________________________

## ⚠️ 重要架构约束

### 1. 服务依赖约束

| Action              | 依赖的服务类型                    | 约束说明                                                 |
| ------------------- | --------------------------------- | -------------------------------------------------------- |
| `merge.multi_tier`  | `hierarchical_memory`             | ❌ 必须有分层服务（Core/Archival/Recall 或 STM/MTM/LTM） |
| `merge.link_expand` | `graph_memory` 或 `hybrid_memory` | ❌ 必须有图结构，才能扩展邻居节点                        |
| `rerank.ppr`        | `graph_memory` 或 `hybrid_memory` | ❌ 必须有图结构，才能运行 PageRank                       |
| `augment.reinforce` | 支持 `update_memory_strength()`   | ❌ 服务必须实现记忆强化接口                              |

### 2. 当前实现限制

**Operator Pipeline 不支持多 Action 组合**：

```python
# operator.py 第 50-80 行
action_key = config.get("action")  # ❌ 只支持单个 action
action_class = PostRetrievalActionRegistry.get(action_key)
```

**影响**：

- 理想架构：`actions: ["rerank.time_weighted", "filter.threshold", "augment"]`
- 当前实现：只能选择一个 action
- 解决方案：
  - **短期**：每个实验只测试单一 action 的效果
  - **长期**：实现 Pipeline 支持，允许 action 组合

### 3. 代码冗余问题

根据之前的 audit，以下 actions **已实现但未使用**：

| Action                | 代码行数 | 状态                               | 建议                            |
| --------------------- | -------- | ---------------------------------- | ------------------------------- |
| `rerank.semantic`     | 130      | ❌ 未使用                          | 可用于 TiM 精准重排实验         |
| `filter.token_budget` | 100      | ❌ 未使用（SCM 应该用）            | 添加到 SCM 配置                 |
| `filter.top_k`        | 80       | ⚠️ 冗余（与 MemoryRetrieval 重复） | 建议删除                        |
| `augment`             | 187      | ❌ 未使用                          | 添加到 MemoryBank/MemoryOS 实验 |

______________________________________________________________________

## 1. 三个代表性记忆体结构选取

与 PreRetrieval 实验保持一致，选取以下代表性配置：

### 1.1 向量数据库结构 - TiM

**代表工作**: `locomo_tim_pipeline.yaml` **架构特点**: LSH哈希桶 + 向量检索 **PostRetrieval Baseline**:
`action: "none"`（原始向量分数）

**适合测试的 PostRetrieval 策略**：

- `rerank.semantic`: 重新计算精确语义相似度（从 LSH 粗排到精确重排）
- `filter.threshold`: 过滤低相似度结果

### 1.2 多层结构 - MemoryOS

**代表工作**: `locomo_memoryos_pipeline.yaml` **架构特点**: STM/MTM/LTM 三层 **PostRetrieval Baseline**:
`merge.multi_query`（融合 4 个查询的结果）

**适合测试的 PostRetrieval 策略**：

- `merge.multi_query`: 融合多个子查询（当前已使用）
- `rerank.time_weighted`: 时间加权重排序
- `augment`: 添加 persona 信息

### 1.3 图结构 - Mem0ᵍ

**代表工作**: `locomo_mem0g_pipeline.yaml` **架构特点**: 向量 + 知识图谱 **PostRetrieval Baseline**:
`action: "none"`

**适合测试的 PostRetrieval 策略**：

- `merge.link_expand`: 扩展图节点邻居（A-Mem 策略）
- `rerank.ppr`: 图结构 PageRank 重排序（HippoRAG 策略）
- `filter.threshold`: 阈值过滤

______________________________________________________________________

## 2. PostRetrieval 策略候选水平

### 2.1 TiM 系列实验（向量优化）

| 配置ID | 配置文件                                   | 内存名称        | PostRetrieval 策略 | 预期假设                  |
| ------ | ------------------------------------------ | --------------- | ------------------ | ------------------------- |
| **T1** | `TiM_locomo_none_post_retrieval.yaml`      | `TiM-none`      | `none`             | Baseline（原始 LSH 分数） |
| **T2** | `TiM_locomo_semantic_post_retrieval.yaml`  | `TiM-semantic`  | `rerank.semantic`  | 精确重排，提升精度        |
| **T3** | `TiM_locomo_threshold_post_retrieval.yaml` | `TiM-threshold` | `filter.threshold` | 过滤低质量结果            |

**配置示例**：

```yaml
# TiM_locomo_semantic_post_retrieval.yaml
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "semantic"
    similarity_metric: "cosine"
    top_k: 10
```

### 2.2 MemoryOS 系列实验（多层优化）

| 配置ID | 配置文件                                            | 内存名称                 | PostRetrieval 策略     | 预期假设             |
| ------ | --------------------------------------------------- | ------------------------ | ---------------------- | -------------------- |
| **M1** | `MemoryOS_locomo_multi_query_post_retrieval.yaml`   | `MemoryOS-multi_query`   | `merge.multi_query`    | Baseline（当前配置） |
| **M2** | `MemoryOS_locomo_time_weighted_post_retrieval.yaml` | `MemoryOS-time_weighted` | `rerank.time_weighted` | 时间加权，重视新鲜度 |
| **M3** | `MemoryOS_locomo_augment_post_retrieval.yaml`       | `MemoryOS-augment`       | `augment`              | 添加 persona 增强    |

**配置示例**：

```yaml
# MemoryOS_locomo_time_weighted_post_retrieval.yaml
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "time_weighted"
    time_decay_rate: 0.1
    time_weight: 0.5
    score_weight: 0.5
    top_k: 10
```

### 2.3 Mem0ᵍ 系列实验（图结构优化）

| 配置ID | 配置文件                                       | 内存名称            | PostRetrieval 策略  | 预期假设               |
| ------ | ---------------------------------------------- | ------------------- | ------------------- | ---------------------- |
| **G1** | `Mem0g_locomo_none_post_retrieval.yaml`        | `Mem0g-none`        | `none`              | Baseline（原始图检索） |
| **G2** | `Mem0g_locomo_link_expand_post_retrieval.yaml` | `Mem0g-link_expand` | `merge.link_expand` | 扩展邻居节点，增强覆盖 |
| **G3** | `Mem0g_locomo_ppr_post_retrieval.yaml`         | `Mem0g-ppr`         | `rerank.ppr`        | PageRank 重排序        |
| **G4** | `Mem0g_locomo_threshold_post_retrieval.yaml`   | `Mem0g-threshold`   | `filter.threshold`  | 阈值过滤               |

**配置示例**：

```yaml
# Mem0g_locomo_link_expand_post_retrieval.yaml
operators:
  post_retrieval:
    action: "merge"
    merge_type: "link_expand"
    expand_top_n: 5        # 对 Top-5 节点扩展邻居
    max_depth: 1           # 只扩展一层
    max_neighbors: 3       # 每个节点最多 3 个邻居
```

______________________________________________________________________

## 3. 实验设计矩阵

### 3.1 核心对比实验（9 个配置）

| 记忆体结构   | Baseline         | 优化策略1          | 优化策略2      |
| ------------ | ---------------- | ------------------ | -------------- |
| **TiM**      | T1 (none)        | T2 (semantic)      | T3 (threshold) |
| **MemoryOS** | M1 (multi_query) | M2 (time_weighted) | M3 (augment)   |
| **Mem0ᵍ**    | G1 (none)        | G2 (link_expand)   | G3 (ppr)       |

### 3.2 扩展实验（高级策略）

#### 3.2.1 复杂 Rerank 策略

| 配置ID | 模型       | 策略                                         | 配置文件                                          |
| ------ | ---------- | -------------------------------------------- | ------------------------------------------------- |
| **E1** | LD-Agent   | `rerank.weighted`                            | `LDAgent_locomo_weighted_post_retrieval.yaml`     |
| **E2** | MemoryBank | `rerank.time_weighted` + `augment.reinforce` | `MemoryBank_locomo_reinforce_post_retrieval.yaml` |

**E1 配置**（多因子加权）：

```yaml
# LDAgent_locomo_weighted_post_retrieval.yaml
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "weighted"
    factors:
      - name: "relevance"
        weight: 0.4
        source: "similarity"
      - name: "recency"
        weight: 0.3
        decay_type: "exponential"
        decay_rate: 0.1
      - name: "topic_overlap"
        weight: 0.3
        source: "keyword_jaccard"
```

**E2 配置**（时间加权 + 记忆强化）：

```yaml
# MemoryBank_locomo_reinforce_post_retrieval.yaml
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "time_weighted"
    time_decay_rate: 0.1
    time_weight: 0.5
    score_weight: 0.5
    top_k: 10
    # 记忆强化（副作用）
    enable_reinforcement: true
    reinforcement_increment: 1.0
    reinforcement_reset_time: true
```

⚠️ **注意**：E2 的 `reinforce` 功能已重构为独立的 `augment.reinforce` action，但因 operator.py 不支持
pipeline，暂时保留内嵌逻辑。

#### 3.2.2 多层融合策略

| 配置ID | 模型   | 策略               | 配置文件                                       |
| ------ | ------ | ------------------ | ---------------------------------------------- |
| **E3** | MemGPT | `merge.multi_tier` | `MemGPT_locomo_multi_tier_post_retrieval.yaml` |
| **E4** | SCM    | `scm_three_way`    | `SCM_locomo_three_way_post_retrieval.yaml`     |

**E3 配置**（三层融合 + RRF）：

```yaml
# MemGPT_locomo_multi_tier_post_retrieval.yaml
operators:
  post_retrieval:
    action: "merge"
    merge_type: "multi_tier"
    tier_mapping:
      core: "core_memory"
      archival: "archival_memory"
      recall: "recall_memory"
    fusion_method: "rrf"
    rrf_k: 60
    enable_memory_pressure_warning: true
    pressure_threshold: 0.8
```

**E4 配置**（三路合并）：

```yaml
# SCM_locomo_three_way_post_retrieval.yaml
operators:
  post_retrieval:
    action: "scm_three_way"
    user_memory_weight: 0.4
    task_memory_weight: 0.3
    conversation_memory_weight: 0.3
    max_history_tokens: 2500
```

______________________________________________________________________

## 4. 实验对比维度

### 4.1 基础 vs 优化策略

**问题**：PostRetrieval 优化是否有效提升最终输出质量？

| 对比组   | Baseline         | 优化策略           | 预期提升           |
| -------- | ---------------- | ------------------ | ------------------ |
| TiM      | T1 (none)        | T2 (semantic)      | 精确重排提升 5-10% |
| MemoryOS | M1 (multi_query) | M2 (time_weighted) | 时间加权提升新鲜度 |
| Mem0ᵍ    | G1 (none)        | G2 (link_expand)   | 邻居扩展提升覆盖率 |

### 4.2 不同优化策略对比

**问题**：哪种优化策略最有效？

| 对比维度        | 对比组                                                  | 关注指标         |
| --------------- | ------------------------------------------------------- | ---------------- |
| **Rerank 策略** | T2 (semantic) vs M2 (time_weighted) vs E1 (weighted)    | 排序精度         |
| **Filter 策略** | T3 (threshold) vs G4 (threshold)                        | 精准率 vs 召回率 |
| **Merge 策略**  | M1 (multi_query) vs G2 (link_expand) vs E3 (multi_tier) | 结果多样性       |

### 4.3 结构特异性分析

**问题**：特定策略是否只在特定结构下有效？

| 结构                     | 最优策略                                      | 原因                |
| ------------------------ | --------------------------------------------- | ------------------- |
| **向量数据库**（TiM）    | `rerank.semantic`                             | LSH 粗排 → 精确重排 |
| **多层结构**（MemoryOS） | `merge.multi_query` 或 `rerank.time_weighted` | 多层融合或时间感知  |
| **图结构**（Mem0ᵍ）      | `merge.link_expand` 或 `rerank.ppr`           | 图结构优势          |

______________________________________________________________________

## 5. 固定配置（确保公平对比）

### 5.1 其他阶段配置（Baseline）

```yaml
operators:
  pre_retrieval:
    action: "embedding"  # 统一使用基础向量化

  pre_insert:
    action: "none"

  post_insert:
    action: "none"
```

### 5.2 统一运行时配置

```yaml
runtime:
  dataset: "locomo"
  test_segments: 10
  memory_insert_verbose: false
  memory_test_verbose: true

  # LLM 配置（统一）
  api_key: "token-abc123"
  base_url: "http://sage2:8000/v1"
  model_name: "/home/cyb/Llama-3.1-8B-Instruct"
  max_tokens: 256
  temperature: 0
  seed: 42

  # Embedding 配置（统一）
  embedding_base_url: "http://localhost:8091/v1"
  embedding_model: "BAAI/bge-m3"
```

### 5.3 MemoryRetrieval 配置（统一）

```yaml
operators:
  memory_retrieval:
    top_k: 50              # 初始检索 50 条
    retrieval_method: "hybrid"  # 混合检索
    vector_weight: 0.7
    fts_weight: 0.3
```

⚠️ **注意**：PostRetrieval 的 `top_k` 参数（如 `rerank.semantic.top_k: 10`）会进一步截断结果。

______________________________________________________________________

## 6. 评估指标

### 6.1 主要指标

| 指标                      | 说明         | 计算方式              |
| ------------------------- | ------------ | --------------------- |
| **Accuracy**              | 答案准确率   | 正确答案数 / 总问题数 |
| **Response Quality**      | 回答质量评分 | LLM 评估（1-5分）     |
| **Retrieval Precision@K** | 检索精准率   | 相关记忆数 / K        |

### 6.2 次要指标

| 指标                       | 说明                             |
| -------------------------- | -------------------------------- |
| **Average Retrieval Time** | 平均检索时间（含 PostRetrieval） |
| **Result Diversity**       | 结果多样性（去重率）             |
| **Memory Coverage**        | 记忆覆盖率（使用的记忆条目比例） |

### 6.3 效率指标

| 指标                      | 关注策略                                |
| ------------------------- | --------------------------------------- |
| **PostRetrieval Latency** | `rerank.weighted`, `rerank.ppr`         |
| **LLM Call Count**        | `augment`                               |
| **Service Call Count**    | `merge.multi_tier`, `merge.link_expand` |

______________________________________________________________________

## 7. 预期实验结果假设

### 7.1 结构特异性假设

| 记忆体结构   | 最优策略            | 理由                         |
| ------------ | ------------------- | ---------------------------- |
| **TiM**      | `rerank.semantic`   | LSH 哈希桶的粗排需要精确重排 |
| **MemoryOS** | `merge.multi_query` | 多查询融合利用分层优势       |
| **Mem0ᵍ**    | `merge.link_expand` | 图结构的邻居扩展增强关联     |

### 7.2 通用策略假设

- **时间加权**（`rerank.time_weighted`）在所有结构下都能提升时间敏感任务的表现
- **阈值过滤**（`filter.threshold`）在精准检索场景下有效，但可能降低召回率
- **复杂策略收益递减**：简单场景下 `rerank.semantic` 足够，复杂场景需要 `rerank.weighted`

### 7.3 效率与效果权衡

| 策略                | 效果提升 | 延迟增加                   | 适用场景 |
| ------------------- | -------- | -------------------------- | -------- |
| `rerank.semantic`   | +5-10%   | 低                         | 精准重排 |
| `rerank.weighted`   | +10-15%  | 中                         | 复杂决策 |
| `rerank.ppr`        | +15-20%  | 高                         | 图推理   |
| `merge.link_expand` | +10-15%  | 中                         | 图扩展   |
| `augment`           | +5-10%   | 低（无 LLM）/ 高（有 LLM） | 个性化   |

______________________________________________________________________

## 8. 配置文件命名规范

```
<MemoryStructure>_locomo_<strategy>_post_retrieval.yaml

例如：
- TiM_locomo_none_post_retrieval.yaml
- TiM_locomo_semantic_post_retrieval.yaml
- MemoryOS_locomo_time_weighted_post_retrieval.yaml
- Mem0g_locomo_link_expand_post_retrieval.yaml
```

______________________________________________________________________

## 9. 未来扩展：Pipeline 支持

### 9.1 理想架构

当 operator.py 实现 Pipeline 支持后，可以组合多个 actions：

```yaml
operators:
  post_retrieval:
    actions:
      - type: "rerank.time_weighted"
        config:
          time_decay_rate: 0.1
          time_weight: 0.5
          score_weight: 0.5

      - type: "filter.threshold"
        config:
          min_score: 0.5

      - type: "augment"
        config:
          augment_type: "persona"
          position: "before"
```

### 9.2 组合实验设计

| 组合ID | Pipeline                                                      | 预期效果               |
| ------ | ------------------------------------------------------------- | ---------------------- |
| **P1** | `rerank.time_weighted` → `filter.threshold`                   | 时间加权 + 质量过滤    |
| **P2** | `rerank.semantic` → `augment`                                 | 精确重排 + 个性化增强  |
| **P3** | `merge.multi_query` → `rerank.weighted` → `augment.reinforce` | 多查询 + 多因子 + 强化 |

______________________________________________________________________

## 10. 下一步实施计划

### Phase 1: 核心对比实验（9 个配置）

1. **TiM 系列**：T1, T2, T3
1. **MemoryOS 系列**：M1, M2, M3
1. **Mem0ᵍ 系列**：G1, G2, G3

**预期时间**：1-2 天（每个配置运行 10 segments）

### Phase 2: 扩展实验（4 个配置）

4. **复杂 Rerank**：E1 (weighted), E2 (reinforce)
1. **多层融合**：E3 (multi_tier), E4 (scm_three_way)

**预期时间**：1 天

### Phase 3: 数据分析与报告

- 生成对比表格（Accuracy, Precision@K, Latency）
- 绘制策略效果热力图
- 撰写 PostRetrieval 策略效果报告

**预期时间**：0.5 天

### Phase 4: 代码优化（可选）

- 实现 operator.py 的 Pipeline 支持
- 清理冗余代码（`filter.top_k`）
- 完善 `rerank.ppr` 实现

**预期时间**：1-2 天

______________________________________________________________________

## 11. 与 PreRetrieval 实验的协同

### 11.1 两阶段独立测试

- **PreRetrieval**：固定 `post_retrieval: "none"`
- **PostRetrieval**：固定 `pre_retrieval: "embedding"`

### 11.2 最优组合测试

在两阶段实验完成后，组合最优策略：

| 记忆体   | 最优 PreRetrieval          | 最优 PostRetrieval  | 组合配置                            |
| -------- | -------------------------- | ------------------- | ----------------------------------- |
| TiM      | `optimize.expand`          | `rerank.semantic`   | `TiM_optimal_combination.yaml`      |
| MemoryOS | `enhancement.route`        | `merge.multi_query` | `MemoryOS_optimal_combination.yaml` |
| Mem0ᵍ    | `optimize.keyword_extract` | `merge.link_expand` | `Mem0g_optimal_combination.yaml`    |

### 11.3 全局最优搜索（终极目标）

当 Pipeline 支持实现后，可以进行组合爆炸式搜索：

```
PreRetrieval × PostRetrieval = 6 × 5 = 30 组合
（每个阶段选 5-6 个代表性策略）
```

______________________________________________________________________

## 总结

通过这个实验设计，我们可以：

1. **系统评估** PostRetrieval 策略在不同记忆体结构下的效果
1. **识别最优策略** 针对每种结构找到最有效的优化方法
1. **理解权衡** 效果提升 vs 延迟增加 vs 实现复杂度
1. **为组合实验奠定基础** 与 PreRetrieval 协同，探索全局最优配置

**实验难度**：★★☆☆☆（中等，需要理解各策略的适用场景）

**预期收益**：PostRetrieval 优化可带来 **5-20%** 的准确率提升，是性价比最高的优化阶段之一。
