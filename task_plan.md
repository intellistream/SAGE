# Task Plan: Semantic MapReduce EuroSys'27 Submission Readiness

## Goal
Make the bounded semantic-reduce operator/runtime contract mechanism-complete,
fairly comparable, and auditable: true SPLIT plus MERGE/KEEP/ABSTAIN over a
finite system-generated proposal catalog; unified H0/fallback/digests; atomic
validation, commit, checkpoint, and replay; shared-catalog deterministic/model
selection; difficult held-out controlled workloads; and a clean reproducible
`simulation/model` matrix, and a three-reviewer-signed, fail-closed reservation
protocol for the still-unexecuted v2 real-online selector experiment.

## Completion Rule
Keep this plan active until either (A) every acceptance item below is backed by
reviewable repository assets, or (B) the same root blocker survives at least
three consecutive goal rounds after safe in-scope alternatives are exhausted
and the impossibility evidence is recorded. An audit, TODO list, plan, or first
failure is not completion.

## Current Phase
Cross-submission audit Phase X4 — request-only reservation handoff

### Phase X4: Frozen Real-Online Reservation Protocol
- [x] Freeze Qwen2.5-7B/NPU3 TP1 service identity, 80-row development and
      200-row held-out matrices, paired endpoint and clustered CI, stopping,
      cleanup/release, canonical raw roots, and non-substitution rules.
- [x] Close request-envelope digest/identity/time, split-specific namespace,
      and complete anonymous-artifact fail-closed gaps with regression tests.
- [x] Obtain fresh SIGN envelopes from systems/novelty,
      experiments/statistics/provenance, and artifact/fail-closed reviewers on
      protocol SHA `33b48e86...a6ba83d` and execution commit `fc0978d`.
- [ ] Emit the request-only reservation JSON after final clean commit/upstream
      equality and read-only queue-base revalidation; do not reserve hardware,
      edit the queue, or start a service.
- **Status:** in progress

## EuroSys'27 Cross-Submission Audit (2026-07-19)

### Phase X1: Independent Read-Only Review and Provenance
- [x] Delegate three independent read-only reviewers for systems claims,
      experiments/statistics, and artifact/anonymity/fail-closed behavior.
- [x] Verify local HEAD/clean/upstream, all submodule pins/branches, public and
      private PDFs with 12 technical pages, artifact, verifier, and handoff.
- [x] Map the paper through the seven-step research framework before editing.
- **Status:** completed

### Phase X2: Evidence Adjudication and Remediation
- [x] Record reviewer agreements and conflicts with exact evidence; resolve
      disagreements by inspected source, raw reports, manifests, and PDF pages.
- [x] Repair every substantiated submission blocker without weakening or hiding
      negative evidence.
- **Status:** completed

### Phase X3: Full Safe Validation and Publication State
- [x] Run the claim verifier, independent artifact unpack/verification,
      anonymity scan, TeX/PDF builds, page/format checks, and page-by-page visual
      inspection; the complete applicable test suite remains the final gate.
- [x] Commit only the audited parent-repository paths, push the current branch,
      and verify local HEAD equals upstream with a clean worktree.
- **Status:** completed

## Acceptance Matrix

- [x] SPLIT is a real, validated state transition; MERGE/KEEP/ABSTAIN and trace
      outcomes exactly match executable behavior.
- [x] H0 reducer, fallback, candidate-state digest, catalog digest, H1 digest,
      checkpoint, and independent replay semantics are unified and tested.
- [x] Evidence conservation, unique ownership, conflict detection, and atomic
      rollback pass adversarial and permutation/renaming invariance tests.
- [x] Deterministic and mock policy selectors receive the identical H0 and proposal
      catalog; constrained full-evidence remains a clearly privileged reference.
- [x] Proposal-oracle coverage, merge/split recall, truncation, selector quality,
      validation outcomes, and edit/no-edit conditioned deltas are quantified.
- [x] Held-out controlled axes reduce score/hint label-proxy separability and
      freeze development/test seeds, parameters, and success criteria in advance.
- [x] A clean-commit `simulation/model` matrix and `derived-artifact` outputs are
      reproducible from a complete manifest in `esage-vllm-hust-dev`.
- [x] Frozen historical online artifacts are byte-preserved and described only
      as the old merge-only implementation; no new online run is performed.
- [x] Paper/readiness/ledger/reviewer/README/NEXT_STEPS/planning claims agree,
      parent branch is clean and pushed, and umbrella handoff is factual.

## Phases

### Phase 1: Provenance and Design Audit
- [x] Confirm parent branch/HEAD/remote, dirty paths, pushed implementation
      commit, submodule pins, and existence of frozen/clean artifacts.
- [x] Audit all submodule branches/dirty state and preserve the known draft
      paths as user work.
- [x] Map current reducer/action/trace/harness/workload/test code and record the
      executable H0→catalog→select→validate→commit→trace contract.
- **Status:** completed

### Phase 2: Typed Catalog, True SPLIT, and Atomic Runtime
- [x] Implement deterministic bounded MERGE and three oracle-free SPLIT proposal
      generators with stable ordering, budgets, provenance, and byte-equivalence.
- [x] Implement typed proposal-ID edits, real SPLIT, evidence/root/affected/schema
      validation, conflict checks, atomic rollback, unified H0/fallback/digests,
      checkpoint, trace, and deterministic replay.
