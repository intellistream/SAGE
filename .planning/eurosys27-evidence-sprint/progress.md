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
- 2026-07-18: User confirmed the vLLM-HUST API bearer token is a locally owned
  test key and authorized direct rotation. Resumed the evidence sprint to
  rotate it secret-safely, launch the clean NPU3 endpoint, and run the pending
  real-online stability/budget matrix.
- 2026-07-18: Rotated the local test bearer key atomically without printing,
  hashing, backing up, or placing it in command arguments. Preserved mode 0600
  and wrote only a secret-free ignored attestation. A post-rotation smoke
  returned HTTP 200.
- 2026-07-18: Launched the pinned Qwen2.5-7B endpoint on NPU3 from clean commit
  `000c513`, then completed nine families x seeds 7/11/13 x five samples x
  three reducers at candidate budgets 4/8/12 (1,215 reducer rows). Raw provider
  envelopes, model text, timing, request status, sample IDs, and provenance are
  retained.
- 2026-07-18: Budget 4 was retained with artifact gate FAIL (action F1 0.7791
  versus hybrid 0.7801). Budgets 8 and 12 pass: action F1 0.8645/0.8571,
  zero action-path fallback or schema invalid, and 4/5 rejected actions.
  Budget 8 has zero within-case F1 standard deviation and 0.9926 mean exact
  action agreement.
- 2026-07-18: Stopped the experiment-owned NPU3 service and verified port 18383
  closed. Scanning the new artifacts and all tracked files for the literal key
  found zero matches.
- 2026-07-18: Packaged the budget-8 full-coverage run plus the three-budget
  curve into an anonymous archive. The full five-sample verifier passes; archive
  SHA-256 is `8587d935f204fd44057a63631b93b2b5c064d0287a74cbe0ab06d0e97a8b82bd`.
- 2026-07-18: Rebuilt the updated anonymous ACM paper. It remains 11 letter-size
  pages; all pages were rendered and visually inspected, fonts are embedded,
  and identity/replacement-glyph searches are clean. PDF SHA-256 is
  `e6c285540cf916a579f2da73b8659fade44d471efe05eec0982fb32e1dfecd75`.
- 2026-07-18: Final focused no-NPU regression passes under the dedicated env:
  `55 passed` with six pre-existing deprecation warnings.
- 2026-07-18: Checked the live official EuroSys 2027 CFP. The 11-page letter
  paper, page numbering, anonymous form, grayscale-readable figures, separate
  supplement, and AI-tool disclosure match public requirements. Final author
  list, conflicts, per-author limit, ORCIDs, and HotCRP metadata remain
  author-owned upload checks rather than repository work.
