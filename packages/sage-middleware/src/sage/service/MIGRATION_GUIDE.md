# SAGE 服务化架构迁移指南

## 概述

SAGE 已完成从单体式 memory service 到微服务架构的重构。新架构将原本耦合的功能拆分为独立的微服务，并由应用程序负责启动和管理这些服务。

## 新架构组件

### 🏗️ 架构层次

```
应用层 (Application Layer)
├── ServiceLauncher - 服务启动器
├── ServiceRegistry - 服务注册表  
└── Application - 业务应用

微服务层 (Microservice Layer)
├── KV Service - 键值存储服务
├── VDB Service - 向量数据库服务
└── Memory Service - 内存编排服务

基础设施层 (Infrastructure Layer)
├── HTTP APIs - RESTful接口
├── Health Monitoring - 健康监控
└── Service Discovery - 服务发现
```

### 🔧 核心服务

1. **KV Service** (`port 8001`)
   - 提供键值存储功能
   - 支持内存和Redis后端
   - REST API接口

2. **VDB Service** (`port 8002`)
   - 提供向量存储和检索
   - 基于ChromaDB
   - 支持相似度搜索

3. **Memory Service** (`port 8000`)
   - 编排KV和VDB服务
   - 提供统一的Memory API
   - 自动服务发现

## 快速开始

### 🚀 启动服务

```bash
# 方式1: 使用启动脚本（推荐）
cd packages/sage-middleware/src/sage/service/
python start_services.py

# 方式2: 使用演示应用
python examples/microservices_demo.py

# 方式3: 自定义配置
python start_services.py --config standard --kv-backend redis --redis-url redis://localhost:6379
```

### 📋 可用配置

```bash
# 标准配置（KV + VDB + Memory）
python start_services.py --config standard

# 最小配置（仅Memory）
python start_services.py --config minimal

# 仅KV服务
python start_services.py --config kv-only

# 仅VDB服务
python start_services.py --config vdb-only
```

## 应用程序集成

### 🔌 在Python应用中使用

```python
import asyncio
from sage.service.launcher.service_launcher import ServiceLauncher

async def my_application():
    # 创建服务启动器
    launcher = ServiceLauncher()
    
    # 添加需要的服务
    launcher.add_kv_service(port=8001, backend_type="memory")
    launcher.add_vdb_service(port=8002, collection_name="my_vectors")
    launcher.add_memory_service(port=8000)
    
    try:
        # 启动所有服务
        await launcher.start_all_services()
        
        # 你的业务逻辑
        await run_my_business_logic()
        
        # 保持服务运行
        await launcher.wait_for_shutdown()
        
    finally:
        # 清理资源
        await launcher.shutdown()

async def run_my_business_logic():
    import httpx
    
    async with httpx.AsyncClient() as client:
        # 存储数据
        response = await client.post(
            "http://localhost:8000/memory",
            json={
                "key": "my_data",
                "data": {"content": "Hello World"},
                "vector": [0.1, 0.2, 0.3]  # 可选的向量
            }
        )
        
        # 检索数据
        response = await client.get("http://localhost:8000/memory/my_data")
        data = response.json()
        print(f"Retrieved: {data}")

if __name__ == "__main__":
    asyncio.run(my_application())
```

### 🌐 HTTP API 使用

#### Memory Service API (http://localhost:8000)

```bash
# 存储数据
curl -X POST http://localhost:8000/memory \
  -H "Content-Type: application/json" \
  -d '{
    "key": "doc1",
    "data": {"title": "My Document"},
    "vector": [0.1, 0.2, 0.3],
    "metadata": {"category": "test"}
  }'

# 检索数据
curl http://localhost:8000/memory/doc1

# 向量搜索
curl -X POST http://localhost:8000/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3],
    "top_k": 5,
    "include_data": true
  }'

# 健康检查
curl http://localhost:8000/health

# 依赖服务状态
curl http://localhost:8000/dependencies
```

#### KV Service API (http://localhost:8001)

```bash
# 设置键值
curl -X POST http://localhost:8001/kv \
  -H "Content-Type: application/json" \
  -d '{"key": "test", "value": "hello", "ttl": 3600}'

# 获取值
curl http://localhost:8001/kv/test

# 删除键
curl -X DELETE http://localhost:8001/kv/test

# 列出键
curl "http://localhost:8001/kv?pattern=*"
```

#### VDB Service API (http://localhost:8002)

```bash
# 添加向量
curl -X POST http://localhost:8002/vectors \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [{
      "id": "vec1",
      "vector": [0.1, 0.2, 0.3],
      "metadata": {"type": "test"}
    }]
  }'

# 向量搜索
curl -X POST http://localhost:8002/vectors/query \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3],
    "top_k": 10
  }'

# 获取向量
curl http://localhost:8002/vectors/vec1
```

## 迁移现有代码

### 🔄 从旧版Memory Service迁移

#### 旧代码（单体式）：
```python
from sage.service.memory.memory_service import MemoryService

# 旧方式
memory_service = MemoryService()
result = memory_service.create_collection("my_collection", "VDB")
memory_service.insert_data("my_collection", "Hello", {"type": "text"})
```

#### 新代码（微服务）：
```python
import httpx
from sage.service.launcher.service_launcher import ServiceLauncher

# 新方式：启动服务
launcher = ServiceLauncher()
await launcher.start_all_services()

# 使用HTTP API
async with httpx.AsyncClient() as client:
    await client.post(
        "http://localhost:8000/memory",
        json={
            "key": "my_key",
            "data": {"content": "Hello"},
            "metadata": {"type": "text"}
        }
    )
```

