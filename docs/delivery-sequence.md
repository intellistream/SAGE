# Fenced ordered delivery receipts

DeliverySequence executes inside an existing WorkJournal attempt. It introduces
no worker, scheduler, polling loop, queue, database or lease mechanism. The
existing WorkService/AsyncWorkService retains heartbeat, capacity, retries and
source acknowledgement. The sequence borrows the journal's existing state.

DeliveryPlan captures immutable JSON destination identity and transport payloads
in memory. Applications must finish lossless formatting and platform-bound
validation before calling this primitive. It is not a Markdown converter or
splitter. Do not put credentials, bearer URLs or authentication headers into a
plan; transport ports resolve credentials only when sending. Frame bodies are
detached on access and redacted from repr. Stable part IDs bind sequence
namespace, native source namespace/request/task, destination/content and order.
They remain stable across source retries but do not collapse identical legitimate
requests or different delivery namespaces.

Only plan/part digests, ordered accepted receipts and preparation/source-attempt
counts are persisted. Original payloads, source lease tokens and exception text
are not copied into receipt storage. Source lease validation and receipt state
changes share the same transaction. No external call occurs within a state
transaction. Late/stale workers cannot advance receipt state or acknowledge
source work. DeliverySequence never marks the source task done.

An asynchronous authorization port must return None for permission and raise
for denial; any other returned value is rejected. It runs on every invocation,
including completed replay, and before every part. Authorization does not come
from the opaque delivery ID or source lease. The caller owns recipient/visibility
policy and scope checks on read-only receipt inspection as well.

An external preparation is persisted before calling send. A second concurrent
invocation under the same source attempt cannot send that unconfirmed part again.
Native retry/reclaim must obtain a new source attempt. Confirmed parts are
skipped; immutable plan/destination changes fail before another send. Each send
must return a typed accepted DeliveryReceipt. Rejected or malformed receipts,
storage failure, cancellation and permission loss cannot become completion.
Synchronous storage calls drain through observer cancellation before it escapes.

Preparation counts are not proof that the external API was actually reached.
After crash, timeout or lost external acknowledgement, an unconfirmed part may
already have been accepted. Retrying that part can duplicate an external effect.
Stable IDs allow capable receivers to deduplicate, but the sequence alone is
not an external exactly-once protocol. Local receipt-commit acknowledgement loss
is different: reopening sees that accepted receipt and does not resend it.
Receiver acceptance is not message display, durable retention or user reading.

Qualification includes actual native workers, partial retry/reopen, source lease
expiry, same-attempt concurrency, authorization revocation, receipt rollback and
lost acknowledgement, cancellation during a live SQLite write, and real child
process death after external acceptance but before local acknowledgement. These
prove a platform primitive, not a particular Slack renderer or live deployment.
