# MemoryService 重构 - 并行任务拆解方案

> **目标**：将重构任务拆分为可并行执行的子任务，每个任务由不同人员独立完成
>
> **重要约束**：
>
> 1. **一个 Service 对应一个 Collection** - 严格 1:1 关系
> 1. **统一接口** - 所有 Service 必须实现 `insert(entry, vector, metadata)` 和
>    `retrieve(query, vector, metadata, top_k)`
> 1. **配置从 from_config 读取** - Service 类自己负责配置解析

**更新时间**：2025-12-23

______________________________________________________________________

## 一、上层代码调用分析

### 1.1 核心调用接口（从 semantic_search 结果总结）

**MemoryInsert 调用**：

```python
# 插入单条记忆
memory_id = call_service(
    service_name,          # 如 "partitional.vector_memory"
    entry=str,             # 记忆文本
    vector=np.ndarray,     # 向量（可选）
    metadata=dict,         # 元数据（可选）
    method="insert"
)
```

**MemoryRetrieval 调用**：

```python
# 检索记忆
results = call_service(
    service_name,
    query=str,             # 查询文本（可选）
    vector=np.ndarray,     # 查询向量（可选）
    metadata=dict,         # 筛选条件（可选）
    top_k=int,             # 返回数量
    method="retrieve"
)
# 返回: list[dict] - [{"text": str, "metadata": dict, "score": float}, ...]
```

### 1.2 关键发现

1. **统一接口已验证**：从测试代码看，所有 Service 都已实现 `insert` 和 `retrieve`
1. **metadata 传递参数**：Service 特定参数通过 `metadata` 传递（如 `tiers`, `method`）
1. **insert_mode/insert_params** 已存在：部分 Service 已支持 `insert_mode="active/passive"`
1. **无多余接口**：主要接口就是 `insert`/`retrieve`/`delete`/`get_stats`

### 1.3 需要调整的接口

根据代码分析，当前 Service 已经比较统一，主要需要：

- ✅ 添加 `from_config` 类方法（新增）
- ✅ 确保 `insert`/`retrieve` 参数完全一致
- ❌ 不需要删除任何现有接口（都有用）

______________________________________________________________________

## 二、并行任务拆解（5个独立任务）

### 任务分配原则

1. **按 Service 类别拆分** - Partitional/Hierarchical/Hybrid 三大类
1. **每个任务独立** - 可并行开发，互不依赖
1. **统一模板** - 提供基类和示例，保证接口一致

______________________________________________________________________

## 任务 1: 基础设施 + Registry（核心，优先级最高）

**负责人**：资深开发者 A

**工作量**：2-3 小时

**目标**：搭建重构基础，供其他任务使用

### 1.1 创建文件

```
packages/sage-middleware/src/sage/middleware/components/sage_mem/memory_service/
├── __init__.py                      # 导出 Registry 和 base
├── base_service.py                  # BaseMemoryService 抽象基类
└── registry.py                      # MemoryServiceRegistry
```

### 1.2 实现内容

#### `base_service.py` - 抽象基类

```python
"""MemoryService 基类 - 定义统一接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

if TYPE_CHECKING:
    from sage.kernel.runtime.factory.service_factory import ServiceFactory

from sage.platform.service import BaseService as PlatformBaseService


class BaseMemoryService(PlatformBaseService, ABC):
    """MemoryService 统一抽象基类

    设计原则：
    1. 一个 Service 对应一个 Collection（严格 1:1）
    2. 统一接口：insert/retrieve/delete/get_stats
    3. 配置通过 from_config 类方法读取
    """

    @classmethod
    @abstractmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory（供 Pipeline 使用）

        Args:
            service_name: 服务名称（如 "partitional.vector_memory"）
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例

        Notes:
            - 子类必须实现此方法
            - 配置路径：services.{service_name}.*
            - 返回 ServiceFactory(service_name, service_class, service_kwargs)
        """
        raise NotImplementedError(f"{cls.__name__} must implement from_config()")

    @abstractmethod
    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入记忆

        Args:
            entry: 记忆文本
            vector: 向量表示（可选）
            metadata: 元数据
            insert_mode: 插入模式（passive=自动处理，active=显式控制）
            insert_params: 插入参数（如 target_tier, priority 等）

        Returns:
            记忆ID
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement insert()")

    @abstractmethod
    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本（可选）
            vector: 查询向量（可选）
            metadata: 筛选条件（可选，如 tiers, method）
            top_k: 返回数量

        Returns:
            记忆列表 [{"text": str, "metadata": dict, "score": float}, ...]
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement retrieve()")

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """删除记忆

        Args:
            item_id: 记忆ID

        Returns:
            是否成功
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement delete()")

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计数据（如 total_count, tier_counts 等）
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_stats()")
```

