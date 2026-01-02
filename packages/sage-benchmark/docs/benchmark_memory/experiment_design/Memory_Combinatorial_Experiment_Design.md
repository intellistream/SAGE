# SAGE 记忆模型排列组合实验设计（五维）

> 目标：在不破坏架构清晰性的前提下，对 PreRetrieval → PostRetrieval → PreInsert → PostInsert → MemoryService
> 五个维度进行可控的排列组合实验，逐步逼近"最优记忆模型"。
>
> 范围：以 Locomo 为主数据集，基于现有算子与服务实现，支持通过 YAML 组合配置与最小仿真策略实现"任意组合可运行"。

______________________________________________________________________

## 1. 设计原则与难度分级

- **分层渐进（从易到难）**：
  1. **PreRetrieval**（最简单，只读）：查询改写，不触碰状态
  1. **PostRetrieval**（简单，只读）：结果加工，不触碰状态
  1. **PreInsert**（中等难度）：改变插入内容，间接影响状态
  1. **PostInsert**（复杂）：直接改状态（CRUD/蒸馏/遗忘/迁移）
  1. **MemoryService**（最复杂）：底层数据结构，决定状态与检索语义
- **明确职责边界**：算子不跨权；服务负责最终状态；仿真策略仅在必要时用于解耦。
- **控制组合爆炸**：分阶段筛选 Top-K 或采用小型正交阵（L9/L12），每阶段在前一阶段优胜组合上增加一个维度。
- **可复现与可比**：固定 LLM/Embedding 参数、固定随机种子、输出统一落盘。

**难度分级理由**：

- PreRetrieval 与 PostRetrieval 都是"只读"操作，但 PreRetrieval 更简单（只需改查询文本），而 PostRetrieval 可能涉及重排、过滤等更复杂逻辑
- PreInsert 开始间接影响状态（改变存入内容），但不直接操作存储
- PostInsert 直接操作存储（删除、合并、迁移），复杂度显著提升
- MemoryService 决定底层数据结构与检索语义，是系统级选择，影响最深远

参考实现：

- 主 Pipeline：见
  [packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py)
- 算子层：见 libs/ 目录（Pre/Post 的 operator 与 registry）
  - PreInsert:
    [pre_insert/operator.py](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/pre_insert/operator.py)
  - PostInsert:
    [post_insert/operator.py](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_insert/operator.py)
  - PreRetrieval:
    [pre_retrieval/operator.py](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/pre_retrieval/operator.py)
  - PostRetrieval:
    [post_retrieval/operator.py](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_retrieval/operator.py)
- 短期记忆服务：见
  [packages/sage-middleware/src/sage/middleware/components/sage_mem/services/short_term_memory_service.py](packages/sage-middleware/src/sage/middleware/components/sage_mem/services/short_term_memory_service.py)
- 典型配置：见 primitive_memory_model 下各 YAML 示例

______________________________________________________________________

## 2. 五维与候选水平（按难度排序）

下述所有水平均可通过 YAML 组合。必要时可采用仿真策略（第 3 节）。

### 2.1 PreRetrieval（难度★☆☆☆☆，只改查询，不触碰状态）

- **目的**：塑形查询形式与 hint，优化检索效果。
- **候选水平**：
  - `none`：直接使用原始问题。
  - `optimize`：关键词提取/扩展/同义词。
  - `rewrite`：LLM 重写问题（使其更清晰/可检索）。
  - `multi_query`：生成多个查询变体。
  - `hybrid_hints`：输出 `retrieve_mode/retrieve_params`（由服务/适配器决定是否使用）。
- **核心配置键**：
  - `operators.pre_retrieval.action`
  - `operators.pre_retrieval.rewrite_prompt | expand_keywords | max_queries`
  - 产出：`question`, `query_embedding`, `retrieve_mode`, `retrieve_params`
- **复杂度分析**：仅文本/Embedding 处理，无状态修改，最安全、最易调试。

### 2.2 PostRetrieval（难度★★☆☆☆，不破坏记忆状态，可多次调用）

- **目的**：仅加工检索结果，安全叠加。
- **候选水平**：
  - `none`：直通。
  - `rerank.time_weighted`：时间衰减重排（`time_decay_rate`, `top_k`）。
  - `rerank.recency`：新近优先。
  - `rerank.llm`：LLM 重排（成本高，建议抽样）。
  - `filter.threshold`：得分阈值过滤。
  - `merge.simple`：相似项合并去重。
  - `formatting`：通过 `conversation_format_prompt` 形成统一上下文。
