# Progress Log: Semantic MapReduce ASPLOS 2027

## Session: 2026-07-19 — EuroSys'27 Cross-Submission Readiness Audit

### Phase X1: Independent Review and Provenance

- **Status:** in_progress
- Loaded the required persistent-planning, seven-step research, systems-paper,
  benchmark, real-experiment, paper-figure/PDF, and optimization-repository
  instructions and their relevant review references.
- Restored the existing planning state rather than replacing the unfinished
  bounded-edit work.
- Delegated three independent, strictly read-only reviewers covering (A)
  systems novelty/semantic contract/related work/claims, (B) experiments and
  statistics including 51 tests/243 reports/evidence classes, and (C) artifact,
  anonymity, independent unpacking, PDF format, and fail-closed verification.
- Verified parent branch `feature/semantic-mapreduce-paper`, HEAD and upstream
  both `0e64c15c7d501aeccb30ec5ad5d2d1eb554efa35`, ahead/behind `0/0`, and
  recorded all current dirty paths without modifying or discarding them.
- Enumerated recursive submodule pins and confirmed no shallow `third_party`
  symlinks. Began the public/private PDF, artifact, verifier, and handoff asset
  inventory.
- Resolved both 12-page US-Letter PDFs and verified their SHA-256 values; the
  private-title PDF matches the frozen hash documented in `NEXT_STEPS.md`.
- The user supplied the archived writer's authoritative handoff and confirmed
  it is stopped. The prior status changes are therefore resolved as that
  writer's expected commits (`a2acd80`, `8b61cbf`, `cef913c`, `0e64c15`) and
  working changes, not unknown pollution. This thread is now the sole writer.
- Read the complete current paper diff. The draft introduces the strongest
  constrained baseline and openly reports the model path loses on matched
  quality, while leaving a potentially inaccurate “hybrid pre-edit state” claim
  for evidence adjudication.
- Audited the verifier, packager, claim-checker, and focused artifact tests. The
  verifier has strong top-level presence/provenance/shape gates but currently
  appears not to derive summary claims from raw reports or validate the
  anonymization-manifest inventory; this is queued for adversarial reproduction.

### Errors

- The official EuroSys 2027 CFP returned empty output in two web retrieval
  attempts (search and direct open). Next attempt will use a different read-only
  retrieval mechanism and will not treat cached prose as authoritative.
- The first state-changing runtime-contract test pass failed because
  `CandidateState` has no convenience `hypotheses` property and the decorated
  test service declaration is not directly callable. Replaced the former with
  explicit candidate-hypothesis extraction and the latter with a plain local
  checkpoint-capable test service; no behavior was weakened.
- The first fail-closed artifact-fixture pass correctly rejected legacy unit
  fixtures that contained empty summary/aggregate/CSV placeholders. Rebuilt the
  fixtures with raw reports, unique matrix keys, summaries, aggregates, CSV,
  and anonymization hashes; then aligned optional target-only fields without
  weakening required full-profile checks.
- Retrieved the official CFP directly and recorded the exact page, geometry,
  font, grayscale, anonymization, AI disclosure, and deadline requirements.
- Safely extracted the normative review archive in `/tmp`, confirmed 693 files,
  verified all manifest-covered hashes, and ran the full five-sample artifact
  verifier successfully without writing the repository. The mutable ignored
  unpacked sibling contains extra unmanifested nested copies, so only the hashed
  tarball is currently a stable handoff object.
- Adjudicated reviewer A's H0/action-algebra finding against code, raw reports,
  and the concurrently changed TeX: the issue was real in the initial snapshot;
  the current dirty TeX fixes it, but other documents and both PDFs remain to be
  synchronized and rebuilt.
- Independently verified that the four “rejected action” rows are parser-level
  malformed responses mapped to ABSTAIN/no-op, not validator rejections. Logged
  exact raw text, counters, null reject reason, and parser/reducer code path.
