# Memory Service（Neuromem 服务封装）

当前仓库并未提供通用的 `MemoryService` 包装模块，所有长期记忆能力均由 Neuromem 组件直接承担。若需要以 `BaseService` 方式暴露向量检索功能，请使用 `packages/sage-middleware/src/sage/middleware/components/neuromem/micro_service/neuromem_vdb_service.py` 提供的 `NeuroMemVDBService`。

> 扩展说明：如果已构建可选的 `sage_db` 或 `sage_flow` C++ 组件，可参考其各自目录下的 `python/micro_service/` 包装（如 `SageDBService`、`SageFlowService`）获得类似的进程内服务封装。下面内容聚焦于默认即可使用的 Neuromem 实现。

## 服务结构概览

```mermaid
flowchart LR
  subgraph App[调用方]
    F[BaseFunction]
    Other[其他服务]
  end

  F -->|call_service["neuromem_vdb"]| Service

  subgraph Middleware[NeuroMemVDBService]
    Service[NeuroMemVDBService]
    Manager[MemoryManager]
    Collection[VDBMemoryCollection]
    Index[index_factory -> FAISS]
  end

  Service --> Manager --> Collection --> Index
```

要点：

- 服务实例仅在本地进程内运行，不包含 RPC 或消息队列。
- `NeuroMemVDBService` 只支持 VDB 集合，并默认使用 `global_index`。
- 集合与索引需在服务实例化之前准备好，否则初始化会失败。

## 一、准备集合

```python
from sage.middleware.components.neuromem.memory_manager import MemoryManager

manager = MemoryManager()
collection = manager.create_collection({
    "name": "qa_collection",
    "backend_type": "VDB",
    "description": "QA memory"
})

collection.batch_insert_data(
    ["Python 是一种编程语言", "FAISS 用于向量检索"],
    [{"tag": "intro"}, {"tag": "retrieval"}]
)

collection.create_index({
    "name": "global_index",
    "description": "默认检索索引",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "dim": 384,
    "backend_type": "FAISS"
})
collection.init_index("global_index")
manager.store_collection("qa_collection")
```

## 二、实例化服务并检索

```python
from sage.middleware.components.neuromem.micro_service.neuromem_vdb_service import NeuroMemVDBService

memory_service = NeuroMemVDBService("qa_collection")
results = memory_service.retrieve(
    "向量数据库是什么？",
    topk=3,
    with_metadata=True
)
print(results)
```

参数说明：

- `collection_name`: 支持字符串或列表。若传入列表，将在多个集合间聚合结果。
- `topk`: 返回结果数量，默认 5。
- `with_metadata`: 是否包含存储时的元数据。
- 额外关键字参数会透传给 `VDBMemoryCollection.retrieve`，如 `threshold`、`metadata_filter_func`。

## 三、在 BaseFunction 中调用

```python
from sage.core.api.function.base_function import BaseFunction

class ConversationMemory(BaseFunction):
    def execute(self, data):
        query = data["query"]
        service = self.call_service["neuromem_vdb"]
        hits = service.retrieve(query, topk=3, with_metadata=True)
        return {"related": hits}
```

在注册服务时，为环境提供一个工厂函数即可：

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("neuromem-demo")
env.register_service("neuromem_vdb", lambda: NeuroMemVDBService("qa_collection"))
```

## 四、限制与注意事项

- **索引必备**：服务构造函数会检查 `global_index` 是否存在；若缺失请先调用 `create_index` / `init_index`。
- **集合类型**：当前实现仅支持 `VDBMemoryCollection`。KV/Graph 集合仍处于骨架阶段。
- **线程安全**：`NeuroMemVDBService` 未实现锁，若存在多线程写入需求，请在上层自行串行化或扩展实现。
- **部署方式**：服务本质是普通 Python 对象。若需跨进程/跨机器访问，需要额外封装 RPC 层。

通过以上流程即可在不引入额外基础设施的情况下，把 Neuromem 的向量记忆能力作为服务对外暴露。
