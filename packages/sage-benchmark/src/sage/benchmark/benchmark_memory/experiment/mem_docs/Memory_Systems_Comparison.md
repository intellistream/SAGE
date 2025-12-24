# 记忆体算法对比表

> 本文档按照统一的记忆体视角框架，对比分析 SAGE 框架下实现的各记忆系统\
> **更新时间**: 2025-12-24

______________________________________________________________________

## 一、统一记忆操作对比表

| #   | 记忆体         | D1 Service（数据结构）                                 | D2 PreInsert                                               | D3 PostInsert                                             | D4 PreRetrieval                                  | D5 PostRetrieval                            |
| --- | -------------- | ------------------------------------------------------ | ---------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------- |
| 1   | **MemoryBank** | `hierarchical_memory`<br>(STM/MTM/LTM 三层)            | `transform.summarize`<br>事件摘要生成                      | `forgetting`<br>Ebbinghaus遗忘曲线                        | `embedding`<br>查询向量化                        | `rerank.time_weighted`<br>时间加权重排序    |
| 2   | **MemGPT**     | `hierarchical_memory`<br>(Core/Archival/Recall 功能层) | `none`<br>无预处理                                         | `none`<br>Agent工具主动管理                               | `embedding`<br>查询向量化                        | `merge.multi_tier`<br>三层RRF融合           |
| 3   | **MemoryOS**   | `hierarchical_memory`<br>(STM/MTM/LPM 三层)            | `none`<br>无预处理                                         | `enhance.profile_extraction`<br>热度触发Profile提取       | `none`<br>无预处理                               | `merge.multi_query`<br>三层并行检索合并     |
| 3   | **MemoryOS**   | `hierarchical_memory`<br>(STM/MTM/LPM 三层)            | `none`<br>（可选：extract.multi_summary/continuity_check） | `migrate`<br>热度迁移（可选：enhance.profile_extraction） | `none`<br>无预处理                               | `merge.multi_query`<br>三层并行检索合并     |
| 4   | **LD-Agent**   | `hierarchical_memory`<br>(STM/LTM 双层)                | `none`<br>无预处理                                         | `migrate`<br>时间间隔触发迁移+摘要                        | `optimize.keyword_extract`<br>名词提取(话题重叠) | `rerank.weighted`<br>语义+时间+话题综合排序 |

______________________________________________________________________

## 二、各算法详细划分

### 2.1 MemoryBank

**论文**: MemoryBank: Enhancing Large Language Models with Long-Term Memory\
**核心特点**: Ebbinghaus 遗忘曲线 + 检索增强记忆

#### 记忆数据结构

**服务**: `HierarchicalMemoryService` (三层模式)

```yaml
tier_mode: "three_tier"
tier_names: ["stm", "mtm", "ltm"]
tier_capacities:
  stm: 50        # 短期记忆
  mtm: 500       # 中期记忆
  ltm: -1        # 长期记忆(无限)
```

**存储内容**:

- STM: 原始对话
- MTM: 事件记忆
- LTM: 事件摘要 + 用户画像

**检索方法**: 向量检索 (FAISS) + 时间加权重排序

#### 记忆操作

##### PreInsert: 事件摘要生成

```yaml
pre_insert:
  action: "transform"
  transform_type: "summarize"
  only_on_session_end: true  # 会话结束时生成
```

**功能**:

- 对对话生成事件摘要
- 提取关键信息（事实、偏好、计划）
- 为 LTM 准备高质量内容

**论文对应**: Daily Event Summary

##### PostInsert: Ebbinghaus 遗忘机制

```yaml
post_insert:
  action: "forgetting"
  strategy: "ebbinghaus"
  forget_threshold: 0.1      # R < 0.1 时删除
  only_on_session_end: true
```

**功能**:

- 计算记忆强度 S = 初始强度 + 检索次数
- 应用遗忘曲线 R = exp(-t/S)
- 删除低保留率记忆
- 检索增强：被检索的记忆 S += 1

