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
