# MemoryService 注册机制重构方案

> **目标**：将 MemoryService 改造为类似其他算子（PreInsert、PostInsert 等）的纯 Registry 模式，支持
> `partitional.vector_memory`、`hierarchical.graph_memory`、`hybrid.three_tier` 等分类注册方式。**移除 Factory
> 层**，由 Service 类自己负责从配置创建实例。

**更新时间**：2025-12-23

______________________________________________________________________

## 一、现状分析与问题识别

### 1.1 当前 MemoryService 架构

**当前实现位置**：

- Factory:
  `packages/sage-middleware/src/sage/middleware/components/sage_mem/services/memory_service_factory.py`
- 各 Service: `packages/sage-middleware/src/sage/middleware/components/sage_mem/services/`

**当前注册方式**（扁平化）：

```python
SERVICE_CLASSES = {
    "short_term_memory": ShortTermMemoryService,
    "vector_memory": VectorMemoryService,
    "graph_memory": GraphMemoryService,
    "hierarchical_memory": HierarchicalMemoryService,
    "hybrid_memory": HybridMemoryService,
    "key_value_memory": KeyValueMemoryService,
}
```

**当前使用方式**（在 Pipeline 中）：

```python
service_name = config.get("services.register_memory_service", "short_term_memory")
factory = MemoryServiceFactory.create(service_name, config)  # 返回 ServiceFactory
env.register_service_factory(service_name, factory)
```

**问题汇总**：

1. **扁平化命名**：无法体现存储结构的本质差异（Partitional/Hierarchical/Hybrid）
1. **分类不清晰**：`hierarchical_memory` 和 `graph_memory` 都是有层级结构，但命名上看不出关系
1. **难以扩展**：新增 Service 时无法明确其归属类别
1. **与论文映射不一致**：无法直接对应到排列组合实验设计中的三大类
1. **Factory 与 Registry 功能重叠**：Factory 只是薄层包装，从 Registry 获取类后调用，增加复杂度

### 1.2 其他算子的模式（参考标杆）

**PreInsert 的实现**（无 Factory，只有 Registry）：

```python
# registry.py - 注册表
class PreInsertActionRegistry:
    _actions: dict[str, type[BasePreInsertAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePreInsertAction]) -> None:
        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePreInsertAction]:
        if name not in cls._actions:
            raise ValueError(f"Unknown action: '{name}'")
        return cls._actions[name]

# 注册示例（支持层级命名）
PreInsertActionRegistry.register("none", NoneAction)
PreInsertActionRegistry.register("transform.chunking", ChunkingAction)
PreInsertActionRegistry.register("extract.keyword", KeywordExtractAction)
PreInsertActionRegistry.register("score.importance", ImportanceScoreAction)
```

**Operator 使用方式**（直接从 Registry 获取类并实例化）：

```python
# operator.py
class PreInsert(MapFunction):
    def __init__(self, config):
        action_config = config.get("operators.pre_insert", {})
        action_name = action_config.get("action", "none")

        # 直接从 Registry 获取类
        action_class = PreInsertActionRegistry.get(action_name)

        # 实例化（配置由 Action 自己读取）
        self.action: BasePreInsertAction = action_class(action_config)
```

**优势**：

- 清晰的层级分类（transform/extract/score）
- 无中间层，代码简洁
- 配置与代码结构一致
- Action 类自己负责配置读取（单一职责）

______________________________________________________________________

## 二、重构目标

### 2.1 新的分类体系

基于论文和实际存储结构，将 MemoryService 分为三大类：

#### **Partitional（无中心化）**

- **特点**：去中心化存储，数据分散在不同分区/桶中，无全局索引
- **典型结构**：哈希桶、LSH、向量索引（FAISS）、KV 存储
- **候选 Service**：
  - `partitional.vector_memory` - 向量记忆（FAISS 索引）
  - `partitional.vector_hash_memory` - LSH 哈希向量记忆
  - `partitional.key_value_memory` - KV 存储（BM25S 索引）
  - `partitional.short_term_memory` - 短期记忆（滑窗+VDB）

#### **Hierarchical（有层级结构）**

- **特点**：分层组织，有明确的层级关系（如 STM→MTM→LTM）
- **典型结构**：多层存储、图结构（有中心节点）
- **候选 Service**：
  - `hierarchical.three_tier` - 三层记忆（STM/MTM/LTM）
  - `hierarchical.graph_memory` - 图记忆（知识图谱）
  - `hierarchical.two_tier` - 两层记忆（Short/Long）

#### **Hybrid（混合结构）**

