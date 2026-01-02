"""LLM Engine Integrations for SAGE.

Layer: L1 (Foundation - LLM Core)

This package provides integrations for multiple LLM inference engines,
all managed by the unified Control Plane (sage.llm.control_plane).

## Directory Structure

```
engines/
├── vllm/                    # vLLM engine integration (✅ Production)
│   ├── service.py
│   ├── api_server.py
│   └── launcher.py
└── sagellm/                 # sageLLM engine (🚧 Under Development)
    └── [submodule: https://github.com/intellistream/sageLLM.git]
```

## Available Engines

### vLLM (Production Ready)
High-performance LLM inference engine from UC Berkeley.
- Location: `sage.llm.engines.vllm`
- Status: ✅ Production Ready
- Repository: https://github.com/vllm-project/vllm

### sageLLM (Under Development)
SAGE's self-developed LLM inference engine with advanced features:
- Prefix reuse and KV cache optimization
- Prefill/Decode separation
- Multi-tier KV cache (GPU/CPU/NVMe)
- Communication backend optimization
- Model compression and acceleration

- Location: `sage.llm.engines.sagellm` (submodule)
- Status: 🚧 Under Development
- Repository: https://github.com/intellistream/sageLLM.git
- Docs: `docs-public/docs_src/dev-notes/research_work/domestic-llm-engine/`

Planned modules (as per refactoring plan):
- `core/` - Minimal coordination layer
- `prefix_reuse/` - Prefix reuse index & matching
- `kv_runtime/` - KV pooling/hierarchy/migration/quota
- `kv_policy/` - Eviction/migration policies
- `scheduler_ir/` - Prefill/Decode decoupled IR
- `comm_backend/` - Communication backend (NCCL/RDMA)
- `accel/` - Quantization/sparse/speculative decoding
- `engines/` - Deep integration with LMDeploy/TurboMind
- `third_party/` - Vendored engines + patches
- `benchmarks/` - Unified benchmarks

### Future Engines
- TensorRT-LLM
- llama.cpp
- And more...

## Architecture

```
sage.llm/
├── control_plane/           # Unified scheduling & routing (engine-agnostic)
│   ├── manager.py
│   ├── strategies/          # Scheduling strategies
│   ├── executors/           # Execution coordinators
│   └── ...
├── engines/                 # Engine-specific implementations
│   ├── vllm/                # vLLM integration (✅)
│   └── sagellm/             # sageLLM integration (🚧 submodule)
├── unified_client.py        # Unified client API (engine-agnostic)
└── control_plane_service.py # Advanced Control Plane service
```

## Usage

Users should interact with engines through the unified Control Plane:

```python
from sage.llm import UnifiedInferenceClient

# Create client (auto-routes through Control Plane)
client = UnifiedInferenceClient.create()

# The Control Plane automatically selects and routes to:
# - vLLM engine (currently)
# - sageLLM engine (when available)
# - Other engines (future)

response = client.chat([{"role": "user", "content": "Hello"}])
```

For direct engine access (advanced use cases):

```python
# vLLM
from sage.llm.engines.vllm import VLLMService
service = VLLMService(config={"model_id": "Qwen/Qwen2.5-7B-Instruct"})

# sageLLM (future, when implemented)
# from sage.llm.engines.sagellm import SageLLMService
# service = SageLLMService(config={"model_id": "Qwen/Qwen2.5-7B-Instruct"})
```
"""

# Re-export vLLM engine (production ready)
from .vllm import (
    DraftModelStrategy,
    LLMAPIServer,
    LLMLauncher,
    LLMLauncherResult,
    LLMServerConfig,
    SpeculativeStrategy,
    VLLMService,
    VLLMServiceConfig,
    get_served_model_name,
)

__all__ = [
    # vLLM Engine (Production)
    "VLLMService",
    "VLLMServiceConfig",
    "LLMAPIServer",
    "LLMServerConfig",
    "LLMLauncher",
    "LLMLauncherResult",
    "get_served_model_name",
    "SpeculativeStrategy",
    "DraftModelStrategy",
    # sageLLM Engine - Future exports (placeholder)
    # "SageLLMService",
    # "SageLLMServiceConfig",
]