- [x] Add adversarial unit/property/runtime tests before producing new results.
- **Status:** completed

### Phase 3: Fair Harness and Held-Out Workloads
- [x] Implement shared-H0/shared-catalog H0, oracle, deterministic, mock policy, and
      constrained-reference evaluation layers with permission labels.
- [x] Add proposal coverage and per-scenario×seed failure/accounting outputs.
- [x] Freeze and implement development/held-out ambiguity axes and separability
      diagnostics without reducer access to `source_incident_id`.
- **Status:** completed

### Phase 4: Clean Offline Evidence
- [x] Commit and push clean implementation/test/workload slices with explicit
      staging, diff checks, secret scan, and remote verification.
- [x] From a clean commit, run a new non-overwriting full offline matrix and
      generate manifest-backed `simulation/model` plus `derived-artifact` data.
- [x] Analyze negative cases and online-readiness gates; write a runbook only if
      every offline gate passes, without using NPU.
- **Status:** completed

### Phase 5: Claims, Figures, and Handoff
- [x] Audit/preserve/revise the existing Figure 3 draft paths against new
      evidence; do not freeze them prematurely.
- [x] Correct paper and readiness/claim/reviewer/README/NEXT_STEPS/planning docs,
      including historical merge-only H0 and matched-statistic distinctions.
- [x] Push final parent state, verify clean/local=remote, and update the umbrella
      handoff with exact commit, pins, evidence path/label, blocker, and command.
- **Status:** completed

## Decisions Made

| Decision | Rationale |
|---|---|
| Prefer offline/controlled multi-seed hardcase closure first | Lowest-cost evidence directly targets the single-seed reviewer attack. |
| Treat real-online as conditional on every preflight gate | Prevents device interference and invalid serving claims. |
| Never promote replay/probe/derived artifacts to online measurements | Required claim discipline. |
| Preserve operator algebra and bounded one-token action contract | User-defined research core and novelty boundary. |
| Join raw reports into a per-case/seed submission table before new runs | All requested fields already exist; deterministic aggregation is cheaper and auditable. |
| Require canonical endpoint metadata for existing-server comparisons | Health alone cannot prove NPU3 binding, model identity, or repo-owned provenance. |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Broad `find ..` governance scan hit permission-denied paths in sibling projects | 1 | Restricted search to the SAGE checkout with `rg --hidden --files`; found root and relevant submodule instructions. |
| `conda env list` failed because bare `conda` is absent from non-interactive PATH | 1 | Use the absolute Miniconda executable or the dedicated environment interpreter. |
| `npu-smi info -i 3` used an unsupported local CLI form | 1 | Retry with the usage-advertised `info -t usages -i 3` and process query; do not repeat the same form. |
| Direct dedicated-Python run left `conda_env` empty in offline manifest | 1 | Update manifest generation to infer the project environment from `sys.prefix`; keep this dirty diagnostic out of paper evidence. |
| Ruff reported import ordering and formatting differences | 1 | Applied Ruff's mechanical fixes; checks and 20 focused tests pass. |
| Endpoint launch created an untracked root-owned zero-byte runtime lock in dev-hub | 1 | Verified no process held it and moved it into the endpoint artifact; clean preflight then passed. |
| Managed systemd stop left the launched VLLM engine child on NPU3 | 1 | Used the repo-owned cleanup script with the exact isolated container/port; NPU3 and 18383 are free. |
| One polling wrapper had a JavaScript parse error | 1 | Switched to a simpler `write_stdin` poll; benchmark session was unaffected. |
| ImageMagick `montage` was unavailable for a PDF contact sheet | 1 | Used direct per-page rendering and visual inspection instead. |
| Two broad documentation `apply_patch` attempts missed changed context | 2 | Split them into narrow, context-accurate patches; no existing work was overwritten. |
| New packaging script had one unused import | 1 | Removed it; Ruff and the complete focused suite pass. |
| Initial bounded-edit v2 focused suite: two malicious split fixtures triggered duplicate checks before their intended reason, and the first merge proposal rolled back validation | 1 | Corrected fixture precedence; preserved existing schema semantics where root and affected are separate evidence-eligible fields. Rerun: 12 passed. |
| Held-out hint-error test realized only 12.5% errors from a 50% Bernoulli setting on a small unit | 1 | Replace Bernoulli corruption with stable hash-ranked exact-count selection so configured and realized rates agree. |
| First focused Ruff pass found modern-import placement plus three unused imports | 1 | Apply narrow import cleanup and rerun Ruff with tests. |
| Generator-specific test expected a temporal SPLIT in a workload whose H0 had already separated the gap | 1 | Use a single-candidate overmerge fixture to test the temporal generator precondition; retain workload-level no-proposal behavior as evidence. |
| Development smoke failed score-proxy gate (0.9404) and two-edit oracle scored below longer deterministic selections | 1 | Cross frozen score overlap into all families; make oracle an upper envelope including both shared-catalog policy selections before held-out runs. |
| Figure 3 draft script Ruff check found `Any` import placement | 1 | Move `Any` to `collections.abc`, rerun Ruff/test/regeneration. |
| First secret-scan shell expression had mismatched quoting around a quote-class regex | 1 | Replace with multiple simple `rg -e` patterns; do not repeat the fragile compound quoting. |
