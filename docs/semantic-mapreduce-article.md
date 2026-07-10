# From MapReduce to Semantic Reduce: SAGE for LLM-Native Data Analysis

## Scope and Evidence Boundary

This draft is grounded in the current SAGE repository state:

- `README.md` positions SAGE as a dataflow-native framework that turns LLM
  reasoning workflows into explicit dataflow pipelines.
- `src/sage/stream/datastream.py` exposes stream composition primitives such as
  `map`, `filter`, `flatmap`, `keyby`, and `connect`.
- `src/sage/runtime/environments.py` exposes `LocalEnvironment` and
  `FlowNetEnvironment` for local and optional FlowNet-backed execution.
- `src/sage/serving/__init__.py` keeps inference engines outside the core SAGE
  package and defines integration contracts instead of implementing an engine.
- `src/sage/workloads/large_scale_analysis.py` implements a synthetic
  large-scale analysis workload with shard-level map analysis and a pluggable
  incident reducer.

The current workload uses deterministic and hybrid reducers as reproducible
baselines, plus live OpenAI-compatible reducer paths for contract testing. The
`llm-stub` reducer is a CI-safe integration placeholder and does not call an
external LLM. The framing should therefore emphasize the systems challenge that
Semantic MapReduce makes explicit: LLM reducers may omit incidents, over-merge
evidence, emit invalid structure, cite incomplete evidence, or amplify
latency/cost. SAGE's contribution is the evidence/reducer/trace contract that
detects and constrains these behaviors, not a claim that a raw LLM prompt is
already a universally better reducer.

## Title Recommendation

Recommended title:

**From MapReduce to Semantic Reduce: Orchestrating LLMs over Large-Scale Data**

This title leads with the research idea rather than the product name. It frames
the contribution as an abstraction shift: traditional MapReduce separates local
processing from global aggregation, while LLM-native analysis needs semantic
evidence fusion, conflict handling, hypothesis generation, and traceable
explanation.

Possible subtitle:

**SAGE as an AI-Native Orchestration Layer for Auditable Data Analysis**

## 中文技术文章初稿

# From MapReduce to Semantic Reduce: 用 SAGE 编排大规模数据上的 LLM 分析

大规模数据分析长期以来有一个清晰的系统分工：底层执行引擎负责把数据高效扫过、连接、聚合和落盘；上层应用或人工分析师负责解释结果、形成假设、合并证据并给出行动建议。Spark、Flink、Hadoop MapReduce、数据库和向量系统已经很好地覆盖了前一部分，但后一部分仍然经常停留在脚本、dashboard、人工排查和临时 prompt 之间。

LLM 的出现让这个边界开始松动。我们不再只希望系统回答“某个指标是否超过阈值”，而是希望它能回答：“这些分散在不同服务、区域和时间窗口里的异常是否属于同一个 incident？哪些证据支持这个判断？有没有冲突证据？下一步应该排查 scheduler、decode，还是 kv-cache？”这类问题不是传统 aggregate 能直接表达的，也不是把一整批日志塞进聊天窗口就能可靠解决的。

本文讨论 SAGE 的一个蓝海方向：把 LLM 接入大规模数据处理 pipeline，使系统具备类似 MapReduce 的语义编排能力。这里的关键不是让 SAGE 替代 Spark、Flink、Ray 或数据库。相反，SAGE 更适合作为 AI-native orchestration layer：它可以接在这些执行引擎之上或旁边，负责任务拆解、分片分析、证据聚合、semantic reduce、解释生成和可审计 workflow trace。

传统 MapReduce 的核心洞见是：大数据任务可以拆成大量局部 map，再通过 reduce 得到全局结果。这个思想在 LLM-native data analysis 中仍然成立，但 reduce 的含义发生了变化。对数值分析来说，reduce 可能是 sum、count、max、group-by；对语义分析来说，reduce 需要合并局部证据、去重相邻事件、处理冲突信号、形成 incident hypothesis，并生成可以追溯到原始 evidence 的解释。因此，我们把这个抽象称为 Semantic MapReduce。

