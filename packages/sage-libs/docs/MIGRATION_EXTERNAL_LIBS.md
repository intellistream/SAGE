# sage-libs → Externalized Algorithm Packages

**Goal:** Keep `sage-libs` as a thin interface/registry layer (L3) while heavy implementations live
in independent PyPI packages. This aligns with SAGE layering (no upward deps) and simplifies
updates/versioning per algorithm family.

## Target split (status)

- **ANNS** → `isage-anns` (**DONE**: code lives externally; local tree slated for removal)
- **AMMS** → `isage-amms` (**IN PROGRESS**: interface stays here; impls move out)
- **Agentic** → `isage-agentic` (planned; keep registries + protocol types here)
- **RAG toolkit** → `isage-rag` (planned; retrievers/chunkers/rerankers move out)
- **Privacy/Unlearning** → `isage-privacy` (planned)
- **Integrations** (vector DB / LLM adapters) → slim adapters here; heavy clients as extras or
  separate packages

## Principles

- **Interface-only in this repo**: registries, protocols, type definitions, light utilities.
- **No silent fallbacks**: if an external package is missing, fail loudly with actionable errors.
- **Dependency declarations**: add optional extras to `pyproject.toml`; never manual `pip install`.
- **Layer purity**: no control-plane/gateway deps; stay within L3.

## Work plan

1. **Strip local impls** for ANNS/AMMS and replace with shims that call external packages or raise
   clear `ModuleNotFoundError`.
1. **Public surface audit**: document exported registries/protocols in
   `packages/sage-libs/README.md` and keep `__init__.py` exports minimal.
1. **Extras & testing**: declare optional extras (`anns`, `amms`, `agentic`, `rag`, `privacy`) in
   `pyproject.toml`; adjust CI to install extras where needed.
1. **Docs**: keep migration notes under `packages/sage-libs/docs/` (not root `docs/`).
1. **Cleanup**: delete or archive legacy C++/wrapper code once external packages are verified.

## Next immediate steps

- Replace `anns/` and `amms/` local code paths with thin compatibility shims pointing to
  `isage-anns` / `isage-amms`.
- Refresh `packages/sage-libs/README.md` to describe the externalization model and current status.
- Add explicit error messages to guide users to install the relevant optional packages.
