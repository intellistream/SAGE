# Pull Request: sageLLM Hybrid Scheduler

## 🎯 PR 概述

**分支**: `feature/embedding_lmm_mixed_scheduler` → `main`

**标题**: feat(sage-llm): 实现 LLM 和 Embedding 混合调度系统

### 📋 变更摘要

本 PR 实现了 sageLLM 混合调度系统，将 `IntelligentLLMClient` 和 `IntelligentEmbeddingClient` 合并为统一的 `UnifiedInferenceClient`，并通过增强的 Control Plane 实现 LLM 和 Embedding 请求在统一 GPU 资源池内的混合调度。

**核心价值**:
- 🔄 **统一入口**: 单一客户端处理 LLM (chat/generate) 和 Embedding 请求
- 📊 **智能调度**: 基于请求类型、负载状态和优先级的自适应调度策略
- 🚀 **资源优化**: Embedding 批处理聚合，减少 GPU 碎片化，提高吞吐量
- 🔌 **OpenAI 兼容**: 统一 API Server 完全兼容 OpenAI API 规范
- ✅ **向后兼容**: 现有 `IntelligentLLMClient` 和 `IntelligentEmbeddingClient` 代码无需修改

---

## 🔄 客户端选择指南

### 三种客户端并存

本 PR **新增** `UnifiedInferenceClient`，但 **保留** 原有的 `IntelligentLLMClient` 和 `IntelligentEmbeddingClient`：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         用户可选的客户端                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────┐    ┌─────────────────────────────────────┐  │
│  │ UnifiedInferenceClient │    │ IntelligentLLMClient (保留)         │  │
│  │ (新增 - 推荐)          │    │ IntelligentEmbeddingClient (保留)   │  │
│  │                       │    │                                     │  │
│  │ • chat()              │    │ • 独立使用场景                       │  │
│  │ • generate()          │    │ • 现有代码无需任何修改               │  │
│  │ • embed()             │    │ • 简单场景更简洁                     │  │
│  └───────────┬───────────┘    └──────────────┬──────────────────────┘  │
│              │                               │                          │
│              └───────────────┬───────────────┘                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┤
│  │              sageLLM Control Plane (共享调度)                        │
│  └─────────────────────────────────────────────────────────────────────┤
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┤
│  │                    统一资源池 (GPU Instances)                        │
│  └─────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────┘
```

### 如何选择？

| 场景 | 推荐客户端 | 理由 |
|------|-----------|------|
| 新项目，同时需要 LLM 和 Embedding | `UnifiedInferenceClient` | 统一入口，享受混合调度 |
| 现有项目，只使用 LLM | `IntelligentLLMClient` | 无需修改，向后兼容 |
| 现有项目，只使用 Embedding | `IntelligentEmbeddingClient` | 无需修改，向后兼容 |
| 简单脚本，只需要单一功能 | 独立客户端 | 代码更简洁 |
| 需要高级调度（Control Plane） | `UnifiedInferenceClient` | 支持 Control Plane 模式 |

### 代码示例

```python
# 方式 1: 新代码 - 使用 UnifiedInferenceClient (推荐)
from sage.common.components.sage_llm import UnifiedInferenceClient
client = UnifiedInferenceClient.create_auto()
response = client.chat([{"role": "user", "content": "Hello"}])
vectors = client.embed(["text1", "text2"])

