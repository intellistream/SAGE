# LLM Preset Launcher Design

## Goals

- Provide a zero-config way to start a bundle of LLM + embedding engines with a single CLI command.
- Encode engine metadata (runtime kind, labels, GPU needs) so the control plane can reason about
  mixed workloads.
- Keep implementation incremental: reuse existing `/v1/management/engines` endpoint instead of
  inventing a new orchestrator.

## Key Concepts

### Engine Kind

The control plane now distinguishes between two runtime kinds:

| Kind        | Runtime Process                                          | Scheduling impact                                             |
| ----------- | -------------------------------------------------------- | ------------------------------------------------------------- |
| `llm`       | `vllm.entrypoints.openai.api_server`                     | Serves chat/completion requests, requires GPU budget          |
| `embedding` | `sage.common.components.sage_embedding.embedding_server` | Serves embeddings only, can run CPU-only (no GPU reservation) |

Engine metadata is recorded with `engine_kind` so that routers/CLIs can surface the correct
information.

### Preset Definition

Presets are simple YAML descriptors that enumerate the engines we want to launch:

```yaml
version: 1
name: qwen-plus-embeddings
engines:
  - name: chat
    kind: llm
    model: Qwen/Qwen2.5-7B-Instruct
    tensor_parallel: 2
    pipeline_parallel: 1
    label: chat-primary
    max_concurrent_requests: 512
    metadata:
      traffic_class: production
  - name: embed
    kind: embedding
    model: BAAI/bge-m3
    port: 8090
    label: embed-default
    metadata:
      traffic_class: production
```

Fields:

| Field                     | Required | Notes                                                |
| ------------------------- | -------- | ---------------------------------------------------- |
| `name`                    | ✅       | Friendly ID, used for logs/CLI only                  |
| `kind`                    | ✅       | `llm` or `embedding` (defaults to `llm`)             |
| `model`                   | ✅       | Model identifier passed to control plane             |
| `tensor_parallel`         | optional | Defaults to 1 when omitted                           |
| `pipeline_parallel`       | optional | Defaults to 1 when omitted                           |
| `port`                    | optional | If unset port auto-selection kicks in                |
| `label`                   | optional | Stored on execution instance metadata                |
| `max_concurrent_requests` | optional | Default 256                                          |
| `metadata`                | optional | Arbitrary dict forwarded to `request_engine_startup` |

## CLI Workflow

New command group: `sage llm preset`.

- `sage llm preset list` — lists built-in presets stored under
  `packages/sage-llm-core/src/sage/llm/presets/*.yaml`.
- `sage llm preset show <name>` — prints the YAML (or JSON) so users know what will start.
- `sage llm preset apply <name>` — sequentially calls `/v1/management/engines` for each engine in
  the preset.
- `sage llm preset apply --file ./custom.yaml` — run any custom descriptor.

The CLI handles retries and supports `--dry-run` to print what would be launched.

## Control Plane / API Changes

1. Extend `EngineStartRequest` with `engine_kind` (default `llm`).
1. `ControlPlaneManager.request_engine_startup` already propagates metadata; update it to:
   - Bypass GPU reservation when `engine_kind=embedding`.
   - Register supported request types so routers can target embedding-only instances.
   - Persist `engine_kind` inside `_engine_registry` and include it in `get_cluster_status`
     snapshots.
1. `EngineLifecycleManager` should include the runtime in `get_engine_status()` results for
   transparency.

## Apply Flow

1. CLI loads preset YAML and validates schema (using `pydantic` or ad-hoc checks).
1. For each engine definition, build payload -> `EngineStartRequest` with `engine_kind=kind`.
1. Call `/v1/management/engines`; collect success IDs.
1. Summarize results, showing port/model/kind.

### Failure Handling

- If an engine fails to start, stop the ones that succeeded unless `--no-rollback` is provided.
- Propagate server error messages to the console with clear instructions (missing GPUs, port
  conflicts, etc.).

## Next Steps

1. Finish wiring `engine_kind` across lifecycle + API + CLI (baseline groundwork).
1. Add preset loader + CLI commands.
1. Layer on optional `sage llm preset daemon` later if we want persistent desired state.
