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
- 2026-07-18: Published the paper/evidence freeze as SAGE commit `14a2a13` on
  `feature/semantic-mapreduce-paper`. Updated only the dedicated Semantic-MR
  handoff in the dirty umbrella checkout, preserved all unrelated changes, and
  pushed llm-optimizations commit `ecb36c3` to `main`.
- 2026-07-18: Reopened the sprint after the EuroSys double-blind review found a
  searchable provenance leak in the nominally anonymous archive. Confirmed the
  parent and pinned submodules remain clean at pushed commit `7405807`; began a
  publication-only anonymization repair while preserving raw online evidence.
- 2026-07-19: Implemented dual raw/publication provenance verification and a
  reverse-identity audit for Git revisions, branch names, remotes, repository
  names, runtime labels, paths, and environment/key identifiers. Generated and
  independently extracted a 429-file opaque-provenance archive; full five-sample
  artifact gate passes. The final generic-name review archive, regenerated
  after path-level and unique-prefix checks, has SHA-256
  `c92cb17f5e43a3a5b3699a736fc5bb410af9ffaf397d0773f63b2e41be4705d5`;
  an independent extraction scan reports zero public system/repository names,
  Git revisions/branches/remotes, local paths, or environment/key identifiers.
- 2026-07-19: Added an untracked private-title PDF staging path so the public
  technical-report title and submission title do not coincide in Git history.
  The 11-page private review PDF has embedded fonts, passed text identity scans
  and visual checks of the title, provenance table, online tables, and final
  pages; the private system alias is also absent from Git history, and the final
  private PDF SHA-256 is
  `6924163cd3fefada557e4ec12234df1b603fc6be7a95623e1344600b25e7049f`.
- 2026-07-19: Rebuilt the tracked public-title technical-report PDF separately
  (11 letter-size pages) and ran the broadened no-NPU regression selection:
  `68 passed`, with six pre-existing runtime-client deprecation warnings.
- 2026-07-19: Found that full `docker top ... args` diagnostics could retain the
  test API token. Stopped the endpoint, revoked and rotated the token without
  printing the replacement, sanitized and invalidated the affected preflight,
  changed diagnostics to non-secret `comm`, and pushed security fix `11e4ec4`.
- 2026-07-19: Launched a clean 14B same-family endpoint from `11e4ec4`; strict
  JSON-Schema smoke passed. Completed nine families x three seeds x three
  samples x three reducers (243 raw reports). Action F1 is 0.8392 versus 0.7801
  hybrid, with two rejected actions, zero schema invalid/fallback, and zero
  unsafe credential files. After freezing the derived summaries, the
  reproducible full-directory digest is
  `825858b062a73b1d24b7998d2750f12b2ce31ed959c576077f82c34aba7d1990`.
- 2026-07-19: Added 27-unit paired bootstrap and call-conditioned cost analysis.
  The 7B/14B paired deltas versus hybrid are +0.0844
  [0.0328,0.1449] and +0.0591 [0.0147,0.1149]. Model-call rate is 48.15%;
  conditional median latency is 160.0/276.2 ms with complete provider-token
  coverage on called action rows.
- 2026-07-19: Added an AIOpsArena reducer-only replay. Twenty-three public
  injection rows define eight native episodes; map-only/window/service-local/
  semantic F1 is 0.5161/0.8000/1.0000/1.0000. Evidence is `replay` and
  explicitly label-conditioned, not end-to-end detection. Focused regression
  selection passes: 49 tests.
- 2026-07-19: From clean pushed commit `d5ba73d`, regenerated the nine-family x
  three-seed model-free runtime-contract matrix. All 27 rows pass commit,
  invalid-edit rejection, baseline preservation, checkpoint restore, and
  deterministic replay; its reproducible directory digest is
  `7330905cb605a32b63e0b01acec0305c3e6b8b0407a29c240cc51eff4161d060`.
- 2026-07-19: Froze the final 693-file anonymous review archive with the primary
  five-sample real-online matrix, 243 raw same-family 14B reports, external
  label-conditioned reducer replay, and runtime-contract matrix. Full-profile
  verification passes; independent extraction finds zero identity/repository,
  email, exact Git revision, or private-IP markers. Archive SHA-256 is
  `f590fde5a371c2d663ebeddd9b609fe4d6ea74a5f36c794e9fd3fbad2d73d4a0`.
- 2026-07-19: Rebuilt the final private-title and public-title PDFs. Both are 12
  letter-size pages with embedded fonts. The private PDF has zero identity,
  email, or replacement-glyph matches and SHA-256
  `d6ec9658b82481e771c9b0af0459278566c60c0b09d32299f74dcdcb47794fbf`;
  the public technical-report PDF SHA-256 is
  `570d8dc37f524f36eda187a62b9ce37cc9b371f8e6c754ac24050e3fe8529c11`.
- 2026-07-19: Added and ran a fail-closed submission-claim verifier. It passes
  the two-scale F1/paired-CI/call-conditioned-cost checks, external replay
  scope, 27-row runtime matrix, archive checksum, and paper claim literals.
  The final relevant regression selection remains `49 passed`.
