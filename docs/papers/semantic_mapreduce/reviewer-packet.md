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
evidence, candidates, and scorer; the difference is the reducer contract.

**Why not ordinary JSON mode?**

JSON mode can improve syntax, but it does not guarantee that the required
decision field is present, that evidence IDs are legal, that candidate edits
preserve the incident unit, or that unsafe edits are rejected. The paper's
mechanism removes JSON construction from the model-facing path and turns
invalid text into bounded action uncertainty.

**Does validator/fallback hide that the LLM contributes little?**

No. The artifact reports accepted edit count, fallback count, invalid action
count, invalid schema count, support recall, latency, tokens, and per-case F1.
In the current hardcase probe, the validated action reducer records accepted
edits and zero fallback. If future runs fall back, that should be reported as a
negative result rather than folded into a success claim.

**Are three workload seeds enough?**

They strengthen the controlled mechanism claim but do not establish stochastic,
cross-model, or production robustness. The nine case/seed runs come from a clean
parent commit with full endpoint/submodule manifests: action-validated reaches
0.9301 mean F1 versus 0.7204 for `hybrid-hint`, disconnected merge is F1 1.0
for every seed, overmerge never regresses, and invalid/fallback counts are zero.
Production-trace replay and repeated model samples remain follow-up evidence.

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
- The live result covers three controlled workload seeds on one model/endpoint;
  it should not be described as stochastic, cross-model, or production generality.
- The prototype does not replace Spark, Flink, Ray, databases, observability
  tools, LangGraph, LlamaIndex, or data+AI platforms.
