# sage-common: Foundation Layer (L1)

#### 请求路径（Control Plane Only）

```
User Code ──► UnifiedInferenceClient.create()
              │ control_plane_url / SAGE_UNIFIED_BASE_URL / Gateway 默认端口
              ▼
          RequestClassifier
              ▼
        HybridSchedulingPolicy ──► Embedding Batcher
              │                        │
              │                        └─► EmbeddingExecutor (batch to /v1/embeddings)
              ▼
     ExecutionCoordinator (HttpExecutionCoordinator)
              ▼
    Gateway/Control Plane → vLLM / TEI / Embedding instances (SagePorts.*)
```

- 唯一入口：`UnifiedInferenceClient.create()`（仅控制平面模式）。
- 默认基址：`control_plane_url` 参数 > `SAGE_UNIFIED_BASE_URL` >
  `http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1`。
- 端口常量来自 `SagePorts`，禁止硬编码。

#### 示例（控制平面）

```python
from sage.llm import UnifiedInferenceClient

# 默认：使用本地 Gateway 端口（SagePorts.GATEWAY_DEFAULT）
client = UnifiedInferenceClient.create()

# 显式指定 Control Plane / Gateway
client = UnifiedInferenceClient.create(control_plane_url="http://localhost:8889/v1")

# 按模型名绑定（仍经由 Control Plane）
model_bound = UnifiedInferenceClient.create_for_model("Qwen/Qwen2.5-7B-Instruct")

resp = client.chat([{ "role": "user", "content": "写一份日报" }])
```

│ ExecutionCoord │ EmbeddingExecutor │ Metrics / Autos │
├───────────────┴──────────────┬──────────────┴──────────────┬───┤ │ GPUResourceManager │
EngineLifecycleManager │ │ ├──────────────────────────────┴──────────────────────────────┴───┤ │
vLLM / TEI / Embedding instances (SagePorts.\*) │
└─────────────────────────────────────────────────────────────────┘

````

- `control_plane/manager.py`：路由 + 负载均衡 + Autoscaler；与 GPU/引擎管理器协作。
- `strategies/hybrid_policy.py`：LLM/Embedding 混合批调度。
- `executors/http_client.py` & `embedding_executor.py`：对接 OpenAI 兼容后端。
- `metrics_collector.py`：SLA/P95 监控，可驱动 `SLOAwarePolicy`。

### Embedding 服务 (sage_embedding)

多种 Embedding 方法的统一接口：

```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory,
    EmbeddingClientAdapter,
)

# EmbeddingFactory 返回单文本接口 → 通过 Adapter 获得批量 embed(list[str])
raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
client = EmbeddingClientAdapter(raw_embedder)
vectors = client.embed(["Hello", "World"])

# 直接消费 BaseEmbedding 时需逐条调用：raw_embedder.embed("only-one-text")
````

**支持的方法**: `hash`, `hf`, `openai`, `jina`, `zhipu`, `cohere`, `ollama`, `siliconcloud`, `bedrock`,
`nvidia_openai`

### 端口配置 (SagePorts)

统一的端口管理，避免硬编码：

```python
from sage.common.config.ports import SagePorts

# 统一端口常量（不要硬编码）
PORT_MAP = {
    "Gateway": (SagePorts.GATEWAY_DEFAULT, "OpenAI 兼容 API"),
    "LLM": (SagePorts.LLM_DEFAULT, "主推理服务"),
    "Embedding": (SagePorts.EMBEDDING_DEFAULT, "Embedding Server"),
    "Benchmark": (SagePorts.BENCHMARK_LLM, "WSL2 fallback / benchmark"),
}

recommended = SagePorts.get_recommended_llm_port()
print(f"LLM 在此机器使用端口: {recommended}")

if SagePorts.is_wsl():
    # 8001 在 WSL2 可能出现监听但拒绝连接 → 回退 8901
    recommended = SagePorts.LLM_WSL_FALLBACK
```

### Data Types

- **BaseDocument**: Foundation for all document types
- **Vector Types**: Dense and sparse vector representations
- **Metadata**: Document metadata management

### Utilities

- **Logger**: Structured logging system
- **Config**: Configuration management
- **Exceptions**: Custom exception hierarchy

### Core Interfaces

- Common protocols and abstract base classes
- Serialization/deserialization interfaces
- Type definitions and validators

## Architecture

```
sage-common/
├── components/
│   └── sage_embedding/     # Embedding 统一接口
│       ├── factory.py          # EmbeddingFactory
│       ├── protocols.py        # EmbeddingProtocol
│       └── ...
├── config/
│   └── ports.py           # SagePorts 端口配置
├── types/                 # Data type definitions
├── utils/                 # Utility functions
└── exceptions/            # Exception classes

