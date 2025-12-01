# D5: PostRetrieval 开发 TODO

## 📌 任务交接说明

**负责人**: _待分配_\
**预估工时**: 22 人天\
**依赖**: D1 Memory Service（`merge` 和 `augment` 需要与存储层交互）\
**交付物**: `libs/post_retrieval.py` 中的新 action 分支实现

本维度负责**记忆检索后的结果整合**，是用户最终看到的记忆上下文的关键处理环节。你需要实现 6 种新的 action：重排序、筛选、多源融合、结果增强、内容压缩、格式化输出。其中 `rerank`
和 `merge` 是核心功能，直接影响最终生成质量。

**开发前请阅读**:

- 现有实现参考: `post_retrieval.py` 中的 `_format_dialog_history` 方法
- 输出要求: 最终需要生成 `history_text` 字段供下游使用
- 重排序: `ppr` 需要与图存储联动，`weighted` 需要多因子计算

**验收标准**:

- [ ] `rerank` 的各种策略（PPR、weighted、cross-encoder）正确工作
- [ ] `filter` 的 token budget 控制精确
- [ ] `merge` 能正确融合多源结果
- [ ] 最终输出格式符合下游 LLM 的输入要求

______________________________________________________________________

> **代码位置**: `libs/post_retrieval.py` **配置键**: `operators.post_retrieval.action` **职责**:
> 记忆检索后的结果整合（重排序、筛选、融合、摘要）

______________________________________________________________________

## 📊 Action 总览

| Action     | 状态      | 小类参数                     | 参考工作                              |
| ---------- | --------- | ---------------------------- | ------------------------------------- |
| `none`     | ✅ 已实现 | `conversation_format_prompt` | 基础格式化                            |
| `rerank`   | ⏳ 待实现 | 见下文                       | HippoRAG, Generative Agents, LD-Agent |
| `filter`   | ⏳ 待实现 | 见下文                       | SCM4LLMs                              |
| `merge`    | ⏳ 待实现 | 见下文                       | MemoryOS, EmotionalRAG, A-mem         |
| `augment`  | ⏳ 待实现 | 见下文                       | LoCoMo, Generative Agents             |
| `compress` | ⏳ 待实现 | 见下文                       | SeCom                                 |
| `format`   | ⏳ 待实现 | 见下文                       | MemGPT, MemoryBank                    |

______________________________________________________________________

## ⏳ TODO-D5-1: `rerank`

### 概述

对检索结果进行重排序。

### 小类参数

```yaml
operators:
  post_retrieval:
    action: rerank

    # 重排序类型
    rerank_type: "weighted"          # semantic | time_weighted | ppr | weighted | cross_encoder

    # semantic 专用
    rerank_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # time_weighted 专用 (LD-Agent)
    time_decay_rate: 0.1             # 每小时衰减率
    time_field: "timestamp"          # metadata 中的时间字段

    # ppr 专用 (HippoRAG)
    damping_factor: 0.5              # PPR 阻尼因子
    max_iterations: 100
    convergence_threshold: 1e-6
    personalization_nodes: "query_entities"  # 个性化节点来源

    # weighted 专用 (Generative Agents)
    factors:
      - name: "recency"
        weight: 0.3
        decay_type: "exponential"
        decay_rate: 0.995            # 每小时
      - name: "importance"
        weight: 0.3
        field: "importance_score"
      - name: "relevance"
        weight: 0.4
        source: "embedding_similarity"

    # cross_encoder 专用
    cross_encoder_model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
    batch_size: 32

    # 通用配置
    top_k: 10
    score_field: "rerank_score"      # 存储重排分数的字段
```

### 参考实现分析

#### HippoRAG (PPR)

- **代码位置**: `/home/zrc/develop_item/HippoRAG/src/`
- **核心逻辑**:
  ```python
  def personalized_pagerank(query_entities, graph, damping=0.5):
      # 初始化：查询实体节点设为 1/n
      personalization = {e: 1/len(query_entities) for e in query_entities}

      # 迭代计算 PPR
      scores = nx.pagerank(
          graph,
          alpha=damping,
          personalization=personalization
      )

      # 按分数排序返回
      return sorted(scores.items(), key=lambda x: x[1], reverse=True)
  ```

#### Generative Agents (weighted)

- **代码位置**: `/home/zrc/develop_item/locomo/generative_agents/`
- **核心逻辑**:
  ```python
  def compute_score(memory, query_embedding, current_time):
      # 时间衰减
      hours_passed = (current_time - memory.timestamp).hours
      recency = 0.995 ** hours_passed

      # 重要性
      importance = memory.importance_score / 10

      # 相关性
      relevance = cosine_similarity(query_embedding, memory.embedding)

      # 加权组合
      score = 0.3 * recency + 0.3 * importance + 0.4 * relevance
      return score
  ```

