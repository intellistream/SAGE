```markdown
# Paper 2 (SIAS) — Task Division Prompt

Purpose: provide assignment-ready prompts for every remaining SIAS workstream (implementation + experiments) so maintainers can copy a section into GitHub issues, PR descriptions, or multi-agent instructions. Distribute **this entire markdown file** to every agent; each agent only needs to complete the task that is explicitly assigned to them, but having full context avoids conflicting assumptions.

Usage flow:
1. Copy the relevant task block into an issue or agent chat.
2. Keep the full file attached/referenceable so agents can cross-check dependencies.
3. Each assignee must report progress + tests using the included template.

Scope clarifications:
- Code lives under `packages/sage-libs/src/sage/libs/sias/` unless otherwise noted.
- Benchmarks, datasets, and experiment scripts belong in **`packages/sage-benchmark/src/sage/benchmark/benchmark_agent/`** (do not create a parallel `benchmarks/` folder).
- Experiments should re-use the existing benchmark_agent tooling (configs, runners, CLI helpers).

---

## High-level work areas

1. StreamingImportanceScorer (SSIS)
2. ReflectiveMemoryStore
3. AdaptiveExecutor (pre/post verification + localized replanning)
4. MultiAgentRouter / Specialist Agents
5. Streaming Trainer (unified batch/stream interface)
6. Datasets & Benchmarks (Streaming Tool-Arena, Continual Tool Drop-In)
7. Experiments & Baselines (Paper 1 baselines + new ablations)
8. Tests & CI (unit/integration, GPU smoke tests)
9. Docs, LaTeX, Release & Submodule extraction

Each section includes: Goal, Deliverables, Acceptance, Estimate, and a ready-to-send assignment prompt.

---

## 1) StreamingImportanceScorer (SSIS)

- **Goal**: Implement the SSIS score \(I(x) = \alpha L_{grad} + \beta D_{ctx} + \gamma T_{exec}\) with configurable weights and incremental updates over streaming data.
- **Deliverables**: `packages/sage-libs/src/sage/libs/sias/scorer.py`, docstring/API reference, unit tests, a comparison script under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/experiments/paper2/ssis_vs_baselines.py`.
- **Acceptance**: Handles ≥200 samples/s on synthetic stream (adjust per hardware), beats random + pure uncertainty by ≥1.5% accuracy on the comparison script, tests cover cold start/high-throughput/weight-reload cases.
- **Estimate**: 2–4 weeks.

**Assignment prompt**:
```

Task: Implement StreamingImportanceScorer for SIAS. Area: SSIS Goal: Provide a plug-and-play scorer
with configurable α/β/γ that maintains incremental statistics and exposes update(), score(), and
top_k() APIs. Files (suggested): packages/sage-libs/src/sage/libs/sias/scorer.py and
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/experiments/paper2/ssis_vs_baselines.py
Tests required: pytest coverage for empty buffer, streaming spikes, weight reload; comparison script
outputs CSV with selectivity/accuracy columns. Estimate: 2–4 weeks. Notes: Re-use existing
SelectionSummary dataclasses; align logging with SAGE style.

```

---

## 2) ReflectiveMemoryStore

- **Goal**: Build a persistent streaming memory that supports append, summarization, pattern extraction, top-k retrieval by importance/time filters, plus snapshot/load APIs.
- **Deliverables**: `packages/sage-libs/src/sage/libs/sias/memory/store.py`, embedding adapter abstractions, optional FAISS/Annoy backend, insert/query latency microbenchmark under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/experiments/paper2/memory_latency.py`.
- **Acceptance**: Stores ≥100k episodes in-memory, query latency <100 ms for k=10, snapshot+restore round-trip with zero data loss, benchmark script reports throughput JSON/CSV.
- **Estimate**: 3–5 weeks.

**Assignment prompt**:
```

Task: Build ReflectiveMemoryStore with pluggable vector index. Area: Memory Goal: Deliver
MemoryStore.append/query/snapshot/load plus summarization hooks; support both in-memory numpy arrays
and FAISS-backed ANN. Files (suggested): packages/sage-libs/src/sage/libs/sias/memory/store.py,
.../memory/embeddings.py,
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/experiments/paper2/memory_latency.py
Tests required: pytest for snapshot round-trip, filter queries, FAISS optional path; latency script
covering 10k insert/query. Estimate: 3–5 weeks. Notes: Document memory footprint tuning knobs for
ICML supplement.