- **特点**：一份数据+多种索引，融合多种检索方式
- **典型结构**：同时支持向量/文本/图检索的混合索引
- **候选 Service**：
  - `hybrid.multi_index` - 多索引混合（VDB+KV+Graph）
  - `hybrid.weighted_fusion` - 加权融合检索
  - `hybrid.rrf_fusion` - RRF 融合检索

### 2.2 映射关系

**现有 Service → 新分类**：

| 现有名称              | 新分类                          | 理由                     |
| --------------------- | ------------------------------- | ------------------------ |
| `short_term_memory`   | `partitional.short_term_memory` | 滑窗+单一VDB索引，无层级 |
| `vector_memory`       | `partitional.vector_memory`     | 单一向量索引（FAISS）    |
| `key_value_memory`    | `partitional.key_value_memory`  | 单一文本索引（BM25S）    |
| `graph_memory`        | `hierarchical.graph_memory`     | 图结构有中心节点         |
| `hierarchical_memory` | `hierarchical.three_tier`       | 显式三层结构             |
| `hybrid_memory`       | `hybrid.multi_index`            | 多索引融合               |

**新增 Service**（未来扩展）：

- `partitional.vector_hash_memory` - VectorHashMemoryService（已存在但未注册）
- `hierarchical.two_tier` - 两层记忆（简化版）
- `hybrid.rrf_fusion` - RRF 融合策略的混合记忆

______________________________________________________________________

## 三、重构方案（移除 Factory，纯 Registry 模式）

### 3.1 核心架构变更

**变更前**（Factory + Registry 重叠）：

```
Pipeline → Factory.create(name, config) → ServiceFactory → Service 实例
                ↓
            Registry.get(name) → Service 类
```

**变更后**（纯 Registry）：

```
Pipeline → Registry.get(name) → Service.from_config(config) → ServiceFactory
```

**关键设计决策**：

1. **移除 MemoryServiceFactory**：功能重叠，增加复杂度
1. **Service 类自己负责配置读取**：通过 `from_config` 类方法
1. **Registry 只做注册表**：name → Service 类的映射

### 3.2 创建 MemoryServiceRegistry

**位置**：`packages/sage-middleware/src/sage/middleware/components/sage_mem/services/registry.py`

```python
"""MemoryService 注册表

管理所有 MemoryService 的注册和获取，支持层级分类。
采用与 PreInsert/PostInsert 一致的纯 Registry 模式。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_service import BaseService


class MemoryServiceRegistry:
    """MemoryService 注册表

    支持层级命名（如 "partitional.vector_memory"），便于分类管理。

    三大类：
    - Partitional（无中心化）：vector_memory, key_value_memory, short_term_memory
    - Hierarchical（有层级）：graph_memory, three_tier, two_tier
    - Hybrid（混合）：multi_index, weighted_fusion, rrf_fusion
    """

    _services: dict[str, type[BaseService]] = {}

    @classmethod
    def register(cls, name: str, service_class: type[BaseService]) -> None:
        """注册一个 Service

        Args:
            name: Service 名称（支持点分隔的层级名，如 "partitional.vector_memory"）
            service_class: Service 类
        """
        cls._services[name] = service_class

    @classmethod
    def get(cls, name: str) -> type[BaseService]:
        """获取 Service 类

        Args:
            name: Service 名称

        Returns:
            Service 类

        Raises:
            ValueError: 如果 Service 未注册
        """
        if name not in cls._services:
            raise ValueError(
                f"Unknown MemoryService: '{name}'. "
                f"Available services: {list(cls._services.keys())}"
            )
        return cls._services[name]

    @classmethod
    def list_services(cls, category: str | None = None) -> list[str]:
        """列出所有已注册的 Service

        Args:
            category: 可选，按类别筛选（"partitional"/"hierarchical"/"hybrid"）

        Returns:
            Service 名称列表
        """
        if category is None:
            return list(cls._services.keys())

        # 按类别筛选
        prefix = f"{category}."
        return [name for name in cls._services.keys() if name.startswith(prefix)]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查 Service 是否已注册

        Args:
            name: Service 名称

        Returns:
            是否已注册
        """
        return name in cls._services

    @classmethod
    def get_category(cls, name: str) -> str | None:
        """获取 Service 的类别

        Args:
            name: Service 名称

        Returns:
            类别名称（"partitional"/"hierarchical"/"hybrid"），如果无层级则返回 None
        """
        if "." in name:
            return name.split(".")[0]
        return None


# ============================================================
# 注册所有内置 Service
# ============================================================

def _register_builtin_services():
    """注册所有内置 Service"""
    from .graph_memory_service import GraphMemoryService
    from .hierarchical_memory_service import HierarchicalMemoryService
    from .hybrid_memory_service import HybridMemoryService
    from .key_value_memory_service import KeyValueMemoryService
    from .short_term_memory_service import ShortTermMemoryService
    from .vector_memory_service import VectorMemoryService
    from .vector_hash_memory_service import VectorHashMemoryService

    # Partitional 类（无中心化）
    MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
    MemoryServiceRegistry.register("partitional.vector_hash_memory", VectorHashMemoryService)
    MemoryServiceRegistry.register("partitional.key_value_memory", KeyValueMemoryService)
    MemoryServiceRegistry.register("partitional.short_term_memory", ShortTermMemoryService)

    # Hierarchical 类（有层级）
    MemoryServiceRegistry.register("hierarchical.graph_memory", GraphMemoryService)
    MemoryServiceRegistry.register("hierarchical.three_tier", HierarchicalMemoryService)

    # Hybrid 类（混合）
    MemoryServiceRegistry.register("hybrid.multi_index", HybridMemoryService)


# 自动注册所有内置 Service
_register_builtin_services()
```

