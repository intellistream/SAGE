# Non-blocking answer advisories

`sage.runtime.answer_advisory.audit_answer` checks source-defined **formula
dependencies**, not semantic truth. It does not generate or return an edited
answer. Applications display the original answer independently and may request
this advisory after delivery. Advisory delay, rejection or failure must not
change the original answer or its completion state.

Trusted catalogs declare sources, scope assumptions, quantity aliases, variable
aliases/definition terms and required dependencies. No question-specific branch
exists in the checker. The KV cache catalog is an explicit source-derived
example; other domains use the same protocol. Conflicting definitions, unknown
symbols and unsupported algebra are reported as unchecked. Even a wrong
coefficient with complete dependencies can escape this limited check: the
`no_dependency_gap` status is **not** a correctness verdict. Other facts are
unchecked. No model invocation or GPU capacity is required.

Reports bind the exact question/answer UTF-8 digests, preserve verbatim formula
quotes and include full source URLs, derivation provenance and assumptions.
Never concatenate advisory text into conversation history, answer copies or
reasoning. Render report text as untrusted text; never execute formulas.

Run the loopback-only bounded adapter separately from inference:

```bash
PYTHONPATH=src python -m sage.serving.advisory_server \
  --catalog docs/advisory-kv-cache-contract.json --port 55109
```

`POST /audit` accepts only `question` and `answer`; `/health` returns metadata.
No raw answer is logged or persisted. Inputs over 2 MB or 256 formulas reject
without truncation. The sequential HTTP adapter bounds memory/concurrency and
uses socket deadlines. Place it behind a same-origin application proxy with its
own deadline; do not bind it publicly. Sources are operator-controlled, not
caller-provided URLs. This adapter does not fetch arbitrary URLs or inherit a
model API key.
### Composite dimensions and Chinese symbols

Source contracts can declare Chinese aliases and `may_cover` dependency roles.
These conditional substitutions require an explicit `scope_note`; they do not
prove equivalence. For example, a hidden-width product may represent KV head
count times per-head width for ordinary MHA, but not unconditionally for GQA or
MQA. Reports retain this ambiguity rather than declaring such a simplification
wrong. Explicit batch-one/single-layer assumptions still require review.

