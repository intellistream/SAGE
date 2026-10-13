# Bounded Qwen3.8 adversarial review and primary verification

The first source-only request used the existing `qwen38` profile
(`Qwen/Qwen3.8-27B`, `sage_qwen38`) and a 32,782-byte prompt. No tools were requested.
It returned no review for approximately 12 minutes and was interrupted. There was
no observed HTTP, Responses tool-protocol, or explicit context-limit error; the
cause of the delay was not established. It is not counted as a successful review.

The same profile completed a retry using a 2,685-byte verified evidence prompt,
no tools, and a four-finding/600-word bound. This reduced the input far below the
profile's intended 32K context. Authentication remained on the existing command
path; no credentials were read or copied. The primary Codex verified each finding
against current source and deterministic tests rather than accepting severity labels.

| Finding | Primary verification | Disposition |
| --- | --- | --- |
| F1: `record_error` races with `end` | A late writer can change status between `span_end` and `trace_end`, producing contradictory terminal records. Python string assignment does not create a partially written enum, and the review incorrectly said the old end read was locked. | Fixed: terminal status freezes under the end lock; late errors cannot rewrite it. A concurrent writer after the first terminal emission is a regression test. |
| F2: post-close loss is not counted | Rejected as stated: the old closed branch already incremented `dropped_events`. A root end attempts three records, so the suggested “exactly one” assertion was also incorrect. Independent inspection found a different real race: close could let the worker exit after the closed check but before enqueue. | Fixed the independently reproduced race by serializing close and admission. A paused enqueue/parallel close test proves every accepted record drains; all three later root records count as drops. |
| F3: purge races with reads; mtime order invalidates timing | A segment can disappear between directory listing and open. This was independently reproduced and fixed before the retry returned. Mtime ordering does not invalidate ID-paired monotonic spans; reversed-input native importer tests pass. A partial tail is held pending, not accepted as torn JSON. | Reader tolerates purged directory segments. Additionally, independently verified two-writer budget overshoot (18,002 bytes against a 16,384-byte cap) led to nonblocking POSIX directory locking. |
| F4: burst and abrupt-exit loss | The measured burst losses are real and explicitly reported. A daemon queue cannot promise durable accounting after `os._exit` or a crash without a different synchronous durability contract. The suggested all-events-or-durable-count crash assertion exceeds this best-effort design. | Retained as an explicit limitation: process-local counters and exported receipts are lower-bound evidence; crash/forced exit can lose queued events and final counters. No lossless throughput or crash-durability claim is made. |

No hidden reasoning capture was introduced. The peer review did not establish a
new secret leak in the bounded summary/HMAC path; trusted application labels remain
an explicitly documented API boundary, not a general secret sanitizer.
