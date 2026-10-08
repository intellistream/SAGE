# Exact SAGE producer artifact for TraceLoom PR 63 joint acceptance

SAGE PR https://github.com/RIDE-Lab/SAGE/pull/1532 (initial head 1267a4ef287daa54025e1d81ef091d646a3dcb13, remediation in progress).

- Actual LocalEnvironment batch + streaming workload, real chat HTTP code with deterministic fake transport only.
- Exact fixture: `/home/shuhao/SAGE-trace/.planning/inference-trace/acceptance/workflow-3/workflow.ndjson`
- SHA256: `8175cb564eb651432576c46f52b671445e476ffc462d4ce669eb467f719b07ee`
- 82 events. Success/retry/error/cancel, packet operator/queue and model scopes, overflow counter. Unavailable exporter produces no events and is verified separately by statistics/semantic equality.
- Generator: `/home/shuhao/SAGE-trace/src/tests/inference_trace_workload.py`
- Manifest: same workflow-3 directory `manifest.json`; original producer bytes preserved.
- Actual native importer used: `/home/shuhao/traceloom-inference-v1/build/native-tests/native/traceloom`, worktree HEAD 8f99ef502f7881e2d8cfabf6e946c3a12cc0ffba.
- Joint E2E checker: `/home/shuhao/SAGE-trace/src/tests/check_inference_trace_import.py`
- Report: `/home/shuhao/SAGE-trace/.planning/inference-trace/acceptance/import-reviewed/report.json`
- Passed v1 import, 82 duplicates/zero insertion on repeat, reversed records, missing start + partial tail, exact retry dependency duration sum, cross-clock no sum, future-version rejection, sensitive canaries absent in SQLite/HTML/Perfetto.

The current tool catalog has no send_message_to_thread capability. This shared handoff and task commentary expose exact bytes/hash for the TraceLoom task and coordinator; confirmation of their independent import remains pending.
