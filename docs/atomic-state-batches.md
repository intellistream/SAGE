# Atomic state batches

`StatefulProcessRuntime.update_many(slots, transform, default=None)` performs a
single read/transform/write transaction for a fixed, nonempty set of state slots.
Each slot is `(stage_id, namespace, key)`. Normalized duplicates are rejected.

The callback receives detached values keyed by normalized slots and must return
exactly the same key set. Missing entries use detached copies of `default`.
The returned values are detached too. The callback must be pure: no model calls,
network requests, external writes, or re-entry into storage. All selected records
receive the same update timestamp. This API is for non-expiring durable records;
TTL-aware single-record updates retain their existing contract.

SQLite reserves the writer with `BEGIN IMMEDIATE` before reading any selected
record. Callback, validation and serialization failures roll back the entire
batch, including SQL writes already performed earlier in the batch. Independent
connections serialize these transactions. Memory storage publishes only after
all replacement values have been prepared successfully under the runtime lock.

```python
memory_slot = ("memory", "session", "turn")
work_slot = ("work", "session", "turn")

def commit(values):
    # Application-specific idempotency/conflict validation belongs here.
    return {memory_slot: {"answer": "..."}, work_slot: {"status": "pending"}}

saved = runtime.update_many([memory_slot, work_slot], commit)
```

This is **not** a transaction spanning different databases, service instances,
or external side effects. Clients must compose their state transformations in
one callback; nesting `update` or another storage operation is unsupported.
It does not make separate `peek` calls a multi-record snapshot, provide an
idempotency policy, or introduce exactly-once task execution.

Tests cover detached state, invalid key sets, callback failure, second-write
serialization failure, concurrent independent connections, process exit after
the first SQL write, and process exit before/after commit followed by reopen.
These are process-crash tests, not power-loss durability certification. Existing
SQLite WAL/synchronous configuration is unchanged. Applications must explicitly
adopt the batch API before claiming atomic destination-state/outbox commits.
