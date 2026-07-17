# Progress Log: Semantic MapReduce ASPLOS 2027

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

## 5-Question Reboot Check

| Question | Answer |
|---|---|
| Where am I? | Submission-readiness gates complete. |
| Where am I going? | Final provenance commit and goal closure. |
| What's the goal? | Auditable ASPLOS 2027 submission readiness without evidence overclaiming. |
| What have I learned? | See `findings.md`. |
| What have I done? | See this session log. |