更精确地说，Semantic MapReduce 应该被写成一组算子表达式，而不是一个“LLM 接入 pipeline”的口号。核心算子包括：`Shard(D; pi) -> {D_i}`，把观测按时间、服务、tenant 或 trace 边界切分；`MapEvidence(D_i; phi) -> E_i`，在每个 shard 中抽取局部 evidence；`Normalize(E; sigma) -> E_hat`，把不同来源的 evidence 规范化；`GroupEvidence(E_hat; gamma) -> C`，形成 reducer candidates；`SemanticReduce(C; rho) -> H_0`，得到初始 incident hypotheses；`Edit(C, H_0; a) -> Delta`，其中 `a` 只能是 `KEEP/MERGE/SPLIT/ABSTAIN`；`Validate(H_0, Delta, E_hat; V) -> H`，负责 schema、root/affected、一致性、evidence reference 和 fallback；最后由 `ReportTrace(H, E_hat, T; tau)` 生成可审计报告。这个表达式让 SAGE 的贡献更清楚：LLM 不是自由写结论，而是在受限的 `Edit` 算子里做 bounded semantic decision；系统负责 evidence binding、合法 JSON 组装、验证和 trace。

在 Semantic MapReduce 中，map 阶段不只是扫描数据，而是在每个 shard 上提取局部异常、摘要和候选证据。例如在 LLM serving telemetry 中，每个 shard 可以按 service、region、time window 计算 p95 latency、error rate、NPU utilization 和 queue depth，并输出异常候选。reduce 阶段则把来自不同 shard 的候选按语义目标合并：相邻窗口可能属于同一 incident，不同信号可能共同指向 queue backlog 或 NPU saturation，孤立低置信度信号可能被保守过滤。final 阶段再把结构化 hypothesis 转换为给 operator 可读、可审计的报告。

SAGE 当前仓库已经具备支撑这一方向的核心系统边界。README 将 SAGE 定义为把 LLM reasoning workflows 显式化为 dataflow pipelines 的框架；`DataStream` 提供 map、filter、flatmap、keyby、connect 等 stream pipeline 组合；`LocalEnvironment` 和 `FlowNetEnvironment` 提供本地和可选分布式执行入口；serving 模块则明确把 inference engine 放在外部，通过 OpenAI-compatible gateway contract 和外部引擎集成。这意味着 SAGE 的合理定位不是“又一个数据执行引擎”，而是面向 LLM-augmented reasoning 的 workflow/runtime/orchestration 层。

为了把这个方向落到可测对象上，我们新增了 `large_scale_analysis_workload.py`。该 workload 模拟 NPU-backed LLM serving 平台产生的大规模 telemetry。服务包括 prefill、decode、kv-cache、scheduler、router、embedding；事件包含 service、tenant、region、latency、error flag、NPU utilization 和 queue depth。生成器会注入隐藏 incident，包括 latency spike、NPU saturation 和 queue backlog。系统需要从事件流中恢复这些 incident。

当前实现把 deterministic 与 hybrid reducer 作为可复现 baseline，同时保留真实 OpenAI-compatible reducer 路径来测试接口、结构化输出、token/latency 和 fallback 机制。这里的核心系统挑战是：LLM reducer 可能漏报、过合并、输出结构不稳定、证据引用不完整，并且带来额外成本。SAGE 的重点是把这些行为放进同一个 evidence schema、scorer、trace 和 validator 中，而不是让一个 prompt 隐式决定所有语义边界。仓库中同时提供 `map-only` 与 `window-aggregate` 两个诊断 baseline：前者模拟只报告 shard-local alert、不做全局 reduce 的工作流；后者模拟传统窗口聚合，只把同一 service/region/window 的候选合并，但不把相邻窗口聚成 incident。`llm-stub` reducer 用来固定离线接口位置；真实模型路径则通过 validated candidate editing 来约束。

