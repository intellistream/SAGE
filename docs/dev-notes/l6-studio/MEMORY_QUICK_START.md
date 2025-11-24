# SAGE Memory 管理快速使用指南

## 🚀 快速开始

### 1. 启动 SAGE Studio

```bash
# 启动 Studio（开发模式，自动启动 Gateway）
sage studio start

# 或指定端口
sage studio start --port 5173

# 或使用生产模式
sage studio start --prod

# 如果只想启动 Gateway
python -m sage.gateway.server
```

### 2. 访问记忆管理界面

1. 打开浏览器访问 `http://localhost:5173`
2. 点击右上角的 **设置** 按钮（⚙️ 图标）
3. 切换到 **"记忆管理"** 选项卡

## 📊 界面功能

### 当前配置卡片
- **记忆后端**: 显示当前使用的后端类型
  - 🔵 短期记忆 (滑动窗口)
  - 🟢 向量数据库 (语义检索)
  - 🟠 键值存储 (关键词检索)
  - 🟣 图记忆 (关系推理)
- **配置参数**:
  - 短期记忆: 最大对话轮数
  - VDB: 嵌入模型、向量维度

### 使用统计卡片
- 活跃会话数
- 记忆后端类型

### 会话详情表格
- 会话 ID
- 后端类型
- 记忆使用情况
  - 短期记忆: 对话数 / 最大数，使用百分比进度条
  - 其他后端: 集合名称、索引状态

> **💡 注意**: 记忆服务是运行时创建的，不会被持久化。会话加载后，第一次发送消息时会自动创建记忆服务。## 🔧 配置记忆后端

### 方式 1: 通过环境变量（推荐）

在启动 Gateway 前设置环境变量：

```bash
# 使用短期记忆（默认）
export SAGE_MEMORY_BACKEND=short_term
export SAGE_MEMORY_MAX_DIALOGS=10

# 使用向量数据库
export SAGE_MEMORY_BACKEND=vdb
export SAGE_MEMORY_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
export SAGE_MEMORY_EMBEDDING_DIM=384

# 使用键值存储
export SAGE_MEMORY_BACKEND=kv
export SAGE_MEMORY_INDEX_TYPE=bm25s

# 使用图记忆
export SAGE_MEMORY_BACKEND=graph
```

### 方式 2: 通过代码配置

```python
from sage.gateway.session.manager import SessionManager

# 短期记忆
manager = SessionManager(
    max_memory_dialogs=10,
    memory_backend="short_term"
)

# 向量数据库
manager = SessionManager(
    memory_backend="vdb",
    memory_config={
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384
    }
)

# 键值存储
manager = SessionManager(
    memory_backend="kv",
    memory_config={
        "default_index_type": "bm25s"
    }
)

# 图记忆
manager = SessionManager(
    memory_backend="graph"
)
```

## 🧪 测试记忆功能

### 使用 Chat 界面测试

1. 在 Chat 模式创建新会话
2. 进行多轮对话（超过窗口大小）
3. 打开记忆管理查看使用情况
4. 观察记忆滑动窗口的效果

### 使用 API 测试

```bash
# 1. 创建会话
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Session"}'

# 2. 发送消息（会自动存储到记忆）
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sage-default",
    "messages": [{"role": "user", "content": "Hello"}],
    "session_id": "<session_id>",
    "stream": false
  }'

# 3. 查看记忆配置（直接访问 Gateway）
curl http://localhost:8000/memory/config

# 4. 查看记忆统计（直接访问 Gateway）
curl http://localhost:8000/memory/stats

# 或通过 Studio 前端代理访问（如果 Studio 在运行）
curl http://localhost:5173/api/chat/memory/config
curl http://localhost:5173/api/chat/memory/stats
```

### 使用 Python 测试

