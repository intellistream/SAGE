# LLM Serving Research Topics — Promising Lines for Team Reference

> Evaluated on problem definition quality, motivation strength, and research prospects (not implementation status).

---

## Tier 1 — Sharp Problems with Compelling Motivation

### 1. Adaptive Decode Backend Selection

Modern LLM serving runtimes ship multiple decode backends (FlashAttention, FlashInfer, etc.) but select among them via static priority — even though the fastest backend changes with batch shape, context length, and runtime state. Measured on A100, static FlashAttention is 42.5% slower than the region oracle on average, showing that static dispatch leaves large structured loss on the table. The research question is whether bounded online control over already-available backends can recover that loss under real serving conditions.

### 2. Transition-Aware Decode Preparation

Steady-state decode benchmarks can look healthy while users experience large latency spikes when the runtime first encounters a new decode shape. On SGLang, a simple 1→2→1→2 batch transition causes a 24× spike (2.5ms → 60ms) due to unnecessary lazy specialization on the metadata path — a root cause localized to a single function. The research question is whether first-use specialization exposure should be treated as user-visible runtime state and prepared eagerly, rather than left to accidental lazy execution.

### 3. Beyond-Prefix Exact Reuse (Segment Reuse)

Strict prefix caching is the wrong reuse abstraction for structured serving workloads (agent pipelines, workflow orchestration, semi-templated traffic), where a short dynamic envelope hides a long stable prompt body. Across a 72-request workload, strict prefix reuse covers only 17% of tokens while exact structural reuse reaches 78% — a 4.5× gap. The research question is whether a minimal mechanism (one fresh leading envelope + one exact reused body) can capture most of this gap without full segment composition.

### 4. Topology-Aware Continuation Placement

In continuation-anchored LLM serving (multi-turn, RAG follow-up, agent loops), decode placement is treated as location-free load balancing — but once useful state exists on one worker, the controller's placement decision either preserves locality or forces a more expensive remote path. Default SGLang produces 50.3% cross-node decode share; a topology-aware controller cuts that to 19.5% and wins on throughput across all seven continuation-anchored scenarios on 8-card Ascend 910B1. The research question is whether controller-visible topology pricing is sufficient to recover a better operating point without redesigning any data-plane mechanism.

---

## Tier 2 — Concrete, Credible Problems

### 5. Incremental KV Transfer for Repeated Handoff (DeltaKV)

In disaggregated LLM serving, rolling maintenance and preemption force repeated KV state transfers, but runtimes export full block-set images each time — even though state growth is mostly append-only. An incremental delta protocol achieves 78%–97% byte reduction (~90% average) on repeated movement traces. The research question is whether incremental transfer can be made latency-neutral under realistic transport settings, turning a protocol opportunity into an end-to-end serving win.

### 6. Workload-Grounded Prefix Sharing Control (PrefixWeave)

KV prefix sharing evaluations commonly blur three distinct questions: whether two requests truly share an exact prefix, whether the runtime can materialize that reuse at the right boundary, and whether the workload actually improves end-to-end. The research contribution is architectural: separating prefix identity, sharing eligibility, and runtime realization into explicit control surfaces with a staged evidence ladder (observe → probe → real-hook), so that overlap ratios are not mistaken for serving benefit.

### 7. Adaptive KV Materialization Control

When reusable KV state exists but resides on another worker or requires transfer/stitching, the runtime faces a three-action decision: fully materialize, partially materialize a profitable segment, or recompute from scratch. This reframes prefix reuse from a binary cache-hit classifier to a cost-benefit control problem, directly relevant to disaggregated serving systems like DistServe and Mooncake where reuse is never free.

---

## Tier 3 — Interesting Directions with Higher Uncertainty

### 8. Shared Execution as Global Planning (MottoServe)

High-concurrency LLM services execute requests that are surface-different but structurally similar — same system prompts, overlapping retrieval targets, same tool pipelines. The thesis is that a global planner should rewrite requests into canonical structure and select which cross-request sharing bundles to materialize under runtime budgets, rather than relying on stage-local caches that miss multi-surface alignment.
