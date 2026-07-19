# Semantic MapReduce Mechanism and Evidence Readiness Report

## 2026-07-19 Current Status: NOT SUBMISSION-READY

The previous submission-freeze conclusion is superseded. The frozen online
artifacts remain valid evidence for the historical `semantic-reduce/v1`
pairwise action implementation, but that implementation was merge-only:
`SPLIT`, `KEEP`, and `ABSTAIN` all preserved state, `split_count` was zero, and
the model edited a `semantic-graph` H0. `hybrid-hint` was a comparison and the
configured fallback, not the pre-edit state.

Runtime v2 now implements a finite system-generated proposal catalog, true
evidence-partitioning SPLIT, ID-only policy selection, unique ownership,
reason-coded atomic rollback, exact H0 fallback, catalog/state/selection
digests, checkpoint restore, and independent replay. This mechanism currently
has unit/property and dirty-development `simulation/model` evidence only. No
new endpoint, model, credential, NPU, or real-online sweep has been used.

- **COMPLETED:** typed v2 contract, three oracle-free split generators,
  adversarial conservation/atomicity tests, shared-H0/shared-catalog
  deterministic and mock policy harness, frozen held-out ambiguity axes.
- **IN PROGRESS:** clean commit and full development/held-out offline matrix,
  proposal coverage and negative-case analysis, derived Figure 3 replacement.
- **BLOCKED:** model-selector increment and real-online v2 validation until all
  offline gates plus endpoint/model/hardware/credential readiness pass.

### Cross-review adjudication

Three independent read-only reviews (systems/claims, experiments/statistics,
and artifact/anonymity) all returned **NOT READY**. There was no substantive
reviewer conflict on the disposition. The apparent H0 conflict was temporal:
the systems reviewer correctly described executable v1, while the current TeX
had already begun admitting that mismatch; source and raw traces decide in
favor of `semantic-graph` H0 plus merge/no-op v1. The artifact root embeds the
public short revision `a48f1e6`, so archive SHA `f590fde5...d73d4a0` is
historical evidence only and must not be uploaded.

The current rebuild uses SIGPLAN's 10pt body and explicitly prevents smaller
caption, table, figure-label, algorithm, and bibliography text. It is 13 PDF
pages on US Letter: technical content ends on page 12 and page 13 contains only
references, which is within the official 12-technical-page-plus-references
limit. Page-by-page review caught and repaired four clipping/overlap defects.
The public/private final hashes remain pending until the clean evidence/package
freeze. The expanded no-NPU audit selection currently passes `80 passed`.

All older “submission-facing,” “READY,” and deadline-oriented sections below
are historical 2026-07-18 records, not the current readiness decision. In
particular, 0.8645/0.7801 is historical merge-only online evidence;
0.9301/0.7204 is a three-hardcase diagnostic; 0.9287 is a controlled strong
reference, not external SOTA; and the matched constrained statistic is 0.9028.

This report summarizes the current EuroSys'27-readiness state for the Semantic
MapReduce paper draft. It separates supported claims from mechanism probes and
keeps real-online evidence provenance explicit.

## Primary Online Result

Submission-facing nine-family, three-seed, five-sample real-online artifact
(135 rows per reducer, candidate budget 8):

```text
.sage/benchmarks/real_online_semantic_merge_stability/20260718T-eurosys27-9family-3seed-5sample-000c513/candidates-8/
```

| Reducer | Precision | Recall | F1 | Support recall | Reduce ms | Tokens | Accepted edits | Invalid/fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `hybrid-hint` | 0.7692 | 0.8426 | 0.7801 | 0.7810 | 0.23 | 0.0 | 0.0 | 0 |
| `llm-pairwise-validated` | 0.7881 | 0.8426 | 0.7932 | 0.7948 | 1980.49 | 276.0 | 0.1259 | 39 schema / 39 fallback |
| `llm-pairwise-action-validated` | 0.8975 | 0.8426 | 0.8645 | 0.8672 | 102.73 | 260.9 | 0.8148 | 4 action / 0 fallback |

This is historical v1 workload-coverage and repeatability evidence. For the
action path, within-case F1 standard deviation is zero, exact action agreement
averages 0.9926, schema invalid and fallback are zero, and four unparsable
response strings map fail-closed to `ABSTAIN`/no-op. They are not validator-
rejected edits. The three-hardcase artifact below remains an
isolated mechanism diagnostic and is no longer the anonymous package source.

