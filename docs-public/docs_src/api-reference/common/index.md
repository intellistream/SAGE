# sage-common API

Common utilities, data types, and base classes used across all SAGE packages.

**Layer**: L1 (Foundation)

## Overview

`sage-common` provides foundational components that all other SAGE packages depend on:

- Core data types and type system
- Configuration management (including **SagePorts** for unified port configuration)
- Logging utilities
- Base exceptions
- Common decorators and utilities
- **UnifiedInferenceClient** - Unified LLM + Embedding client (NEW)
- **EmbeddingFactory** and adapters for embedding services
- Model registry and vLLM integration

## Quick Start: UnifiedInferenceClient

The recommended way to interact with LLM and Embedding services:

**Python 方式**:

```python
from sage.llm import UnifiedInferenceClient
from sage.common.config.ports import SagePorts

# Auto-detect available services (Simple mode)
client = UnifiedInferenceClient.create_auto()

# Or use Control Plane mode for production (recommended)
client = UnifiedInferenceClient.create_with_control_plane(
    llm_base_url=f"http://localhost:{SagePorts.BENCHMARK_LLM}/v1",
    llm_model="Qwen/Qwen2.5-7B-Instruct",
    embedding_base_url=f"http://localhost:{SagePorts.EMBEDDING_DEFAULT}/v1",
    embedding_model="BAAI/bge-m3",
)

# Chat completion
response = client.chat([{"role": "user", "content": "Hello"}])

# Text generation
text = client.generate("Once upon a time")

# Embedding
vectors = client.embed(["text1", "text2"])
```

**curl 方式** (兼容 OpenAI API):

```bash
# Chat Completion via Gateway (端口 8000)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-7B-Instruct", "messages": [{"role": "user", "content": "Hello"}]}'

# Embedding (端口 8090)
curl -X POST http://localhost:8090/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "BAAI/bge-m3", "input": ["text1", "text2"]}'
```

## Modules

### Core Types and Exceptions

#### Data Types

::: sage.common.core.data_types
    options:
      show_root_heading: true
      show_source: false
      members:
        - Message
        - Record
        - Batch

#### Type System

::: sage.common.core.types
    options:
      show_root_heading: true
      show_source: false

#### Exceptions

::: sage.common.core.exceptions
    options:
      show_root_heading: true
      show_source: false
      members:
        - SAGEException
        - ConfigurationError
        - ValidationError
        - ServiceError

#### Constants

::: sage.common.core.constants
    options:
      show_root_heading: true
      show_source: false

### Configuration

#### Port Configuration (SagePorts) ⭐ NEW

::: sage.common.config.ports
    options:
      show_root_heading: true
      show_source: false
      members:
        - SagePorts
        - is_wsl

Centralized port configuration to avoid conflicts:

```python
from sage.common.config.ports import SagePorts

# Standard port allocation
SagePorts.GATEWAY_DEFAULT      # 8000 - sage-llm-gateway (OpenAI-compatible API)
SagePorts.LLM_DEFAULT          # 8001 - vLLM inference service
SagePorts.STUDIO_BACKEND       # 8080 - sage-studio backend
SagePorts.STUDIO_FRONTEND      # 5173 - sage-studio frontend (Vite)
SagePorts.EMBEDDING_DEFAULT    # 8090 - Embedding service
SagePorts.BENCHMARK_LLM        # 8901 - Benchmark LLM (WSL2 fallback)

# Auto-detect for WSL2 compatibility
port = SagePorts.get_recommended_llm_port()

# Check port availability
if SagePorts.is_available(8001):
    # Port is free
    pass
```

| 常量 | 端口 | 说明 |
|------|------|------|
| `SagePorts.GATEWAY_DEFAULT` | 8000 | UnifiedAPIServer / sage-llm-gateway OpenAI 兼容接口 |
| `SagePorts.LLM_DEFAULT` | 8001 | vLLM 推理服务（WSL2 可能不可用） |
| `SagePorts.LLM_WSL_FALLBACK` / `BENCHMARK_LLM` | 8901 | WSL2 推荐端口、benchmark LLM |
| `SagePorts.EMBEDDING_DEFAULT` | 8090 | Embedding Server（`sage llm serve --with-embedding` 默认值） |
| `SagePorts.STUDIO_BACKEND` / `STUDIO_FRONTEND` | 8080 / 5173 | Studio 后端 / 前端 |