# 方式 2: 现有代码 - 继续使用独立客户端 (仍然有效)
from sage.common.components.sage_llm import IntelligentLLMClient
from sage.common.components.sage_embedding import IntelligentEmbeddingClient
llm = IntelligentLLMClient.create_auto()
embedder = IntelligentEmbeddingClient.create_auto()
```

> **重要**: 三种客户端**都连接到同一个 sageLLM 资源池**，享受混合调度的好处。选择哪种客户端取决于你的使用场景和代码风格偏好。

---

## 📊 变更统计

| 类型 | 数量 |
|------|------|
| 新增文件 | 12 |
| 修改文件 | 8 |
| 新增代码行 | ~6,500 行 |
| 单元测试 | 55 个 |
| 集成测试 | 87 个 |
| CLI 测试 | 23 个 |
| **总测试数** | **165 个** |

---

## 🏗️ 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (Application Layer)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                      UnifiedInferenceClient                              │
│                 chat() | generate() | embed()                            │
│        ┌─────────────────────┬─────────────────────┐                    │
│        │   Simple Mode       │  Control Plane Mode │                    │
│        │  (直连后端 API)      │  (通过调度器路由)    │                    │
│        └─────────────────────┴─────────────────────┘                    │
├─────────────────────────────────────────────────────────────────────────┤
│                       UnifiedAPIServer                                   │
│              (OpenAI-Compatible REST API Gateway)                        │
│   ┌────────────────┬────────────────┬────────────────┬──────────────┐   │
│   │ /v1/chat/      │ /v1/           │ /v1/           │ /v1/models   │   │
│   │ completions    │ completions    │ embeddings     │ /health      │   │
│   └────────────────┴────────────────┴────────────────┴──────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                    sageLLM Control Plane (增强版)                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                   RequestClassifier                              │   │
│   │    (请求分类: LLM_CHAT / LLM_GENERATE / EMBEDDING)               │   │
│   ├─────────────────────────────────────────────────────────────────┤   │
│   │                  HybridSchedulingPolicy                          │   │
│   │  • 请求类型分组          • Embedding 批处理聚合                    │   │
│   │  • 优先级调度            • 混合实例负载均衡                        │   │
│   │  • 专用实例优先          • 可配置 LLM 回退策略                     │   │
│   ├─────────────────────────────────────────────────────────────────┤   │
│   │    ExecutionCoordinator        EmbeddingExecutor                 │   │
│   │    (LLM 请求执行)              (Embedding 批处理执行)             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                        统一资源池 (GPU Pool)                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│   │  vLLM Instance  │  │  vLLM Instance  │  │  TEI Instance   │        │
│   │  (LLM Only)     │  │  (LLM+Embed)    │  │  (Embed Only)   │        │
│   │  Type: GENERAL  │  │  Type: MIXED    │  │  Type: EMBEDDING│        │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 核心组件关系

```
UnifiedInferenceClient
    │
    ├── Simple Mode ──────────────────────────────────────┐
    │       │                                              │
    │       ├── OpenAI Client (LLM) ─────────────────────► Backend LLM
    │       └── OpenAI Client (Embedding) ───────────────► Backend Embedding
    │
    └── Control Plane Mode
            │
            └── ControlPlaneManager
                    │
                    ├── RequestClassifier ──► RequestType 分类
                    │
                    ├── HybridSchedulingPolicy
                    │       │
                    │       ├── LLM 请求 ──► 现有调度策略 (Adaptive/FIFO/Priority)
                    │       └── Embedding 请求 ──► 批处理聚合 + EmbeddingExecutor
                    │
                    └── ExecutionCoordinator ──► Backend Instances
