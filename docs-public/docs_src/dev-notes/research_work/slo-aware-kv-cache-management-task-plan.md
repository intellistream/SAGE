# SLO-Aware KV Cache Management Work Plan

## Gap Snapshot (2025-12-02)

**sageLLM Control Plane (`packages/sage-llm-core/src/sage/llm/control_plane/`)**

- No `memory_manager/` package yet; `ControlPlaneManager` only tracks queues and GPU reservations
  without per-request KV/embedding memory budgets.
- `RequestMetadata` and `ExecutionInstance` lack fields for predicted KV cache size, active
  embedding workspace, or SLO slack needed for eviction heuristics.
- Missing predictors for output length and embedding load despite references in the research
  proposal; `load_predictor.py` only handles aggregate request counts.
- No admission control hook in `_scheduling_loop`; requests are scheduled solely by policy outputs
  without checking available memory.
- No quota allocation or per-instance budgeting to partition memory between LLM and embedding jobs;
  `gpu_manager.py` exposes total reservations but not workload-aware shares.
- Eviction relies entirely on backend (vLLM) defaults; there is no SLO-aware block manager wrapper
  or telemetry about evictions in `metrics_collector.py`.
- Monitoring endpoints (`metrics_collector`, `monitoring`) expose throughput/latency only; they do
  not publish KV cache pressure, predicted vs actual memory, or preemption counts.

**Benchmark Control Plane (`packages/sage-benchmark/src/sage/benchmark/benchmark_control_plane`)**

- Mixed workloads exist, but workload generators (`workload.py`, `hybrid_scheduler/workload.py`)
  cannot synthesize deterministic KV pressure (e.g., long decode bursts + large embedding batches)
  or annotate expected memory demand.
- Metrics collectors lack GPU memory attribution per request type; `gpu_monitor.py` captures coarse
  device stats without correlating against LLM vs embedding queue states.
- No experiment tracks SLO attainment under memory stress; existing experiments (throughput,
  latency, mixed ratio) lack knobs for quota policies or admission controllers.
- CLI/runner plumbing has no notion of memory-focused policies (e.g., toggling eviction strategies)
  and cannot surface KV eviction counts from Control Plane telemetry.
- There is no automated regression harness to validate new memory manager modules or ensure
  prompts/forecasters stay calibrated.

## Sequential Task Groups & Prompts

Each group must be completed in order. Tasks inside the same group can run in parallel. Task IDs are
unique and referenced by prompts.

### Group 1 – Telemetry & Predictors (establish data plumbing)

#### T1 – Memory Telemetry Surfaces

- **Goal**: Extend `RequestMetadata`, `ExecutionInstance`, and monitoring paths so every request and
  instance reports predicted vs actual KV/embedding memory, SLO slack, and eviction counters.
- **Key Files**: `control_plane/types.py`, `control_plane/monitoring.py`,
  `control_plane/metrics_collector.py`, `control_plane/executors/*`.
- **Deliverable**: Structured dataclasses plus serialization hooks that expose `kv_cache_tokens`,
  `embedding_workspace_mb`, `slo_slack_ms`, and `eviction_events`.
- **Prompt (T1)**:
  > Implement per-request and per-instance memory telemetry across the sageLLM Control Plane. Add
  > explicit fields to `RequestMetadata` and `ExecutionInstance` for predicted/actual KV cache size,
  > embedding workspace consumption, and SLO slack. Ensure `MetricsCollector` and `monitoring`
  > endpoints expose these metrics and that executors populate them when requests start/finish.
  > Update docstrings/tests accordingly.

#### T2 – Predictive Signal Providers

- **Goal**: Add dedicated predictors for output length and embedding batch memory under
  `control_plane/predictors/` and expose them through a registry.
- **Key Files**: new `predictors/output_length_predictor.py`,
  `predictors/embedding_load_forecaster.py`, updates to `load_predictor.py` and
  `ControlPlaneManager` constructor.
- **Deliverable**: Interfaces that can return confidence intervals for KV size and embedding
  reservations, plus unit tests with synthetic traces.
- **Prompt (T2)**:
  > Create predictor modules that estimate (a) LLM output length / KV cache footprint from prompt
  > features and (b) embedding batch memory from queue state. Place them under
  > `control_plane/predictors/`, provide a pluggable registry, expose calibration hooks, and write
  > unit tests covering constant/moving-average baselines and mock ML models. Wire the predictors
  > into the Control Plane so future modules can request forecasts.