在当前 10-seed 大规模 telemetry 矩阵中，tail-aware evidence policy 下，`map-only` 的 mean F1 为 0.3075，`window-aggregate` 为 0.7129，deterministic incident reducer 为 0.9579。这个结果说明 proposal 不是普通 agent workflow：在相同 generator、evidence schema、scorer 和 report contract 下，显式 SemanticReduce 把输出单位从 alert/window fragments 改成 incident hypotheses，并显著减少重复报告。后续 baseline-aware evidence policy 进一步把低 baseline 服务上的 latency spike 纳入 evidence，使 deterministic reducer 在 50K/100K 10-seed 矩阵上达到 1.0000 mean precision/recall/F1；这不是“调参掩盖问题”，而是 operator boundary 的价值：trace 能告诉我们问题发生在 MapEvidence policy，而不是笼统归咎于 LLM 或 reducer。

为了把 LLM reducer 的挑战机制化，我们又加入 semantic-merge suite。主论文矩阵包含 single-service、cascade、shared-bottleneck、concurrent、false-correlation、partial-evidence 和 ambiguous-overmerge 七类场景。七场景 10-seed 聚合下，`map-only` F1 为 0.0906，`service-local` 为 0.0922，`window-aggregate` 为 0.4531，`semantic-graph` 为 0.7696，`hybrid-hint` 为 0.8173。`partial-evidence` 暴露的是缺少 root evidence 时 affected-service contract 的问题，`hybrid-hint` 把该场景 F1 从 0.5761 提高到 0.8878；`ambiguous-overmerge` 暴露的是两个相关 incident 被压成一个 candidate 时需要 safe split 的问题。这些场景把 Semantic MR 必须处理的 reducer challenge 转成了可复现的机制测试。

真实 LLM 路径的实机结果也按同样逻辑解释。full-evidence prompting 在三个 hard semantic-merge 场景上都只有 F1 0.4000，说明“把 evidence 全塞给模型”会丢 incident unit 和 evidence links；raw `llm-hybrid` 则暴露了 candidate editing 的机会和风险：它在 ambiguous-overmerge 上把 F1 从 0.8571 提高到 1.0000，说明 split 操作确实是 semantic reducer 需要的能力；但它在 partial-evidence 上又加入额外碎片，把 F1 从 1.0000 降到 0.6667。`llm-hybrid-validated` 通过 schema validator、coverage validator、root/affected consistency、evidence-reference validator 和 fallback，把不合格编辑转成可审计的 rejected operation，并保持 hybrid baseline。这里的贡献不是说 LLM 已经稳定赢 deterministic，而是证明：一旦把 LLM 作为 semantic reducer，就必须有 validated candidate editing 和 no-regression fallback。

最近一轮 ambiguous candidate stress suite 进一步把问题压到“accepted LLM edit 能否稳定超过 hybrid-hint”。我们新增了 `ambiguous-disconnected-merge` 和 `ambiguous-temporal-split` 两类场景：前者让同一上游 incident 通过弱连接服务碎片出现，后者让同一 incident 以分离时间片出现。离线 smoke 中三类 stress case 的 evidence coverage 都是 1.0，但 `semantic-graph` 只有 F1 0.3463，`hybrid-hint` 为 0.6948，说明问题不在 map coverage，而在 semantic merge。mocked LLM edit 单测证明，validated contract 可以接受 evidence-preserving merge 并把 hard case 修到 F1 1.0；但 NPU3 上的 Qwen2.5-7B 实机并没有稳定给出这种 accepted merge。raw `llm-hybrid` 在该 stress suite 上 F1 只有 0.1717，`llm-openai` 为 0.2667，`llm-hybrid-validated` 通过 fallback 保持 0.6948。后续 probe 显示模型会返回 `{}`、合法但无 merge 的 keep/edit payload，或在更长 merge-hint prompt 下输出非 JSON 文本。这个结果不应包装成胜利；它把下一刀明确成系统问题：需要更短的 candidate compression、merge-pair accept/reject contract，或 grammar/JSON-schema 级结构化解码，才能让 accepted LLM edits 真正稳定超过 deterministic hybrid。

