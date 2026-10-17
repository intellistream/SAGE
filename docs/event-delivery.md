# Durable event delivery primitives

`sage.runtime.event_journal.EventJournal` records JSON events on an injected
`StatefulProcessRuntime`. Use a persistent backend for restart recovery. Stream
IDs are application-authorized identities, not access tokens. A stable event ID
deduplicates identical appends; changed payload or terminal status conflicts.
Sequences are assigned in the state transaction, not from wall-clock order.

`prepare_append` captures a pure mutation that can join WorkJournal destination
mutations on the same store. Preparing is not committing. Terminal publication
and closure are atomic; no new events may follow, but identical retries remain
valid. Reads return detached pages with cursor, tail, closed and caught_up flags.
An ahead-of-tail cursor fails explicitly. There is no silent truncation or TTL.

`WorkJournal.finish(..., mutations=...)` joins pure destination mutations to the
lease-fenced task acknowledgement/result transaction. A stale lease, conflicting
event or storage failure cannot publish half a completion. Retry acknowledgements
cannot publish destination state; journal slots are reserved. No external effect
is protected by this transaction. A lost acknowledgement after a successful commit
leaves the task done and its event available for replay after restart.

`WorkService`/`WorkDispatcher` accept `completion_mutations(lease, result)` to
prepare these transforms on successful handler completion. The callback must be
pure: use `EventJournal.prepare_append`, not `append` or another storage call.
Preparation failures propagate without acknowledging the task. Reconstruct the
same completion policy when recovering workers; it is not serialized in the journal.

`sage.runtime.event_subscription.EventSubscription` gives every asynchronous
iterator its own cursor. It yields committed event records and `None` heartbeats.
Reconnection supplies the last delivered sequence as `after`; clients may need
to deduplicate an event delivered before their acknowledgement was lost. A
closed stream only ends after the subscriber has received its full final page.
No shared subscriber queue is replaced, and disconnect does not cancel producers.

The store is borrowed. Cancel and await subscription tasks, or close suspended
iterators, before closing it. Cancellation waits for any actual blocking read
to finish, including repeated cancellation, rather than abandoning a thread
that still accesses storage. This is not forced cancellation of blocking I/O.

Qualification covers independent subscribers, pagination/reconnection, terminal
replay, separate SQLite connections, concurrent idempotent publication, lost
acknowledgements, atomic rollback with work admission, heartbeats and cancellation
drain. The combined source suite passed 43 tests; the installed-wheel journal and
subscription suite passed 13 tests outside the source directory.

Limitations: per-stream snapshot rewriting and polling load still need capacity
and retention qualification. These primitives do not provide HTTP authorization,
SSE framing, producer recovery, distributed cancellation, or a complete transport
lifecycle. Applications must not claim durable final-answer delivery until their
canonical answer and event intents share a qualified commit boundary.

## Async service integration

`sage.runtime.async_work_service.AsyncWorkService` adapts async handlers to the
same `WorkService` dispatcher and journal. Construct it on the application's
running event loop; `await start()` recovers pending work, `await commit(...)`
admits work, and `await wait(request_id, timeout=...)` observes completion.
Handlers run on that loop, so loop-bound model/HTTP clients can be reused.
Worker bounds, lease renewal, retry, routing and completion mutations remain
owned by the existing dispatcher; this does not create a second task engine.

Call `await aclose()` before closing borrowed storage, async clients or the
event loop. Cancellation of a commit or close waits for the actual blocking
operation to finish; it cannot roll back a transaction that already committed.
Cancellation of a waiter does not cancel the handler. Close timeout reports an
incomplete drain and leaves resources owned; retry close after handlers finish.
A handler cannot wait on or close its own service. Cross-loop use is rejected.
Handlers must cooperate with the event loop; blocking async code can prevent
shutdown. Abrupt loop destruction is not a graceful shutdown protocol.

External deliveries remain at-least-once attempts, not exactly-once effects.
Applications must provide destination idempotency and revalidate authorization,
and must not place bearer callback URLs or credentials in task payloads. This
adapter alone does not make a transport durable: its admission, answer and
delivery intents still need the appropriate atomic commit boundary.
