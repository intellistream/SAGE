# Findings & Decisions: Semantic MapReduce Submission Readiness

## Requirements

- Persistent `/goal`; do not finish after a single audit, TODO list, plan, or
  first failure.
- Preserve existing uncommitted work; read before edit; never overwrite others.
- Prioritize low-cost, high-discrimination multi-seed hardcase closure.
- Only run real-online after NPU3 endpoint/device, `esage-vllm-hust-dev`,
  repo-owned runtime/submodules, evidence label, and manifest gates pass.
- Report per case/seed F1, support recall, accepted edits, fallback,
  invalid action/schema, tokens, latency, and failure taxonomy.
- Retain hybrid-hint strong baseline and negative controls.
- Finish implementation/tests, claim ledger, paper tables/figures, artifact
  package, reviewer packet, anonymous 11-page packaging, citations, visual
  checks, artifact gate, reproduction commands, and clean provenance.

## Repository Recovery Findings

- Verified repository root: `/home/shuhao/SAGE`.
- Parent branch: `feature/semantic-mapreduce-paper`; HEAD:
  `d6d059e21c5168156e104a9c493402f2177ca9b2`.
- Initial parent `git status --short --branch` was clean.
- Relevant pinned submodules exist for vLLM-HUST, vLLM-Ascend-HUST,
  Triton-Ascend-HUST, dev-hub, Ascend runtime manager, and
  `llm-serving-workloads`; selected deeper recursive dependencies are currently
  uninitialized and must not be initialized unless required.
- Existing paper assets include `main.tex`, `main.pdf`, `claim-ledger.md`,
  `readiness-report.md`, `reviewer-packet.md`, and paper README.
- Existing harnesses include semantic-mapreduce offline and NPU3 scripts plus
  comparison/summary tools.
- The paper package currently contains three raster figures, a 62 KB TeX source,
  a 1.2 MB generated PDF, and substantial README/claim/readiness documents.
- No manifest/CSV/JSON result files were found under root-level `results/` or
  `artifacts/` at depth three; evidence paths may live elsewhere or be absent and
  must be resolved before accepting any numerical claim.
- Claim ledger and README point instead to ignored `.sage/benchmarks/...`
  directories. The leading result is explicitly single-seed: three controlled
  hardcases, mean F1 0.8857 vs hybrid-hint 0.6948, zero fallback/invalid action/
  invalid schema, about 534 estimated tokens and 326 ms mean reduce latency.
- Existing checked-in prose already warns against multi-seed robustness,
  production telemetry generality, quality-cost frontier, and full-evidence
  prompting claims. The requested work therefore aligns with documented gaps,
  but the underlying ignored artifact still needs direct inspection.
- The deterministic/hybrid evidence is broader (including 10-seed controlled
  suites), while live LLM action evidence remains seed 7. Full-evidence prompting
  is already retained as a negative control and hybrid-hint is the strong baseline.
- The ignored artifact is present and substantial. Its primary manifest records
  clean parent commit `c3d4dfa`, dedicated env `esage-vllm-hust-dev`, NPU3,
  endpoint `127.0.0.1:18383`, repo-local workload source, and clean runtime/
  workload submodule provenance with evidence label `real-online`.
- `matrix/summary.json` exposes scenario/seed F1, support recall, and reduce
  latency, but not accepted edits, fallback, invalid action/schema, or token
  fields. Those fields must be joined from aggregate/raw traces for the requested
  per-case/seed report or added to the summary schema.
- Raw reports already contain all missing fields in `cost_accounting`, including
  accepted edits, fallback, invalid action, JSON/schema validity, token estimates,
  retry count, validator rejection, and latency. The gap is aggregation/reporting,
  not instrumentation.
- `summarize_semantic_merge_llm_comparison.py` currently emits reducer-level
  means only. `run_semantic_merge_matrix.py` writes case/seed rows without the
  cost/failure fields and labels offline execution `simulation/model`. A small,
  deterministic per-case/seed summarizer extension can close most reporting
  requirements without new hardware use.
- Relevant parent-owned submodules are currently clean and on the expected
  project feature branches; no user edits were found inside them.
- The dedicated interpreter exists at
  `/home/shuhao/miniconda3/envs/esage-vllm-hust-dev/bin/python` and imports the
  `sage` namespace. Bare `conda` is not on non-interactive PATH, so future checks
  must use `/home/shuhao/miniconda3/bin/conda` or direct interpreter paths.
- Port 18383 currently has no listener. The first NPU query used an unsupported
  command form and returned usage rather than occupancy; retry must use the
  installed tool's `info -t usages -i 3` / `info proc` syntax.
- Absolute-path Conda inventory confirms `esage-vllm-hust-dev` exists and its
  Python imports the semantic workload with all nine scenarios. It was not the
  active shell environment, so commands must continue to use the direct path or
  explicit activation.
- NPU3 reports 65,536 MiB HBM, 5% HBM usage, and 0% AI-core/vector usage; the
  installed driver does not support `info proc`, so this is not yet sufficient
  to prove absence of a process. Port 18383 remains free. No online run is
  authorized by this partial gate alone.