- Confirmed reviewer C's private build-manifest mismatch: manifest records an
  obsolete 11-page PDF/hash while the actual private PDF is the documented
  12-page `5d2a46...` artifact.
- Reproduced reviewer B's runtime-contract diagnosis in source: the “valid”
  output is a deepcopy of baseline, the aggregate equates schema validity with
  a successful transition, and recovery snapshots the live object at invocation
  time. Queued a state-changing/persisted-checkpoint repair rather than merely
  relabeling 27/27.
- Recorded the unresolved v1-online/v2-offline contribution split as a genuine
  submission risk and queued primary-source verification for the closest-work
  novelty gap.
- Reproduced reviewer C's short-SHA anonymity leak: the final tar root embeds a
  seven-character public commit prefix that the 40-hex-only path scanner misses.
  Marked the documented `f590...` package non-submittable and queued an opaque
  root plus regression tests.
- Confirmed both public/private PDFs are stale relative to current TeX; their
  page/hash/visual attestations cannot be carried forward.
- All three read-only reviewers returned `NOT READY`. Their common P0s are the
  v2-offline/v1-online contribution split and stale publication assets. The
  artifact reviewer additionally found a short public SHA in the archive root;
  the experimental reviewer found non-state-changing runtime rows and no raw
  closure; the systems reviewer found missing closest semantic-transaction work.
- Repaired the runtime harness so all 27 model-free rows commit a digest-changing
  catalog proposal, reject an unknown proposal, corrupt live state, restore a
  supplied pre-failure snapshot into a new service instance, and replay the
  committed digest. Focused runtime/shared-state tests pass (`18 passed`).
- Extended the artifact verifier through raw-report, CSV, aggregate, comparison,
  Cartesian-key, and anonymization-manifest inventory/hash closure. Hardened the
  packager to use archive root `artifact` and reject short revisions in paths;
  refined content scanning to known source revisions after catching 122 false
  positives from timestamps/request IDs. Combined focused tests pass (`24 passed`).
- Added family-clustered bootstrap sensitivity and Figure 3 input hashes. The
  matched action-minus-constrained delta remains `-0.0384`; clustered 95% CI is
  `[-0.0955, 0.0247]`. Profiled 540 controlled rows: each plotted policy has
  90 observations and discrete/tied F1 values, so a jittered raw-point plot is
  more honest than a mean bar; panel B uses direct family means, not an n=3 box.
- Verified primary descriptions for DocETL, SagaLLM, Cordon, and Mnemosyne and
  added them as the closest pipeline/transaction neighbors. Narrowed novelty to
  the partitioned-evidence-to-incident reducer contract and finite proposal
  catalog, not generic transactionality.

## Session: 2026-07-19 — Bounded Edit Runtime and Fair Offline Evidence

### Phase 1: Provenance and Design Audit

- **Status:** in_progress
- Read the complete goal objective and registered the substantive persistent
  goal after completing the initial file-read goal (23,027 tokens, 38 seconds).
- Loaded the persistent-planning and optimization-repository workflow skills,
  including the full optimization playbook, and ran session catchup.
- Verified parent branch/HEAD/remote/status, remote containment of the expected
  pushed commit, recursive submodule pins, absence of shallow `third_party`
  symlinks, and existence of both required artifact directories.
- Confirmed the only parent dirty paths are the five explicitly warned
  paper/Figure 3 drafts; no edit, reset, checkout, NPU access, or online run was
  performed.
- Reopened and re-scoped the persistent plan because the previous plan's
  submission-readiness completion does not satisfy the new mechanism goal.
- Verified every relevant initialized submodule is clean and on its required
  project `feature/...` branch.
- Read the complete dirty `main.tex` diff and all four untracked Figure 3
  assets. Recorded the exact inaccurate hybrid-H0 statement and the draft's
  matched 3/15/9 action-versus-constrained result without modifying user work.
