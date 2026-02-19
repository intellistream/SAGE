# sage-kernel Test Taxonomy (Issue #1440)

This package uses a **3-layer test taxonomy** for Flownet migration boundaries.

## Directory convention

- `tests/declaration/`

  - Declaration-layer unit tests.
  - Scope: flow graph declaration, validation, schema/type contracts, context propagation
    declarations.
  - Must run **without** runtime backend dependency.

- `tests/contract/`

  - Facade/API contract tests.
  - Scope: user-visible API signatures and behavior (`create/submit/run/call` semantics, error
    contracts).
  - Must remain backend-agnostic.

- `tests/adapter/`

  - SAGE-to-Flownet adapter integration tests.
  - Scope: protocol conformance and adapter boundary behavior.
  - Live runtime tests may be `skipif`-guarded when `sageFlownet` is unavailable.

## Where to add new tests

- New declaration DSL/type validation behavior → `tests/declaration/`
- New public facade behavior/signature contract → `tests/contract/`
- New protocol/adapter mapping or Flownet bridge behavior → `tests/adapter/`

## CI mapping

The workflow `.github/workflows/ci-flownet-layer-tests.yml` runs these three layers as independent
jobs:

1. Layer 1 — Declaration
1. Layer 2 — Contract
1. Layer 3 — Adapter

A failure in any layer blocks merge and exposes boundary regressions early.