The paired analysis uses the 27 scenario x seed means as independent units;
the five repeated rows within each unit are not treated as independent. Against
`hybrid-hint`, action validation has mean paired delta F1 `+0.0844` with a
deterministic 10,000-draw bootstrap 95% CI `[0.0328, 0.1449]` (8 wins, 19 ties,
0 losses). The model is called on 65/135 action rows (48.15%). Conditional on a
call, median reducer latency is 160.0 ms and mean provider-reported tokens are
541.8; provider token coverage is 65/65. These conditional numbers are the
submission-facing cost result, while the pooled row means above include cheap
no-pair rows.

Second-checkpoint, same-family real-online artifact (three samples per unit,
81 rows per reducer):

```text
.sage/benchmarks/real_online_semantic_merge_cross_model/20260719T165239Z-qwen25-14b-9family-3seed-3sample/
directory digest: 825858b062a73b1d24b7998d2750f12b2ce31ed959c576077f82c34aba7d1990
```

| Reducer | F1 | Mean reduce ms | Tokens | Invalid schema/action | Fallback |
| --- | ---: | ---: | ---: | ---: | ---: |
| `hybrid-hint` | 0.7801 | 0.24 | 0.0 | 0 | 0 |
| `llm-pairwise-validated` | 0.7977 | 3056.63 | 308.9 | 12 schema | 12 |
| `llm-pairwise-action-validated` | 0.8392 | 187.02 | 261.1 | 2 action | 0 |

For the action path, the 27-unit paired delta versus hybrid is `+0.0591`, 95%
CI `[0.0147, 0.1149]` (7 wins, 20 ties, 0 losses). It calls the model on 39/81
rows; conditional median latency is 276.2 ms, mean provider tokens are 542.3,
and provider-token coverage is 39/39. All 243 raw reports are retained, each
reducer has 81 rows, the matrix is labeled `real-online`, and the credential
scan reports zero unsafe files. This is a second model scale in the same Qwen
family, not cross-family robustness. The directory digest is computed as
`find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum` after the
derived stability summaries are frozen; it therefore covers both raw reports
and the cited derived analyses.

Clean three-workload-seed real-online artifact:

```text
.sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e/
```

Anonymous submission artifact package:

```text
.sage/benchmarks/semantic-reduction-eurosys27-review-evidence.tar.gz
sha256: f590fde5a371c2d663ebeddd9b609fe4d6ea74a5f36c794e9fd3fbad2d73d4a0
```

The final archive contains 693 files. Its supplementary evidence includes all
243 raw 14B reports, the AIOpsArena label-conditioned reducer-only replay, and
the clean 27-row model-free runtime-contract matrix. An independent extraction
found zero identity/repository markers, emails, exact 40-hex Git revisions, or
private IPs. The `.sage/` tree is ignored by git, so this archive should be attached as a
separate artifact rather than committed. The raw local evidence remains intact;
the submission package uses an allowlist, replaces identity-bearing paths,
hostnames, private IPs, Git commits/branches, repository/runtime names, key
variable names, and SHA-bearing run IDs with internally consistent opaque
labels, excludes historical service logs, and records source and packaged
SHA-256 hashes in `ANONYMIZATION_MANIFEST.json`. The verifier accepts opaque
publication provenance only when endpoint/run revision equality, clean state,
device/model identity, and the full evidence contract still match.

Do not submit the superseded archive whose filename ends in
`000c513-anonymous.tar.gz`: its exact public Git provenance is reversible and
therefore violates the double-blind boundary even though local identity fields
were removed.

Provenance:

- Evidence label: `real-online`
- Endpoint: `http://127.0.0.1:18383`
- Model: `qwen25-7b-sage-realonline`
- Hardware: NPU3, Ascend 910B2
- Conda env: `esage-vllm-hust-dev`
- Clean run parent commit: `000c513eb4a90104ce09e2222d3ced62906117b2`
- Paper package commit: any later paper-only synchronization commit that
  preserves this clean replay artifact and result table.
- Parent dirty: `false`
- `third_party/llm-serving-workloads`: `79ed8e3469c0bcfccdf1cd0a66efa2db27156055`
- `third_party/ascend-runtime-manager`: `c5b0461aaecffe7e5011f8fab0944d32bedb1092`, clean
- Workload source: repo-local `src/sage/workloads/semantic_merge_analysis.py`
- Scenarios: all nine controlled workload families
- Workload seeds: `7`, `11`, `13`
- Samples per case/seed/reducer: `5`
- Candidate budgets: `4`, `8`, `12`; budget 8 is the primary configuration

