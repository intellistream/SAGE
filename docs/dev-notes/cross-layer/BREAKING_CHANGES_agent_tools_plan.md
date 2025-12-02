# Feature Branch: agent_tools_plan - 开发者注意事项

> **合并日期**: 2025-11-27
> **影响范围**: sage-common, sage-libs, copilot-instructions

本文档总结 `feature/agent_tools_plan` 分支合并到 `main-dev` 后，**其他开发者需要注意的改动**。
Agent Benchmark 相关的内容（sage-benchmark/benchmark_agent）不在此文档范围内。

---

## 🚨 重要改动

### 1. IntelligentLLMClient 新增 Embedded 模式

**文件**: `packages/sage-common/src/sage/common/components/sage_llm/client.py`

**变更**: LLM Client 现在支持三种模式：

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| Simple Mode | OpenAI 兼容 API 调用 | 在线服务、多客户端共享 |
| Control Plane Mode | 多实例调度 | 大规模部署 |
| **Embedded Mode (新增)** | 进程内 vLLM 推理 | 批处理、离线任务、无需启动服务 |

**新增 API**:
```python
from sage.common.components.sage_llm import IntelligentLLMClient

# 自动检测：优先本地 API → 内嵌 vLLM → 云端回退
client = IntelligentLLMClient.create_auto_with_fallback()

# 显式内嵌模式
client = IntelligentLLMClient.create_embedded(
    model="Qwen/Qwen2.5-0.5B-Instruct"
)

# 单例缓存（避免重复加载模型）
client = IntelligentLLMClient.get_cached("my_key", model="Qwen/Qwen2.5-7B-Instruct")
```

**注意**: Embedded 模式需要 GPU + vLLM 安装。

---

### 2. 新增 IntelligentEmbeddingClient

**文件**: `packages/sage-common/src/sage/common/components/sage_embedding/client.py` (新文件)

**说明**: 新的统一 Embedding 客户端，支持 API 模式和内嵌模式。

```python
from sage.common.components.sage_embedding import IntelligentEmbeddingClient

# 自动检测：本地 server → 内嵌 HuggingFace
client = IntelligentEmbeddingClient.create_auto()
vectors = client.embed(["文本1", "文本2"])  # 批量接口

# 显式 API 模式
client = IntelligentEmbeddingClient.create_api(
    base_url="http://localhost:8090/v1",
    model="BAAI/bge-m3"
)

# 显式内嵌模式
client = IntelligentEmbeddingClient.create_embedded(
    model="BAAI/bge-small-zh-v1.5"
)
```

---

### 3. 新增 EmbeddingProtocol 和适配器

**文件**: `packages/sage-common/src/sage/common/components/sage_embedding/protocols.py` (新文件)

**说明**: 标准化 Embedding 接口协议。

**问题背景**: `EmbeddingFactory.create()` 返回单文本接口 (`embed(text: str)`)，但很多组件需要批量接口 (`embed(texts: list[str])`)。

**解决方案**:
```python
from sage.common.components.sage_embedding import (
    EmbeddingFactory,
    EmbeddingClientAdapter,
    adapt_embedding_client,
)

# 方式 1: 手动适配
raw_embedder = EmbeddingFactory.create("hf", model="BAAI/bge-small-zh-v1.5")
client = EmbeddingClientAdapter(raw_embedder)
vectors = client.embed(["文本1", "文本2"])  # 批量接口

# 方式 2: 自动适配（推荐）
raw_embedder = EmbeddingFactory.create("hash", dim=64)
client = adapt_embedding_client(raw_embedder)  # 自动检测并适配
```

**接口对比**:
| 接口 | 签名 | 来源 |
|------|------|------|
| 单文本 (BaseEmbedding) | `embed(text: str) -> list[float]` | `EmbeddingFactory.create()` |
| 批量 (EmbeddingProtocol) | `embed(texts: list[str]) -> list[list[float]]` | `EmbeddingClientAdapter` |

---

### 4. copilot-instructions.md 更新

**文件**: `.github/copilot-instructions.md`

**变更**:
- 新增 LLM & Embedding 服务使用说明
- 更新架构图（11 packages，含 sage-gateway）
- 新增常见问题：bash 感叹号问题

---

### 5. 新增 Tool Selection 和 Planning 模块

**位置**: `packages/sage-libs/src/sage/libs/agentic/agents/`

**新增模块**:
- `action/tool_selection/` - 工具选择器（Keyword, Embedding, Hybrid, Gorilla, DFSDT）
- `planning/` - 任务规划器（Hierarchical, ReAct, ToT）
- `runtime/` - 运行时适配器

这些是新增模块，不影响现有代码，但可以被其他开发者使用。

---

## ✅ 无破坏性改动

以下改动是向后兼容的：

1. **pyproject.toml 依赖更新** - transformers 版本对齐
2. **代码风格修复** - `isinstance(x, (A, B))` → `isinstance(x, A | B)`
3. **文档整理** - dev-notes 文件移至对应子目录

---

## 📋 迁移检查清单

如果你的代码使用了以下功能，请检查：

- [ ] **使用 EmbeddingFactory**: 考虑使用 `adapt_embedding_client()` 获得批量接口
- [ ] **使用 IntelligentLLMClient**: 了解新的 Embedded 模式（可选）
- [ ] **自定义 Embedding 实现**: 可以实现 `EmbeddingProtocol` 接口

---

## 🔗 相关文档

- [LLM & Embedding 服务指南](/.github/copilot-instructions.md#llm--embedding-services)
- [Agent Finetune API 参考](/docs/dev-notes/l3-libs/AGENT_FINETUNE_API_REFERENCE.md)
- [Data Architecture](/docs/dev-notes/cross-layer/data-architecture/)

---

*如有问题，请联系 @shuhao 或在 GitHub Issues 中提问。*