```

---

## 3) AdaptiveExecutor

- **Goal**: Add pre-condition verification, post-execution validation, and localized replanning when tool outputs deviate from expectations.
- **Deliverables**: `packages/sage-libs/src/sage/libs/sias/runtime/adaptive_executor.py`, integration with `orchestrator.py`, failure-injection tests under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/tests/runtime/test_adaptive_executor.py`.
- **Acceptance**: In simulated failure scenarios, adaptive executor recovers with ≤3 local retries and improves success rate vs naive re-run baseline; telemetry logs detail verifier decisions.
- **Estimate**: 2–3 weeks.

**Assignment prompt**:
```

Task: Implement AdaptiveExecutor with verifier + local replanner hooks. Area: Runtime Goal: When a
tool result mismatches expectations, run verifier.check(), call replanner.generate_local_fix(), and
only re-execute impacted sub-steps. Files (suggested):
packages/sage-libs/src/sage/libs/sias/runtime/adaptive_executor.py, .../workflow/orchestrator.py,
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/tests/runtime/test_adaptive_executor.py
Tests required: integration test that injects tool errors and asserts higher completion rate + fewer
restarts. Estimate: 2–3 weeks. Notes: Follow existing telemetry schema for metrics emission.

```

---

## 4) MultiAgentRouter / Specialist Agents

- **Goal**: Route tasks to specialist agents (Researcher, Coder, Analyst, Coordinator) with a streaming blackboard; only Coordinator publishes final answers.
- **Deliverables**: `packages/sage-libs/src/sage/libs/sias/agents/router.py`, role-specific agent stubs, collaborative demo under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/demos/paper2/multi_agent_collab.py`.
- **Acceptance**: Multi-agent demo shows ≥X% improvement on multi-hop tasks vs single-agent baseline or provides qualitative case studies; router exposes policies for role assignment.
- **Estimate**: 3–6 weeks.

**Assignment prompt**:
```

Task: Implement MultiAgentRouter and specialist roles. Area: Router Goal: Provide a router that
decomposes tasks, dispatches to specialist agents, and synchronizes via shared summaries;
Coordinator finalizes outputs. Files (suggested):
packages/sage-libs/src/sage/libs/sias/agents/router.py, .../agents/specialists/\*.py,
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/demos/paper2/multi_agent_collab.py
Tests required: scenario script comparing single vs multi-agent success; unit tests for routing
policies. Estimate: 3–6 weeks. Notes: Re-use planning/timing utilities from sage.libs.agentic where
possible.

```

---

## 5) Streaming Trainer

- **Goal**: Deliver a unified trainer that supports streaming + batch regimes, integrates SSIS coreset sampling, replay buffers, EWC-style regularizer, and optional PPO/DPO fine-tuning hooks.
- **Deliverables**: `packages/sage-libs/src/sage/libs/sias/training/streaming_trainer.py`, `.../batch_trainer.py`, configs under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/configs/paper2/`, runnable training scripts.
- **Acceptance**: Reproduces sample-efficiency improvements (streaming vs batch) on a small dataset, deterministic seeds, CLI entrypoint documented in README.
- **Estimate**: 4–6 weeks.

**Assignment prompt**:
```

Task: Implement unified Streaming Trainer. Area: Trainer Goal: Create trainer APIs supporting replay
\+ SSIS sampling, EWC regularizer, and optional PPO/DPO hooks with consistent logging. Files
(suggested): packages/sage-libs/src/sage/libs/sias/training/\*.py,
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/configs/paper2/streaming_trainer.yaml,
.../scripts/trainers/run_streaming_trainer.py Tests required: unit tests for replay scheduling +
regularizer, smoke training run (tiny dataset) that completes locally. Estimate: 4–6 weeks. Notes:
Provide metrics export compatible with ICML plots.

```

---

## 6) Datasets & Benchmarks

- **Goal**: Build Streaming Tool-Arena generator + Continual Tool Drop-In datasets, wire them into `benchmark_agent` runners.
- **Deliverables**: Data scripts under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/data/streaming_tool_arena/`, documentation, dataset samples, runner entrypoints.
- **Acceptance**: Scripts deterministically create datasets, at least three baselines run successfully via benchmark_agent CLI, metadata logged for paper tables.
- **Estimate**: 2–4 weeks.

**Assignment prompt**:
```

