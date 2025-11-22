# Memory Backend Configuration Guide

SAGE Gateway 支持多种记忆后端，您可以根据应用场景选择最适合的记忆架构。

## 支持的后端类型

### 1. Short-Term Memory (默认)

基于滑动窗口的短期记忆，适合简单对话场景。

**特点:**

- 轻量级，低延迟
- 固定窗口大小，自动淘汰旧对话
- 无需额外配置

**配置示例:**

```python
from sage.gateway.session.manager import SessionManager

manager = SessionManager(
    storage=storage,
    memory_backend="short_term",
    max_memory_dialogs=10  # 保留最近10轮对话
)
```

**适用场景:**

- 简单问答系统
- 对话历史不需要长期保存
- 性能优先的场景

______________________________________________________________________

### 2. Vector Database (VDB)

基于向量数据库的语义检索记忆，支持相似对话检索。

**特点:**

- 语义相似度检索
- 支持大规模对话历史
- 可配置嵌入模型

**配置示例:**

```python
manager = SessionManager(
    storage=storage,
    memory_backend="vdb",
    memory_config={
        "embedding_model": "text-embedding-3-small",  # OpenAI embedding
        "embedding_dim": 1536,
        "backend_type": "faiss",  # FAISS 向量索引
        "max_retrieve": 10  # 最多检索10条相关对话
    }
)
```

**适用场景:**

- 需要语义相似度搜索
- 大规模对话历史存储
- 智能客服、知识问答

______________________________________________________________________

### 3. Key-Value Store (KV)

基于键值对的快速检索记忆。

**特点:**

- 极快的查询速度
- 精确匹配检索
- 支持 BM25 等关键词检索

**配置示例:**

```python
manager = SessionManager(
    storage=storage,
    memory_backend="kv",
    memory_config={
        "default_index_type": "bm25s",  # BM25 索引
        "max_retrieve": 10
    }
)
```

**适用场景:**

- 需要精确关键词匹配
- 低延迟要求
- 结构化对话历史

______________________________________________________________________

### 4. Graph Memory

基于图结构的关系型记忆，支持对话关系推理。

**特点:**

- 存储对话之间的关系
- 支持图遍历和子图查询
- 适合复杂对话流程

**配置示例:**

```python
manager = SessionManager(
    storage=storage,
    memory_backend="graph",
    memory_config={
        "max_depth": 2,  # 最大遍历深度
        "max_retrieve": 10
    }
)
```

**适用场景:**

- 多轮复杂对话
- 需要推理对话关系
- 任务型对话系统

______________________________________________________________________

## 后端选择建议

| 场景       | 推荐后端   | 原因                 |
| ---------- | ---------- | -------------------- |
| 简单问答   | short_term | 低延迟，够用         |
| 智能客服   | vdb        | 语义搜索，找相似问题 |
| 知识库问答 | vdb        | 大规模历史，语义检索 |
| 精确查询   | kv         | 关键词匹配，速度快   |
| 任务型对话 | graph      | 对话流程，关系推理   |
| 混合场景   | vdb + kv   | 语义+精确结合        |

______________________________________________________________________

## 运行时配置

您也可以在运行时通过环境变量或配置文件指定：

```bash
# 环境变量
export SAGE_MEMORY_BACKEND=vdb
export SAGE_MEMORY_CONFIG='{"embedding_model": "text-embedding-3-small", "embedding_dim": 1536}'

# 启动服务
sage-gateway start
```

______________________________________________________________________

## API 差异

不同后端的存储和检索 API 是统一的，由 SessionManager 自动处理：

```python
# 存储对话（所有后端通用）
manager.store_dialog_to_memory(
    session_id="session-123",
    user_message="你好",
    assistant_message="您好！有什么可以帮您的吗？"
)

# 检索历史（所有后端通用）
history = manager.retrieve_memory_history(session_id="session-123")
```

______________________________________________________________________

## 性能对比

| 后端       | 写入延迟 | 查询延迟 | 内存占用 | 磁盘占用 |
| ---------- | -------- | -------- | -------- | -------- |
| short_term | ~1ms     | ~1ms     | 低       | 无       |
| vdb        | ~10ms    | ~20ms    | 中       | 中       |
| kv         | ~5ms     | ~5ms     | 低       | 低       |
| graph      | ~10ms    | ~15ms    | 中       | 中       |

*注：以上数据为参考值，实际性能取决于硬件和数据规模*

______________________________________________________________________

## 注意事项

1. **VDB 后端**: 需要配置嵌入模型 API（如 OpenAI），确保 `OPENAI_API_KEY` 已设置
1. **持久化**: VDB/KV/Graph 后端支持持久化到磁盘，数据存储在 `.sage/memory/` 目录
1. **清理**: 删除会话时会自动清理对应的记忆数据
1. **切换后端**: 切换后端后，旧数据不会自动迁移，需要手动处理

______________________________________________________________________

## 示例代码

完整示例请参考 `examples/tutorials/l6/memory_backend_demo.py`