- **核心配置键**：
  - `operators.post_retrieval.action`
  - `operators.post_retrieval.rerank_type | threshold | conversation_format_prompt | top_k | time_decay_rate`
- **复杂度分析**：涉及相似度计算、LLM 调用（rerank）、多维度筛选，比 PreRetrieval 稍复杂，但仍无状态修改。

### 2.3 PreInsert（难度★★★☆☆，间接改状态：改变插入内容/结构/元数据）

- **目的**：将对话转化为 `memory_entries` 列表。
- **候选水平**：
  - `none`：原样插入。
  - `transform.summarize`：摘要压缩（MemoryBank 风格）。
  - `transform.chunking`：长文本分块。
  - `transform.segment`：主题分段。
  - `extract.triple`：三元组抽取（HippoRAG 风格）。
  - `extract.entity|keyword|noun`：稀疏信号，利于 KV/KG/Hybrid。
  - `score.importance|heat`：重要度/热度打分，写入 metadata；可配合 PostInsert/Migration。
- **核心配置键**：
  - `operators.pre_insert.action`
  - `operators.pre_insert.transform_type | extract_type`
  - 产出项字段：`text | embedding | metadata | insert_mode | insert_params`
- **复杂度分析**：涉及文本转换、信息抽取、评分等，间接影响后续状态，但不直接操作存储。

### 2.4 PostInsert（难度★★★★☆，直接改状态：CRUD/蒸馏/遗忘/迁移/建边）

- **目的**：插入完成后，服务侧维护与增强。
- **候选水平**：
  - `none`：直通。
  - `forgetting`：如艾宾浩斯衰减（`decay_type`, `review_boost`, `retention_min`）。
  - `distillation`：蒸馏/合并（TiM/MemGPT/SeCom 类）。
  - `crud`：LLM 决策插/改/删（Mem0 类）。
  - `migrate`：层级迁移（STM→MTM→LTM）。
  - `link_evolution`：同义/时间等关系建边（图存储）。
- **核心配置键**：
  - `operators.post_insert.action`
  - 动作专属参数：`decay_type | migration_policy | ...`
  - 通过 `_ServiceProxy` 具备 CRUD 能力（取/查/插/改/删）。
- **复杂度分析**：直接修改存储状态，涉及复杂决策逻辑（遗忘策略、蒸馏算法、迁移条件），可能引入副作用，需要仔细评测。

### 2.5 MemoryService（难度★★★★★，数据结构，决定状态与检索语义）

- **目的**：底层集合/索引及其检索策略。
- **候选水平**：
  - `short_term_memory`（STM）：滑窗+VDB，FIFO；`max_dialog`, `embedding_dim`。
  - `hierarchical_memory`：分层（STM/MTM/LTM）与迁移策略。
  - `graph_memory`：知识图谱 + 遍历/PPR；适配 `link_evolution`。
  - `hybrid_memory | vector_memory`：多索引/向量索引（如可用）。
- **核心配置键**：
  - `services.register_memory_service = short_term_memory | hierarchical_memory | graph_memory | ...`
  - 服务块参数：`{service_name}.*`（如 `tier_capacities`, `retrieval_top_k`, `max_depth` 等）
- **复杂度分析**：决定系统底层架构，影响检索语义、扩展性、性能，是最根本的选择，改动成本最高。

______________________________________________________________________

## 3. 捆绑关系与仿真策略

为保持“任意组合可运行”，当算子与服务强耦合时，采用下述仿真策略：

- `link_evolution` ↔ 图存储（强耦合）

  - 仿真（非图存储）：将同义集合写入 `metadata.synonyms`；
    - `post_retrieval.merge` 在结果侧展开同义项并合并；
    - `rerank` 根据同义/别名匹配提升得分；
    - 可选：向存储插入轻量“派生条目”模拟软边。

- 层级迁移 ↔ 分层存储（强耦合）

  - 仿真（STM）：`post_insert.migrate` 写 `metadata.target_tier` 与 `insert_mode="active"` +
    `insert_params.priority` 实现“软钉住”；
    - LTM 档案写外存（文件/DB），在 `post_retrieval.merge` 合并摘要/画像。

- 关键词检索 ↔ KV/Hybrid

  - 仿真（VDB）：`pre_retrieval.optimize.expand_keywords` 生成扩展词；`post_retrieval.rerank` 结合关键词重排。

- 三元组抽取 ↔ KG

  - 仿真（非 KG）：以普通条目插入并附 `metadata.triple`；检索时按 triple 匹配/相似度重排。

______________________________________________________________________