**论文对应**: Ebbinghaus Forgetting Curve + Memory Reinforcement

##### PreRetrieval: 查询向量化

```yaml
pre_retrieval:
  action: "embedding"
```

**功能**: 为向量检索生成 query embedding

##### PostRetrieval: 时间加权重排序

```yaml
post_retrieval:
  action: "rerank"
  rerank_type: "time_weighted"
  time_decay_rate: 0.1
  enable_reinforcement: true  # 检索后增强记忆
```

**功能**:

- 公式: score = similarity × exp(-decay × elapsed_days)
- 近期记忆权重更高
- 检索后自动增强记忆强度

**论文对应**: Date-based Sorting (SAGE 增强为时间加权)

#### 关键创新

1. **Ebbinghaus 遗忘曲线**: 模拟人类记忆遗忘规律
1. **检索增强**: 被检索的记忆强度增加，不易遗忘
1. **多层摘要**: 原始对话 → 事件摘要 → 全局画像

______________________________________________________________________

### 2.2 MemGPT

**论文**: MemGPT: Towards LLMs as Operating Systems\
**核心特点**: OS-inspired 虚拟内存管理 + Agent 工具调用

#### 记忆数据结构

**服务**: `HierarchicalMemoryService` (功能层模式)

```yaml
tier_mode: "functional"
tier_names: ["core", "archival", "recall"]
tier_capacities:
  core: 2000      # Working Context (字符限制)
  archival: -1    # 档案存储(无限)
  recall: -1      # 对话历史(无限)
```

**存储内容**:

- Core Memory: 始终在 LLM context 中（Persona + Human 信息）
- Archival Storage: 长期知识，手动插入
- Recall Storage: 对话历史，自动追加

**检索方法**:

- Core: 不检索（始终在 context）
- Archival: 向量检索
- Recall: 混合检索（向量 + 全文 + RRF）

#### 记忆操作

##### PreInsert: 无操作

```yaml
pre_insert:
  action: "none"
```

**原因**: Agent 通过工具主动决定插入内容，无需自动预处理

##### PostInsert: 无操作

```yaml
post_insert:
  action: "none"
```

**原因**: Core Memory 编辑由 Agent 通过工具主动调用

- `core_memory_append`: 追加内容
- `core_memory_replace`: 替换内容

**论文对应**: Agent 通过函数调用管理 Working Context

##### PreRetrieval: 查询向量化

```yaml
pre_retrieval:
  action: "embedding"
```

**功能**: 为 Archival 和 Recall 的向量检索生成 query embedding

##### PostRetrieval: 三层 RRF 融合

```yaml
post_retrieval:
  action: "merge"
  merge_type: "multi_tier"
  fusion_strategy: "rrf"
  rrf_k: 60
  enable_memory_pressure_warning: true
```

**功能**:

1. Core Memory: 始终在 context，完整返回
1. Archival + Recall: RRF 融合后返回 Top-K
1. Memory Pressure Warning: context 超过 70% 时警告

**论文对应**:

- RRF (k=60) 混合检索融合
- Memory Pressure Warning (核心创新)

#### 关键创新

1. **OS-inspired 架构**: Core (寄存器) / Archival (磁盘) / Recall (内存)
1. **混合检索 + RRF**: 向量检索和全文检索融合
1. **Memory Pressure Warning**: 自动提醒 Agent 管理 context
1. **Agent 工具调用**: LLM 主动管理记忆，无被动操作

______________________________________________________________________

### 2.3 MemoryOS

**论文**: Memory OS of AI Agent\
**核心特点**: 三层架构+热度迁移（migrate）为主，批量多主题摘要/LLM知识提取为可选，Segment-Page结构、两阶段检索

#### 记忆数据结构

**服务**: `HierarchicalMemoryService` (三层模式)

```yaml
tier_mode: "three_tier"
tier_names: ["stm", "mtm", "lpm"]
tier_capacities:
  stm: 20         # FIFO 队列
  mtm: 200        # Segment-Page 结构
  lpm: -1         # Persona/Knowledge/Traits
```