```

---

## 📁 文件变更清单

### 新增文件

#### Control Plane 核心 (`sageLLM/control_plane/`)

| 文件 | 行数 | 描述 |
|------|------|------|
| `request_classifier.py` | ~576 | 请求分类器：自动识别 LLM/Embedding 请求，筛选兼容实例 |
| `strategies/hybrid_policy.py` | ~885 | 混合调度策略：请求分组、Embedding 批处理、负载均衡 |

#### 统一客户端与服务器 (`sage_llm/`)

| 文件 | 行数 | 描述 |
|------|------|------|
| `unified_client.py` | ~1062 | 统一推理客户端：合并 LLM 和 Embedding 接口 |
| `unified_api_server.py` | ~956 | OpenAI 兼容 API 服务器：统一 REST 网关 |

#### CLI 命令 (`sage-cli/`)

| 文件 | 行数 | 描述 |
|------|------|------|
| `commands/apps/inference.py` | ~650 | 推理服务管理命令：start/stop/status/config |

#### 测试文件

| 文件 | 测试数 | 描述 |
|------|--------|------|
| `tests/unit/.../test_unified_client.py` | 38 | 客户端单元测试 |
| `tests/unit/.../test_compat.py` | 17 | 向后兼容测试 |
| `tests/integration/conftest.py` | - | 测试 fixtures 和 Mock 后端 |
| `tests/integration/test_hybrid_scheduling_e2e.py` | 22 | 混合调度端到端测试 |
| `tests/integration/test_unified_api_server.py` | 33 | API 服务器集成测试 |
| `tests/integration/test_unified_client_e2e.py` | 32 | 客户端集成测试 |
| `sage-cli/tests/test_inference_cli.py` | 23 | CLI 命令测试 |

### 修改文件

| 文件 | 变更类型 | 描述 |
|------|----------|------|
| `sageLLM/control_plane/types.py` | 扩展 | 新增 `RequestType` 枚举、扩展 `RequestMetadata` 和 `ExecutionInstance` |
| `sageLLM/control_plane/strategies/__init__.py` | 扩展 | 导出 `HybridSchedulingPolicy` |
| `sageLLM/control_plane/__init__.py` | 扩展 | 导出新增类型 |
| `sage_llm/__init__.py` | 扩展 | 导出 `UnifiedInferenceClient` 和 `UnifiedAPIServer` |
| `sage_llm/client.py` | 兼容层 | 保持向后兼容，内部使用 UnifiedInferenceClient |
| `sage_embedding/client.py` | 兼容层 | 保持向后兼容，内部使用 UnifiedInferenceClient |
| `sage-cli/commands/apps/__init__.py` | 扩展 | 注册 inference 命令组 |
| `sage-cli/main.py` | 扩展 | 添加 inference 子命令 |

---

## 🔧 核心实现详情

### 1. 请求类型扩展 (`types.py`)

```python
class RequestType(Enum):
    """请求类型枚举"""
    LLM_CHAT = "llm_chat"        # 对话请求
    LLM_GENERATE = "llm_generate" # 文本生成请求
    EMBEDDING = "embedding"       # 向量嵌入请求

class ExecutionInstanceType(Enum):
    """实例类型枚举 - 新增混合类型"""
    GENERAL = "general"
    PREFILLING = "prefilling"
    DECODING = "decoding"
    HYBRID = "hybrid"
    EMBEDDING = "embedding"       # 新增：纯 Embedding 实例
    LLM_EMBEDDING = "llm_embedding" # 新增：混合实例

@dataclass
class RequestMetadata:
    # ... 现有字段 ...

    # 新增 Embedding 相关字段
    request_type: RequestType = RequestType.LLM_CHAT
    embedding_texts: list[str] | None = None
    embedding_model: str | None = None
    embedding_batch_size: int = 32
```

### 2. 请求分类器 (`request_classifier.py`)

```python
class RequestClassifier:
    """请求分类器 - 自动识别请求类型并筛选兼容实例"""

    def classify(self, request: RequestMetadata) -> RequestType:
        """分类逻辑:
        1. 如果 request_type 已设置，直接返回
        2. 如果 embedding_texts 非空，返回 EMBEDDING
        3. 如果 prompt 非空，根据上下文返回 LLM_CHAT 或 LLM_GENERATE
        4. 默认返回 LLM_CHAT
        """

    def get_compatible_instances(
        self,
        request_type: RequestType,
        instances: list[ExecutionInstance],
    ) -> list[ExecutionInstance]:
        """根据请求类型筛选兼容的执行实例"""

    def validate_request(self, request: RequestMetadata) -> ValidationResult:
        """验证请求完整性"""
```

### 3. 混合调度策略 (`hybrid_policy.py`)

```python
@dataclass
class HybridSchedulingConfig:
    embedding_batch_size: int = 32          # Embedding 批大小
    embedding_priority: str = "normal"       # high/normal/low/adaptive
    llm_fallback_policy: str = "adaptive"   # fifo/priority/slo_aware/adaptive
    hybrid_instance_ratio: float = 0.7      # 混合实例 LLM:Embedding 比例
    prefer_specialized_instances: bool = True

