# Findings & Decisions: Semantic MapReduce Submission Readiness

## 2026-07-19 EuroSys'27 Cross-Submission Audit Baseline

- The cross-audit's authoritative handoff is parent branch
  `feature/semantic-mapreduce-paper` at local/upstream commit
  `0e64c15c7d501aeccb30ec5ad5d2d1eb554efa35`; ahead/behind
  is `0/0`, but the parent worktree is not clean.
- Dirty state comprises eight modified tracked files and four untracked Figure 3
  assets. These are pre-existing bounded-edit/held-out/paper/planning changes and
  must be inspected and integrated, not discarded or overwritten.
- Six relevant initialized submodules are pinned; the recursive LLVM/torch-mlir
  entries remain intentionally uninitialized. No `third_party` symlink was
  reported at depth two.
- Three independent read-only reviewers are active: systems/novelty/contract,
  experiments/statistics/provenance, and artifact/anonymity/fail-closed.
- The initial tracked-file inventory found `docs/papers/semantic_mapreduce/main.pdf`;
  public/private packaging variants and exact 12-page identity still require
  resolution from ignored artifact/output paths.
- The two 12-page, US-Letter candidates are now identified. The public tracked
  PDF is `docs/papers/semantic_mapreduce/main.pdf`, SHA-256
  `51b68c45944283bf2c2b883dce8c690a986e839d5d005e1fe47ad87ca40eda8a`,
  titled “Semantic MapReduce: An Auditable Operator Contract for LLM-Backed
  Reduction.” The untracked private-title review PDF is
  `.sage/submission/semantic-mapreduce-eurosys27/submission.pdf`, SHA-256
  `5d2a46f1a011e87b1575cd391bfc7ef5c4070fb1a38a1d75b91800cb4263ebdf`,
  titled “Auditable Semantic Reduction as a Bounded Runtime Operator.” The
  private hash exactly matches `NEXT_STEPS.md`.
- The user confirmed that the old concurrent writer stopped and was archived,
  and supplied its commit chain and dirty-path handoff. The earlier changing
  status is therefore attributed to that writer, not unknown external pollution.
  This thread preserves and integrates those changes as the sole writer.
- The current dirty paper draft adds a constrained-agglomerative baseline and a
  two-panel Figure 3. It explicitly admits the action path does not beat that
  policy, but calls the model baseline “hybrid pre-edit state”; executable-v1
  audit already found that model-seen H0 and fallback policy can differ, so this
  wording remains evidence-sensitive.
- The artifact verifier is fail-closed for missing top-level files, declared
  evidence label/env/device/dirty status, scenario/seed/reducer/sample shape,
  required summary-row fields, endpoint/run consistency, target-vs-hybrid mean,
  and selected contract outcomes. However, its current inspected path computes
  hashes only after trusting the supplied summary files; it does not yet prove
  those summaries were derived from the 243 raw reports, validate the CSV or
  aggregate contents, or validate `ANONYMIZATION_MANIFEST.json` coverage. This is
  a candidate P1/P0 artifact-integrity gap pending independent reviewer
  confirmation and adversarial tests.
- The claim verifier checks a useful fixed set of frozen numbers and archive
  SHA, but several paper assertions are verified only by literal substring
  presence. It is not by itself a semantic or raw-evidence derivation check.
- Two attempts to retrieve the official EuroSys 2027 CFP through the web tool
  returned no content. Use a different read-only retrieval path and record this
  as a tooling failure rather than silently relying on memory.
- Direct retrieval of the official EuroSys 2027 CFP confirms: at most 12 pages
  of technical content plus unlimited references; A4 or US Letter; 178 x 229 mm
  text block; two columns separated by at least 8 mm; all text including figures
  and captions at least 10pt on at least 12pt leading; grayscale readability;
  page numbers; double-blind good-faith anonymization; AI-tool use disclosure;
  and the fall full-paper deadline of 2026-09-24 AoE. The current two PDFs are
  12 total pages on US Letter, so page count itself is compliant; font size,
  block geometry, grayscale, page numbering, and disclosure still need direct
  verification.
- The normative review archive hash in `NEXT_STEPS.md` is correct:
  `.sage/benchmarks/semantic-reduction-eurosys27-review-evidence.tar.gz` hashes
  to `f590fde5...d73d4a0`. A safe independent extraction yielded 693 files and
  nine directories; the full-profile verifier passed at 5 samples, 9 scenarios,
  3 seeds, and the documented 0.8645 vs 0.7801 F1.
