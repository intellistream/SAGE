# Bounded Semantic-Reduce Edit Runtime Contract (v2 Draft)

Status: executable design contract for the mechanism-completion phase. This is
not evidence that v2 has run online. Historical online artifacts were produced
by the legacy merge-only pairwise action implementation.

## State machine

1. **H0** — An explicitly configured `base_reducer` consumes observable
   evidence and produces a legal, evidence-linked candidate state. The runtime
   canonicalizes that state, assigns stable candidate IDs, and records the H0
   and evidence digests. The policy sees this exact H0.
2. **Catalog** — The runtime deterministically constructs a finite catalog from
   H0 and observable evidence only. It contains typed KEEP, MERGE, SPLIT, and
   ABSTAIN proposals. A proposal records its generator and exact consumed and
   produced evidence partition. Catalog order and budget are fixed; identical
   canonical inputs produce byte-equivalent catalogs.
3. **Select** — A deterministic or model policy receives the same H0 and catalog
   and may return only catalog proposal IDs (or bounded aliases such as `A0`).
   It cannot generate candidates, hypothesis fields, evidence IDs, or split
   partitions. Malformed or unknown output is an invalid selection, not KEEP.
4. **Validate** — The system checks proposal existence; unique candidate
   consumption; action conflicts; evidence conservation and unique ownership;
   non-empty split parts; no foreign evidence; schema; root and affected-service
   eligibility; and batch atomicity. Sequential merge-then-split and
   split-then-merge are unsupported in one batch because proposals are defined
   only over H0; consuming the same H0 candidate twice is a conflict.
5. **Commit** — The batch is atomic. If every selected proposal is valid, the
   runtime applies all state-changing edits once and carries unconsumed H0
   candidates forward to H1. Any invalid selection or edit rolls the entire
   batch back to byte-equivalent H0. ABSTAIN and an empty catalog also preserve
   H0, but have distinct outcomes. KEEP is a validated per-candidate no-op.
6. **Trace** — The runtime records contract/version, configured H0 reducer,
   evidence/H0/catalog/selection/H1 digests, catalog budget/truncation, selected
   proposal IDs and typed actions, validator acceptance/reason codes, commit
   outcome, action/state-change counters, fallback reason, checkpoint ID, and
   replay ID. Checkpoint restore must reproduce the pre-commit H0 digest;
   independent replay must rebuild the same catalog, selection digest, and H1.

## Typed action semantics

### `KEEP(candidate_id)`

- Consumes no candidate for mutation and changes no state.
- The referenced H0 candidate must exist.
- Evidence ownership and all candidate fields remain byte-equivalent.
- Counted separately from ABSTAIN, empty catalog, and invalid selection.

### `MERGE(left_id, right_id, proposal_id)`

- Both distinct H0 candidates must exist and be otherwise unconsumed.
- Only a cataloged pair is legal.
- The produced hypothesis evidence is exactly the set union of both source
  candidate evidence sets; no omission, duplication, or foreign evidence.
- Root and affected services are deterministically rebuilt from that evidence
  and validated against observed services and non-null upstream hints.

### `SPLIT(candidate_id, split_plan_id)`

- The H0 candidate and cataloged plan must exist and be otherwise unconsumed.
- A plan has at least two non-empty parts.
- Part evidence sets are pairwise disjoint and their union exactly equals the
  source candidate evidence set; no source-external evidence is legal.
- Every output part is deterministically rebuilt and individually passes schema,
  root, affected-service, and provenance validation.
- The policy selects only the plan/proposal ID. It never supplies evidence lists.

### `ABSTAIN`

- Expresses that the policy proposes no modification and preserves H0.
- It is recorded distinctly from KEEP, no proposal, invalid output, validation
  rejection, and request failure.
- ABSTAIN cannot be combined with another proposal in one batch.

## Deterministic catalog generation

All generators ignore `scenario`, `source_incident_id`, hidden incidents, and
scorer callbacks. Inputs are canonicalized by observable evidence content and
IDs only for stable references.

- **MERGE**: enumerate legal distinct H0 candidate pairs in canonical order,
  retaining exact union evidence and a bounded deterministic affinity/rule
  annotation. Deterministic and model selectors receive this same list.
- **Conflicting-hint SPLIT**: when a candidate contains at least two distinct
  non-null upstream hints, partition evidence by hint; evidence without a hint
  forms a deterministic residual part rather than being dropped.
- **Temporal-gap SPLIT**: sort candidate evidence by interval and stable evidence
  key; create a partition at an obvious fixed-threshold gap, preserving every
  item on exactly one side.
- **Topology-disconnected SPLIT**: form the undirected induced service graph from
  the fixed observable service topology and partition evidence by disconnected
  components. Do not fabricate a plan when fewer than two non-empty components
  exist.

Duplicate partitions produced by multiple rules are deduplicated by canonical
partition digest while retaining deterministic generator provenance. Budgets are
applied after canonical sort and traces record total, retained, and truncated
counts by action/rule.

## H0, fallback, and outcomes

Fallback always means “retain/rebuild the configured H0,” never invoke a
different reducer. The H0 digest in the trace is the state the policy actually
saw. Required outcomes are:

- `committed-edits`: at least one valid MERGE or SPLIT changed state;
- `committed-keep`: valid KEEP-only selection, H1 equals H0;
- `preserved-abstain`: explicit ABSTAIN, H1 equals H0;
- `preserved-no-proposal`: no selectable proposal, H1 equals H0;
- `rolled-back-invalid-selection`: malformed/unknown/conflicting selection;
- `rolled-back-validation`: cataloged selection failed an invariant;
- `preserved-request-failure`: selector request failed;
- `legacy-merge-only`: verifier label for frozen v1 artifacts only.

Successful no-op outcomes are never counted as accepted state-changing edits.

## Fair evaluation boundary

H0/no-edit, deterministic selection, and model selection share the byte-identical
H0 and catalog. A proposal oracle may use hidden ground truth only after catalog
construction to measure reachability and is labeled diagnostic/oracle. The
constrained-agglomerative reducer remains a strong full-evidence reference with
evidence-level reclustering permission; results must state that its input and
permission differ from bounded H0 editing.

## Historical compatibility

The frozen 2026-07-18 online action artifacts remain immutable and readable as
`semantic-reduce/v1` / `legacy-merge-only`. Their SPLIT enum advertised an
unimplemented branch and their `split_count` is therefore zero. A v2 verifier
must not infer executable SPLIT from the enum list or rescore old responses as
new real-online evidence.
