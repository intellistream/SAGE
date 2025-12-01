# R1: MemoryService 重构 - 继承 BaseService + 使用 NeuroMem

> **优先级**: P0（基础任务，其他任务依赖此任务） **预估工时**: 3 天 **依赖**: 无 **状态**: ✅ **已完成** (2025-12-01)

______________________________________________________________________

## 一、任务目标

重构所有 MemoryService，确保：

1. **继承正确的基类**：`from sage.platform.service import BaseService`
1. **使用 NeuroMem 底层**：`MemoryManager` + `MemoryCollection`
1. 不要自己维护数据结构

______________________________________________________________________

## 二、当前问题

### 2.1 基类错误

**❌ 当前错误做法** (`base_memory_service.py` 自定义基类):

```python
# 这个文件是错误的，不应该存在
from abc import ABC, abstractmethod

class BaseMemoryService(ABC):  # ❌ 错误：自己定义基类
    @abstractmethod
    def insert(...): pass
    @abstractmethod
    def retrieve(...): pass
```

**✅ 正确做法**：

```python
from sage.platform.service import BaseService  # ✅ 使用平台提供的基类

class SomeMemoryService(BaseService):
    def __init__(self, ...):
        super().__init__()  # 调用 BaseService 的初始化
        self.manager = MemoryManager(...)
```

### 2.2 正确示例：NeuroMemVDBService

```python
# neuromem_vdb_service.py - 这是正确的实现！
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService  # ✅ 继承平台基类


class NeuroMemVDBService(BaseService):  # ✅ 继承 BaseService
    def __init__(self, collection_name: str | list[str]):
        super().__init__()  # ✅ 调用父类初始化
        self.manager = MemoryManager(self._get_default_data_dir())  # ✅ 使用 MemoryManager
        self.online_register_collections: dict[str, VDBMemoryCollection] = {}

        for name in collection_names:
            collection = self.manager.get_collection(name)  # ✅ 获取 Collection
            self.online_register_collections[name] = collection

    def retrieve(self, query_text, topk, ...):
        for name, collection in self.online_register_collections.items():
            results = collection.retrieve(query_text, topk=topk, ...)  # ✅ 调用底层
        return results
```

### 2.3 错误示例：GraphMemoryService

```python
# graph_memory_service.py - 当前错误实现
from .base_memory_service import AdvancedMemoryService  # ❌ 继承错误的基类

class GraphMemoryService(AdvancedMemoryService):  # ❌ 错误
    def __init__(self, ...):
        # ❌ 自己维护数据结构
        self.nodes: dict[str, dict] = {}
        self.edges: dict[tuple[str, str], dict] = {}
        self.node_embeddings: dict[str, np.ndarray] = {}
```

### 2.4 需要重构的服务清单

| 服务文件                         | 当前问题                                   | 应使用的 NeuroMem 模块                                       |
| -------------------------------- | ------------------------------------------ | ------------------------------------------------------------ |
| `graph_memory_service.py`        | 继承错误基类 + 自维护 nodes/edges          | `BaseService` + `GraphMemoryCollection`                      |
| `hierarchical_memory_service.py` | 继承错误基类 + 自维护各层结构              | `BaseService` + 多个 `VDBMemoryCollection`                   |
| `short_term_memory_service.py`   | 继承错误基类 + 自维护 deque                | `BaseService` + `VDBMemoryCollection`                        |
| `key_value_memory_service.py`    | 继承错误基类 + 自维护 dict                 | `BaseService` + `KVMemoryCollection`                         |
| `hybrid_memory_service.py`       | 继承错误基类                               | `BaseService` + `VDBMemoryCollection` + `KVMemoryCollection` |
| `vector_hash_memory_service.py`  | 继承错误基类（但已正确使用 MemoryManager） | `BaseService` + `VDBMemoryCollection`                        |
| `base_memory_service.py`         | **应该删除**                               | N/A                                                          |

______________________________________________________________________

## 三、NeuroMem 底层模块

### 3.1 模块位置

```
sage-middleware/src/sage/middleware/components/sage_mem/neuromem/
├── memory_manager.py          # MemoryManager: 管理所有 Collection 实例
├── memory_collection/
│   ├── base_collection.py     # BaseMemoryCollection 抽象基类
│   ├── vdb_collection.py      # VDBMemoryCollection (FAISS 向量数据库)
│   ├── graph_collection.py    # GraphMemoryCollection (邻接表图结构)
│   └── kv_collection.py       # KVMemoryCollection (BM25 索引)
├── storage_engine/            # 底层存储引擎
└── search_engine/             # 索引和检索引擎
```

