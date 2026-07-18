# ASPLOS'27 Contract Reframing Plan

## Goal
Reframe the Semantic MapReduce paper's first two pages around an OS/PL-style
operator/runtime contract, keep claims aligned with the current real-online
evidence, and define the workload-coverage expansion needed for submission.

## Phases
- [complete] Audit the abstract, first two pages, contribution framing, and operator figure against the seven-step research logic.
- [complete] Revise the paper so operator algebra, bounded Edit/Validate, runtime integration, and auditable execution are the causal spine.
- [complete] Add a defensible workload taxonomy/coverage plan without overstating the current nine-row hardcase matrix.
- [complete] Rebuild the PDF, inspect pages 1-2 and affected figures, and synchronize readiness documentation.

## Constraints
- Preserve `real-online` provenance and one-model/one-endpoint evidence boundary.
- Do not claim production-trace, cross-model, or stochastic robustness.
- Do not run additional NPU experiments unless the expanded workload claim requires them.
- Preserve unrelated user changes and submodule state.

## Errors Encountered
| Error | Attempt | Resolution |
| --- | --- | --- |
| Planning-file read used a path relative to the paper subdirectory | 1 | Re-run planning checks from repository root or use an absolute path. |
| Workload coverage table exceeded text width by 42 pt | 1 | Replaced natural-width columns with fixed proportional paragraph columns. |
| Final render command was rejected because it included `rm -f` for temporary contact-sheet inputs | 1 | Use a fresh filename prefix and leave temporary render files intact. |
