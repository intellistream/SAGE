# Runtime API Layering Policy (Facade + Advanced Environments)

- Version: 2026-02-20
- Scope: SAGE public runtime programming interfaces
- Related issues: intellistream/SAGE#1446, intellistream/sageFlownet#14

This document defines the canonical runtime API layering in SAGE:

1. **Facade API (default tier)** for most users
2. **Advanced Environment API (expert tier)** for low-level runtime control

`LocalEnvironment` and `FlownetEnvironment` are **public advanced APIs**, not legacy/deprecated APIs.

---

## 1) Layering and Positioning

### Tier A: Facade API (default)

- Entry points: `sage.kernel.facade.create`, `submit`, `run`, `call`
- Target users: most application developers
- Contract: stable, backend-agnostic user semantics
- Recommendation: first choice for new app-level code

### Tier B: Advanced Environment API (expert)

- Entry points: `sage.kernel.api.LocalEnvironment`, `sage.kernel.api.FlownetEnvironment`
- Target users: advanced users needing low-level execution control
- Contract: public and supported, with shared semantic invariants
- Recommendation: use when environment-level control is required

---

## 2) Shared Semantic Invariants (Must Match)

Across facade and environment tiers, the following semantics must not drift:

- submit/call lifecycle meaning
- result retrieval and completion behavior
- cancel behavior and terminal states
- error propagation/classification surface
- resource declaration handoff semantics

Differences are allowed only for explicit runtime capability controls at the advanced tier.

---

## 3) Public Symbol Ownership Mapping

| Symbol | Tier | Owner Layer | Owner Package | Stability |
|---|---|---|---|---|
| `create` | Facade | L3 | `sage-kernel` (`sage.kernel.facade`) | Stable |
| `submit` | Facade | L3 | `sage-kernel` (`sage.kernel.facade`) | Stable |
| `run` | Facade | L3 | `sage-kernel` (`sage.kernel.facade`) | Stable |
| `call` | Facade | L3 | `sage-kernel` (`sage.kernel.facade`) | Stable |
| `LocalEnvironment` | Advanced | L3 API / L2 protocol / runtime backend | `sage-kernel` + L2 protocol contracts | Advanced Stable |
| `FlownetEnvironment` | Advanced | L3 API / L2 protocol / Flownet runtime core | `sage-kernel` + `sageFlownet` runtime | Advanced Stable |

Notes:

- SAGE owns declaration/API/protocol abstraction layers.
- Flownet owns runtime core implementation.
- No shim/re-export compatibility layer should be introduced for migration work.

---

## 4) Enforcement Checklist (For PRs touching runtime API)

- Do not label environment APIs as legacy/deprecated.
- Keep facade and environment semantics aligned with contract tests.
- Keep runtime core logic in Flownet runtime repository.
- Route cross-backend behavior through protocol contracts (Protocol/ABC), not backend internals.

---

## 5) Change Management

- Breaking changes on facade tier require explicit migration notes.
- Advanced tier extension is allowed, but must preserve shared semantic invariants.
- Any contract-level change requires coordinated updates in:
  - SAGE contract tests
  - sageFlownet conformance tests
  - SAGE-Docs runtime API documentation
