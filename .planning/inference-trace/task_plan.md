# SAGE inference trace
- [complete] Map collection points and existing telemetry; obtain and verify bounded Qwen review; align TraceLoom contract.
- [complete] Implement default no-op tracing, bounded asynchronous export, privacy/retention, timeline/observed-dependency-path view and instrumentation.
- [complete] Tests and documentation complete; commit 1267a4e and draft PR https://github.com/RIDE-Lab/SAGE/pull/1532 published with reproduced baseline failure disclosed.

Workspace /home/shuhao/SAGE-trace, branch codex/inference-trace, base dd8658b. Original /home/shuhao/SAGE compiler/cache edits are untouched and excluded.
Scope: observable execution events only, no hidden reasoning, no raw prompt/output persistence by default, no credentials. No NPU or deployment.

## Acceptance remediation (requested 2026-09-09)
- [complete] Exact PR/CI inventory and same-environment clean main/candidate baseline comparison.
- [complete] Reproducible real minimal workflow artifacts, error/cancel/retry/drop/unavailable exporter and privacy gates.
- [complete] Actual TraceLoom PR 63 importer E2E, shared artifact hash, disorder/incompleteness/clocks/idempotence. Independent peer confirmation pending.
- [complete] Three-mode 10k-span benchmark and bounded Qwen adversarial review complete; all four findings independently checked and documented.
- [complete] Fixes and evidence committed/pushed as 47a6ed0; same draft PR updated and exact body verified. All four new-head checks pass, including both required CI jobs. Draft preserved for joint review.