**存储内容**:

- STM: 最新对话 (FIFO)
- MTM: 主题段落 (Segment) + 对话页 (Page)
  - Segment: LLM多摘要+主题分组结果，含Summary/Keywords
  - Page: 对话内容+Embedding+主题标签+链接关系
- LPM: 用户画像（Profile）+ 用户知识（Knowledge）+ 助手知识

**检索方法**: 两阶段检索

1. Segment Selection: F_score = α×cos + β×jaccard + γ×recency
1. Page Retrieval: FAISS 向量检索

#### 记忆操作

##### PreInsert: 默认禁用（none），可选多主题摘要/连续性检查

```yaml
pre_insert:
  action: "none"
# 可选：
# pre_insert:
#   action: "extract"
#   extract_type: "multi_summary"
#   ...
# pre_insert:
#   action: "transform"
#   transform_type: "continuity_check"
#   ...
```

**功能**:

- 默认不做预处理，直接写入STM
- 可选启用多主题摘要或连续性检查（需手动切换配置）

**实现细节**:

- 当前pipeline默认none，multi_summary/continuity_check为注释可选

**论文对应**: Multi-topic Dialogue Summarization（可选）

##### PostInsert: 热度迁移（migrate），可选LLM知识提取

```yaml
post_insert:
  action: "migrate"
  migrate_policy: "heat"
  heat_threshold: 0.7
  ...
# 可选：
# post_insert:
#   action: "enhance"
#   enhance_type: "profile_extraction"
#   heat_threshold: 5.0
#   ...
```

**功能**:

- 默认采用热度迁移（高热升级，低热降级/淘汰）
- 可选启用LLM驱动的Profile/Knowledge提取（需手动切换配置）

**实现细节**:

- 当前pipeline默认migrate，profile_extraction为注释可选

**论文对应**: Hot Session Profile/Knowledge Extraction（可选）

##### PreRetrieval: 无操作

```yaml
pre_retrieval:
  action: "none"
```

**原因**: MemoryOS 直接使用原始 query，不需要预处理

##### PostRetrieval: 多层并行检索合并

```yaml
post_retrieval:
  action: "merge"
  merge_type: "multi_query"
  secondary_queries:
    - {tier: "stm"}   # 最近对话
    - {tier: "mtm"}   # 主题相关段落
    - {tier: "lpm"}   # 用户画像和知识
```

**功能**:

- 并行检索三层 (ThreadPoolExecutor)
- 合并结果构造 Prompt

**论文对应**: Three-tier Parallel Retrieval

#### 关键创新

1. **三层架构+热度迁移**: STM/MTM/LPM三层，热度驱动迁移（高热升级，低热降级）
1. **多主题摘要/LLM知识提取为可选**: 可按需启用批量多主题摘要、Profile/Knowledge提取
1. **Segment-Page结构**: 主题段落+对话页双层组织，便于主题化管理
1. **两阶段检索**: Segment Selection → Page Retrieval，提升检索相关性

______________________________________________________________________

### 2.4 LD-Agent

**论文**: Hello Again! LLM-powered Personalized Agent for Long-term Dialogue\
**核心特点**: 事件摘要 + 话题重叠检索 + 多因子重排序

#### 记忆数据结构

**服务**: `HierarchicalMemoryService` (双层模式)

```yaml
tier_mode: "two_tier"
tier_names: ["stm", "ltm"]
tier_capacities:
  stm: 50         # 当前会话缓存
  ltm: -1         # 事件摘要库
```

**存储内容**:

- STM: 当前会话原始对话
- LTM: 历史会话事件摘要 + 名词集合

**检索方法**:

- 语义检索 (FAISS)
- 话题重叠 (名词 Jaccard 相似度)
- 时间衰减

#### 记忆操作

##### PreInsert: 无操作

```yaml
pre_insert:
  action: "none"
```

**原因**: 事件摘要在 PostInsert 的迁移时生成，而非插入前

##### PostInsert: 时间间隔触发迁移 + 摘要生成

