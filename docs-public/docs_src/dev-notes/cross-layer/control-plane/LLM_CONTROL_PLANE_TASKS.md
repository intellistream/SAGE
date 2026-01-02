# SAGE LLM Control Plane Enhancement Tasks

This document outlines the tasks for enhancing the sageLLM Control Plane to support dynamic engine
lifecycle management and GPU resource scheduling (Issue #1284).

## Task 1: GPU Resource Manager (Phase 1)

**Assignee**: Copilot A

**Goal**: Implement `GPUResourceManager` to monitor and manage GPU resources.

**File**: `packages/sage-llm-core/src/sage/llm/control_plane/gpu_manager.py`

**Instructions**:

1. Create the file `gpu_manager.py`.
1. Implement the `GPUResourceManager` class.
1. **Dependencies**: Use `pynvml` for GPU monitoring.
   - Check `packages/sage-common/pyproject.toml`. If `nvidia-ml-py` is not listed, add it to
     dependencies.
   - Handle `ImportError` gracefully (mock if not available or if running on CPU).
1. **Key Methods**:
   - `__init__(self)`: Initialize NVML.
   - `get_system_status(self) -> List[Dict]`: Return status of all GPUs (index, name, memory_total,
     memory_used, memory_free, utilization).
   - `check_resource_availability(self, required_memory_gb: float, count: int = 1) -> List[int]`:
     Return list of GPU indices that satisfy the requirement.
   - `allocate_resources(self, required_memory_gb: float, count: int = 1) -> List[int]`: Reserve
     resources (internal accounting).
   - `release_resources(self, gpu_ids: List[int], memory_gb: float)`: Release resources.
   - `estimate_model_memory(self, model_name: str, tensor_parallel_size: int = 1) -> float`:
     Implement a heuristic to estimate memory usage (e.g., 2GB per 1B params + overhead). You can
     use a simple lookup or formula for now.
1. **Error Handling**: Ensure robust error handling for NVML calls.

## Task 2: Engine Lifecycle Manager (Phase 2)

**Assignee**: Copilot B

**Goal**: Implement `EngineLifecycleManager` to spawn and stop vLLM processes.

**File**: `packages/sage-llm-core/src/sage/llm/control_plane/engine_lifecycle.py`

**Instructions**:

1. Create the file `engine_lifecycle.py`.
1. Implement the `EngineLifecycleManager` class.
1. **Dependencies**: `subprocess`, `psutil` (for process management),
   `sage.common.config.ports.SagePorts`.
1. **Key Methods**:
   - `spawn_engine(self, model_id: str, gpu_ids: List[int], port: int, extra_args: List[str] = None) -> str`:
     - Launch `vllm.entrypoints.openai.api_server` as a subprocess.
     - Set `CUDA_VISIBLE_DEVICES` env var based on `gpu_ids`.
     - Return a unique `engine_id`.
   - `stop_engine(self, engine_id: str) -> bool`:
     - Send SIGTERM, wait, then SIGKILL if needed.
   - `get_engine_status(self, engine_id: str) -> Dict`: Return status (RUNNING, STOPPED, FAILED),
     PID, port, model.
   - `list_engines(self) -> List[Dict]`: List all managed engines.
1. **Port Management**: You might need a simple helper to find available ports if `port` is not
   provided, or rely on the caller.
1. **Logging**: Log all spawn/stop events.

## Task 3: Control Plane Integration & API (Phase 2/3)

**Assignee**: Copilot C

**Goal**: Integrate managers into `ControlPlaneManager` and expose Management API.

**Files**:

- `packages/sage-llm-core/src/sage/llm/control_plane/manager.py`
- `packages/sage-llm-core/src/sage/llm/unified_api_server.py`

**Instructions**:

1. **Update `ControlPlaneManager`**:

   - Import `GPUResourceManager` and `EngineLifecycleManager` (assume they exist from Task 1 & 2).
   - Initialize them in `__init__`.
   - Add method `request_engine_startup(self, model_id: str, ...)`:
     - Calculate required memory.
     - Call `gpu_manager.allocate_resources`.
     - If successful, call `lifecycle_manager.spawn_engine`.
     - Register the new instance using `self.register_instance`.
   - Add method `request_engine_shutdown(self, engine_id: str)`:
     - Call `lifecycle_manager.stop_engine`.
     - Call `gpu_manager.release_resources`.
     - Unregister instance.
   - Add method `get_cluster_status(self)`: Return GPU status and Engine list.

1. **Update `UnifiedAPIServer`**:

   - Add new FastAPI routes for management:
     - `POST /v1/management/engines`: Trigger startup.
     - `DELETE /v1/management/engines/{engine_id}`: Trigger shutdown.
     - `GET /v1/management/status`: Get cluster status.
   - Connect these routes to the `ControlPlaneManager` methods.

## Task 4: CLI Commands (Phase 3)

**Assignee**: Copilot D

**Goal**: Add CLI commands to manage engines.

**File**: `packages/sage-cli/src/sage/cli/commands/apps/llm.py` (or new file `llm_engine.py`
imported there)

**Instructions**:

1. Extend the `sage llm` command group.
1. **New Subcommands**:
   - `sage llm engine list`: Call `GET /v1/management/status` and display table.
   - `sage llm engine start <model_id>`: Call `POST /v1/management/engines`.
   - `sage llm engine stop <engine_id>`: Call `DELETE /v1/management/engines/{engine_id}`.
   - `sage llm gpu`: Call `GET /v1/management/status` and display GPU info.
1. **Implementation Details**:
   - Use `httpx` or `requests` to talk to the local `UnifiedAPIServer` (default port 8000 or from
     config).
   - Use `rich` for pretty printing tables (Engine status, GPU usage).
   - Handle connection errors (e.g., if `sage llm serve` is not running).