#### `registry.py` - 注册表

```python
"""MemoryService 注册表"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_service import BaseMemoryService


class MemoryServiceRegistry:
    """MemoryService 注册表

    支持层级命名（如 "partitional.vector_memory"）

    三大类：
    - Partitional：vector_memory, key_value_memory, short_term_memory, vector_hash_memory
    - Hierarchical：graph_memory, three_tier
    - Hybrid：multi_index
    """

    _services: dict[str, type[BaseMemoryService]] = {}

    @classmethod
    def register(cls, name: str, service_class: type[BaseMemoryService]) -> None:
        """注册一个 Service"""
        cls._services[name] = service_class

    @classmethod
    def get(cls, name: str) -> type[BaseMemoryService]:
        """获取 Service 类"""
        if name not in cls._services:
            raise ValueError(
                f"Unknown MemoryService: '{name}'. "
                f"Available: {list(cls._services.keys())}"
            )
        return cls._services[name]

    @classmethod
    def list_services(cls, category: str | None = None) -> list[str]:
        """列出所有已注册的 Service"""
        if category is None:
            return list(cls._services.keys())
        prefix = f"{category}."
        return [name for name in cls._services.keys() if name.startswith(prefix)]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查 Service 是否已注册"""
        return name in cls._services

    @classmethod
    def get_category(cls, name: str) -> str | None:
        """获取 Service 的类别"""
        if "." in name:
            return name.split(".")[0]
        return None
```

#### `__init__.py` - 导出接口

```python
"""MemoryService 重构版本 - 纯 Registry 模式"""

from .base_service import BaseMemoryService
from .registry import MemoryServiceRegistry

__all__ = [
    "BaseMemoryService",
    "MemoryServiceRegistry",
]
```

### 1.3 验收标准

- ✅ `BaseMemoryService` 定义清晰的抽象接口
- ✅ `MemoryServiceRegistry` 支持注册和查询
- ✅ 单元测试通过（测试 Registry 基本功能）

______________________________________________________________________

## 任务 2: Partitional 类 Service（4个，可并行）

**负责人**：开发者 B、C、D、E（每人 1-2 个）

**工作量**：每个 Service 约 1-1.5 小时

**目标**：实现 Partitional 类的 4 个 Service

### 2.1 Service 列表

| Service 名称                     | 对应原文件                     | Collection 类型             | 负责人   |
| -------------------------------- | ------------------------------ | --------------------------- | -------- |
| `partitional.short_term_memory`  | `short_term_memory_service.py` | `VDBMemoryCollection`       | 开发者 B |
| `partitional.vector_memory`      | `vector_memory_service.py`     | `VDBMemoryCollection`       | 开发者 C |
| `partitional.key_value_memory`   | `key_value_memory_service.py`  | `KVMemoryCollection`        | 开发者 D |
| `partitional.vector_hash_memory` | （新增，参考 vector_memory）   | `VDBMemoryCollection` + LSH | 开发者 E |

### 2.2 实现模板（以 short_term_memory 为例）

**文件位置**：`memory_service/partitional/short_term_memory.py`

