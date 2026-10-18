# Native durable work-attempt observations

WorkObserver is an optional content-free observation destination for the existing
WorkDispatcher/WorkService/AsyncWorkService, not a second scheduler or worker.
Callers map an authoritative TaskLease to an owned WorkEventDestination containing
an existing EventJournal and stream ID. The destination must borrow the exact
same state instance as the WorkJournal. Authorization remains the caller's job;
an arbitrary client-supplied stream ID must never become delivery authority.

The factory may return None for an explicitly unobserved task. It has the lifetime
of the work service, so it must not capture credentials or strongly retain an
application owner that needs to be collected. There is no inherited request-scoped
observer ContextVar on background workers.

## Meaning of states

- started: a worker has entered its actual attempt and durably published the event
  under a still-current lease, before invoking the handler. Queue admission alone
  is not execution. If publication fails, the handler is not invoked.
- completed: result, destination mutations, task acknowledgement and event commit
  in the same fenced transaction. Future completion or handler return is not enough.
- retrying: the real failed attempt and delayed retry decision commit together.
  This does not publish a business result or an ordinary destination effect.
- failed: classified terminal failure, dependent blocking and event commit together.

Events identify namespace/request/task/attempt, timestamp, elapsed attempt duration,
dependency IDs and native success-versus-settled dependency mode. Same labels across
jobs/attempts are not identities or concurrency evidence. The events contain no
payloads, results, lease tokens, raw exception text or transport addresses. Safe
failure code and exception type are separate from private exception details.

A queued task, blocked dependent or cancelled/stale handler that never obtains a
valid publication does not acquire an invented event. Current WorkJournal state
remains the authority for queueing, cancellation and dependent blocking; clients
must not derive these states solely from an absent attempt or familiar task name.
Expired/dead attempts retain their truthful incomplete history; recovery emits a
new attempt, never retroactively invents completion for the old one.

## Atomic publication and integration boundary

WorkJournal.observe accepts only a prepared started observation. WorkJournal.finish
and fail accept only observations bound to the same journal, lease, attempt and
matching transition. Ordinary retry result/destination prohibitions are unchanged.
An observation does not extend a lease or acknowledge an external side effect.

Native acknowledgement observations compose BEFORE application completion mutations
on a shared EventJournal slot, so an application's terminal frame can close the
stream in the same transaction. A stale lease or storage failure rolls everything
back. Closed or misrouted event destinations fail explicitly; publication is never
silently dropped to fabricate a successful task.

Prepared observations are in-memory pure values, not acknowledgements or portable
credentials. Prepare once when settling an attempt. Stable IDs reject conflicting
duplicate content; after a lost commit acknowledgement, inspect the durable task
and event records rather than executing a completed handler again.

The caller must choose explicit terminal ownership. Do not observe arbitrary HTTP
ingress acknowledgements into an already-closed answer stream; a post-answer task
may have legitimately closed its own delivery scope first. No new polling loop,
handler wrapper in the application, or second storage mechanism is required.

## Qualification

Tests use actual SQLite transactions, native dispatchers and services, a real child
process exiting between entry and acknowledgement, lost-ack/reopen recovery,
concurrent owner-separated streams, success and settled dependencies, delayed
retries, failed-start prevention, completion/failure rollback, stale leases and
wrong-store rejection. Platform tests alone do not prove application adoption,
production cutover or browser acceptance.