## Operator Model Update

The paper now frames Semantic MapReduce as an operator algebra rather than a
workflow demo. The core operators are:

```text
Shard(D; pi) -> {D_i}
MapEvidence(D_i; phi) -> E_i
Normalize(E; sigma) -> E_hat
GroupEvidence(E_hat; gamma) -> C
SemanticReduce(C; rho) -> H_0
Edit(C, H_0; a) -> Delta, where a in {KEEP, MERGE, SPLIT, ABSTAIN}
Validate(H_0, Delta, E_hat; V) -> H or fallback(H_0)
ReportTrace(H, E_hat, T; tau) -> report + trace
```

This reframes the live LLM result as a reducer-interface result. Free-form
pairwise JSON asks the model to implement too much of `SemanticReduce` and
`ReportTrace` at once, so schema failures and evidence-reference failures
become reducer failures. The new action reducer maps the model to `Edit` only:
the model emits a bounded enum action, while the system owns evidence binding,
JSON assembly, schema validation, root/affected-service checks, fallback, and
trace capture. This is the central abstraction that should carry the EuroSys
paper narrative.

Three-hardcase, three-workload-seed aggregate (nine rows per reducer):

| Reducer | Precision | Recall | F1 | Support recall | Tokens | Accepted edits | Fallback | Invalid action | Invalid schema |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `semantic-graph` | 0.4427 | 0.4722 | 0.4318 | 0.5185 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `hybrid-hint` | 0.6596 | 0.9167 | 0.7204 | 0.7083 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `llm-pairwise-validated` | 0.6596 | 0.9167 | 0.7204 | 0.7083 | 508.7 | 0.0 | 1.0 | 0.0 | 9 |
| `llm-pairwise-action-validated` | 0.9630 | 0.9167 | 0.9301 | 0.9815 | 536.1 | 2.2222 | 0.0 | 0.0 | 0 |

Per-case action-validated outcomes:

| Scenario | Hybrid F1 | Action-validated F1 | Accepted merges | Main interpretation |
| --- | ---: | ---: | ---: | --- |
| `ambiguous-disconnected-merge` | 0.7273 | 1.0000 | 3 | Succeeds: validated merge edits repair fragmented incident evidence. |
| `ambiguous-temporal-split` | 0.5769 | 0.9333 | 3.67 | Two seeds reach F1 1.0; seed 7 retains two unmatched fragments. |
| `ambiguous-overmerge` | 0.8571 | 0.8571 | 0 | Safe abstention: action reducer avoids gratuitous edits and preserves baseline. |

## Accepted Edit Example

For `ambiguous-disconnected-merge`, the endpoint returned three enum actions:

```json
[
  {"pair": 0, "raw": "MERGE", "action": "MERGE", "valid": true},
  {"pair": 1, "raw": "MERGE", "action": "MERGE", "valid": true},
  {"pair": 2, "raw": "MERGE", "action": "MERGE", "valid": true}
]
```

The system assembled validated merge edits:

```json
[
  {"candidate": 0, "action": "merge", "candidates": [0, 4], "evidence_ids": ["e4", "e5"]},
  {"candidate": 2, "action": "merge", "candidates": [2, 6], "evidence_ids": ["e0", "e1"]},
  {"candidate": 3, "action": "merge", "candidates": [3, 5], "evidence_ids": ["e2", "e3"]}
]
```

The validator recorded `schema_valid=true`, `fallback_count=0`,
`repair_count=0`, `candidate_evidence_count=8`, and
`output_evidence_count=8`.

## Failure Taxonomy

- Output format: fixed for action reducers in the latest run. Free-form
  pairwise JSON still fails schema in all three cases.
- Candidate pair expression: still weak for `ambiguous-temporal-split`; valid
  pairwise merges reduce fragmentation but still leave too many hypotheses.
- Evidence coverage: not the blocker in the latest run; all three hardcases
  have evidence coverage 1.0.
- Action granularity: enum actions are sufficient for disconnected merge and
  safe abstention, but temporal grouping may need multi-pair grouping or
  transitive closure constraints.
- Model semantic ability: useful bounded merge decisions repeat across three
  workload seeds at 7B and 14B scales in one model family. Cross-family and
  production robustness remain untested.
- Validator conservatism: four proposed actions are rejected at budget 8 and
  five at budget 12; no action-path schema failure or fallback occurs.

