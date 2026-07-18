# Progress

- 2026-07-18: Target changed from ASPLOS'27 to EuroSys'27 fall; started full
  remediation rather than venue-name substitution.
- 2026-07-18: Re-read paper, benchmark, experiment-readiness, optimization-repo,
  and persistent-planning instructions; captured existing dirty tree and pinned
  submodule state.
- 2026-07-18: Verified the dedicated environment and idle NPU3/port 18383; found
  existing runtime recovery machinery that can support stronger contract-level
  evidence without inventing a new recovery subsystem.
- 2026-07-18: Completed the nine-family ten-seed derived matrix (540 rows),
  27-run runtime contract matrix (all invariants pass), AIOps 2020 public replay
  (P/R/F1 1.0/0.5/0.6667), and nine-family three-seed real-online comparison.
- 2026-07-18: Expanded real-online action validation improves pooled F1 from
  0.7801 to 0.8571 and support recall from 0.7810 to 0.8795 with zero invalid
  action/schema/fallback; stopped the scoped NPU3 service after the run.
- 2026-07-18: Rebuilt an 11-page EuroSys PDF and visually inspected every page;
  47 focused runtime/workload tests pass in `esage-vllm-hust-dev`.
- 2026-07-18: Started publication handoff: recording the clean-tree rerun,
  anonymous artifact freeze, robustness extensions, and credential-rotation
  follow-up in SAGE and the `llm-optimizations` umbrella repository before
  committing and pushing both repositories.
