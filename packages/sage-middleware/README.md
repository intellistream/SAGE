# SAGE 微服务架构改造

## 📋 改造概述

本次改造将SAGE的集成式memory service重构为真正的服务化架构，符合您提出的要求：

1. ✅ **使用sage-kernel的BaseServiceTask** - 所有服务继承自`sage.runtime.service.base_service_task.BaseServiceTask`
2. ✅ **服务作为Task运行** - 服务本质上是特殊的Task，可以在DAG中作为节点运行
3. ✅ **移除服务启动脚本** - 不再有独立的服务启动器，服务由应用程序在构建DAG时初始化
4. ✅ **支持Ray分布式** - 服务可以作为Ray Actor运行，支持集群部署

## 🏗️ 新架构

```
用户应用
    ↓ 注册服务
SAGE Environment
    ↓ 创建DAG
Service Tasks (BaseServiceTask)
    ├── KVService (键值存储)
    ├── VDBService (向量数据库) 
    └── MemoryOrchestratorService (记忆编排)
        ↓ 队列通信
    其他Function Tasks
```

## 🔧 核心组件

### 1. KVService
- **文件**: `src/sage/service/kv/kv_service.py`
- **基类**: `BaseServiceTask`
- **后端**: 内存 或 Redis
- **方法**: `get()`, `put()`, `delete()`, `list_keys()`, `clear()`

### 2. VDBService  
- **文件**: `src/sage/service/vdb/vdb_service.py`
- **基类**: `BaseServiceTask`
- **后端**: ChromaDB
- **方法**: `add()`, `search()`, `get()`, `delete()`, `update()`

### 3. MemoryOrchestratorService
- **文件**: `src/sage/service/memory_orchestrator/memory_service.py`
- **基类**: `BaseServiceTask`
- **功能**: 协调KV和VDB服务，提供统一记忆管理
- **方法**: `store_memory()`, `search_memories()`, `get_memory()`

## 🚀 使用方式

### 第一步：注册服务

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.service import (
    create_kv_service_factory,
    create_vdb_service_factory,
    create_memory_service_factory
)

# 创建环境
env = LocalEnvironment("my_app", {})

# 注册服务
env.register_service("kv_service", KVService, create_kv_service_factory())
env.register_service("vdb_service", VDBService, create_vdb_service_factory()) 
env.register_service("memory_service", MemoryOrchestratorService, create_memory_service_factory())
```

### 第二步：在Function中使用

```python
from sage.core.function.base_function import BaseFunction

class MyProcessor(BaseFunction):
    def process(self, data):
        # 直接调用服务
        self.call_service["kv_service"].put("key1", data)
        result = self.call_service["memory_service"].store_memory(
            session_id="session_1",
            content=data['content'],
            vector=data['vector']
        )
        return result
```

### 第三步：构建DAG并运行

```python
# 创建数据流
stream = env.from_kafka_source(...)

# 应用处理函数
processed = stream.map(MyProcessor())

# 运行（服务自动启动）
env.execute()
```

## 📁 项目结构

```
packages/sage-middleware/
├── src/sage/service/
│   ├── __init__.py                     # 统一接口
│   ├── kv/kv_service.py               # KV服务任务
│   ├── vdb/vdb_service.py             # VDB服务任务
│   ├── memory_orchestrator/memory_service.py  # Memory编排服务
│   └── memory/                        # 旧版服务(兼容)
├── examples/
│   ├── dag_microservices_demo.py      # 完整使用演示
│   └── run_demo.sh                    # 快速启动脚本
├── MICROSERVICES_GUIDE.md             # 详细使用指南
└── README.md                          # 本文件
```

## 🎯 关键特性

### 1. 真正的服务化
- 每个服务都是独立的BaseServiceTask
- 服务可以单独运行、测试和扩展
- 支持不同的技术栈和存储后端

### 2. DAG集成
- 服务作为Task节点在DAG中运行
- 与其他数据处理Task无缝集成
- 统一的生命周期管理

### 3. 队列通信
- 使用SAGE的高性能队列机制
- 支持同步和异步调用
- 自动请求/响应匹配

### 4. 分布式支持
- 服务可以作为Ray Actor运行
- 支持跨节点服务调用
- 自动负载均衡和故障恢复

### 5. 应用控制
- 应用程序控制服务的启动和配置
- 不需要外部服务管理器
- 灵活的服务组合和依赖关系

## 📊 性能优势

1. **高效通信**: 队列机制比HTTP调用更高效
2. **内存优化**: 服务和数据处理共享内存空间
3. **批处理**: 支持批量服务调用
4. **并发处理**: 服务可以并发处理多个请求

## 🔄 迁移路径

### 从HTTP微服务迁移
- 移除HTTP客户端代码
- 使用`self.call_service[service_name].method()`替代HTTP调用
- 服务注册到SAGE环境而不是独立启动

### 从集成式服务迁移  
- 将大型服务拆分为独立的Service Task
- 使用服务调用替代直接方法调用
- 保持相同的业务逻辑和API

## 🧪 运行演示

```bash
# 快速启动
cd packages/sage-middleware
./examples/run_demo.sh

# 或直接运行Python
python examples/dag_microservices_demo.py
```

## 📚 参考文档

- **微服务指南**: [MICROSERVICES_GUIDE.md](MICROSERVICES_GUIDE.md)
- **SAGE文档**: [packages/sage-kernel/src/sage/runtime/service/README.md](../sage-kernel/src/sage/runtime/service/README.md)
- **BaseServiceTask**: [packages/sage-kernel/src/sage/runtime/service/base_service_task.py](../sage-kernel/src/sage/runtime/service/base_service_task.py)

---

## ✅ 改造成果

这次改造成功实现了您要求的所有目标：

1. ✅ **继承sage-kernel的BaseServiceTask** - 所有服务都继承正确的基类
2. ✅ **服务即Task** - 服务本质上是在DAG中运行的特殊Task
3. ✅ **应用控制** - 用户在构建DAG时初始化服务，而非独立启动脚本
4. ✅ **支持Ray** - 服务可以作为Ray Actor分布式运行
5. ✅ **队列通信** - 使用SAGE统一的高性能队列机制
6. ✅ **向后兼容** - 保留原有API兼容性

现在SAGE拥有了真正的服务化架构，每个服务都是独立的Task，可以灵活组合、分布式部署，完全符合现代微服务架构的设计理念！