- A second driver-supported process probe, `npu-smi info -t proc-mem -i 3`, now
  reports `No process in device`; `/dev/davinci3` also has no `fuser` owner.
  NPU3 is currently free, but parent dirtiness and missing endpoint still block
  a valid real-online run.
- The more complete `run_npu3_semantic_mapreduce_experiment.sh` already contains
  NPU isolation and submodule provenance logic that can guide hardening of the
  smaller comparison script; no need to invent a separate device policy.
- Controlled endpoint runs already emit `.sage/.../metadata.json` with exactly
  the needed binding fields: evidence label, base URL, NPU device, model path/
  served name, dedicated Conda env, clean parent commit, and clean repo-owned
  submodule commits. The comparison runner should require and validate this file
  before treating an existing endpoint as `real-online`.
- The comparison runner now requires that endpoint metadata and fails closed on
  wrong device/env, existing output, dirty parent/submodules, commit/submodule
  provenance mismatch, or failed health check. A preflight-only invocation
  correctly stopped at the current dirty-parent gate before contacting the model.
- After commit `33055c8`, the same preflight rejects the old endpoint metadata
  because its parent commit is `c3d4dfa`. This is the intended stale-provenance
  negative control; a new online run requires a newly launched endpoint manifest.
- A new controlled endpoint at commit `5a8419e` passed runtime pins, NPU3-only
  binding, Triton import, model loading, and health gates. The follow-on real-online
  matrix covers workload seeds 7/11/13 across all three hardcases.
- Action-validated aggregate over 9 case/seed rows: F1 0.9301 vs hybrid-hint
  0.7204, support recall 0.9815, 2.2222 accepted edits, 536.1111 estimated
  tokens, and 324.1933 ms reduce latency; fallback, invalid action, and invalid
  schema are all zero.
- Per scenario, action-validated is 1.0 F1 on disconnected merge for all seeds;
  temporal split is 0.8/1.0/1.0 with seed-7 retaining two unmatched fragments;
  overmerge is 0.8571 for all seeds with zero edits and one wrong-root miss.
- The free-form `llm-pairwise-validated` negative control has invalid JSON/schema
  and fallback on all 9 runs, matches hybrid F1, and averages 7.50 s because one
  seed-7 call took 62.5 s. The one-token contract therefore removes a concrete
  output-contract/tail-latency failure, not merely prompt wording.
- The real-online artifact records clean parent and all runtime/workload
  submodules, dedicated env, NPU3, model, workload source, and per-case schema.
  The managed service was stopped; a repo-owned aggressive cleanup removed its
  known isolated-container engine child, and NPU3/18383 are now free.
- The first rebuilt review PDF was 12 pages, with body/conclusion ending on page
  11 and all 18 references isolated on page 12. Before checking the live CFP,
  this was conservatively treated as a total-page failure and prompted useful
  removal of repeated prose; the official rule later confirmed references are
  excluded from the 11-page limit.
- Visual inspection of pages 9, 11, and 12 found no clipping or unreadable
  real-online table content. Page 9 is text-dense but legible; page 11 ends
  cleanly at the conclusion; page 12's large unused lower/right area confirms
  packaging, rather than content overflow, is the immediate PDF defect.
- Compacting repeated open-challenge/audit prose (without removing evidence or
  scope limits) yields an 11-page PDF. A complete page-by-page visual pass found
  all three figures, seven tables, equations, algorithm, and references legible
  and unclipped; the real-online table now begins page 10 at full column span.
- The first raw tarball was not double-blind safe: endpoint diagnostics exposed
  the local username, home path, hostname/private IP, and unrelated historical
  journal entries. The raw evidence remains unchanged, while the submission
  packager now allowlists six endpoint provenance files, sanitizes identity
  fields, records pre/post hashes, and rejects residual identity/email/private-IP
  matches. The extracted anonymous tar passes both anonymity and evidence gates.
- The official ASPLOS 2027 CFP confirms the required class already used by the
  draft (`sigplan,anonymous,review,nonacm`), US Letter, 10pt body, double-blind
  metadata/repository requirements, and an 11-page limit that excludes the
  generative-AI acknowledgment and references. It forbids reference squeezing
  and requires 8pt references, so the temporary 7pt bibliography override was
  removed. After adding complete clickable citation links, the final PDF has 11
  counted pages plus one references-only continuation page, uses 8pt references,
  and places the required generative-AI disclosure immediately before them.
- Citation audit corrected the LO2 entry's erroneous three-author attribution
  to the paper's full eight-author list and added official USENIX, DOI, arXiv,
  or project links to every reference while retaining full author names.
- Semantic workload code already classifies missed and false-positive incidents;
  the per-case reporter should surface these taxonomies rather than invent a new
  failure model.
- Existing tests already assert trace/cost/failure-taxonomy completeness and the
  hybrid/action contract, so the new reporter can be tested with a small raw
  fixture without touching model/network code.
