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
  `269e28bfa363d3de4dfc51e78c4a09b407a5a69662c1bc9c733c79e139db9232`;
  technical content ends on page 11. The ignored private-title review PDF is
  also 12 pages, SHA-256
  `e40160980d3fcc9a901cf488de87365f79e89e9e3b24553cd272026de8e667c7`.
  Both have embedded fonts and zero identity/email/path/replacement-glyph hits.
- The frozen evidence archive remains unchanged at SHA-256
  `f590fde5a371c2d663ebeddd9b609fe4d6ea74a5f36c794e9fd3fbad2d73d4a0`;
  the submission-claim verifier passes every numeric and scope check, and the
  focused no-NPU regression selection passes 49/49 tests.
