# Complete bounded Markdown delivery plans

Install `isage[delivery-markdown]` (also included in development dependencies).
`sage.runtime.markdown_delivery.plan_markdown(source, max_chars=...)` builds
immutable self-contained CommonMark/GFM frames. There is no model, transport,
worker, app monkeypatch, retry loop or summary fallback in this module.

The planner parses the **entire** source, indexes Unicode grapheme content units,
and covers them with consecutive, non-overlapping intervals. It projects the
selected syntax tree, preserving complete link destinations, formatting and
container nesting. A pinned maintained mdformat renderer reconstructs valid
Markdown, reference definitions and code fences. An independent parse of each
rendered frame must match its projected visible text, formatting, links, code
and table-column positions before any plan is returned. Unknown/unrenderable
structure, content drift or an indivisible construct exceeding the bound fails
explicitly before delivery. There is no slicing/truncation fallback.

Bounds count UTF-16 code units conservatively, so supplementary characters
cannot exceed receivers that count that way. Individual graphemes are never
cut. Total source/answer length is not capped by this per-frame bound. A full
destination URL or table header that cannot fit even one content unit requires
an explicit transport/product decision; it is not shortened or silently removed.

This is **not byte-identical source serialization**. Canonical source is
unchanged and identified by SHA-256. Markdown markup/whitespace is normalized,
styles and container markers reopen in later frames, table headers can repeat,
and closing code fences require a framing newline. Code whitespace is checked
apart from that framing newline; ordinary inter-word whitespace can normalize
at message boundaries. HTML is rendered literally, not executed. The optional
`literal_tokens` tuple protects exact platform control strings as inline code
in text nodes, without rewriting existing code or link destinations.

Before the upstream generation step is acknowledged, the consuming application
must put the already planned transport payloads into `DeliveryPlan.to_dict()`
and its owner-scoped durable result. Delivery retries restore those same inputs
with `DeliveryPlan.from_dict()`: never regenerate, reformat or repartition after
partial acceptance. Receipt storage remains metadata-only. Formatting does not
authorize a destination or prove that a real client rendered a frame.

Initial source qualification: 257 related runtime tests passed (24.60 seconds),
including 31 Markdown cases. Coverage includes long captions retaining full
reference URLs in every referencing frame, independent full text/code
reconstruction, long table cells and empty column positions, nested and numbered
lists, multiline styles, code fencing, Unicode graphemes, literal control tokens,
and deliberate renderer text/link/style corruption. Ruff and diff checks pass.
Installed-package and actual application/transport acceptance remain separate.

Runtime revision `4c4abffe` was then installed in a **fresh** virtual environment
from the owned Git mirror, whose exact commit matched the published main ref.
Installing the declared `delivery-markdown` extra plus pytest/pytest-asyncio
resolved only 16 packages; no Twin, NeuroMem, SageVDB or existing app environment
was borrowed. The same 257 installed-package tests passed in 24.84 seconds from
`/tmp`, with PYTHONPATH removed and user-site imports disabled. Module location
and VCS revision were verified in site-packages. This also exercised a newer
compatible regex wheel (2026.9.29 rather than the source fixture's 2026.7.19).
This verifies the packaged capability and declared dependencies, not Twin
adoption, real Slack rendering, recipient visibility or production promotion.