```python
from sage.gateway.session.manager import SessionManager

# 创建管理器
manager = SessionManager(max_memory_dialogs=3)

# 创建会话
session = manager.create_session(title="Test")

# 模拟多轮对话
dialogs = [
    ("你好", "你好！有什么可以帮助你的？"),
    ("SAGE 是什么？", "SAGE 是一个数据处理框架"),
    ("它有什么特点？", "SAGE 支持声明式编程"),
    ("如何安装？", "使用 pip install isage"),
    ("能举个例子吗？", "当然，请看示例代码..."),
]

for user_msg, assistant_msg in dialogs:
    manager.store_dialog_to_memory(session.id, user_msg, assistant_msg)
    print(f"✅ 存储: {user_msg[:20]}...")

# 检索记忆
history = manager.retrieve_memory_history(session.id)
print(f"\n📝 记忆历史:\n{history}")

# 检查记忆服务
memory_service = manager.get_memory_service(session.id)
print(f"\n📊 记忆统计:")
print(f"   类型: {type(memory_service).__name__}")
print(f"   大小: {len(memory_service.dialog_queue)}/{memory_service.max_dialog}")
```

## 📈 监控记忆使用

### Dashboard 指标

访问记忆管理界面可以看到：

1. **实时统计**
   - 总会话数
   - 每个会话的记忆使用情况
   - 容量使用百分比

2. **使用趋势**
   - 对话数随时间变化
   - 记忆溢出情况
   - 会话活跃度

### API 监控

```bash
# 定期检查记忆状态（直接访问 Gateway）
watch -n 5 'curl -s http://localhost:8000/memory/stats | jq .'

# 或通过前端代理访问（如果 Studio 在运行）
watch -n 5 'curl -s http://localhost:5173/api/chat/memory/stats | jq .'

# 监控特定会话
curl http://localhost:8000/sessions/<session_id>
```

## 💡 最佳实践

### 1. 选择合适的记忆后端

- **短期记忆**: 适合短期对话、快速响应
- **VDB**: 适合需要语义检索的长期记忆
- **KV**: 适合关键词精确匹配
- **图记忆**: 适合需要关系推理的场景

### 2. 配置窗口大小

```python
# 短对话：小窗口
manager = SessionManager(max_memory_dialogs=5)

# 长对话：大窗口
manager = SessionManager(max_memory_dialogs=20)

# 需要平衡性能和上下文
manager = SessionManager(max_memory_dialogs=10)  # 推荐
```

### 3. 定期清理过期会话

```python
# 清理超过 30 分钟未活动的会话
manager.cleanup_expired(max_age_minutes=30)
```

### 4. 监控内存使用

```python
# 获取统计信息
stats = manager.get_stats()
print(f"Total sessions: {stats['total']}")
print(f"Active sessions: {stats['active']}")
```

## 🔍 故障排查

### 问题 1: 记忆管理界面空白

**解决方案:**
1. 检查 Gateway 是否运行: `curl http://localhost:8000/health`
2. 检查浏览器控制台是否有错误
3. 确认 API 端点可访问: `curl http://localhost:8000/memory/config`

### 问题 2: 记忆数据不显示

**解决方案:**
1. 确认有活跃会话
2. 检查会话中是否有对话
3. 查看 Gateway 日志: `tail -f ~/.sage/gateway.log`

### 问题 3: 记忆统计不准确

**解决方案:**
1. 刷新页面重新加载数据
2. 检查 SessionManager 状态
3. 重启 Gateway 服务

## 📚 相关文档

- [SAGE Memory 架构文档](../../docs-public/docs_src/guides/packages/sage-middleware/components/neuromem.md)
- [Gateway API 文档](../../packages/sage-gateway/README.md)
- [改进报告](./MEMORY_INTEGRATION_IMPROVEMENTS.md)

## 🎯 下一步

1. 尝试不同的记忆后端
2. 测试大量会话的性能
3. 集成到你的应用中
4. 提供反馈和建议

Happy coding! 🚀