进一步收紧后，pairwise constrained interface 给出了第一条更积极的实机信号。`llm-pairwise` 不再让模型生成完整 hypothesis，而是由系统提出短候选对，模型只回答 `merge`/`keep`/`split`、复制 evidence ids、给一个短 reason。在 `ambiguous-disconnected-merge` 上，raw pairwise 路径返回合法 JSON，接受 3 个 evidence-preserving merges，把 F1 从 `hybrid-hint` 的 0.7273 提高到 1.0000，token 估计约 530。这个结果说明“受约束 edit interface”确实能让真实 LLM 在 hard semantic merge 上产生增益。但独立的 `llm-pairwise-validated` 调用仍会因为缺少 required `decisions` list 或非 JSON 输出而 fallback，即使加了一次 retry。

最新一轮把输出约束继续推进到 one-token action classification。`llm-pairwise-action-validated` 只允许模型在 `KEEP`、`MERGE`、`SPLIT`、`ABSTAIN` 中选一个 token；合法 JSON edit 由系统根据候选对和 evidence ids 组装，然后再经过 schema、root/affected、evidence-reference 和 fallback validator。在 NPU3 Qwen2.5-7B 的三个 hardcase 上，旧 free-form pairwise reducers 仍然全部 invalid schema 或 fallback，而 action-validated path 没有 invalid action、没有 invalid schema、没有 fallback，mean F1 从 `hybrid-hint` 的 0.6948 提高到 0.8857。`ambiguous-disconnected-merge` 达到 F1 1.0000，`ambiguous-temporal-split` 从 0.5000 提高到 0.8000 但仍有 over-report，`ambiguous-overmerge` 则返回 `ABSTAIN` 并保持 baseline。这不是“LLM reducer 全面胜利”，而是更有系统味道的结论：Semantic Reduce 不应该让模型自由写 reducer JSON；模型只做受约束语义判断，系统负责组装、验证、审计和回退。

这组对比不是完整的 SOTA 系统实验；它更像 state-of-practice proxy baseline，用同一 generator、map outputs、evidence schema 和 scorer 隔离“semantic reduce”本身的价值。真正对 Spark/Flink/Ray/LangGraph/LlamaIndex/AutoGen 这类系统做公平比较，需要为它们实现相同 evidence contract 的 adapter，并保证输出用同一个 incident matcher 打分。当前结果可以支持较窄但有用的 claim：在这个 workload 中，incident-level semantic reduction 显著优于 map-only alert 和简单 window aggregation。

为了进一步检查“能不能和相邻系统放在同一实验框架下比较”，我们又做了一个 adapter-level comparison。这个实验固定 synthetic generator、evidence schema、deterministic reducer 和 scorer，只替换外层编排/封装路径：`sage-local` 使用原生 workload 路径，`ray-local` 用 Ray local task 执行 shard map，`langgraph-local` 用 LangGraph `StateGraph` 封装 generate/map/reduce 节点，`llamaindex-docstore` 把候选 evidence 包装为 LlamaIndex-core `Document` 并写入 `SimpleDocumentStore`。结果保存在 `.sage/benchmarks/large_scale_analysis_adapters/20260630T-adapter-comparison-steady/`。四个 adapter 的 mean F1 都是 0.9392，这是预期结果，因为 reducer 和 scorer 完全相同；更有意义的是本地封装开销：SAGE local、LangGraph local、LlamaIndex docstore 和 Ray local 的 mean throughput 分别约为 58,594、60,051、61,519 和 39,739 events/s。Ray local 这一行运行时出现了 NPU detection 与 `/tmp/ray` 空间告警，因此只能作为本机诊断数据，不能解释为调优 Ray cluster 的性能结论。