class HybridSchedulingPolicy(SchedulingPolicy):
    """混合调度策略"""

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """调度逻辑:
        1. 按 request_type 分组请求
        2. Embedding 请求：批量聚合 → 优先专用实例 → 次选混合实例
        3. LLM 请求：使用配置的回退策略 → 排除纯 Embedding 实例
        4. 混合实例负载均衡
        """

    def _aggregate_embedding_batches(
        self,
        requests: list[RequestMetadata],
    ) -> list[EmbeddingBatch]:
        """将多个 Embedding 请求聚合为批次"""
```

### 4. 统一推理客户端 (`unified_client.py`)

```python
class UnifiedInferenceClient:
    """统一推理客户端 - 合并 LLM 和 Embedding 功能"""

    @classmethod
    def create_auto(
        cls,
        llm_model: str | None = None,
        embedding_model: str | None = None,
        **kwargs,
    ) -> UnifiedInferenceClient:
        """自动检测模式:
        1. 环境变量: SAGE_UNIFIED_BASE_URL
        2. 本地 LLM: localhost:8001, 8000
        3. 本地 Embedding: localhost:8090, 8080
        4. 云端 API: DashScope
        """

    @classmethod
    def create_with_control_plane(
        cls,
        instances: list[dict],
        scheduling_policy: str = "hybrid",
        **kwargs,
    ) -> UnifiedInferenceClient:
        """Control Plane 模式 - 支持高级调度"""

    def chat(self, messages: list[dict], **kwargs) -> str:
        """聊天补全"""

    def generate(self, prompt: str, **kwargs) -> str:
        """文本生成"""

    def embed(self, texts: list[str], **kwargs) -> list[list[float]]:
        """文本嵌入"""
```

### 5. 统一 API 服务器 (`unified_api_server.py`)

```python
class UnifiedAPIServer:
    """OpenAI 兼容的统一 API 服务器"""

    # 端点
    # GET  /              # 服务器信息
    # GET  /health        # 健康检查
    # GET  /v1/models     # 模型列表
    # POST /v1/chat/completions   # 聊天补全
    # POST /v1/completions        # 文本补全
    # POST /v1/embeddings         # 向量嵌入

    def __init__(self, config: UnifiedServerConfig):
        """初始化服务器"""

    async def start(self) -> None:
        """启动服务器"""

    async def stop(self) -> None:
        """优雅关闭"""
```

### 6. CLI 命令 (`inference.py`)

```bash
# 启动统一推理服务
sage inference start \
    --llm-model Qwen/Qwen2.5-7B-Instruct \
    --embedding-model BAAI/bge-m3 \
    --scheduling-policy hybrid \
    --port 8000 \
    --background

# 停止服务
sage inference stop [--force]

# 查看状态
sage inference status

# 查看日志
sage inference logs [--follow] [--lines 100]

# 配置管理
sage inference config show
sage inference config set --key llm_model --value "..."
```

---

## 🧪 测试覆盖

### 测试统计

| 类别 | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| 单元测试 - 客户端 | `test_unified_client.py` | 38 | ✅ 全部通过 |
| 单元测试 - 兼容性 | `test_compat.py` | 17 | ✅ 全部通过 |
| 集成测试 - 调度 | `test_hybrid_scheduling_e2e.py` | 22 | ✅ 全部通过 |
| 集成测试 - 服务器 | `test_unified_api_server.py` | 33 | ✅ 全部通过 |
| 集成测试 - 客户端 | `test_unified_client_e2e.py` | 32 | ✅ 全部通过 |
| CLI 测试 | `test_inference_cli.py` | 23 | ✅ 全部通过 |
| **总计** | **6 个测试文件** | **165** | ✅ |

### 测试运行命令

```bash
# 运行所有测试
cd /home/yjy/SAGE

# 单元测试
conda run -n sage python -m pytest packages/sage-common/tests/unit/components/sage_llm/ -v

# 集成测试
conda run -n sage python -m pytest packages/sage-common/tests/integration/ -v

# CLI 测试
conda run -n sage python -m pytest packages/sage-cli/tests/test_inference_cli.py -v

