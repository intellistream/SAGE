# ICPP 2026 Demo Revision Plan

本文档用于指导 SAGE + SageFlow ICPP 2026 demo paper、demo pipeline、runtime、UI 和实验证据的后续修改。目标不是重写论文故事线，而是把当前叙事中的系统承诺落到可运行、可展示、可复现实验上。

## 0. Revision Goal

最终 demo 应该让审稿人和现场观众明确看到：

1. 真实公开数据进入 SAGE pipeline，而不是 handcrafted replay 或 mock data。
2. 数据经过真实 embedding 模型生成向量，并进入 SageFlow runtime。
3. SageFlow runtime 在流式窗口中产生 vector join、cluster、snapshot contract 和 runtime counters。
4. Snapshot contract 被送入真实 OpenAI-compatible LLM API 节点。
5. UI 展示 LLM API 的真实输出、证据来源、pipeline 节点状态和 runtime 指标。
6. Paper 中的实验表格和图只报告可复现的真实测量结果。

ICPP 2026 demo paper 上限为 4 页，正文必须清楚覆盖 Motivation、System Overview、Demonstration Plan，并说明现场展示内容和观众交互方式。

## 1. Current Critical Gaps

### G1. Pipeline stops before real LLM generation

Current state:

- `sage-examples/apps/src/sage/apps/sageflow_service_demo/workflow.py` pipeline ends at `DeriveOperationalInsightStep`.
- `DeriveOperationalInsightStep` is rule-based and does not call vLLM.
- UI labels imply an LLM-facing response layer, but the visible response is prepared text.

Required state:

```text
Real data source
  -> Real embedding step
  -> Normalize event
  -> SageFlow runtime join service
  -> Snapshot contract builder
  -> Prompt builder
  -> OpenAI-compatible LLM generation step
  -> Answer sink
  -> UI
```

### G2. Embedding is deterministic and too small

Current state:

- `EmbedTextSignalStep` and demo data utilities generate 16-dimensional keyword/hash vectors.
- This is useful for deterministic replay, but it is not convincing as an embedding-based system demo.

Required state:

- Use a real embedding model or OpenAI-compatible embedding endpoint.
- Cache embeddings with model metadata.
- Keep deterministic replay by caching real embeddings, not by replacing embeddings with hand-authored vectors.

### G3. Dataset is too small and expanded by repetition

Current state:

- Baseline demo data is a small, manually curated CVE/advisory replay.
- Scaled runs are created by deterministic repetition and modified IDs.

Required state:

- Build at least one real public dataset from sources such as NVD CVE feeds, CISA KEV, OSV, or GitHub Security Advisories.
- Persist raw records, parsed text fields, embeddings, and dataset manifest.
- Use real subsets for experiments, for example 1k, 5k, and 10k records when feasible.

### G4. SageFlow runtime is real but under-demonstrated

Current state:

- `InMemorySageFlowSnapshotAdapter` uses `PersistentVectorJoinRuntime`.
- Default configuration uses `parallelism=1` and `join_method="bruteforce_lazy"`.
- Paper and UI do not sufficiently expose throughput, latency, retained records, queue state, and emitted pairs.

Required state:

- Run and report scalability with multiple parallelism levels.
- Expose runtime counters in both UI and experiment tables.
- Make the runtime contribution visible as the system's middle layer, not a hidden implementation detail.

### G5. UI is too descriptive and not evidence-first

Current state:

- UI contains descriptive copy and prepared/static data paths.
- It does not clearly show the final vLLM answer as the output of the pipeline.
- Figure screenshots risk looking generated or ornamental.

Required state:

- UI should work as a live pipeline control console.
- The first screen should show pipeline DAG, current event, SageFlow runtime state, snapshot contract, and vLLM answer.
- Static/prepared mode may remain as fallback, but live backend + real data + real model should be the primary demo path.

## 2. Target Demo Architecture

### 2.1 Runtime data flow

```text
Public vulnerability/advisory dataset
  -> Dataset parser
  -> Text normalization
  -> Embedding cache builder
  -> SAGE source operator
  -> SAGE map operators
  -> SageFlow service adapter
  -> PersistentVectorJoinRuntime
  -> Snapshot contract
  -> Prompt builder
  -> vLLM generation operator
  -> UI/live backend
```

### 2.2 Snapshot contract schema

The contract sent to vLLM should be explicit and serializable:

```json
{
  "contract_id": "snapshot-...",
  "latest_event_id": "...",
  "query_event": {
    "event_id": "...",
    "source": "...",
    "title": "...",
    "summary": "...",
    "severity": 0.0,
    "timestamp": "..."
  },
  "neighbors": [
    {
      "event_id": "...",
      "similarity": 0.0,
      "source": "...",
      "summary": "..."
    }
  ],
  "cluster": {
    "cluster_id": "...",
    "size": 0,
    "source_breakdown": {},
    "top_tags": []
  },
  "runtime": {
    "join_method": "...",
    "parallelism": 0,
    "window_size_ms": 0,
    "retained_left_records": 0,
    "retained_right_records": 0,
    "queued_left_records": 0,
    "queued_right_records": 0,
    "emitted_pairs": 0
  }
}
```

