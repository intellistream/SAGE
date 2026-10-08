# Collector map / proposed TraceLoom contract
Initial candidates: Environment/JobManager root run; CompiledActorGraph source polling and packet dispatch; actor wrapper execution and method submission/queue boundary; serving integration import/submit/poll/result; chat HTTP completion boundary; FlowNet ActorInvoker and flow observation contract. Existing logging is CustomLogger; FlowNet has telemetry/state-query/observation contracts to inspect.
Proposed sage.trace.v1 span event: schema_version, event_id, trace_id, span_id, parent_span_id, event(start/end), wall_time, duration_ns from monotonic clock, name/component/kind, status, attempt, attributes allowlist, decision_summary, evidence_refs, input/output summaries + hashes. Export must not block inference; no-op default; bounded queue/drop counters; endpoint metadata strips auth/query; LLM content defaults to type/size/hash only. Timeline interface must reconstruct live and finished spans and label critical path semantics explicitly.

## Verified source map
- pipeline_compiler.CompiledActorGraph.submit is the common high-level Local/FlowNet run boundary; streaming returns before source threads finish, so trace receipt must wait for its own source-thread completion.
- _dispatch_from_source/_process_packet own generic operator execution; _execute_chain submits actor calls. Instrumenting operators.py alone misses both active paths.
- local_backend / flownet_backend async_call lose ContextVars through ThreadPoolExecutor; explicit copy_context wrapper is required. FlowNet executor_lanes already provides run_in_executor_with_context for inner actor execution.
- serving.integrations.registry import/submit/poll/collect are public adapter boundaries; existing contracts include request/result/status but no complete hierarchical execution trace.
- cli.commands.apps.chat._request_openai_chat is real HTTP model boundary; parse usage without persisting messages or SSE content. Direct sagellm is only an observable subprocess span, not inner model visibility.
- Foundation CustomLogger and FlowNet telemetry/observation contracts expose logs, queue counts and terminal receipts; do not export arbitrary telemetry/traceback payloads, which may include raw values.
- Optional RAG/tool packages own their internal operations; expose model/retrieval/tool span helpers rather than pretend all external internal steps are visible.

## TraceLoom alignment
Read /home/shuhao/traceloom-inference-v1/docs/contracts/inference-trace-v1.md. Adopt its integer schema_version=1 and exact envelope, NDJSON local spool, start/end/event/trace_end/metrics, OTel-compatible IDs, clock domain, sequence and scalar allowlist. Avoid a parallel sage.trace.v1 wire schema.
Component is encoded by bounded name prefix; queue and execution have separate step spans; endpoint and bounded input/output hashes use opaque evidence_refs (endpoint-..., input-..., output-...). No raw URL, body, exception text, stack or arbitrary attributes are emitted. Public summaries are opt-in. links mean completion-before-start dependencies, never just parentage. Timeline will expose longest observed dependency path with an explicit partial-evidence caveat.
