# Control Plane 路由修复

**日期**: 2025-12-04\
**分支**: main-dev\
**相关组件**: sage-llm-gateway, sage-common (sageLLM)

## 问题背景

用户反馈 `sage studio start --prod` 启动时出现以下错误：

1. **LLM 启动失败**: "Insufficient GPU memory" - GPU 被孤儿进程占用
1. **Embedding 端口冲突**: "Requested port 8090 is reserved" - STOPPED 引擎未释放端口
1. **端口配置问题**: `UnifiedInferenceClient.create()` 把 8001 端口的 Embedding 服务误认为 LLM

## 根本原因分析

### 问题 1: 资源未释放

`stop_engine_gracefully()` 和 `prune_stopped_engines()` 只更新了引擎状态为 STOPPED，但没有释放：

- 端口 (`_reserved_ports`)
- GPU 内存 (`gpu_manager`)
- Executor 实例注册 (`unregister_instance`)

### 问题 2: Gateway 重启后丢失引擎信息

1. `EngineLifecycleManager` 初始化时没有传入 `control_plane` 引用
1. `discover_running_engines()` 虽然发现了引擎，但无法调用 `register_engine()` 注册
1. `register_engine()` 只更新了 `_registered_engines` 字典，没有创建 `ExecutionInstance`

### 问题 3: 端口扫描误判

RAG Pipeline 使用端口扫描作为 fallback，但无法区分 LLM 和 Embedding 服务：

- `/v1/models` 端点两者都会响应
- 8001 端口可能是 Embedding 服务

## 修复方案

### 1. 资源释放修复 (manager.py)

**文件**: `packages/sage-llm-core/src/sage/llm/control_plane/manager.py`

#### stop_engine_gracefully()

```python
def stop_engine_gracefully(self, engine_id: str) -> bool:
    # ... 停止引擎进程 ...

    # 释放资源 (port, GPU, instance registration)
    engine_entry = self._pop_engine_metadata(engine_id)
    if engine_entry:
        gpu_ids = engine_entry.get("gpu_ids", [])
        memory_per_gpu_gb = engine_entry.get("memory_per_gpu_gb", 0.0)
        port = engine_entry.get("port")
        instance_id = engine_entry.get("instance_id")

        if gpu_ids and memory_per_gpu_gb and self.gpu_manager:
            self.gpu_manager.release_resources(gpu_ids, memory_per_gpu_gb)
        if port:
            self._release_port(port)
        if instance_id:
            self.unregister_instance(instance_id)

    # 清理健康状态追踪
    with self._engine_health_state_lock:
        self._engine_health_state.pop(engine_id, None)

    self.update_engine_state(engine_id, EngineState.STOPPED)
    return True
```

#### prune_stopped_engines()

```python
def prune_stopped_engines(self) -> int:
    # 先释放所有 stopped/failed 引擎的资源
    engines_to_prune = []
    for engine_info in self.lifecycle_manager.list_engines():
        status = engine_info.get("status", "")
        engine_id = engine_info.get("engine_id", "")
        if status in {"STOPPED", "FAILED"} and engine_id:
            engines_to_prune.append(engine_id)

    for engine_id in engines_to_prune:
        engine_entry = self._pop_engine_metadata(engine_id)
        if engine_entry:
            # 释放 GPU, port, instance
            ...

    # 然后清理记录
    return self.lifecycle_manager.prune_stopped_engines()
```

### 2. 引擎注册修复 (manager.py)

#### \_init_engine_lifecycle_manager()

```python
def _init_engine_lifecycle_manager(self) -> EngineLifecycleManager | None:
    try:
        # 传入 control_plane=self 以便发现的引擎可以注册
        return RuntimeEngineLifecycleManager(control_plane=self)
    except Exception:
        return None
```

#### register_engine()

```python
def register_engine(self, engine_id, model_id, host, port, engine_kind, metadata):
    # ... 原有的 _registered_engines 注册 ...

    # 创建并注册 ExecutionInstance 用于请求路由
    instance = ExecutionInstance(
        instance_id=engine_id,
        host=host if host != "0.0.0.0" else "localhost",
        port=port,
        model_name=model_id,
        instance_type=(
            ExecutionInstanceType.EMBEDDING
            if engine_kind == "embedding"
            else ExecutionInstanceType.GENERAL
        ),
        # ...
    )
    self.register_instance(instance)
    self._reserved_ports.add(port)
```

