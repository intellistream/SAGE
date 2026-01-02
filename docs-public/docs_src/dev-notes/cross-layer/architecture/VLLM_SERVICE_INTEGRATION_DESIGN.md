# VLLM Service Integration – Design Proposal

**Date**: 2024-09-20\
**Author**: SAGE Team\
**Summary**: vLLM 服务集成设计，包括 API 封装、配置管理和性能优化策略

## 1. Goals & Requirements

Issue [#809](https://github.com/intellistream/SAGE/issues/809) asks us to promote vLLM from a
standalone CLI launcher to a first-class, blocking SAGE service that can be orchestrated by the
kernel. The target features are:

- Treat vLLM as an in-process (blocking) service that can be registered with
  `LocalEnvironment`/`ServiceManager` and invoked by operators.
- Manage local models via CLI: `show`, `download`, and `delete` operations.
- Provide a SAGE operator/service interface that exposes both generation and embedding tasks through
  the Service API.
- Offer a fine-tuning entry point (initially a stub) so downstream contributors have a stable hook.
- Expose an `execute` interface toward the kernel to schedule vLLM workloads via existing service
  dispatching.
- Legacy `sage llm start/stop/status` commands were removed in Dec 2025; all flows now rely on the
  blocking `sage llm run` interface.

## 2. Current State & Gaps

- `sage tools` (`packages/sage-tools/src/sage/tools/cli/commands/llm.py`) wraps `vllm serve` in a
  subprocess, offering lifecycle management only.
- There is no reusable model registry; model paths are implicit and rely on Hugging Face defaults.
- Middleware lacks a service abstraction for vLLM. Existing services (e.g., `NeuroMemVDBService`,
  `RAGMemoryService`) demonstrate how `BaseService` subclasses should behave, but nothing similar
  exists for LLMs.
- Operators (e.g., `OpenAIGenerator`) talk to HTTP endpoints via the OpenAI-compatible protocol
  instead of first-party services.
- No embedding pathway runs through vLLM today; embedding tasks rely on `EmbeddingModel` factory
  utilities or remote endpoints.

## 3. Proposed Architecture Overview

```
+-------------------------------+
|           CLI Layer           |
|  sage llm (Typer commands)    |
|   • llm model show/download   |
|   • llm model delete          |
|   • llm run (blocking service)|
+---------------+---------------+
                |
                v
+-------------------------------+
|      Shared Model Registry    |
|   sage.common.model_registry  |
|   • Track local model cache   |
|   • Hugging Face downloads    |
|   • metadata.json manifest    |
+---------------+---------------+
                |
                v
+-------------------------------+
|      Middleware Service       |
|  sage.middleware.components   |
|       .vllm.service           |
|   • VLLMServiceConfig         |
|   • VLLMService (BaseService) |
|   • Methods: generate/embed   |
|     show_models/download/etc  |
|   • Fine-tune stub hook       |
+---------------+---------------+
                |
                v
+-------------------------------+
|      Kernel / Operators       |
|  sage.libs.operators / RAG    |
|   • VLLMServiceGenerator      |
|   • VLLMEmbeddingOperator     |
|   • Use call_service(...)     |
+-------------------------------+
```

## 4. Detailed Components

### 4.1 Model Registry (`sage.common.model_registry.vllm_registry`)

Responsibilities:

- Store models under `~/.local/share/sage/models/vllm/<model-id>` (see
  `get_user_paths().models_dir`, configurable via env var `SAGE_LLM_MODEL_ROOT`).
- Maintain a manifest (`metadata.json`) capturing model id, revision, local path, size, last_used,
  and tags (e.g., `{"type": "text"|"embedding"}`).
- Expose Python API:
  - `list_models() -> List[ModelInfo]`
  - `get_model_path(model_id, revision=None)`
  - `download_model(model_id, revision=None, progress=True)` (delegates to
    `huggingface_hub.snapshot_download`)
  - `delete_model(model_id)`
  - `touch_model(model_id)` to update `last_used`.
- Provide exceptions for missing models; these errors should be mapped to user-friendly CLI
  messages.
- The module will live in `packages/sage-common/src/sage/common/model_registry/vllm_registry.py` so
  it can be imported both by CLI and middleware.
- `huggingface-hub` will become an explicit dependency for `isage-tools` (CLI) and is already
  available in middleware.

### 4.2 Middleware Service (`packages/sage-llm-core/src/sage/llm/service.py`)

Key pieces:

- `VLLMServiceConfig` dataclass capturing `model_id`, `engine_kwargs`, `sampling_defaults`,
  `embedding_model_id` (optional), `tensor_parallel_size`, etc.
- `VLLMService(BaseService)` implementing:
  - `setup()` → load configured text model via `vllm.LLM` using local path from registry. If
    missing, raise informative error recommending `sage llm model download`.
  - Internal `_load_embedding_engine()` that either shares the main engine with `embedding=True` or
    instantiates lightweight embedding-only engine (`engine.get_embeddings`).
  - `process(self, payload: dict)` entrypoint handling generic calls from ServiceManager. Expected
    payload shape:
    ```python
    {
        "task": "generate" | "embed",
        "inputs": {...},
        "options": {...},
    }
    ```
  - `generate(self, prompts: List[dict] | List[str], **options)` returning structured responses
    (text + token usage + latency).
  - `embed(self, texts: List[str], **options)` returning embeddings (list of floats per text).
  - `show_models()` returning registry metadata.
  - `download_model(model_id, revision=None)` and `delete_model(model_id)` delegating to registry
    utilities. Downloads trigger hot-reload if `auto_reload=True` in config.
  - `switch_model(model_id, revision=None)` to unload current engines and load new weights
    atomically.
  - `fine_tune(self, request: dict)` stub raising
    `NotImplementedError("Fine-tuning pipeline pending")` but validating payload schema for future
    extension.
- Concurrency & blocking considerations: service runs inside kernel worker threads; generation is
  synchronous. Provide GPU memory guard rails via config values (`max_model_len`,
  `gpu_memory_utilization`).
- Logging: leverage `self.logger` for lifecycle events, note path of loaded models, warn when using
  fallback embedding engines.
- Dependencies: `vllm`, `huggingface-hub`, `numpy`. Guard imports so tests can patch them.

### 4.3 Service Registration Helper

Add `register_vllm_service(env, service_name, config)` utility (probably under
`sage.middleware.services.vllm.registry`) that builds a `ServiceFactory` and registers it with any
SAGE environment. This mirrors patterns in `NeuroMemVDB` examples and simplifies pipelines.

### 4.4 Operators (`packages/sage-libs`)

- `VLLMServiceGenerator(MapFunction)`: used in pipelines like `OpenAIGenerator` but routes to the
  local service instead of HTTP.
  - Accept `service_name` and default timeout. In `execute`, call
    `self.call_service(service_name, payload, method="generate")` and return the enriched record.
- `VLLMEmbeddingOperator(MapFunction)` (or `BatchFunction` if batching embeddings is more efficient)
  to fetch embeddings from the service. Integrate with `VDBMemoryCollection` by plugging this
  operator in pipelines needing vectorization.

### 4.5 CLI Enhancements (`packages/sage-tools/src/sage/tools/cli/commands/llm.py`)

- Introduce `llm model` Typer sub-app with commands:
  - `show` → call registry `list_models`, render table (model id, revision, size, last-used, tags).
  - `download` → support `--model`, `--revision`, `--source` (future). Show progress bar using
    `huggingface_hub` callbacks.
  - `delete` → remove local cache entry (with confirmation unless `--yes`).
- New `llm run` command: spins up `VLLMService` within the current process for quick trials (plugs
  into middleware service loader). Accepts same config flags as `start`, but blocks the terminal and
  uses Service API rather than CLI subprocess.
- Adjust existing `start/stop/status` commands:
  - `start` still launches `vllm serve` for compatibility but prints a deprecation note pointing to
    `sage llm run` and service integration docs.
  - `status` should report both subprocess-based and in-process services (if we can detect service
    registrations via lock file or PID file).
- Add `fine-tune` command stub aligning with service stub: parse dataset/model parameters, validate
  paths, and call service `fine_tune` (which currently raises `NotImplementedError` so CLI can
  surface a friendly message).

### 4.6 Execute Interface & Kernel Flow

- The service exposes `process(payload)` plus explicit `generate/embed` methods to align with
  `ServiceManager.call_service(..., method="generate")`.
- Operators or external code can call
  `ctx.call_service("vllm_service", prompts, method="generate", timeout=...)`.
- For embedding heavy workflows, `VDBMemoryCollection` may call the service via dependency injection
  (e.g., allow customizing embedding model factory to use `VLLMService` instead of
  `EmbeddingModel`). Initial scope: expose service-level `embed` and update `EmbeddingModel` factory
  to optionally proxy to service when configured (future work; for now we provide service operator).

## 5. Configuration & Data Contracts

- Service config example (`dev-notes` usage snippet):
  ```python
  vllm_config = {
      "model_id": "meta-llama/Llama-3-8B-Instruct",
      "embedding_model_id": "intfloat/e5-large-v2",
      "engine": {
          "dtype": "auto",
          "tensor_parallel_size": 1,
          "gpu_memory_utilization": 0.9,
          "max_model_len": 4096,
      },
      "sampling": {
          "temperature": 0.7,
          "top_p": 0.95,
          "max_tokens": 512,
      },
      "auto_reload": True,
  }
  ```
- `process` payload structure:
  ```python
  {
      "task": "generate",
      "inputs": [{"role": "user", "content": "Hi"}],
      "options": {"max_tokens": 128}
  }
  ```
  ```python
  {
      "task": "embed",
      "inputs": ["Text A", "Text B"],
      "options": {"normalize": True}
  }
  ```
- `generate` returns list of dicts (`[{"text": ..., "finish_reason": ..., "tokens_used": {...}}]`).
- `embed` returns dict with `vectors` (List\[List[float]\]), `dim`, `model_id`.

## 6. Fine-Tuning Stub Strategy

- Service defines `fine_tune(self, request: dict)` which validates fields (`base_model`,
  `dataset_path`, `output_dir`, `strategy`) but raises for now.
- CLI `sage llm fine-tune` constructs request payload and warns users the feature needs
  contributions; pre-validation ensures eventual compatibility.

## 7. Backward Compatibility & Migration

- Legacy `sage llm start/stop/status` were removed after the migration window; script authors must
  switch to `sage llm run` (blocking) or `sage llm serve` (background daemon) for managed services.
- New documentation in `tools/install/VLLM_INSTALLATION_GUIDE.md` and `docs-public` describing the
  service-based workflow.
- Provide sample pipeline `examples/service/vllm/vllm_service_demo.py` demonstrating registration +
  operator usage.

## 8. Testing Strategy

1. **Model Registry** (unit tests under
   `packages/sage-common/tests/model_registry/test_vllm_registry.py`):

   - `list_models` empty/non-empty behavior.
   - `download_model` mocked `snapshot_download` verifying manifest updates.
   - `delete_model` removes files and manifest entries.

1. **Middleware Service** (unit tests under
   `packages/sage-middleware/tests/services/test_vllm_service.py`):

   - Engine load success with mocked vllm objects.
   - `generate` / `embed` request flow using fake outputs.
   - `switch_model` reload logic.
   - `process` routing, error handling for unknown tasks.

1. **CLI** (extend `packages/sage-tools/tests/test_cli/llm_suite.py`):

   - `llm model show/download/delete` with patched registry functions.
   - `llm run` ensures config handed to middleware bootstrap.

1. **Operators** (tests under
   `packages/sage-libs/tests/lib/operators/test_vllm_service_operator.py`):

   - `VLLMServiceGenerator` integration with `ServiceCallProxy` (mock ServiceManager).
   - Embedding operator returns expected data structure.

1. **End-to-End Smoke** (optional):

   - Example pipeline registering mocked service and verifying `env.submit` executes without kernel
     errors.

## 9. Documentation & Developer Experience

- Update `tools/install/VLLM_INSTALLATION_GUIDE.md` with new commands + migration guidance.
- Add `docs-public/docs_src/middleware/tools/vllm_service.md` describing architecture,
  configuration, and sample code.
- Expand `dev-notes/DEV_COMMANDS.md` with instructions for the new CLI.

## 10. Open Questions & Future Work

- **Fine-tuning pipeline**: placeholder only; gather requirements from fine-tune owners before
  implementing.
- **Multi-model concurrency**: initial scope loads one text engine + optional embedding engine;
  future iterations may allow multiple concurrent models via internal engine pool.
- **Embedding reuse**: consider wiring `EmbeddingModel` factory to delegate to this service for a
  centralized embedding flow.
- **Remote execution**: design assumes local GPU; extend to Ray or remote executors later.

______________________________________________________________________

This design satisfies the listed requirements and maps them to concrete modules, contracts, and
tests. Next steps: implement registry utilities, scaffold middleware service, extend CLI, add
operators, and land tests/docs following the strategy above.
