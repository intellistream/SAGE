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

The current workload uses a deterministic reducer baseline by default. The
`llm-stub` reducer is a CI-safe integration placeholder and does not call an
external LLM. This document must therefore not claim that SAGE already performs
production-grade distributed shuffle, exactly-once fault tolerance for this
workload, real Spark/Ray backend execution, or end-to-end LLM semantic
reduction.

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

在 Semantic MapReduce 中，map 阶段不只是扫描数据，而是在每个 shard 上提取局部异常、摘要和候选证据。例如在 LLM serving telemetry 中，每个 shard 可以按 service、region、time window 计算 p95 latency、error rate、NPU utilization 和 queue depth，并输出异常候选。reduce 阶段则把来自不同 shard 的候选按语义目标合并：相邻窗口可能属于同一 incident，不同信号可能共同指向 queue backlog 或 NPU saturation，孤立低置信度信号可能被保守过滤。final 阶段再把结构化 hypothesis 转换为给 operator 可读、可审计的报告。

SAGE 当前仓库已经具备支撑这一方向的核心系统边界。README 将 SAGE 定义为把 LLM reasoning workflows 显式化为 dataflow pipelines 的框架；`DataStream` 提供 map、filter、flatmap、keyby、connect 等 stream pipeline 组合；`LocalEnvironment` 和 `FlowNetEnvironment` 提供本地和可选分布式执行入口；serving 模块则明确把 inference engine 放在外部，通过 OpenAI-compatible gateway contract 和外部引擎集成。这意味着 SAGE 的合理定位不是“又一个数据执行引擎”，而是面向 LLM-augmented reasoning 的 workflow/runtime/orchestration 层。

为了把这个方向落到可测对象上，我们新增了 `large_scale_analysis_workload.py`。该 workload 模拟 NPU-backed LLM serving 平台产生的大规模 telemetry。服务包括 prefill、decode、kv-cache、scheduler、router、embedding；事件包含 service、tenant、region、latency、error flag、NPU utilization 和 queue depth。生成器会注入隐藏 incident，包括 latency spike、NPU saturation 和 queue backlog。系统需要从事件流中恢复这些 incident。

当前实现采用 deterministic reducer baseline，而不是在线 LLM 调用。这是一个重要边界：它让 workload 可以在 CI 或普通开发环境中稳定运行，也让我们先测量 pipeline 结构本身，包括分片、局部证据抽取、全局 incident clustering 和解释生成。仓库中同时提供 `map-only` 与 `window-aggregate` 两个诊断 baseline：前者模拟只报告 shard-local alert、不做全局 reduce 的工作流；后者模拟传统窗口聚合，只把同一 service/region/window 的候选合并，但不把相邻窗口聚成 incident。`llm-stub` reducer 用来固定未来 LLM semantic reducer 的接口位置；它不访问外部服务，也不应被当成真实 LLM 实验结果。

我们在 `esage-vllm-hust-dev` 环境中把实验扩展为一个小矩阵：两个规模（50,000 events / 16 shards / top-k 12，以及 100,000 events / 32 shards / top-k 16）、三个 seeds（7、11、13）、四个 reducers（`map-only`、`window-aggregate`、deterministic 与 `llm-stub`）。结果保存在 `.sage/benchmarks/large_scale_analysis/20260630T-sota-proxy-baselines/`。跨 6 个配置聚合后，`map-only` 的 mean F1 为 0.2250，`window-aggregate` 为 0.7600，deterministic incident reducer 为 0.9392。`llm-stub` 与 deterministic 的指标完全相同，因为它当前只是离线 stub，会委托 deterministic reducer 做 evidence fusion。

这组对比不是完整的 SOTA 系统实验；它更像 state-of-practice proxy baseline，用同一 generator、map outputs、evidence schema 和 scorer 隔离“semantic reduce”本身的价值。真正对 Spark/Flink/Ray/LangGraph/LlamaIndex/AutoGen 这类系统做公平比较，需要为它们实现相同 evidence contract 的 adapter，并保证输出用同一个 incident matcher 打分。当前结果可以支持较窄但有用的 claim：在这个 workload 中，incident-level semantic reduction 显著优于 map-only alert 和简单 window aggregation。

