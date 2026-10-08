# Evidence and assessment

Raw reviews 2012A/2012B are not checked in; rejection diagnosis is based on the repository's response/ledger, not direct review quotations.

## Current state, distinguishing revisions
- /home/shuhao/vamos/docs/planning/atc-early-reject-revision-plan.md: original unclear problem/importance/contribution/evaluation; familiar cap/defer/reject bundle; weak auditability framing; v1 prompt lengths invalid, historical figures diagnostic only.
- /home/shuhao/vamos/paper/main.tex: abstract still centers contract compilation; later Seven-Question section centers verifier-bound short-first cascade. Contribution must be unified. Seven-question method should guide structure rather than appear as a literal paper section.
- Latest authoritative protocol is manifests/experiments/vamos-osdi2027-conditional-gate.json, superseding earlier cascade yaml. It uses 6/14 full-required/concise-sufficient request overlay with minimum output lengths 4/1 and short cap1; semantic_quality_claim=false. It proves structural token-contract enforcement, not useful answer preservation. Later gate has explicit post-start repairs; do not describe them as originally preregistered unchanged protocol.
- tools/run_osdi2027_matrix.py DOES schedule concurrent open-loop arrivals with ThreadPoolExecutor; do not incorrectly generalize the older serial endpoint helper to the authoritative runner.
- tools/run_verified_degradation_endpoint.py: request verifier checks markers/minimum tokens; coverage is candidate successes/count, not verifiable traffic fraction; finalization_count derives from HTTP success; helper false_accepts hardcoded0. Latest validate_osdi2027_run.py recomputes false accepts, so do not claim the complete pipeline blindly trusts hardcoded0. Nonetheless no independent semantic quality ground truth, and exactly-once needs receiver/side-effect fault tests, not HTTP success counters.
- B2 labeled strongest unchanged-objective uses pinned SAGE deferral-only. Baseline strength requires empirical tuning/comparison, not a label.
- Native JITServe/Niyama incompatibility is already recorded (CUDA-specific carriers); acknowledge it, do not claim absent documentation. A matched same-stack cascade baseline remains necessary for the revised idea.
- Causal recovery host M0 is a distinct mechanism; avoid combining it with service-contract optimization into an unfocused paper.

## Recommended thesis
Investigate load- and remaining-deadline-aware verified degradation with explicit fallback capacity budgeting. Show a measurable region where task-correct on-time goodput improves at fixed resources while accounting for verification, second prefill, fallback, rejection, deferral and fairness. This is a proposed hypothesis, not demonstrated novelty or benefit.

## Falsifiable early test
In a simplified fixed-cost model without reuse: expected cascade cost Cs+Cv+(1-p)Cf. Improvement requires p>(Cs+Cv)/Cf; 20% savings require p>=0.2+(Cs+Cv)/Cf. Real tests must use conditional fallback cost/queueing, full workflow wall time and device cost; token counts alone are insufficient.
Separate deployable verifier coverage, conditional pass probability, and independently evaluated correctness. Use real constrained tasks (tool argument correctness/execution, extraction exactness, independently held-out program tests) rather than minimum token counts or markers as semantic utility. Runtime verifier must not see evaluation answers. Structural validity alone is not correctness.

## Baselines and evaluation
Full budget + tuned unchanged-objective control; fixed short cap; ordinary verified cascade with same verifier/fallback; proposed pressure/deadline/fallback-capacity-aware controller. Keep models, prompts, arrival schedule, output contract, capacity, seeds and tuning budgets matched. Open-loop mixed/burst arrivals, full-request time from arrival, all offered requests counted; task-success deadline goodput plus per-class harm, false accepts, fallback frequency/cost, p95/p99, compute and controller overhead. Fault injection for timeout/cancel/retry/late completion/client disconnect and non-idempotent tool calls.
Expand model/hardware matrix after mechanism wins against ordinary cascade on one meaningful task; preserve negative results and stop if no useful region exists. Prioritize causal identification over more provenance paperwork.

## Primary sources checked
- JITServe https://arxiv.org/abs/2504.20068 (SLO-aware scheduling, imprecise lengths/dependencies)
- Niyama https://arxiv.org/abs/2503.22562 (QoS scheduling and graceful overload relegation)
- FrugalGPT https://arxiv.org/abs/2305.05176 (quality/cost LLM cascades)
- SLOs-Serve https://arxiv.org/abs/2504.08784 (multi-stage, multi-SLO serving)
These invalidate broad claims of first overload control/cascade/application SLO. They do not establish that the proposed combined mechanism is novel without deeper algorithm-level comparison.