在真实执行面上，我们还做了小规模 real-online readiness 和 reducer smoke：通过本仓库 pinned 的 `external/vllm-hust-dev-hub/manage.sh` 在 NPU3 上启动 vLLM-HUST，并用项目专属 `esage-vllm-hust-dev` conda 环境发起 OpenAI-compatible 请求。启动过程中也暴露了运行时可复现性问题：dev-hub 默认寻找 sibling `ascend-runtime-manager`，而本课题要求使用 `third_party/ascend-runtime-manager` submodule；容器还需要显式挂载 `/data` 才能访问模型。因此我们在 runtime manager submodule 中加入了可配置 extra mounts，并在实验 provenance 中记录 manager 源码路径、模型、endpoint、eager fallback 和 submodule commits。这个结果不是 SOTA 性能对比，而是说明 SAGE 的实验路径已经可以从 orchestration workload 走到真实 vLLM-HUST endpoint，并能记录 latency/token/cost 这类 LLM semantic reducer 必需的成本指标。

这个多 seed 结果比单次满分更有价值，因为它把系统挑战分解成可定位的 operator 问题。MapEvidence policy 决定 incident 是否进入 evidence set；SemanticReduce 决定 evidence 是否被合并成正确 hypothesis；ReportTrace 决定每个 match、miss、false positive 是否能被审计。对于 ASPLOS 风格的系统论文，这种分解比“LLM 是否回答对了”更重要：它让我们能设计 coverage gate、deterministic baseline、LLM-hybrid validator、structured output readiness probe、cost/latency accounting 和 trace audit。

与现有系统相比，SAGE 的位置需要谨慎表述。Spark 和 Flink 是强大的 batch/stream 执行引擎，适合 scan、join、window aggregation 和状态计算；Ray 是通用分布式 AI/Python compute runtime；LangGraph、LangChain、AutoGen 更强调 agent 或 workflow 编排；LlamaIndex 强在数据连接、索引和 RAG；Databricks、Snowflake Cortex、BigQuery ML 等 data+AI 平台提供深度集成能力。这些方向都需要进一步系统调研。SAGE 的差异化不应建立在“别人不能做”这种夸张判断上，而应建立在更精确的边界上：SAGE 把 LLM reasoning workflow 作为显式 dataflow/stream/runtime 对象，并强调 semantic reduce、auditable evidence 和与外部数据系统的开放集成。

因此，这篇文章的核心贡献可以谨慎概括为三点。第一，提出 Semantic MapReduce 作为大规模数据上 LLM-native analysis 的系统抽象：局部 evidence extraction，全局 semantic reduction，可追溯 explanation。第二，明确 SAGE 在该抽象中的定位：它不是底层执行引擎替代品，而是 AI-native orchestration layer。第三，通过 large-scale analysis workload 给出一个可复现 baseline，展示 shard-level analysis 和 deterministic incident reduction 的可行性，同时暴露当前 reducer 在 precision/recall 上的改进空间。

下一步最小增强不是再写一个更长 prompt，而是把 one-token action reducer 做成更稳定的实验主线：从 clean commit 复跑多 seed hardcase，加入 batched pair judging、candidate compression 和 temporal grouping 约束，比较 accepted edit count、fallback rate、invalid action、invalid schema、token/latency 与 F1/support recall。只有当这个 validated path 在更宽场景上稳定超过 hybrid-hint，文章才能把它写成强质量 claim；在那之前，它已经足以支撑一个清晰的系统 claim：LLM semantic reducer 需要 constrained edit interface。

## English Abstract