# LLM 控制面与统一客户端已迁移至 packages/sage-llm-core/src/sage/llm/
```

## sageLLM Control Plane

高级调度系统，支持 LLM + Embedding 混合工作负载：

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           UnifiedInferenceClient                            │
│ create() / create(control_plane_url=...)                                     │
├──────────────────────────────┬──────────────────────────────────────────────┤
│  RequestClassifier           │  分类: LLM_CHAT / LLM_GENERATE / EMBEDDING    │
├──────────────────────────────┼──────────────────────────────────────────────┤
│  HybridSchedulingPolicy      │  批量 Embedding + SLO_Aware/FIFO/Fair 选路    │
├───────────────────────┬──────┴──────────────┬──────────────────────────────┤
│ ExecutionCoordinator  │ EmbeddingExecutor  │ Metrics/Autoscaler/PD Routing │
├───────────────────────┴────────────────────┴──────────────────────────────┤
│             vLLM / TEI / Embedding instances (SagePorts.*)                  │
└────────────────────────────────────────────────────────────────────────────┘
```

- `control_plane/manager.py`：路由 + 负载均衡 + Autoscaler
- `strategies/hybrid_policy.py`：LLM/Embedding 混合批调度
  (`sage.llm.control_plane.strategies.hybrid_policy`)
- `executors/http_client.py` & `embedding_executor.py`：对接 OpenAI 兼容后端
- `metrics_collector.py`：SLA/P95 监控，可驱动 `SLOAwarePolicy`

### 动态引擎管理

Control Plane 支持运行时启动/停止推理引擎，并自动追踪 GPU 显存：

| 组件                     | 说明                                                              |
| ------------------------ | ----------------------------------------------------------------- |
| `GPUResourceManager`     | 通过 NVML 监控 GPU 状态，维护逻辑预留账本                         |
| `EngineLifecycleManager` | 管理 vLLM / Embedding Server 进程生命周期                         |
| Management API           | `/v1/management/engines` (POST/DELETE) 与 `/v1/management/status` |

**CLI 命令**:

```bash
# 列出引擎
sage llm engine list

# 启动 LLM 引擎
sage llm engine start Qwen/Qwen2.5-7B-Instruct --tensor-parallel 2

# 启动 Embedding 引擎
sage llm engine start BAAI/bge-m3 --engine-kind embedding

# 停止引擎
sage llm engine stop <engine_id>

# 查看 GPU 状态
sage llm gpu
```

### 预设编排

使用预设一键部署多个引擎：

```bash
# 列出内置预设
sage llm preset list

# 查看预设详情
sage llm preset show -n qwen-mini-with-embeddings

# 应用预设
sage llm preset apply -n qwen-mini-with-embeddings
```

预设 YAML 示例：

```yaml
version: 1
name: qwen-mini-with-embeddings
engines:
  - name: chat
    kind: llm
    model: Qwen/Qwen2.5-1.5B-Instruct
  - name: embed
    kind: embedding
    model: BAAI/bge-small-zh-v1.5
```

> > > > > > > feature/control-plane-enhancement

## Usage Examples

### 统一推理客户端

```python
from sage.llm import UnifiedInferenceClient
from sage.common.config.ports import SagePorts

# 推荐：自动检测（Control Plane First）
client = UnifiedInferenceClient.create()

# 显式连接本地 Gateway（如 UnifiedAPIServer）
gateway = UnifiedInferenceClient.create(control_plane_url=f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1")

# 内嵌模式适合批处理脚本
embedded = "(deprecated)"

status = client.get_status()
print(f"LLM available: {status['llm_available']}")
print(f"Embedding available: {status['embedding_available']}")
```

### 本地 Embedding

```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory,
    EmbeddingClientAdapter,
    list_embedding_models,
)

for method, info in list_embedding_models().items():
    print(f"{method}: {info['description']}")

embedder = EmbeddingFactory.create("hash", dim=384)
client = EmbeddingClientAdapter(embedder)  # 获得批量接口
vectors = client.embed(["Hello", "World"])
single_vector = embedder.embed("single-text")  # 仍可按需单条调用

# 离线模式：配合 UnifiedInferenceClient 只负责 embedding，LLM 仍可走 Control Plane
```

