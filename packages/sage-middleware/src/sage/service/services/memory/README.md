# Memory Service Module

## 重构后的架构

基于您的建议，我们重新设计了架构：

### 1. 保留并改进原有Memory Service

**原有MemoryService的优势:**
- 功能完整，接口丰富
- 有完整的collection、storage、search层次
- 已经过验证的架构

**改进方案:**
- 创建 `MemoryServiceTask` 继承 `BaseServiceTask`
- 保留原有 `MemoryService` 以维持向后兼容
- 保持所有原有功能不变

### 2. 分离Storage和Search Engine

按照单一职责原则，将引擎组件分离到对应服务：

**迁移映射:**
```
memory/storage_engine/kv_backend/     -> kv/storage_engine/
memory/storage_engine/text_storage.py -> kv/text_storage.py
memory/search_engine/kv_index/        -> kv/search_engine/

memory/storage_engine/vector_storage.py -> vdb/vector_storage.py  
memory/search_engine/vdb_index/          -> vdb/search_engine/
```

**保留在Memory中:**
- memory_collection/ (高级抽象层)
- memory_manager.py (核心管理器)
- storage_engine/metadata_storage.py (元数据管理)
- search_engine/graph_index/ (图相关索引)
- search_engine/hybrid_index/ (混合索引)

## 目录结构

```
memory/
├── __init__.py                     # 模块初始化
├── README.md                       # 本文档  
├── REFACTOR_PLAN.md               # 重构计划
├── api.py                         # 原有API接口
├── memory_service.py              # 原有Memory服务 (兼容性)
├── memory_service_task.py         # 新的Memory服务任务 (BaseServiceTask)
├── memory_manager.py              # Memory管理器
├── memory_collection/             # Collection层抽象
│   ├── base_collection.py         # 基础集合类
│   ├── kv_collection.py          # KV集合 (使用kv服务)
│   ├── vdb_collection.py         # VDB集合 (使用vdb服务)  
│   └── graph_collection.py       # 图集合
├── search_engine/                 # 剩余的搜索引擎
│   ├── graph_index/              # 图索引
│   └── hybrid_index/             # 混合索引
├── storage_engine/                # 剩余的存储引擎  
│   └── metadata_storage.py       # 元数据存储
└── utils/                         # 工具函数
    └── path_utils.py             # 路径工具
```

## 使用方式

### 1. 原有方式 (保持兼容)

```python
from sage.service.memory import MemoryService, get_memory

# 直接使用原有服务
memory_service = MemoryService()

# 或使用全局API
memory = get_memory({
    'collection_name': 'test_collection',
    'backend_type': 'VDB',
    'embedding_model_name': 'default',
    'dim': 384
})
```

### 2. 新的服务任务方式

```python
from sage.service.memory import MemoryServiceTask, create_memory_service_factory

# 创建服务工厂
memory_factory = create_memory_service_factory(
    service_name="memory_service",
    data_dir="/path/to/data"
)

# 在SAGE DAG中使用
# env.register_service_factory(memory_factory)
```

### 3. 与KV/VDB服务协同

```python
from sage.service import (
    create_kv_service_factory, 
    create_vdb_service_factory,
    create_memory_service_factory
)

# 创建完整的服务栈
kv_factory = create_kv_service_factory("kv_service")
vdb_factory = create_vdb_service_factory("vdb_service") 
memory_factory = create_memory_service_factory("memory_service")

# Memory服务可以调用KV/VDB服务的底层功能
```

## 架构优势

1. **保留原有功能**: Memory服务的完整功能得以保留
2. **职责分离**: Storage/Search引擎分离到对应服务  
3. **灵活部署**: 支持单机和分布式部署
4. **向后兼容**: 原有代码无需修改
5. **渐进迁移**: 可逐步从Legacy迁移到Task模式
