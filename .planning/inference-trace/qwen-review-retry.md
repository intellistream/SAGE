

Scope: read-only, evidence-only; no tools/files used. Below are the risks the 28-batch pass left unpinned, then a test matrix to close them.

**Missing risks**

1. **Completion-contract ambiguity (highest).** Two independent paths conflate "submit returned" with "job done": `CompiledActorGraph.submit(False)` returns a handle while sources still run, and `_run_source_thread` *catches* exceptions and only logs them; `WorkflowIntegrationRegistry.submit` returns an *accepted reference*, not completion. So (a) a raised error yields silent partial success, and (b) no single status distinguishes accepted / span-completed / job-completed / failed. Same root cause in three places — the main thing to pin down.

2. **Context loss at the local thread boundary.** `local_backend`/`flownet_backend` submit `self.call` to a `ThreadPoolExecutor` **without `copy_context`**, so `ContextVar`s (span id, tenant, auth) are dropped on the linear batch path. FlowNet's `ActorInvoker._call_sync_target` uses `run_in_executor_with_context` — the paths are inconsistent, and the contract's "explicit validated carrier" is honored on only one. The linear path silently produces disconnected / mis-parented spans.

3. **Cross-job lifecycle coupling.** `_run_source_thread`'s `finally` enumerates *globally* enumerated source threads. Under concurrent submits this can see another job's threads → premature/incorrect completion. Marked out-of-scope, but any multi-job use inherits it.

4. **Raw-content leak on the DAG path.** `_process_packet` handles arbitrary payloads (possibly creds/reasoning). The "no raw content/keys/errors by default" guarantee lives in the TraceLoom writer, but there's no redaction boundary *at the deque/packet path* before any span event is built.

5. **Cross-clock invalidity.** `producer/clock_id` + dual wall/monotonic timestamps are present, but there's no rule/flag preventing wall_time subtraction across divergent producers. Naive analysis yields bogus durations/orderings.

6. **Silent partiality.** Bounded spool + whole-trace sampling + failure isolation all produce partial traces, yet there's no `events_dropped`/completeness flag, and "longest dependency path" must be marked *partial*, not global critical path. Without a flag an incomplete trace reads as complete.

7. **Opaque subprocess boundary.** `sagellm` is a subprocess; inner spans are unavailable unless it participates. The unexplained time is real but invisible — must be an explicit boundary, not zero.

(Fidelity note: SSE prints only `delta.content`, ignoring reasoning — a real signal is dropped from the observables.)

**Test matrix**

| # | Test | Setup | Expected |
|---|------|-------|----------|
| T1 | async-not-complete | `submit(False)`, multi-source | handle ≠ completion; explicit join/await exists |
| T2 | failure propagation | one source raises | job reports failure, not silent success |
| T3 | cross-job race | two concurrent submits | `finally` enumeration doesn't see the other job |
| T4 | local context loss | set ContextVar, run linear path | expect LOST; then run FlowNet (preserved) to expose the gap |
| T5 | lock timing | measure `_call_sync_target` span | start = execution after lock; queue-wait excluded |
| T6 | DAG redaction | Packet w/ fake cred + reasoning | NDJSON shows only evidence_refs; no raw content by default |
| T7 | chat leak | fake key + sensitive prompt | no auth/prompt logged by default; SSE = content only |
| T8 | parentage≠dependency | links differ from data deps | no global critical path derivable; path flagged `partial` |
| T9 | cross-clock | two producers, divergent clocks | no cross-producer wall_time subtraction; durations per clock_id |
| T10 | spool drop + isolation | overflow spool; crash one producer | `events_dropped` counted, trace marked partial; others still emit |
| T11 | workflow boundary | `submit` then `poll`/`collect` | span ends at accepted-ref, not job-done |
| T12 | optional adapter | remove RAG/tool pkg | explicit typed availability error, not silent no-op |
| T13 | subprocess boundary | invoke sagellm | marked opaque boundary w/ wall-clock; no fake inner spans |
| T14 | remote carrier | context across RPC | travels only via validated carrier; drop ⇒ absent, not wrong |

Must-haves: T1–T3 (completion), T4 (context parity), T6/T7 (secrets). Those are exactly the gaps the long review read but never closed.