### 3.3 修改 BaseService 添加 from_config 方法

**位置**：`packages/sage-middleware/src/sage/middleware/components/sage_mem/services/base_service.py`

```python
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.runtime.factory.service_factory import ServiceFactory


class BaseService(ABC):
    """MemoryService 基类"""

    @classmethod
    def from_config(
        cls, service_name: str, config: Any
    ) -> ServiceFactory:
        """从配置创建 ServiceFactory（供 Pipeline 使用）

        Args:
            service_name: 服务名称（如 "partitional.vector_memory"）
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例

        Notes:
            - 子类需要重写此方法，实现自己的配置读取逻辑
            - 配置路径：services.{service_name}.*
        """
        raise NotImplementedError(f"{cls.__name__} must implement from_config()")
```

### 3.4 示例：ShortTermMemoryService 实现 from_config

```python
from sage.kernel.runtime.factory.service_factory import ServiceFactory

class ShortTermMemoryService(BaseService):
    # ... 现有代码 ...

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              partitional.short_term_memory:
                max_dialog: 10
                embedding_dim: 1024
        """
        # 读取配置参数
        max_dialog = config.get(f"services.{service_name}.max_dialog")
        if max_dialog is None:
            raise ValueError(f"Missing config: services.{service_name}.max_dialog")

        embedding_dim = config.get(f"services.{service_name}.embedding_dim", 1024)

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "max_dialog": max_dialog,
                "embedding_dim": embedding_dim,
            },
        )
```

### 3.5 Pipeline 使用方式

**位置**：`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py`

**变更前**：

```python
from sage.middleware.components.sage_mem.services import MemoryServiceFactory

service_name = config.get("services.register_memory_service", "short_term_memory")
factory = MemoryServiceFactory.create(service_name, config)  # 使用 Factory
env.register_service_factory(service_name, factory)
```

**变更后**：

```python
from sage.middleware.components.sage_mem.services import MemoryServiceRegistry

service_name = config.get("services.register_memory_service")
service_class = MemoryServiceRegistry.get(service_name)  # 从 Registry 获取类
factory = service_class.from_config(service_name, config)  # 调用类方法
env.register_service_factory(service_name, factory)
```

### 3.6 配置文件格式

**新格式**（唯一格式，不向后兼容）：

```yaml
services:
  # 使用层级命名
  register_memory_service: "hierarchical.three_tier"

  # 配置路径与服务名一致
  hierarchical.three_tier:
    tier_mode: "three_tier"
    tier_capacities:
      stm: 20
      mtm: 200
      lpm: -1
    migration_policy: "heat"
    embedding_dim: 1024
```

### 3.7 文件结构调整