```yaml
post_insert:
  action: "migrate"
  migrate_policy: "time"
  session_gap: 3600               # 1小时
  upgrade_transform: "summarize"  # STM→LTM时生成摘要
```

**功能**:

1. 检测会话间隔 > 1 小时
1. 触发 STM → LTM 迁移
1. 迁移时生成事件摘要
1. 提取名词集合用于话题重叠

**论文对应**: Session-gap Triggered Migration + Event Summarization

##### PreRetrieval: 名词提取（话题重叠）

```yaml
pre_retrieval:
  action: "optimize"
  optimize_type: "keyword_extract"
  extractor: "spacy"
  extract_types: ["NOUN", "PROPN"]
  max_keywords: 15
```

**功能**:

- 使用 spaCy 提取查询中的名词
- 用于后续的话题重叠计算

**论文对应**: Noun Set Extraction for Topic Overlap

##### PostRetrieval: 多因子加权重排序

```yaml
post_retrieval:
  action: "rerank"
  rerank_type: "weighted"
  factors:
    - name: "relevance"           # 语义相似度
      weight: 0.4
    - name: "recency"             # 时间新近度
      weight: 0.3
      decay_rate: 1e-7
    - name: "topic_overlap"       # 话题重叠
      weight: 0.3
      source: "keyword_jaccard"
```

**功能**:

- 综合得分 = 0.4×语义 + 0.3×时间 + 0.3×话题
- 话题重叠: Jaccard(query_nouns, memory_nouns)
- 时间衰减: exp(-decay_rate × elapsed_seconds)

**论文对应**: Multi-factor Weighted Retrieval

#### 关键创新

1. **会话间隔触发**: 1小时后自动迁移并生成摘要
1. **话题重叠检索**: 基于名词集合的 Jaccard 相似度
1. **多因子加权**: 平衡语义、时间、话题三个维度
1. **轻量级设计**: 双层架构，适合长期对话场景

______________________________________________________________________

## 三、对比分析

### 3.1 PreInsert 阶段对比

| 记忆体     | PreInsert 操作                                             | 目的                        | 特点                   |
| ---------- | ---------------------------------------------------------- | --------------------------- | ---------------------- |
| MemoryBank | `transform.summarize`                                      | 生成事件摘要                | 会话结束时批量生成     |
| MemGPT     | `none`                                                     | 无                          | Agent 工具主动管理     |
| MemoryOS   | `extract.multi_summary` 或<br>`transform.continuity_check` | 多主题识别 或<br>连续性判断 | 实时处理，支持复杂场景 |
| LD-Agent   | `none`                                                     | 无                          | 摘要在 PostInsert 生成 |

**设计思路**:

- **MemoryBank**: 离线批处理，生成高质量摘要
- **MemGPT**: Agent 主动控制，不需要自动化
- **MemoryOS**: 实时多维处理，适合混合对话
- **LD-Agent**: 延迟到迁移时生成，节省资源

### 3.2 PostInsert 阶段对比

| 记忆体     | PostInsert 操作              | 目的                   | 特点                  |
| ---------- | ---------------------------- | ---------------------- | --------------------- |
| MemoryBank | `forgetting`                 | 遗忘曲线管理           | Ebbinghaus + 检索增强 |
| MemGPT     | `none`                       | 无                     | Agent 工具主动管理    |
| MemoryOS   | `enhance.profile_extraction` | Profile/Knowledge 提取 | 热度触发，并行 LLM    |
| LD-Agent   | `migrate`                    | 时间触发迁移           | 迁移时生成摘要        |

**设计思路**:

- **MemoryBank**: 模拟人类记忆规律
- **MemGPT**: Agent 完全自主
- **MemoryOS**: 智能感知热度，主动提取
- **LD-Agent**: 简单高效的时间策略

### 3.3 PreRetrieval 阶段对比

