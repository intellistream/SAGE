# SAGE LLM Gateway (L6)

OpenAI/Anthropic compatible API surface for the SAGE LLM stack. This package will host the FastAPI
app, adapters, and control-plane-facing endpoints once the flag-day refactor migrates code from
`sage-gateway` to the new `sage.llm.gateway` namespace.

- Layer: L6 (Interface / Gateway)
- Responsibilities: OpenAI-compatible routes, engine management endpoints, session/memory boundary
- Dependencies: `isage-llm-core`, `isage-common`

## Status

Scaffolded as part of Task A (Option A flag-day). Implementation will be moved from the legacy
`sage-gateway` package in subsequent tasks.