```
packages/sage-middleware/src/sage/middleware/components/sage_mem/services/
├── __ini（不向后兼容，直接重构）

### Phase 1: 创建 Registry 和 BaseService.from_config

**任务**：
1. ✅ 创建 `registry.py`（只注册新格式名称）
2. ✅ 修改 `base_service.py`，添加 `from_config` 抽象方法
3. ✅ 编写单元测试验证 Registry 功能

**验收标准**：
- `MemoryServiceRegistry.get("partitional.vector_memory")` 返回 `VectorMemoryService`
- `MemoryServiceRegistry.list_services("partitional")` 返回所有 Partitional 类 Service
- `BaseService.from_config` 定义清晰

**预计工作量**：1-2 小时

### Phase 2: 所有 Service 实现 from_config

**任务**：
1. ✅ `ShortTermMemoryService.from_config` - 参考现有 `_create_short_term_memory`
2. ✅ `VectorMemoryService.from_config` - 参考现有 `_create_vector_memory`
3. ✅ `GraphMemoryService.from_config` - 参考现有 `_create_graph_memory`
4. ✅ `HierarchicalMemoryService.from_config` - 参考现有 `_create_hierarchical_memory`
5. ✅ `HybridMemoryService.from_config` - 参考现有 `_create_hybrid_memory`
6. ✅ `KeyValueMemoryService.from_config` - 参考现有 `_create_key_value_memory`
7. ✅ `VectorHashMemoryService.from_config` - 新增（参考 vector_memory）

**验收标准**：
- 每个 Service 能从配置正确创建 ServiceFactory
- 配置参数读取与原 Factory 逻辑一致
- 单元测试覆盖所有 Service

**预计工作量**：3-4 小时

### Phase 3: 修改 Pipeline 使用 Registry

**任务**：
1. ✅ 修改 `memory_test_pipeline.py` 使用新模式
2. ✅ 删除 `memory_service_factory.py`
3. ✅ 更新 `services/__init__.py` 导出 Registry
4. ✅ 更新单元测试

**验收标准**：
- Pipeline 能正常启动
- 所有现有功能测试通过
- 代码更简洁（移除 Factory 层）

**预计工作量**：1-2 小时

### Phase 4: 迁移所有配置文件

**任务**：
1. ✅ 迁移 `primitive_memory_model/` 下的所有配置（13 个文件）
2. ✅ 更新排列组合实验设计文档
3. ✅ 更新示例（`examples/tutorials/l6/`）
4. ✅ 更新文档（`docs-public/`）

**迁移清单**：
```

locomo_short_term_memory_pipeline.yaml → partitional.short_term_memory locomo_tim_pipeline.yaml →
partitional.vector_memory locomo_scm_pipeline.yaml → partitional.short_term_memory
locomo_hipporag_pipeline.yaml → hierarchical.graph_memory locomo_hipporag2_pipeline.yaml →
hierarchical.graph_memory locomo_amem_pipeline.yaml → hierarchical.graph_memory locomo_m在 Pipeline
中使用 Service

```python
from sage.middleware.components.sage_mem.services import MemoryServiceRegistry

# 从配置读取服务名
service_name = config.get("services.register_memory_service")
# 输出: "partitional.vector_memory"

# 从 Registry 获取 Service 类
service_class = MemoryServiceRegistry.get(service_name)
# 输出: <class 'VectorMemoryService'>

# 调用类方法创建 ServiceFactory
factory = service_class.from_config(service_name, config)
# 内部读取 services.partitional.vector_memory.* 的配置

# 注册到环境
env.register_service_factory(service_name, factory)
```

### 5.2 列举所有 Partitional 类 Service

````python
from sage.middleware.components.sage_mem.services import MemoryServiceRegistry

# 列出所有 Partitional 类 Service
partitional_services = MemoryServiceRegistry.list_services("partitional")
print(partitional_services)
# 输出: ['partitional.vector_memory', 'partitional.vector_hash_memory',
#        'partitional.key_value_memory', 'partitional.short_term_memory']

# 列出所有 Service
all_services = MemoryServiceRegistry.list_services()
print(all_services)
# 输出: ['partitional.vector_memory', 'partitional.vector_hash_memory', ...,
#        'hierarchical.graph_memory', 'hierarchical.three_tier',
#        'hybrid.multi_index'

---

## 五、示例代码

### 5.1 使用新格式创建 Service

```python
from sage.middleware.components.sage_mem.services import MemoryServiceFactory

# 新格式：明确指定类别
factory = MemoryServiceFactory.create("partitional.vector_memory", config)
env.register_service_factory("partitional.vector_memory", factory)

# 旧格式：仍然支持（但不推荐）
factory = MemoryServiceFactory.create("vector_memory", config)
env.register_service_factory("vector_memory", factory)
````

### 5.2 列举所有 Partitional 类 Service

```python
from sage.middleware.components.sage_mem.services import MemoryServiceRegistry

# 列出所有 Partitional 类 Service
partitional_services = MemoryServiceRegistry.list_services("partitional")
print(partitional_services)
# 输出: ['partitional.vector_memory', 'partitional.vector_hash_memory',
#        'partitional.key_value_memory', 'partitional.short_term_memory']