| 记忆体     | PreRetrieval 操作          | 目的       | 特点               |
| ---------- | -------------------------- | ---------- | ------------------ |
| MemoryBank | `embedding`                | 查询向量化 | 基础向量检索       |
| MemGPT     | `embedding`                | 查询向量化 | 支持混合检索       |
| MemoryOS   | `none`                     | 无         | 直接使用原始 query |
| LD-Agent   | `optimize.keyword_extract` | 名词提取   | 话题重叠准备       |

**设计思路**:

- **MemoryBank**: 简单向量化
- **MemGPT**: 支持向量+全文双路
- **MemoryOS**: 依赖两阶段检索的综合得分
- **LD-Agent**: 多因子需要提前准备

### 3.4 PostRetrieval 阶段对比

| 记忆体     | PostRetrieval 操作     | 目的             | 特点             |
| ---------- | ---------------------- | ---------------- | ---------------- |
| MemoryBank | `rerank.time_weighted` | 时间加权重排序   | 近期记忆优先     |
| MemGPT     | `merge.multi_tier`     | 三层 RRF 融合    | Core始终在 + RRF |
| MemoryOS   | `merge.multi_query`    | 三层并行检索合并 | ThreadPool 并行  |
| LD-Agent   | `rerank.weighted`      | 多因子加权重排序 | 语义+时间+话题   |

**设计思路**:

- **MemoryBank**: 平衡相似度与时效性
- **MemGPT**: OS-inspired 层级管理
- **MemoryOS**: 并行加速检索
- **LD-Agent**: 全面综合评估

### 3.5 数据结构对比

| 记忆体     | 层级架构                      | 容量策略                  | 淘汰策略         | 特殊结构            |
| ---------- | ----------------------------- | ------------------------- | ---------------- | ------------------- |
| MemoryBank | STM/MTM/LTM (三层)            | 固定容量                  | Ebbinghaus 遗忘  | 无                  |
| MemGPT     | Core/Archival/Recall (功能层) | Core 有限，其他无限       | 无（Agent 管理） | Core 始终在 context |
| MemoryOS   | STM/MTM/LPM (三层)            | STM 20, MTM 200, LPM 无限 | FIFO + LFU       | Segment-Page 双层   |
| LD-Agent   | STM/LTM (双层)                | STM 50, LTM 无限          | 时间触发迁移     | 名词集合            |

______________________________________________________________________

## 四、实现完整性验证

| 记忆体     | PreInsert | PostInsert | PreRetrieval | PostRetrieval | 数据结构 | 状态   |
| ---------- | --------- | ---------- | ------------ | ------------- | -------- | ------ |
| MemoryBank | ? 已实现  | ? 已实现   | ? 已实现     | ? 已实现      | ? 已实现 | ? 完整 |
| MemGPT     | ? 已实现  | ? 已实现   | ? 已实现     | ? 已实现      | ? 已实现 | ? 完整 |
| MemoryOS   | ? 已实现  | ? 已实现   | ? 已实现     | ? 已实现      | ? 已实现 | ? 完整 |
| LD-Agent   | ? 已实现  | ? 已实现   | ? 已实现     | ? 已实现      | ? 已实现 | ? 完整 |

**总代码量**:

- MemoryBank: ~800 行
- MemGPT: ~1,200 行 (含 Agent 工具)
- MemoryOS: ~1,022 行 (P1 核心功能)
- LD-Agent: ~600 行

______________________________________________________________________

## 五、配置文件路径

| 记忆体     | 配置文件路径                                                    |
| ---------- | --------------------------------------------------------------- |
| MemoryBank | `config/primitive_memory_model/locomo_memorybank_pipeline.yaml` |
| MemGPT     | `config/primitive_memory_model/locomo_memgpt_pipeline.yaml`     |
| MemoryOS   | `config/primitive_memory_model/locomo_memoryos_pipeline.yaml`   |
| LD-Agent   | `config/primitive_memory_model/locomo_ldagent_pipeline.yaml`    |

______________________________________________________________________

**文档版本**: v1.0\
**最后更新**: 2025-12-24\
**作者**: GitHub Copilot (Claude Sonnet 4.5)
