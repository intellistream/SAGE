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

The caller must durably capture the already formatted destination/payload inputs
before their source step is acknowledged, for example as that step's immutable
result. Reconstruct the same plan from those captured inputs on recovery, not
by regenerating an answer or silently reformatting a partially delivered one.
`DeliveryPlan.to_dict()` exports a detached versioned object for this upstream
result; `DeliveryPlan.from_dict()` verifies the schema and captured fingerprint
without invoking a formatter. The exported object **contains private content**:
it belongs in the protected source result, not logs, public status, or the
metadata-only receipt ledger. Fingerprints provide integrity, not authorization.
Unknown versions or changed bodies/destinations fail explicitly; no legacy
renderer or schema fallback is selected. The receiving app must additionally
validate its expected transport/destination policy on every attempt.
Receipt metadata is not a replacement for that durable canonical input. Changing
formatters while unfinished old plans exist requires an explicit drain/migration
decision; plan conflicts must not reset confirmed receipts.

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

Runtime `bc3879e2` passed 216 related source tests (17.98 seconds) and 216
independent installed-package tests (44.39 seconds), including 14 new delivery
cases. The installed module was loaded from site-packages without PYTHONPATH or
a source overlay. These results do not certify a Markdown boundary planner,
application adoption, payload-format compatibility or actual Slack rendering.
