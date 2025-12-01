# Memory System Taxonomy for LLM Agents

本文档总结了 LLM 记忆系统的五维度分类体系，**与代码实现完全对齐**。

## 📐 核心设计原则

```
大类 = 算子的 action 参数（代码内部的 if-elif 分支）
小类 = 同一 action 下的配置参数（外部 YAML 控制）
```

每个记忆工作可以在五个维度上各选择一个 action，通过参数配置形成具体实现。

---

## 📊 维度一：Memory Datastructure（记忆数据结构）

> **代码位置**: `services/` 目录下的各 Memory Service 实现
> **配置方式**: `services.register_memory_service` 指定服务名

| Action (大类) | 小类参数 | 描述 | 参考项目 |
|---------------|----------|------|----------|
| **short_term_memory** | `maxlen` | 滑动窗口队列（deque） | SCM4LLMs, 基础对话 |
| **vector_hash_memory** | `lsh_nbits`, `k_nearest` | LSH哈希桶 + FAISS向量检索 | HippoRAG, A-mem |
| **neuromem_vdb** | `collection_name`, `top_k` | 向量数据库（VDB）存储 | MemGPT, MemoryBank |
| **graph_memory** | `graph_type`, `edge_policy` | 知识图谱存储 | HippoRAG (KG部分) |
| **hierarchical_memory** | `tier_count`, `migration_policy` | 分层存储（STM/MTM/LTM） | MemoryOS, MemGPT |

### 小类参数详解

```yaml
# short_term_memory 小类参数
services:
  short_term_memory:
    maxlen: 100              # 窗口大小

# vector_hash_memory 小类参数
services:
  vector_hash_memory:
    lsh_nbits: 8             # LSH哈希位数
    k_nearest: 10            # 近邻数量
    embedding_dim: 768       # 向量维度

# neuromem_vdb 小类参数
services:
  neuromem_vdb:
    collection_name: "default"
    top_k: 5
    distance_metric: "cosine"
```

---

## 📊 维度二：PreInsert（记忆前预处理）

> **代码位置**: `libs/pre_insert.py`
> **配置方式**: `operators.pre_insert.action`

| Action (大类) | 小类参数 | 描述 | 参考项目 |
|---------------|----------|------|----------|
| **none** | - | 透传，不做预处理 | 简单对话存储 |
| **tri_embed** | `triple_extraction_prompt` | 三元组抽取 + Embedding | HippoRAG, A-mem |
| **validate** | `validation_rules` | 输入验证/过滤 | 通用 |
| **transform** | `transform_type`, `transform_prompt` | 格式转换/改写 | MemGPT (chunking) |

### 小类参数详解

```yaml
# tri_embed 小类参数
operators:
  pre_insert:
    action: tri_embed
    triple_extraction_prompt: |
      Extract (subject, relation, object) triples from the text...
    embedding_model: "text-embedding-3-small"
    
# transform 小类参数（待实现）
operators:
  pre_insert:
    action: transform
    transform_type: "chunking"      # chunking | summarize | fact_extract
    chunk_size: 512
    chunk_overlap: 50
```

### 代表性工作映射

| 工作 | action | 关键参数 |
|------|--------|----------|
| HippoRAG | `tri_embed` | OpenIE prompt |
| MemGPT | `transform` | chunking |
| Generative Agents | `none` + 外部评分 | importance_prompt |
| A-mem | `tri_embed` | keyword extraction prompt |
| LoCoMo | `transform` | fact_extract |

---

## 📊 维度三：PostInsert（记忆后巩固）

> **代码位置**: `libs/post_insert.py`
> **配置方式**: `operators.post_insert.action`

| Action (大类) | 小类参数 | 描述 | 参考项目 |
|---------------|----------|------|----------|
| **none** | - | 不做后处理 | 简单存储 |
| **distillation** | `topk`, `threshold`, `prompt` | 记忆蒸馏/压缩 | SCM4LLMs, MemGPT |
| **reflection** | `trigger_mode`, `reflection_prompt` | 反思生成 | Generative Agents |
| **link_evolution** | `link_policy`, `strengthen_factor` | 链接演化 | A-mem |
| **forgetting** | `decay_type`, `decay_rate` | 遗忘淘汰 | MemoryBank |
| **log** | `log_level` | 日志记录 | 调试用 |
| **stats** | `stats_fields` | 统计信息 | 分析用 |

### 小类参数详解

```yaml
# distillation 小类参数
operators:
  post_insert:
    action: distillation
    distillation_topk: 5             # 保留前k条
    distillation_threshold: 0.7      # 相关性阈值
    distillation_prompt: |
      Summarize the following memories...

# reflection 小类参数（待实现）
operators:
  post_insert:
    action: reflection
    trigger_mode: "threshold"        # threshold | periodic | count
    reflection_threshold: 100        # 触发阈值
    reflection_prompt: |
      Given the recent experiences, what high-level insights can you infer?

# forgetting 小类参数（待实现）
operators:
  post_insert:
    action: forgetting
    decay_type: "ebbinghaus"         # time_decay | lru | lfu | ebbinghaus
    decay_rate: 0.1
    retention_min: 50                # 最少保留条数
```

