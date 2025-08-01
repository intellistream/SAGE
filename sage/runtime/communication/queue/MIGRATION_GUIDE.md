# Queue Architecture Migration Guide

## 概述

从 SAGE v2.0 开始，我们统一了队列通信架构，使用单一的 `QueueDescriptor` 类替代之前分散的 `queue_stubs` 实现。这个变化大大简化了代码结构，提高了可维护性，并提供了更好的序列化支持。

## 为什么进行这次重构？

### 之前的问题
1. **代码重复**：每个 queue stub 都实现了相同的队列接口方法（put, get, empty, qsize 等）
2. **架构复杂**：需要维护多个 stub 类和注册系统
3. **功能重叠**：QueueDescriptor 已经具备了 stub 类的所有功能
4. **维护成本高**：修改队列接口需要同时更新多个文件

### 新架构的优势
1. **统一接口**：所有队列类型使用同一个 QueueDescriptor 类
2. **简化代码**：移除了重复的实现代码
3. **更好的序列化**：统一的序列化机制
4. **懒加载支持**：按需创建底层队列实例
5. **易于扩展**：添加新队列类型只需要在一个地方修改

## 迁移指南

### 1. 基本迁移

#### 旧代码（已废弃）
```python
from sage.runtime.communication.queue.queue_stubs import SageQueueStub, LocalQueueStub

# 创建 SAGE 队列
descriptor = QueueDescriptor.create_sage_queue(queue_id="my_queue")
sage_stub = SageQueueStub.from_descriptor(descriptor)
sage_stub.put("hello")
item = sage_stub.get()

# 创建本地队列
descriptor = QueueDescriptor.create_local_queue(queue_id="local_queue")
local_stub = LocalQueueStub.from_descriptor(descriptor)
local_stub.put("world")
```

#### 新代码（推荐）
```python
from sage.runtime.communication.queue import QueueDescriptor

# 创建 SAGE 队列 - 直接使用描述符
sage_queue = QueueDescriptor.create_sage_queue(queue_id="my_queue")
sage_queue.put("hello")  # 直接调用，无需 stub
item = sage_queue.get()

# 创建本地队列
local_queue = QueueDescriptor.create_local_queue(queue_id="local_queue")
local_queue.put("world")  # 统一接口
```

### 2. 自动迁移工具

如果您有大量使用旧 API 的代码，可以使用我们提供的迁移工具：

```python
from sage.runtime.communication.queue import (
    QueueMigrationHelper, 
    migrate_queue_pool,
    quick_migrate
)

# 单个队列迁移
old_sage_stub = SageQueueStub(descriptor)
new_descriptor = quick_migrate(old_sage_stub)

# 批量迁移
old_queue_pool = {
    "queue1": old_sage_stub,
    "queue2": old_local_stub,
    # ...
}
new_queue_pool = migrate_queue_pool(old_queue_pool)
```

### 3. 向后兼容包装器

如果您需要逐步迁移，可以使用向后兼容包装器：

```python
from sage.runtime.communication.queue import LegacyQueueStubWrapper

# 创建新式描述符
descriptor = QueueDescriptor.create_sage_queue(queue_id="my_queue")

# 包装成旧式接口
legacy_wrapper = LegacyQueueStubWrapper(descriptor)
legacy_wrapper.put("hello")  # 使用旧式方法
item = legacy_wrapper.get()
```

## 支持的队列类型

新架构支持所有之前的队列类型：

### 1. 本地队列 (local)
```python
queue = QueueDescriptor.create_local_queue(
    queue_id="local_queue",
    maxsize=100
)
```

### 2. 共享内存队列 (shm)
```python
queue = QueueDescriptor.create_shm_queue(
    shm_name="shared_queue",
    queue_id="shm_queue",
    maxsize=1000
)
```

### 3. SAGE 队列 (sage_queue)
```python
queue = QueueDescriptor.create_sage_queue(
    queue_id="sage_queue",
    maxsize=1024 * 1024,
    auto_cleanup=True,
    namespace="my_namespace",
    enable_multi_tenant=True
)
```

### 4. Ray 队列 (ray_queue)
```python
queue = QueueDescriptor.create_ray_queue(
    queue_id="ray_queue",
    maxsize=0  # 无限制
)
```

### 5. Ray Actor 队列 (ray_actor)
```python
queue = QueueDescriptor.create_ray_actor_queue(
    actor_name="my_actor",
    queue_id="ray_actor_queue"
)
```

### 6. RPC 队列 (rpc)
```python
queue = QueueDescriptor.create_rpc_queue(
    server_address="localhost",
    port=8080,
    queue_id="rpc_queue"
)
```

## 统一接口方法

所有队列类型都支持以下标准接口：

```python
# 基本操作
queue.put(item, block=True, timeout=None)
item = queue.get(block=True, timeout=None)

# 非阻塞操作
queue.put_nowait(item)
item = queue.get_nowait()

# 状态查询
is_empty = queue.empty()
size = queue.qsize()
is_full = queue.full()

# 描述符管理
queue.clear_cache()  # 清除内部缓存
is_init = queue.is_initialized()  # 检查是否已初始化
clone = queue.clone("new_id")  # 克隆描述符
```

## 序列化支持

新架构提供了强大的序列化功能：

```python
# 序列化为字典
data = queue.to_dict()

# 序列化为 JSON
json_str = queue.to_json()

# 从字典/JSON 恢复
queue2 = QueueDescriptor.from_dict(data)
queue3 = QueueDescriptor.from_json(json_str)

# 批量序列化
queue_pool = {
    "q1": queue1,
    "q2": queue2
}
json_data = serialize_queue_pool(queue_pool)
restored_pool = deserialize_queue_pool(json_data)
```

## 性能优化

### 1. 懒加载
队列实例只在首次使用时创建，减少资源消耗：

```python
queue = QueueDescriptor.create_sage_queue(queue_id="lazy_queue")
# 此时还没有创建底层队列实例

queue.put("item")  # 现在才创建底层实例
```

### 2. 缓存管理
```python
# 清除缓存以释放资源
queue.clear_cache()

# 检查是否已初始化
if not queue.is_initialized():
    print("Queue not yet initialized")
```

## 常见问题 (FAQ)

### Q: 旧的 queue_stubs 代码还能运行吗？
A: 是的，我们提供了向后兼容层，但会显示废弃警告。建议尽快迁移到新架构。

### Q: 如何处理现有的序列化数据？
A: 旧的序列化格式仍然兼容，可以正常反序列化。

### Q: 性能有什么变化？
A: 新架构通过减少对象创建和统一接口，通常性能更好。懒加载也减少了内存使用。

### Q: 如何扩展新的队列类型？
A: 只需要在 `QueueDescriptor._create_queue_instance()` 方法中添加新的队列类型处理逻辑。

## 最佳实践

1. **优先使用工厂方法**：使用 `QueueDescriptor.create_*()` 方法创建队列
2. **利用序列化功能**：在跨进程通信中充分利用序列化能力
3. **使用懒加载**：对于可能不会立即使用的队列，利用懒加载特性
4. **及时清理**：对于临时队列，记得调用相应的清理方法
5. **统一错误处理**：所有队列类型使用相同的错误处理模式

## 迁移时间表

- **v2.0**: 新架构发布，旧架构标记为废弃
- **v2.1**: 增强迁移工具和文档
- **v3.0**: 完全移除旧的 queue_stubs 模块

建议在 v3.0 发布前完成迁移工作。