为了进一步检查“能不能和相邻系统放在同一实验框架下比较”，我们又做了一个 adapter-level comparison。这个实验固定 synthetic generator、evidence schema、deterministic reducer 和 scorer，只替换外层编排/封装路径：`sage-local` 使用原生 workload 路径，`ray-local` 用 Ray local task 执行 shard map，`langgraph-local` 用 LangGraph `StateGraph` 封装 generate/map/reduce 节点，`llamaindex-docstore` 把候选 evidence 包装为 LlamaIndex-core `Document` 并写入 `SimpleDocumentStore`。结果保存在 `.sage/benchmarks/large_scale_analysis_adapters/20260630T-adapter-comparison-steady/`。四个 adapter 的 mean F1 都是 0.9392，这是预期结果，因为 reducer 和 scorer 完全相同；更有意义的是本地封装开销：SAGE local、LangGraph local、LlamaIndex docstore 和 Ray local 的 mean throughput 分别约为 58,594、60,051、61,519 和 39,739 events/s。Ray local 这一行运行时出现了 NPU detection 与 `/tmp/ray` 空间告警，因此只能作为本机诊断数据，不能解释为调优 Ray cluster 的性能结论。

在真实执行面上，我们还做了一个小规模 real-online readiness 实验：通过 `vllm-hust-dev-hub/scripts/run_vllm_hust_engine.sh` 在单张 Ascend 910B2 NPU（device 4）上启动 `/data/shared_models/Qwen2.5-7B-Instruct`，served model name 为 `qwen25-7b-sage-realonline`，TP=1，`max_model_len=1024`，`max_num_seqs=1`。实验使用 streaming `/v1/completions`，每组 2 个 warmup request 和 8 个 measured requests，`max_tokens=48`。concurrency=1 时，mean TTFT 为 117.69 ms，mean TPOT 为 70.18 ms，端到端 completion throughput 为 13.82 tokens/s；concurrency=2 时，mean TTFT 上升到 1494.64 ms，而 mean TPOT 仍为 70.24 ms，端到端 completion throughput 为 13.883 tokens/s。这个结果不是 SOTA 性能对比，而是说明 SAGE 的实验环境已经可以从 orchestration workload 走到真实 vLLM-HUST endpoint，并能记录 TTFT/TPOT 这类未来 LLM semantic reducer 必需的成本指标。concurrency=2 的 TTFT 增大是预期现象，因为服务被故意设置为 `max_num_seqs=1`，并发请求会排队。

这个多 seed 结果比单次满分更有价值。50,000 events 下，seed 7 能完整恢复 4/4 incident；但 seed 11 和 13 会报告 5 个 incident，其中 4 个匹配 ground truth，precision 降到 0.8。100,000 events 下，seed 11 和 13 是满分；但 seed 7 只检测到 3/4 incident，漏掉 scheduler/npu-a 上的 NPU saturation，recall 降到 0.75。这说明 workload 不是一个总能满分的 toy benchmark：当前阈值式 reducer 既可能产生 false positive，也可能漏掉部分弱信号。真正的 semantic reducer 可以尝试利用跨窗口上下文、服务依赖关系和历史 baseline 来提高 recall 或 precision，同时避免把噪声变成 false positive。

与现有系统相比，SAGE 的位置需要谨慎表述。Spark 和 Flink 是强大的 batch/stream 执行引擎，适合 scan、join、window aggregation 和状态计算；Ray 是通用分布式 AI/Python compute runtime；LangGraph、LangChain、AutoGen 更强调 agent 或 workflow 编排；LlamaIndex 强在数据连接、索引和 RAG；Databricks、Snowflake Cortex、BigQuery ML 等 data+AI 平台提供深度集成能力。这些方向都需要进一步系统调研。SAGE 的差异化不应建立在“别人不能做”这种夸张判断上，而应建立在更精确的边界上：SAGE 把 LLM reasoning workflow 作为显式 dataflow/stream/runtime 对象，并强调 semantic reduce、auditable evidence 和与外部数据系统的开放集成。