### 代表性工作映射

| 工作 | action | 关键参数 |
|------|--------|----------|
| SCM4LLMs | `distillation` | summarization prompt |
| Generative Agents | `reflection` | threshold=100, periodic |
| MemoryBank | `forgetting` | ebbinghaus curve |
| A-mem | `link_evolution` | activate + strengthen |
| MemGPT | `distillation` | archival summarization |

---

## 📊 维度四：PreRetrieval（回忆前预处理）

> **代码位置**: `libs/pre_retrieval.py`
> **配置方式**: `operators.pre_retrieval.action`

| Action (大类) | 小类参数 | 描述 | 参考项目 |
|---------------|----------|------|----------|
| **none** | - | 透传查询 | STM直接检索 |
| **embedding** | `embedding_model` | 查询向量化 | 向量检索必需 |
| **optimize** | `optimize_type`, `optimize_prompt` | 查询优化/改写 | LD-Agent |
| **validate** | `validation_rules` | 查询验证 | 通用 |

### 小类参数详解

```yaml
# embedding 小类参数
operators:
  pre_retrieval:
    action: embedding
    embedding_model: "text-embedding-3-small"
    batch_size: 32

# optimize 小类参数（待实现）
operators:
  pre_retrieval:
    action: optimize
    optimize_type: "keyword_extract"  # keyword_extract | expand | decompose
    optimize_prompt: |
      Extract key nouns from the query...
```

### 代表性工作映射

| 工作 | action | 关键参数 |
|------|--------|----------|
| HippoRAG | `embedding` | query instruction prefix |
| LD-Agent | `optimize` | noun extraction |
| EmotionalRAG | `embedding` | multi-aspect (semantic + emotion) |
| SCM4LLMs | `embedding` | standard |

---

## 📊 维度五：PostRetrieval（回忆后整合）

> **代码位置**: `libs/post_retrieval.py`
> **配置方式**: `operators.post_retrieval.action` + 参数

| Action (大类) | 小类参数 | 描述 | 参考项目 |
|---------------|----------|------|----------|
| **none** | `conversation_format_prompt` | 基础格式化拼接 | 通用基础 |
| **rerank** | `rerank_type`, `rerank_model` | 重排序 | HippoRAG (PPR) |
| **filter** | `filter_type`, `token_budget` | 智能筛选 | SCM4LLMs |
| **merge** | `merge_strategy` | 多源融合 | MemoryOS |
| **summarize** | `summarize_prompt` | 结果摘要 | LoCoMo |

### 小类参数详解

```yaml
# none (基础格式化) 小类参数
operators:
  post_retrieval:
    action: none
    conversation_format_prompt: |
      Below is a conversation between two people...

# rerank 小类参数（待实现）
operators:
  post_retrieval:
    action: rerank
    rerank_type: "ppr"               # semantic | time_weighted | ppr | llm
    rerank_model: "cross-encoder"
    top_k: 10

# filter 小类参数（待实现）
operators:
  post_retrieval:
    action: filter
    filter_type: "token_budget"      # token_budget | threshold | llm
    token_budget: 2000
    relevance_threshold: 0.5

# merge 小类参数（待实现）
operators:
  post_retrieval:
    action: merge
    merge_strategy: "interleave"     # concat | interleave | priority
    source_weights: [0.5, 0.3, 0.2]
```

### 代表性工作映射

| 工作 | action | 关键参数 |
|------|--------|----------|
| HippoRAG | `rerank` | PPR + semantic rerank |
| SCM4LLMs | `filter` | token_budget control |
| Generative Agents | `rerank` | recency * importance * relevance |
| MemoryOS | `merge` | multi-tier parallel |
| LoCoMo | `summarize` | reflection integration |

---

## 📋 代表性工作的五维度 Action 配置

每个工作对应的五维度 action 配置（可直接用于 YAML）：

| 工作 | D1 Service | D2 PreInsert | D3 PostInsert | D4 PreRetrieval | D5 PostRetrieval |
|------|------------|--------------|---------------|-----------------|------------------|
| **HippoRAG** | `graph_memory` | `tri_embed` | `link_evolution` | `embedding` | `rerank` |
| **MemGPT/Letta** | `hierarchical_memory` | `transform` | `distillation` | `none` | `none` |
| **Generative Agents** | `neuromem_vdb` | `none`* | `reflection` | `embedding` | `rerank` |
| **MemoryBank** | `hierarchical_memory` | `none` | `forgetting` | `embedding` | `none` |
| **A-mem** | `graph_memory` | `tri_embed` | `link_evolution` | `embedding` | `merge` |
| **MemoryOS** | `hierarchical_memory` | `none` | `forgetting` | `embedding` | `merge` |
| **SCM4LLMs** | `short_term_memory` | `none` | `distillation` | `embedding` | `filter` |
| **SeCom** | `neuromem_vdb` | `transform` | `distillation` | `none` | `none` |
| **EmotionalRAG** | `neuromem_vdb` | `tri_embed` | `none` | `embedding` | `merge` |
| **LD-Agent** | `hierarchical_memory` | `tri_embed` | `forgetting` | `optimize` | `rerank` |
| **LoCoMo** | `neuromem_vdb` | `transform` | `reflection` | `embedding` | `summarize` |