### 🔧 在SAGE流水线中使用

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.map_function import MapFunction
import httpx

class MemoryServiceFunction(MapFunction):
    def __init__(self, memory_url="http://localhost:8000", **kwargs):
        super().__init__(**kwargs)
        self.memory_url = memory_url
        self.client = httpx.AsyncClient()
    
    async def execute(self, data):
        # 存储到memory service
        response = await self.client.post(
            f"{self.memory_url}/memory",
            json={
                "key": f"data_{data.get('id')}",
                "data": data,
                "vector": data.get("embedding")
            }
        )
        return data

# 在环境中注册memory服务启动
async def setup_pipeline():
    # 启动微服务
    launcher = ServiceLauncher()
    await launcher.start_all_services()
    
    # 创建流水线
    env = LocalEnvironment()
    stream = env.from_source(DataSource).map(MemoryServiceFunction)
    
    env.submit()
```

## 服务配置

### 🔧 环境变量

```bash
# KV Service配置
SAGE_KV_BACKEND=redis
SAGE_REDIS_URL=redis://localhost:6379

# VDB Service配置  
SAGE_VDB_COLLECTION=my_vectors
SAGE_VDB_PERSIST_DIR=./vector_storage

# Memory Service配置
SAGE_MEMORY_KV_URL=http://localhost:8001
SAGE_MEMORY_VDB_URL=http://localhost:8002
```

### 📋 配置文件（可选）

```yaml
# services_config.yaml
services:
  kv_service:
    host: "localhost"
    port: 8001
    backend_type: "redis"
    redis_url: "redis://localhost:6379"
  
  vdb_service:
    host: "localhost"
    port: 8002
    collection_name: "sage_vectors"
    persist_directory: "./vector_storage"
  
  memory_service:
    host: "localhost"
    port: 8000
    dependencies: ["kv_service", "vdb_service"]
```

## 监控和运维

### 📊 健康检查

```bash
# 检查所有服务状态
curl http://localhost:8000/health
curl http://localhost:8001/health  
curl http://localhost:8002/health

# 检查服务依赖
curl http://localhost:8000/dependencies
```

### 📈 服务指标

```bash
# 获取服务指标
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics
curl http://localhost:8002/metrics
```

### 🔍 故障排查

1. **服务启动失败**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :8000
   
   # 查看服务日志
   python start_services.py --config standard
   ```

2. **服务间通信失败**
   ```bash
   # 测试服务连通性
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   ```

3. **依赖服务不可用**
   ```bash
   # 检查依赖状态
   curl http://localhost:8000/dependencies
   ```

## 最佳实践

### 🏗️ 开发环境

1. **本地开发**
   ```bash
   # 使用内存后端，快速启动
   python start_services.py --config standard --kv-backend memory
   ```

2. **集成测试**
   ```bash
   # 使用持久化存储
   python start_services.py --persist-dir ./test_storage
   ```

### 🚀 生产环境

1. **使用Redis**
   ```bash
   python start_services.py --kv-backend redis --redis-url redis://prod-redis:6379
   ```

2. **持久化向量存储**
   ```bash
   python start_services.py --persist-dir /data/vector_storage
   ```

3. **容器化部署**
   ```dockerfile
   FROM python:3.11-slim
   COPY . /app
   WORKDIR /app
   RUN pip install -r requirements.txt
   CMD ["python", "start_services.py", "--config", "standard"]
   ```

### 🔧 性能优化

1. **服务配置调优**
   - 根据负载调整服务端口和实例数
   - 使用Redis集群提高KV性能
   - 配置向量索引参数优化搜索速度

2. **监控和告警**
   - 定期检查服务健康状态
   - 监控响应时间和错误率
   - 设置服务降级策略

## 常见问题

### ❓ FAQ

**Q: 如何在现有SAGE应用中集成新的微服务架构？**

A: 在应用启动时先启动微服务，然后使用HTTP API调用服务功能。参考上面的迁移示例。

**Q: 服务启动顺序有要求吗？**

A: ServiceLauncher会自动计算依赖关系和启动顺序。Memory服务依赖KV和VDB服务，会最后启动。

**Q: 可以只使用部分服务吗？**

A: 可以。使用`--config`参数选择需要的服务组合，如`kv-only`或`vdb-only`。

**Q: 如何扩展到分布式部署？**

A: 每个服务都可以独立部署到不同节点。通过环境变量或配置文件指定服务地址。

**Q: 数据持久化如何保证？**

A: KV使用Redis持久化，VDB使用ChromaDB的持久化存储。通过`--persist-dir`指定存储路径。

### 🆘 支持

遇到问题请：
1. 查看服务日志和错误信息
2. 检查端口占用和网络连通性
3. 验证依赖服务状态
4. 参考本文档的故障排查部分

---

## 总结

新的微服务架构提供了：
- ✅ 更好的服务解耦和独立性
- ✅ 更灵活的部署和扩展方式  
- ✅ 更清晰的服务边界和职责
- ✅ 更强的故障隔离能力
- ✅ 应用程序控制的服务生命周期

通过本指南，你可以顺利完成从单体式到微服务架构的迁移，并享受微服务带来的各种优势。
