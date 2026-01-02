# sage-studio

Interactive web console for building SAGE pipe-

- Chat tab calls Gateway's `/v1/chat/completions`, reusing the same session IDs as the UI.
- Built-in session list (create, rename, clear, delete) talks to Gateway's `/sessions/**` routes.
- Memory panel (`MemorySettings.tsx`) uses `/memory/config|stats` to display backend type,
  short-term usage, or Neuromem collection state.
- `UnifiedInferenceClient` 优先本地 LLM；未检测到可用端点时会报错并提示启动本地服务或显式配置 `SAGE_CHAT_BASE_URL`，不再隐式回退云端。

### Fine-tuning Centerb calls Gateway's `/v1/chat/completions`, reusing the same session IDs as the UI.

- Built-in session list (create, rename, clear, delete) talks to Gateway's `/sessions/**` routes.
- Memory panel (`MemorySettings.tsx`) uses `/memory/config|stats` to display backend type,
  short-term usage, or Neuromem collection state.
- `UnifiedInferenceClient` 优先本地 LLM；未检测到可用端点时会报错并提示启动本地服务或显式配置 `SAGE_CHAT_BASE_URL`，不会自动回退云端。

**Layer**: L6 (Interface) · **Package**: `packages/sage-studio`

## Overview

Studio bundles four major experiences in a single CLI-driven service:

- **Visual Flow Editor** – drag-and-drop pipelines backed by `PipelineBuilder` + `NodeRegistry`.
- **Playground / Chat Mode** – OpenAI-compatible chat UI on top of `sage-llm-gateway`, including
  memory inspection and session tools.
- **Fine-tuning Center** – upload datasets, launch finetune jobs, monitor GPU usage, and hot-swap
  models without leaving the browser.
- **Local LLM Orchestration** – `ChatModeManager` can start/stop a vLLM server (port 8001) and fall
  back to cloud APIs automatically.

All flows share one CLI entrypoint (`sage studio ...`) that supervises the frontend (Vite, port
5173), backend API (FastAPI, port 8080), Gateway (FastAPI, port 8000), and optional local LLM
service.

