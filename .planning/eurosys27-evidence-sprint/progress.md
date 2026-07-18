# Progress

- 2026-07-18: Loaded seven-step paper review, systems-review claim discipline,
  benchmark design, real-experiment readiness, optimization repository, and
  persistent-planning instructions.
- 2026-07-18: Confirmed clean SAGE branch and clean pinned submodules; opened a
  new evidence-sprint plan without altering the completed remediation record.
- 2026-07-18: Audited primary paper/result wording, online manifest fields,
  per-case execution-contract traces, existing artifact inventory, and AIOps
  replay code; identified repeated-sampling/raw-attempt metadata and cost-curve
  aggregation as concrete harness gaps.
- 2026-07-18: Audited action-reducer request path and matrix/summarizer schema;
  selected a backwards-compatible `samples` axis, per-request attempt trace,
  stability aggregation, and external contract-conformance replay as the next
  implementation slice.
- 2026-07-18: Implemented repeated sample IDs/artifacts, per-request response
  traces, temperature/retry metadata, stability and budget aggregators, a
  full-nine-family artifact profile, and AIOps public-data contract replay.
  Focused static checks and 23 tests pass.
- 2026-07-18: Completed online preflight without starting a service: NPU3/model/
  port are ready, but credential rotation is not evidenced, so online runs are
  blocked rather than silently reusing the exposed key.
- 2026-07-18: Corrected stability aggregation to report within-case repeated-
  sampling variance and action agreement rather than cross-workload variance.
  Added provider-usage token accounting with explicit estimate fallback, a
  secret-free key-rotation attestation gate, and a full-profile artifact-gate
  fixture. Static checks and 25 focused tests pass.
- 2026-07-18: Committed and pushed the harness/claim-boundary slice at
  `e0ffdffeef7a059ee3059064eb5c86a25307738a`; the broad relevant regression
  selection passes (`53 passed`, six pre-existing deprecation warnings).
- 2026-07-18: From that clean commit, reran the nine-family x three-seed
  model-free runtime-contract matrix: all 27 rows pass valid commit, invalid
  reference rejection, baseline preservation, checkpoint restore, and
  deterministic replay.
- 2026-07-18: From the same clean commit, ran public AIOps external contract
  conformance over the two replay-detected windows. Valid commit, missing-
  evidence rejection, baseline preservation, and deterministic replay pass;
  this remains `replay`, not reducer-quality evidence.
- 2026-07-18: Synchronized the paper, claim ledger, readiness report, README,
  and freeze checklist with the clean evidence paths and the explicit online
  blocker. Corrected Table 1 and Figure 2 wording so all nine online families,
  rather than only the three diagnostics, are visibly primary.
- 2026-07-18: Rebuilt the anonymous ACM PDF with Tectonic. It remains 11 letter-
  size pages; all 11 rendered pages were visually inspected, fonts are
  embedded, no identity/home/email marker or replacement glyph was found, and
  the PDF SHA-256 is
  `2ff1fe68fcad173274d6decfc9dd0ce09615068caeb8090b37e31eafa84b75b7`.
- 2026-07-18: Pushed the paper/evidence synchronization as SAGE commit
  `fe9c8885ff39d1b11187d21f9a3f4d0b794930ce`. After that publication, updated
  only the clean Semantic-MR handoff file in the dirty umbrella checkout,
  preserving all unrelated user changes, and pushed llm-optimizations commit
  `ac29450` to `main`.
