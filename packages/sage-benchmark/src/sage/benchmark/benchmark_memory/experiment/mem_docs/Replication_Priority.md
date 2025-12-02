# 记忆体复现优先级排序

基于学术影响力、实现创新性和与 SAGE 框架的匹配度，给出复现优先级排序。

**核心原则**：大类对应 action 参数，小类由配置参数控制，可模块化复现。

______________________________________________________________________

## 📋 工作五维度 Action 配置总览

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

______________________________________________________________________

## 🏆 复现优先级排序

### Tier 1: 核心工作（必须复现）

#### 1. HippoRAG ⭐⭐⭐⭐⭐

**Action 配置**: `(graph_memory, tri_embed, link_evolution, embedding, rerank)`

| 维度             | Action           | 小类参数                           | 具体实现                               |
| ---------------- | ---------------- | ---------------------------------- | -------------------------------------- |
| D1 Service       | `graph_memory`   | `graph_type: knowledge_graph`      | iGraph 知识图谱 + 三类 Embedding Store |
| D2 PreInsert     | `tri_embed`      | `triple_extraction_prompt: OpenIE` | 三元组抽取 + NER                       |
| D3 PostInsert    | `link_evolution` | `link_policy: synonym_edge`        | 基于 KNN 相似度构建同义边              |
| D4 PreRetrieval  | `embedding`      | `model: NV-Embed-v2`               | 查询向量化                             |
| D5 PostRetrieval | `rerank`         | `rerank_type: ppr`                 | Personalized PageRank                  |

**GitHub**: https://github.com/OSU-NLP-Group/HippoRAG\
**会议**: NeurIPS'24, ICML'25\
**复现价值**: 知识图谱 + PPR 的创新组合，多跳推理 SOTA

**YAML 配置**:

```yaml
services:
  register_memory_service: graph_memory
  graph_memory:
    graph_type: "knowledge_graph"
    edge_policy: "synonym"

operators:
  pre_insert:
    action: tri_embed
    triple_extraction_prompt: "Extract (subject, predicate, object) triples..."
  post_insert:
    action: link_evolution
    link_policy: "synonym_edge"
    knn_k: 10
  pre_retrieval:
    action: embedding
  post_retrieval:
    action: rerank
    rerank_type: "ppr"
    damping_factor: 0.5
```

______________________________________________________________________

#### 2. Generative Agents ⭐⭐⭐⭐⭐

**Action 配置**: `(neuromem_vdb, none, reflection, embedding, rerank)`

| 维度             | Action         | 小类参数                                          | 具体实现                   |
| ---------------- | -------------- | ------------------------------------------------- | -------------------------- |
| D1 Service       | `neuromem_vdb` | `top_k: 100`                                      | 向量数据库存储记忆流       |
| D2 PreInsert     | `none`         | -                                                 | 外部进行重要性评分         |
| D3 PostInsert    | `reflection`   | `trigger_mode: threshold, threshold: 100`         | 累计重要性超阈值触发反思   |
| D4 PreRetrieval  | `embedding`    | `model: text-embedding-3-small`                   | 查询向量化                 |
| D5 PostRetrieval | `rerank`       | `rerank_type: weighted, weights: [0.3, 0.3, 0.4]` | 相关性 × 时间衰减 × 重要性 |

**GitHub**: https://github.com/joonspk-research/generative_agents\
**会议**: UIST'23 (Stanford)\
**复现价值**: 记忆领域奠基性工作，反思机制经典实现

**YAML 配置**:

```yaml
services:
  register_memory_service: neuromem_vdb
  neuromem_vdb:
    collection_name: "agent_memory"
    top_k: 100

operators:
  pre_insert:
    action: none
  post_insert:
    action: reflection
    trigger_mode: "threshold"
    reflection_threshold: 100
    reflection_prompt: "What are 5 most salient high-level questions..."
  pre_retrieval:
    action: embedding
  post_retrieval:
    action: rerank
    rerank_type: "weighted"
    weights: [0.3, 0.3, 0.4]  # recency, importance, relevance
```

______________________________________________________________________