```
┌──────────────────────────────────────────────────────────────────┐
│                            User Browser                          │
│ ┌────────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │Flow Editor │ │Playground   │ │Memory Panel  │ │Finetune Panel│ │
│ └────────────┘ └─────────────┘ └──────────────┘ └──────────────┘ │
└──────────────────────▲───────────────────────────────────────────┘
                       │ REST (Vite dev server ➜ FastAPI backend)
┌──────────────────────┼───────────────────────────────────────────┐
│ Studio backend (`config/backend/api.py`)                         │
│  • Pipeline CRUD / execution requests                            │
│  • `/api/finetune/**`, `/api/chat/memory/**`, `/api/system/**`   │
│  • Bridges to Gateway + finetune manager + chat manager          │
└───────────────▲───────────────┬──────────────────────────────────┘
                │               │
      CLI (`ChatModeManager`)   │
   ┌────────────┴────────────┐  │
   │ 1. `sage studio start`  │  │
   │ 2. Start gateway + LLM  │  │
   │ 3. Manage logs/status   │  │
   └────────────┬────────────┘  │
                │               │
        ┌───────┴───────┐  ┌────┴──────────────────────┐
        │ sage-llm-gateway  │  │ Finetune Manager (L6 svc) │
        │ /v1/chat/...  │  │ Task queue + GPU detect   │
        └───────┬───────┘  └────────────┬──────────────┘
                │                       │
        ┌───────┴──────────┐      ┌──────┴─────────┐
        │ sage-middleware  │      │ Local LLM/vLLM │
        │ + sage-kernel    │      │ (optional)     │
        └──────────────────┘      └────────────────┘
```

## Key Features

### Visual Flow Editor

- Canvas built with React Flow (`FlowEditor.tsx`).
- `NodeRegistry` exposes curated operators (retrievers, promptors, generators, sinks, adapters,
  etc.).
- `PipelineBuilder` turns `VisualPipeline` JSON into an executable `LocalEnvironment` pipeline,
  preserving node configuration.
- Supports import/export to `.sage/pipelines/pipeline_*.json`, undo/redo, template palette, and
  Python export.

### Playground & Chat Mode

- Chat tab calls Gateway’s `/v1/chat/completions`, reusing the same session IDs as the UI.
- Built-in session list (create, rename, clear, delete) talks to Gateway’s `/sessions/**` routes.
- Memory panel (`MemorySettings.tsx`) uses `/memory/config|stats` to display backend type,
  short-term usage, or Neuromem collection state.
- `UnifiedInferenceClient` 优先本地 LLM；如果不可用需显式配置 `SAGE_CHAT_BASE_URL` 或启动本地服务，不会自动回退云端。

### Fine-tuning Center

- `FinetunePanel.tsx` uploads datasets, runs validation, and calls `/api/finetune/create`.
- `services/finetune_manager.py` schedules tasks, gathers GPU metadata, streams logs, and stores
  outputs at `~/.sage/studio_finetune/<task_id>/`.
- Completed runs surface as selectable models. Clicking “切换为对话后端” or picking from the “当前使用的模型”
  dropdown triggers a hot switch (LLM server restart + environment update).
- API endpoints mirror the UI: `/api/finetune/tasks`, `/models`, `/current-model`, `/switch-model`,
  `/use-as-backend`, `/prepare-sage-docs`.

### Local LLM orchestration

- CLI flag `--llm/--no-llm` controls whether a vLLM server launches.
- `ChatModeManager._start_llm_service()` wraps `LLMAPIServer` (from `sage.llm`) and binds to port
  8001\.
- Automatic cache lookup via `vllm_registry` accelerates model startup; environment variables
  `SAGE_STUDIO_LLM_MODEL`, `SAGE_STUDIO_LLM_GPU_MEMORY`, `SAGE_CHAT_MODEL` override defaults.
- Orphaned processes are cleaned up via `lsof + kill` if Studio restarts unexpectedly.

## Installation

```bash
# install SAGE in editable mode (recommended for contributors)
pip install -e .[all]

# or install the standalone package
cd packages/sage-studio
pip install -e .
```

Requirements: Python 3.10+, Node.js 18+, modern browser, optional GPU (CUDA) for vLLM/finetune.

## Starting Studio

### CLI (one-command startup)

```bash
# Development (hot reload frontend, auto start gateway + backend + local LLM if available)
sage studio start

# Production bundle (requires `sage studio build` once)
sage studio start --prod
```

Useful flags:

```
--host 0.0.0.0         # bind externally
--port 5173            # frontend port (dev mode)
--backend-port 8080    # FastAPI backend
--gateway-port 8000    # sage-llm-gateway (OpenAI API)
--no-llm             # skip local vLLM service (enabled by default)
--llm-model <name>     # override default model
--use-finetuned        # auto-select latest finetuned model
```

Services start in this order: (1) optional LLM ➜ (2) Gateway ➜ (3) FastAPI backend ➜ (4)
Vite/production frontend. Logs live under `~/.sage/studio/*`.

### Manual dev mode

```bash
# Backend (FastAPI)
cd packages/sage-studio
python -m sage.studio.config.backend.api  # http://localhost:8080

# Frontend (Vite dev server)
cd packages/sage-studio/src/sage/studio/frontend
pnpm install  # or yarn/npm
pnpm dev      # http://localhost:5173
```

Start Gateway separately if you only need the API:

```bash
python -m sage.llm.gateway.server  # http://localhost:8000
```

## Fine-tuning workflow

1. Open the **Finetune** tab.
1. Upload JSON/JSONL or click “使用 SAGE 文档样例” to auto-generate training data.
1. Configure epochs, batch size, learning rate (GPU-aware recommendations appear automatically).
1. Submit the task and monitor the table (refreshes every 3 seconds). Click a row to view live logs.
1. When status turns ✅, either:
   - Choose the model from the “当前使用的模型” dropdown (hot switch), or
   - Click “切换为对话后端”.
1. Switch to **Chat** to test the model; Gateway now points at the restarted vLLM server.

CLI shortcuts:

```bash
sage finetune start --model Qwen/Qwen2.5-1.5B-Instruct --data data.jsonl
sage studio start --list-finetuned
sage studio start --use-finetuned
```

## Memory dashboard

- Navigate to Settings → “记忆管理”.
- Cards show the active backend (`short_term`, `vdb`, `kv`, `graph`), max dialogs, embedding model,
  and total sessions.
- Table rows mirror `GET /memory/stats`: short-term sessions display dialog counts + progress bars;
  Neuromem-backed sessions display collection/index info.
- Automate via Gateway endpoints:

```bash
curl http://localhost:8000/memory/config | jq
curl http://localhost:8000/memory/stats | jq
curl -X POST "http://localhost:8000/sessions/cleanup?max_age_minutes=30"
```

## Programmatic Pipeline Builder

```python
from sage.studio.models import VisualNode, VisualPipeline
from sage.studio.services.pipeline_builder import PipelineBuilder

pipeline = VisualPipeline(
    id="rag-demo",
    name="Docs QA",
    nodes=[
        VisualNode(id="source", type="file", config={"path": "docs.md"}),
        VisualNode(id="retriever", type="rag.retriever", config={"collection": "docs"}),
        VisualNode(
            id="generator",
            type="rag.generator",
            config={"model": "Qwen/Qwen2.5-7B-Instruct"},
        ),
    ],
    connections=[
        ("source", "retriever"),
        ("retriever", "generator"),
    ],
)

env = PipelineBuilder().build(pipeline)
env.execute()
```

## Directory structure

```
packages/sage-studio/
├── README.md
├── src/sage/studio/
│   ├── studio_manager.py         # CLI entry + ChatModeManager
│   ├── chat_manager.py           # Local LLM + session helpers
│   ├── config/backend/api.py     # FastAPI backend
│   ├── services/
│   │   ├── pipeline_builder.py
│   │   ├── node_registry.py
│   │   ├── finetune_manager.py
│   │   └── docs_processor.py
│   ├── frontend/ (Vite app)
│   │   └── src/components/
│   │       ├── FlowEditor.tsx
│   │       ├── ChatMode.tsx
│   │       ├── MemorySettings.tsx
│   │       └── FinetunePanel.tsx
│   └── data/operators/*.json     # Palette metadata
└── tests/
    ├── test_pipeline_builder.py
    ├── test_node_registry.py
    ├── test_studio_cli.py
    └── test_e2e_integration.py
```

## Testing

```bash
cd packages/sage-studio
pytest tests -v

# Frontend lint/tests
cd src/sage/studio/frontend
pnpm lint
pnpm test
```

## Related docs

- [CLI reference](../sage-tools/cli_reference.md)
- [Architecture overview](../../../concepts/architecture/overview.md)
- [Package architecture (dev notes)](../../../dev-notes/package-architecture.md#sage-studio-l6)
- [Finetune & memory deep dives](../../../dev-notes/index.md)

Studio evolves alongside Gateway, sage-memory, and sage-llm; update this page whenever new endpoints
or UI panels land so public docs stay aligned with the dev notes.
