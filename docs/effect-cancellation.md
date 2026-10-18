# Cross-store effect cancellation

`sage.runtime.effect_cancellation` provides destination-local `EffectFences` and
a `CancellationService` over the existing native `WorkJournal`/`WorkService`.
It is not a second scheduler, distributed rollback, or an external exactly-once
API. Its guarantee applies only when every effect writer participates.

## Contract

1. Trusted ingress supplies a unique owner-scoped request identity. The application
   authorizes every cancellation, observation and replay; a request ID is not a
   capability or authorization token.
2. Every controlled destination wraps its writes and receipt replay in its local
   transaction guard. Preparation is not a check; the check must run inside the
   same transaction that commits the effect and its receipt.
3. Cancellation admits a durable native task for each declared destination seal,
   then a dependent final task. Admission returns `accepted`, never `cancelled`.
4. A seal serializes against in-flight local writes, is permanent for that scope,
   and denies future guarded commits, including replay. Past committed effects
   remain. An unavailable destination leaves cancellation pending and recoverable.
5. Only after all seals are acknowledged does the final native task revalidate
   destination bindings, idempotently re-seal and attempt origin-task cancellation.
   Existing canonical-answer protection still applies in the origin transaction.
6. `wait` reports `cancelled`, `protected`, `terminal` or `missing` only after
   native settlement. An observation timeout or an exception is NOT successful
   cancellation. Restart calls `start` to recover pending intents, without needing
   a new user request. Lost origin-cancel acknowledgements recover as `cancelled`
   only when the origin task durably records `request_cancelled`.

Destination identities are generated and persisted in each store/namespace.
An old acknowledged seal cannot unlock cancellation against a different store
later mounted under the same destination name. Such configuration errors remain
pending, with only the safe `cancellation_unavailable` code recorded. Error text,
credentials and endpoint details are not serialized by this service.

## Usage

```python
from sage.runtime.effect_cancellation import CancellationService, EffectFences
from sage.runtime.operation_receipts import OperationReceipts

# These are independent SAGE state backends. They remain borrowed resources.
bookings = EffectFences(booking_state, namespace="preanswer-effects")
knowledge = EffectFences(knowledge_state, namespace="preanswer-effects")

# Every pre-answer effect, draft mutation and replay must pass its local guard.
receipt = OperationReceipts(booking_state, namespace="booking-effects")
result = receipt.commit(
    effect_id, inputs=inputs, slots=effect_slots, transition=pure_transition,
    guard=bookings.prepare_guard(trusted_request_id),
)

cancellations = CancellationService(
    origin_journal, task_id="answer",
    targets={"bookings": bookings, "knowledge": knowledge},
    protection=prepare_canonical_answer_protection,
)
cancellations.start()
admission = cancellations.request(trusted_request_id)
if admission == "accepted":
    outcome = cancellations.wait(trusted_request_id, timeout=30)
# Close only after successful drain, before closing ANY of the borrowed stores.
cancellations.close()
```

Async adapters use `astart`, `arequest`, `await_result` and `aclose` on this same
service. These ports reuse the existing async work service's
`complete_sync_call` ownership boundary: cancellation of an asyncio observer,
including repeated cancellation, waits for its underlying synchronous call to
settle before propagating. No borrowed-store read or close thread is abandoned.
This is an async facade over the same durable worker, not another scheduler.

Lazy providers returning `EffectFences` are supported. Destination names and
bindings are immutable within an admitted cancellation. Changing a declaration
on replay raises a journal conflict; missing/remapped providers cannot become
successful acknowledgements. An empty declaration is supported for a task with
no controlled remote effects, using the same native cancellation workflow.

## Application integration and non-guarantees

The origin's normal producer/answer-commit lease guard remains necessary. A local
effect guard does not grant an origin lease. A producer encountering
`EffectCancelled` while a cancellation is pending must not publish an early
terminal cancellation notice: its adapter must await native cancellation settlement
or let the native producer remain recoverable until that settlement. Likewise,
an HTTP/UI response must distinguish pending admission from completed cancellation.
Do not enable cross-store success acknowledgement before adapting every declared
writer, including draft capture/settle and any retry or alternate entry point.

Sealing does not undo an existing reservation/document, remove already admitted
index/outbox work, or recall an email already sent. Those effects need an explicit
compensation policy if desired. A protected canonical answer is retained, not
rewritten as cancelled. Leases do not interrupt an already executing synchronous
OS/network call; the guarantee is no later guarded transaction after its seal.

The service does not delete or expire fences or audit records. Never reuse request
identities or perform live store rollback/replacement while writers/coordinators
are active. Offline restore must preserve canonical state and pending cancellation
intents together. This protocol is not atomic commit across independently restored
databases, and the in-memory state backend is not crash durable.

## Qualification

Tests use real independent SQLite stores/connections: prepared stale guards,
replay denial, racing seal/write transactions, wrong-store guard rejection,
corrupt fence fail-closed behavior, unavailable destinations, lost cancellation
acknowledgements, canonical-answer protection, remapped destination identity both
before and after seal acknowledgement, zero-destination cancellation, and actual
process death after a seal commits but before its acknowledgement. This foundation
qualification does not claim that any particular application has adopted all
guards or completed production migration.
