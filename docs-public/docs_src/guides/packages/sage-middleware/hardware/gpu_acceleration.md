# SAGE-Flow（数据流/执行引擎）GPU 与硬件加速

SAGE 的数据流执行由 Engine 负责，将逻辑管道编译为物理执行图并在本地或分布式环境高效运行。

- 本地：多线程加速
- 分布式：通过远程环境运行（示例文档展示了在分布式环境提交作业），仪表盘支持 GPU 资源指标监控

Flow/Engine 本身不直接“持有” GPU 计算核，而是以两类方式利用硬件加速：

1. 通过服务：将需要 GPU 的能力封装为服务并在 Flow 中调用（如 vLLM 推理服务、SAGE-DB 作为 VDB 后端）
1. 通过分布式运行时：在具备 GPU 的节点上部署/调度上述服务与算子进程，使其绑定并使用 GPU

## 典型 GPU 加速路径

- LLM 推理：使用 vLLM 等 GPU 推理后端的服务（仓库文档提供了 LLMService 示例）
- 向量检索：使用启用 GPU 加速的 SAGE-DB 作为 VDB Service 后端（见 middleware/components/sage_db.md）
- 图/混合检索：由 Memory/Neuromem 编排 KV/VDB/Graph；VDB 段可利用 GPU
- 可观测性：仪表盘展示包含 GPU 在内的资源监控（README 展示了 GPU 监控与可视化）

## 编排示例（服务驱动的 GPU 使用）

在数据流中，只需要调用对应服务即可；GPU 的分配与使用由服务进程与后端引擎负责：

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.base_function import BaseFunction
from sage.middleware.services.memory import MemoryService
from sage.middleware.services.vdb import VDBService

env = LocalEnvironment("gpu_flow_demo")
env.register_service("memory_service", lambda: MemoryService())
env.register_service("vdb_service", lambda: VDBService())


class RAGStep(BaseFunction):
    def execute(self, data):
        # 向量检索（VDB 后端可指向 SAGE-DB GPU）
        results = self.call_service["vdb_service"].search(
            query=data["query_vector"], top_k=10
        )
        # 长期记忆交互（Memory 内部编排 KV/VDB/Graph）
        self.call_service["memory_service"].store_memory(
            content=data["content"],
            vector=data["query_vector"],
            session_id=data.get("sid", "default"),
            memory_type="conversation",
        )
        return {"hits": results}
```

## 分布式与 GPU 资源

- 运行时支持将同一份流图提交到分布式环境执行（仓库示例展示了远程环境的使用）

- 在分布式部署中：

  - 将 GPU 服务（如 vLLM、VDB/SAGE-DB）部署到具备 GPU 的节点
  - 数据流通过 Service API 访问这些服务，服务进程自行绑定并使用 GPU
  - 通过仪表盘监控 GPU 与任务状态，结合批处理/异步，提高吞吐

## 性能与工程建议

- 服务粒度：

  - 将 GPU 密集型能力统一封装为长生命周期服务，避免在算子内频繁初始化 GPU 上下文

- 批处理与异步：

  - 在算子内使用 self.call_service_async 发起检索/推理批请求，减少阻塞
  - 配合 SAGE-DB 的 numpy 批路径（add/search）大幅提升吞吐

- 数据搬运：

  - 尽量合并请求，避免频繁的小数据量往返带来的 PCIe/NVLink 抖动

- 监控与扩容：

  - 使用仪表盘观测 GPU 利用率与延迟
  - 通过服务分片（shard）与副本（replica）扩展多 GPU 并发

- 容错与降级：

  - 服务不可用或 GPU 饱和时，服务层可降级到 CPU/其他后端；数据流逻辑保持不变

参考：

- Engine/RemoteEnvironment 的分布式示例（仓库 README）
- GPU 资源监控与仪表盘（仓库 README）
- SAGE-DB GPU/索引配置（middleware/components/sage_db.md）

```
```