## Strongest Current Claim

Semantic MapReduce is best framed as an operator algebra for evidence-linked
semantic reduction, not as a prompt chain. Its key operators are
`MapEvidence`, `SemanticReduce`, `Edit`, `Validate`, and `ReportTrace`.
Semantic Reduce should expose a constrained, evidence-linked edit protocol
rather than asking an LLM to emit free-form hypotheses or reducer JSON. In the
current prototype, one-token pairwise action classification maps the model only
to `Edit` and converts output instability into bounded action uncertainty:
invalid model text becomes `ABSTAIN`, evidence references are supplied by the
system, validators enforce the incident schema, and fallback protects baseline
output. A three-workload-seed real-online hardcase matrix shows this design can
accept validated merge edits and improve over `hybrid-hint` on covered ambiguous
merge cases under one model and endpoint. Five repeated samples per case show
zero within-case F1 variation for the action path, while validator rejections
remain explicit rather than being reported as successful model actions.

## Current Final State

- Paper narrative has been updated around the `Semantic MapReduce Operator
  Model`.
- The complete nine-family, ten-seed derived matrix contains 540 rows (90 per
  reducer). `hybrid-hint` reaches mean F1 0.7796 versus 0.0705 map-only and
  0.4916 window aggregation. Artifact:
  `.sage/benchmarks/semantic_merge_analysis/20260718T-eurosys27-9family-10seed/`.
- The runtime-contract matrix covers nine families x seeds 7/11/13. All 27
  runs pass valid commit, invalid-edit rejection, baseline preservation,
  checkpoint-digest restoration, and deterministic replay. Artifact:
  `.sage/benchmarks/semantic_mapreduce_runtime_contract/20260719T-eurosys27-final-d5ba73d-clean/`.
- The AIOps Challenge 2020 May-29 public replay consumes the official daily ZIP
  without republishing raw rows. It detects 2/4 official fault windows with
  zero false positives over eight matched negative windows (precision 1.0,
  recall 0.5, F1 0.6667). The misses are retained as evidence-coverage limits.
  Artifact: `.sage/benchmarks/aiops2020_public_replay/20260718T-may29-map-evidence-replay-v4/`.
- The AIOpsArena complex-case replay uses 23 public injection rows grouped by
  the dataset fields `(timestamp, service, failure_type, duration)` into eight
  native incident episodes. With label-conditioned evidence and episode IDs
  withheld from reducers, map-only reaches F1 0.5161, window aggregation 0.8000,
  and service-local/semantic reduction 1.0000. Artifact:
  `.sage/benchmarks/aiopsarena_reducer_grouping/20260719T-complex-case2-reducer-grouping-v1/`,
  result SHA-256
  `111c3489d1c8b49a78a13a636bcfd9c278a2515ba4da9b32cde49b02643d676e`.
  Evidence label: `replay`; scope: `reducer-only-label-conditioned`. It is not
  end-to-end detection or production/model generality.
- A new operator-algebra figure shows the model-facing boundary at `Edit`,
  while `Validate`, trace generation, and fallback remain system-owned.
- A concrete reducer-lifecycle figure makes the invocation contract explicit
  across admit, reduce, select, propose, assemble, validate, publish, reject,
  checkpoint/recover, and trace phases. The model owns only one enum action;
  evidence eligibility, edit construction, commit/fallback, checkpoint state,
  and replay digests remain runtime-owned.
- The paper explicitly separates the model-free checkpoint/recovery fault
  matrix from the real-online path: the former executes logical reducer-state
  recovery, while the latter archives compatible candidate/evidence/state
  digests and outcomes. Neither is described as distributed exactly-once.
- The action reducer is written as an `Edit` + `Validate` instance, not as a
  prompt-engineering trick.
- The historical EuroSys PDF was 12 pages total. It is superseded by the
  current 10pt-compliant rebuild and cannot be used as a current visual or
  page-count attestation.
- The historical focused no-NPU selection reported `51 passed`; the current
  audit uses an expanded selection and records its result in the status section
  above.
- The full nine-family, three-seed, five-sample NPU3 matrix passes the artifact
  gate at candidate budget 8: F1 0.8645 versus 0.7801 for `hybrid-hint`, zero
  fallback/schema invalid, four unparsable responses mapped to no-op, and clean parent/submodule
  provenance. A later process-diagnostic audit found that full container argv
  could retain the test token; that token was immediately revoked, the affected
  preflight was invalidated and sanitized, and commit `11e4ec4` changed process
  diagnostics from full `args` to non-secret `comm`. The replacement 14B run
  passes a zero-unsafe-file credential scan. The 0.9301 hardcase result remains
  diagnostic only.