Task: Implement Streaming Tool-Arena + Continual Tool Drop-In datasets. Area: Data Goal: Provide
reproducible data generation scripts with config knobs and integrate them with benchmark_agent
runners. Files (suggested):
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/data/streaming_tool_arena/*.py,
.../data/continual_tool_drop_in/*.py, README snippets. Tests required: deterministic generation
test, CLI run that materializes sample datasets. Estimate: 2–4 weeks. Notes: Include license +
citation info for any external assets.

```

---

## 7) Experiments & Baselines

- **Goal**: Set up automated experiment pipelines (multi-seed, multi-method) that include ReAct, Reflexion, ToolLLM, Gorilla, AutoGPT, plus SIAS ablations.
- **Deliverables**: Scripts under `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/experiments/paper2/`, Slurm/CI snippets, result aggregation notebook producing figures/tables for ICML.
- **Acceptance**: Runs on 2×A100 within budget, exports CSV/JSON for Tables 1–4, generates plots (sample efficiency, forgetting curves, etc.).
- **Estimate**: 3–8 weeks (depends on scale).

**Assignment prompt**:
```

Task: Build Paper 2 experiment pipeline under benchmark_agent. Area: Experiments Goal: Automate
baselines + ablations with reproducible configs and artifact export. Files (suggested):
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/experiments/paper2/*.py,
.../configs/paper2/*.yaml, docs/dev-notes/research_work/agent-tool-benchmark/paper2/figures.md Tests
required: dry-run smoke test (tiny dataset) per baseline; CI job that validates config loading.
Estimate: 3–8 weeks. Notes: Align naming with Paper 1 experiment scripts for consistency.

```

---

## 8) Tests & CI

- **Goal**: Expand unit/integration coverage and add lightweight CI smoke tests for SIAS (no-GPU and GPU modes as needed).
- **Deliverables**: pytest cases across SIAS modules, GitHub workflow `paper2-experiments.yml` (quick mode) leveraging `sage-dev project test` subsets.
- **Acceptance**: All new tests pass locally + in CI; smoke workflow runs on PRs under 15 minutes.
- **Estimate**: 1–3 weeks.

**Assignment prompt**:
```

Task: Strengthen SIAS test + CI coverage. Area: Tests Goal: Add targeted unit/integration tests and
a lightweight CI workflow to prevent regressions. Files (suggested):
packages/sage-libs/tests/sias/\*, .github/workflows/paper2-experiments.yml Tests required: pytest
suite + workflow dry run (act or GitHub). Estimate: 1–3 weeks. Notes: Re-use existing test utilities
from sage.libs.agentic where possible.

```

---

## 9) Docs, LaTeX & Submodule Extraction

- **Goal**: Keep ICML prompt, LaTeX, README, and submodule migration docs in sync; prepare extraction checklist once SIAS becomes its own repo.
- **Deliverables**: `docs/dev-notes/research_work/agent-tool-benchmark/paper2/icml_prompt.md` updates, `docs/dev-notes/.../paper2/latex/main.tex`, README with compile + reproduction steps, updated `packages/sage-libs/src/sage/libs/sias/SUBMODULE.md` extraction section.
- **Acceptance**: LaTeX builds cleanly, README instructions reproduce main results, extraction checklist covers git subtree/submodule steps.
- **Estimate**: 2–3 weeks (parallel with other work).

**Assignment prompt**:
```

Task: Finalize docs, LaTeX, and submodule plan. Area: Docs Goal: Align ICML text with
implementation, ensure latex/main.tex compiles, and provide a clear extraction checklist. Files
(suggested): docs/dev-notes/research_work/agent-tool-benchmark/paper2/\*,
packages/sage-libs/src/sage/libs/sias/SUBMODULE.md Tests required: `make -C docs-public` (or latex
build) succeeds; checklist reviewed by maintainer. Estimate: 2–3 weeks. Notes: Reference Paper 1
prompt structure for tone and citation density.

```

---

## Assignment / Issue Template (copy-ready)

**Title**: `[SIAS][Area] Short description — Assignee`

**Body**:
```

Task: <short title> Area: \<SSIS | Memory | Runtime | Router | Trainer | Data | Experiments | Tests
| Docs> Assignee: @<github-id> Goal: \<one-sentence goal + acceptance criteria> Scope & files:
<relative paths> Tests: \<unit/integration/benchmark requirements> Estimate: <weeks> Dependencies:
<upstream tasks or data>

PR Checklist:

- [ ] Linked this issue in the PR description
- [ ] Attached logs for required tests/benchmarks
- [ ] Documented configuration or new CLI flags

```

Each agent should leave a short progress ping in their issue at least once per week (or per sprint), noting blockers or interface changes.

---

## Quick next steps

1. Maintainer assigns tasks by referencing the sections above (feel free to tag multiple agents but clarify the exact subsection each handles).
2. Prioritize SSIS → Memory → Streaming Trainer (core dependency chain) before large-scale experiments.
3. Run small smoke tests (tiny dataset, 1–2 seeds) before launching full GPU jobs.

If you want automated assistance (e.g., generate GitHub issues or wire up CI stubs), let me know which sections to process next.

```