#### 3. MemGPT/Letta ⭐⭐⭐⭐⭐

**Action 配置**: `(hierarchical_memory, transform, distillation, none, none)`

| 维度             | Action                | 小类参数                                         | 具体实现                |
| ---------------- | --------------------- | ------------------------------------------------ | ----------------------- |
| D1 Service       | `hierarchical_memory` | `tier_count: 3, tiers: [core, archival, recall]` | 三层功能分层            |
| D2 PreInsert     | `transform`           | `transform_type: chunking, chunk_size: 512`      | 固定大小文本分块        |
| D3 PostInsert    | `distillation`        | `distillation_prompt: summarize`                 | 超过 Token 阈值自动摘要 |
| D4 PreRetrieval  | `none`                | -                                                | 通过函数调用检索        |
| D5 PostRetrieval | `none`                | `conversation_format_prompt: system template`    | 系统消息模板格式化      |

**GitHub**: https://github.com/cpacker/MemGPT\
**会议**: NeurIPS'23\
**复现价值**: LLM OS 概念开创者，19k+ stars

______________________________________________________________________

### Tier 2: 重要工作（推荐复现）

#### 4. MemoryBank ⭐⭐⭐⭐

**Action 配置**: `(hierarchical_memory, none, forgetting, embedding, none)`

| 维度             | Action                | 小类参数                 | 具体实现                             |
| ---------------- | --------------------- | ------------------------ | ------------------------------------ |
| D1 Service       | `hierarchical_memory` | `tier_count: 2`          | History + Summary + Personality 分层 |
| D2 PreInsert     | `none`                | -                        | 日期+对话内容格式化                  |
| D3 PostInsert    | `forgetting`          | `decay_type: ebbinghaus` | 艾宾浩斯遗忘曲线 + 多层摘要          |
| D4 PreRetrieval  | `embedding`           | -                        | LlamaIndex 查询                      |
| D5 PostRetrieval | `none`                | -                        | 角色信息 + 检索内容模板              |

**GitHub**: https://github.com/zhongwanjun/MemoryBank-SiliconFriend\
**会议**: AAAI'24\
**复现价值**: 心理学启发的遗忘机制

______________________________________________________________________

#### 5. A-mem ⭐⭐⭐⭐

**Action 配置**: `(graph_memory, tri_embed, link_evolution, embedding, merge)`

| 维度             | Action           | 小类参数                           | 具体实现                        |
| ---------------- | ---------------- | ---------------------------------- | ------------------------------- |
| D1 Service       | `graph_memory`   | `graph_type: link_graph`           | Zettelkasten 风格链接图         |
| D2 PreInsert     | `tri_embed`      | `extract_type: keyword_context`    | LLM 提取关键词/标签/上下文      |
| D3 PostInsert    | `link_evolution` | `link_policy: strengthen_neighbor` | strengthen/update_neighbor 操作 |
| D4 PreRetrieval  | `embedding`      | `hybrid: true`                     | BM25 + 语义向量混合             |
| D5 PostRetrieval | `merge`          | `merge_strategy: link_expansion`   | 返回结果及其邻居节点            |

**GitHub**: https://github.com/agiresearch/A-mem\
**复现价值**: Zettelkasten 原则的 AI 应用

______________________________________________________________________

#### 6. MemoryOS ⭐⭐⭐⭐

**Action 配置**: `(hierarchical_memory, none, forgetting, embedding, merge)`

| 维度             | Action                | 小类参数                                | 具体实现                               |
| ---------------- | --------------------- | --------------------------------------- | -------------------------------------- |
| D1 Service       | `hierarchical_memory` | `tier_count: 3, tiers: [stm, mtm, ltm]` | 短期 deque + 中期 FAISS + 长期 Profile |
| D2 PreInsert     | `none`                | -                                       | Embedding 在服务层完成                 |
| D3 PostInsert    | `forgetting`          | `decay_type: lfu, heat_threshold: 0.7`  | 热度超阈值触发 Profile 更新 + LFU 驱逐 |
| D4 PreRetrieval  | `embedding`           | -                                       | 查询向量化                             |
| D5 PostRetrieval | `merge`               | `merge_strategy: multi_tier`            | 三路结果合并 (MTM + User KG + Asst KG) |