## 4. 分阶段实验计划（控规模 → 逼近最优）

**总体策略**：从最简单维度开始，每阶段固定前面优胜组合，只变化一个维度，逐步积累最优配置。

### Phase A（PreRetrieval 扫描 - 难度★☆☆☆☆）

**固定配置**：`post_ret=none, pre_ins=none, post_ins=none, service=STM`

- **变化维度**：PreRetrieval
  - 候选：`none, optimize.rewrite, optimize.expand_keywords, optimize.embed_only, hybrid_hints`
- **目的**：隔离观察"查询优化"的收益（准确率提升 vs LLM 调用成本）
- **预期结论**：找出最有效的查询优化策略（可能是 rewrite 或 expand_keywords）

### Phase B（在 A 优胜组合上，引入 PostRetrieval - 难度★★☆☆☆）

**固定配置**：`pre_ret=<A-Top-2>, pre_ins=none, post_ins=none, service=STM`

- **变化维度**：PostRetrieval
  - 候选：`none, rerank.time_weighted, rerank.recency, filter.threshold, merge.simple, rerank.llm(抽样)`
- **目的**：在优化查询的基础上，观察结果加工的增益
- **预期结论**：查询优化与结果加工的协同效果（可能 time_weighted 或 filter 有效）

### Phase C（在 A+B 优胜组合上，引入 PreInsert - 难度★★★☆☆）

**固定配置**：`pre_ret=<A-Top-1>, post_ret=<B-Top-1>, post_ins=none, service=STM`

- **变化维度**：PreInsert
  - 候选：`none, transform.summarize, transform.chunking, extract.triple, extract.entity, score.importance`
- **目的**：插入内容形态对检索与 QA 的影响
- **预期结论**：找出最优内容转换策略（summarize 可能对长对话有效，extract 对结构化任务有效）

### Phase D（在 A+B+C 优胜组合上，引入 PostInsert - 难度★★★★☆）

**固定配置**：`pre_ret=<A-Top-1>, post_ret=<B-Top-1>, pre_ins=<C-Top-1>, service=STM`

- **变化维度**：PostInsert
  - 候选：`none, forgetting, distillation, crud, migrate（需仿真）, link_evolution（需仿真）`
- **目的**：服务侧维护/增强策略对质量与时延的影响
- **预期结论**：找出最优维护策略（forgetting 可能改善长期质量，distillation 可能压缩存储）
- **注意**：migrate 和 link_evolution 在 STM 上需要仿真策略

### Phase E（替换 MemoryService 并复跑优胜子集 - 难度★★★★★）

**固定配置**：前四个维度使用 A-D 的优胜组合

- **变化维度**：MemoryService
  - 路径：`STM → Hierarchical → Graph → Hybrid`（若可用）
  - 对耦合点使用仿真以保持可比
- **目的**：评估不同数据结构对整体性能的影响
- **预期结论**：找出最适合特定任务的存储架构（Hierarchical 可能适合长期记忆，Graph 适合关系推理）

**组合规模控制**：建议每阶段采用 Top-K 保留（如 Top-2 或 Top-3）或小型正交阵（如 L9/L12）以控制组合爆炸。

______________________________________________________________________

## 5. 命名、配置映射与运行

### 5.1 命名约定（用于 `runtime.memory_name` 与落盘目录）

**格式**：`MS-{service}__PR-{pre_retrieval}__POR-{post_retrieval}__PI-{pre_insert}__POI-{post_insert}`

**示例（按阶段）**：

- Phase A: `MS-stm__PR-rewrite__POR-none__PI-none__POI-none`
- Phase B: `MS-stm__PR-rewrite__POR-timew__PI-none__POI-none`
- Phase C: `MS-stm__PR-rewrite__POR-timew__PI-summarize__POI-none`
- Phase D: `MS-stm__PR-rewrite__POR-timew__PI-summarize__POI-forgetting`
- Phase E: `MS-hierarchical__PR-rewrite__POR-timew__PI-summarize__POI-migrate`

**缩写对照表**：

| 维度          | 缩写 | 示例值                                 |
| ------------- | ---- | -------------------------------------- |
| MemoryService | MS   | stm, hierarchical, graph               |
| PreRetrieval  | PR   | none, rewrite, expand, multi           |
| PostRetrieval | POR  | none, timew, recency, filter, llm      |
| PreInsert     | PI   | none, summarize, chunk, triple, entity |
| PostInsert    | POI  | none, forget, distill, crud, migrate   |

### 5.2 关键配置键（YAML）

**维度顺序（按实验阶段）**：