- Before hardening, the online comparison script's gate was incomplete for the user's standard:
  it checks opt-in plus endpoint health but does not fail closed on dirty parent/
  submodules, exact NPU3 binding, dedicated-env resolution, or process occupancy;
  it also calls bare `conda` and creates the output directory before health
  validation. It must not be used for a new online run until hardened.
- The script rewrites the matrix evidence label to `real-online` and records
  submodules, but current `run_metadata.json` generation lacks an explicit
  hardware/device block. The clean artifact has that field because it was
  produced with a later/manual path; reproducibility needs one canonical gate.
- The new per-case/seed reporter passes its focused test and successfully joins
  the clean artifact. For action-validated seed 7 it reports: disconnected merge
  F1/support 1.0/1.0, 3 accepted edits, 483 estimated tokens, 287.16 ms reduce;
  temporal split 0.8/0.8333, 4 edits, 950 tokens, 573.26 ms, two unmatched
  fragments; overmerge 0.8571/1.0, 0 edits, 169 tokens, 116.7 ms, one wrong-root
  miss. All three have zero fallback/invalid action/invalid schema.
- This per-case view reveals the quality-cost boundary more clearly than means:
  the temporal-split gain is the most expensive case and still leaves two false
  positives; overmerge spends tokens while abstaining and preserving baseline.
- A 10-seed offline diagnostic confirms all three hardcase families maintain full
  evidence coverage. Hybrid-hint remains imperfect on every seed: disconnected
  merge F1 is fixed at 0.7273; temporal split ranges 0.5--0.6667 (mean 0.5678);
  overmerge ranges 0.5714--0.8571 (mean 0.7143). This validates the workload as
  discriminating across seeds but is `simulation/model`, not LLM robustness.
- The direct-interpreter diagnostic manifest correctly records dirty parent and
  `simulation/model`, but its `conda_env` is empty because the runner trusts
  `CONDA_DEFAULT_ENV`. This is a reproducibility bug when using the mandated
  dedicated interpreter directly; infer the environment from `sys.prefix` when
  the variable is absent.
- Manifest environment inference and the per-case reporter now pass the full
  semantic-merge workload test file: 20 tests passed in the dedicated environment.
- On seed 7, action-validated improves disconnected merge from hybrid F1 0.7273
  to 1.0 and temporal split from 0.5 to 0.8, while overmerge abstains/preserves
  F1 0.8571. This is discriminating mechanism evidence, not broad robustness.
- No previous root or scoped planning files were present; session catchup
  produced no unsynced report.

## Governance Findings

- Root `AGENTS.md` mandates project-specific Conda environment
  `esage-vllm-hust-dev`; the shared baseline environment must not be mutated.
- Root Copilot instructions forbid `.venv`/`venv`, require fail-fast behavior,
  and preserve the four-layer dependency direction and Flutty-first runtime.
- Runtime/workload changes must remain in repo-owned real Git submodules on
  project `feature/...` branches; no sibling-checkout dependency or symlink.
- Every paper result needs an evidence label. Only `real-online` can support
  measured live serving throughput/latency for its exact topology.
- An occupied reserved device is a stop condition for that run, not permission
  to kill a process, switch devices, or downgrade modes.
- Systems-paper review must start from the seven-step research logic, treat
  implementation as supporting evidence, and attach every major figure to a
  reviewer question.
- A benchmark/workload contribution must expose behavior invisible to existing
  benchmarks, define provenance and controlled axes, and distinguish fair peers
  from diagnostic/degraded-mode references; a controlled workload cannot imply
  production representativeness by itself.

## Seven-Step Research Skeleton (Initial, To Validate Against Draft)

1. Problem: structured semantic aggregation needs bounded, auditable actions
   rather than unconstrained prompt-only merging.
2. Importance: quality, validity, cost, and failure containment must be shown as
   a systems tradeoff, not assumed from workflow completion.
3. Gap: existing substrates/baselines may perform semantic merging but do not
   necessarily expose the same operator/action/validation contract; exact
   comparison and citations remain to be audited.
4. Key idea: operator algebra plus bounded one-token edits and validation turns
   semantic aggregation into a constrained execution mechanism.
5. Feasibility: current repo is mechanism-ready with single-seed evidence and
   already contains offline/NPU3 harnesses; missing closure must be inventoried.
6. Evaluation: multi-seed hardcases, hybrid-hint baseline, negative controls,
   quality/cost metrics, schema/action failures, and substrate comparisons.
7. Takeaway: must be a scoped knowledge claim about when bounded semantic
   reduction is effective—not “running the SAGE workflow is a contribution.”

## Issues Encountered

| Issue | Resolution |
|---|---|
| Broad governance search traversed unreadable sibling paths | Re-ran a checkout-local `rg` search; no project data was modified. |

## Resources

- `/home/shuhao/SAGE/AGENTS.md`
- `/home/shuhao/SAGE/.github/copilot-instructions.md`
- `/home/shuhao/SAGE/docs/papers/semantic_mapreduce/`
- `/home/shuhao/SAGE/tools/benchmark_carrier/`
- `/home/shuhao/SAGE/third_party/llm-serving-workloads`
