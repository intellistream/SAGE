

**F1 — Proven bug: `record_error` races with `Span.end`.**
`record_error` mutates status with no lock, while `end()` reads status under the lock and emits after releasing it. A concurrent `record_error` during `end()` can lose the error (emission precedes the write) or expose a partially written status to the exporter.
*Minimal test:* one span; a thread loops `record_error(e)` while the main thread calls `end()`; 10k iterations. Assert the exported `span_end` status is always a valid enum value, and in the join-ordered variant (writer joined before `end`) the status equals the last error written.

**F2 — Proven gap (potential bug): post-close emissions may bypass drop accounting.**
`emit` checks `closed` *before* `queue.put_nowait`, and only `put_nowait` drops are documented as counted. Spans completing after `close()` — late async callbacks, retries landing after "workload finish" — are discarded by the `closed` check. If that path does not increment the drop counter, "all losses are reported" is false for the most common production sequence (close, then final completions).
*Minimal test:* enable tracer, `close(timeout=0)`, then call `span.end()` once; assert either the event appears in the exported stream or `drop_count` increased by exactly 1.

**F3 — Proven limitation: purge-vs-reader race and mtime order ≠ event order.**
The reader opens files normally, unsynchronized with purge: a file can be deleted between list and open, or a line read mid-append (no interprocess lock; per-exporter thread lock only). Additionally, per-export `stat mtime` sorting is not a total event order — same-second mtimes across exporters, or an append mutating mtime, can order files inconsistently with event time, undermining the monotonic-same-clock assumptions of strict readers.
*Minimal test:* one process; background purge loop (~1 ms interval) while a reader iterates lines; assert every line obtained parses as NDJSON, and a mid-read deletion raises only a documented exception type — never a torn record accepted as valid.

**F4 — Proven limitation: enabled mode is heavily lossy under bursts, and the exit path loses events unreported.**
Measured: ~95% of events dropped at 10k child spans (NDJSON: ~18,974/20,000). Worse, the worker is a *daemon* thread and retention "runs on export or explicit purge, not after exit": a crash, or the documented absence of `close`, kills the worker mid-drain, and queued-but-unexported events are lost without any count — the "all losses are reported" guarantee does not extend to that path.
*Minimal test:* subprocess enables the tracer, emits 20k spans, then `os._exit(0)` without `close`; the parent asserts either all events are present in the NDJSON dir or the loss is recorded in some durable artifact.

**Summary:** F1 is a proven concurrency bug; F2 is a proven accounting gap that becomes a bug if the `closed` path skips the counter; F3 and F4 are proven, documented-limitation-class issues with concrete exploitation shapes. No further proven bugs are derivable from the stated facts; the bounded secret redactor, trusted-label handling, and ID-collision surface are design limitations, not demonstrated defects.