# 全量测试
conda run -n sage python -m pytest \
    packages/sage-common/tests/unit/components/sage_llm/ \
    packages/sage-common/tests/integration/ \
    packages/sage-cli/tests/test_inference_cli.py \
    -v --tb=short
```

### 关键测试场景

| 场景 | 描述 | 覆盖 |
|------|------|------|
| 请求分类 | LLM/Embedding 自动识别 | ✅ |
| 实例筛选 | 按类型筛选兼容实例 | ✅ |
| Embedding 批处理 | 请求聚合与拆分 | ✅ |
| 混合调度 | LLM + Embedding 并发处理 | ✅ |
| 端点兼容 | OpenAI API 规范 | ✅ |
| 自动检测 | 本地/云端服务检测 | ✅ |
| 向后兼容 | 现有客户端无修改 | ✅ |
| 单例模式 | 客户端实例缓存 | ✅ |
| 错误处理 | 超时、重试、降级 | ✅ |
| CLI 命令 | start/stop/status | ✅ |

---

## 📖 使用示例

### 1. 统一客户端 - 自动检测模式

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 自动检测最佳可用服务
client = UnifiedInferenceClient.create_auto()

# 聊天
response = client.chat([
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": "什么是混合调度？"}
])
print(response)

# 文本生成
text = client.generate("从前有座山，山上有座庙，")
print(text)

# 向量嵌入
vectors = client.embed(["文本1", "文本2", "文本3"])
print(f"维度: {len(vectors[0])}")
```

### 2. 统一客户端 - Control Plane 模式

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 配置多实例 + 混合调度
client = UnifiedInferenceClient.create_with_control_plane(
    instances=[
        {
            "host": "localhost",
            "port": 8001,
            "model_name": "Qwen/Qwen2.5-7B-Instruct",
            "instance_type": "llm",
        },
        {
            "host": "localhost",
            "port": 8090,
            "model_name": "BAAI/bge-m3",
            "instance_type": "embedding",
        },
    ],
    scheduling_policy="hybrid",
    embedding_batch_size=32,
)

# 使用方式与 Simple 模式完全相同
response = client.chat([{"role": "user", "content": "Hello"}])
vectors = client.embed(["Hello", "World"])
```

### 3. 启动统一 API 服务器

```python
from sage.common.components.sage_llm import (
    UnifiedAPIServer,
    UnifiedServerConfig,
    BackendInstanceConfig,
)

config = UnifiedServerConfig(
    host="0.0.0.0",
    port=8000,
    llm_backends=[
        BackendInstanceConfig(
            host="localhost",
            port=8001,
            model_name="Qwen/Qwen2.5-7B-Instruct",
            instance_type="llm",
        ),
    ],
    embedding_backends=[
        BackendInstanceConfig(
            host="localhost",
            port=8090,
            model_name="BAAI/bge-m3",
            instance_type="embedding",
        ),
    ],
    scheduling_policy="hybrid",
)

server = UnifiedAPIServer(config)
server.start()  # 阻塞运行
```

### 4. 使用 CLI

```bash
# 启动服务 (前台)
sage inference start

# 启动服务 (后台 + 自定义配置)
sage inference start \
    --llm-backend http://localhost:8001 \
    --embedding-backend http://localhost:8090 \
    --scheduling-policy hybrid \
    --port 8000 \
    --background

# 查看状态
sage inference status

# 查看日志
sage inference logs --follow

# 停止服务
sage inference stop
```

### 5. 使用 OpenAI SDK 调用

```python
from openai import OpenAI

# 连接统一 API 服务器
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",  # 本地服务无需 API Key
)

# 聊天
response = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)