### Group 2 – Core Memory Manager (admission, quotas, eviction)

#### T3 – Embedding-Aware Admission Controller

- **Goal**: Build `memory_manager/admission_controller.py` implementing Algorithm 1, invoking
  predictors plus telemetry before enqueuing LLM jobs.
- **Key Files**: new directory `control_plane/memory_manager/`, integration in
  `ControlPlaneManager.submit_request` / `_scheduling_loop`.
- **Deliverable**: Configurable controller with defer/reject/preempt decisions, safety margins, and
  instrumentation hooks.
- **Prompt (T3)**:
  > Introduce `memory_manager/admission_controller.py` that consumes predictor outputs and live
  > telemetry to decide ADMIT/DEFER/REJECT/PREEMPT for incoming requests. Embed policy parameters
  > (safety ratios, defer thresholds) in a dataclass, expose async hooks for the Control Plane, and
  > log structured reasons for tracing. Cover edge cases (unknown output length, predictor failure)
  > with fallbacks.

#### T4 – SLO-Driven Quota Allocator

- **Goal**: Implement Algorithm 2 inside `memory_manager/quota_allocator.py` to rebalance LLM vs
  embedding budgets per instance and system-wide.
- **Key Files**: new allocator module, updates to `ControlPlaneManager`, `ExecutionInstance`,
  `autoscaler.py`.
- **Deliverable**: Smooth quota adjustments with urgency scoring and integration tests verifying
  stability.
- **Prompt (T4)**:
  > Add a quota allocator that periodically recomputes LLM and embedding memory shares using SLO
  > urgency scores. Provide APIs to query/set per-instance budgets, ensure adjustments obey min/max
  > limits, and persist recent history to damp oscillations. Wire it into the scheduling loop and
  > autoscaler so load spikes trigger quota shifts without thrashing.

#### T5 – SLO-Aware KV Eviction & Block Manager Hook

- **Goal**: Wrap vLLM block management with a SLO-aware eviction policy (Algorithm 3) and expose
  eviction telemetry.
- **Key Files**: new `memory_manager/eviction_policy.py`, adapter class (e.g.,
  `SLOAwareBlockManager`), updates under `service.py` or executor layer.
- **Deliverable**: Eviction selection logic plus integration tests using mocked block allocations.
- **Prompt (T5)**:
  > Implement a SLO-aware KV eviction component that scores active requests by slack, priority, and
  > recompute cost, selects victims greedily, and instructs the vLLM block manager wrapper to evict
  > blocks. Ensure the wrapper surfaces eviction events to telemetry, handles near-completion
  > protection, and cleanly falls back if eviction cannot free enough memory.

### Group 3 – Control Plane & Policy Integration

#### T6 – Control Plane Wiring & APIs

- **Goal**: Thread the new memory manager through `ControlPlaneManager`: lifecycle management,
  configuration, background loops, and REST/CLI toggles.
- **Key Files**: `control_plane/manager.py`, `control_plane_service.py`, config schemas, CLI glue.
- **Deliverable**: Configurable feature flags plus admin APIs to inspect memory state and override
  policies.
- **Prompt (T6)**:
  > Integrate the admission controller, quota allocator, and eviction policy into
  > `ControlPlaneManager`. Add configuration options (env + JSON) to enable/disable each module,
  > expose health/metrics endpoints for memory state, and ensure the manager starts/stops background
  > tasks cleanly. Update client/service layers so users can set memory-policy parameters via
  > presets.

#### T7 – Policy, Router, and Autoscaler Updates

- **Goal**: Teach `HybridSchedulingPolicy`, PD router, and autoscaler to consume memory budgets and
  predicted conflicts.
- **Key Files**: `strategies/hybrid_policy.py`, `pd_routing.py`, `autoscaler.py`, `router.py`.
- **Deliverable**: Priority adjustments based on quotas, ability to reserve memory for incoming
  embedding batches, and autoscaler signals tied to memory strain.
- **Prompt (T7)**:
  > Modify scheduling and routing layers so embedding batches reserve quota before dispatch, mixed
  > instances respect per-type budgets, and autoscaler decisions incorporate memory pressure (e.g.,
  > sustained quota deficits). Include tests showing queue drains when memory frees up and
  > documentation for new policy behaviors.

### Group 4 – Benchmark & Evaluation Enhancements

#### T8 – Memory-Stress Workload Generator & Datasets