- Located the reducer/action/trace implementation and current tests; confirmed
  the action reducer advertises SPLIT while recording `split_count = 0`.
- Audited the legacy apply/validator/trace/runtime-contract benchmark paths and
  recorded their H0/fallback mismatch, no-op action collapse, missing ownership
  and atomicity checks, and non-catalog replay limitation.
- Added the executable v2 bounded-edit runtime contract design document before
  implementation, including fixed action semantics, three oracle-free split
  generators, atomic batch rules, distinct outcomes, and historical v1 handling.
- Added the separate `semantic_reduce_edit_runtime.py` v2 implementation and 12
  focused tests covering true SPLIT, conservation, malicious partitions, merge,
  outcome counters, conflicts/atomicity, invariance, budget, checkpoint, and
  executable-action trace agreement.
- First dedicated-environment run: 9 passed, 3 failed. Two failures are fixture
  precedence mistakes (duplicate evidence is correctly rejected first); one is
  a merge proposal rejected by downstream schema validation and is under audit.
- Diagnosed the merge rejection as a mismatch between the new validator and the
  existing legal hypothesis schema (root is separate from affected services),
  corrected the validator and malicious fixtures, and reran: 12 passed in 0.17s.
- Froze development/held-out seeds, ten ambiguity axes, proposal parameters, and
  success gates in `experiments/semantic_mapreduce/heldout_v2_config.json` before
  viewing a held-out matrix; added deterministic held-out generation/tests.
- Initial combined run: 14 passed, 1 failed because Bernoulli hint corruption
  under-realized the configured error rate on a small unit. Replaced it with
  stable exact-count hash-ranked corruption; no result matrix has been run.
- Added the shared-catalog evaluation module and offline matrix entry point with
  complete clean-provenance manifest, permission labels, proposal coverage,
  separability, per-policy actions/failures/conservation, and frozen gate
  aggregation. Focused runtime/workload/harness run: 17 passed in 0.97s.
- Ruff identified five mechanical import findings in new files; recorded and
  corrected them with narrow edits. No behavior or user draft was changed.
- Invoked the legacy artifact verifier as a read-only function on the frozen
  full matrix: PASS, five samples, historical action F1 0.8645 vs hybrid 0.7801.
  Recorded a whole-tree content hash for final immutability verification.
- Added generator-specific and independent-process replay tests. The first run
  showed that the existing temporal workload's H0 had already split the large
  gap, so the generator correctly emitted no plan; replaced the unit fixture
  with an actual single-candidate temporal overmerge precondition.
- Pre-commit focused/legacy test gate passes 42 tests in 1.78s and
  `git diff --check` is clean. The first secret-scan command had a shell quoting
  error before scanning; recorded it and switched to simpler patterns.
- Committed and pushed three explicit slices: bounded runtime/design `a2acd80`,
  adversarial/replay tests `8b61cbf`, and held-out fair harness `cef913c`;
  local and remote matched at `cef913c`.
- Ran only a dirty development seed-7 diagnostic (new non-overwriting path; no
  NPU/endpoint). It exposed a failed score-proxy gate and an oracle search-depth
  flaw. Recorded all negative rows, crossed score overlap into every family,
  and made the oracle include both policy selections before any held-out run.
- Reran the same development-only seed after the fixes at a new path. All frozen
  offline gates pass and the oracle upper-envelope invariant holds on 10/10
  units; added a regression assertion. No held-out seed has been viewed yet.
- Loaded and applied the seven-step, systems-paper, benchmark-contribution, and
  real-experiment provenance skills before claim editing. Added the updated
  seven-step argument: finite evidence-conserving transactions and fair policy
  permissions, not model quality superiority or submission readiness.
- Corrected the paper abstract/evaluation and working Figure 3 framing: legacy
  action H0 is semantic-graph, v1 is merge-only, hybrid is comparison/fallback,
  constrained has broader permission, and v2 SPLIT is offline-only. Added
  superseding status/claim sections to readiness, ledger, reviewer packet,
  README, NEXT_STEPS, and root README without deleting historical evidence.
