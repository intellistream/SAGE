# Memory 组件设计文档

!!! note "当前状态"
    `sage-libs` 仍未内置统一的 `BaseMemory` 抽象，但仓库已经提供完善的 Neuromem MemoryService、`MemoryManager` 以及多个可直接运行的示例，可满足大多数记忆场景。

---

## 1. 架构概览

- **Neuromem 服务栈（`packages/sage-middleware`）**：提供 KV / VDB / Graph 多种存储后端，包含 `MemoryManager`、`NeuromemVDBService`、`micro_service` 等组件，可直接部署为本地或远程服务。
- **`sage-libs` 组件**：通过 `AgentRuntime` / `Planner` 的 hook（如 `post_cycle`、`summarizer`）或自定义 Action 将记忆读写能力串联进 Agent 流水线。
- **RAG 能力**：`packages/sage-libs/src/sage/libs/rag/` 下的检索模块可以复用 Neuromem 的集合数据，支撑问答、对话记忆等场景。
- **示例工程**：`examples/memory`、`examples/agents`、`examples/rag` 等目录展示了如何加载 MemoryService、执行检索与写回。

---

## 2. 集成路径

| 场景 | 推荐做法 |
|------|-----------|
| 单机快速体验 | 使用 `examples/memory/rag_memory_service.py` 启动内存集合，通过 `MemoryManager` 完成插入与检索 |
| Pipeline + Agent | 参考 `examples/memory/rag_memory_pipeline.py` 或 `examples/agents/agent.py`，在 `AgentRuntime` 的 `memory_read` / `memory_write` 逻辑中调用 `MemoryManager` 或远程服务 |
| 远程多实例部署 | 通过 `sage-middleware` 的 `micro_service/neuromem_vdb_service.py` 启动独立 MemoryService，再由 Agent / RAG 组件以 HTTP/RPC 接入 |
| 自定义实现 | 如果只需轻量记忆，可在 Python 层编写自定义缓存（列表、SQLite、向量数据库 SDK），并通过 `AgentRuntime` 的扩展点注入 |

---

## 3. 示例索引

- `examples/memory/README_memory_service.md`：概述 MemoryService 的启动与常见任务。
- `examples/memory/rag_memory_service.py`：最小化脚本，演示集合创建、数据写入、Top-K 检索。
- `examples/memory/rag_memory_pipeline.py`：结合 `LocalEnvironment`、`QAPromptor`、`OpenAIGenerator` 的端到端流水线示例。
- `examples/memory/rag_memory_manager.py`：展示 MemoryManager 的集合管理与批量操作。
- `examples/agents/agent.py`：说明 Agent 在执行流程中如何读取上下文并写回记忆。
- `examples/rag/qa_dense_retrieval_ray.py`：演示与检索流水线结合的记忆使用方式。

访问这些示例即可获得可运行的参考实现，无需额外的适配层。

---

## 4. 与 Agent 协同的最佳实践

1. 在 `AgentRuntime` 子类中覆盖 `before_cycle` / `after_cycle`，于会话开始时加载记忆，于生成后写回摘要。
2. 为 `Planner` 或 Action 添加 `MemoryManager` 依赖，在工具执行前后检索历史、追加关联上下文。
3. 对多轮会话，建议在 `summarizer` hook 内落盘对话摘要，降低长对话的上下文长度。
4. 若使用远程 MemoryService，可通过自定义 `ServiceClient` 封装 HTTP/RPC 调用，再注入到 Agent 配置中。

---

## 5. 后续规划

1. 提供官方的轻量 `BaseMemory` 协议，统一 `AgentRuntime` 与 Pipeline 间的调用方式。
2. 发布与 Neuromem 服务对接的 Python Adapter（含鉴权、批处理、重试策略）。
3. 在文档中补充更多真实业务场景示例，并发布端到端测试用例。

欢迎根据实际需求扩展或贡献新的记忆实现。