- Implementation-layer boundary is explicit: the submitted Semantic MapReduce
  mechanism does not require new Ascend kernel, Triton operator, mask/packing,
  or runtime-operator semantic changes. If future work needs such behavior, it
  must land in the pinned `external/triton-ascend-hust` feature branch rather
  than as an ad hoc `vllm-ascend-hust` workaround; `vllm-ascend-hust` remains
  thin glue, and `vllm-hust` owns scheduler/KV/request-metadata concerns.
- The nine-family derived matrix, 27-run runtime fault matrix, clean five-sample
  real-online sweep, second-scale three-sample matrix, and anonymous
  full-coverage package are complete. Cross-family and production
  incident-group claims remain separate evidence upgrades.

## EuroSys Workload-Coverage Gate

The current workload inventory contains nine unique repo-local scenario
families. All nine now have a common ten-seed derived matrix and three-seed
runtime fault injection; three ambiguity families have the current real-online
action matrix.

Before submission, organize coverage by contract obligation rather than by
adding more names:

| Obligation | Existing families | What the action path must demonstrate |
| --- | --- | --- |
| Sanity/no-op | `single-service` | Preserve an already-correct incident without gratuitous edits. |
| Positive cross-service fusion | `cascade`, `shared-bottleneck`, `ambiguous-disconnected-merge`, `ambiguous-temporal-split` | Accept only evidence-preserving merges and improve fragmentation when candidate ambiguity exists. |
| Negative separation | `concurrent`, `false-correlation`, `ambiguous-overmerge` | Reject spurious merges or abstain without regressing the hybrid baseline. |
| Incomplete evidence | `partial-evidence` | Expose that missing root evidence is a coverage/inference boundary; do not manufacture provenance. |
| Recovery/admission | all families | Every action is accepted, rejected, or mapped to `ABSTAIN`; rejected edits retain `H_0`, and the trace records action, validation, latency, and tokens. |

The completed real-online matrix uses all nine families with seeds `7`, `11`,
and `13` (27 case/seed rows per reducer), under the same model, endpoint,
evidence schema, scorer, and candidate generator. It keeps three fixed comparison
regimes:

1. `hybrid-hint` as the valid pre-edit state `H_0`;
2. `llm-pairwise-validated` as the free-form/schema negative control; and
3. `llm-pairwise-action-validated` as bounded `Edit` + system-owned `Validate`.

The expanded 7B repeated run meets the admission gate at candidate budgets 8 and
12: accepted edits do not violate schema or evidence invariants, pooled F1
improves, and accepted and rejected actions remain visible in the trace. Budget
4 is intentionally retained as a failed quality point because candidate
truncation reduces F1 to 0.7791. The 14B same-family matrix independently
passes the action contract but records two unparsable responses mapped to no-op.

## Claims Not Yet Supported

- Do not turn three controlled workload seeds at two same-family model scales
  into broad stochastic, cross-family, or production robustness.
- Do not claim a general quality-cost frontier. The three measured budget points
  show an operating boundary: budget 8 reaches the best F1 (0.8645), while
  budget 12 costs more and reaches 0.8571.
- Do not claim production incident-group generality. AIOps 2020 covers
  MapEvidence/Normalize; AIOpsArena adds native episode grouping but uses
  oracle/label-conditioned evidence and only eight incident episodes.
- Do not claim that this replaces Spark, Flink, Ray, databases, LangGraph, or
  LlamaIndex.
- Do not claim that validators prove the LLM is always useful; validators make
  model edits auditable, rejectable, and fallback-safe.

## 2026-07-18 Evidence-Sprint Audit

The submission-facing claim boundary is sound. This sprint added and executed
an auditable repeated-sampling and candidate-budget harness rather than
rewriting an earlier point estimate as robustness evidence:

- `run_semantic_merge_matrix.py --samples N` writes a distinct raw report for
  every case/seed/reducer/sample tuple.
- The bounded action reducer retains model text, provider response envelope,
  prompt/response digests, timestamps, latency, and every request failure. No
  credential or bearer header is retained.
- `summarize_semantic_merge_stability.py` reports within-case F1 standard
  deviation and exact action agreement. Cross-workload F1 variation is not
  mislabeled as sampling instability.
