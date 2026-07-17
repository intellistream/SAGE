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
Phase 1 — Repository and evidence recovery

## Acceptance Matrix

- [ ] Multi-seed hardcase evidence, or three-round evidence of infeasibility.
- [ ] Per case/seed: F1, support recall, accepted edits, fallback, invalid
      action/schema, tokens, latency, and failure taxonomy.
- [ ] Controlled-workload mechanism evidence is explicitly separated from
      production generality and real-online claims.
- [ ] Hybrid-hint strong baseline and negative controls are retained.
- [ ] Operator algebra remains centered on MapEvidence / SemanticReduce / Edit /
      Validate / ReportTrace and the bounded one-token action contract.
- [ ] Implementation and focused/full tests are reproducible.
- [ ] Claim ledger, paper tables/figures, artifact package, and reviewer packet
      agree with manifest-backed evidence.
- [ ] Anonymous 11-page paper packaging, citations, and final-PDF visual checks pass.
- [ ] Artifact gate, reproduction commands, clean provenance, parent/submodule
      pins, dedicated environment, device binding, and evidence labels pass.

## Phases

### Phase 1: Repository and Evidence Recovery
- [x] Confirm `/home/shuhao/SAGE`, parent branch/HEAD, and clean parent worktree.
- [x] Read repository governance and required workflow/provenance skills.
- [ ] Inventory submodule dirty state, dedicated environment, NPU3 occupancy,
      existing results/manifests, paper sources, tests, and artifact gates.
- [ ] Reconstruct the seven-step research argument and reviewer attack matrix.
- **Status:** in_progress

### Phase 2: Evidence Schema and Low-Cost Closure Plan
- [x] Establish a machine-checkable per-case/per-seed result schema.
- [ ] Identify the cheapest discriminating hardcases and seed set.
- [x] Verify hybrid-hint baseline, negative controls, invalid-action/schema,
      fallback, token, latency, and failure-taxonomy instrumentation.
- [ ] Decide whether existing offline/controlled execution can close the seed gap.
- **Status:** pending

### Phase 3: Implementation and Controlled Multi-Seed Evidence
- [x] Implement the missing per-case/seed evidence reporter and focused test.
- [ ] Run focused unit/integration tests in an allowed existing environment.
- [ ] Run controlled multi-seed hardcases and preserve raw + derived provenance.
- [ ] Analyze variance and failure modes without robust-frontier overclaiming.
- **Status:** pending

### Phase 4: Conditional Real-Online Evaluation
- [ ] Pass NPU3 endpoint, fixed-device, dedicated Conda, repo-owned runtime,
      port/model/workload, evidence-label, and fresh-manifest preflight.
- [x] Harden existing-endpoint comparison preflight to fail closed and support
      a no-request preflight-only mode.
- [ ] If occupied or any gate fails, stop safely and record BLOCKED evidence.
- [ ] If all gates pass, run manifest-backed real-online comparisons; otherwise
      improve only controlled/replay/derived assets with correct labels.
- **Status:** pending

### Phase 5: Paper, Figures, Artifact, and Reviewer Packet
- [ ] Align the seven-step argument, systems novelty, substrate comparison, and
      quality-cost framing with the evidence boundary.
- [ ] Regenerate tables/figures from checked-in or manifest-backed inputs.
- [ ] Complete claim ledger, artifact instructions, reviewer packet, anonymity,
      citations, 11-page packaging, and visual PDF inspection.
- **Status:** pending

### Phase 6: Submission-Readiness Gate
- [ ] Run focused and full applicable tests plus artifact/reproduction gates.
- [ ] Audit every numerical and generality claim against evidence provenance.
- [ ] Verify repository and submodule provenance without disturbing user work.
- [ ] Close every acceptance-matrix item with a path/command/result.
- **Status:** pending

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
