# Durable active-request capacity

`WorkJournal.configure_capacity(max_active_requests=N)` installs a namespace-wide
persisted capacity policy. This is an **offline maintenance operation**: stop all
admission and worker processes for that namespace, including older versions,
before calling it. It scans existing records, then seeds the policy in a single
transaction. The scan is not an online snapshot. Live leases and a limit below
the existing backlog reject configuration without changing records.

After configuration, direct commits and `PreparedWorkCommit.slots/apply` include
the policy slot in the same backend transaction as the result, active index and
application destinations. SQLite serializes independent-process admissions.
`WorkCapacityError` means the attempted new active request was not committed;
callers must expose explicit overload/backpressure, not report it as accepted.

The limit counts requests with at least one pending/running task, including
delayed retries and settled finalizers. It does not limit payload bytes, tasks
within a request, retained history, or external model concurrency. It is not a
throughput or fairness guarantee. Different namespaces have independent quotas.

Identical replay does not consume an additional slot. The last terminal task
releases capacity atomically without deleting the result or task history.
Terminal failure with pending settled finalizers does not release capacity until
those finalizers finish. Recovery uses the same persisted policy; no process-local
counter or startup reset is used. External effects remain at-least-once.

Capacity-enabled records use version 6 so older workers reject their mutation.
This is not a substitute for stopping older writers: an old binary could still
admit a new request without understanding the namespace policy. Rollback requires
a matching state/code migration, not a live mixed-version deployment.
Unconfigured namespaces retain existing behavior; no policy is silently enabled.
No TTL or automatic deletion is introduced.

Qualification: `src/tests/test_work_capacity.py` covers independent-process
contention, prepared transaction rollback, offline migration, retained replay,
settled finalizers, restart, missing policy failure and process exit before commit.
Application integration and production capacity selection remain separate gates.
