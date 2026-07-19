# Progress

- 2026-07-19: Started from clean pushed SAGE commit `03bad6e`; all submodules
  are pinned and clean. Loaded seven-step, systems-paper, claim-discipline,
  paper/PDF readiness, planning, and optimization-repository workflows.
- 2026-07-19: Confirmed the current public PDF is 12 letter-size pages and
  references begin on page 11, leaving about one safe page for technical prose.
- 2026-07-19: Reframed the problem statement around eligibility, transition
  integrity, and recovery/audit rather than a generic orchestration challenge
  list. Added an explicit runtime-ownership explanation and concrete invocation, validation,
  commit, checkpoint, and replay lifecycle, with an explicit non-claim for
  distributed exactly-once execution. Updated the introduction for the
  same-family second scale and both external replay boundaries.
- 2026-07-19: Visually inspected the first strengthened 12-page build. Technical
  content ends on page 11 and references occupy page 12; all pages are readable
  with no clipping or overlap. Tightened the model-free checkpoint versus
  real-online trace boundary and replaced residual generic "orchestration
  layer" language with the runtime-owned reducer boundary.
- 2026-07-19: Rebuilt and visually checked final public/private 12-page PDFs;
  both pass letter-size, embedded-font, anonymity, replacement-glyph, and
  layout gates. Updated readiness, checklist, README, claim ledger, and reviewer
  packet. Frozen-evidence claim verification passes, and 49 focused regression
  tests pass without rerunning or modifying online evidence.
- 2026-07-19: Final pre-commit audit passes `git diff --check`, secret-pattern
  scan, frozen archive checksum, all paper numeric/scope literals, and public/
  private PDF hashes. Ready to commit, push, and synchronize the umbrella
  handoff without touching unrelated umbrella changes.
- 2026-07-19: Reopened the visual/structure gate after reviewer-style feedback.
  Replaced the abstract boundary figure with the concrete reducer invocation,
  validation, rejection, trace, and recovery path; removed three obsolete
  bitmap assets and four low-value or redundant tables.
- 2026-07-19: Added a three-panel quality--latency--token figure generated as
  deterministic TikZ by a Python-standard-library script. The generator reads
  frozen budget-4/8/12 summaries and fails on any mismatch with the recorded
  F1, support, latency, or token values; no online evidence was rerun.
- 2026-07-19: Merged the former standalone open-challenges and auditability
  sections into one conventional Discussion and Limitations section, retained
  Related Work as Section 9, and collapsed Conclusion to one paragraph. The
  current 12-page public build is visually clean at both revised figures.
- 2026-07-19: Final public/private PDFs are 12 letter-size pages with all fonts
  embedded and SHA-256 values `51b68c45944283bf2c2b883dce8c690a986e839d5d005e1fe47ad87ca40eda8a`
  and `5d2a46f1a011e87b1575cd391bfc7ef5c4070fb1a38a1d75b91800cb4263ebdf`.
  The submission claim verifier, hardcase artifact gate, independently unpacked
  693-file artifact gate, anonymity scans, and 51 focused tests all pass.
- 2026-07-19: Reopened the evaluation-comparison phase after the Figure 3
  critique. The budget plot is correctly classified as an internal operating-
  point ablation, not a SOTA comparison. New work will add a strong label-free
  non-LLM reducer under the identical generator/evidence/scorer contract and a
  separate main comparison visualization; frozen online evidence remains read-
  only and no NPU run is planned.
- 2026-07-19: Reducer/API audit confirms a fair plug-in point and a fixed common
  scorer. Existing deterministic baselines are mostly fixed-rule grouping; the
  planned stronger peer is label-free constrained agglomerative evidence
  clustering. `source_incident_id` is forbidden input for its decisions and
  will receive an invariance regression test.
- 2026-07-19: Implemented the constrained-agglomerative reducer and two leakage/
  contract tests; the semantic-merge test file passes 22/22. A dirty exploratory
  540-row matrix completed successfully. No threshold was changed after viewing
  results; the next valid paper artifact will be rerun from a clean committed
  implementation.
- 2026-07-19: Profiled the exploratory 540-row output. The new baseline reaches
  0.9287 mean F1 over nine families x ten seeds, materially above hybrid 0.7796,
  with non-perfect ordinary-family results. Chose a point/delta comparison over
  a mean-only bar so per-unit variation remains visible. The matrix is
  `simulation/model`; only its regenerated visualization is `derived-artifact`.