- Provider-reported token usage is used when available; otherwise the artifact
  labels the value as a character-based estimate.
- `run_npu3_semantic_merge_stability_sweep.sh` evaluates candidate budgets
  `4,8,12` over all nine families, seeds `7,11,13`, and repeated samples, then
  derives a quality--reducer-latency--token curve. It does not claim an
  end-to-end serving speedup or a monetary-cost frontier.

A deterministic five-sample development run over all nine families verified
the repetition and aggregation plumbing. Its source evidence label is
`simulation/model`; it is not LLM stability evidence. A public AIOps replay now
also executes the reducer contract over the two detected official windows:
valid bounded edits commit, an edit that cites missing evidence is rejected,
the baseline is preserved, and deterministic replay succeeds. Because AIOps
2020 does not provide incident-group merge/split labels, this is external
contract conformance, not reducer-quality generalization.

The locally controlled test bearer key was rotated without printing or copying
its value. A secret-free attestation records only `rotated_utc`, `api_key_env`,
and `operator_acknowledged_no_key_logged=true`; the run metadata retains only
the attestation basename and SHA-256. Literal-key scanning found zero matches in
the real-online artifacts and tracked files. The clean sweep at commit
`000c513` completed 1,215 reducer rows across budgets 4/8/12. Budgets 8 and 12
pass the full artifact gate; budget 4 is preserved with gate `FAIL` because its
0.7791 F1 does not exceed hybrid 0.7801. A second, same-family 14B checkpoint is
now measured separately; no cross-family result is inferred.

The derived budget curve is:

| Candidate budget | Action F1 | Support recall | Mean reduce ms | p95 ms | Tokens | Gate |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 0.7791 | 0.7455 | 19.76 | 104.81 | 45.8 | FAIL (below baseline) |
| 8 | 0.8645 | 0.8672 | 102.73 | 366.39 | 260.9 | PASS |
| 12 | 0.8571 | 0.8795 | 120.34 | 547.21 | 304.1 | PASS |

Clean no-credential evidence at parent commit
`e0ffdffeef7a059ee3059064eb5c86a25307738a`:

```text
.sage/benchmarks/semantic_mapreduce_runtime_contract/20260719T-eurosys27-final-d5ba73d-clean/
.sage/benchmarks/aiops2020_semantic_reduce_contract/20260718T-eurosys27-public-contract-e0ffdff-clean/
```

The runtime matrix is `derived-artifact`: 27/27 valid commits, invalid-edit
rejections, baseline-preservation checks, checkpoint restores, and
deterministic replays pass. The AIOps artifact is `replay`: it contains two
stable evidence IDs from the previously detected public windows and passes
valid commit, missing-evidence rejection, baseline preservation, and
deterministic replay. Its contract-result SHA-256 is
`f490e817a9ff1d04958d3853430c85fd879c716b574d666a39e03cdbdb7300ce`.

## Reviewer Attack Prep

**Is this just prompt engineering?**

No. The paper should answer this through the operator model. The model is not
asked to write an incident report or full reducer JSON; it implements only the
`Edit` operator over candidate pairs. `Validate` is a separate system operator
that owns evidence IDs, JSON construction, schema validation, merge
application, fallback, cost accounting, and trace capture. The experiment
contrasts free-form `SemanticReduce`-style JSON with `Edit`+`Validate` under
the same model, evidence, scorer, and endpoint.

**Why not just use JSON mode?**

JSON mode can make syntax valid but does not guarantee that the required
decision list is present, that evidence IDs are copied correctly, or that the
incident unit is preserved. The previous pairwise JSON path still falls back
with invalid schema in the latest hardcases. The action protocol removes JSON
generation from the model-facing contract and moves it into the system-owned
`Validate` path.

**Why is deterministic hybrid not enough?**

Hybrid-hint is a strong baseline and should stay in the paper. Its limitation
is visible on covered ambiguous merge cases: it recovers recall but over-reports
fragmented incidents. The action reducer improves disconnected merge to F1 1.0
and temporal split to F1 0.8 by applying evidence-preserving merge edits. The
correct framing is not "LLMs replace deterministic reducers"; it is that
deterministic reducers provide `H_0`, while bounded `Edit` can repair ambiguous
candidate relations when evidence coverage is sufficient.

**Does LLM instability invalidate the direction?**

