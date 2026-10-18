# Read-only state storage observation

`sage.runtime.state_storage_report.inspect_sqlite_state(path)` reports counts and
byte totals for an existing SAGE SQLite state database. It does not deserialize
values, return identifiers or payloads, or alter retention/admission policy.
Use `dataclasses.asdict(report)` for a content-free structured observation.

SQLite entry/blob/page counters share one read transaction. WAL size and free
filesystem space are advisory observations, not an atomic reservation. Logical
payload bytes, allocated pages, reusable pages and WAL bytes are distinct metrics;
do not sum payload bytes with allocated page bytes as if both were disk usage.
The largest blob is a stored snapshot, not necessarily an individual event.

Missing databases fail without creation. Invalid schemas and access failures are
errors, not healthy empty stores. The connection uses `mode=ro` and `query_only`;
no checkpoint, vacuum, TTL, pruning or replay truncation is performed.

WorkJournal and EventJournal retain canonical results and replay events unless
the application explicitly performs a separately authorized migration. An active
request limit does not bound retained disk usage. Operators must observe storage
growth and provision capacity; a full filesystem is not permission to delete
answers or reuse request identities. This API does not implement automatic alerts,
archival, backups, deletion, or a hard storage admission reservation.

Tests cover byte accounting, opaque/non-pickle values, missing/invalid stores,
preserved replay across reopen, and completed records surviving time advancement
and new work admission. They do not establish throughput or retention-at-scale.