- Every extracted archive file except `ANONYMIZATION_MANIFEST.json` itself is
  listed and hash-covered by that manifest; all 692 listed hashes matched. The
  manifest's self-exclusion is structurally necessary unless a detached/root
  hash is used and is not by itself a blocker.
- The ignored unpacked directory with the same review-evidence stem currently
  contains 2,531 files, including 2,103 unlisted nested prior-finalization
  directories. The tarball remains clean at 693 files, but handoff language must
  name the archive (and its hash), not imply that the mutable unpacked directory
  itself has manifest-complete integrity.
- Reviewer A's first H0/action-algebra P0 was correct for the initial snapshot
  and executable v1 evidence. During the audit, external concurrent changes
  rewrote current `main.tex` to identify semantic-graph as the action H0, hybrid
  as a separate comparator/fallback, v1 as merge/no-op, and v2 as offline-only.
  Therefore the finding is adjudicated as “real issue, currently repaired in
  dirty TeX, must propagate to all docs and rebuilt PDFs,” not dismissed as a
  stale reviewer error.
- Reviewer A found a second substantiated claim bug: the four budget-8 events
  called “validator-rejected inadmissible actions” are actually malformed text
  responses mapped by `_parse_pair_action` to `ABSTAIN` with `valid=false`.
  The four summary rows have `invalid_action_count=1`, `fallback_count=0`,
  `validator_reject_reason=null`, and `commit_outcome=committed`; raw text is
  “Based on the input JSON-like-object,”. The code maps every non-MERGE v1 token
  to `keep`. Paper and handoff must say “four malformed/non-enum responses were
  fail-closed to ABSTAIN/no-op,” not validator rejection.
- Reviewer C found and the main thread confirmed a concrete private-PDF handoff
  defect: `.sage/submission/semantic-mapreduce-eurosys27/build-manifest.json`
  says 11 pages and SHA `6924163...`, while the actual file is 12 pages and SHA
  `5d2a46...`. The PDF itself and `NEXT_STEPS.md` agree; the build manifest is
  stale and must be regenerated or corrected by the packaging workflow.
- Reviewer B found a substantiated runtime-contract evidence flaw. The 27-row
  runner validates `deepcopy(baseline)` as the “valid output,” so the committed
  state equals the baseline in every row. `valid_commit_passes` counts only
  `valid_schema`, not an actual state transition. The recovery call snapshots
  the still-live service at recovery time before instantiating/restoring a new
  object, so this demonstrates serialization/reconstruction round-trip, not
  recovery from an independently persisted pre-failure checkpoint. The current
  table labels “Valid transition commits” and “Checkpoint digest restored” are
  therefore materially stronger than the experiment. Repair requires a
  state-changing legal edit, a pre-recorded checkpoint independent of the live
  object, and aggregate gates that assert digest change plus exact restoration;
  otherwise the paper must downgrade the claims.
- The strongest remaining systems-review conflict is central scope: current TeX
  honestly says v2 proposal catalogs, true SPLIT, atomic batches, and shared
  catalogs are offline-only, while the only real-online evidence is historical
  v1 merge/no-op. This is not a prose-only defect. Either produce clean, fair v2
  evidence (and online evidence if the contribution headline remains the live
  action algebra), or explicitly scope the submitted mechanism to offline
  contract validation plus historical integration evidence. Calling the paper
  ready while this remains unresolved would be misleading.
- Reviewer A also identified a plausible closest-work novelty gap: the current
  related-work section does not discuss DocETL, SagaLLM, or recent transactional
  agent/runtime systems that overlap declarative LLM operators,
  independent validation, versioned state, commit/rollback, provenance, or
  audit. These citations and claimed overlaps require primary-source
  verification before paper edits, but the paper must isolate novelty to its
  partitioned-evidence reducer semantics and bounded proposal catalog rather
  than claiming generic validator-owned transactionality as wholly missing.
- Reviewer C found a submission-blocking anonymity leak in the nominal final
  archive. Its sole top-level directory is
  `20260719T-final-multievidence-a48f1e6`; `a48f1e6` resolves exactly to this
  public repository's commit `a48f1e6bb387...` (“artifact: document
  supplementary evidence boundaries”). The packager audits only 40-hex SHA
  patterns, while tar creation preserves `output_dir.name`, so the current
  `f590...` archive is not double-blind safe despite all 692 internal file hashes
  matching. It must be rebuilt under an opaque root, and packaging tests/audit
  must reject short revision prefixes in archive paths and content.