- Regenerated the working Figure 3 data/TikZ from the unchanged clean/frozen
  inputs with new permission metadata. Ruff then found one import-placement
  issue in the draft plot script; corrected it for the next gate.

## Session: 2026-07-18

### Phase 1: Repository and Evidence Recovery

- **Status:** in_progress
- **Started:** 2026-07-18 Asia/Shanghai
- Created the persistent Codex goal with the user's completion/blocking rules.
- Loaded the optimization repository, file-planning, seven-step research, and
  real-experiment-readiness instructions plus required references.
- Verified `/home/shuhao/SAGE`, branch `feature/semantic-mapreduce-paper`, HEAD
  `d6d059e21c5168156e104a9c493402f2177ca9b2`, and initially clean parent status.
- Enumerated parent submodules and found existing paper/harness assets.
- Read root governance and recorded environment, submodule, device, and claim
  boundaries.
- Created `task_plan.md`, `findings.md`, and `progress.md`; no prior copies existed.
- Loaded systems-paper and benchmark-contribution review rules before auditing
  draft claims or workload validity.
- Re-read the persistent plan and inventoried the paper package and conventional
  root result directories; conventional `results/`/`artifacts/` yielded no raw
  result inventory at the searched depth.
- Mapped readiness, ledger, reviewer-packet, and README claims to their named
  `.sage/benchmarks` assets and confirmed that the primary unresolved reviewer
  gap is multi-seed live action evidence plus quality-cost/generalization scope.
- Directly inspected the clean hardcase artifact and confirmed manifest-backed
  NPU3/env/submodule provenance and per-case seed-7 quality/latency rows.
- Traced accepted-edit/fallback/invalid/token data to raw `cost_accounting` and
  identified the current summarizer's reducer-only aggregation as the immediate
  low-cost implementation gap.
- Verified all relevant submodule worktrees are clean, the dedicated Python
  interpreter exists, and port 18383 is free. Logged and corrected the local
  Conda/NPU CLI invocation mismatches before retrying occupancy checks.
- Confirmed the dedicated Conda environment imports the workload and recorded
  low NPU3 utilization; process-level occupancy remains unproven because the
  local driver rejects process queries.
- Audited benchmark tests and the NPU3 comparison script. Decided not to invoke
  it because its current preflight does not satisfy the requested fail-closed
  dirty/device/environment gates.
- Implemented `case_seed_summary.json/.csv` generation and a focused regression
  test; the dedicated environment reports `1 passed`.
- Regenerated only derived summaries for the clean seed-7 artifact and verified
  every requested metric/failure field for the action-validated reducer.
- Ran a 10-seed, three-hardcase offline baseline diagnostic (`simulation/model`)
  and confirmed full coverage plus persistent hybrid blind spots. Logged the
  empty Conda-name manifest defect exposed by direct-interpreter execution.
- Fixed Conda-name inference for direct project-interpreter runs and ran the
  reporter plus semantic workload test files: `20 passed in 0.62s`.
- Obtained a supported process-level NPU3 check: no device process and no
  `/dev/davinci3` owner. Kept online work blocked because the parent is dirty and
  the endpoint is not running.
- Confirmed the canonical controlled-endpoint metadata schema and selected it as
  the required provenance input for future existing-endpoint comparisons.
- Hardened the online comparison runner and verified shell syntax. Its
  preflight-only check stopped at the expected dirty-parent gate, so no model
  request or output directory was created.
- Applied Ruff import/format fixes and reran validation: Ruff clean, shell
  syntax clean, and 20 focused tests pass.
- Committed the auditable evidence slice as `33055c8` and verified the clean gate
  rejects stale endpoint provenance from commit `c3d4dfa`.