# 嵌入
response = client.embeddings.create(
    model="BAAI/bge-m3",
    input=["Hello", "World"],
)
print(len(response.data[0].embedding))
```

---

## 🔧 配置参考

### 环境变量

| 变量名 | 用途 | 示例值 |
|--------|------|--------|
| `SAGE_UNIFIED_BASE_URL` | 统一服务端点 | `http://localhost:8000/v1` |
| `SAGE_CHAT_BASE_URL` | LLM 服务端点 | `http://localhost:8001/v1` |
| `SAGE_EMBEDDING_BASE_URL` | Embedding 服务端点 | `http://localhost:8090/v1` |
| `SAGE_CHAT_MODEL` | 默认 LLM 模型 | `Qwen/Qwen2.5-7B-Instruct` |
| `SAGE_EMBEDDING_MODEL` | 默认 Embedding 模型 | `BAAI/bge-m3` |
| `SAGE_CHAT_API_KEY` | LLM API 密钥 | `sk-xxx` |

### 调度策略配置

```python
HybridSchedulingConfig(
    embedding_batch_size=32,           # Embedding 批处理大小
    embedding_priority="normal",        # high/normal/low/adaptive
    llm_fallback_policy="adaptive",    # fifo/priority/slo_aware/adaptive
    hybrid_instance_ratio=0.7,         # 混合实例 LLM:Embedding 比例
    prefer_specialized_instances=True, # 优先使用专用实例
    max_embedding_wait_ms=50.0,        # 批处理最大等待时间
)
```

---

## ⚠️ 破坏性变更

**无破坏性变更**。本 PR 完全向后兼容：

1. ✅ `IntelligentLLMClient` 现有代码无需修改
2. ✅ `IntelligentEmbeddingClient` 现有代码无需修改
3. ✅ 现有 API 签名保持不变
4. ✅ 现有环境变量继续生效

---

## 🔮 未来架构演进

### 当前架构

```
sage-common/components/
├── sage_embedding/        # 独立的 Embedding 后端适配层（~20 个文件）
│   ├── client.py          # IntelligentEmbeddingClient
│   ├── factory.py         # EmbeddingFactory (HF, OpenAI, Jina...)
│   └── wrappers/          # 各种后端封装
│
└── sage_llm/              # LLM 组件 + sageLLM 调度框架
    ├── client.py          # IntelligentLLMClient
    ├── unified_client.py  # UnifiedInferenceClient (本 PR 新增)
    └── sageLLM/           # Control Plane 调度框架
        └── control_plane/
            └── strategies/hybrid_policy.py  # 混合调度策略
```

### 本 PR 的设计决策

**保持 `sage_embedding` 独立**，原因：

| 原因 | 说明 |
|------|------|
| **职责分离** | `sage_embedding` 是"后端适配层"，`sageLLM` 是"调度框架层" |
| **最小变更** | 本 PR 目标是"实现混合调度"，而非"重构目录结构" |
| **向后兼容** | 现有 `from sage_embedding import ...` 的代码无需修改 |
| **独立演进** | Embedding 后端种类繁多，独立维护更清晰 |

`UnifiedInferenceClient` 已在**逻辑上**统一了 LLM 和 Embedding，物理目录的整合可留待后续。

### 未来可选重构 (TODO)

如果团队决定进一步整合，建议的目录结构：

```
sage_llm/
├── sageLLM/
│   ├── control_plane/     # 调度层 (不变)
│   └── backends/          # 后端适配层 (新)
│       ├── llm/           # LLM 后端 (vLLM, OpenAI, ...)
│       └── embedding/     # 从 sage_embedding 迁移
├── unified_client.py
└── ...
```

**重构范围**：
- 迁移 `sage_embedding/` 到 `sage_llm/sageLLM/backends/embedding/`
- 更新所有 import 路径
- 添加兼容性 re-export 层
- 更新文档和测试

> **建议**: 开一个单独的 Issue 跟踪此重构，不在本 PR 中进行。

---

## 📋 Checklist

- [x] 代码符合项目编码规范 (`sage-dev quality` 通过)
- [x] 所有单元测试通过 (55 个)
- [x] 所有集成测试通过 (87 个)
- [x] 所有 CLI 测试通过 (23 个)
- [x] 类型注解完整 (Mypy 检查通过)
- [x] 文档字符串完整 (所有公开 API)
- [x] 向后兼容性验证通过
- [x] 开发文档已更新 (`DEVELOPMENT_SUMMARY.md`)


*PR 创建日期: 2025年11月27日*