### 2.3 vLLM answer schema

The generated answer should be captured with provenance:

```json
{
  "answer_id": "answer-...",
  "contract_id": "snapshot-...",
  "model": "Qwen/Qwen2.5-7B-Instruct",
  "base_url": "http://127.0.0.1:8000/v1",
  "latency_ms": 0.0,
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "evidence_ids": ["..."],
  "prompt_hash": "...",
  "answer": "..."
}
```

## 3. Work Plan

### P0. Make the demo truthful end to end

#### T0.1 Add real embedding support

Scope:

- Replace the default 16d deterministic embedding path with a pluggable real embedding implementation.
- Keep the old deterministic embedder only as a test fixture or fallback, never as the paper/demo default.

Implementation tasks:

- Add `RealEmbeddingStep` or equivalent SAGE map operator.
- Support at least one local model path or OpenAI-compatible `/v1/embeddings` endpoint.
- Add embedding cache loader/writer.
- Add a dataset manifest recording model name, dimension, source count, record count, and hash.

Acceptance:

- A command can build embeddings from raw public records without manually authored vectors.
- Cached embedding files contain real vector dimensions such as 384, 768, or the configured service dimension.
- UI and paper no longer describe the default path as `deterministic vector`.
- Unit test verifies that records without cached embeddings are embedded or rejected with a clear error.

Suggested verification:

```bash
python -m sage.apps.sageflow_service_demo.build_embeddings --dataset nvd-kev --model BAAI/bge-small-en-v1.5
python -m pytest packages/sage-apps/tests/sageflow_service_demo -q
```

#### T0.2 Build a real vulnerability dataset

Scope:

- Use public records instead of small handcrafted replay as the primary dataset.

Implementation tasks:

- Add a reproducible dataset builder for NVD/CISA KEV/OSV or a selected subset.
- Normalize fields into `event_id`, `source`, `title`, `summary`, `tags`, `severity`, `timestamp`, `metadata`.
- Produce fixed subsets for demo and experiments.
- Store dataset manifest with source URLs and generation timestamp.

Acceptance:

- Dataset builder produces at least one live-demo subset and one larger experiment subset.
- The paper can cite exact record counts from the generated manifest.
- No scaled experiment result is produced by merely copying the same handcrafted events.

Suggested verification:

```bash
python -m sage.apps.sageflow_service_demo.build_dataset --source nvd --source cisa-kev --out data/icpp_demo
python -m sage.apps.sageflow_service_demo.describe_dataset data/icpp_demo/manifest.json
```

#### T0.3 Add a real LLM API generation node

Scope:

- Make the final pipeline output come from OpenAI-compatible chat completion.

Implementation tasks:

- Add `SnapshotContractBuilderStep`.
- Add `PromptBuilderStep`.
- Add an LLM response step that calls `/chat/completions`.
- Capture `model`, `latency_ms`, token usage if returned, evidence ids, and prompt hash.
- Add a strict offline fallback mode only for tests, clearly labeled as `template_fallback`.

Acceptance:

- Live run shows the actual LLM response text returned by the configured endpoint.
- The response object contains evidence ids that match the SageFlow snapshot.
- If vLLM is unavailable, the UI shows a clear backend error instead of silently presenting prepared prose.
- Paper can honestly say the final node is a live vLLM generation node.

Suggested verification:

```bash
curl http://127.0.0.1:8000/v1/models
python -m sage.apps.sageflow_service_demo.run_live_pipeline --llm-base-url http://127.0.0.1:8000/v1
```

#### T0.4 Make UI live-first and evidence-first

Scope:

- Remove visual clutter and make the UI prove the pipeline works.

Implementation tasks:

- Make live backend mode the default path.
- Add a visible backend status strip: dataset, embedding model, SageFlow runtime, vLLM model.
- Replace broad explanatory panels with compact evidence panels.
- Show pipeline DAG with node status: source, embed, join, contract, prompt, vLLM, answer.
- Add contract viewer and final answer viewer.
- Keep static/prepared data only as an explicitly labeled fallback.

Acceptance:

- A screenshot of the first viewport shows the real pipeline output, not just descriptive text.
- The final answer panel includes model name, latency, evidence ids, and generated answer.
- No primary UI label says `prepared contract ready` or `deterministic vector` in live mode.
- Figure 2 in the paper can be a direct UI screenshot.

Suggested verification:

```bash
npm run dev
python backend/live_demo_server.py
```

Manual UI checks:

- Start replay.
- Select a cluster.
- Inspect evidence ids.
- Trigger or observe vLLM answer.
- Confirm answer text changes when the evidence contract changes.

### P1. Produce credible experimental evidence

#### T1.1 Add end-to-end measurement harness

Scope:

- Measure the real pipeline rather than prepared summaries.

Metrics:

- embedding latency
- SageFlow append/join latency
- contract materialization latency
- vLLM generation latency
- end-to-end latency
- throughput
- emitted pairs
- retained records
- p50/p95/p99 latency

Acceptance:

- Script writes machine-readable results, for example JSONL or CSV.
- Each result row includes dataset id, record count, embedding model, join method, window size, threshold, parallelism, LLM model, hardware summary.
- Paper tables are generated from these result files or manually checked against them.

#### T1.2 Add scalability and ablation runs

Required comparisons:

- Dataset size: small live subset, medium experiment subset, large experiment subset.
- Parallelism: 1, 2, 4, 8 if hardware permits.
- Window size: at least 2-3 values.
- Threshold: at least 2 values.
- With and without SageFlow snapshot batching if implemented.

Acceptance:

- Results show where SageFlow helps and where LLM latency dominates.
- Paper includes one compact table or plot with real numbers.
- Any failed or timeout configuration is reported honestly as unavailable or omitted with reason.

#### T1.3 Add quality/faithfulness checks

Scope:

- Demonstrate that generated answers are grounded in the snapshot contract.

Possible metrics:

- Cluster purity using weak labels such as product, vendor, CWE, or CVE family.
- Evidence citation accuracy: percentage of generated answers that cite only event ids present in the contract.
- Top-k neighbor relevance by shared CVE/vendor/product tags.

Acceptance:

- At least one quality metric appears in the paper.
- Example answers include evidence ids and can be traced to source records.
- No paper claim depends only on subjective visual inspection.

### P2. Paper and artifact polish

#### T2.1 Update system figure

Required content:

- SAGE pipeline operators.
- SageFlow runtime service boundary.
- Snapshot contract boundary.
- vLLM generation node.
- UI/control plane.

Acceptance:

- Figure 1 answers: what is SAGE, what is SageFlow, what is the LLM, and what crosses each boundary.
- The figure is readable in two-column ACM format.

#### T2.2 Replace generated-looking screenshots

Scope:

- Use real UI screenshots from the live demo.

Acceptance:

- Figure 2 is captured from a real running UI.
- It shows live backend status, pipeline DAG, runtime counters, evidence ids, and LLM answer.
- Caption explains what the audience can do in the demo.

#### T2.3 Rewrite experiment and demo sections

Required paper changes:

- Add dataset and model configuration.
- Add a live demo script.
- Add real measurements.
- Remove claims based on deterministic embeddings or replay copies.
- Add SAGE ICML 2026 citation and correct related systems citations.

Acceptance:

- Paper remains within 4 pages.
- The four-page space is used for complete demo narrative, not compressed into a too-short paper.
- Every numeric claim can be traced to a generated result file or dataset manifest.

## 4. Definition of Done

The demo revision is complete only when all P0 items and selected P1 evidence items pass.

### Engineering DoD

- Real public dataset builder exists.
- Real embeddings are built or loaded from cache.
- SageFlow runtime consumes real embeddings.
- Pipeline includes vLLM generation.
- UI displays the real LLM answer and evidence contract.
- Tests cover embedding cache loading, contract construction, and LLM failure handling.

### Experiment DoD

- Results include at least one end-to-end run over a real dataset subset.
- Results include runtime scalability or ablation evidence.
- Results include one quality/faithfulness metric.
- All reported numbers have result files.

### Paper DoD

- System overview matches the implemented architecture.
- Demonstration plan describes actual audience interaction.
- Figures are direct representations of implemented system behavior.
- References include SAGE, SageFlow-related/runtime work, vLLM, and dataset sources.
- PDF is no more than 4 pages.

## 5. Suggested Milestones

### Milestone A: truthful live path

Deliverables:

- real embedding cache
- real dataset subset
- pipeline with vLLM node
- UI showing live vLLM answer

Exit criteria:

- One command can run the live pipeline and produce a real answer with evidence ids.

### Milestone B: experimental evidence

Deliverables:

- measurement harness
- scalability table
- quality/faithfulness table
- generated result files

Exit criteria:

- Paper-ready numbers are available and reproducible.

### Milestone C: four-page paper revision

Deliverables:

- revised architecture figure
- real UI screenshot
- updated experiment table/figure
- updated references
- compiled PDF under 4 pages

Exit criteria:

- A reviewer can map each claim to code, data, UI, or measured result.

## 6. Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| vLLM unavailable on demo machine | final node cannot produce live output | add explicit health check and clearly labeled fallback, but paper default must be real vLLM |
| embedding model too slow | live demo stalls | precompute cache and show cache metadata; measure online embedding separately |
| dataset too noisy | clusters look weak | use documented filtering by severity/date/vendor and report filtering rules |
| UI becomes too dense | screenshot unreadable | keep first viewport to pipeline, runtime, contract, answer only |
| paper exceeds 4 pages | invalid submission | move implementation detail to artifact/repo; keep paper focused on demo and evidence |

## 7. Immediate Next Task List

1. Add dataset builder and manifest format.
2. Add real embedding cache builder and loader.
3. Add snapshot contract schema and builder.
4. Add vLLM response operator.
5. Change live backend to return contract and real answer.
6. Change UI live mode to show DAG, runtime counters, contract, and answer.
7. Add end-to-end benchmark script.
8. Regenerate paper figures from real UI/results.
9. Revise paper text and references.
10. Compile and verify the PDF is within 4 pages.
