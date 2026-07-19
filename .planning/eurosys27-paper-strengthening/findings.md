# Findings

- Initial PDF has 12 total pages, with references beginning on page 11; the
  safe revision budget is roughly one page of technical content.
- The paper already leads with the operator algebra, but the runtime integration
  section is short relative to the evaluation and leaves a reviewer to infer
  where admission, atomic commit, checkpoint state, and replay live.
- The strongest use of added space is a compact execution-contract table plus
  concrete runtime lifecycle/integration prose, not another result table.
- Implementation audit confirms that the model supplies only enum decisions;
  the reducer constructs edits from candidate/evidence IDs, maps malformed enum
  text to abstention, validates coverage/schema/root/affected-service fields,
  and emits candidate/evidence/committed-state digests plus a replay ID.
- Checkpoint/recovery evidence is deliberately model-free: a runtime-owned
  `ReductionStateService` initializes the baseline, commits only validated
  hypotheses, snapshots hypotheses+trace, restores through the shared-state
  registry, and checks digest equality. This supports logical reducer-state
  recovery, not distributed exactly-once semantics.
- High-impact prose changes should replace the generic six-challenge problem
  list and "orchestration is the right layer" language with three precise
  obligations: evidence eligibility, bounded transition/commit, and recovery/
  audit. This both saves space and reduces the prompt/workflow-paper reading.
- The first strengthened build moves all references to page 12, so technical
  content ends on page 11 and remains within the 12-page EuroSys allowance.
  Pages 1--12 were rendered; pages 1--11 show no clipping, overlap, illegible
  table text, or broken figure alignment, and page 12 contains only references.
- The evaluation-dense pages 6--10 remain readable: the architecture figure
  and Tables 2--12 fit their columns, captions identify evidence tiers, and the
  online table is visually separated from the external and runtime-contract
  results. Final wording changes still require a fresh full render.
- A final claim audit found one potentially misleading seam: checkpointable
  state is directly exercised by the model-free fault matrix, whereas the live
  online path archives compatible digests and outcomes. The paper now states
  that distinction explicitly instead of implying live checkpoint recovery.
- The final public PDF is 12 letter-size pages, SHA-256
  `51b68c45944283bf2c2b883dce8c690a986e839d5d005e1fe47ad87ca40eda8a`;
  technical content ends on page 11. The ignored private-title review PDF is
  also 12 pages, SHA-256
  `5d2a46f1a011e87b1575cd391bfc7ef5c4070fb1a38a1d75b91800cb4263ebdf`.
  Both have embedded fonts and zero identity/email/path/replacement-glyph hits.
- The frozen evidence archive remains unchanged at SHA-256
  `f590fde5a371c2d663ebeddd9b609fe4d6ea74a5f36c794e9fd3fbad2d73d4a0`;
  the submission-claim verifier passes every numeric and scope check, and the
  focused no-NPU regression selection passes 51/51 tests.

## Visual and structural remediation (2026-07-19)

- The old Figure 2 described components but did not expose authority or state
  transitions. The replacement follows one invocation from typed evidence to
  validated commit, with separate reject, checkpoint/recover, and ReportTrace
  paths; only the enum proposal crosses the model boundary.
- The paper had too many tables and no experimental plot. Four low-value or
  redundant tables were removed; the remaining seven carry comparison matrices
  or contract evidence. Figure 3 now exposes the measured budget-4/8/12 quality,
  mean/p95 reducer latency, and mean/p95 tokens without implying a general
  frontier.
- A standard-library generator emits deterministic TikZ and asserts every
  plotted submission value against frozen summaries. This avoids adding an
  unpinned plotting dependency and makes the figure fail closed on drift.
- Combining scope/challenges with trust/auditability yields one conventional
  Discussion and Limitations section. Related Work remains distinct, and the
  conclusion is a single paragraph.

## Strong-baseline extension (2026-07-19)

- Figure 3 currently answers only a candidate-budget quality/cost question. It
  is an ablation with a hybrid guide line and cannot support an external-SOTA
  claim.
- The fair comparison regime is same workload, evidence objects, candidate
  groups, scorer, and output schema. Spark/Flink/Ray and agent/workflow systems
  are substrates, not reducer algorithms, so an F1 head-to-head would be a task
  mismatch.
- The missing evidence is a strong label-free algorithmic reducer beyond simple
  windows/service-local rules. It must consume no injected labels and should be
  evaluated across all nine obligation families and seeds, including negative
  and partial-evidence cases.
- The reducer interface accepts only `list[EvidenceObject]` and returns the
  common hypothesis schema. Existing baselines are map-only, service-local,
  fixed 40-minute windows, a hand-coded semantic graph, and the same graph with
  upstream-root hints. The matrix runner already fixes scenarios, seeds,
  generator, scorer, and manifest shape, so a new reducer can enter without
  changing ground truth or scoring.
- `EvidenceObject` includes `source_incident_id` solely for scorer/diagnostic
  provenance. The new baseline must explicitly ignore it; tests should verify
  invariance when this hidden field is removed or permuted.
- The strongest honest comparison is therefore an algorithmic reducer such as
  constrained agglomerative evidence clustering, not a Spark/Ray/workflow row.
  It can use observable service dependencies, region, temporal overlap,
  signals, scores, and upstream hints, but no incident IDs or labels.
- The three ambiguity generators make the needed algorithmic capability
  explicit without requiring labels: conflicting hints separate coincident
  incidents, a shared hint reconnects dependency-disconnected fragments, and a
  shared hint bridges temporally separated bursts. A constrained clustering
  baseline can therefore be described by observable pair/cluster rules rather
  than scenario-name branches.
- The implementation will use no scenario field and no scorer callback. If it
  performs extremely well, the paper must acknowledge that these controlled
  workloads admit a strong deterministic solution; the operator-contract claim
  then rests on common validation/audit semantics, not LLM superiority.
- The first exploratory matrix completed all 9 families x 10 seeds x 6
  reducers. The new baseline is deliberately not being weakened after seeing
  results: it solves the three ambiguity mechanisms consistently in the visible
  output and has some ordinary-family misses (for example shared-bottleneck and
  several single-service seeds). This is a credible strong peer rather than a
  perfect oracle, and its exact aggregate will be read from the generated
  summary before the clean rerun.
- Exact exploratory aggregate: constrained-agglomerative reaches P/R/F1
  0.9269/0.9361/0.9287 and support recall 0.9031 over 90 units, versus hybrid
  0.7585/0.8556/0.7796. Per-family F1 is 1.0 on all three ambiguity families
  and ranges from 0.8278 to 0.9746 elsewhere. This is stronger than expected and
  must be presented as evidence that structured hints admit a strong
  deterministic policy, not suppressed to protect the LLM result.
- Data profiling confirms 10 units per reducer/family group, F1 range [0,1],
  and strong within-group variation. A bare mean bar would hide this. The main
  comparison should expose the 27 matched scenario/seed units used by the
  online result (individual points or paired deltas), while the 90-unit derived
  matrix establishes broader deterministic coverage separately.
- Evidence labels must remain exact: the controlled generated matrix is
  `simulation/model`; a figure or CSV computed from it is `derived-artifact`;
  the action rows remain `real-online`. Combining them in one panel requires
  explicit provenance styling/caption language, not a homogeneous "measured"
  claim.