1. **MemoryService**（基础）：`services.register_memory_service` + `{service_name}.*`
1. **PreRetrieval**（Phase A）：`operators.pre_retrieval.action` + `optimize_type`（可输出 `retrieve_*`）
1. **PostRetrieval**（Phase B）：`operators.post_retrieval.action` +
   `rerank_type | threshold | conversation_format_prompt | top_k | time_decay_rate`
1. **PreInsert**（Phase C）：`operators.pre_insert.action` + `transform_type | extract_type`
1. **PostInsert**（Phase D）：`operators.post_insert.action` + 动作专属参数

### 5.3 参考 YAML（primitive memory models）

- **STM 基线**：
  [locomo_short_term_memory_pipeline.yaml](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model/locomo_short_term_memory_pipeline.yaml)
- **MemoryBank**（三层+遗忘）：
  [locomo_memorybank_pipeline.yaml](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model/locomo_memorybank_pipeline.yaml)
- **HippoRAG**（图+建边）：
  [locomo_hipporag_pipeline.yaml](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model/locomo_hipporag_pipeline.yaml)
- **MemGPT**（Agent/工具）：
  [locomo_memgpt_pipeline.yaml](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model/locomo_memgpt_pipeline.yaml)

### 5.4 运行示例（从 Repo 根目录）

```bash
python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py \
  --config packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model/locomo_short_term_memory_pipeline.yaml \
  --task_id conv-26
```

______________________________________________________________________

## 6. 指标、日志与产出

- 任务指标：
  - QA 正确率（Exact / Partial）；可加命中率@k、MRR（若有标注）。
  - 稳定性：默认固定 `seed`，必要时小样本多 seed 测方差。
- 系统指标：
  - 时延：`stage_timings` 已分段收集（插入/检索/评估）。
  - 成本：LLM 调用次数、tokens、Embedding 调用量。
  - 存储动力学：分层占比、CRUD 比率、遗忘保留率。
- 产出：
  - Sink 统一落盘：`.sage/benchmarks/benchmark_memory/<dataset>/<timestamp>/<memory_name>/`
  - 见
    [packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/memory_sink.py](packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/memory_sink.py)

______________________________________________________________________

## 7. 风险与控制

- **组合爆炸**：分阶段筛选 + Top-K/正交阵；优先保留显著差异的水平
- **成本失控**：限制 `rerank.llm`、`optimize.rewrite` 的抽样频率；评估阶段可走小集
- **服务耦合**：优先在"服务原生 + 仿真"双路径各取一条以对比
- **可比性**：固定基础模型、温度、`top_k`；统一输出命名与路径

______________________________________________________________________

## 8. 实验难度分级总结

| 阶段    | 维度          | 难度  | 状态影响 | 调试复杂度        | 典型水平数 |
| ------- | ------------- | ----- | -------- | ----------------- | ---------- |
| Phase A | PreRetrieval  | ★☆☆☆☆ | 无       | 低（纯文本处理）  | 4-5        |
| Phase B | PostRetrieval | ★★☆☆☆ | 无       | 中（相似度/重排） | 5-6        |
| Phase C | PreInsert     | ★★★☆☆ | 间接     | 中高（转换/抽取） | 6-7        |
| Phase D | PostInsert    | ★★★★☆ | 直接     | 高（状态维护）    | 5-6        |
| Phase E | MemoryService | ★★★★★ | 根本     | 最高（架构级）    | 3-4        |

**难度递增理由**：

1. **PreRetrieval**：仅文本/Embedding 处理，无状态修改，最安全
1. **PostRetrieval**：涉及相似度计算和LLM调用，但仍是只读操作
1. **PreInsert**：开始影响存储内容，但不直接操作存储
1. **PostInsert**：直接修改存储状态，涉及复杂决策和副作用
1. **MemoryService**：决定系统架构，影响最深远，改动成本最高

______________________________________________________________________

## 9. 后续扩展

### 9.1 自动派生与批量运行

- 提供一个小型 runner（参数 → 派生 YAML → 顺序执行 → 聚合报告）
- 支持多任务并行（基于 Ray/Dask）

### 9.2 报告聚合

- 按阶段汇总准确率/时延/成本的雷达图与帕累托前沿
- 输出"最优曲线"与"性价比优选"

### 9.3 交互式可视化

- 提供 Web UI 展示各维度组合的效果对比
- 支持动态筛选和钻取分析

______________________________________________________________________

如需，我可以基于 Phase A/B 立即派生一组最小 YAML 变体与一个一键 runner，直接开始首轮扫描。
