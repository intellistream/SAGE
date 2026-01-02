# API 参考

SAGE 各个包的完整 API 文档。

## 📚 API 文档概览

API 文档按照 SAGE 的 **L1-L6 分层架构**组织，帮助您快速找到所需的 API 接口。

## 🔧 端口与环境变量配置

### 端口分配表 (SagePorts)

所有端口号必须使用 `sage.common.config.ports.SagePorts`，禁止硬编码。

| 常量 | 端口 | 用途 |
|------|------|------|
| `GATEWAY_DEFAULT` | 8000 | sage-llm-gateway (OpenAI 兼容 API Gateway) |
| `LLM_DEFAULT` | 8001 | vLLM 推理服务 |
| `LLM_WSL_FALLBACK` | 8901 | WSL2 备用 LLM 端口 |
| `STUDIO_BACKEND` | 8080 | sage-studio 后端 API |
| `STUDIO_FRONTEND` | 5173 | sage-studio 前端 (Vite) |
| `EMBEDDING_DEFAULT` | 8090 | Embedding 服务 |
| `BENCHMARK_LLM` | 8901 | Benchmark 专用 LLM 端口 |

```python
from sage.common.config.ports import SagePorts

# 推荐用法
port = SagePorts.LLM_DEFAULT           # 8001
gateway_port = SagePorts.GATEWAY_DEFAULT  # 8000

# WSL2 环境推荐
port = SagePorts.get_recommended_llm_port()  # 自动检测 WSL2 并选择合适端口
```

### 关键环境变量