#### LD-Agent (time_weighted + topic overlap)

- **代码位置**: `/home/zrc/develop_item/LD-Agent/`
- **核心逻辑**:
  - 话题重叠度评分
  - 时间衰减加权
  - 组合排序

### 开发任务

- [ ] 实现 `semantic` 子类型
  - [ ] Cross-encoder 重排
- [ ] 实现 `time_weighted` 子类型
  - [ ] 时间衰减计算
  - [ ] 与相关性组合
- [ ] 实现 `ppr` 子类型
  - [ ] Personalized PageRank 实现
  - [ ] 与图存储联动
- [ ] 实现 `weighted` 子类型
  - [ ] 多因子加权
  - [ ] 可配置权重
- [ ] 实现 `cross_encoder` 子类型
  - [ ] 模型加载
  - [ ] 批量推理

### 预估工时: 5 天

______________________________________________________________________

## ⏳ TODO-D5-2: `filter`

### 概述

对检索结果进行筛选过滤。

### 小类参数

```yaml
operators:
  post_retrieval:
    action: filter

    # 筛选类型
    filter_type: "token_budget"      # token_budget | threshold | top_k | llm | dedup

    # token_budget 专用 (SCM4LLMs)
    token_budget: 2000
    token_counter: "tiktoken"        # tiktoken | simple
    overflow_strategy: "truncate"    # truncate | summarize | drop_lowest
    priority_field: "relevance"      # 保留优先级

    # threshold 专用
    score_threshold: 0.5
    score_field: "relevance"

    # top_k 专用
    k: 10

    # llm 专用
    filter_prompt: |
      Given the query and these retrieved memories,
      select the most relevant ones for answering the question.
      Query: {query}
      Memories: {memories}
      Selected indices:

    # dedup 专用
    dedup_threshold: 0.95            # 相似度阈值
    dedup_strategy: "keep_first"     # keep_first | keep_highest | merge

    # 三元决策 (SCM4LLMs)
    decision_mode: "three_way"       # simple | three_way
    three_way_actions:
      - condition: "too_long"
        action: "summarize"
      - condition: "irrelevant"
        action: "drop"
      - condition: "relevant"
        action: "keep"
```

### 参考实现分析

#### SCM4LLMs (token_budget + three_way)

- **代码位置**: `/home/zrc/develop_item/SCM4LLMs/`
- **核心逻辑**:
  ```python
  def filter_with_budget(memories, query, budget):
      total_tokens = 0
      result = []

      for memory in sorted(memories, key=lambda m: m.relevance, reverse=True):
          mem_tokens = count_tokens(memory.text)

          if total_tokens + mem_tokens <= budget:
              # 直接保留
              result.append(memory)
              total_tokens += mem_tokens
          elif memory.relevance > high_threshold:
              # 高相关性但太长：摘要
              summary = summarize(memory.text)
              result.append(summary)
              total_tokens += count_tokens(summary)
          else:
              # 低相关性：丢弃
              pass

      return result
  ```

### 开发任务

- [ ] 实现 `token_budget` 子类型
  - [ ] Token 计数
  - [ ] 预算控制
  - [ ] 溢出策略
- [ ] 实现 `threshold` 子类型
  - [ ] 分数阈值筛选
- [ ] 实现 `top_k` 子类型
  - [ ] Top-K 截断
- [ ] 实现 `llm` 子类型
  - [ ] LLM 筛选判断
- [ ] 实现 `dedup` 子类型
  - [ ] 相似度去重
- [ ] 实现三元决策逻辑

### 预估工时: 4 天

______________________________________________________________________

## ⏳ TODO-D5-3: `merge`

### 概述

合并多源检索结果。

### 小类参数

```yaml
operators:
  post_retrieval:
    action: merge

    # 合并策略
    merge_strategy: "weighted"       # concat | interleave | weighted | rrf | link_expand

    # weighted 专用 (MemoryOS)
    source_weights:
      stm: 0.3
      mtm: 0.4
      ltm: 0.3
    normalize_scores: true

    # rrf 专用 (Reciprocal Rank Fusion)
    rrf_k: 60

    # interleave 专用
    interleave_ratio: [2, 1, 1]      # 每轮从各源取的数量

    # link_expand 专用 (A-mem)
    expansion_depth: 1               # 链接扩展深度
    expansion_weight: 0.5            # 扩展结果的权重衰减
    include_original: true           # 是否包含原始结果

    # multi_aspect 专用 (EmotionalRAG)
    aspect_fusion: "late"            # early | late
    aspect_weights:
      semantic: 0.6
      emotion: 0.4
    fusion_strategies:               # EmotionalRAG 的 4 种策略
      - name: "C-A"                  # Concatenate-All
        method: "concat"
      - name: "C-M"                  # Concatenate-Max
        method: "max_per_source"
      - name: "S-C"                  # Select-Concat
        method: "select_then_concat"
      - name: "S-S"                  # Select-Select
        method: "select_both"

    # 去重
    dedup_after_merge: true
    dedup_threshold: 0.9

    # 结果限制
    max_results: 20
```