- **Goal**: Extend `HybridWorkloadGenerator` and base workloads to synthesize configurable KV
  footprints, embedding bursts, and correlated arrival traces; add sample datasets under
  `data/model_context/`.
- **Key Files**: `benchmark_control_plane/workload.py`, `hybrid_scheduler/workload.py`, dataset
  README.
- **Deliverable**: YAML-driven workload profiles that specify prompt/response length distributions,
  embedding batch waves, and SLO envelopes.
- **Prompt (T8)**:
  > Enhance workload generators so benchmark configs can dictate KV cache pressure (e.g., long
  > decode tails) and embedding surges. Add dataset loaders that annotate expected memory per
  > request, update config schemas, and provide sample YAML profiles plus documentation.

#### T9 – Memory-Centric Metrics & Telemetry Plumbed Through Benchmarks

- **Goal**: Capture Control Plane memory stats, GPU monitor data, and SLO outcomes in benchmark
  outputs.
- **Key Files**: `benchmark_control_plane/client.py`, `metrics.py`, `hybrid_scheduler/metrics.py`,
  `common/gpu_monitor.py`, visualization utilities.
- **Deliverable**: Reports highlighting SLO attainment vs memory usage, eviction counts, quota
  shifts, with charts for P99 TTFT/TPOT under stress.
- **Prompt (T9)**:
  > Extend benchmark clients to request the new memory telemetry endpoints, tag each request with
  > predicted vs actual memory, and aggregate results into the metrics collectors. Update GPU
  > monitor summaries to align with Control Plane data, surface everything in JSON reports, and add
  > charts for quota utilization and SLO attainment.

#### T10 – Dedicated Memory Benchmark Suite & CLI Hooks

- **Goal**: Create `benchmark_control_plane/memory_benchmark/` with workload generators, metric
  evaluators, CLI commands, and documentation that replicate the proposal’s experiments.
- **Key Files**: new package directory, `cli.py`, `runner.py`, docs.
- **Deliverable**: Commands like `sage-cp-bench run --mode memory` plus comparison tooling.
- **Prompt (T10)**:
  > Add a memory-focused benchmark suite featuring scripts/tests that sweep workload ratios, quota
  > configs, and eviction policies. Provide CLI commands to trigger these scenarios, emit CSV/JSON
  > summaries for plotting, and ensure results include derived metrics (SLO attainment, throughput,
  > fairness) required by the research plan.

### Group 5 – Validation, CI, and Documentation

#### T11 – Regression Tests & CI Wiring

- **Goal**: Add unit/integration tests plus CI targets that cover predictors, admission decisions,
  quota convergence, and benchmark CLI smoke tests.
- **Key Files**: `packages/sage-common/tests`, `packages/sage-benchmark/tests`, `tools/pytest.ini`,
  GitHub workflows.
- **Deliverable**: Repeatable test matrix (CPU-friendly mocks) and optional nightly GPU job specs.
- **Prompt (T11)**:
  > Expand the test suite to cover the new memory manager components (unit tests with mocked
  > predictors/GPU stats) and add integration tests that run the benchmark CLI in mock mode. Update
  > pytest config and CI workflows so these tests run in PRs (CPU) and optionally in nightly GPU
  > pipelines.

#### T12 – Documentation & Research Artifacts

- **Goal**: Update the research proposal, developer docs, and tutorials with architecture diagrams,
  configuration guides, and benchmark instructions.
- **Key Files**: `docs/dev-notes/research_work/*.md`, `docs/dev-notes/l3-l6/*`,
  `docs-public/docs_src`.
- **Deliverable**: User-facing guide for enabling SLO-aware memory management plus reproducibility
  appendix.
- **Prompt (T12)**:
  > Refresh the documentation to describe the new memory management stack end-to-end. Update the
  > research proposal with implementation details, add developer guides explaining configuration
  > knobs, and provide HOWTOs for running the memory benchmark suite. Include diagrams, config
  > snippets, and troubleshooting tips.

## Execution Diagram

```
[Group 1: Telemetry & Predictors (T1,T2)]
          |
          v
[Group 2: Core Memory Manager (T3,T4,T5)]
          |
          v
[Group 3: Control Plane Integration (T6,T7)]
          |
          v
[Group 4: Benchmark & Evaluation (T8,T9,T10)]
          |
          v
[Group 5: Validation & Docs (T11,T12)]
```
