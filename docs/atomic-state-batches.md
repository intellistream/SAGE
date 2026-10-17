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

## Composing a work intent

`WorkJournal.prepare_commit(request_id, result=..., tasks=...)` returns a fixed
pair of slots (journal and active index) and pure `apply(values)` with captured
JSON inputs. It performs no write. Both slots must participate in `update_many`:

```python
intent = journal.prepare_commit("turn", result={"answer": "..."}, tasks={"post": {}})
runtime.update_many([destination.slot, *intent.slots], lambda values: {
    destination.slot: destination.transform(values[destination.slot]),
    **intent.apply(values),
})
```

The destination and journal must use this same state store. Each owns its replay
identity and conflict checks; the transaction supplies all-or-nothing commit.
Preparing or evaluating a transform is not a persistence receipt. Worker startup
belongs after commit. `WorkJournal.commit` delegates to the same prepared
transform, so standalone and composed commits have identical journal semantics.

## Atomic work admission with destination mutations

`WorkJournal.commit` and `WorkService.commit` accept an optional `mutations`
mapping from canonical `(stage, namespace, key)` tuples to pure single-value
transformations. The journal adds its own prepared transform and applies every
destination plus result/task intent in **one** `update_many` transaction on its
state store. Destination slots must be nonempty trimmed strings, and the
`sage-work-journal-v1` and `sage-work-active-v1` stages are reserved: callers cannot overwrite any journal
record via this interface. Invalid slots or non-callables fail before writes.

New and mutated journal records use version 5. Every pending/running record has
one active-index entry; terminal-only records remove it atomically, retaining
the canonical result/history. Older workers fail closed on v5. Stop old writers
before upgrade and back up code and state together. The single-slot prepared
transform is intentionally removed: callers must adopt `slots`/`apply` rather
than silently omit the index.

Before indexed dispatch, `recover_active_index()` scans legacy journal rows in
bounded keyset pages, re-reading each row in its own atomic index transaction.
Only a completed sweep publishes the readiness marker. Interrupted rebuilding
repeats safely; live pre-v5 leases reject migration without executing work.
Old writers must be stopped before this operation; the marker cannot protect
against an old process creating a new v1 record after migration. Retain a
consistent code/state backup for rollback. Completed histories remain intact.

`WorkDispatcher` now uses `active_records(after_key=..., limit=...)`; it no
longer scans historical records on each poll. Canonical state is revalidated at
claim, so concurrent completion cannot cause duplicate admission. Keys inserted
behind the cursor are discovered on the next sweep. The initial legacy rebuild
still costs a full scan; indexed steady-state recovery does not erase that cost.

```python
service.commit(
    "turn", result={"answer": "..."}, tasks={"post": {"turn": "turn"}},
    mutations={destination.slot: destination.transform},
)
```

`WorkService` holds its admission lock across the transaction and starts its
dispatcher only after a successful acknowledgement. Shutdown takes the same
lock: a previously admitted commit finishes before shutdown, and new mutations
are rejected once closing begins. Already-running workers may observe the
complete transaction as soon as it commits, not a partial destination/outbox.
Therefore application read views must be reconstructible from committed state;
this API does not wait for an application-side cache to be updated.

Every destination must supply its own replay/conflict checks; a repeated journal
commit does not make a non-idempotent destination safe. No model calls, external
effects, or nested storage calls are permitted in transforms. Inputs captured by
destination closures must be detached by their owner. This does not coordinate
different stores or databases. An exception after persistence but before the
acknowledgement is an uncertain outcome: replay the same identities/transforms
or start a new service on the same store to recover committed tasks. Do not
regenerate a turn ID and claim that the first attempt was rolled back.

Acceptance covers callback failure, journal conflict, failure after the second
SQL write, lost acknowledgement/reopen/replay, worker observation of committed
destination state, close racing an admitted transaction, rejected post-close
mutations, and process exit after an uncommitted SQL write or after commit but
before dispatcher startup. This is process-crash coverage, not power-loss
certification or application deployment acceptance.