从 `.env.template` 配置，详见 [配置决策对照表](#配置决策对照表)。

| 变量 | 用途 | 何时需要真实 Key |
|------|------|-----------------|
| `OPENAI_API_KEY` | OpenAI 兼容 API 调用 | 使用云端/自托管 OpenAI 兼容服务时 |
| `HF_TOKEN` | HuggingFace 模型下载 | 下载私有模型时 |
| `SAGE_CHAT_*` | Gateway/Studio LLM 访问密钥 | 本地 vLLM/Gateway 需要鉴权时 |
| `VLLM_API_KEY` | 本地 vLLM 认证 | 本地开发可用 `token-abc123` |

**本地开发 Mock**: 如果仅测试框架逻辑，可设置 mock 值或使用本地模型。

## 🏗️ 按架构层级浏览

### 🔹 L1: 基础设施层

#### [sage-common API](common/index.md)

基础工具库，提供通用的数据类型、配置管理和工具函数。

**主要模块**：
- `sage.common.core` - 核心类型和异常
- `sage.llm` - **UnifiedInferenceClient** ⭐ (LLM + Embedding 统一客户端)
- `sage.common.components.sage_embedding` - **EmbeddingFactory** (Embedding 服务)
- `sage.common.config.ports` - **SagePorts** ⭐ (统一端口配置)
- `sage.common.utils` - 日志、序列化等工具

👉 [查看 Common API](common/index.md)

---

### 🔹 L2: 平台服务层

#### [sage-platform API](platform/index.md)

平台抽象层，提供队列、存储、服务等基础设施抽象。

**主要模块**：
- `sage.platform.queue` - 队列抽象（Python Queue、Ray Queue、RPC Queue）
- `sage.platform.storage` - Key-Value 存储后端
- `sage.platform.service` - 服务基类

👉 [查看 Platform API](platform/index.md)

---

### 🔹 L3: 核心层

#### [sage-kernel API](kernel/index.md)

执行引擎和流式处理核心。

**主要模块**：
- `sage.kernel.api` - DataStream API、Environment、Functions
- `sage.kernel.operators` - Map、Filter、Join 等算子
- `sage.kernel.runtime` - 运行时系统（通信、任务管理）
- `sage.kernel.graph` - 图编译器

**详细 API 文档**：
- [DataStreams API](../guides/packages/sage-kernel/api/datastreams.md) - 数据流 API
- [Functions API](../guides/packages/sage-kernel/api/functions.md) - 函数接口
- [Environments API](../guides/packages/sage-kernel/api/environments.md) - 执行环境
- [Connected Streams API](../guides/packages/sage-kernel/api/connected-streams.md) - 连接流

👉 [查看 Kernel API](kernel/index.md)

---

#### [sage-libs API](libs/index.md)

AI 组件库，包含 RAG、Agents、Embeddings 等高级功能。

**主要模块**：
- `sage.libs.agentic.agents.action.tool_selection` - **工具选择器** ⭐ (Keyword, Embedding, Hybrid, Gorilla, DFSDT)
- `sage.libs.agentic.agents.planning` - **规划器** ⭐ (Hierarchical, ReAct, ToT) + **时机决策**
- `sage.libs.agentic.agents.runtime` - Agent 运行时
- `sage.libs.rag` - RAG Pipeline（检索、生成、评估）
- `sage.libs.tools` - 工具集（搜索、图像、文本处理）

**详细 API 文档**：
- [RAG API 参考](../guides/packages/sage-libs/rag/api_reference.md) - RAG 组件 API
- [算子参考](../guides/packages/sage-libs/operators_reference.md) - Libs 算子 API

👉 [查看 Libs API](libs/index.md)

---

### 🔹 L4: 中间件层

#### [sage-middleware API](middleware/index.md)

领域特定的中间件服务。

**主要模块**：
- `sage.middleware.components.sage_mem` - NeuroMem 记忆管理 + Multimodal 存储
- `sage.middleware.components.sage_db` - 数据库服务
- `sage.middleware.components.sage_refiner` - Refiner 服务
- `sage.middleware.services.autostop` - AutoStop 服务

**详细 API 文档**：
- [服务 API](../guides/packages/sage-middleware/service/service_api.md) - 中间件服务接口

👉 [查看 Middleware API](middleware/index.md)

---

### 🔹 L5-L6: 应用层和接口层

应用层（sage-apps、sage-benchmark）和接口层（sage-studio、sage-cli、sage-tools）的文档请参考 [用户指南](../guides/index.md)。

---

## 📖 API 文档生成

API 文档通过以下方式自动生成：

- **mkdocstrings** - 从 Python docstrings 自动生成文档
- **Google style** - 使用 Google 风格的 docstring 格式
- **类型提示** - 完整的类型注解支持

## 🚀 快速开始

### 推荐: UnifiedInferenceClient (LLM + Embedding)

**Python 方式**:

```python
from sage.llm import UnifiedInferenceClient
from sage.common.config.ports import SagePorts

# Auto-detect available services
client = UnifiedInferenceClient.create_auto()

# Or use Control Plane mode (recommended for production)
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
# Chat Completion (Gateway 端口 8000)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Embedding (端口 8090)
curl -X POST http://localhost:8090/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-m3",
    "input": ["text1", "text2"]
  }'

# 直连 vLLM (端口 8901)
curl -X POST http://localhost:8901/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Kernel Pipeline 示例

```python
from sage.kernel.api.local_environment import LocalStreamEnvironment

env = LocalStreamEnvironment("my_app")
stream = (env
    .from_source(data_source)
    .map(transform_function)
    .filter(filter_function)
    .sink(output_sink)
)
env.execute()
```

### Agent 框架示例

```python
from sage.libs.agentic.agents.planning import HierarchicalPlanner, PlannerConfig
from sage.libs.agentic.agents.action.tool_selection import get_selector

# Create tool selector
selector = get_selector("hybrid")  # keyword, embedding, hybrid, gorilla, dfsdt

# Create planner
config = PlannerConfig(min_steps=3, max_steps=10)
planner = HierarchicalPlanner.from_config(
    config=config,
    llm_client=client,
    tool_selector=selector
)
```

## 📋 快速链接

### 按层级查找

| 层级 | 包 | API 文档 |
|------|-----|----------|
| L1 | sage-common | [Common API](common/index.md) |
| L2 | sage-platform | [Platform API](platform/index.md) |
| L3 | sage-kernel | [Kernel API](kernel/index.md) |
| L3 | sage-libs | [Libs API](libs/index.md) |
| L4 | sage-middleware | [Middleware API](middleware/index.md) |

### 常用 API

- [DataStream API](../guides/packages/sage-kernel/api/datastreams.md) - 构建数据流
- [Functions API](../guides/packages/sage-kernel/api/functions.md) - 自定义函数
- [RAG API](../guides/packages/sage-libs/rag/api_reference.md) - RAG 组件
- [算子参考](../guides/packages/sage-libs/operators_reference.md) - Libs 算子
- [服务 API](../guides/packages/sage-middleware/service/service_api.md) - 中间件服务

## 📚 相关文档

- [用户指南](../guides/index.md) - 各层级的详细使用指南
- [快速入门](../getting-started/quickstart.md) - 快速开始使用 SAGE
- [包架构](../dev-notes/package-architecture.md) - 了解 SAGE 的架构设计
- [核心概念](../concepts/index.md) - 理解 SAGE 的核心概念
- [FAQ](../community/faq.md) - 常见问题解答

## 配置决策对照表

根据不同场景选择合适的配置方案：

| 场景 | 环境变量 | 参考脚本/配置 |
|------|---------|---------------|
| **本地开发 (GPU)** | 无需配置云端 Key | `sage llm serve` 启动本地服务 |
| **本地开发 (CPU)** | 需要 `SAGE_CHAT_*` 云端回退 | `.env.template` → `.env` |
| **WSL2 开发** | 使用 `SagePorts.get_recommended_llm_port()` | `ports.py` 自动检测 |
| **CI/CD (GitHub)** | `OPENAI_API_KEY`, `HF_TOKEN` 通过 Secrets 注入 | `.github/workflows/*.yml` |
| **中国大陆部署** | `SAGE_FORCE_CHINA_MIRROR=true` | `quickstart.sh`, `network.py` |
| **生产环境** | 建议使用 Control Plane 模式 | `UnifiedInferenceClient.create_with_control_plane()` |
| **模型下载** | `HF_TOKEN` (私有模型), `HF_ENDPOINT` (镜像) | `ensure_hf_mirror_configured()` |
| **Embedding 服务** | 端口 `8090` (SagePorts.EMBEDDING_DEFAULT) | `sage llm serve --with-embedding` |

### 网络自动检测

SAGE 会自动检测网络区域并配置 HuggingFace 镜像：

```python
from sage.common.config import (
    detect_china_mainland,
    ensure_hf_mirror_configured,
)

# 自动检测并配置（推荐在 CLI 入口调用）
ensure_hf_mirror_configured()

# 手动检测
is_china = detect_china_mainland()  # True/False
```

## 🤝 贡献 API 文档

要改进 API 文档：

1. 在代码中编写清晰的 docstrings
2. 遵循 [Google docstring 格式](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
3. 在 docstrings 中包含示例代码
4. 为所有公共 API 编写文档
5. 添加类型提示以提高文档质量

示例 docstring：

```python
def process_data(data: List[str], threshold: int = 10) -> Dict[str, int]:
    """处理输入数据并返回统计结果。

    Args:
        data: 要处理的字符串列表
        threshold: 过滤阈值，默认为 10

    Returns:
        包含统计信息的字典，键为字符串，值为计数

    Raises:
        ValueError: 当 threshold 为负数时

    Examples:
        >>> result = process_data(["a", "b", "a"], threshold=1)
        >>> print(result)
        {'a': 2, 'b': 1}
    """
    # Implementation here
    pass
```
