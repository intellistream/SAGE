# L1 Common 开发文档

`sage-common` 属于 L1（基础层），提供 SAGE 框架的核心基础设施和通用组件。本目录记录 sage-common 的开发文档和历史。

## 📦 主要模块

### 🤖 sageLLM 组件 (`components/sage_llm/`)

统一的 LLM 和 Embedding 推理客户端和调度系统：

| 模块 | 描述 |
|------|------|
| `unified_client.py` | `UnifiedInferenceClient` - 统一推理客户端（推荐） |
| `unified_api_server.py` | `UnifiedAPIServer` - OpenAI 兼容 API Gateway |
| `client.py` | `IntelligentLLMClient` - 独立 LLM 客户端（保留） |
| `control_plane_service.py` | Control Plane SAGE 封装层 |
| `sageLLM/control_plane/` | 核心调度框架 |

**使用示例**:
```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 自动检测模式（推荐）
client = UnifiedInferenceClient.create_auto()
response = client.chat([{"role": "user", "content": "Hello"}])
vectors = client.embed(["text1", "text2"])

# Control Plane 模式（高级）
client = UnifiedInferenceClient.create_with_control_plane(
    llm_base_url="http://localhost:8901/v1",
    embedding_base_url="http://localhost:8090/v1",
)
```

### 🎯 sage_embedding 组件 (`components/sage_embedding/`)

Embedding 服务和工厂：

| 模块 | 描述 |
|------|------|
| `embedding_server.py` | OpenAI 兼容 Embedding 服务器 |
| `factory.py` | `EmbeddingFactory` - 本地模型加载 |
| `client.py` | `IntelligentEmbeddingClient` - 独立客户端（保留） |

### ⚙️ 配置模块 (`config/`)

| 模块 | 描述 |
|------|------|
| `ports.py` | `SagePorts` - 统一端口配置 |
| `env.py` | 环境变量管理 |

## 📁 文档结构

### 核心文档

- **[control-plane-enhancement.md](./control-plane-enhancement.md)** - Control Plane 动态引擎管理增强（GPU/Lifecycle/预设）
- **[hybrid-scheduler/README.md](./hybrid-scheduler/README.md)** - sageLLM 混合调度器项目总结
- **[hybrid-scheduler/PULL_REQUEST.md](./hybrid-scheduler/PULL_REQUEST.md)** - PR 详细说明

### 工具文档

- **[CLEANUP_AUTOMATION.md](./CLEANUP_AUTOMATION.md)** - 自动清理功能说明
- **[VLLM_TORCH_VERSION_CONFLICT.md](./VLLM_TORCH_VERSION_CONFLICT.md)** - vLLM 和 Torch 版本冲突解决

## 🎯 快速导航

| 想要了解... | 查看 |
|-------------|------|
| 统一推理客户端使用 | [hybrid-scheduler/README.md](./hybrid-scheduler/README.md) |
| 动态引擎管理 | [control-plane-enhancement.md](./control-plane-enhancement.md) |
| Control Plane 架构 | `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/` |
| 端口配置 | `packages/sage-common/src/sage/common/config/ports.py` |
| Embedding 服务 | `packages/sage-common/src/sage/common/components/sage_embedding/` |

## 🔗 相关资源

- **代码位置**: `packages/sage-common/src/sage/common/`
- **测试**: `packages/sage-common/tests/`
- **Copilot 指南**: `.github/copilot-instructions.md`

---

**最后更新**: 2025-12-02
