# Findings

- Current strongest evidence: 3 workload seeds x 3 hardcases, real-online,
  action-validated F1 0.9301 vs hybrid 0.7204, with zero fallback, invalid
  action, and invalid schema.
- Artifact integrity is no longer the primary submission blocker.
- Primary reviewer risk: the paper may be categorized as data/AI orchestration
  or prompt engineering unless the first two pages foreground a formal operator
  algebra, a bounded Edit/Validate split, concrete runtime integration, and an
  auditable execution contract.
- Current coverage is controlled and mechanism-specific; broader workload
  families are needed before broad robustness or generality claims.
- Before revision, the title foregrounded "Orchestrating LLMs," page 1 had no
  contract visual, and the operator-algebra figure first appeared on page 3.
  Page 2 spent substantial space on prototype/evidence-ladder details.
- The introduction already had the correct ingredients but not the ASPLOS
  causal order: typed state, bounded transition, invariants, recovery, runtime
  integration, then evidence.
- The repository implements nine unique scenario families. Seven share a
  ten-seed derived suite; three ambiguity families have ten-seed diagnostic
  baselines; and three hardcases have three-seed real-online evidence, with
  `ambiguous-overmerge` shared by the last two sets.
- A defensible next coverage gate is all nine families x seeds 7/11/13 under
  one endpoint and three fixed reducers. Success must be per-family contract
  behavior, not merely pooled F1 or zero fallback.