> **WSL2 提示**：调用 `SagePorts.get_recommended_llm_port()` 与 `SagePorts.get_llm_ports()` 可以自动在 8001 → 8901 之间切换。`UnifiedInferenceClient.create()` 与 `sage llm serve` 均使用此顺序，避免“端口显示监听但拒绝连接”的 WSL2 问题。

#### Output Paths

::: sage.common.config.output_paths
    options:
      show_root_heading: true
      show_source: false
      members:
        - OutputPaths
        - get_output_dir
        - ensure_output_dir

#### Network Detection & HuggingFace Mirror ⭐ NEW

::: sage.common.config.network
    options:
      show_root_heading: true
      show_source: false
      members:
        - detect_china_mainland
        - get_hf_endpoint
        - ensure_hf_mirror_configured
        - get_network_region
        - HF_MIRROR_CN

SAGE 会自动检测网络区域并配置 HuggingFace 镜像：

```python
from sage.common.config import (
    detect_china_mainland,
    ensure_hf_mirror_configured,
    get_network_region,
)

# 自动检测并配置 (推荐在 CLI 入口调用)
ensure_hf_mirror_configured()  # 仅首次调用时检测，结果缓存

# 手动检测
is_china = detect_china_mainland()  # True/False
region = get_network_region()       # "china" | "international"
```

**自动配置的命令**：
- `sage llm run` - 运行 vLLM 服务
- `sage llm model download` - 下载模型
- `sage llm fine-tune` - 微调模型
- Embedding 相关服务

#### Environment Keys & 本地/云端策略

`UnifiedInferenceClient` 与 `sage llm serve` 统一读取以下键：

| 变量 | 示例 | 何时需要真实 Key |
|------|------|------------------|
| `SAGE_CHAT_API_KEY` | `sk-xxx` | 当 Gateway/vLLM 需要鉴权或回退到远端 OpenAI 兼容端点时填写。|
| `SAGE_CHAT_MODEL` / `SAGE_CHAT_BASE_URL` | `Qwen/Qwen2.5-7B-Instruct` / `http://localhost:8889/v1` | 本地/云端均可设置，用于覆盖自动探测模型名与端点。|
| `SAGE_EMBEDDING_BASE_URL` / `SAGE_EMBEDDING_MODEL` | `http://localhost:8090/v1` / `BAAI/bge-m3` | 自定义 Embedding 服务端点。|
| `SAGE_LLM_PORT` / `SAGE_EMBEDDING_PORT` | `8001` / `8090` | `sage llm serve` 会在写入配置文件时同步更新，可在 CI 中强制指定端口。|
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | `sk-...` / `https://api.openai.com/v1` | 直接调用 OpenAI 兼容 API 时使用（可指向自托管或官方服务）。|
| `HF_TOKEN` / `HF_ENDPOINT` | `hf_xxx` / `https://hf-mirror.com` | 下载 HuggingFace 模型（`ensure_hf_mirror_configured()` 会在大陆网络自动设置镜像）。|

> **本地开发 (GPU)**：优先运行 `sage llm serve --model <LLM> --embedding-model <Embedding>`，无需云端 Key，仅需 `HF_TOKEN` 用于模型下载。
>
> **云端 / 无 GPU**：预先在 `.env` 中填好 `SAGE_CHAT_*` + `SAGE_EMBEDDING_*`，或直接配置 `OPENAI_API_KEY`/`BASE_URL`，`UnifiedInferenceClient.create()` 会自动走云端。

### Components

#### UnifiedInferenceClient ⭐ NEW (Recommended)

Control Plane first 客户端：统一提供 `chat()`、`generate()`、`embed()`，自动探测 `SagePorts`、`.env` 与云端回退，并可通过 `create_for_model()` 协调引擎生命周期。

| 创建方式 | 示例 | 说明 |
|----------|------|------|
| 默认自动探测 | `UnifiedInferenceClient.create()` | 优先本地 `SagePorts` 端口 → `SAGE_*` 环境变量 → OpenAI 兼容云 API（仅在本地不可用时）。 |
| 外部 Control Plane | `create(control_plane_url="http://localhost:8000/v1")` | 复用 UnifiedAPIServer / Gateway，享受现有调度策略。 |
| 内嵌模式 | `create(embedded=True)` | 在进程内运行控制面，适合批处理脚本或 CI。 |
| 按模型创建 | `create_for_model("Qwen/Qwen2.5-7B-Instruct")` | 调用管理 API 自动拉起/复用 vLLM 引擎，确保 SLA。 |

