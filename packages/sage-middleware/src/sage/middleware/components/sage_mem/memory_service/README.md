# MemoryService Registry 使用指南

> **最后更新**：2025-12-24
>
> **状态**：✅ 任务1已完成（基础设施 + Registry）

## 概述

MemoryService Registry 是一个纯 Registry 模式的服务管理系统，用于替代原有的 Factory + Registry 双层架构。

**设计原则**：

1. **纯 Registry 模式** - 移除 Factory 层，Service 类自己负责配置解析
1. **层级命名** - 支持 `category.service_name` 格式（如 `partitional.vector_memory`）
1. **统一接口** - 所有 Service 必须实现 `insert`/`retrieve`/`delete`/`get_stats`/`from_config`
1. **严格 1:1 关系** - 一个 Service 对应一个 Collection

## 文件结构

```
packages/sage-middleware/src/sage/middleware/components/sage_mem/memory_service/
├── __init__.py                      # 导出 Registry 和 BaseService
├── base_service.py                  # BaseMemoryService 抽象基类
├── registry.py                      # MemoryServiceRegistry 注册表
├── partitional/                     # Partitional 类服务（待实现）
│   ├── vector_memory.py
│   ├── key_value_memory.py
│   ├── short_term_memory.py
│   └── vector_hash_memory.py
├── hierarchical/                    # Hierarchical 类服务（待实现）
│   ├── graph_memory.py
│   ├── three_tier.py
│   └── two_tier.py
└── hybrid/                          # Hybrid 类服务（待实现）
    ├── multi_index.py
    └── rrf_fusion.py
```

## 快速开始

### 1. 创建一个 MemoryService

```python
from sage.middleware.components.sage_mem.memory_service import BaseMemoryService
from sage.kernel.runtime.factory.service_factory import ServiceFactory
import numpy as np


class VectorMemoryService(BaseMemoryService):
    """向量记忆服务"""

    @classmethod
    def from_config(cls, service_name: str, config) -> ServiceFactory:
        """从配置创建 ServiceFactory"""
        # 读取配置
        dim = config.get(f"services.{service_name}.dim", 768)
        index_type = config.get(f"services.{service_name}.index_type", "IndexFlatL2")

        # 返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            dim=dim,
            index_type=index_type,
        )

    def __init__(self, dim: int = 768, index_type: str = "IndexFlatL2"):
        super().__init__()
        self.dim = dim
        self.index_type = index_type
        # ... 初始化 Collection

    def insert(self, entry: str, vector=None, metadata=None, *,
               insert_mode="passive", insert_params=None) -> str:
        """插入记忆"""
        # ... 实现
        return "memory_id_123"

    def retrieve(self, query=None, vector=None, metadata=None, top_k=10):
        """检索记忆"""
        # ... 实现
        return [{"text": "...", "metadata": {}, "score": 0.95}]

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        # ... 实现
        return True

    def get_stats(self):
        """获取统计信息"""
        # ... 实现
        return {"total_count": 100, "index_type": self.index_type}
```

### 2. 注册 Service

```python
from sage.middleware.components.sage_mem.memory_service import MemoryServiceRegistry

# 注册服务
MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
```

### 3. 在 Pipeline 中使用

```python
# 获取 Service 类
service_class = MemoryServiceRegistry.get("partitional.vector_memory")

# 从配置创建 ServiceFactory
factory = service_class.from_config(service_name, config)

# 在环境中注册
env.register_service_factory(service_name, factory)
```

### 4. 调用 Service

```python
# 插入记忆
memory_id = env.call_service(
    "partitional.vector_memory",
    entry="Hello, world!",
    vector=embedding,
    method="insert"
)

# 检索记忆
results = env.call_service(
    "partitional.vector_memory",
    query="Hello",
    vector=query_embedding,
    top_k=5,
    method="retrieve"
)
```

## Registry API

### 注册服务

```python
MemoryServiceRegistry.register(name: str, service_class: type[BaseMemoryService])
```

**参数**：

- `name`: 服务名称（如 `"partitional.vector_memory"`）
- `service_class`: Service 类（必须继承 `BaseMemoryService`）

**示例**：

```python
MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
```

### 获取服务类

```python
service_class = MemoryServiceRegistry.get(name: str) -> type[BaseMemoryService]
```

**参数**：

- `name`: 服务名称

**返回**：

- Service 类

**异常**：

- `ValueError`: 如果服务不存在

**示例**：

```python
service_class = MemoryServiceRegistry.get("partitional.vector_memory")
```

### 列出所有服务

```python
services = MemoryServiceRegistry.list_services(category: str | None = None) -> list[str]
```

**参数**：

- `category`: 类别名称（可选），如 `"partitional"`, `"hierarchical"`, `"hybrid"`

**返回**：

- 服务名称列表

**示例**：

