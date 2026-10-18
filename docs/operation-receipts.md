# Atomic operation receipts

`OperationReceipts(store, namespace=...).commit(operation_id, inputs=..., slots=...,
transition=..., guard=...)` binds a trusted operation identity to canonical JSON
input and a fixed destination set. A pure transition receives current detached
slot values and returns `(json_result, replacement_mapping)`. Result receipt and
all destination replacements commit in the same SAGE state transaction.

Same identity/input/destinations returns the original saved result without running
the transition or rewriting current destination state. Changed input/destinations
raises `OperationConflict`. A failed transition or commit leaves no partial effect.
Missing acknowledgements can be retried. Receipts have no automatic TTL.

The caller must authenticate and authorize every call, including replay. Namespace
and operation IDs are not capabilities: derive them from verified owner/request
identity, not a client-chosen global key. Include all meaning-bearing business
inputs in `inputs`; do not include credentials. The receipt stores only the input
digest, declared destinations and JSON result, but the result itself may be private
and must receive the same storage/access protections as the destination.

An optional `PreparedLeaseGuard` must share the exact store; it is checked before
both initial execution and replay. This API does not coordinate separate databases
or fence an external destination. A durable backend is required across restarts.

## Composing background work

Declare a prepared `WorkJournal.prepare_commit(...).slots` alongside destination
slots. The pure transition combines destination replacements with
`prepared_work.apply(values)`. This admits the indexing/notification intent in the
same transaction, including native active-request capacity accounting. Start the
worker outside the transaction. Capacity rejection rolls back destination and
receipt too; replay of a committed operation does not readmit its completed work.

Never send email, execute a model, access the network, write files or invoke store
methods from the transition. Persist a stable intent, then execute it with the
existing SAGE work service and destination idempotency. External acceptance with
a lost acknowledgement remains at-least-once unless that external destination
enforces an idempotency key. Do not advertise this API as external exactly-once.

For model-derived plans, capture the authorized plan durably before retryable
effects; rerunning a model and silently accepting a changed payload is not safe.
Keep a receipt and its destination lifecycle coordinated: never discard a receipt
while the same operation identity can be retried.

Qualification covers independent connections/processes, reconstruction, altered
input/destination rejection, same-store/cancelled guards, failed SQLite writes,
lost acknowledgements, process death before and after commit, and atomic outbox
capacity admission. Application wiring and production migration require their own
end-to-end tests; the primitive alone does not repair existing callers.

## Explicit destination-schema migration

`migrate_destinations(operation_id, migration_id=..., old_slots=..., new_slots=...,
evidence=...)` is an operator-authorized migration, not an automatic replay fallback.
It requires an existing receipt and a strict destination superset. In one state
transaction it preserves the complete original receipt in a migration audit and
changes only the receipt's declared destinations. Input digest and canonical
result are unchanged; no destination is initialized and no historical task is
admitted. Historical effects on newly declared destinations remain unproven.

The nonempty JSON evidence must explain the application migration policy, including
unknown external delivery outcomes. A repeated identical migration returns its
audit without rewriting state; changed evidence, source schema or target schema
fails closed. An absent receipt cannot be fabricated. A new producer can continue
to use the strict commit contract after migration, while old operations replay
their original result without rerunning effects. Do not use this to claim that
historical external effects were atomic or delivered. Migration auditing is
persistent and subject to the same authorization and retention as receipts.
