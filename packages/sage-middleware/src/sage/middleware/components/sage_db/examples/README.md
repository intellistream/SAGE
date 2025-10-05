# SageDB Python Examples

These lightweight scripts demonstrate how to interact with the rebuilt SageDB core (vector store + ANNS plugins) directly from Python.

## Prerequisites

1. Install the SageDB native extension (run once per environment):
   ```bash
   sage extensions install sage_db  # append --force to rebuild if needed
   ```
2. Ensure the repository root is on your `PYTHONPATH` (each script does this automatically by appending `packages/`).

## Included demos

| Script | Highlights |
|--------|-----------|
| `quickstart.py` | Minimal add/search/update/save cycle with metadata and persistence checks. |
| `faiss_plugin_demo.py` | Shows how to opt into the FAISS backend, tune build/query parameters, and gracefully fall back if FAISS is unavailable. |

Run any script from the repository root, e.g.:
```bash
python examples/sage_db/quickstart.py
```

> Both scripts print step-by-step progress so you can follow the state changes inside the vector store.