# 列出所有 Service
all_services = MemoryServiceRegistry.list_services()
print(all_services)
# 输出: ['partitional.vector_memory', ..., 'hie纯 Registry 模式
5. **无中间层**：移除 Factory，代码更简洁，职责更清晰

### 6.2 实验优势

1. **组合实验更清晰**：`Phase D1.1: Partitional 扫描`，`Phase D1.2: Hierarchical 扫描`
2. **结果分析更直观**：可按类别汇总性能指标
3. **易于对比**：同类别内的不同实现可直接对比

### 6.3 开发体验

1. **单一职责**：Service 类自己负责配置读取
2. **易于理解**：从 Registry 获取类 → 调用 from_config → 得到 ServiceFactory

#### Partitional 类（无中心化）
- `partitional.short_term_memory` - STM（滑窗+VDB）
  - 参数：`max_dialog`, `embedding_dim`
- `partitional.vector_memory` - 向量记忆（FAISS）
  - 参数：`dim`, `index_type`, `index_config`
- `partitional.vector_hash_memory` - LSH 哈希向量记忆
  - 参数：`dim`, `nbits`, `k_nearest`
- `partitional.key_value_memory` - KV 存储（BM25S）
  - 参数：`match_type`, `key_extractor`, `fuzzy_threshold`

#### Hierarchical 类（有层级）
- `hierarchical.three_tier` - 三层记忆（STM/MTM/LTM）
  - 参数：`tier_mode`, `tier_capacities`, `migration_policy`
- `hierarchical.graph_memory` - 图记忆（知识图谱）
  - 参数：`graph_type`, `edge_types`, `link_policy`

#### Hybrid 类（混合）
- `hybrid.multi_index` - 多索引混合（VDB+KV+Graph）
  - 参数：`indexes`, `fusion_strategy`, `fusion_weights`
```

______________________________________________________________________

## 六、优势总结

### 6.1 架构优势

1. **清晰的分类体系**：Partitional/Hierarchical/Hybrid 直接对应存储结构本质
1. **易于扩展**：新增 Service 时自然归入对应类别
1. **与论文一致**：直接映射到排列组合实验设计
1. **代码一致性**：与其他算子（PreInsert/PostInsert）使用相同的 Registry 模式

### 6.2 实验优势

1. **组合实验更清晰**：`Phase D1.1: Partitional 扫描`，`Phase D1.2: Hierarchical 扫描`
1. **结果分析更直观**：可按类别汇总性能指标
1. **易于对比**：同类别内的不同实现可直接对比

### 6.3 用户体验

1. **向后兼容**：旧配置文件无需修改
1. **渐进迁移**：可逐步升删除 Factory，修改所有 Service 和配置文件
1. **测试覆盖**：需要确保所有 Service 的 from_config 正确工作
1. **文档更新**：需要同步更新所有文档
1. **不向后兼容**：旧配置文件需要全部迁移

### 7.2 缓解措施

1. **分阶段实施**：每个 Phase 都有明确的验收标准
1. **充分测试**：为每个 Service 的 from_config 编写单元测试
1. **批量迁移工具**：编写脚本批量更新配置文件
1. **代码迁移成本**：需要修改 Factory 和配置文件
1. **测试覆盖**：需要确保新旧格式都能正常工作
1. **文档更新**：需要同步更新所有文档

### 7.2 缓解措施

1. **分阶段实施**：Phase 1-3 不破坏现有代码，Phase 4 在下一个大版本
1. **充分测试**：每个 Phase 都有明确的验收标准
1. **向后兼容**：保留旧格式支持，给用户足够的迁移时间
1. **文档先行**：先更新设计文档，再逐步实施

______________________________________________________________________

## 八、时间表

| Phase | 任务 | 预计工作量 | 优和 BaseService.from_config | 1-2 小时 | 高 | | Phase 2 | 所有 Service 实现
from_config | 3-4 小时 | 高 | | Phase 3 | 修改 Pipeline 和删除 Factory | 1-2 小时 | 高 | | Phase 4 | 迁移所有配置文件 |
4-6 小时 | 中 |

**总计**：约 9-14 小时（1-2 个工作日| 低 |

**总计**：约 1-2 个工作日（Phase 1-3）

______________________________________________________________________

## 九、参考资料

- **PreInsert Registry
  实现**：`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/pre_insert/registry.py`
- **PostInsert Registry
  实现**：`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/post_insert/registry.py`
- **现有
  MemoryServiceFactory**：`packages/sage-middleware/src/sage/middleware/components/sage_mem/services/memory_service_factory.py`
- **排列组合实验设计**：`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/Memory_Combinatorial_Experiment_Design.md`