> `sage llm serve` 负责在 `SagePorts.LLM_DEFAULT/EMBEDDING_DEFAULT` 上托管 OpenAI 兼容接口；`UnifiedInferenceClient.create()` 会自动连接这些端点。若不想启服务，可直接使用 `EmbeddingFactory` + `EmbeddingClientAdapter` 获得批量 embed 接口。

::: sage.llm.unified_client
    options:
      show_root_heading: true
      show_source: false
      members:
        - UnifiedInferenceClient
        - UnifiedClient
        - UnifiedClientConfig
        - UnifiedClientMode
        - InferenceResult

#### vLLM Service

::: sage.llm.service
    options:
      show_root_heading: true
      show_source: false
      members:
        - VLLMService
        - VLLMServiceConfig

#### Control Plane Service

::: sage.llm.control_plane_service
    options:
      show_root_heading: true
      show_source: false
      members:
        - ControlPlaneVLLMService
        - ControlPlaneVLLMServiceConfig

#### Unified API Server

::: sage.llm.unified_api_server
    options:
      show_root_heading: true
      show_source: false
      members:
        - UnifiedAPIServer
        - UnifiedServerConfig
        - BackendInstanceConfig
        - SchedulingPolicyType
        - create_unified_server

#### Compatibility Adapters ⭐ NEW

::: sage.llm.compat
    options:
      show_root_heading: true
      show_source: false
      members:
        - LLMClientAdapter
        - EmbeddingClientAdapter
        - create_llm_client_compat
        - create_embedding_client_compat

Adapters for integrating with legacy code:

```python
from sage.llm import (
    EmbeddingClientAdapter,
    create_embedding_client_compat
)

# Wrap an existing embedding implementation
adapted = EmbeddingClientAdapter(existing_embedder)
vectors = adapted.embed(["text1", "text2"])  # Batch interface
```

#### Embedding Services

::: sage.common.components.sage_embedding
    options:
      show_root_heading: true
      show_source: false
      members:
        - EmbeddingFactory
        - EmbeddingService
        - EmbeddingServiceConfig
        - BaseEmbedding
        - EmbeddingRegistry
        - EmbeddingProtocol
        - EmbeddingClientAdapter
        - get_embedding_model
        - list_embedding_models
        - check_model_availability

**Supported Embedding Providers:**

| Provider | Method | Description |
|----------|--------|-------------|
| HuggingFace | `hf` | Local models (BGE, MiniLM, etc.) |
| OpenAI | `openai` | text-embedding-3-small/large |
| Jina | `jina` | Multilingual, late chunking |
| Zhipu | `zhipu` | Chinese-optimized |
| Cohere | `cohere` | Multilingual |
| Bedrock | `bedrock` | AWS Bedrock |
| Ollama | `ollama` | Local deployment |
| SiliconCloud | `siliconcloud` | China-accessible |
| Hash | `hash` | Lightweight (testing) |
| Mock | `mockembedder` | Unit tests |

```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory,
    EmbeddingClientAdapter,
    get_embedding_model
)

# Create embedding model
embedder = get_embedding_model("hf", model="BAAI/bge-small-zh-v1.5")
vector = embedder.embed("hello world")  # Single text

# For batch interface, wrap with adapter
adapter = EmbeddingClientAdapter(embedder)
vectors = adapter.embed(["text1", "text2"])  # Batch
```

### Model Registry

::: sage.common.model_registry
    options:
      show_root_heading: true
      show_source: false
      members:
        - ModelRegistry
        - register_model
        - get_model

### Utilities

#### Logging

::: sage.common.utils.logging
    options:
      show_root_heading: true
      show_source: false
      members:
        - setup_logger
        - get_logger
        - LogLevel

#### Serialization

::: sage.common.utils.serialization
    options:
      show_root_heading: true
      show_source: false
      members:
        - serialize
        - deserialize
        - to_json
        - from_json

#### System Utilities

::: sage.common.utils.system
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_cpu_count
        - get_memory_info
        - check_gpu_available

