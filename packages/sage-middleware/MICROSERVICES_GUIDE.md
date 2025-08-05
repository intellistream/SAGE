# SAGE 微服务架构改造完成指南

## 🎯 改造概述

根据您的需求，已将SAGE的集成式memory service成功改造为真正的服务化架构：
- **原始架构**: Memory Service集成了KV、VDB功能  
- **新架构**: KV Service、VDB Service、Memory Orchestrator作为独立的Service Tasks在DAG中运行
- **核心原理**: 服务本质上是特殊的Task，可以是本地任务或Ray分布式任务

## 🏗️ 新架构组件

### 1. 服务任务 (Service Tasks)

| 服务名称 | 基类 | 功能 | 方法 |
|---------|------|------|------|
| **KVService** | BaseServiceTask | 键值存储 | `get()`, `put()`, `delete()`, `list_keys()` |
| **VDBService** | BaseServiceTask | 向量数据库 | `add()`, `search()`, `get()`, `delete()` |
| **MemoryOrchestratorService** | BaseServiceTask | 记忆编排 | `store_memory()`, `search_memories()`, `get_memory()` |

### 2. 架构特点

- **继承BaseServiceTask**: 所有服务都继承sage-kernel的BaseServiceTask
- **DAG集成**: 服务作为Task节点在DAG中运行
- **队列通信**: 服务间通过SAGE的队列机制通信
- **应用控制**: 应用程序在构建DAG时初始化服务
- **Ray支持**: 服务可以作为Ray Actor运行，支持分布式

## 🚀 在应用中使用服务

### 第一步: 注册服务到环境

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.service import (
    create_kv_service_factory,
    create_vdb_service_factory,
    create_memory_service_factory
)

# 创建环境
env = LocalEnvironment("my_app", {})

# 注册KV服务
kv_factory = create_kv_service_factory(
    service_name="kv_service",
    backend_type="memory",  # 或 "redis"
    max_size=10000
)
env.register_service("kv_service", kv_factory.service_class, kv_factory)

# 注册VDB服务
vdb_factory = create_vdb_service_factory(
    service_name="vdb_service", 
    collection_name="my_vectors",
    dimension=384
)
env.register_service("vdb_service", vdb_factory.service_class, vdb_factory)

# 注册Memory编排服务
memory_factory = create_memory_service_factory(
    service_name="memory_service",
    kv_service_name="kv_service",
    vdb_service_name="vdb_service"
)
env.register_service("memory_service", memory_factory.service_class, memory_factory)
```

### 第二步: 在Function中调用服务

```python
from sage.core.function.base_function import BaseFunction

class MyProcessor(BaseFunction):
    """我的处理函数"""
    
    def process(self, data):
        # 调用KV服务
        kv_result = self.call_service["kv_service"].put("key1", {"data": "value"})
        stored_data = self.call_service["kv_service"].get("key1")
        
        # 调用VDB服务
        vectors = [{
            "id": "doc1",
            "vector": [0.1] * 384,
            "metadata": {"type": "document"}
        }]
        self.call_service["vdb_service"].add(vectors)
        
        # 搜索相似向量
        search_results = self.call_service["vdb_service"].search(
            query_vector=[0.1] * 384,
            n_results=5
        )
        
        # 调用Memory服务
        memory_id = self.call_service["memory_service"].store_memory(
            session_id="session_123",
            content="用户的对话内容",
            vector=[0.1] * 384,
            memory_type="conversation"
        )
        
        return {"processed": True, "memory_id": memory_id}
```

### 第三步: 构建和运行DAG

```python
# 创建数据流
stream = env.from_kafka_source(...)

# 应用处理函数（自动访问服务）
processed_stream = stream.map(MyProcessor())

# 输出结果
processed_stream.sink(...)

# 运行（服务会自动启动和管理）
env.execute()
```

## 🔧 服务配置选项

### KV Service配置

```python
kv_factory = create_kv_service_factory(
    service_name="kv_service",
    backend_type="memory",        # "memory" 或 "redis"
    redis_url="redis://localhost:6379",  # Redis URL (当使用Redis时)
    max_size=10000,              # 最大存储条目数 (内存后端)
    ttl_seconds=3600             # 数据过期时间 (秒)
)
```

### VDB Service配置

```python
vdb_factory = create_vdb_service_factory(
    service_name="vdb_service",
    collection_name="my_collection",    # 集合名称
    dimension=384,                      # 向量维度
    persist_directory="./vector_db",    # 持久化目录
    distance_metric="cosine"            # 距离度量 ("cosine", "euclidean", "manhattan")
)
```

### Memory Service配置

```python
memory_factory = create_memory_service_factory(
    service_name="memory_service",
    kv_service_name="kv_service",       # 依赖的KV服务名
    vdb_service_name="vdb_service",     # 依赖的VDB服务名
    default_vector_dimension=384,       # 默认向量维度
    max_search_results=50               # 最大搜索结果数
)
```

## 🚦 分布式部署 (Ray)

服务可以作为Ray Actor运行，支持分布式部署：

```python
# 创建远程环境 (Ray集群)
env = LocalEnvironment("distributed_app", {}, platform="remote")