It invalidates free-form reducer prompting, not Semantic Reduce. The system
contribution is to turn instability into an explicit protocol with bounded
actions, validation, and fallback.

**Do validators/fallback hide that the LLM contributes little?**

The artifact reports accepted edit count, fallback count, invalid action count,
invalid schema count, and per-case F1. In the latest action run, the validated
path has accepted edits and zero fallback; in prior runs, fallback preserved the
baseline and was reported rather than hidden.

**Is the workload toy?**

The workload is controlled, not production trace replay. Its role is to expose
operator-level semantic reduction behaviors that ordinary alert/window
benchmarks do not isolate. The paper should frame public/production replay as
the next validation step, while emphasizing that the suite has multiple
scenario families, shared scorer, evidence objects, and failure taxonomies.

**How is this different from LangGraph, Ray, Spark, or Flink?**

Those systems can carry parts of the computation. Spark/Flink/Ray can execute
`Shard`, `MapEvidence`, or grouping work; LangGraph/LangChain can express a
control flow. The paper's abstraction is the operator contract across
`MapEvidence`, `SemanticReduce`, `Edit`, `Validate`, and `ReportTrace`: bounded
evidence objects, candidate pairs, validated edits, fallback-safe execution,
and workflow trace under one scorer. Adapter results should be framed as
substrate probes, not SOTA leaderboards.

**Where is the systems contribution?**

The contribution is the reducer protocol and evaluation harness: standard
Semantic MapReduce operators, a semantic-merge workload suite, constrained
edit interfaces, evidence-linked validators, fallback-safe execution,
real-online NPU endpoint evidence, and claim discipline around coverage,
latency, token cost, and traceability.

## Status

Historical 2026-07-18 assessment: READY for the then-bounded-contract mechanism
claim and internal EuroSys review. This assessment is superseded by the
2026-07-19 mechanism-completion status at the top of this report.
The code, evidence, artifact, paper, and public CFP checks are frozen; only
author-owned conflicts/identity/HotCRP metadata remain before submission.
The real-online matrix and machine-executable artifact gates pass. Per-case/seed
JSON and CSV report F1, support recall, accepted edits, fallback, invalid
action/schema, tokens, latency, and failure taxonomy. The current PDF has 12
total pages and has passed a complete visual inspection. The clean
full-coverage rerun, regenerated anonymous package, rebuilt PDF, and
public policy audit are complete. Author-owned upload checks remain in
[`NEXT_STEPS.md`](NEXT_STEPS.md).

The private-title review PDF is built outside the tracked paper tree with
`tools/benchmark_carrier/build_semantic_mapreduce_submission.py`. Its title
title/system-name sources and PDF are ignored and verified as untracked, so
pushing the public technical report does not reveal the submission title or
system alias. The 2026-07-19 build is
12 letter-size pages; all pages were rendered, fonts are embedded, and the
title page, reducer-lifecycle figure, anonymous workload-revision table, online
tables, quality--cost figure, limitations, and references have no identity marker, replacement
glyph, clipping, overlap, or caption drift. Private review PDF SHA-256:
`5d2a46f1a011e87b1575cd391bfc7ef5c4070fb1a38a1d75b91800cb4263ebdf`.
The separately tracked public technical-report PDF SHA-256 is
`51b68c45944283bf2c2b883dce8c690a986e839d5d005e1fe47ad87ca40eda8a`.
The machine-executable submission-claim cross-check
`tools/benchmark_carrier/verify_semantic_mapreduce_submission_claims.py`
passes all primary/second-scale F1, paired-unit CI, conditional-cost, external
scope, 27-row runtime-contract, archive-checksum, and paper-literal checks.

## Clean Replay Artifact Gate

The gate below has been run successfully for
`.sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e/`.
Run it again only when refreshing the submission artifact or changing reducer
code.

Prerequisite endpoint path:

```bash
# Optional: start the NPU3 service through the repo-owned dev-hub/runtime path.
# This launches through external/vllm-hust-dev-hub/manage.sh and enforces NPU3.
SAGE_REAL_ONLINE_NPU_DEVICE=3 \
SAGE_REAL_ONLINE_PORT=18383 \
SAGE_REAL_ONLINE_RUN_ID=clean-semantic-merge-endpoint \
SAGE_REAL_ONLINE_EVENTS=2000 \
SAGE_REAL_ONLINE_SHARDS=4 \
tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh \
  --skip-llm-reducer \
  --run-id clean-semantic-merge-endpoint
```

