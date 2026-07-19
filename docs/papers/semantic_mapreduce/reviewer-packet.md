# Semantic MapReduce Reviewer Packet

## 2026-07-19 Mechanism-Completion Update

This packet is not a submission-readiness attestation. The frozen real-online
action result is historical merge-only v1. Its H0 is `semantic-graph`; hybrid is
a comparison/fallback. Runtime v2 implements true cataloged SPLIT and atomic
rollback offline. Its clean held-out matrix has 40 units, 36 oracle repairs,
and improving merge/split proposals in 29/14 units, but has no online model
result. The strongest fair v2
question is proposal coverage and selector quality under identical H0/catalog
input, not whether the model beats a full-evidence reclustering reference.

The exact v2 real-online protocol is now frozen and request-ready at SHA
`8e760c7c4e716bfdcdfdde656fab62d17d98e664fe5877df0be2b919f6d0934e`
with three independent SIGN envelopes. It has not been granted or executed;
old v1, offline, replay, simulation, projected, and derived evidence cannot
substitute. Any future claim must come from its canonical final closure.

This one-page packet records the submission-facing answers that should remain
consistent across the paper, rebuttal notes, and talks.

## Core Claim

Semantic MapReduce is an operator contract for evidence-linked semantic
reduction over partitioned observations. Its key contribution is not calling an
LLM from a data workflow; it is separating `SemanticReduce`, bounded `Edit`,
system-owned `Validate`, and `ReportTrace` so that model decisions are
auditable, rejectable, and fallback-safe.

## Likely Reviewer Questions

**Is this just prompt engineering?**

No. In runtime v2 the system builds a finite catalog containing legal KEEP,
MERGE, and evidence-partitioning SPLIT proposals plus ABSTAIN. A policy returns
proposal IDs only; the system binds evidence, checks schema/root/affected
eligibility and unique ownership, and commits the whole batch or preserves the
exact H0. Historical online v1 exposed the four enum words but executed only
MERGE as a state change, so it is not evidence for true SPLIT.
The comparison against free-form pairwise JSON uses the same endpoint, model,
evidence, candidates, and scorer; the difference is the reducer contract. The
paper's concrete reducer-lifecycle figure makes this executable boundary
explicit across admit, reduce, select, propose, assemble, validate, publish,
reject, recover, and trace; the model owns only the single enum proposal.

**Did the live model path itself demonstrate checkpoint recovery?**

No. The 27-row model-free runtime-contract matrix directly exercises commit,
reject, baseline preservation, checkpoint restore, and deterministic replay.
The real-online path archives compatible candidate, evidence, and committed-
state digests plus commit/preserve outcomes. This separates runtime recovery
semantics from model quality and does not claim distributed exactly-once.

**Why not ordinary JSON mode?**

JSON mode can improve syntax, but it does not guarantee that the required
decision field is present, that evidence IDs are legal, that candidate edits
preserve the incident unit, or that unsafe edits are rejected. The paper's
mechanism removes JSON construction from the model-facing path and turns
invalid text into bounded action uncertainty.

**Does validator/fallback hide that the LLM contributes little?**

No. The artifact reports accepted edit count, fallback count, invalid action
count, invalid schema count, support recall, latency, tokens, and per-case F1.
In the full five-sample probe, the validated action reducer records accepted
edits and four unparsable strings mapped fail-closed to `ABSTAIN`/no-op, with
zero validator rejections, schema failures, or fallback. Parser uncertainty
remains visible in the trace rather than being folded into success.

**Are three workload seeds enough?**

They strengthen the controlled mechanism claim but do not establish broad
cross-model or production robustness. The primary run repeats all nine
families, three seeds, and three reducers five times from a clean parent commit.
At candidate budget 8, historical merge-only action reaches 0.8645 mean F1
versus 0.7801 for the separately evaluated `hybrid-hint`; a paired bootstrap
over the 27 scenario--seed means gives delta `+0.0844`, 95% CI
`[0.0328,0.1449]`. This is not its pre-edit baseline and not the strongest
reference. Matched constrained is 0.9028, and action records 3 wins, 15 ties,
and 9 losses. A same-family 14B checkpoint with
three repeats reaches 0.8392 versus 0.7801, delta `+0.0591`, CI
`[0.0147,0.1149]`. This is a second scale check, not cross-family robustness.

**Is the workload toy?**

The workload is controlled, not a production trace replay. Its purpose is to
isolate semantic-reduction behaviors that alert/window benchmarks do not expose:
fragmented evidence, missing root evidence, false correlation, overmerge, and
ambiguous pair decisions. The paper should not claim production generality until
public or production-derived telemetry is replayed through the same evidence
schema and coverage gate.

## Claims To Keep Narrow

- Existing systems can serve as substrates; the missing abstraction here is the
  evidence-linked semantic reducer contract, not another execution engine.
- The live result covers temperature-zero samples at two checkpoints in one
  model family; it should not be described as broad stochastic, cross-family,
  or production generality.
- The prototype does not replace Spark, Flink, Ray, databases, observability
  tools, LangGraph, LlamaIndex, or data+AI platforms.

## Frozen Review Evidence

The replacement anonymous 1,329-file bundle contains the five-sample primary matrix, 243 raw
same-family second-scale reports, the label-conditioned external reducer replay,
the 27-row supplied-checkpoint runtime-contract matrix, the 40-unit v2
development/held-out matrices, and the 540-row controlled baseline matrix. It
bundles a standard-library verifier and passes a safe fresh extraction. Its
archive checksum and every
submission-facing number/scope literal pass the artifact and submission-claim
verifiers. This supports the bounded runtime-operator claim only; it does not
remove the cross-family, non-oracle external MapEvidence, or production gap.
