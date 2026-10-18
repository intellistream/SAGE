# Native work service and task status

WorkService.status observes supervisor/admission lifecycle under its existing
lock. Created services may accept an admission that starts their supervisor;
they are not ready yet. Running means the supervisor is alive. Draining, stopped,
closed and failed are distinct, non-accepting states. A recorded supervisor
failure remains failed even after close; unexpected normal supervisor exit
rejects further admission before committing work. Error type is included, never
raw exception text, payloads, results, lease tokens or credentials.
The independent drained flag confirms dispatcher close completed. After a failed
supervisor, close still reports that failure; once it explicitly confirms drain,
retirement may release resources exactly once without erasing the failed state.
An undrained failed service still cannot retire its resources. Thread exit alone
is not drain acknowledgement.

AsyncWorkService.status projects the same lifecycle and separately observes its
owner event loop. A live dispatch thread cannot make a stopped/closed loop ready
or accepting. Observation is thread-safe and schedules nothing onto that loop.
Neither API is a handler-progress heartbeat, storage/connectivity test, external
delivery receipt or guarantee that a future operation succeeds. A blocked but
running thread/loop needs its own progress instrumentation; do not invent it.

WorkJournal.status(request_id) reads one validated durable record and returns
immutable content-free metadata, or None for missing records. Tasks retain their
actual native state, attempt number, due/lease times, dependencies and last
recorded failure code. That code can describe an earlier failure after a later
successful retry; it is not a fabricated current failure. An expired lease is
still running until reclaimed, with lease_expired flagged. Claimability uses the
exact predicate used by native claim, not a second scheduling implementation.
It is only an observation, not a reservation, authority grant or lease renewal.
Reading has no effect on canonical state, active indexes or attempt history.

The caller must authorize namespace/request identity before exposing these
snapshots. Per-request task state does not certify supervisor or destination
health; service lifecycle does not certify a particular task's completion.
Application status composition must retain these independent meanings.
