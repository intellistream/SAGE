# Native conditional branches and merge

Application graphs can branch using captured, stable decisions and SAGE's native
`filter` operators, then `connect` selected outputs into a shared `map`, `filter`
or `process` continuation. SAGE owns scheduling, cancellation and request-chain
accounting. Applications must not implement a second executor to achieve this.

`ConnectedStreams._apply` attaches inherited operators to every connected upstream.
Composing a single stream with connected streams, or two connected groups, keeps
all upstreams; connected groups are recognized before the broader DataStream type.
The merge forwards each emitted item, not a barrier join or deduplication service.
Exclusive routes must therefore use complementary predicates over the same
captured decision. Do not base the predicates on mutable state which another
branch can change before its sibling predicate evaluates.

The native regression covers one selected side effect, zero rejected side effects,
one common render, graph reuse and clean request accounting. A separate composed
merge verifies all five upstreams and an empty filtered result. Existing parallel
request and execution-observation regressions qualify cancellation and parentage.

This does not add automatic retries or make external effects exactly-once.
Applications still need destination idempotency, cancellation fences and durable
receipt handling for effects such as booking or sending notifications.