#### Network Utilities

::: sage.common.utils.network
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_free_port
        - check_port_available
        - get_local_ip

## Quick Examples

### Using Core Data Types

```python
from sage.common.core.data_types import Message, Record

# Create a message
msg = Message(
    key="user123",
    value={"text": "Hello, world!"},
    timestamp=1234567890
)

# Create a record
record = Record(data="sample data", metadata={"source": "api"})
```

### Using Embedding Service

```python
from sage.common.components.sage_embedding import EmbeddingFactory

# Create OpenAI embedding service
embedding = EmbeddingFactory.create_embedding(
    provider="openai",
    model_name="text-embedding-3-small"
)

# Encode text
vector = embedding.encode("Hello, world!")
print(f"Embedding dimension: {len(vector)}")

# Batch encode
texts = ["text1", "text2", "text3"]
vectors = embedding.encode_batch(texts)
```

### Using vLLM Service

```python
from sage.llm import VLLMService

# Initialize vLLM service
vllm = VLLMService(
    model_name="meta-llama/Llama-2-7b-chat-hf",
    base_url="http://localhost:8000"
)

# Generate text
response = vllm.generate(
    prompt="What is SAGE?",
    max_tokens=100,
    temperature=0.7
)
print(response)
```

### Configuration Management

```python
from sage.common.config.output_paths import OutputPaths, ensure_output_dir

# Get output directory
output_dir = OutputPaths.get_output_dir("my_app")

# Ensure directory exists
data_dir = ensure_output_dir("my_app/data")

# Use in your code
output_file = output_dir / "results.json"
```

### Logging

```python
from sage.common.utils.logging import setup_logger, get_logger

# Setup logger
setup_logger(level="INFO", log_file="app.log")

# Get logger
logger = get_logger(__name__)

# Use logger
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred")
```

### Serialization

```python
from sage.common.utils.serialization import to_json, from_json

# Serialize to JSON
data = {"name": "SAGE", "version": "1.0.0"}
json_str = to_json(data)

# Deserialize from JSON
loaded_data = from_json(json_str)
```

### System Utilities

```python
from sage.common.utils.system import (
    get_cpu_count,
    get_memory_info,
    check_gpu_available
)

# Get system info
cpu_count = get_cpu_count()
memory_info = get_memory_info()
has_gpu = check_gpu_available()

print(f"CPUs: {cpu_count}")
print(f"Memory: {memory_info['total'] / 1024**3:.2f} GB")
print(f"GPU available: {has_gpu}")
```

### Network Utilities

```python
from sage.common.utils.network import get_free_port, get_local_ip

# Get a free port
port = get_free_port()
print(f"Free port: {port}")

# Get local IP
ip = get_local_ip()
print(f"Local IP: {ip}")
```

### Exception Handling

```python
from sage.common.core.exceptions import (
    SAGEException,
    ConfigurationError,
    ValidationError
)

try:
    # Your code here
    if not config_valid:
        raise ConfigurationError("Invalid configuration")
except SAGEException as e:
    logger.error(f"SAGE error: {e}")
```

## Module Organization

```
sage.common/
├── core/                    # Core types and exceptions
│   ├── data_types.py       # Message, Record, Batch
│   ├── types.py            # Type definitions
│   ├── exceptions.py       # Exception classes
│   └── constants.py        # Constants
├── components/              # Reusable components
│   ├── sage_embedding.py   # Embedding services
│   └── sage_llm.py        # vLLM integration
├── config/                  # Configuration
│   └── output_paths.py     # Output path management
├── model_registry/          # Model registry
│   └── ...                 # Model management
└── utils/                   # Utilities
    ├── logging/            # Logging utilities
    ├── serialization/      # Serialization utils
    ├── system/             # System utilities
    └── network/            # Network utilities
```

## Architecture Notes

**Layer**: L1 (Foundation)

**Can be imported by**: L2-L6 (all upper layers)

**Must NOT import from**: sage.kernel, sage.middleware, sage.libs, sage.apps

**Dependencies**: Only standard library and external packages (e.g., openai, transformers)

## See Also

- [Package Architecture](../../dev-notes/package-architecture.md)
- [Common Utilities Guide](../../guides/packages/sage-common/overview.md)
- [L1 Layer Overview](../../guides/index.md#l1-基础设施层)