- Both existing PDFs predate the current TeX and remain semantically stale: they
  present the old full-action/hybrid-H0/rejected-action narrative and do not
  contain the 0.9287 constrained baseline or v1/v2 boundary. All earlier visual
  checks apply only to superseded bytes. Rebuild, new hashes, claim gate, format
  checks, and full visual inspection are mandatory after corrections.

## 2026-07-19 Bounded-Edit Goal Reset

- The new objective supersedes the prior submission-readiness conclusion: the
  goal is mechanism completeness and offline-evidence readiness, not a deadline.
- Required initial provenance matches exactly: parent branch
  `feature/semantic-mapreduce-paper`, HEAD
  `2e709088f77e4cd475a8cf81b02cfb33e5724238`, origin branch contains that
  commit, and remote is `git@github.com:intellistream/SAGE.git`.
- Parent dirtiness is limited to the five warned paper/Figure 3 draft paths:
  modified `main.tex` plus four untracked data/figure/plot/test files. Treat all
  five as user work; inspect and preserve or revise factually, never overwrite.
- The frozen historical online directory and the clean strong-baseline directory
  both exist. The frozen directory remains read-only and cannot be reinterpreted
  under future SPLIT semantics.
- Recorded submodule pins: Triton `612d577`, vLLM-Ascend `339b27a`, vLLM
  `5de748b`, dev-hub `7ab7499`, Ascend runtime manager `c5b0461`, and shared
  workloads `79ed8e3`. Recursive LLVM/torch-mlir dependencies are uninitialized;
  do not initialize unless the implementation actually requires them.
- No symlinks were reported under `third_party` at depth two.
- The existing planning files describe a completed prior ASPLOS-readiness phase
  and are therefore reopened/re-scoped for true SPLIT, fair selection, held-out
  ambiguity, clean offline evidence, and claim/handoff work.
- All six relevant initialized submodules are clean and on project-specific
  `feature/...` branches. In particular, `third_party/ascend-runtime-manager` is
  the required real submodule on `feature/semantic-mapreduce-runtime-integration`.
- The uncommitted paper draft adds a constrained-agglomerative baseline and a
  Figure 3 sourced from the clean offline matrix plus frozen online summary. It
  also introduces the known-false phrase “hybrid pre-edit state”; preserve the
  draft but revise that statement after the executable H0 audit.
- The draft's own paired data records action versus constrained as 3 wins, 15
  ties, and 9 losses with mean delta -0.0384 on 27 matched units. It correctly
  distinguishes 0.9287 (90-unit controlled aggregate) from 0.9028 (matched
  constrained), but currently mixes policies with unequal candidate permissions.
- Current implementation is concentrated in
  `src/sage/workloads/semantic_merge_analysis.py`; action reducer counters still
  hard-code `split_count: 0`, while bounded action labels advertise SPLIT.
- Existing focused tests include true-SPLIT expectations for a different/free-form
  path, but the action path tests equate accepted edits with merges. This confirms
  that tests and trace claims must be separated by reducer/version, not inferred
  from the enum vocabulary.
- The legacy action reducer builds H0 with `SemanticGraphMergeReducer` but its
  validated subclass defaults the separately executed fallback reducer to
  `HybridHintMergeReducer`; request/validation failure can therefore replace the
  model-seen H0 with a different policy state.
- In the action loop, only `MERGE` creates a merge decision. KEEP, SPLIT, and
  ABSTAIN are all converted into pairwise `keep`; the trace preserves the token
  but the state machine does not distinguish their outcomes.
- `_validate_hybrid_edits` checks candidate/output evidence as sets and may
  repair root/affected fields, but does not enforce unique ownership, reject
  foreign IDs/duplicates, validate proposal existence, detect conflicts, or
  implement atomic proposal batches.
- The old runtime benchmark validates complete prebuilt hybrid hypotheses
  against semantic-graph candidates. It does not construct a proposal catalog,
  select proposal IDs, test true edits, or replay selection/catalog digests.
- The v2 executable contract is now frozen in
  `docs/papers/semantic_mapreduce/bounded-edit-runtime-contract.md` before code
  changes: explicit H0, finite typed catalog, ID-only selection, atomic rollback,
  real SPLIT, distinct outcomes, deterministic digests/replay, and legacy labels.
- Existing legal hypotheses represent `root_service` separately from
  `affected_services`; semantic-graph H0 does not always repeat the root in the
  affected list. V2 therefore validates both fields against evidence-observable
  services/hints without inventing a new root-membership schema requirement.