Large-scale data systems efficiently scan, join, and aggregate massive datasets,
but they do not directly solve semantic interpretation tasks such as evidence
fusion, incident hypothesis generation, explanation, and auditable reasoning.
Simply attaching an LLM to a database or log store is also insufficient: the
context is too large, intermediate evidence is hard to audit, and global
conclusions must be derived from partitioned observations. This report sketches
SAGE as an AI-native orchestration layer for large-scale LLM-augmented data
analysis. Rather than replacing Spark, Flink, Ray, databases, or vector systems,
SAGE coordinates workflow and stream pipelines above or alongside them. We frame
the core abstraction as Semantic MapReduce: shard-level map stages extract local
evidence and anomaly candidates, semantic reduce stages merge related evidence,
remove duplicates, handle conflicts, and form structured hypotheses, and final
stages generate traceable explanations. We introduce a synthetic large-scale
analysis workload based on NPU-backed LLM serving telemetry, with injected
latency spikes, NPU saturation, and queue backlog incidents. Across a small
multi-seed matrix, the deterministic reducer baseline reaches mean precision
0.9579 under a tail-aware evidence policy, compared with 0.3075 for map-only
alerts and 0.7129 for window aggregation. A seven-family semantic-merge suite
further shows that map-only, service-local, and window aggregation fail to
recover incident-level hypotheses under cascade, false-correlation,
partial-evidence, and ambiguous-overmerge cases. Live LLM reducer probes expose
the core systems challenge: raw model calls may return valid JSON while losing
incident units or evidence links, and unconstrained candidate edits may regress
quality. SAGE addresses this with an explicit evidence schema, deterministic
baselines, coverage gates, validated candidate editing, no-regression fallback,
token/cost accounting, and auditable workflow traces.

## Slide Outline

### 1. Why LLMs Need Data-System Orchestration

Key message: LLMs should analyze data pipelines, not only chat over data.

- Traditional systems solve scan/join/aggregate.
- Operators need explanation, hypotheses, and evidence.
- Direct DB-to-LLM workflows fail under scale and audit constraints.
- SAGE targets the orchestration layer between engines and LLM reasoning.

Suggested figure: data systems below, SAGE orchestration in the middle, LLM
interpretation above.

### 2. Problem Statement

Key message: Large-scale LLM analysis is evidence reduction under scale
constraints.

- Inputs: events, logs, metrics, traces, documents, experiment results.
- Outputs: structured insights, incident hypotheses, explanations, actions.
- Core challenges: coverage, semantic merge, LLM output validity, evidence
  references, latency/cost, auditability.
- Additional constraints: latency, cost, and safety boundaries.

Suggested figure: many event shards flowing into structured incident reports.

### 3. From MapReduce to Semantic Reduce

Key message: Map/reduce remains useful, but reduce becomes semantic.

- Map extracts local evidence and anomaly candidates.
- Reduce merges related candidates across shards.
- Conflicts, duplicates, weak signals, and over-merged candidates become
  explicit reducer challenges.
- Final output must link claims back to evidence.

Suggested figure: classic MapReduce versus Semantic MapReduce.

### 4. SAGE Positioning

Key message: SAGE is an AI-native orchestration layer, not a Spark/Flink
replacement.

- Stream-first dataflow API.
- Local and FlowNet runtime entrypoints.
- External inference-engine boundary.
- Can sit above or beside Spark, Ray, Flink, DBs, and vector systems.

Suggested figure: layered stack from data engines to SAGE to LLM reducers.

### 5. Workload Scenario

Key message: NPU-backed LLM serving telemetry is a natural semantic analysis
target.

- Services: prefill, decode, kv-cache, scheduler, router, embedding.
- Metrics: latency, error, NPU utilization, queue depth.
- Incidents: latency spike, NPU saturation, queue backlog.
- Goal: recover injected incidents from event streams.

Suggested figure: LLM serving platform emitting telemetry.

### 6. Workload Pipeline

Key message: Current implementation tests evidence extraction, semantic
reduction, and validated LLM reducer contracts under one scorer.

