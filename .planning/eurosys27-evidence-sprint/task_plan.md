# EuroSys'27 Semantic-MR Evidence Sprint

## Goal
Raise the Semantic MapReduce submission's acceptance probability with evidence,
not packaging alone: preserve the bounded operator/runtime-contract claim,
measure repeated-sampling and quality/cost stability, test the external-validity
boundary honestly, and prepare a clean, secret-safe submission freeze.

## Seven-Step Research Logic
1. Problem: unconstrained model outputs can mutate distributed analysis state
   without eligibility, validation, recovery, or replay guarantees.
2. Importance: model-backed operators increasingly enter data/runtime paths;
   syntactic structured output alone does not protect state integrity.
3. Gap: workflow engines, data systems, and agent runtimes do not jointly own
   evidence IDs, bounded edits, validator-owned commit/fallback, checkpoint
   recovery, and deterministic trace replay.
4. Idea: expose the model only through bounded `Edit`; keep assembly,
   `Validate`, fallback, checkpoint, trace, and replay in the runtime contract.
5. Feasibility: SAGE parent code and pinned runtime submodules already implement
   the required prototype path; no new kernel semantics are required.
6. Evaluation: full nine-family online matrix as the primary quality result;
   repeated sampling and budget/cost sweeps; runtime-contract matrix; external
   replay/label audit; honest negative and unsupported-claim boundaries.
7. Takeaway: model judgments can enter distributed analysis as validated,
   replayable state transitions rather than generated state.

## Phases
- [completed] Audit paper claims, current artifacts, raw-response retention,
  manifests, external labels, endpoint/key/hardware readiness, and baselines.
- [completed] Implement repeated-sampling, budget/cost aggregation, provenance and
  validation harnesses with no-online regression tests.
- [completed] Execute all valid no-credential experiments; run clean real-online
  matrices only if NPU3, controlled endpoint metadata, and rotated credentials
  satisfy preflight.
- [completed] Synchronize paper, readiness, claim ledger, NEXT_STEPS, artifact
  verifier, and PDF based only on completed evidence.
- [completed] Commit and push SAGE; update and push the umbrella handoff only after
  the corresponding SAGE work is real and published.
- [in_progress] Rotate the user-owned local vLLM-HUST bearer key without logging
  it, attest the rotation, launch a clean NPU3 endpoint, and execute the
  full-nine-family repeated-sampling/candidate-budget sweep.
- [pending] Validate and package the resulting real-online evidence, update the
  paper/readiness/claim ledger and umbrella handoff, rebuild/inspect the PDF,
  then commit and push all new tracked work.

## Constraints
- Use `esage-vllm-hust-dev`; never mutate shared `vllm-hust-dev`.
- Preserve user changes; never reset, clean, or overwrite a dirty tree.
- Use only repo-owned pinned submodules; submodule changes require project
  `feature/...` branches and must be pushed before parent pointers.
- Never log or commit API keys; record only the key environment-variable name.
- Label evidence as `real-online`, `existing-server-probe`, `replay`,
  `simulation/model`, `projected-profile`, or `derived-artifact`.
- The nine-family matrix is primary; hardcase-only results are diagnostic.
- Do not infer production, cross-model, or stochastic robustness from one model
  or from replay/derived artifacts.

## Errors Encountered
| Error | Attempt | Resolution |
| --- | ---: | --- |
| Initial `jq` projections assumed object-shaped comparison summary and a nonexistent AIOps `summary.json` | 1 | Inspect actual keys; use the comparison array and AIOps `aggregate.json`/`manifest.json` paths. |
| Combined case-summary/artifact-verifier patch missed current verifier context | 1 | No partial patch applied; split into schema change and small verifier hunks against exact current lines. |
| Broad regression collection could not import `tools` with `PYTHONPATH=src` | 1 | Rerun with the repository root and source tree: `PYTHONPATH=.:src`. |
| Runtime-contract CLI does not accept the shorthand `--scenarios all` | 1 | Reran with the explicit nine-family comma-separated list; clean run passed. |