**GitHub**: https://github.com/MemoryOS-AI/MemoryOS\
**复现价值**: 完整三层架构 + 热度驱动机制

______________________________________________________________________

### Tier 3: 补充工作（选择复现）

#### 7. SCM4LLMs ⭐⭐⭐

**Action 配置**: `(short_term_memory, none, distillation, embedding, filter)`

| 维度             | Action              | 小类参数                                    | 具体实现                  |
| ---------------- | ------------------- | ------------------------------------------- | ------------------------- |
| D1 Service       | `short_term_memory` | `maxlen: 50`                                | Turn 列表 + 向量          |
| D2 PreInsert     | `none`              | -                                           | 直接存储                  |
| D3 PostInsert    | `distillation`      | `distillation_prompt: hierarchical_summary` | 层次化摘要                |
| D4 PreRetrieval  | `embedding`         | -                                           | 查询向量化                |
| D5 PostRetrieval | `filter`            | `filter_type: token_budget, budget: 2000`   | drop/summary/raw 三元决策 |

**位置**: /home/zrc/develop_item/SCM4LLMs\
**复现价值**: 自控制压缩机制

______________________________________________________________________

#### 8. SeCom ⭐⭐⭐

**Action 配置**: `(neuromem_vdb, transform, distillation, none, none)`

| 维度             | Action         | 小类参数                             | 具体实现              |
| ---------------- | -------------- | ------------------------------------ | --------------------- |
| D1 Service       | `neuromem_vdb` | -                                    | FAISS/Chroma 向量存储 |
| D2 PreInsert     | `transform`    | `transform_type: topic_segmentation` | LLM 驱动话题分段      |
| D3 PostInsert    | `distillation` | `distillation_type: llmlingua`       | LLMLingua-2 压缩      |
| D4 PreRetrieval  | `none`         | -                                    | 分段级检索            |
| D5 PostRetrieval | `none`         | -                                    | 返回原始内容拼接      |

**位置**: /home/zrc/develop_item/SeCom\
**复现价值**: 分段 + 压缩组合

______________________________________________________________________

#### 9. EmotionalRAG ⭐⭐⭐

**Action 配置**: `(neuromem_vdb, tri_embed, none, embedding, merge)`

| 维度             | Action         | 小类参数                                                 | 具体实现                 |
| ---------------- | -------------- | -------------------------------------------------------- | ------------------------ |
| D1 Service       | `neuromem_vdb` | -                                                        | Memory Bank JSON         |
| D2 PreInsert     | `tri_embed`    | `embed_type: multi_aspect, aspects: [semantic, emotion]` | 语义向量 + 情感向量      |
| D3 PostInsert    | `none`         | -                                                        | 无后处理                 |
| D4 PreRetrieval  | `embedding`    | `embed_type: multi_aspect`                               | 双向量查询               |
| D5 PostRetrieval | `merge`        | `merge_strategy: multi_aspect_fusion`                    | C-A/C-M/S-C/S-S 融合策略 |

**位置**: /home/zrc/develop_item/EmotionalRAG\
**复现价值**: 多维向量融合策略

______________________________________________________________________

#### 10. LD-Agent ⭐⭐⭐

**Action 配置**: `(hierarchical_memory, tri_embed, forgetting, optimize, rerank)`

| 维度             | Action                | 小类参数                                    | 具体实现                      |
| ---------------- | --------------------- | ------------------------------------------- | ----------------------------- |
| D1 Service       | `hierarchical_memory` | `tier_count: 2`                             | ChromaDB + 短期列表           |
| D2 PreInsert     | `tri_embed`           | `extract_type: noun_persona`                | spaCy 名词提取 + Persona 提取 |
| D3 PostInsert    | `forgetting`          | `decay_type: time_transfer, interval: 3600` | 会话间隔>1小时触发摘要转存    |
| D4 PreRetrieval  | `optimize`            | `optimize_type: keyword_extract`            | 名词化查询                    |
| D5 PostRetrieval | `rerank`              | `rerank_type: time_weighted`                | 话题重叠 × 时间衰减           |

