# SAGE Middleware Structure

本文档描述了 sage-middleware 的重构后结构。

## 目录结构

```
src/sage/service/
├── api/                    # API接口定义
│   ├── __init__.py
│   ├── kv_api.py          # KV服务API接口
│   ├── vdb_api.py         # VDB服务API接口  
│   ├── memory_api.py      # Memory服务API接口
│   └── graph_api.py       # Graph服务API接口
├── examples/              # 示例代码
│   ├── dag_microservices_demo.py
│   ├── microservices_demo.py
│   ├── microservices_integration_demo.py
│   └── microservices_registration_demo.py
├── services/              # 具体服务实现
│   ├── kv/               # 键值存储服务
│   │   ├── __init__.py
│   │   ├── kv_service.py
│   │   ├── examples/
│   │   └── search_engine/
│   ├── vdb/              # 向量数据库服务
│   │   ├── __init__.py
│   │   ├── vdb_service.py
│   │   ├── examples/
│   │   └── search_engine/
│   ├── memory/           # 记忆编排服务
│   │   ├── __init__.py
│   │   ├── memory_service.py
│   │   ├── examples/
│   │   ├── memory_collection/
│   │   └── utils/
│   └── graph/           # 图数据库服务
│       ├── __init__.py
│       ├── graph_service.py
│       ├── examples/
│       └── search_engine/
└── utils/                # 工具类
    ├── __init__.py
    ├── embedding/        # 嵌入模型工具
    └── llm-clients/      # LLM客户端工具
```

## 架构设计

### 核心理念
- **服务解耦**: 每个服务都是独立的微服务，通过BaseServiceTask实现
- **统一API**: 通过api/目录定义统一的服务接口  
- **编排服务**: Memory服务作为高级编排服务，调用其他基础服务

### 服务层次
1. **基础服务**: KV、VDB、Graph - 提供基础存储能力
2. **编排服务**: Memory - 协调基础服务，提供高级功能
3. **API层**: 统一的接口定义
4. **工具层**: 通用工具和客户端

### 导入方式

```python
# 导入服务类
from sage.middleware.services import KVService, VDBService, MemoryService, GraphService

# 导入工厂函数
from sage.middleware.services import (
    create_kv_service_factory,
    create_vdb_service_factory, 
    create_memory_service_factory,
    create_graph_service_factory
)

# 导入API接口
from sage.middleware.services.api import KVServiceAPI, VDBServiceAPI, MemoryServiceAPI, GraphServiceAPI
```

## 重构要点

1. **移除storage_engine**: 存储逻辑直接在各服务内部实现
2. **统一memory_service**: 合并memory_orchestrator_service到memory_service
3. **清理重复文件**: 删除多余的工厂函数和旧版本文件
4. **统一API设计**: 为每个服务定义清晰的API接口
5. **结构标准化**: 每个服务都包含service.py、__init__.py、examples/等标准结构
