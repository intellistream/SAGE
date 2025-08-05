# Memory Service Module

## 简洁架构

Memory服务现在只包含3个文件：

```
memory/
├── __init__.py           # 模块初始化
├── memory_service.py     # Memory微服务实现
└── README.md            # 本文档
```

## 架构设计

### Memory微服务

Memory服务是一个**协调服务**，它继承自`BaseServiceTask`，在SAGE DAG中作为服务节点运行。

**职责**：
- 协调KV和VDB服务
- 提供高级记忆管理功能
- 管理会话记忆
- 提供语义搜索

**不包含**：
- 具体的存储实现（由KV服务负责）
- 向量搜索实现（由VDB服务负责）
- 复杂的索引引擎（分离到相应服务）

### 架构原则

1. **单一职责**：Memory服务只做记忆管理和协调
2. **依赖倒置**：依赖抽象的KV和VDB服务接口
3. **简洁设计**：避免过度工程化
4. **微服务化**：每个服务专注自己的核心功能

## 使用示例

### 在SAGE DAG中使用

```python
from sage.service.memory import create_memory_service_factory
from sage.service.kv import create_kv_service_factory
from sage.service.vdb import create_vdb_service_factory

# 创建服务工厂
kv_factory = create_kv_service_factory("kv_service")
vdb_factory = create_vdb_service_factory("vdb_service") 
memory_factory = create_memory_service_factory("memory_service")

# 在DAG中注册
dag.register_service(kv_factory)
dag.register_service(vdb_factory)
dag.register_service(memory_factory)

# 使用Memory服务
memory_service = dag.get_service("memory_service")

# 存储记忆
memory_id = memory_service.store_memory(
    session_id="user123",
    content="用户询问了Python的使用方法",
    vector=[0.1, 0.2, 0.3, ...],  # 384维向量
    memory_type="conversation"
)

# 搜索相关记忆
memories = memory_service.search_memories(
    query_vector=[0.1, 0.2, 0.3, ...],
    session_id="user123",
    limit=5
)
```

### API接口

**存储记忆**：
- `store_memory(session_id, content, vector, memory_type, metadata)`

**搜索记忆**：
- `search_memories(query_vector, session_id, memory_type, limit, score_threshold)`

**管理记忆**：
- `get_memory(memory_id)`
- `delete_memory(memory_id)`
- `get_session_memories(session_id)`
- `clear_session(session_id)`

**元数据管理**：
- `get_session_metadata(session_id)`

**统计信息**：
- `stats()`

## 与其他服务的关系

```
Memory Service
    ├── 依赖 KV Service（存储记忆数据）
    └── 依赖 VDB Service（向量搜索）
```

Memory服务通过服务代理机制调用KV和VDB服务，实现松耦合的微服务架构。

## 配置选项

```python
config = MemoryConfig(
    kv_service_name="kv_service",        # KV服务名称
    vdb_service_name="vdb_service",      # VDB服务名称  
    default_vector_dimension=384,        # 默认向量维度
    max_search_results=50               # 最大搜索结果数
)
```

## 为什么这样设计？

1. **避免重复造轮子**：原有的Memory服务功能复杂，但KV和VDB已有专门的服务
2. **职责清晰**：每个服务专注自己的核心功能
3. **易于维护**：简洁的代码结构，便于理解和维护
4. **灵活扩展**：可以轻松替换底层的KV或VDB实现
5. **分布式友好**：服务间通过代理通信，支持分布式部署