因此，这篇文章的核心贡献可以谨慎概括为三点。第一，提出 Semantic MapReduce 作为大规模数据上 LLM-native analysis 的系统抽象：局部 evidence extraction，全局 semantic reduction，可追溯 explanation。第二，明确 SAGE 在该抽象中的定位：它不是底层执行引擎替代品，而是 AI-native orchestration layer。第三，通过 large-scale analysis workload 给出一个可复现 baseline，展示 shard-level analysis 和 deterministic incident reduction 的可行性，同时暴露当前 reducer 在 precision/recall 上的改进空间。

下一步最小增强是把 deterministic reducer 与真实 LLM semantic reducer 放在同一接口下比较。当前代码已经提供 reducer abstraction 和 `llm-stub` placeholder；后续可以接入真实 LLM，保留 evidence object schema，记录 token/cost/latency，并在同一 seed、同一 incident ground truth 下比较 precision、recall、F1、evidence coverage 和 human analyst review。

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
0.9333, mean recall 0.9583, and mean F1 0.9392, while exposing both false
positives and a missed NPU-saturation incident. The current `llm-stub` reducer
matches the deterministic baseline because it is only an offline integration
placeholder, leaving real LLM-based semantic reduction as future work.

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
- Challenges: sharding, compression, semantic merge, auditability.
- Additional constraints: latency, cost, and safety boundaries.

Suggested figure: many event shards flowing into structured incident reports.

### 3. From MapReduce to Semantic Reduce

Key message: Map/reduce remains useful, but reduce becomes semantic.

- Map extracts local evidence and anomaly candidates.
- Reduce merges related candidates across shards.
- Conflicts, duplicates, and weak signals must be handled.
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

Key message: Current implementation tests shard analysis and deterministic
incident fusion.

- Generate synthetic events and ground truth incidents.
- Partition events into shards.
- Map shard-level anomaly candidates.
- Reduce adjacent windows into incident hypotheses.
- Score against injected ground truth.

Suggested figure: Generate -> Shard Map -> Reducer -> Explain -> Score.

### 7. Experimental Results

Key message: Multi-seed runs expose both false positives and false negatives.

- Deterministic mean precision/recall/F1: 0.9333 / 0.9583 / 0.9392.
- 50K seed 11/13: recall remains 1.0 but precision drops to 0.8.
- 100K seed 7: precision remains 1.0 but recall drops to 0.75.
- `llm-stub` matches deterministic because it is an offline fallback.
- Real-online vLLM-HUST readiness: Qwen2.5-7B on one 910B2 reaches mean
  TTFT 117.69 ms and mean TPOT 70.18 ms at concurrency 1.

Suggested figure: result table plus precision/recall bars by seed.

### 8. What the Results Mean

Key message: The baseline is useful because it is not perfect.

- High precision cases show reported incidents can match ground truth.
- 50K false positives and the missed scheduler saturation show threshold limits.
- The workload creates room for LLM-based semantic reduction.
- Current result is not an end-to-end LLM claim.

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

Key message: Compare deterministic and real LLM semantic reducers under one
workload.

- Keep the reducer interface stable.
- Preserve evidence object schema and missed-incident reporting.
- Add token/cost accounting.
- Run deterministic versus LLM reducer on identical seeds.
- Compare with ground truth and human analyst review.

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

## Future Work

- Replace the `llm-stub` reducer with a real LLM-backed semantic reducer.
- Integrate external Spark/Ray/Flink/database scans as upstream data sources.
- Add workflow trace visualization for map candidates, reducer decisions, and
  final reports.
- Track token usage, monetary cost, and LLM latency.
- Add multi-modal evidence such as screenshots, traces, and experiment plots.
- Run on real vLLM-HUST/NPU telemetry rather than synthetic events.
- Compare deterministic reducer, LLM reducer, and human analyst labels.
