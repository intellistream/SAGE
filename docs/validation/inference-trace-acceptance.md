# Observable inference trace acceptance

This is a CPU-only local acceptance record for SAGE PR #1532 and TraceLoom PR #63.
It is not a real model-service benchmark. The machine used Linux 5.15 aarch64,
Python 3.13.13, and the same Miniconda interpreter/dependencies for both checkouts.
No NPU, deployment, network inference, or real credential was used.

## Baseline and tests

Clean main `dd8658bd79f07828ea6b4a2b22e5053437476be0` and clean initial candidate
`1267a4ef287daa54025e1d81ef091d646a3dcb13` ran the identical command from their
respective checkout directories:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src \
  /home/shuhao/miniconda3/bin/python -m pytest src/tests -q
```

Base: 141 passed, 1 skipped, 1 failed. Initial candidate: 163 passed, 1 skipped,
1 failed. After acceptance remediation: 169 passed, 1 skipped, 1 failed.
All failures are the same pre-existing
`test_local_environment_round_robins_unkeyed_parallel_map_locally` scheduling
assertion. The 28 tracing tests pass. Ruff and release/tools boundary checks pass.
The machine-readable companion records the exact command, environment overrides,
base/candidate SHAs and run results. CI must be checked against the current PR head;
the required checks are Deployment Readiness Check and the all-sub-package smoke test.

## Actual workflow and joint importer

`src/tests/inference_trace_workload.py` executes a real LocalEnvironment batch
pipeline with key routing, a model map and sink, and a streaming source stopped
while active. Chat uses its actual HTTP request/response code with a deterministic
fake transport. Attempts fail/succeed deterministically; no event records are
handwritten. Disabled/enabled/unavailable-exporter runs compare original return
contracts, sink output, exception type/message and chat output in memory. Job IDs
are checked against each environment's generated ID rather than compared between runs.

The committed `src/tests/fixtures/inference_workflow_v1.ndjson` preserves all
producer bytes from this run. SHA-256:
`8175cb564eb651432576c46f52b671445e476ffc462d4ce669eb467f719b07ee`.
It contains 82 events, including root/operator/packet-queue/model, success/error/
cancel and retry links. The main tracer exported all 76 accepted events. A separate
capacity-one stalled exporter produced 6 exported records and 51 dropped events;
its receipt includes an explicitly sampled cumulative drop count. The unavailable
exporter produced 42 export errors/drops and no events; its evidence is the manifest,
not fabricated spans claiming export success.

The actual TraceLoom native importer from PR #63 source
`8f99ef502f7881e2d8cfabf6e946c3a12cc0ffba` consumed the artifact. The checker verifies:

- v1 import: 82 events; repeat import: 82 duplicates and zero new inserts.
- Reversed event order yields the same span IDs and durations.
- Removing an attempt start yields `missing_start` and an incomplete trace;
  a partial final record remains pending.
- The explicit retry edge has exactly the sum of the two attempt durations.
- Moving one complete attempt into another clock domain removes the duration sum.
- A future schema version is rejected.
- Sensitive canaries are absent from SQLite, HTML and Perfetto projections.
- Actual SAGE `trace export --follow` and TraceLoom `import-inference --follow`
  processes advance from 41 to 82 events after an atomic source replacement;
  the HTML projection advertises refresh and neither process exits prematurely.

Disorder, missing-start and cross-clock files are labeled derived fault probes;
they are not presented as additional real executions. Reproduction commands are
in DEVELOPER.md. Full importer commands/results are in the companion JSON.

## Three-mode microbenchmark

Five fresh processes per mode, 1,000 warmup spans, then 10,000 child spans per
sample. The queue capacity is 1,024 events. Wall-clock medians include one scope
entry/exit per span; drained time additionally waits for accepted records to export.
RSS is process high-water memory including interpreter/imports. Separate allocation
probes use tracemalloc because it changes timing. No CPU affinity was set.

| Mode | Enqueue wall median | Drained wall median | Peak RSS median | Dropped events in each repeat |
| --- | ---: | ---: | ---: | --- |
| Off | 5.44 ms | 5.44 ms | 21,616 KiB | 0; 0; 0; 0; 0 |
| On + discard exporter | 572.48 ms | 573.94 ms | 22,596 KiB | 5,797; 12,261; 9,672; 636; 1,118 |
| On + NDJSON | 525.45 ms | 696.58 ms | 22,608 KiB | 18,970; 18,973; 18,973; 18,972; 18,972 |

There are 20,000 attempted events per timed sample. The tight loop saturates the
export worker, especially NDJSON. These measurements demonstrate bounded loss
and significant enabled instrumentation cost; they do not establish lossless
throughput or a general inference slowdown percentage. All samples and separate
allocation probes are retained in the companion JSON.

## Privacy and display ownership

Canaries cover tokens, Authorization, endpoint URLs, raw prompts/outputs, exception
text and hidden reasoning. Adversarial unknown metadata, oversized references,
large redactor output and malformed Unicode are covered. Summaries are absent by
default; explicit producer-authored summaries remain capped at 256 UTF-8 bytes.
Metadata is a typed application API, not a general-purpose sanitizer for arbitrary
secrets disguised as trusted operation/model labels.

SAGE adds no browser frontend. TraceLoom owns visualization; SAGE exposes trace IDs,
the configured spool path, JSON/terminal inspection, and atomic snapshot refresh.
The longest observed dependency path always remains partial evidence; no synchronized
global clock or complete global critical path is claimed.

The bounded Qwen3.8 review and primary verification are recorded in
[inference-trace-qwen-review.md](inference-trace-qwen-review.md).