# 注册服务 (会自动创建为Ray Actor)
env.register_service("kv_service", KVService, kv_factory)
env.register_service("vdb_service", VDBService, vdb_factory)
env.register_service("memory_service", MemoryOrchestratorService, memory_factory)

# 其余代码相同，但服务会在Ray集群中运行
```

## 🔄 迁移指南

### 从旧Memory Service迁移

**旧代码**:
```python
from sage.service.memory import MemoryService

memory = MemoryService()
await memory.store(session_id, content, vector)
```

**新代码**:
```python
# 在应用初始化时注册服务
env.register_service("memory_service", MemoryOrchestratorService, memory_factory)

# 在Function中使用
class MyFunction(BaseFunction):
    def process(self, data):
        memory_id = self.call_service["memory_service"].store_memory(
            session_id=data['session_id'],
            content=data['content'],
            vector=data['vector']
        )
        return memory_id
```

### 保持兼容性

旧的MemoryService仍然可用：

```python
from sage.service import LegacyMemoryService

# 旧的MemoryService仍然可用
memory = LegacyMemoryService()
```

## 📁 新文件结构

```
packages/sage-middleware/src/sage/service/
├── __init__.py                           # 统一导入接口
├── kv/
│   └── kv_service.py                    # KV服务任务
├── vdb/
│   └── vdb_service.py                   # VDB服务任务
├── memory_orchestrator/
│   └── memory_service.py                # Memory编排服务任务
└── memory/                              # 旧版Memory服务(兼容性)
    ├── memory_service.py
    └── memory_manager.py
```

## � 架构优势

1. **真正的服务化**: 每个服务都是独立的Task，可以单独运行和扩展
2. **DAG集成**: 服务作为DAG节点，与其他Task无缝集成  
3. **分布式支持**: 服务可以作为Ray Actor运行，支持集群部署
4. **队列通信**: 使用SAGE统一的队列机制，性能优异
5. **应用控制**: 应用程序控制服务生命周期，不需要外部服务管理
6. **向后兼容**: 保留原有API的兼容性

## 🔍 核心概念

### Service Task vs 普通Task

- **普通Task**: 处理数据流中的记录，有输入输出
- **Service Task**: 提供服务接口，响应其他Task的调用请求
- **统一基类**: 都继承自BaseServiceTask，使用相同的队列机制

### 服务调用机制

```python
# 在Function中
result = self.call_service["service_name"].method_name(args)

# 实际发生的事情:
# 1. 请求通过队列发送到服务Task
# 2. 服务Task处理请求并返回结果  
# 3. 结果通过队列返回给调用者
# 4. 支持同步和异步调用
```

### 依赖管理

```python
# Memory服务依赖KV和VDB服务
# 在Memory服务中:
def _get_kv_service(self):
    return self.ctx.service_manager.get_service_proxy(self.config.kv_service_name)

def _get_vdb_service(self):
    return self.ctx.service_manager.get_service_proxy(self.config.vdb_service_name)
```

## 📋 运行示例

```bash
# 运行完整演示
cd /home/shuhao/SAGE/packages/sage-middleware
python examples/dag_microservices_demo.py
```

## 🆘 故障排除

### 常见问题

1. **服务未注册**: 确保在创建数据流之前注册所有服务
2. **依赖缺失**: 确保依赖的服务已经注册并正确命名
3. **配置错误**: 检查服务工厂的配置参数
4. **队列问题**: 确保ServiceContext正确配置

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查服务统计
stats = self.call_service["kv_service"].stats()
print(f"KV Service stats: {stats}")
```

---

## ✅ 改造总结

✅ **完成项**:
- 🏗️ 基于BaseServiceTask的服务架构
- 🔧 KVService (支持内存和Redis后端)
- 📊 VDBService (基于ChromaDB)
- 🧠 MemoryOrchestratorService (统一记忆接口)
- 🎯 DAG集成 (服务作为Task节点)
- 📋 服务间通信 (队列机制)
- 🚀 Ray分布式支持
- 🧪 完整的演示和测试代码
- 📚 详细的使用文档和迁移指南

您的memory service现在已经成功改造为**真正的服务化架构**！每个服务都是独立的Task，在DAG中运行，服务间通过队列通信，完全符合您的需求。服务本质上就是Task，可以是本地任务或Ray任务，由应用程序在构建DAG时初始化。
