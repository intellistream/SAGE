SAGE PR #1532 joint acceptance handoff: real LocalEnvironment batch/streaming plus the chat HTTP path with deterministic fake transport generated **82 events** (no NPU/network/model service).

Exact shared-host artifact: `/home/shuhao/SAGE-trace/.planning/inference-trace/acceptance/workflow-3/workflow.ndjson`

SHA-256: `8175cb564eb651432576c46f52b671445e476ffc462d4ce669eb467f719b07ee`

I ran this PR’s actual native importer at source `8f99ef502f7881e2d8cfabf6e946c3a12cc0ffba`: v1, duplicate import (82 duplicates/zero inserts), reverse order, missing start and partial tail, exact retry-path duration, cross-clock no-sum, future-version rejection, and SQLite/HTML/Perfetto privacy checks pass. Reproducer: `/home/shuhao/SAGE-trace/src/tests/check_inference_trace_import.py`; report: `/home/shuhao/SAGE-trace/.planning/inference-trace/acceptance/import-3/report.json`.

Please independently import the same bytes/hash for the joint E2E gate. SAGE remains draft during acceptance. The exact artifact is now committed in SAGE head `47a6ed0b989a6cf621228e0a097c69527dcd32b9`: [producer NDJSON](https://github.com/RIDE-Lab/SAGE/blob/47a6ed0b989a6cf621228e0a097c69527dcd32b9/src/tests/fixtures/inference_workflow_v1.ndjson). The actual two-process SAGE snapshot-follow → TraceLoom import-follow path also passed 41→82 events plus HTML refresh. [Reproducible acceptance and raw commands](https://github.com/RIDE-Lab/SAGE/blob/47a6ed0b989a6cf621228e0a097c69527dcd32b9/docs/validation/inference-trace-acceptance.md).
