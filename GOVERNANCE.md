# SAGE Governance and Stewardship

## Shared Product Identity

SAGE — **Streaming-Augmented Generative Execution** — is the shared flagship
product and technical vision of the IntelliStream research ecosystem. It applies
streaming-computing principles to LLM inference and agent execution.

SAGE is a product boundary, not a fifth research organization. Its public surface
integrates work across agent systems, evolving-data infrastructure, and model
execution while keeping each implementation boundary explicit.

## Core Stewardship

The SAGE core series is hosted under the `RIDE-Lab` GitHub namespace because RIDE
Lab is its principal engineering steward. RIDE Lab maintains the core framework,
agent-facing product surfaces, reviews, releases, and product documentation.

Namespace placement is an operational home, not a claim of exclusive academic or
product ownership. SAGE remains a shared ecosystem product.

## Technical Ownership Boundaries

- **IntelliStream** incubates early cross-layer research until its public
  abstraction, maintainers, evaluation path, and durable home are clear.
- **RIDE Lab** owns agent-native research systems and stewards SAGE core,
  orchestration, RAG, evaluation, studio, and application-facing integration.
- **DataSys** owns framework-neutral stream, graph, vector/index, evolving-data,
  query, lifecycle, and data-system benchmark implementations.
- **vLLM-HUST** owns model execution, KV-cache mechanisms, decode scheduling,
  compilation, kernels, hardware backends, and inference validation.

SAGE consumes DataSys capabilities and calls vLLM-HUST through documented
interfaces. Shared product language never transfers implementation ownership across
these boundaries.

## Decision and Contribution Model

- Decisions remain with the maintainers of the repository that owns the affected
  implementation.
- Cross-boundary changes should define an interface or integration contract and be
  reviewed by maintainers on both sides.
- SAGE product documentation should distinguish shared product vision, core
  stewardship, and dependency ownership.
- Moving a repository between organizations requires a durable ownership change;
  product integration alone is not sufficient.

## Applications

Applications such as [Sage Mate](https://github.com/RIDE-Lab/sage-mate) are built
with SAGE and use vLLM-HUST or another explicitly configured inference service for
model execution. Application placement does not alter SAGE's shared-product status.
