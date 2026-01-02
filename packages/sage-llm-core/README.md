# SAGE LLM Core (L1)

Foundation package for SAGE's LLM and embedding control plane. This package will host the unified
inference client, scheduling control plane, and related utilities after the flag-day refactor.

- Layer: L1 (Foundation)
- Responsibilities: Control plane logic, unified inference client, shared LLM/embedding utilities
- Dependencies: Reuses foundation utilities from `isage-common`

## Status

This package is scaffolded as part of the flag-day refactor (Option A). Functionality will be moved
from `sage.llm` into this namespace.