Clean hardcase replay:

```bash
RUN_ID=clean-pairwise-action-hardcases-$(git rev-parse --short HEAD) \
OUTDIR=.sage/benchmarks/real_online_semantic_merge/${RUN_ID} \
ALLOW_NPU3_REAL_ONLINE=1 \
SAGE_SMR_CONDA_ENV=esage-vllm-hust-dev \
SAGE_SMR_LLM_BASE_URL=http://127.0.0.1:18383 \
SAGE_SMR_LLM_MODEL=qwen25-7b-sage-realonline \
SAGE_SMR_LLM_MAX_EVIDENCE=24 \
SAGE_SMR_LLM_MAX_CANDIDATES=12 \
SAGE_SMR_LLM_MAX_TOKENS=8 \
SAGE_SMR_ENDPOINT_METADATA=.sage/benchmarks/real_online_semantic_mapreduce/20260718T-smr-multiseed-endpoint-5a8419e/metadata.json \
SEEDS=7,11,13 \
SCENARIOS=ambiguous-disconnected-merge,ambiguous-temporal-split,ambiguous-overmerge \
REDUCERS=semantic-graph,hybrid-hint,llm-pairwise-validated,llm-pairwise-action-validated \
SHARDS=8 \
INCIDENTS=4 \
bash tools/benchmark_carrier/run_npu3_semantic_merge_llm_comparison.sh
```

Required manifest fields:

- `evidence_label=real-online`.
- `conda_env=esage-vllm-hust-dev`.
- `hardware.npu_device=3` or equivalent `device_label=NPU3`.
- `git.commit`, `git.branch`, and `git.dirty=false`.
- Endpoint `base_url`, `model`, and `api_key_env`.
- Workload source: repo-local `src/sage/workloads/semantic_merge_analysis.py`.
- `third_party/llm-serving-workloads` commit and dirty status.
- Runtime submodule commits and dirty status, especially
  `third_party/ascend-runtime-manager`.
- Reducers, scenarios, seed, shards, incidents, token limits, and result path.

Pass criteria for keeping the current mechanism claim at a clean three-workload-
seed real-online result:

- `llm-pairwise-action-validated` has `fallback=0`, `invalid action=0`, and
  `invalid schema=0` over all nine case/seed runs.
- Mean F1 for `llm-pairwise-action-validated` is greater than `hybrid-hint`
  under the same scorer.
- `ambiguous-disconnected-merge` reaches F1 1.0 with at least one accepted
  evidence-preserving merge edit.
- `ambiguous-overmerge` does not regress below `hybrid-hint`.
- The result directory contains `manifest.txt`, `run_metadata.json`,
  `python-env.json`, `matrix/manifest.json`, `matrix/summary.json`,
  `matrix/scenario_summary.json`, `comparison_summary.json`,
  `case_seed_summary.json`, `case_seed_summary.csv`, and `artifact_gate.json`.

Machine-executable gate:

```bash
python tools/benchmark_carrier/verify_semantic_merge_artifact.py \
  .sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e \
  --endpoint-metadata \
  .sage/benchmarks/real_online_semantic_mapreduce/20260718T-smr-multiseed-endpoint-5a8419e/metadata.json
```

Anonymous package and recheck:

```bash
python tools/benchmark_carrier/package_semantic_merge_artifact.py \
  --comparison-dir .sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e \
  --endpoint-dir .sage/benchmarks/real_online_semantic_mapreduce/20260718T-smr-multiseed-endpoint-5a8419e \
  --output-dir .sage/benchmarks/submission_semantic_mapreduce/20260718T-smr-hardcases-3seed-5a8419e-anonymous \
  --archive .sage/benchmarks/semantic-mapreduce-3seed-real-online-5a8419e-anonymous.tar.gz
python tools/benchmark_carrier/verify_semantic_merge_artifact.py \
  .sage/benchmarks/submission_semantic_mapreduce/20260718T-smr-hardcases-3seed-5a8419e-anonymous/comparison \
  --endpoint-metadata \
  .sage/benchmarks/submission_semantic_mapreduce/20260718T-smr-hardcases-3seed-5a8419e-anonymous/endpoint/metadata.json
```

Fail criteria:

- Dirty parent commit, missing manifest fields, or missing submodule provenance.
- Any validated action fallback or invalid action/schema output.
- Action-validated F1 not above `hybrid-hint` on the three-hardcase aggregate.
- Accepted edits cite evidence that fails the validator.