- Generate synthetic events and ground truth incidents.
- Partition events into shards.
- Map shard-level anomaly candidates.
- Reduce adjacent windows into incident hypotheses.
- Validate LLM candidate edits before accepting them.
- Score against injected ground truth.

Suggested figure: Generate -> Shard Map -> Reducer -> Explain -> Score.

### 7. Experimental Results

Key message: Explicit SemanticReduce beats alert/window baselines under the
same schema and scorer.

- Tail-aware large-scale matrix: map-only F1 0.3075, window F1 0.7129,
  incident reducer F1 0.9579.
- Baseline-aware evidence policy reaches 1.0000 deterministic F1 on the
  current 50K/100K 10-seed matrix.
- Seven-family semantic-merge suite: window F1 0.4531, semantic-graph F1
  0.7696, hybrid-hint F1 0.8173.
- Ambiguous-candidate stress suite: full evidence coverage; constrained raw
  pairwise editing can improve one hard merge case, while validated robustness
  still requires stronger structured output.
- Real-online LLM reducer probes record token/latency cost and edit/fallback
  behavior under the same scorer.

Suggested figure: result table plus precision/recall bars by seed.

### 8. What the Results Mean

Key message: LLM reducer instability is a systems challenge handled by
validation, not a footnote.

- Full-evidence prompting can lose incident units and evidence links.
- Raw candidate editing can produce incomplete split/merge edits or invalid
  structure.
- `llm-hybrid-validated` rejects unsafe edits and preserves no-regression.
- Coverage gates separate map evidence misses from reducer mistakes.

Suggested figure: detected versus missed incident timeline.

### 9. Related Systems and Boundary

Key message: Compare by layer, and use adapter experiments only for scoped claims.

- Spark/Flink/Hadoop: execution engines for batch/stream analytics.
- Ray: general distributed AI/Python compute runtime.
- LangGraph/AutoGen: agent and workflow orchestration.
- LlamaIndex: data connectors, indexing, and RAG workflows.
- Local adapter comparison: fixed reducer/scorer, wrapper overhead only.

Suggested figure: layer map plus small adapter comparison table.

### 10. Next Minimal Step

Key message: Stabilize the one-token action reducer before broad live runs.

- Rerun `llm-pairwise-action-validated` from a clean commit across more seeds
  and hardcase families.
- Preserve evidence object schema, missed-incident reporting, and validators.
- Keep token/cost accounting attached to every accepted/rejected edit.
- Compare semantic-graph, hybrid-hint, free-form pairwise, action-validated
  pairwise, and full-evidence LLM on identical seeds.
- Compare with ground truth and, later, human analyst review.

Suggested figure: same map outputs feeding deterministic and LLM reducers.

## Claim Discipline

Supported by current code and workload:

- SAGE supports MapReduce-like semantic orchestration as a workload pattern.
- The workload demonstrates shard-level analysis and incident-level reduction.
- SAGE can be positioned as an orchestration layer above or beside data engines.
- Current benchmark reports precision, recall, F1, throughput, map latency,
  reduce latency, detected incidents, injected incidents, and missed incidents.

Not supported as current claims:

- SAGE replaces Spark, Flink, Ray, databases, or vector systems.
- This workload provides production-grade distributed shuffle.
- This workload has exactly-once fault tolerance.
- The current baseline is a real LLM semantic reducer.
- SAGE has no competitors.

## Next Mechanisms

- Treat constrained merge-pair actions as the default live LLM reducer
  interface before scaling live runs.
- Add batched pair judging and candidate compression to reduce token/latency
  overhead.
- Integrate external Spark/Ray/Flink/database scans as upstream data sources.
- Add workflow trace visualization for map candidates, reducer decisions, and
  final reports.
- Track token usage, monetary cost, and LLM latency.
- Add multi-modal evidence such as screenshots, traces, and experiment plots.
- Run on real vLLM-HUST/NPU telemetry rather than synthetic events.
- Compare deterministic reducer, LLM reducer, and human analyst labels.