```python
"""短期记忆服务 - Partitional 类"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.common.config.output_paths import get_appropriate_sage_dir

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    pass


class ShortTermMemoryService(BaseMemoryService):
    """短期记忆服务 - 滑窗 + FIFO

    设计原则：
    - Service : Collection = 1 : 1
    - 使用 VDBMemoryCollection
    - 自动淘汰最旧记忆
    """

    def __init__(
        self,
        max_dialog: int,
        collection_name: str = "stm_collection",
        embedding_dim: int = 1024,
    ):
        super().__init__()
        self.max_dialog = max_dialog
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        # 创建 MemoryManager + Collection（1:1 关系）
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或加载 Collection
        if not self.manager.has_collection(collection_name):
            self.collection = self.manager.create_collection({
                "name": collection_name,
                "backend_type": "vdb",
                "description": "Short-term memory with sliding window",
            })
            # 创建索引
            self.collection.create_index({
                "name": "main_index",
                "type": "vdb",
                "index_type": "IndexFlatL2",
                "dim": embedding_dim,
            })
        else:
            self.collection = self.manager.get_collection(collection_name)

        self.index_name = "main_index"

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              partitional.short_term_memory:
                max_dialog: 10
                embedding_dim: 1024
        """
        max_dialog = config.get(f"services.{service_name}.max_dialog")
        if max_dialog is None:
            raise ValueError(f"Missing config: services.{service_name}.max_dialog")

        embedding_dim = config.get(f"services.{service_name}.embedding_dim", 1024)
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"stm_{service_name.replace('.', '_')}"
        )

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "max_dialog": max_dialog,
                "embedding_dim": embedding_dim,
                "collection_name": collection_name,
            },
        )

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入记忆（FIFO 淘汰）"""
        # 转换 vector
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)

        # 检查容量，FIFO 淘汰
        stats = self.collection.list_indexes()[0]
        if stats["item_count"] >= self.max_dialog:
            # 获取最旧的记忆并删除（简化实现，实际可用时间戳）
            all_items = self.collection.retrieve(
                query=None,
                index_name=self.index_name,
                top_k=1,
                with_metadata=True,
            )
            if all_items:
                oldest_id = all_items[0]["stable_id"]
                self.collection.delete(oldest_id)

        # 插入新记忆
        memory_id = self.collection.insert(
            content=entry,
            index_names=[self.index_name],
            vector=vector,
            metadata=metadata,
        )

        return memory_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆"""
        # 转换 vector
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)

        results = self.collection.retrieve(
            query=vector if vector is not None else query,
            index_name=self.index_name,
            top_k=top_k,
            with_metadata=True,
        )

        # 转换为统一格式
        return [
            {
                "text": r.get("text", ""),
                "metadata": r.get("metadata", {}),
                "score": r.get("distance", 0.0),
            }
            for r in results
        ]

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        return self.collection.delete(item_id)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        indexes = self.collection.list_indexes()
        return {
            "total_count": indexes[0]["item_count"] if indexes else 0,
            "max_dialog": self.max_dialog,
            "collection_name": self.collection_name,
        }

    def _get_default_data_dir(self) -> str:
        """获取默认数据目录"""
        return str(get_appropriate_sage_dir("data") / "memory_service")
```

### 2.3 注册 Service（在 `partitional/__init__.py`）

```python
"""Partitional 类 Service"""

from .short_term_memory import ShortTermMemoryService
from .vector_memory import VectorMemoryService
from .key_value_memory import KeyValueMemoryService
from .vector_hash_memory import VectorHashMemoryService

from ..registry import MemoryServiceRegistry

# 注册所有 Partitional Service
MemoryServiceRegistry.register("partitional.short_term_memory", ShortTermMemoryService)
MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
MemoryServiceRegistry.register("partitional.key_value_memory", KeyValueMemoryService)
MemoryServiceRegistry.register("partitional.vector_hash_memory", VectorHashMemoryService)

__all__ = [
    "ShortTermMemoryService",
    "VectorMemoryService",
    "KeyValueMemoryService",
    "VectorHashMemoryService",
]
```

### 2.4 各 Service 要点

#### `partitional.short_term_memory`（开发者 B）

- ✅ Collection: `VDBMemoryCollection`
- ✅ 核心逻辑：FIFO 淘汰最旧记忆
- ✅ 配置参数：`max_dialog`, `embedding_dim`
- ✅ 参考文件：`services/short_term_memory_service.py`

#### `partitional.vector_memory`（开发者 C）

- ✅ Collection: `VDBMemoryCollection`
- ✅ 核心逻辑：纯向量检索，支持多种索引类型
- ✅ 配置参数：`dim`, `index_type`（IndexFlatL2/IndexIVFFlat）, `index_config`
- ✅ 参考文件：`services/vector_memory_service.py`

#### `partitional.key_value_memory`（开发者 D）

- ✅ Collection: `KVMemoryCollection`
- ✅ 核心逻辑：关键词匹配 + BM25S 检索
- ✅ 配置参数：`match_type`, `key_extractor`, `fuzzy_threshold`
- ✅ 参考文件：`services/key_value_memory_service.py`