### 3. RAG Pipeline 路由修复 (rag_pipeline.py)

**文件**: `packages/sage-llm-gateway/src/sage/gateway/rag_pipeline.py`

移除端口扫描 fallback，完全依赖 Control Plane：

```python
def _get_llm_client(self):
    """获取通过 Control Plane 路由的 LLM 客户端"""
    llm_base_url = self._get_llm_backend_url()

    if llm_base_url:
        logger.info(f"Using LLM backend from Control Plane: {llm_base_url}")
        # 直接创建客户端连接后端
        ...
    else:
        # Control Plane 没有可用的 LLM 后端
        raise RuntimeError(
            "No LLM backend available in Control Plane. "
            "Start an LLM engine with: sage llm engine start <model_name>"
        )

def _get_llm_backend_url(self) -> str | None:
    """从 Control Plane 获取可用的 LLM 后端 URL（不做端口扫描）"""
    manager = get_control_plane_manager()
    backends_info = manager.get_registered_backends()
    llm_backends = backends_info.get("llm_backends", [])

    # 选择第一个健康的后端
    for backend in llm_backends:
        if backend.get("is_healthy", False):
            return backend.get("base_url")
    return None
```

## 修复后的架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户请求                                      │
│              /v1/chat/completions                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway (sage-llm-gateway)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   RAG Pipeline                               │ │
│  │  _get_llm_backend_url() → Control Plane                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Control Plane Manager                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ get_registered_backends()                                    │ │
│  │   → executor.get_all_instances()                             │ │
│  │   → 返回 LLM/Embedding 后端列表                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Gateway 启动时:                                              │ │
│  │   → discover_running_engines() 扫描进程                       │ │
│  │   → register_engine() 注册到 executor                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM 后端 (vLLM)                               │
│              http://localhost:8901/v1                            │
└─────────────────────────────────────────────────────────────────┘
```

## 关键改进

1. **资源释放**: 引擎停止时立即释放端口、GPU、实例注册
1. **引擎发现**: Gateway 重启后自动发现并注册运行中的引擎
1. **统一路由**: 所有 LLM 请求通过 Control Plane 路由，支持多引擎、负载均衡
1. **类型区分**: Control Plane 正确区分 LLM 和 Embedding 后端

## 测试验证

```bash
# 1. 重启 Gateway
sage gateway restart

# 2. 检查后端发现
curl -s http://localhost:8000/v1/management/backends | python3 -m json.tool
# 应显示 LLM 和 Embedding 后端

# 3. 测试 chat 请求
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'

# 4. 检查日志确认路由
tail -20 ~/.sage/gateway/gateway.log | grep "LLM backend"
# 应显示 "Using LLM backend from Control Plane: http://localhost:8901/v1"
```

## 相关文件

- `packages/sage-llm-core/src/sage/llm/control_plane/manager.py`
- `packages/sage-llm-core/src/sage/llm/control_plane/engine_lifecycle.py`
- `packages/sage-llm-gateway/src/sage/gateway/rag_pipeline.py`
- `packages/sage-llm-gateway/src/sage/gateway/routes/control_plane.py`
- `packages/sage-llm-core/src/sage/llm/api_server.py`

______________________________________________________________________

## 追加修复: GPU 自动选择 (2025-12-04)

### 问题描述

当 `sage studio start --prod` 启动时，如果 Control Plane 还没运行，会通过 `LLMLauncher` → `LLMAPIServer` 路径启动
vLLM。这个路径没有 GPU 选择逻辑，vLLM 默认使用 GPU 0。

**错误现象**:

```
ValueError: The model's max seq len (131072) is larger than the maximum number of
tokens that can be stored in KV cache (42192). Try increasing `gpu_memory_utilization`
or decreasing `max_model_len` when initializing the engine.

Free memory on device (21.96/79.25 GiB) on startup is less than
desired GPU memory utilization (0.7, 55.48 GiB)
```

**原因**: GPU 0 被其他进程占用（如 58GB），只剩 22GB，但 vLLM 需要 55GB (70% × 80GB)。

### 启动路径分析

```
sage studio start
    │
    ├─[Control Plane 已运行]
    │   └→ _start_llm_via_control_plane()
    │       └→ Gateway API: POST /v1/management/engines
    │           └→ request_engine_startup()
    │               └→ GPUResourceManager.allocate_resources()  ✅ 有 GPU 选择
    │                   └→ engine_lifecycle.spawn_engine(gpu_ids=[1])
    │                       └→ CUDA_VISIBLE_DEVICES=1
    │
    └─[Control Plane 未运行] ← 问题路径
        └→ LLMLauncher.launch()
            └→ LLMAPIServer.start()
                └→ subprocess.Popen(cmd)  ❌ 无 GPU 选择
                    └→ vLLM 默认使用 GPU 0