```python
# 列出所有服务
all_services = MemoryServiceRegistry.list_services()
# ['partitional.vector_memory', 'partitional.key_value_memory', ...]

# 列出 Partitional 类服务
partitional_services = MemoryServiceRegistry.list_services(category="partitional")
# ['partitional.vector_memory', 'partitional.key_value_memory', ...]
```

### 检查服务是否已注册

```python
is_registered = MemoryServiceRegistry.is_registered(name: str) -> bool
```

**示例**：

```python
if MemoryServiceRegistry.is_registered("partitional.vector_memory"):
    print("Service is registered")
```

### 获取服务类别

```python
category = MemoryServiceRegistry.get_category(name: str) -> str | None
```

**示例**：

```python
category = MemoryServiceRegistry.get_category("partitional.vector_memory")
# "partitional"
```

### 列出所有类别

```python
categories = MemoryServiceRegistry.list_categories() -> list[str]
```

**示例**：

```python
categories = MemoryServiceRegistry.list_categories()
# ['partitional', 'hierarchical', 'hybrid']
```

### 注销服务（测试用）

```python
success = MemoryServiceRegistry.unregister(name: str) -> bool
```

**示例**：

```python
MemoryServiceRegistry.unregister("partitional.vector_memory")
```

### 清空所有注册（测试用）

```python
MemoryServiceRegistry.clear()
```

## BaseMemoryService 接口

所有 MemoryService 必须继承 `BaseMemoryService` 并实现以下方法：

### 1. from_config（类方法）

```python
@classmethod
def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
    """从配置创建 ServiceFactory"""
```

**职责**：

- 读取配置（`config.get(f"services.{service_name}.*")`）
- 创建 `ServiceFactory` 实例
- 返回 `ServiceFactory(service_name, service_class, **kwargs)`

### 2. insert

```python
def insert(
    self,
    entry: str,
    vector: np.ndarray | list[float] | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    insert_mode: Literal["active", "passive"] = "passive",
    insert_params: dict[str, Any] | None = None,
) -> str:
    """插入记忆"""
```

**参数**：

- `entry`: 记忆文本
- `vector`: 向量表示（可选）
- `metadata`: 元数据（可选）
- `insert_mode`: 插入模式
  - `"passive"`: 自动处理（默认）
  - `"active"`: 显式控制（通过 `insert_params` 指定）
- `insert_params`: 插入参数（如 `target_tier`, `priority`, `ttl`）

**返回**：

- 记忆ID（字符串）

### 3. retrieve

```python
def retrieve(
    self,
    query: str | None = None,
    vector: np.ndarray | list[float] | None = None,
    metadata: dict[str, Any] | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """检索记忆"""
```

**参数**：

- `query`: 查询文本（可选）
- `vector`: 查询向量（可选）
- `metadata`: 筛选条件（可选），常用字段：
  - `tiers`: 指定检索的层级（如 `["STM", "MTM"]`）
  - `method`: 检索方法（如 `"vector"`, `"text"`, `"hybrid"`）
  - `min_score`: 最小相似度阈值
  - `time_range`: 时间范围
- `top_k`: 返回数量

**返回**：

- 记忆列表，每个元素为 dict：
  - `text`: 记忆文本（str）
  - `metadata`: 元数据（dict）
  - `score`: 相似度分数（float）
  - `id`: 记忆ID（str，可选）

### 4. delete

```python
def delete(self, item_id: str) -> bool:
    """删除记忆"""
```

**参数**：

- `item_id`: 记忆ID

**返回**：

- 是否成功删除

### 5. get_stats

```python
def get_stats(self) -> dict[str, Any]:
    """获取统计信息"""
```

**返回**：

- 统计数据，常见字段：
  - `total_count`: 总记忆数量
  - `tier_counts`: 各层级记忆数量（dict）
  - `index_type`: 索引类型
  - `collection_name`: Collection 名称
  - `last_updated`: 最后更新时间

## 三大类 Service

### Partitional（去中心化存储）

**特点**：数据分散在不同分区/桶中，无全局索引

**候选 Service**：

- `partitional.vector_memory` - 向量记忆（FAISS 索引）
- `partitional.key_value_memory` - 文本记忆（BM25S 索引）
- `partitional.short_term_memory` - 短期记忆（滑窗+VDB）
- `partitional.vector_hash_memory` - LSH 哈希记忆

### Hierarchical（有层级结构）

**特点**：分层组织，有明确的层级关系

**候选 Service**：

- `hierarchical.graph_memory` - 图记忆（有中心节点）
- `hierarchical.three_tier` - 三层记忆（STM/MTM/LTM）
- `hierarchical.two_tier` - 两层记忆（Short/Long）

### Hybrid（混合结构）

**特点**：一份数据+多种索引，融合多种检索方式

**已实现 Service**：

- ✅ `hybrid.multi_index` - 多索引混合（VDB+KV+Graph）
  - 支持模式：Mem0 基础版、Mem0ᵍ 图增强版、EmotionalRAG 双向量、自定义组合
  - 融合策略：weighted（加权）、rrf（倒数排名）、union（合并）
  - 被动插入：自动检测相似项，触发 CRUD 决策

