# Findings

- EuroSys'27 fall full-paper deadline is 2026-09-24 AoE; the official scope
  explicitly includes AI/ML systems, language/runtime support, and database/data
  analytics frameworks.
- Current strongest real-online evidence is three hardcases x seeds 7/11/13 on
  one model/endpoint: action-validated F1 0.9301 vs hybrid 0.7204, with zero
  invalid action/schema/fallback.
- Current paper already foregrounds typed evidence, bounded Edit, system-owned
  Validate, fallback, and replayable trace, but runtime enforcement evidence and
  workload external validity remain weaker than the abstraction claim.
- Current working tree includes the prior ASPLOS reframing edits; they are user-
  directed work and must be preserved while migrating to EuroSys.
- The dedicated `esage-vllm-hust-dev` Conda environment exists. All eight 910B2
  NPUs are healthy and idle at audit time; TCP port 18383 is not listening.
- The runtime already implements best-effort, restart, and checkpoint-restore
  policies, recovery summaries, state-query audit, and checkpoint fault-
  tolerance tests. The missing piece is a Semantic MapReduce-specific benchmark
  that ties these mechanisms to bounded Edit/Validate/fallback/replay claims.
- The source probe identifies AIOps Challenge 2020, LO2, OpenTelemetry Demo,
  and DeathStarBench as plausible external substrates. The existing probe is
  only source/readiness evidence; it is not an external-workload result.
- AIOps Challenge 2020 supports selective ZIP range extraction. The completed
  May-29 replay reads official metrics and labels without archiving raw rows;
  two of four labeled windows are evidence-positive and eight matched negative
  windows produce no false positives. The two misses remain an explicit map-
  coverage limitation.
- Across all nine controlled families and seeds 7/11/13, the live bounded-action
  path improves pooled F1 0.7801 -> 0.8571 and support recall 0.7810 -> 0.8795,
  with zero invalid actions, invalid schemas, or fallbacks. Free-form validated
  pairwise decisions are valid in this structured-output run but are slower and
  less accurate, so old schema-failure behavior must not be generalized.
- The final submission freeze still requires a clean-tree repetition of the
  nine-family real-online matrix, regeneration of the anonymous artifact from
  that commit, an anonymization audit, and cross-checking the frozen PDF against
  the packaged manifests. Cross-model and repeated-sampling runs are evidence
  upgrades, not blockers for the bounded-contract claim.
- The umbrella repository is `/home/shuhao/llm-optimizations`; its venue label,
  taxonomy validator, priority notes, and a dedicated SAGE handoff must all point
  to EuroSys'27 rather than retaining the superseded ASPLOS'27 classification.
- Published coordination state: SAGE paper/implementation commit `e342fda` is
  on `origin/feature/semantic-mapreduce-paper`; umbrella handoff commit
  `81e33b1` is on `origin/main`.