- The first v2 core suite now passes 12/12 in `esage-vllm-hust-dev`, covering
  real SPLIT output partitions, duplicate/missing/foreign/single-part rejection,
  merge union, atomic conflicts, distinct no-op outcomes, request/selection
  failures, source/order/renaming invariance, catalog truncation, checkpoint
  digests, and action/trace agreement.
- Frozen held-out workload configuration now defines four development seeds,
  four disjoint held-out seeds, ten ambiguity axes, exact hint corruption,
  overlapping score distributions, topology missing/stale, unseen service,
  mixed split+merge, budget truncation, and fragmentation/shard variation.
- The fair harness evaluates H0, proposal oracle, deterministic selector,
  mock ID-only model-policy emulator, and constrained full-evidence reference.
  H0/deterministic/mock share an exact catalog digest; the oracle is explicitly
  diagnostic and constrained is explicitly a broader-permission reference.
- Per-unit output includes all five F1 values, selected/proposed/accepted/rejected
  actions, evidence conservation, catalog truncation, source-label diagnostic
  merge/split proposal recall, selector/oracle overlap, conditioned deltas,
  separability, and failure taxonomy. No endpoint/model/NPU is invoked.
- The existing full-profile artifact verifier reads the frozen five-sample,
  nine-family, three-seed online directory without modification and still PASSes
  at historical action F1 0.8645 versus hybrid 0.7801. A whole-tree content-hash
  baseline is `ce66fbe00b7896bd8fdca5e104c6103de6dac3bdac1cb1503167339a5b9d873c`.
- Dirty development seed-7 diagnostic (not claim evidence) produced 10 units:
  oracle repaired 8/9 erroneous H0 units; improving merge proposals appeared in
  6 units and improving splits in 4; shared catalogs matched. The score proxy
  remained 0.9404 and failed its frozen gate, while the hint proxy was 0.63.
- Development negatives are retained: hint-error deterministic/mock selection
  regressed H0 F1 0.2857 to 0.2; shared-hint remained 0.2857; budget=2 truncated
  22 merge and 2 split proposals. Constrained full-evidence reached 1.0 on the
  mixed and truncation units, exposing the bounded catalog/permission gap.
- The first oracle implementation searched at most two edits, so deterministic
  multi-edit selection exceeded it on mixed/fragmented units. The oracle is now
  defined as the upper envelope of bounded search plus both evaluated policy
  selections; this preserves its diagnostic-upper-bound meaning.
- The revised development-only seed-7 diagnostic passes every frozen offline
  gate: score proxy 0.6210, hint proxy 0.63, repairable H0 10/10, improving
  merge units 9, improving split units 4, and identical shared catalogs. Oracle
  is now >= both selectors on all ten units. This authorizes broader offline
  evaluation only; it is not online readiness or paper evidence.

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

## 2026-07-19 Seven-Step Mechanism Reframe

1. **Problem:** A model-backed reducer currently has no executable contract
   tying advertised actions to finite legal state transitions; legacy SPLIT was
   a no-op and rejection could switch to a different baseline state.
2. **Importance:** Without state/evidence conservation, atomic rollback, and
   replayable proposal identity, semantic aggregation cannot be audited like a
   data operator and quality comparisons conflate policy with permissions.
3. **Existing-work/evaluation gap:** Adjacent AIOps/root-cause systems and the
   full-evidence constrained reducer do not expose the same H0-edit permission.
   The old controlled generator also made score/hint close to label proxies.
4. **Key idea:** The system owns H0 and a finite MERGE/SPLIT/KEEP/ABSTAIN
   proposal catalog; any policy chooses IDs only, and a system validator commits
   the batch atomically or preserves the exact H0.
5. **Feasibility/scope:** V2 is a repo-local, model-free runtime/harness slice
   using observable evidence and a project-specific Conda environment. It can
   be mechanism-complete offline without NPU or credentials; new online model
   evidence remains a separate gated step.
6. **Evaluation:** Shared H0/catalog deterministic and mock-ID selectors,
   proposal oracle diagnostic, permission-labeled constrained reference,
   adversarial/property/replay tests, and frozen dev/held-out ambiguity axes.
   Success and failure gates were fixed before viewing held-out seeds.
7. **Takeaway:** If supported by clean evidence, others should cite the work as
   showing that model-backed semantic reduction can be expressed as a finite,
   evidence-conserving, replayable transaction whose policy quality is separable
   from proposal coverage and reducer permission—not that models necessarily
   beat strong deterministic grouping.

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