#### `partitional.vector_hash_memory`（开发者 E）

- ✅ Collection: `VDBMemoryCollection`
- ✅ 核心逻辑：LSH 哈希索引（IndexLSH）
- ✅ 配置参数：`dim`, `nbits`, `k_nearest`
- ✅ 参考文件：参考 `vector_memory_service.py`，修改 index_type 为 IndexLSH

### 2.5 验收标准

每个 Service 必须：

- ✅ 实现 `from_config` 类方法
- ✅ 实现 `insert/retrieve/delete/get_stats` 方法
- ✅ 遵循 1 Service : 1 Collection 原则
- ✅ 单元测试通过

______________________________________________________________________

## 任务 3: Hierarchical 类 Service（2个）

**负责人**：开发者 F、G

**工作量**：每个 Service 约 1.5-2 小时

**目标**：实现 Hierarchical 类的 2 个 Service

### 3.1 Service 列表

| Service 名称                | 对应原文件                       | Collection 类型         | 负责人   |
| --------------------------- | -------------------------------- | ----------------------- | -------- |
| `hierarchical.three_tier`   | `hierarchical_memory_service.py` | `HybridCollection`      | 开发者 F |
| `hierarchical.graph_memory` | `graph_memory_service.py`        | `GraphMemoryCollection` | 开发者 G |

### 3.2 要点

#### `hierarchical.three_tier`（开发者 F）

- ✅ Collection: `HybridCollection`（一个 Collection，多个索引代表层级）
- ✅ 核心逻辑：三层结构（STM/MTM/LTM），支持 heat/overflow 迁移
- ✅ 配置参数：`tier_mode`, `tier_capacities`, `migration_policy`, `embedding_dim`
- ✅ 参考文件：`services/hierarchical_memory_service.py`
- ⚠️ **注意**：虽然有三层，但仍是 1 个 Service : 1 个 Collection

#### `hierarchical.graph_memory`（开发者 G）

- ✅ Collection: `GraphMemoryCollection`
- ✅ 核心逻辑：图结构存储，支持节点/边操作，PPR 检索
- ✅ 配置参数：`graph_type`, `node_embedding_dim`, `edge_types`, `link_policy`
- ✅ 参考文件：`services/graph_memory_service.py`
- ⚠️ **注意**：`insert` 时可能同时创建节点和边（通过 metadata.edges）

### 3.3 验收标准

- ✅ 实现 `from_config` 类方法
- ✅ 实现 `insert/retrieve/delete/get_stats` 方法
- ✅ 支持层级特定功能（three_tier 的迁移，graph_memory 的边）
- ✅ 单元测试通过

______________________________________________________________________

## 任务 4: Hybrid 类 Service（1个）

**负责人**：开发者 H

**工作量**：约 1.5-2 小时

**目标**：实现 Hybrid 类的 Service

### 4.1 Service 列表

| Service 名称         | 对应原文件                 | Collection 类型    | 负责人   |
| -------------------- | -------------------------- | ------------------ | -------- |
| `hybrid.multi_index` | `hybrid_memory_service.py` | `HybridCollection` | 开发者 H |

### 4.2 要点

- ✅ Collection: `HybridCollection`（一份数据，多种索引）
- ✅ 核心逻辑：多索引融合检索（VDB + KV + Graph）
- ✅ 配置参数：`indexes`（索引配置列表）, `fusion_strategy`（weighted/rrf）, `fusion_weights`
- ✅ 参考文件：`services/hybrid_memory_service.py`
- ⚠️ **注意**：虽然有多个索引，但仍是 1 个 Service : 1 个 Collection

### 4.3 验收标准

- ✅ 实现 `from_config` 类方法
- ✅ 实现 `insert/retrieve/delete/get_stats` 方法
- ✅ 支持多索引融合检索
- ✅ 单元测试通过

______________________________________________________________________

## 任务 5: Pipeline 适配 + 配置文件迁移

**负责人**：开发者 I（与任务 1 负责人协作）

**工作量**：约 2-3 小时

**前置依赖**：任务 1 完成

**目标**：修改 Pipeline 使用 Registry，迁移所有配置文件

### 5.1 修改 memory_test_pipeline.py

**位置**：`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py`

**变更**：