**位置**: /home/zrc/develop_item/LD-Agent\
**复现价值**: 时间感知的层级迁移

______________________________________________________________________

#### 11. LoCoMo ⭐⭐⭐

**Action 配置**: `(neuromem_vdb, transform, reflection, embedding, summarize)`

| 维度             | Action         | 小类参数                       | 具体实现                         |
| ---------------- | -------------- | ------------------------------ | -------------------------------- |
| D1 Service       | `neuromem_vdb` | -                              | Embedding 存储                   |
| D2 PreInsert     | `transform`    | `transform_type: fact_extract` | 对话转事实条目                   |
| D3 PostInsert    | `reflection`   | `trigger_mode: periodic`       | Session 结束触发 self/other 反思 |
| D4 PreRetrieval  | `embedding`    | -                              | 查询向量化                       |
| D5 PostRetrieval | `summarize`    | `summarize_prompt: integrate`  | 反思内容整合到上下文             |

**位置**: /home/zrc/develop_item/locomo\
**复现价值**: 事实提取 + 双向反思

______________________________________________________________________

## 📅 推荐复现顺序

按维度覆盖度和创新性排序：

```
阶段1 (Week 1-2):  本地项目快速验证
  - SCM4LLMs: 验证 D5-5.3.1 Token Budget Filtering
  - SeCom:    验证 D2-2.2.3 Topic Segmentation + D3-3.2.3 Compression

阶段2 (Week 3-4):  经典反思机制
  - Generative Agents: D2-2.5.1 + D3-3.4.2 + D5-5.2.2 (重要性+反思+时间加权)

阶段3 (Week 5-7):  知识图谱方向
  - HippoRAG: D1-1.3.1 + D2-2.3.1 + D3-3.3.2 + D5-5.2.3 (KG+OpenIE+PPR)

阶段4 (Week 8-10): 分层记忆系统
  - MemGPT:   D1-1.4.3 (功能分层) + D3-3.2.1 (摘要)
  - MemoryOS: D1-1.4.2 (三层) + D3-3.6.2 (热度迁移)

阶段5 (Week 11-12): 遗忘机制
  - MemoryBank: D3-3.5.3 Ebbinghaus Forgetting

阶段6 (Week 13+): 按需补充
  - A-mem:       D1-1.3.2 + D3-3.3.1 (链接图+链接演化)
  - EmotionalRAG: D2-2.4.2 + D4-4.2.2 (多维向量)
  - LD-Agent:    D3-3.6.1 + D4-4.3.1 (时间迁移+名词查询)
```

______________________________________________________________________

## 🎯 Action 实现清单

每个 action 对应代码中的一个分支，参数控制具体行为：

### D1 Memory Service Actions

| Action                | 实现状态  | 参考工作         | 核心参数                         |
| --------------------- | --------- | ---------------- | -------------------------------- |
| `short_term_memory`   | ✅ 已实现 | SCM4LLMs         | `maxlen`                         |
| `vector_hash_memory`  | ✅ 已实现 | -                | `lsh_nbits`, `k_nearest`         |
| `neuromem_vdb`        | ✅ 已实现 | MemGPT, GA       | `collection_name`, `top_k`       |
| `graph_memory`        | ⏳ 待实现 | HippoRAG, A-mem  | `graph_type`, `edge_policy`      |
| `hierarchical_memory` | ⏳ 待实现 | MemoryOS, MemGPT | `tier_count`, `migration_policy` |

### D2 PreInsert Actions

| Action      | 实现状态  | 参考工作      | 核心参数                       |
| ----------- | --------- | ------------- | ------------------------------ |
| `none`      | ✅ 已实现 | -             | -                              |
| `tri_embed` | ✅ 已实现 | HippoRAG      | `triple_extraction_prompt`     |
| `transform` | ⏳ 待实现 | MemGPT, SeCom | `transform_type`, `chunk_size` |
| `validate`  | ⏳ 待实现 | -             | `validation_rules`             |

### D3 PostInsert Actions

