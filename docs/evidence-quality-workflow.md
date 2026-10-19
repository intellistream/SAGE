# Native evidence quality workflow

`sage.runtime.evidence_workflow.EvidenceWorkflowRuntime` is a single persistent
native flow for read-only evidence work. Applications supply request-scoped
`assess`, `supplement`, `compose` and `review` ports, not another scheduler.

The flow is:

1. Assess coverage against the complete question and authorized source snapshot.
2. Route only missing evidence through one supplement round and fresh assessment.
3. Compose a source-constrained plan; mapped witnesses may not disappear from
   the selected factual source set.
4. Research requests execute a separate proposal review. Ordinary factual
   requests do not incur this model stage. Review cannot change factual sources.
5. Verify exact source rendering and render any remaining evidence gaps as
   original question spans, explicitly not negative factual conclusions.

Native observations expose these actual decisions, nodes and call relationships.
The complete declared graph includes inactive repair/research branches. A
completed condition is not evidence that its branch was selected.

## Evidence contract

`prepare_coverage` requires non-overlapping contiguous spans partitioning EVERY
character of the question. `question_requirements` supplies conservative
syntactic sentence/list units; it does not claim semantic decomposition. Adapters
with a qualified parser may supply finer partitions. Qualifiers, references and
the full original question remain available to the assessor in every case.

The assessor returns exactly one receipt per requirement, bound to a digest of
the question, spans and complete sources. Witnesses are exact nonempty substrings
of authorized source IDs. Unknown IDs, dropped requirements, altered source text,
forged/stale receipts, duplicated JSON fields and unwitnessed prose are rejected.
Requests are rebound to their canonical content during validation. No snippets,
document truncation, response budget lowering or source mutation is used.

An exact witness proves provenance, NOT entailment or independent truth. The
model's relevance/completeness assessment still needs real-question qualification.
Never advertise a coverage receipt as a guarantee that the answer is correct.
Research proposals likewise remain labeled prospective inferences, not facts.

## Adapter obligations

The immutable adaptive plan distinguishes `evidence_required` (an explicitly
source-constrained request) from opportunistic knowledge retrieval. Empty Wiki
retrieval must not disable ordinary advice or a caller's own conversation memory.
Conversely, denied/empty explicitly requested sources must not silently turn into
unconstrained factual generation. Resolved/business turns remain resolved.

- Supply only sources visible to the verified caller. Every supplement search
  and document hydration must reapply the same captured identity and source scope;
  question/model text must never widen permissions. There are no write ports.
- Supplement accepts only missing original question spans and returns immutable
  `PlanSource` records. Conflicting reuse of a source ID is rejected. The runtime
  preserves all existing sources rather than replacing them with an abstract.
- `assess(request)` returns coverage JSON; `compose(request, assessment)` returns
  source-plan JSON; `review(request, plan)` returns reviewed source-plan JSON.
  Fact selection is unchanged by review. These ports must use configured models
  and auth helpers without logging credentials or private request payloads.
- Respect the caller's remaining deadline. Native child requests inherit
  cancellation. No business writes are replayed, and gaps do not start an
  unbounded search/generation loop.

Structured child failure types survive the parent native flow boundary, so a
permanent validation rejection cannot become a generic retryable generation
failure simply because a quality subflow was introduced.

This module's synthetic unit/integration fixtures do not qualify real model
quality, live ACL behavior, application integration or production deployment.