### 参考实现分析

#### MemoryOS (multi-tier merge)

- **代码位置**: `/home/zrc/develop_item/MemoryOS/`
- **核心逻辑**:
  ```python
  def merge_results(stm_results, mtm_results, ltm_results, weights):
      all_results = []

      for result in stm_results:
          result.score *= weights['stm']
          all_results.append(result)

      for result in mtm_results:
          result.score *= weights['mtm']
          all_results.append(result)

      for result in ltm_results:
          result.score *= weights['ltm']
          all_results.append(result)

      # 排序去重
      return deduplicate(sorted(all_results, key=lambda x: x.score, reverse=True))
  ```

#### A-mem (link_expand)

- **代码位置**: `/home/zrc/develop_item/A-mem/`
- **核心逻辑**:
  ```python
  def expand_results(results, depth=1):
      expanded = list(results)

      for result in results:
          neighbors = get_neighbors(result.id, depth)
          for neighbor in neighbors:
              neighbor.score = result.score * 0.5  # 衰减
              expanded.append(neighbor)

      return deduplicate(expanded)
  ```

#### EmotionalRAG (multi_aspect)

- **代码位置**: `/home/zrc/develop_item/EmotionalRAG/`
- **核心逻辑**:
  - 4 种融合策略
  - 语义+情感双维检索结果融合

### 开发任务

- [ ] 实现 `concat` 子类型
- [ ] 实现 `interleave` 子类型
- [ ] 实现 `weighted` 子类型
  - [ ] 多源加权
  - [ ] 分数归一化
- [ ] 实现 `rrf` 子类型
  - [ ] Reciprocal Rank Fusion
- [ ] 实现 `link_expand` 子类型
  - [ ] 链接扩展
  - [ ] 权重衰减
- [ ] 实现 `multi_aspect` 子类型
  - [ ] 多维向量结果融合
  - [ ] 4 种 EmotionalRAG 策略
- [ ] 去重逻辑

### 预估工时: 5 天

______________________________________________________________________

## ⏳ TODO-D5-4: `augment`

### 概述

对检索结果进行增强，添加额外上下文。

### 小类参数

```yaml
operators:
  post_retrieval:
    action: augment

    # 增强类型
    augment_type: "reflection"       # reflection | context | metadata | temporal

    # reflection 专用 (LoCoMo, Generative Agents)
    include_reflections: true
    reflection_source: "memory"      # memory | generate
    reflection_prompt: |             # generate 模式
      Based on these memories, what insights can be drawn?
    max_reflections: 3

    # context 专用
    context_window: 2                # 前后各取 N 条
    context_source: "temporal"       # temporal | semantic

    # metadata 专用
    include_metadata: ["timestamp", "importance", "source"]
    metadata_format: "inline"        # inline | header | json

    # temporal 专用
    add_time_context: true
    time_format: "relative"          # relative | absolute | both
    time_template: "{time_ago}: {content}"
```

### 参考实现分析

#### LoCoMo (reflection integration)

- **代码位置**: `/home/zrc/develop_item/locomo/`
- **核心逻辑**:
  ```python
  def augment_with_reflections(results, reflections):
      augmented = []

      for result in results:
          # 找相关反思
          relevant_reflections = find_relevant_reflections(result, reflections)

          # 添加到结果
          result.context += "\nReflections:\n"
          for ref in relevant_reflections:
              result.context += f"- {ref.content}\n"

          augmented.append(result)

      return augmented
  ```

#### Generative Agents (temporal context)

- **代码位置**: `/home/zrc/develop_item/locomo/generative_agents/`
- **核心逻辑**:
  - 添加时间上下文
  - 显示"2 hours ago"等相对时间

### 开发任务

- [ ] 实现 `reflection` 子类型
  - [ ] 反思检索
  - [ ] 反思生成
  - [ ] 整合到结果
- [ ] 实现 `context` 子类型
  - [ ] 时间上下文窗口
  - [ ] 语义上下文窗口
- [ ] 实现 `metadata` 子类型
  - [ ] 元数据提取
  - [ ] 格式化输出