```python
# 变更前
from sage.middleware.components.sage_mem.services import MemoryServiceFactory

service_name = config.get("services.register_memory_service", "short_term_memory")
factory = MemoryServiceFactory.create(service_name, config)
env.register_service_factory(service_name, factory)

# 变更后
from sage.middleware.components.sage_mem.memory_service import MemoryServiceRegistry

service_name = config.get("services.register_memory_service")
service_class = MemoryServiceRegistry.get(service_name)
factory = service_class.from_config(service_name, config)
env.register_service_factory(service_name, factory)
```

### 5.2 迁移配置文件（13 个）

**位置**：`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/primitive_memory_model/`

**迁移清单**：

| 旧配置文件                               | 旧 service_name       | 新 service_name                 | 配置块重命名 |
| ---------------------------------------- | --------------------- | ------------------------------- | ------------ |
| `locomo_short_term_memory_pipeline.yaml` | `short_term_memory`   | `partitional.short_term_memory` | ✅           |
| `locomo_scm_pipeline.yaml`               | `short_term_memory`   | `partitional.short_term_memory` | ✅           |
| `locomo_tim_pipeline.yaml`               | `vector_memory`       | `partitional.vector_memory`     | ✅           |
| `locomo_hipporag_pipeline.yaml`          | `graph_memory`        | `hierarchical.graph_memory`     | ✅           |
| `locomo_hipporag2_pipeline.yaml`         | `graph_memory`        | `hierarchical.graph_memory`     | ✅           |
| `locomo_amem_pipeline.yaml`              | `graph_memory`        | `hierarchical.graph_memory`     | ✅           |
| `locomo_memoryos_pipeline.yaml`          | `hierarchical_memory` | `hierarchical.three_tier`       | ✅           |
| `locomo_memorybank_pipeline.yaml`        | `hierarchical_memory` | `hierarchical.three_tier`       | ✅           |
| `locomo_ldagent_pipeline.yaml`           | `hierarchical_memory` | `hierarchical.three_tier`       | ✅           |
| `locomo_secom_pipeline.yaml`             | `hierarchical_memory` | `hierarchical.three_tier`       | ✅           |
| `locomo_memgpt_pipeline.yaml`            | `hierarchical_memory` | `hierarchical.three_tier`       | ✅           |
| `locomo_mem0_pipeline.yaml`              | `hybrid_memory`       | `hybrid.multi_index`            | ✅           |
| `locomo_mem0g_pipeline.yaml`             | `hybrid_memory`       | `hybrid.multi_index`            | ✅           |

**配置文件修改示例**：

```yaml
# 变更前
services:
  register_memory_service: "hierarchical_memory"
  hierarchical_memory:
    tier_mode: "three_tier"
    # ...

# 变更后
services:
  register_memory_service: "hierarchical.three_tier"
  hierarchical.three_tier:
    tier_mode: "three_tier"
    # ...
```

### 5.3 验收标准

- ✅ Pipeline 能正常启动
- ✅ 所有配置文件迁移完成
- ✅ 原有实验结果可复现
- ✅ CI 测试通过

______________________________________________________________________

## 三、并行执行时间表

### 阶段 1: 基础设施（串行）

| 任务   | 负责人   | 工作量 | 输出                   |
| ------ | -------- | ------ | ---------------------- |
| 任务 1 | 开发者 A | 2-3h   | Registry + BaseService |

### 阶段 2: Service 实现（并行）

| 任务     | 负责人   | 工作量 | 可并行 |
| -------- | -------- | ------ | ------ |
| 任务 2.1 | 开发者 B | 1-1.5h | ✅     |
| 任务 2.2 | 开发者 C | 1-1.5h | ✅     |
| 任务 2.3 | 开发者 D | 1-1.5h | ✅     |
| 任务 2.4 | 开发者 E | 1-1.5h | ✅     |
| 任务 3.1 | 开发者 F | 1.5-2h | ✅     |
| 任务 3.2 | 开发者 G | 1.5-2h | ✅     |
| 任务 4   | 开发者 H | 1.5-2h | ✅     |

**阶段 2 总时间**：约 1.5-2 小时（并行执行）

### 阶段 3: 集成测试（串行）

| 任务   | 负责人       | 工作量 | 依赖                    |
| ------ | ------------ | ------ | ----------------------- |
| 任务 5 | 开发者 I + A | 2-3h   | 任务 1 + 所有任务 2/3/4 |