> *注：Generative Agents 的重要性评分在外部完成，PreInsert 使用 `none`

---

## 📝 YAML 配置示例

### 示例1：复现 HippoRAG

```yaml
services:
  register_memory_service: graph_memory
  graph_memory:
    graph_type: "knowledge_graph"
    edge_policy: "synonym"

operators:
  pre_insert:
    action: tri_embed
    triple_extraction_prompt: |
      Extract all factual triples (subject, predicate, object) from the text.
    embedding_model: "text-embedding-3-small"
  
  post_insert:
    action: link_evolution
    link_policy: "synonym_edge"
    strengthen_factor: 0.1
  
  pre_retrieval:
    action: embedding
    embedding_model: "text-embedding-3-small"
  
  post_retrieval:
    action: rerank
    rerank_type: "ppr"
    damping_factor: 0.5
    top_k: 10
```

### 示例2：复现 Generative Agents

```yaml
services:
  register_memory_service: neuromem_vdb
  neuromem_vdb:
    collection_name: "agent_memory"
    top_k: 100

operators:
  pre_insert:
    action: none
    # 重要性评分在外部 importance_scorer 完成
  
  post_insert:
    action: reflection
    trigger_mode: "threshold"
    reflection_threshold: 100
    reflection_prompt: |
      Given only the information above, what are 5 most salient high-level questions we can answer about the subjects in the statements?
  
  pre_retrieval:
    action: embedding
    embedding_model: "text-embedding-3-small"
  
  post_retrieval:
    action: rerank
    rerank_type: "weighted"
    # score = recency * importance * relevance
    weights: [0.3, 0.3, 0.4]
```

### 示例3：复现 SCM4LLMs

```yaml
services:
  register_memory_service: short_term_memory
  short_term_memory:
    maxlen: 50

operators:
  pre_insert:
    action: none
  
  post_insert:
    action: distillation
    distillation_topk: 10
    distillation_threshold: 0.5
    distillation_prompt: |
      Summarize the key information from the conversation...
  
  pre_retrieval:
    action: embedding
    embedding_model: "text-embedding-3-small"
  
  post_retrieval:
    action: filter
    filter_type: "token_budget"
    token_budget: 2000
```

---

## 🔗 参考项目地址

| 工作 | GitHub | 论文 | Stars |
|------|--------|------|-------|
| HippoRAG | [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | NeurIPS'24, ICML'25 | 3k+ |
| MemGPT/Letta | [cpacker/MemGPT](https://github.com/cpacker/MemGPT) | NeurIPS'23 | 19k+ |
| Generative Agents | [joonspk-research/generative_agents](https://github.com/joonspk-research/generative_agents) | UIST'23 | 20k+ |
| MemoryBank | [zhongwanjun/MemoryBank-SiliconFriend](https://github.com/zhongwanjun/MemoryBank-SiliconFriend) | AAAI'24 | 500+ |
| A-mem | [agiresearch/A-mem](https://github.com/agiresearch/A-mem) | 2024 | 200+ |
| MemoryOS | [MemoryOS-AI/MemoryOS](https://github.com/MemoryOS-AI/MemoryOS) | 2024 | 300+ |
| SCM4LLMs | 本地 /home/zrc/develop_item/SCM4LLMs | ACL'24 | - |
| SeCom | 本地 /home/zrc/develop_item/SeCom | 2024 | - |
| EmotionalRAG | 本地 /home/zrc/develop_item/EmotionalRAG | 2024 | - |
| LD-Agent | 本地 /home/zrc/develop_item/LD-Agent | 2024 | - |
| LoCoMo | 本地 /home/zrc/develop_item/locomo | 2024 | - |
| MemEngine | [nuster1128/MemEngine](https://github.com/nuster1128/MemEngine) | 2024 | 100+ |

---

## 🛠️ 待实现 Action 列表

| 维度 | Action | 优先级 | 参考工作 |
|------|--------|--------|----------|
| D1 | `graph_memory` | P0 | HippoRAG, A-mem |
| D1 | `hierarchical_memory` | P1 | MemoryOS, MemGPT |
| D2 | `transform` | P0 | MemGPT, SeCom |
| D3 | `reflection` | P0 | Generative Agents |
| D3 | `link_evolution` | P1 | A-mem |
| D3 | `forgetting` | P1 | MemoryBank |
| D4 | `optimize` | P1 | LD-Agent |
| D5 | `rerank` | P0 | HippoRAG, GA |
| D5 | `filter` | P0 | SCM4LLMs |
| D5 | `merge` | P1 | MemoryOS |
| D5 | `summarize` | P2 | LoCoMo |

---

*文档更新时间: 2025-01-27*
*维护者: SAGE Team*
