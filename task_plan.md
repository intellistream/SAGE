# Task Plan: Semantic MapReduce ASPLOS 2027 Submission Readiness

## Goal
Advance Semantic MapReduce from single-seed mechanism-ready evidence to a strong,
auditable ASPLOS 2027 systems-paper package without overstating controlled or
non-online evidence.

## Completion Rule
Keep this plan active until either (A) every acceptance item below is backed by
reviewable repository assets, or (B) the same root blocker survives at least
three consecutive goal rounds after safe in-scope alternatives are exhausted
and the impossibility evidence is recorded. An audit, TODO list, plan, or first
failure is not completion.

## Current Phase
Complete — all submission-readiness gates below have reviewable assets

## Acceptance Matrix

- [x] Multi-seed hardcase evidence, or three-round evidence of infeasibility.
- [x] Per case/seed: F1, support recall, accepted edits, fallback, invalid
      action/schema, tokens, latency, and failure taxonomy.
- [x] Controlled-workload mechanism evidence is explicitly separated from
      production generality and real-online claims.
- [x] Hybrid-hint strong baseline and negative controls are retained.
- [x] Operator algebra remains centered on MapEvidence / SemanticReduce / Edit /
      Validate / ReportTrace and the bounded one-token action contract.
- [x] Implementation and focused/full tests are reproducible.
- [x] Claim ledger, paper tables/figures, artifact package, and reviewer packet
      agree with manifest-backed evidence.
- [x] Anonymous ASPLOS 11-page counted-content packaging, citations, and final-PDF visual checks pass.
- [x] Artifact gate, reproduction commands, clean provenance, parent/submodule
      pins, dedicated environment, device binding, and evidence labels pass.

## Phases

### Phase 1: Repository and Evidence Recovery
- [x] Confirm `/home/shuhao/SAGE`, parent branch/HEAD, and clean parent worktree.
- [x] Read repository governance and required workflow/provenance skills.
- [x] Inventory submodule dirty state, dedicated environment, NPU3 occupancy,
      existing results/manifests, paper sources, tests, and artifact gates.
- [x] Reconstruct the seven-step research argument and reviewer attack matrix.
- **Status:** completed

### Phase 2: Evidence Schema and Low-Cost Closure Plan
- [x] Establish a machine-checkable per-case/per-seed result schema.
- [x] Select three full-coverage hardcases and workload seeds 7/11/13.
- [x] Verify hybrid-hint baseline, negative controls, invalid-action/schema,
      fallback, token, latency, and failure-taxonomy instrumentation.
- [x] Confirm offline 10-seed hardness, then close the live gap with a minimal
      three-seed controlled real-online matrix.
- **Status:** completed

### Phase 3: Implementation and Controlled Multi-Seed Evidence
- [x] Implement the missing per-case/seed evidence reporter and focused test.
- [x] Run focused unit/integration tests in an allowed existing environment.
- [x] Run controlled multi-seed hardcases and preserve raw + derived provenance.
- [x] Analyze workload-seed variance and failure modes without production or
      stochastic-robustness overclaiming.
- **Status:** completed

### Phase 4: Conditional Real-Online Evaluation
- [x] Pass NPU3 endpoint, fixed-device, dedicated Conda, repo-owned runtime,
      port/model/workload, evidence-label, and fresh-manifest preflight.
- [x] Harden existing-endpoint comparison preflight to fail closed and support
      a no-request preflight-only mode.
- [x] Verify the reserved device is free before and after the run; no occupied-device
      stop or unrelated-process intervention was required.
- [x] Run the manifest-backed minimal three-seed real-online comparison after
      every gate passed, then stop and clean only the managed NPU3 service.
      improve only controlled/replay/derived assets with correct labels.
- **Status:** completed

### Phase 5: Paper, Figures, Artifact, and Reviewer Packet
- [x] Align the seven-step argument, systems novelty, substrate comparison, and
      quality-cost framing with the evidence boundary.
- [x] Regenerate tables/figures from checked-in or manifest-backed inputs.
- [x] Complete claim ledger, artifact instructions, reviewer packet, anonymity,
      citations, 11-page packaging, and visual PDF inspection.
- **Status:** completed

### Phase 6: Submission-Readiness Gate
- [x] Run focused and full applicable tests plus artifact/reproduction gates.
- [x] Audit every numerical and generality claim against evidence provenance.
- [x] Verify repository and submodule provenance without disturbing user work.
- [x] Close every acceptance-matrix item with a path/command/result.
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