### 3.2 核心接口

**MemoryManager**:

```python
class MemoryManager:
    def create_collection(self, config: dict) -> MemoryCollection
    def get_collection(self, collection_name: str) -> MemoryCollection
    def delete_collection(self, collection_name: str) -> bool
```

**VDBMemoryCollection**:

```python
class VDBMemoryCollection:
    def insert(self, index_name, text, vector, metadata) -> str
    def retrieve(self, query, index_name, topk, ...) -> list[dict]
    def create_index(self, config: dict) -> bool
    def delete(self, text) -> bool
```

______________________________________________________________________

## 四、重构目标代码

### 4.1 GraphMemoryService 重构

```python
# 重构后的 graph_memory_service.py
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.middleware.components.sage_mem.neuromem.memory_collection.graph_collection import GraphMemoryCollection
from sage.platform.service import BaseService


class GraphMemoryService(BaseService):  # ✅ 继承 BaseService
    def __init__(self, collection_name: str, graph_type: str = "knowledge_graph", ...):
        super().__init__()  # ✅ 调用父类
        self.manager = MemoryManager(self._get_default_data_dir())

        # ✅ 使用 GraphMemoryCollection
        collection_config = {
            "name": collection_name,
            "backend_type": "graph",
            "graph_type": graph_type,
        }
        self.collection = self.manager.create_collection(collection_config)

    def insert(self, entry: str, vector=None, metadata=None, ...):
        # ✅ 调用底层 Collection
        return self.collection.insert(entry, metadata)

    def retrieve(self, query: str, topk: int = 10, ...):
        # ✅ 调用底层 Collection
        return self.collection.retrieve(query, topk=topk)

    def optimize(self, trigger: str = "auto"):
        # 业务逻辑：link_evolution 等
        # 仍然调用 self.collection 的方法
        pass
```

### 4.2 HierarchicalMemoryService 重构

```python
from sage.platform.service import BaseService

class HierarchicalMemoryService(BaseService):  # ✅ 继承 BaseService
    def __init__(self, tier_mode: str = "three_tier", ...):
        super().__init__()
        self.manager = MemoryManager(self._get_default_data_dir())

        # ✅ 使用多个 VDBMemoryCollection 作为各层
        self.stm_collection = self.manager.create_collection({"name": "stm", "backend_type": "VDB"})
        self.mtm_collection = self.manager.create_collection({"name": "mtm", "backend_type": "VDB"})
        self.ltm_collection = self.manager.create_collection({"name": "ltm", "backend_type": "VDB"})

    def insert(self, entry, vector=None, metadata=None, *, target_tier="stm", ...):
        collection = getattr(self, f"{target_tier}_collection")
        return collection.insert(entry, vector, metadata)

    def optimize(self, trigger="auto"):
        # 业务逻辑：迁移、遗忘等
        pass
```

______________________________________________________________________

## 五、开发步骤

### Step 1: 删除错误的基类文件

- [x] 删除或废弃 `base_memory_service.py`（自定义的 BaseMemoryService 是错误的）
- [x] 移除 `InsertResult`, `RetrieveResult` 等自定义数据类（或移入公共 utils）

### Step 2: 重构各服务继承 BaseService + 使用 NeuroMem (2天)

- [x] `graph_memory_service.py`:
  - 改为 `class GraphMemoryService(BaseService)`
  - 使用 `MemoryManager` + `GraphMemoryCollection`
- [x] `hierarchical_memory_service.py`:
  - 改为 `class HierarchicalMemoryService(BaseService)`
  - 使用多个 `VDBMemoryCollection`
- [x] `short_term_memory_service.py`:
  - 改为 `class ShortTermMemoryService(BaseService)`
  - 使用 `VDBMemoryCollection`
- [x] `key_value_memory_service.py`:
  - 改为 `class KeyValueMemoryService(BaseService)`
  - 使用 `KVMemoryCollection`
- [x] `hybrid_memory_service.py`:
  - 改为 `class HybridMemoryService(BaseService)`
  - 使用 `VDBMemoryCollection` + `KVMemoryCollection`