- Committed preflight evidence as `5a8419e`, launched a new controlled NPU3
  endpoint, passed full runtime/Triton/health gates, and completed a minimal
  three-seed real-online hardcase matrix.
- Generated 36 raw reducer reports plus per-case JSON/CSV. Action-validated
  improves mean F1 from hybrid 0.7204 to 0.9301 with zero fallback or invalid
  outputs; the free-form validated negative fails schema in all 9 LLM rows.
- Stopped the exact managed service and used its repo-owned isolated-container
  cleanup for the residual child; confirmed NPU3 has no process and port 18383
  has no listener.
- Added a machine-checkable artifact verifier plus regression test, generated a
  checksummed real-online artifact archive, and passed the gate on the three-seed
  evidence package.
- Updated the abstract, evaluation table, claim ledger, readiness report,
  reviewer packet, and artifact README to the scoped three-seed result; rebuilt
  the PDF successfully.
- Rendered the PDF and visually inspected the real-online evidence page,
  conclusion page, and bibliography page. The table is legible, but the build
  is 12 pages and therefore remains blocked on the 11-page packaging gate.
- Removed repeated positioning prose from the open-challenges/audit sections,
  rebuilt to exactly 11 pages, rerendered every page, and completed a full visual
  inspection with no clipping, overlaps, or unreadable tables/figures.
- Audited the raw archive for double-blind leakage, added an allowlisted
  anonymizing packager and regression test, generated the anonymous archive,
  extracted it independently, and passed both the anonymity scan and evidence
  verifier. The raw run remains untouched for provenance.
- Ran the complete applicable suite in `esage-vllm-hust-dev`: Ruff and shell
  syntax clean, 33 tests passed, raw and anonymous artifact gates passed, all
  submodules clean, NPU3 free, and port 18383 closed.
- Checked the live ASPLOS 2027 CFP, removed the temporary bibliography squeeze,
  added the mandated generative-AI disclosure, and rebuilt. At this stage the PDF
  remained 11 total pages, used the required review class and 8pt references,
  had no author metadata, and the updated final page was visually clean.
- Audited all 18 bibliography entries, corrected LO2's author list, and added
  clickable official/DOI/arXiv links. The final file is 12 PDF pages only because
  references continue onto page 12; all counted content remains within page 11,
  matching the official CFP, and both reference pages were visually inspected.

## Test Results

