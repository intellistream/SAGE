# MemoryService 使用示例

这个示例展示了如何在SAGE中设置和使用MemoryService进行高级记忆管理。

## 概述

MemoryService 是 SAGE middleware 中的高级编排服务，它协调 KV、VDB 和 Graph 微服务，提供统一的记忆管理接口。这个例子演示了：

- 如何使用MemoryService进行记忆管理
- 记忆的存储、检索和语义搜索
- 不同记忆类型的处理
- 上下文生成和会话管理

## 功能特性

- ✅ **记忆存储和检索**：存储对话和语义记忆，支持向量相似性搜索
- ✅ **会话管理**：支持多会话隔离，每个会话有独立的记忆空间
- ✅ **记忆分类**：支持 conversation（对话记忆）、knowledge（知识记忆）、working（工作记忆）
- ✅ **语义搜索**：基于向量相似度的智能记忆检索
- ✅ **上下文生成**：自动生成相关对话上下文

## 运行要求

### 依赖包

```bash
pip install pyyaml numpy
```

## 快速开始

### 直接运行示例

这个示例现在使用 `MockMemoryService` 进行演示，可以直接运行而不需要完整的SAGE服务基础设施：

```bash
cd examples/memory
python memory_service_demo.py
```

### 查看演示结果

示例会执行以下步骤：

1. **记忆存储阶段**：
   - 存储示例对话数据到模拟记忆系统
   - 自动分类为对话记忆和知识记忆
   - 演示不同记忆类型的存储

2. **记忆检索阶段**：
   - 基于查询进行语义搜索
   - 展示相似度排序的结果
   - 显示会话记忆统计

## 示例输出

```
🚀 MemoryService 使用示例
============================================================
📋 初始化 MemoryService...
✅ MockMemoryService 初始化成功
   💡 使用模拟服务展示MemoryService功能

🔄 阶段1: 存储对话记忆
   处理对话 1/5...
     ✅ 用户消息已存储: mem_0
     ✅ AI回复已存储: mem_1
     ✅ 语义记忆已存储: mem_2

🔄 阶段2: 记忆检索演示
   🔍 查询: Python编程学习
     📚 找到 3 条相关记忆:
       1. [conversation] Python有以下基本数据类型：...
       2. [conversation] 你好，我想学习Python编程，应该从哪里开始？...
       3. [knowledge] 用户对编程感兴趣：...
```

## 完整SAGE环境运行

如果要在完整的SAGE环境中运行MemoryService，需要：

### 1. 启动底层服务

MemoryService 需要以下底层服务：

1. **KV Service**：键值存储服务
2. **VDB Service**：向量数据库服务
3. **Graph Service**：图数据库服务（可选，用于知识图谱）

### 2. 配置服务

使用 `examples/config/config_memory_service_demo.yaml` 配置文件：

```yaml
memory_service:
  kv_service_name: "kv_service"
  vdb_service_name: "vdb_service"
  graph_service_name: "graph_service"
  default_vector_dimension: 384
  max_search_results: 10
  enable_caching: true
  enable_knowledge_graph: true
```

### 3. 修改代码

将示例中的 `MockMemoryService()` 替换为真实的 `MemoryService()`：

```python
from sage.middleware.services.memory.memory_service import MemoryService

memory_service = MemoryService()
```

## 代码结构

### 主要组件

- `MockMemoryService`: 模拟MemoryService，用于演示功能
- `mock_embedding()`: 模拟的文本嵌入函数
- `create_sample_conversations()`: 生成示例对话数据

### 核心功能演示

1. **记忆存储**：展示如何存储不同类型的记忆
2. **语义检索**：演示基于向量相似度的搜索
3. **会话管理**：展示会话级别的记忆隔离
4. **上下文生成**：演示如何生成相关上下文

## API使用示例

### 存储记忆

```python
memory_id = memory_service.store_memory(
    content="用户的问题内容",
    vector=embedding_vector,
    session_id="session_123",
    memory_type="conversation",
    metadata={
        "speaker": "user",
        "topic": "programming",
        "timestamp": time.time()
    }
)
```

### 检索记忆

```python
relevant_memories = memory_service.search_memories(
    query_vector=query_embedding,
    session_id="session_123",
    limit=5
)
```

### 获取会话记忆

```python
session_memories = memory_service.get_session_memories("session_123")
```

## 实际应用场景

### 智能对话系统
- 维护对话历史和用户偏好
- 提供上下文相关的回答

### 知识管理系统
- 存储和检索文档片段
- 支持语义搜索和问答

### 推荐系统
- 记住用户行为和偏好
- 基于历史数据进行个性化推荐

## 扩展和定制

### 使用真实的嵌入模型

替换 `mock_embedding()` 函数：

```python
def real_embedding(text: str) -> List[float]:
    # 使用真实的embedding模型，如sentence-transformers
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(text).tolist()
```

### 添加记忆过期机制

```python
def store_memory_with_expiry(memory_service, content, vector, session_id, ttl_seconds=3600):
    """存储带过期时间的记忆"""
    metadata = {
        "expiry": time.time() + ttl_seconds,
        "created_at": time.time()
    }
    return memory_service.store_memory(content, vector, session_id, "working", metadata)
```

## 故障排除

### 常见问题

1. **依赖缺失**：确保安装了 `pyyaml` 和 `numpy`
2. **编码问题**：确保Python文件使用UTF-8编码
3. **路径问题**：确保配置文件路径正确

### 调试模式

启用详细输出：

```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" memory_service_demo.py
```

## 相关链接

- [SAGE 文档](https://github.com/intellistream/SAGE)
- [MemoryService 源码](../packages/sage-middleware/sage/middleware/services/memory/)
- [其他记忆相关示例](rag_memory_pipeline.py)