- [x] `vector_hash_memory_service.py`:
  - 改为 `class VectorHashMemoryService(BaseService)`
  - 使用 `MemoryManager` + `VDBMemoryCollection` (LSH 索引)

### Step 3: 更新服务工厂 (0.5天)

- [x] 更新 `__init__.py` 导出（移除错误的 base_memory_service 导入）
- [ ] 更新 `memory_service_factory.py`（待验证是否需要修改）

### Step 4: 测试验证 (0.5天)

- [ ] 确保现有测试通过
- [ ] 添加 NeuroMem 集成测试

______________________________________________________________________

## 六、验收标准

1. **正确的继承**：

   - ✅ 所有服务继承 `from sage.platform.service import BaseService`
   - ❌ 不得使用自定义的 `BaseMemoryService`

1. **NeuroMem 集成**：

   - ✅ 服务层通过 `MemoryManager` 获取/创建 `MemoryCollection`
   - ❌ 服务层不得自己维护 `nodes`, `edges`, `deque`, `dict` 等数据结构
   - ✅ 存储、索引、检索逻辑由 NeuroMem 底层实现

1. **测试通过**：现有测试用例全部通过

______________________________________________________________________

## 七、影响范围

### 需要修改的文件

| 文件                             | 修改内容                       |
| -------------------------------- | ------------------------------ |
| `base_memory_service.py`         | 删除或废弃                     |
| `graph_memory_service.py`        | 改继承 + 使用 NeuroMem         |
| `hierarchical_memory_service.py` | 改继承 + 使用 NeuroMem         |
| `short_term_memory_service.py`   | 改继承 + 使用 NeuroMem         |
| `key_value_memory_service.py`    | 改继承 + 使用 NeuroMem         |
| `hybrid_memory_service.py`       | 改继承 + 使用 NeuroMem         |
| `vector_hash_memory_service.py`  | 改继承（已使用 MemoryManager） |
| `memory_service_factory.py`      | 更新创建逻辑                   |
| `__init__.py`                    | 更新导出                       |

______________________________________________________________________

*文档创建时间: 2025-12-01*

______________________________________________________________________

## 八、完成记录

**完成时间**: 2025-12-01

### 已完成的工作

| 文件                             | 状态      | 使用的 NeuroMem 模块                                         |
| -------------------------------- | --------- | ------------------------------------------------------------ |
| `base_memory_service.py`         | ✅ 已删除 | N/A                                                          |
| `graph_memory_service.py`        | ✅ 已重构 | `BaseService` + `GraphMemoryCollection`                      |
| `hierarchical_memory_service.py` | ✅ 已重构 | `BaseService` + 多个 `VDBMemoryCollection`                   |
| `short_term_memory_service.py`   | ✅ 已重构 | `BaseService` + `VDBMemoryCollection`                        |
| `key_value_memory_service.py`    | ✅ 已重构 | `BaseService` + `KVMemoryCollection`                         |
| `hybrid_memory_service.py`       | ✅ 已重构 | `BaseService` + `VDBMemoryCollection` + `KVMemoryCollection` |
| `vector_hash_memory_service.py`  | ✅ 已重构 | `BaseService` + `VDBMemoryCollection` (LSH)                  |
| `__init__.py`                    | ✅ 已更新 | 移除错误导入                                                 |

### 统一接口

所有服务现在使用简单统一的接口：

```python
class XxxMemoryService(BaseService):
    def __init__(self, collection_name: str, ...):
        super().__init__()
        self.manager = MemoryManager(self._get_default_data_dir())
        self.collection = self.manager.create_collection({...})

    def insert(self, entry: str, vector=None, metadata=None) -> str
    def retrieve(self, query=None, vector=None, metadata=None, top_k=10) -> list[dict]
    def delete(self, entry_id: str) -> bool
    def get_stats(self) -> dict
```

### 待完成

- [ ] 运行完整测试验证
- [ ] 更新 `memory_service_factory.py`（如需要）

| `libs/post_insert.py` | 调用 `optimize()` 而非自己实现 |

### 不需要修改的文件

| 文件                     | 原因                       |
| ------------------------ | -------------------------- |
| `libs/pre_insert.py`     | 不直接调用服务接口         |
| `libs/pre_retrieval.py`  | 不访问记忆数据结构         |
| `libs/post_retrieval.py` | 只读取检索结果，不调用服务 |

______________________________________________________________________

*文档创建时间: 2025-12-01*