```

### 修复方案

**文件**: `packages/sage-llm-core/src/sage/llm/api_server.py`

#### 1. 添加 GPU 选择函数

```python
def _select_available_gpus(
    required_memory_gb: float,
    tensor_parallel_size: int = 1,
) -> list[int] | None:
    """Select GPUs with sufficient available memory.

    Uses GPUResourceManager to find GPUs with enough free memory for LLM inference.

    Args:
        required_memory_gb: Required free memory per GPU in GB
        tensor_parallel_size: Number of GPUs needed

    Returns:
        List of GPU IDs with sufficient memory, or None if not available
    """
    try:
        from sage.llm.control_plane import GPUResourceManager
    except ImportError:
        logger.debug("GPUResourceManager not available, using default GPU selection")
        return None

    try:
        gpu_manager = GPUResourceManager()
        available_gpus = gpu_manager.allocate_resources(
            required_memory_gb, tensor_parallel_size
        )
        if available_gpus and len(available_gpus) >= tensor_parallel_size:
            logger.info(f"Selected GPUs with sufficient memory: {available_gpus}")
            # Release the "allocation" - we only needed to find available GPUs
            gpu_manager.release_resources(available_gpus, required_memory_gb)
            return available_gpus
        else:
            logger.warning(
                f"Could not find {tensor_parallel_size} GPUs with {required_memory_gb}GB free"
            )
            return None
    except Exception as e:
        logger.debug(f"GPU selection failed: {e}")
        return None
```

#### 2. 修改 LLMAPIServer.start()

```python
def start(self, background: bool = True, log_file: Path | None = None) -> bool:
    # ... 原有的检查 ...

    # Auto-select GPUs with sufficient free memory
    # Estimate required memory: gpu_memory_utilization * 80GB (typical GPU size)
    # For safety, require at least 40GB free to avoid OOM during startup
    estimated_required_gb = max(40.0, 80.0 * self.config.gpu_memory_utilization)
    selected_gpus = _select_available_gpus(
        required_memory_gb=estimated_required_gb,
        tensor_parallel_size=self.config.tensor_parallel_size,
    )

    # Prepare environment with GPU selection
    env = os.environ.copy()
    if selected_gpus:
        cuda_devices = ",".join(str(gpu) for gpu in selected_gpus)
        env["CUDA_VISIBLE_DEVICES"] = cuda_devices
        logger.info(f"Set CUDA_VISIBLE_DEVICES={cuda_devices}")
    else:
        logger.warning(
            "Could not auto-select GPUs, using system default. "
            "This may fail if default GPU has insufficient memory."
        )

    # Start process with GPU-aware environment
    self.process = subprocess.Popen(
        cmd,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid if os.name != "nt" else None,
        env=env,  # ← 关键：传入设置了 CUDA_VISIBLE_DEVICES 的环境变量
    )
```

### 修复效果

修复后日志：

```
Selected GPUs with sufficient memory: [1]
Set CUDA_VISIBLE_DEVICES=1
LLM API server started in background (PID: 1856760)
✅ LLM API server is ready! (took 46.2s, 47 attempts)
```

GPU 状态对比：

```
修复前:
GPU 0: 58169 MB used (被占用)  ← vLLM 尝试在这里启动，失败
GPU 1: 17 MB used (空闲)

修复后:
GPU 0: 60775 MB used (未变)
GPU 1: 57881 MB used ← LLM 正确加载到 GPU 1
```

### 统一的 GPU 选择逻辑

现在两条启动路径都使用 `GPUResourceManager` 进行 GPU 选择：

| 路径               | GPU 选择逻辑                                                    | 环境变量设置                      |
| ------------------ | --------------------------------------------------------------- | --------------------------------- |
| Control Plane 模式 | `request_engine_startup()` → `gpu_manager.allocate_resources()` | `engine_lifecycle.spawn_engine()` |
| LLMLauncher 模式   | `LLMAPIServer.start()` → `_select_available_gpus()`             | `subprocess.Popen(env=...)`       |

两者都调用 `GPUResourceManager._filter_available()` 来过滤有足够内存的 GPU。