### 环境变量示例

Control Plane 自动探测优先读取 `SAGE_*` 前缀，随后才会尝试本地端口与云 API：

```bash
# .env（示例，数值来自 SagePorts 常量）
SAGE_CHAT_BASE_URL=http://localhost:8901/v1   # SagePorts.get_recommended_llm_port()
SAGE_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
SAGE_CHAT_API_KEY=token-optional
SAGE_EMBEDDING_BASE_URL=http://localhost:8090/v1  # SagePorts.EMBEDDING_DEFAULT
SAGE_EMBEDDING_MODEL=BAAI/bge-m3
HF_TOKEN=hf_xxx
# detect_china_mainland() 会在 CLI 中自动调用 ensure_hf_mirror_configured()
# 如果在中国大陆，可提前设置：
HF_ENDPOINT=https://hf-mirror.com
```

> CLI 入口如 `sage llm serve` 和 `sage llm model download` 均会调用
> `sage.common.config.network.ensure_hf_mirror_configured()`，自动根据 `detect_china_mainland()` 调整
> `HF_ENDPOINT`。

### 端口 & WSL2 指南

```python
from sage.common.config.ports import SagePorts

if SagePorts.is_wsl():
    llm_port = SagePorts.LLM_WSL_FALLBACK  # 8901
else:
    llm_port = SagePorts.LLM_DEFAULT       # 8001

print("启动命令:", f"sage llm serve --port {llm_port} --embedding-port {SagePorts.EMBEDDING_DEFAULT}")
```

- `UnifiedInferenceClient.create()` 仅使用 Control Plane/Gateway 端口（默认
  `SagePorts.GATEWAY_DEFAULT`），不再扫描本地 vLLM 端口。
- `SagePorts.is_available(port)` 可在脚本内检测端口是否被占用。
- `sage llm serve --port <LLM_PORT> --embedding-port <EMBED_PORT>` 会自动写入 `.sage/llm/daemon.json`，供
  CLI 与 Control Plane 共享。

### 服务启动示例

```bash
# recommended: 通过 CLI 在 SagePorts 上启动服务栈
sage llm serve \
  --model Qwen/Qwen2.5-7B-Instruct \
  --embedding-model BAAI/bge-m3 \
  --port $(python -c "from sage.common.config.ports import SagePorts; print(SagePorts.get_recommended_llm_port())") \
    --embedding-port 8090  # SagePorts.EMBEDDING_DEFAULT

# 无需 Embedding 时：
sage llm serve --no-embedding

# 查看状态/日志
sage llm status && sage llm logs --tail 100
```

## Dependencies

- **External**: `openai`, `httpx`, `torch` (optional for HF models)
- **Internal**: None (foundation layer)

## Environment Variables（本地优先）

参考 `.env.template`：

```bash
# Chat / LLM（显式指定或使用本地端口探测）
SAGE_CHAT_API_KEY=sk-your-key
SAGE_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
SAGE_CHAT_BASE_URL=http://localhost:8001/v1   # SagePorts.LLM_DEFAULT；WSL2 可用 8901

# Embedding（显式指定或使用本地端口探测）
SAGE_EMBEDDING_BASE_URL=http://localhost:8090/v1  # SagePorts.EMBEDDING_DEFAULT
SAGE_EMBEDDING_MODEL=BAAI/bge-m3

# 本地端口（CLI 会写入）
SAGE_LLM_PORT=8001    # SagePorts.LLM_DEFAULT（WSL2 可改为 8901）
SAGE_EMBEDDING_PORT=8090

# HF 下载
HF_TOKEN=hf_xxx
# CLI 入口会调用 ensure_hf_mirror_configured() 自动判断是否需要 HF_ENDPOINT
```

## See Also

- [Embedding 模块](../sage-libs/embedding.md) - 详细的 Embedding 用法
- [部署指南](../../deployment/index.md) - LLM/Embedding 服务部署
- [Architecture Overview](../../../concepts/architecture/overview.md)
- [Package Structure](../../../concepts/architecture/package-structure.md)

> 网络/镜像：参见 `sage.common.config.network` 中的
> `detect_china_mainland()`、`ensure_hf_mirror_configured()`。
