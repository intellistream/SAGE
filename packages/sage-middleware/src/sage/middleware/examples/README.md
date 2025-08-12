# SAGE Middleware Examples Guide

本目录包含了展示如何正确使用SAGE微服务API的各种示例。

## 📁 目录结构

```
examples/
├── api_usage_tutorial.py          # 🎓 完整的API使用教程 (推荐起点)
├── microservices_integration_demo.py  # 🏢 企业级集成示例
├── microservices_registration_demo.py # 📋 服务注册和配置示例
└── services/                       # 各服务的专门示例
    ├── kv/examples/kv_demo.py          # 📦 KV服务API使用
    ├── vdb/examples/vdb_demo.py        # 🗂️ VDB服务API使用
    ├── memory/examples/memory_demo.py  # 🧠 Memory服务API使用
    └── graph/examples/graph_demo.py    # 🕸️ Graph服务API使用
```

## 🎯 推荐学习路径

### 1. 新手入门
**从这里开始！** → `api_usage_tutorial.py`
- 完整的API接口介绍
- 标准使用模式
- 错误处理最佳实践
- 服务组合使用示例

### 2. 单个服务深入
选择你感兴趣的服务深入学习：
- **KV服务**: `services/kv/examples/kv_demo.py`
- **VDB服务**: `services/vdb/examples/vdb_demo.py` 
- **Memory服务**: `services/memory/examples/memory_demo.py`
- **Graph服务**: `services/graph/examples/graph_demo.py`

### 3. 企业级应用
完成基础学习后，查看实际应用场景：
- **集成示例**: `microservices_integration_demo.py`
- **注册配置**: `microservices_registration_demo.py`

## 🛠️ API使用核心概念

### 服务注册和获取
```python
# 1. 注册服务
from sage.middleware.services import create_kv_service_factory
from sage.api.local_environment import LocalEnvironment

env = LocalEnvironment("my_app")
kv_factory = create_kv_service_factory("my_kv", backend_type="memory")
env.register_service_factory("my_kv", kv_factory)

# 2. 获取服务代理 (在实际应用中)
# env.submit()  # 启动环境
# kv_service = env.get_service_proxy("my_kv")  # 获取服务代理

# 3. 使用API
# result = kv_service.put("key", "value")
# data = kv_service.get("key")
```

### API接口层次

#### 🔹 基础服务 (直接存储)
- **KVService**: 键值存储
  - `put()`, `get()`, `delete()`, `list_keys()`
- **VDBService**: 向量数据库
  - `add_vectors()`, `search()`, `get_vector()`
- **GraphService**: 图数据库
  - `add_node()`, `add_edge()`, `find_path()`

#### 🔹 编排服务 (高级功能)
- **MemoryService**: 记忆管理 (调用上述基础服务)
  - `store_memory()`, `retrieve_memories()`, `search_memories()`

### 正确的调用模式

✅ **推荐方式: 通过服务代理调用API**
```python
# 获取服务代理
memory_service = env.get_service_proxy("memory_service")

# 使用API方法
memory_id = memory_service.store_memory(
    content="用户询问了关于Python的问题",
    vector=[0.1, 0.2, ...],
    session_id="session_123"
)
```

❌ **避免: 直接实例化服务类**
```python
# 不推荐 - 绕过了服务管理机制
memory_service = MemoryService(...)  # 这样使用是错误的
```

## 🚀 快速开始

1. **运行完整教程**:
   ```bash
   cd packages/sage-middleware
   python src/sage/service/examples/api_usage_tutorial.py
   ```

2. **尝试单个服务**:
   ```bash
   python src/sage/service/services/kv/examples/kv_demo.py
   ```

3. **查看集成示例**:
   ```bash
   python src/sage/service/examples/microservices_integration_demo.py
   ```

## 🎨 使用场景示例

### 智能问答系统
```python
class IntelligentQA:
    def __init__(self, env):
        self.memory = env.get_service_proxy("memory_service")
        self.kv = env.get_service_proxy("kv_service")
    
    async def answer_question(self, user_id: str, question: str):
        # 1. 获取用户上下文
        context = self.kv.get(f"user:{user_id}:context")
        
        # 2. 检索相关记忆
        question_vector = embed_text(question)
        related = self.memory.retrieve_memories(
            query_vector=question_vector,
            session_id=context["session_id"],
            top_k=5
        )
        
        # 3. 生成回答并存储记忆
        answer = generate_answer(question, related)
        self.memory.store_memory(
            content=f"Q: {question}\\nA: {answer}",
            vector=question_vector,
            session_id=context["session_id"]
        )
        
        return answer
```

### 文档管理系统
```python
class DocumentManager:
    def __init__(self, env):
        self.vdb = env.get_service_proxy("vdb_service")
        self.kv = env.get_service_proxy("kv_service")
    
    def index_document(self, doc_id: str, content: str):
        # 向量索引
        vector = embed_text(content)
        self.vdb.add_vectors([{
            "id": doc_id,
            "vector": vector,
            "text": content[:500],  # 预览
            "metadata": {"full_content_key": f"doc:{doc_id}"}
        }])
        
        # 全文存储
        self.kv.put(f"doc:{doc_id}", {
            "content": content,
            "indexed_at": time.time(),
            "status": "indexed"
        })
```

## 🔧 高级主题

### 错误处理
所有示例都展示了正确的错误处理模式，包括：
- 服务不可用处理
- 超时处理  
- 数据一致性保证
- 重试策略

### 性能优化
- 批量操作最佳实践
- 索引管理策略
- 缓存使用模式
- 内存管理

### 监控和度量
- 服务健康检查
- 性能指标收集
- 日志和追踪

## 📚 下一步

1. 完成所有examples的学习
2. 查看各服务的API文档
3. 在你的项目中集成SAGE服务
4. 参与SAGE社区讨论

---

💡 **提示**: 所有examples都可以独立运行，但某些功能需要启动完整的服务环境才能真正执行API调用。