| Check | Expected | Actual | Status |
|---|---|---|---|
| Repository identity | `/home/shuhao/SAGE` | `/home/shuhao/SAGE` | PASS |
| Parent branch | paper feature branch | `feature/semantic-mapreduce-paper` | PASS |
| Initial parent worktree | Preserve and inventory user changes | Clean | PASS |
| Session catchup | Recover prior state if present | No prior planning/catchup state | PASS |
| Per-case summary unit test | New schema and CSV are emitted | `1 passed in 0.17s` | PASS |
| Clean artifact derived summary | All requested fields join from raw reports | 3 action-validated case rows verified | PASS |
| Semantic merge focused suite | Reporter + workload/operator contracts | `20 passed in 0.62s` | PASS |
| Online preflight dirty gate | Dirty parent must prevent model access | Refused with explicit dirty-parent error | PASS |
| Ruff + shell syntax | Changed Python/shell files are clean | All checks passed | PASS |
| Stale endpoint provenance gate | Old commit metadata must be rejected | Rejected `c3d4dfa` vs current `33055c8` | PASS |
| New endpoint preflight | NPU3/env/model/commit/submodules/health | All gates passed at `5a8419e` | PASS |
| Three-seed real-online hardcases | Action path beats hybrid without invalid/fallback | F1 0.9301 vs 0.7204; all invalid/fallback counts zero | PASS |
| Managed cleanup | Only launched service removed; NPU3/18383 free | No NPU3 process; no listener | PASS |
| Artifact gate | Complete fields, clean provenance, baselines/controls, checksums | PASS on `20260718T-smr-hardcases-3seed-5a8419e` | PASS |
| PDF build | Tectonic build; counted content ≤11 pages; references 8pt | 12 PDF pages, page 12 references only | PASS |
| PDF visual check | Tables/content are legible and unclipped | All content plus final reference pages inspected | PASS |
| Final PDF packaging | Official anonymous review form and 11-page counted-content limit | Body ends on page 11; references excluded by CFP | PASS |
| Anonymous artifact | No identity/private-IP/email leak; exact evidence survives | Extracted tar clean; verifier PASS | PASS |
| Complete applicable test suite | Workloads, reporter, artifact gate/packager | `33 passed in 4.35s` | PASS |
| Final device/submodule state | NPU3/18383 free; all submodules clean | Verified | PASS |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|---|---|---:|---|
| 2026-07-18 | Broad `find ..` hit permission-denied sibling paths | 1 | Restricted governance search to repository-local paths with `rg`. |
| 2026-07-18 | Bare `conda` not found | 1 | Use `/home/shuhao/miniconda3/bin/conda` and the dedicated interpreter. |
| 2026-07-18 | Unsupported `npu-smi info -i 3` form | 1 | Switch to advertised type/process forms for the installed CLI. |
| 2026-07-18 | Offline manifest omitted Conda name under direct interpreter | 1 | Infer environment from `sys.prefix`; do not use the dirty diagnostic as submission evidence. |
| 2026-07-18 | Ruff import/format findings | 1 | Applied automated fixes and reran checks/tests. |
| 2026-07-18 | Runtime-generated dev-hub lock dirtied preflight | 1 | Preserved it in endpoint artifact; source checkout returned clean. |
| 2026-07-18 | Managed stop left launched engine child | 1 | Ran scoped repo-owned container cleanup and verified device/port free. |
| 2026-07-18 | Poll wrapper JS parse error | 1 | Simplified polling; live run continued unaffected. |
| 2026-07-18 | ImageMagick `montage` unavailable for contact sheet | 1 | Inspected rendered pages directly with the image viewer. |
| 2026-07-18 | Two combined doc/planning patches missed current context | 2 | Reapplied as narrow patches with exact context. |
| 2026-07-18 | Ruff found an unused `shutil` import in the packager | 1 | Removed it; all checks pass. |

## 2026-07-19 Cross-Submission Audit Update

- Collected three independent read-only reviews and recorded a single NOT READY
  disposition with evidence-based v1/v2 scope adjudication.
- Committed and pushed mechanism/runtime/statistics/related-work repairs as
  `bb140c0`, then ran clean development, held-out, and 27-row runtime matrices
  without NPU, endpoint, model, or credentials.
- Rebuilt the anonymous package with constant `artifact/` root, exact raw and
  inventory closure, controlled baselines, v2 matrices, supplied-checkpoint
  runtime evidence, bundled verifier, and standard-library environment record.
- Independently inspected 1,342 safe tar members, extracted into a fresh
  temporary directory, and ran the bundled full-profile verifier successfully.
- Rebuilt public/private PDFs at 14 physical pages on Letter; technical content
  ends on page 12 and pages 13--14 are references. Both 14-page contact sheets
  were visually inspected after table/figure/layout repairs.
- Preserved the remaining scientific blocker: no v2 real-online model-selector
  increment has been measured.
- Added a real OpenAI-compatible v2 proposal-ID selector and a grant/SHA-bound
  online matrix runner. Malformed responses fail closed to exact H0, raw
  provider envelopes are retained without credentials, and held-out execution
  requires a matching development gate. The expanded no-NPU suite passes 82
  tests; no service or hardware was touched.

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Submission-readiness gates complete. |
| Where am I going? | Final provenance commit and goal closure. |
| What's the goal? | Auditable ASPLOS 2027 submission readiness without evidence overclaiming. |
| What have I learned? | See `findings.md`. |
| What have I done? | See this session log. |