- [ ] 实现 `temporal` 子类型
  - [ ] 相对时间计算
  - [ ] 时间模板

### 预估工时: 3 天

______________________________________________________________________

## ⏳ TODO-D5-5: `compress`

### 概述

对检索结果进行压缩。

### 小类参数

```yaml
operators:
  post_retrieval:
    action: compress

    # 压缩类型
    compress_type: "llmlingua"       # llmlingua | extractive | abstractive

    # llmlingua 专用 (SeCom)
    compression_ratio: 0.5
    model: "llmlingua-2"
    preserve_keywords: true

    # extractive 专用
    sentence_count: 3
    extraction_method: "textrank"    # textrank | tfidf | embedding

    # abstractive 专用
    summary_prompt: |
      Summarize the following retrieved context concisely...
    max_tokens: 200

    # 选择性压缩
    compress_threshold: 500          # 超过此 token 数才压缩
    preserve_recent: 2               # 保留最近 N 条不压缩
```

### 参考实现分析

#### SeCom (LLMLingua)

- **代码位置**: `/home/zrc/develop_item/SeCom/`
- **核心逻辑**:
  ```python
  from llmlingua import PromptCompressor

  compressor = PromptCompressor(model="llmlingua-2")

  def compress_context(context, ratio=0.5):
      compressed = compressor.compress(
          context,
          compression_ratio=ratio,
          use_sentence_level=True
      )
      return compressed
  ```

### 开发任务

- [ ] 实现 `llmlingua` 子类型
  - [ ] LLMLingua 集成
  - [ ] 压缩比控制
- [ ] 实现 `extractive` 子类型
  - [ ] 关键句抽取
- [ ] 实现 `abstractive` 子类型
  - [ ] 摘要生成
- [ ] 选择性压缩逻辑

### 预估工时: 3 天

______________________________________________________________________

## ⏳ TODO-D5-6: `format`

### 概述

对检索结果进行格式化输出。

### 小类参数

```yaml
operators:
  post_retrieval:
    action: format

    # 格式化类型
    format_type: "template"          # template | structured | chat | xml

    # template 专用 (MemGPT, MemoryBank)
    template: |
      ## Relevant Memories
      {memories}

      ## User Profile
      {profile}
    memory_template: "- [{timestamp}] {content}"

    # structured 专用
    structure:
      - section: "Recent Conversations"
        source: "stm"
        max_items: 5
      - section: "Related Memories"
        source: "ltm"
        max_items: 10
      - section: "User Preferences"
        source: "profile"

    # chat 专用
    role_mapping:
      user: "Human"
      assistant: "AI"
    include_timestamps: true

    # xml 专用 (Claude style)
    xml_tags:
      memories: "relevant_context"
      profile: "user_profile"
```

### 参考实现分析

#### MemGPT (template + system message)

- **代码位置**: `/home/zrc/develop_item/MemGPT/memgpt/`
- **核心逻辑**:
  - 系统消息模板
  - Core Memory 嵌入
  - Recall Memory 格式化

#### MemoryBank (role + profile)

- **代码位置**: `/home/zrc/develop_item/MemoryBank-SiliconFriend/`
- **核心逻辑**:
  - 角色信息头
  - 对话历史格式化
  - 用户画像整合

### 开发任务

- [ ] 实现 `template` 子类型
  - [ ] 可配置模板
  - [ ] 变量替换
- [ ] 实现 `structured` 子类型
  - [ ] 分区格式化
  - [ ] 多源整合
- [ ] 实现 `chat` 子类型
  - [ ] 对话格式
  - [ ] 角色映射
- [ ] 实现 `xml` 子类型
  - [ ] XML 标签包装

### 预估工时: 2 天

______________________________________________________________________

## 📋 开发优先级

| 优先级 | Action     | 小类                                     | 参考工作                      | 预估工时 |
| ------ | ---------- | ---------------------------------------- | ----------------------------- | -------- |
| P0     | `rerank`   | semantic, time_weighted, ppr, weighted   | HippoRAG, GA, LD-Agent        | 5天      |
| P0     | `filter`   | token_budget, threshold, top_k, dedup    | SCM4LLMs                      | 4天      |
| P0     | `merge`    | weighted, rrf, link_expand, multi_aspect | MemoryOS, A-mem, EmotionalRAG | 5天      |
| P1     | `augment`  | reflection, context, temporal            | LoCoMo, GA                    | 3天      |
| P1     | `compress` | llmlingua, extractive, abstractive       | SeCom                         | 3天      |
| P2     | `format`   | template, structured, chat, xml          | MemGPT, MemoryBank            | 2天      |

**总计**: 22 人天

______________________________________________________________________

*文档创建时间: 2025-01-27*
