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

`await wait(request_id, timeout=..., start_timeout=...)` optionally bounds how
long an observer waits for the first journal claim. It raises
`WorkStartTimeoutError` while an unclaimed request remains durably queued; it
does not reject or cancel that work. Callers can report retryable backpressure
and retry the same ID. A claimed request (including delayed retries) uses only
the overall completion timeout. A claim is not proof that an external model
has begun executing, and this API does not claim an exact queue position.

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

## Native task prerequisites

`WorkJournal.prepare_commit/commit`, `WorkService.commit`, and
`AsyncWorkService.commit` accept `dependencies={"deliver": ["answer"]}`. The
graph is captured with task payloads and is part of immutable admission identity.
Unknown tasks, duplicate prerequisites and cycles fail before writing. Independent
tasks retain the existing record format; graphs use version 2 so older workers
fail closed instead of ignoring ordering. Upgrade all consumers before producers.

The dispatcher skips known-blocked tasks and `claim` atomically rechecks that all
parents are done. Waiting for a prerequisite does not acquire a lease, increment
attempts or enter failure backoff. Retried or expired parents remain unfinished;
their children cannot run until a successful fenced completion. This is not a
terminal-failure/cancellation propagation policy or cross-request dependency graph.

For offline migration of independent records, stop old workers and call
`upgrade_dependencies(request_id, graph)` before starting new consumers. It rejects
live leases, changed graphs and already-completed children with unfinished parents.
Existing valid results, attempts and payloads are retained. Replay admission must
include the same graph. Do not run old and new writers concurrently during cutover.

## Classified task failures

Dispatchers and both work services accept `failure_policy(lease, exception)`.
Return `WorkFailure(code, retry_delay=seconds)` for a delayed retry, or
`WorkFailure(code)` for terminal failure. Policies can use the durable
`lease.attempt` to bound retries across restarts. Classification is synchronous,
must be fast, and must not perform external effects. Invalid policies fail the
supervisor without acknowledging the task. Without a policy the existing retry
behavior is unchanged; applications must explicitly adopt and qualify a policy.

Only a restricted application-defined code is persisted, not exception text,
tracebacks or credentials. Failure uses the same lease-token and expiry fence as
completion. Terminal tasks become `failed`; their pending transitive dependents
become `blocked` in that transaction and are never claimed. Independent siblings
may still run. `wait` raises `WorkFailedError`, not a success record or observer
timeout; `read` retains results, attempt counts and failure codes for inspection.
Retry success may retain the prior failure code as diagnostic history.

Classified failures write version-3 records. Stop older consumers before adopting
this policy; older readers fail closed. Rollback requires matching state and code,
not a downgrade over version-3 data. Terminal failure is durable across restart;
there is no automatic requeue or deletion. It does not undo prior external effects
and does not provide exactly-once delivery. Retention, administrative remediation
and application-specific failure notices remain separate responsibilities.

## Durable finalizers

Admission accepts `settled=["finalize"]` together with, for example,
`dependencies={"deliver": ["answer"], "finalize": ["answer", "deliver"]}`.
Ordinary dependency edges still require success. A named settled task instead
waits for every parent to be `done`, `failed`, or `blocked`; pending retries and
running leases are not terminal. Both dispatcher selection and atomic claim use
the same readiness predicate. A failure does not block the settled task itself.
Its handler inspects parent outcomes and can publish a failure notice or do
nothing on success. The finalizer uses the same leases, retry policy, recovery
and destination-idempotency requirements as every other task, not a callback.

Finalizer completion does not erase parent failures. `wait` still raises on a
terminal parent failure and does not promise that finalizers have finished;
consumers inspect task state for their receipts. A stopped service can leave
pending finalizers for its successor, like any other admitted task. A finalizer
that fails terminally remains failed and is not recursively regenerated.

Settled dependencies require at least version 4; current indexed admissions use
version 5, failing closed on older readers. To add a
finalizer to an existing record, stop old consumers and use
`extend_tasks(request_id, tasks=..., dependencies=..., settled=...)` before
starting the upgraded consumer. The extension is atomic and additive: existing
payloads, edges, results, attempts and terminal states cannot be rewritten.
Identical replay is safe; changed payloads/edges and active leases reject edits.
This migration does not requeue failed work or imply delivery has occurred.
Subsequent admission replay must include the extended task graph and settled set.
Back up code and state consistently before upgrading; rollback must restore both.