| Action           | 实现状态  | 参考工作          | 核心参数                              |
| ---------------- | --------- | ----------------- | ------------------------------------- |
| `none`           | ✅ 已实现 | -                 | -                                     |
| `distillation`   | ✅ 已实现 | SCM4LLMs          | `topk`, `threshold`, `prompt`         |
| `reflection`     | ⏳ 待实现 | Generative Agents | `trigger_mode`, `threshold`, `prompt` |
| `link_evolution` | ⏳ 待实现 | A-mem             | `link_policy`, `strengthen_factor`    |
| `forgetting`     | ⏳ 待实现 | MemoryBank        | `decay_type`, `decay_rate`            |
| `log`            | ✅ 已实现 | -                 | `log_level`                           |
| `stats`          | ✅ 已实现 | -                 | `stats_fields`                        |

### D4 PreRetrieval Actions

| Action      | 实现状态  | 参考工作     | 核心参数                           |
| ----------- | --------- | ------------ | ---------------------------------- |
| `none`      | ✅ 已实现 | -            | -                                  |
| `embedding` | ✅ 已实现 | HippoRAG, GA | `embedding_model`                  |
| `optimize`  | ⏳ 待实现 | LD-Agent     | `optimize_type`, `optimize_prompt` |
| `validate`  | ⏳ 待实现 | -            | `validation_rules`                 |

### D5 PostRetrieval Actions

| Action      | 实现状态  | 参考工作     | 核心参数                           |
| ----------- | --------- | ------------ | ---------------------------------- |
| `none`      | ✅ 已实现 | -            | `conversation_format_prompt`       |
| `rerank`    | ⏳ 待实现 | HippoRAG, GA | `rerank_type`, `weights`           |
| `filter`    | ⏳ 待实现 | SCM4LLMs     | `filter_type`, `token_budget`      |
| `merge`     | ⏳ 待实现 | MemoryOS     | `merge_strategy`, `source_weights` |
| `summarize` | ⏳ 待实现 | LoCoMo       | `summarize_prompt`                 |

______________________________________________________________________

## 📅 推荐复现顺序

按 Action 覆盖度和创新性排序：

```
阶段1 (Week 1-2):  基于已有 action 的验证
  - SCM4LLMs: distillation action + filter action (待实现)
  - 扩展 filter action (token_budget 小类参数)

阶段2 (Week 3-4):  反思机制
  - Generative Agents: 实现 reflection action
    - trigger_mode: threshold | periodic | count
    - reflection_prompt 参数

阶段3 (Week 5-7):  图存储 + PPR
  - HippoRAG:
    - 实现 graph_memory service
    - 实现 link_evolution action
    - 实现 rerank action (ppr 小类)

阶段4 (Week 8-10): 分层存储
  - MemGPT: 实现 hierarchical_memory service (functional tier)
  - MemoryOS: 实现 hierarchical_memory service (stm/mtm/ltm tier)
  - 实现 forgetting action (lfu 小类)

阶段5 (Week 11-12): 遗忘机制
  - MemoryBank: 扩展 forgetting action (ebbinghaus 小类)

阶段6 (Week 13+): 按需补充
  - transform action (chunking, topic_segmentation 小类)
  - optimize action (keyword_extract 小类)
  - merge action (multi_tier, link_expansion 小类)
```

______________________________________________________________________

## 🔧 新增 Action 开发模板

在算子中添加新 action 的标准流程：

```python
# 1. 在 __init__ 中读取 action 和相关参数
def __init__(self, config):
    self.action = config.get("operators.xxx.action", "none")
    if self.action == "new_action":
        self.param1 = config.get("operators.xxx.param1", default_value)
        self.param2 = config.get("operators.xxx.param2", default_value)

# 2. 在 execute 中添加分支
def execute(self, data):
    if self.action == "none":
        return data
    elif self.action == "new_action":
        return self._new_action_handler(data)
    # ...

# 3. 实现具体处理函数
def _new_action_handler(self, data):
    # 使用 self.param1, self.param2 控制行为
    pass
```

______________________________________________________________________

*文档更新时间: 2025-01-27* *维护者: SAGE Team*
