# Native cursor execution observations

`sage.runtime.execution_observation.ExecutionObserver` exposes native local
FlowNet cursor execution, rather than reconstructing execution from application
step names. It adds no executor, background worker, scheduler or alternate flow.
Without a bound observer, the existing execution path remains in use.

```python
from sage.runtime.execution_observation import ExecutionObserver

events = []
with ExecutionObserver(events.append, trace_id=trusted_trace_id).bind():
    outputs = endpoint.call(request, request_id=trusted_request_id)
```

The sink receives immutable `ExecutionEvent` objects. `to_dict()` returns detached
JSON-compatible metadata. Sinks may persist or forward events, but must not execute
workflows or re-enter observation delivery. Delivery is serialized per observer;
sequence numbers define delivery order, including across native parallel workers.
Sink exceptions become explicit `ExecutionObservationError`, without sink error
text in the public failure classification; they cannot silently become successful
operator execution or be absorbed by a flow exception fallback.

## What an event proves

- `started`: native cursor execution has entered its attempt, before application
  target execution. It is not merely a submitted request or an inferred stage.
- `completed`: the cursor step returned normally. This does not acknowledge a
  database commit, complete all background work, or prove external delivery.
- `failed`: cursor execution failed or an exception policy dropped/aborted it.
- `cancelled`: cursor execution raised native cooperative/async cancellation.
- `recovered`: a real native exception handler produced fallback outputs. It is
  deliberately distinct from ordinary completion.

`resolution` distinguishes fallback, drop and abort. Events contain wall-clock
nanoseconds, measured monotonic duration nanoseconds for terminal states, and
unique execution/event IDs. Sequence is the ordering authority; clients must not
infer ordering from rounded wall-clock values. A cursor that never starts does
not receive an invented completion/cancellation event. If cancellation occurs
after an operator returns, the operator may truthfully be completed while the
overall request is cancelled; the existing request outcome remains authoritative.

## Topology, scheduling and nesting

Events carry actual program URI/revision and native node ID. Optional
`operator_key` is explicit definition metadata, exposed by
`stream.map(target, operator_key="read-memory")`; it is a label, not an execution
identity or concurrency hint. Callers must use non-secret registry identifiers.

`upstream_node_ids`/`downstream_node_ids` describe ordinary compiled graph links.
They are not guessed or completed from operator names. Native entry routing and
dynamic transitions need not appear in those ordinary links. Terminal events
therefore separately include `next_nodes`, copied from the actual materialized
successor cursors, including their program URI/revision and node ID. Router fanout
is qualified against actual branch starts, not an assumed static upstream list.

`wave_id` and `wave_size` identify the native ready-wave scheduling boundary.
They prove co-scheduling eligibility, not measured temporal overlap. Applications
must not relabel a wave “ran concurrently” solely because it contains siblings.
Tests separately demonstrate overlapping starts with a barrier. Nested native
calls carry `parent_execution_id` through the existing copied request contexts;
ordinary graph dependency is represented by node links, not fabricated nesting.

## Privacy, durability and scope

Events do not include operator input/output, tags, exceptions/messages, actor
transport addresses or arbitrary target configuration. Trace/request/registry
identifiers must themselves be non-secret. Native request contexts isolate
observers across concurrent calls sharing a resident executor. A new observer
binding resets parent/wave context, and cleanup restores its enclosing scope.

The observer is a local process port, not serialized into business payloads or
sent as a credential to remote actors. When a cursor waits on a remote target,
these events measure that local cursor attempt, not remote GPU/kernel start time.
Remote worker telemetry requires its own qualified transport contract.

Observation is not durable by itself: durability belongs to its injected sink.
`ExecutionObserver.journaled(journal, stream_id=owned_stream)` persists metadata
using that existing SAGE EventJournal and the same native observer. It emits
`execution-event` frames with stable event IDs, without a second store or worker.
Applications must retain authorization and delivery scope. They must keep operator
completion separate from a durable WorkJournal task acknowledgement, answer
commit and terminal delivery. In particular, never append late telemetry to an
already-closed canonical answer stream or turn an answer into a failure just to
hide such ordering bugs; that integration needs an explicit lifecycle boundary.

Application notes such as “booking not requested” or “source unavailable” remain
business annotations. They are not a substitute for these execution states, and
must not restore guessed parallel groups when native events are unavailable.

## Qualification boundary

Real native flow tests cover overlapping fanout starts, actual router successor
edges, nested runtime parentage, concurrent request isolation, unobserved-call
cleanup, failure and cancellation, fallback/drop/abort distinctions and fail-closed
sink delivery/reentrancy. This platform qualification is not a claim that an
application already persists or renders all events, or that durable background
task acknowledgement/production visual acceptance has been completed.
