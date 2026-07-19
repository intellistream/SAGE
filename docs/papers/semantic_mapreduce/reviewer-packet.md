# Semantic MapReduce Reviewer Packet

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

No. The model-facing API is an operator boundary. The action reducer lets the
model choose only `KEEP`, `MERGE`, `SPLIT`, or `ABSTAIN` over candidate pairs.
The system assembles the edit, binds evidence identifiers, checks schema and
root/affected consistency, records costs, and falls back if validation fails.
The comparison against free-form pairwise JSON uses the same endpoint, model,
evidence, candidates, and scorer; the difference is the reducer contract. The
paper's ownership table makes this executable boundary explicit across admit,
propose, assemble, validate, publish, and recover; the model owns only the
single enum proposal.

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
edits, four rejected proposed actions, zero schema failures, and zero fallback.
Rejections remain visible in the trace rather than being folded into success.

**Are three workload seeds enough?**

They strengthen the controlled mechanism claim but do not establish broad
cross-model or production robustness. The primary run repeats all nine
families, three seeds, and three reducers five times from a clean parent commit.
At candidate budget 8, action-validated reaches 0.8645 mean F1 versus 0.7801
for `hybrid-hint`; a paired bootstrap over the 27 scenario--seed means gives
delta `+0.0844`, 95% CI `[0.0328,0.1449]`. A same-family 14B checkpoint with
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

The anonymous 693-file bundle contains the five-sample primary matrix, 243 raw
same-family second-scale reports, the label-conditioned external reducer replay,
and the 27-row derived runtime-contract matrix. Its archive checksum and every
submission-facing number/scope literal pass the artifact and submission-claim
verifiers. This supports the bounded runtime-operator claim only; it does not
remove the cross-family, non-oracle external MapEvidence, or production gap.