**待实现 Service**：

- ⏳ `hybrid.rrf_fusion` - RRF 融合检索（简化版）

## 测试

### 运行单元测试

```bash
# 独立测试脚本（避免 C++ 依赖问题）
python packages/sage-middleware/tests/unit/components/sage_mem/memory_service/test_registry_standalone.py
```

**测试覆盖**：

- ✅ 注册/注销服务
- ✅ 获取服务类
- ✅ 列出所有服务
- ✅ 按类别列出服务
- ✅ 检查注册状态
- ✅ 获取服务类别
- ✅ 列出所有类别
- ✅ 清空注册表

## 迁移指南

### 从旧的 Factory 模式迁移

**旧代码**（使用 MemoryServiceFactory）：

```python
from sage.middleware.components.sage_mem.services.memory_service_factory import MemoryServiceFactory

# 创建 Factory
factory = MemoryServiceFactory.create("vector_memory", config)

# 注册
env.register_service_factory("vector_memory", factory)
```

**新代码**（使用 Registry）：

```python
from sage.middleware.components.sage_mem.memory_service import MemoryServiceRegistry

# 获取 Service 类
service_class = MemoryServiceRegistry.get("partitional.vector_memory")

# 从配置创建 Factory
factory = service_class.from_config("partitional.vector_memory", config)

# 注册
env.register_service_factory("partitional.vector_memory", factory)
```

### Service 实现迁移

**需要添加**：

1. `from_config` 类方法（必须）
1. 确保 `insert`/`retrieve` 参数签名与 `BaseMemoryService` 一致

**示例**：

```python
@classmethod
def from_config(cls, service_name: str, config) -> ServiceFactory:
    """从配置创建 ServiceFactory"""
    # 读取配置
    dim = config.get(f"services.{service_name}.dim", 768)
    index_type = config.get(f"services.{service_name}.index_type", "IndexFlatL2")
    collection_name = config.get(f"services.{service_name}.collection_name", "vector_memory")

    # 返回 ServiceFactory
    return ServiceFactory(
        service_name=service_name,
        service_class=cls,
        dim=dim,
        index_type=index_type,
        collection_name=collection_name,
    )
```

## 下一步工作

根据 [PARALLEL_TASKS_BREAKDOWN.md](../PARALLEL_TASKS_BREAKDOWN.md)，接下来需要完成：

- [ ] **任务2**: Partitional 类 Service（4个）

  - `partitional.vector_memory`
  - `partitional.key_value_memory`
  - `partitional.short_term_memory`
  - `partitional.vector_hash_memory`

- [ ] **任务3**: Hierarchical 类 Service（2个）

  - `hierarchical.graph_memory`
  - `hierarchical.three_tier`

- [ ] **任务4**: Hybrid 类 Service（1个）

  - `hybrid.multi_index`

- [ ] **任务5**: 集成测试 + 文档

## 参考资料

- [REFACTOR_MEMORY_SERVICE_REGISTRY.md](../REFACTOR_MEMORY_SERVICE_REGISTRY.md) - 重构方案文档
- [PARALLEL_TASKS_BREAKDOWN.md](../PARALLEL_TASKS_BREAKDOWN.md) - 任务拆解方案
- [PreInsert Registry](../../../../../middleware/operators/pre_insert/registry.py) - 参考实现

## 常见问题

### Q1: 为什么移除 Factory 层？

**A**: Factory 层与 Registry 功能重叠，增加了复杂度。纯 Registry 模式更简洁，与其他算子（PreInsert/PostInsert）一致。

### Q2: 为什么 Registry 不做运行时类型检查？

**A**: 为了避免循环导入问题。我们假设调用者确保传入的类正确继承 `BaseMemoryService`。

### Q3: 如何处理配置路径？

**A**: 配置路径格式为 `services.{service_name}.*`，例如：

```yaml
services:
  partitional.vector_memory:
    dim: 1024
    index_type: "IndexHNSWFlat"
```

### Q4: insert_mode 和 insert_params 有什么用？

**A**:

- `insert_mode="passive"`: 自动处理（默认），如自动选择 tier、自动生成 ID
- `insert_mode="active"`: 显式控制，通过 `insert_params` 指定详细参数（如 `target_tier`, `priority`, `ttl`）

### Q5: 如何处理 metadata 参数？

**A**: `metadata` 用于传递 Service 特定参数：

- **insert**: 存储额外信息（如 `source`, `timestamp`）
- **retrieve**: 筛选条件（如 `tiers`, `method`, `min_score`, `time_range`）

## 更新日志

- **2025-12-24**: 任务1完成
  - ✅ 创建 `base_service.py`
  - ✅ 创建 `registry.py`
  - ✅ 创建 `__init__.py`
  - ✅ 创建单元测试 `test_registry_standalone.py`
  - ✅ 测试通过
