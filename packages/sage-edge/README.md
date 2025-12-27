# SAGE Edge (L6 Aggregator)

Minimal FastAPI shell for mounting the LLM gateway with optional prefixing.

- Default behavior mounts the LLM gateway at `/`, keeping `/v1/*` endpoints stable.
- Optional `llm_prefix` (env/CLI) mounts the gateway under a custom path while preserving `/healthz`
  and `/readyz` at the edge level.
- Edge health endpoints live at `/healthz` and `/readyz` regardless of mount path.
- Uses `SagePorts.EDGE_DEFAULT` as the default port and respects XDG user paths for logs/PID files.

## Quickstart

```bash
# Start in foreground (mount gateway at /)
python -m sage.edge.server --port 8899

# Start with prefix
python -m sage.edge.server --port 8899 --llm-prefix /llm
```

## Design Notes

- No backward-compat shims: imports should use `sage.llm.gateway` directly.
- Uses `get_user_paths()` for runtime state and logs (no `~/.sage` usage).
- Intended as an opt-in shell; runtime behavior only changes when the edge server is started.