**总时间**：约 5.5-7 小时（并行执行）

______________________________________________________________________

## 四、质量保证

### 4.1 代码审查 Checklist

每个 Service 提交前必须检查：

- [ ] 实现 `from_config` 类方法
- [ ] 实现 `insert/retrieve/delete/get_stats` 方法
- [ ] 参数签名与 `BaseMemoryService` 完全一致
- [ ] 遵循 1 Service : 1 Collection 原则
- [ ] Collection 在 `__init__` 中创建或加载
- [ ] 配置参数从 `config.get(f"services.{service_name}.*")` 读取
- [ ] 返回值格式统一（retrieve 返回 `[{"text", "metadata", "score"}]`）
- [ ] 添加单元测试
- [ ] 代码符合 Ruff 规范

### 4.2 单元测试要求

每个 Service 必须测试：

```python
def test_service_from_config():
    """测试 from_config 创建 ServiceFactory"""
    pass

def test_service_insert():
    """测试 insert 方法"""
    pass

def test_service_retrieve():
    """测试 retrieve 方法"""
    pass

def test_service_delete():
    """测试 delete 方法"""
    pass

def test_service_get_stats():
    """测试 get_stats 方法"""
    pass
```

### 4.3 集成测试

任务 5 完成后，运行：

```bash
# 测试所有 Service 注册
python -c "from sage.middleware.components.sage_mem.memory_service import MemoryServiceRegistry; print(MemoryServiceRegistry.list_services())"

# 运行 Pipeline
sage-dev project test packages/sage-benchmark/tests/unit/benchmark_memory/

# 运行一个完整实验
bash packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/script/primitive_memory_model/run_locomo_short_term_memory.sh
```

______________________________________________________________________

## 五、常见问题 FAQ

### Q1: 为什么要求 1 Service : 1 Collection？

**A**: 简化设计，避免状态管理复杂度。即使是 HierarchicalMemoryService（三层），也只用一个 HybridCollection（通过不同索引区分层级）。

### Q2: metadata 如何传递 Service 特定参数？

**A**: 例如 HierarchicalMemoryService，可以通过 `metadata["tiers"] = ["stm", "mtm"]` 指定检索哪几层。

### Q3: from_config 读取配置失败怎么办？

**A**: 抛出 `ValueError` 并明确提示缺失的配置项，例如：

```python
if max_dialog is None:
    raise ValueError(f"Missing config: services.{service_name}.max_dialog")
```

### Q4: 如何处理向后兼容？

**A**: **不需要**。本次重构不保留向后兼容，所有配置文件统一迁移到新格式。

### Q5: Collection 的 index_name 如何命名？

**A**:

- 单索引：`"main_index"`
- 多索引：`"stm_index"`, `"mtm_index"`, `"ltm_index"` 等，与层级或用途对应

______________________________________________________________________

## 六、沟通协调

### 6.1 任务认领

请在此文档对应任务下签名认领：

- 任务 1（基础设施）：`_______`
- 任务 2.1（short_term_memory）：`_______`
- 任务 2.2（vector_memory）：`_______`
- 任务 2.3（key_value_memory）：`_______`
- 任务 2.4（vector_hash_memory）：`_______`
- 任务 3.1（three_tier）：`_______`
- 任务 3.2（graph_memory）：`_______`
- 任务 4（multi_index）：`_______`
- 任务 5（Pipeline 适配）：`_______`

### 6.2 进度汇报

每完成一个任务，在此更新：

- [ ] 任务 1 - 完成时间：`_______`
- [ ] 任务 2.1 - 完成时间：`_______`
- [ ] 任务 2.2 - 完成时间：`_______`
- [ ] 任务 2.3 - 完成时间：`_______`
- [ ] 任务 2.4 - 完成时间：`_______`
- [ ] 任务 3.1 - 完成时间：`_______`
- [ ] 任务 3.2 - 完成时间：`_______`
- [ ] 任务 4 - 完成时间：`_______`
- [ ] 任务 5 - 完成时间：`_______`

### 6.3 问题跟踪

遇到问题请在此记录：

| 问题ID | 负责人 | 问题描述 | 解决方案 | 状态 |
| ------ | ------ | -------- | -------- | ---- |
| 1      |        |          |          |      |
| 2      |        |          |          |      |

______________________________________________________________________

**最后更新**：2025-12-23
