# Acceptance matrix
1. Disabled tracer: no exporter/thread/file creation; exact return/error behavior; compare timed no-op pipeline against tracing call bypass, report rather than assume overhead budget.
2. IDs/context: valid 32/16 lowercase hex; nested spans preserve parent; 8 concurrent roots isolated; executor and source thread propagation; explicit remote carrier API uses IDs only.
3. Timing/status: fake wall clock jumps leave monotonic elapsed correct; retries use new spans and causal links; cancellation/error never record exception messages; streaming root remains live until all its sources end.
4. Privacy: adversarial prompt/output/headers/reasoning/password/token/URL query nested in payload never serialized; summaries disabled by default and explicit redactor required for text; unknown metadata dropped; type/size/hash bounded without repr(custom_object).
5. Export resilience: queue full, slow/raising exporter, closed exporter, bad path, rotation, TTL, record size, max bytes, stalled sink close timeout; inference outcomes unaffected; drop/export-error counters visible.
6. Protocol: producer fixture consumed by TraceLoom; repeat read, partial NDJSON last line, missing starts/ends, future schema, event provenance; exact allowlist and no arbitrary payload object.
7. Integration: Local batch and streaming, FlowNet lightweight actor, generic Packet path, model nonstream/SSE usage, tool/retrieval extension span, adapter calls; no NPU/network in unit tests.
8. View: live/finished receipts, missing-span caveats, dependencies distinct from parentage, longest observed dependency path (no parent duration double count), JSON CLI output and follow refresh.
