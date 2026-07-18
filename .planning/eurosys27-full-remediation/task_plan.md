# EuroSys'27 Full Remediation Plan

## Goal
Turn the Semantic MapReduce draft and artifact into a defensible EuroSys'27
systems submission: broaden evaluation beyond controlled hardcases, deepen the
runtime contract and recovery evidence, position against adjacent systems, and
deliver a venue-compliant, visually checked paper with synchronized claims.

## Research Logic
1. Problem: model-backed semantic reduction can mutate distributed analysis state without a typed, recoverable runtime contract.
2. Importance: compound AI/data workflows increasingly span engines and model endpoints, but prompt success does not establish state integrity or auditability.
3. Gap: data engines, AI data operators, and agent runtimes each cover part of the path but do not jointly define evidence eligibility, bounded semantic transitions, validation, fallback, and trace replay.
4. Idea: Semantic MapReduce makes these responsibilities explicit as typed operators with bounded `Edit`, system-owned `Validate`, and recovery to a valid pre-edit state.
5. Feasibility: parent-repo prototype plus pinned serving/runtime submodules; no kernel or scheduler semantic change is required for the current mechanism.
6. Evaluation: controlled nine-family matrices, real-online action admission, external/production-derived workload evidence, runtime recovery/concurrency tests, cost and negative cases.
7. Takeaway: model judgments should enter distributed analysis as validated, replayable state transitions, not as unconstrained generated state.

## Phases
- [completed] Audit EuroSys format, current code/artifacts, runtime boundaries, public workload candidates, and hardware readiness.
- [completed] Implement missing workload/runtime mechanisms and regression tests.
- [completed] Run derived, public-replay, recovery, and real-online experiment matrices with explicit provenance.
- [completed] Reframe and revise the full paper for EuroSys, including related work, evaluation, limitations, and venue metadata.
- [completed] Synchronize README, readiness report, claim ledger, workload docs, and artifact instructions.
- [completed] Build the final PDF, inspect all pages/figures/tables, run tests and artifact verification, and report remaining evidence boundaries.
- [in_progress] Record post-remediation submission gates, synchronize the
  `llm-optimizations` umbrella handoff, and publish all authorized repository
  changes.

## Constraints
- Use `esage-vllm-hust-dev`; never modify the shared `vllm-hust-dev` environment.
- Preserve all existing user and paper changes; stage/commit nothing unless requested.
- Runtime/environment changes belong in pinned project submodules and their mandated feature branches.
- Do not kill or displace unrelated NPU workloads; stop on device or port conflict.
- Label every result as real-online, existing-server-probe, replay, simulation/model, projected-profile, or derived-artifact.
- Do not upgrade controlled or replay evidence into production or cross-model claims.
- Treat the expanded diff-hashed real-online run as valid development evidence,
  but require a clean-tree rerun before the final anonymous submission freeze.

## Errors Encountered
| Error | Attempt | Resolution |
| --- | --- | --- |
| `conda` was not on PATH in the initial login shell | 1 | Locate the project Conda installation explicitly before experiment commands. |
| A broad public-source audit rendered binary ZIP bytes | 1 | Restrict subsequent inspection to known text files and metadata; do not stream downloaded archives. |
| Runtime-contract test initially compared audit annotations as semantic state | 1 | Canonicalize hypothesis digests by excluding `llm_fallback`/validation trace annotations; retain those fields separately in the audit record. |
| First AIOps replay timestamp conversion double-applied UTC+8 | 1 | Use the host's Asia/Shanghai timezone directly; rerun under a new artifact id and retain the failed attempt as diagnostic evidence. |
| First expanded online comparison missed `hashlib` in run-metadata block | 1 | Add the import, regenerate diff-hashed endpoint metadata against the unchanged live endpoint, and rerun under a new artifact id. |
| Initial repository-wide credential heuristic matched ordinary `token`/`secret` variable names in source | 1 | Restrict the publication check to strong credential prefixes and added literal assignments; do not print candidate values. |
| Broad `rm -rf` form for one generated parent-repo `__pycache__` was rejected by command safety | 1 | Resolve the single generated `.pyc` explicitly, then use exact `unlink` and `rmdir`; never stage generated cache files. |
