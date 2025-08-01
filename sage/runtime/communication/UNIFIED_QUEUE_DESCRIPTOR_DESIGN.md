# 统一多态队列描述符 (UnifiedQueueDescriptor) 设计文档

## 概述

`UnifiedQueueDescriptor` 是一个统一的多态队列描述符，提供了一个可序列化的通信描述符结构，用于在异构通信系统中统一描述和管理各种类型的队列通信方式。

## 核心特性

### 1. 多态接口 (Polymorphic Interface)
- **统一的队列操作接口**: 实现了 `QueueLike` 协议，所有队列类型都提供相同的 `put()`, `get()`, `empty()`, `qsize()` 等方法
- **透明的类型抽象**: 用户无需关心底层队列的具体实现，统一调用接口
- **扩展方法支持**: 自动适配底层队列的额外方法如 `put_nowait()`, `get_nowait()`, `full()` 等

```python
# 不同类型的队列使用相同的接口
local_queue = UnifiedQueueDescriptor.create_local_queue("local_q")
shm_queue = UnifiedQueueDescriptor.create_shm_queue("shared", "shm_q")
ray_queue = UnifiedQueueDescriptor.create_ray_queue("ray_q")

# 统一的操作方式
for queue in [local_queue, shm_queue, ray_queue]:
    queue.put("Hello")           # 统一的put操作
    item = queue.get()           # 统一的get操作
    print(f"Size: {queue.qsize()}")  # 统一的状态查询
```

### 2. 懒加载 (Lazy Loading)
- **按需初始化**: 队列描述符创建时不会立即创建实际的队列实例
- **首次访问初始化**: 第一次调用队列方法时才会创建底层队列对象
- **缓存管理**: 支持清除缓存和重新初始化
- **性能优化**: 避免不必要的资源创建

```python
# 创建描述符（不会创建实际队列）
desc = UnifiedQueueDescriptor.create_ray_actor_queue("worker", "ray_q")
print(desc.is_initialized())  # False

# 第一次使用时才初始化
desc.put("item")  # 此时才创建实际的队列
print(desc.is_initialized())  # True

# 可以清除缓存
desc.clear_cache()
print(desc.is_initialized())  # False
```

### 3. 序列化支持 (Serialization Support)
- **智能序列化**: 自动识别并过滤不可序列化的对象引用
- **跨进程安全**: 支持在进程间安全传递队列描述符信息
- **多种格式**: 支持 JSON 和 Pickle 序列化
- **类型转换**: 提供不可序列化到可序列化的转换

```python
# 可序列化的描述符
desc = UnifiedQueueDescriptor.create_shm_queue("shared", "q1")
json_str = desc.to_json()  # 序列化为JSON
restored = UnifiedQueueDescriptor.from_json(json_str)  # 反序列化

# 包含队列实例的描述符（不可序列化）
desc_with_queue = UnifiedQueueDescriptor.create_local_queue(
    "local", queue_instance=real_queue_obj
)
print(desc_with_queue.can_serialize)  # False

# 转换为可序列化版本
serializable_desc = desc_with_queue.to_serializable_descriptor()
json_str = serializable_desc.to_json()  # 现在可以序列化
```

### 4. 类型安全处理
- **自动类型检测**: 自动识别描述符是否包含不可序列化对象
- **安全转换**: 提供安全的序列化转换机制
- **元数据过滤**: 智能过滤元数据中的不可序列化字段
- **错误预防**: 在序列化前检查并防止错误

### 5. 队列池管理
- **批量创建**: 支持批量创建多个队列描述符
- **统一管理**: 提供队列池的序列化和管理功能
- **配置驱动**: 通过配置文件或配置对象批量创建队列

```python
# 批量创建队列池
pool_config = [
    {"type": "local", "maxsize": 10, "queue_id": "worker_1"},
    {"type": "shm", "shm_name": "shared", "maxsize": 50, "queue_id": "shared_1"},
    {"type": "ray_actor", "actor_name": "processor", "queue_id": "ray_1"}
]

pool = create_queue_pool(pool_config, "production_pool")
pool_json = serialize_queue_pool(pool)  # 序列化整个池
restored_pool = deserialize_queue_pool(pool_json)  # 恢复队列池
```

## 架构设计

### 类层次结构

```
QueueLike (Protocol)  ← 定义队列接口协议
    ↑
UnifiedQueueDescriptor ← 统一的多态描述符实现
    ↑
QueueDescriptor (alias) ← 向后兼容别名
LocalQueueDescriptor (alias) ← 向后兼容别名  
RemoteQueueDescriptor (alias) ← 向后兼容别名
```

### 核心组件

1. **UnifiedQueueDescriptor**: 核心类，实现所有主要功能
2. **QueueLike Protocol**: 定义队列接口标准
3. **队列注册系统**: 支持动态注册不同类型的队列实现
4. **序列化系统**: 处理跨进程数据传递
5. **工厂方法**: 提供便捷的队列创建接口

### 数据结构

```python
class UnifiedQueueDescriptor:
    queue_id: str                    # 队列唯一标识符
    queue_type: str                  # 队列类型 ("local", "shm", "ray_actor", etc.)
    metadata: Dict[str, Any]         # 队列配置元数据
    can_serialize: bool              # 是否可序列化标志
    created_timestamp: float         # 创建时间戳
    
    # 私有属性
    _queue_instance: QueueLike       # 缓存的队列实例
    _initialized: bool               # 初始化状态
    _lazy_loading: bool              # 懒加载标志
```

## 支持的队列类型

### 1. 本地队列 (Local Queue)
```python
desc = UnifiedQueueDescriptor.create_local_queue("local_q", maxsize=10)
```

### 2. 共享内存队列 (Shared Memory Queue)  
```python
desc = UnifiedQueueDescriptor.create_shm_queue("shm_name", "shm_q", maxsize=100)
```

### 3. Ray Actor队列 (Ray Actor Queue)
```python
desc = UnifiedQueueDescriptor.create_ray_actor_queue("actor_name", "ray_q")
```

### 4. Ray分布式队列 (Ray Distributed Queue)
```python
desc = UnifiedQueueDescriptor.create_ray_queue("ray_q", maxsize=50)
```

### 5. RPC队列 (RPC Queue)
```python
desc = UnifiedQueueDescriptor.create_rpc_queue("localhost", 8080, "rpc_q")
```

### 6. SAGE高性能队列 (SAGE High-Performance Queue)
```python
desc = UnifiedQueueDescriptor.create_sage_queue(
    "sage_q", 
    maxsize=1000,
    auto_cleanup=True,
    namespace="production"
)
```

## 使用示例

### 基本使用
```python
from sage.runtime.communication.queue_descriptor import UnifiedQueueDescriptor

# 创建队列描述符
queue_desc = UnifiedQueueDescriptor.create_local_queue("my_queue", maxsize=10)

# 直接使用队列接口
queue_desc.put("Hello World")
queue_desc.put("Another Message")

print(f"Queue size: {queue_desc.qsize()}")
print(f"Is empty: {queue_desc.empty()}")

# 获取消息
message = queue_desc.get()
print(f"Received: {message}")
```

### 跨进程使用
```python
# 进程A：创建并序列化队列描述符
desc = UnifiedQueueDescriptor.create_shm_queue("shared_mem", "process_queue")
serialized = desc.to_json()

# 通过网络或文件传递 serialized 到进程B
send_to_process_b(serialized)

# 进程B：反序列化并使用队列
desc = UnifiedQueueDescriptor.from_json(serialized)
desc.put("Message from Process B")
item = desc.get()
```

### 队列池管理
```python
# 创建队列池
configs = [
    {"type": "local", "maxsize": 10},
    {"type": "shm", "shm_name": "shared", "maxsize": 100},
    {"type": "ray_actor", "actor_name": "worker", "maxsize": 50}
]

pool = create_queue_pool(configs, "worker_pool")

# 使用队列池中的队列
for queue_id, queue_desc in pool.items():
    queue_desc.put(f"Task for {queue_id}")
    
# 序列化整个队列池
pool_data = serialize_queue_pool(pool)
```

## 向后兼容性

为了保持向后兼容，提供了以下别名：
- `QueueDescriptor` = `UnifiedQueueDescriptor`
- `LocalQueueDescriptor` = `UnifiedQueueDescriptor`
- `RemoteQueueDescriptor` = `UnifiedQueueDescriptor`

原有的 API 继续可用：
```python
# 旧式 API 仍然有效
desc = QueueDescriptor.create_local_queue("old_style")
desc.put("Still works")
```

## 扩展性

### 注册新的队列类型
```python
from sage.runtime.communication.queue_descriptor import register_queue_implementation

class MyCustomQueueStub:
    def __init__(self, descriptor):
        self.desc = descriptor
        # 初始化自定义队列
    
    def put(self, item, block=True, timeout=None):
        # 实现put逻辑
        pass
    
    def get(self, block=True, timeout=None):
        # 实现get逻辑
        pass
    
    def empty(self):
        # 实现empty逻辑
        pass
    
    def qsize(self):
        # 实现qsize逻辑
        pass

# 注册自定义队列类型
register_queue_implementation("custom", MyCustomQueueStub)

# 现在可以使用自定义队列类型
desc = UnifiedQueueDescriptor("custom_q", "custom", {"param": "value"})
```

## 最佳实践

### 1. 选择合适的队列类型
- **本地队列**: 单进程内使用，性能最好
- **共享内存队列**: 同一机器多进程通信
- **Ray队列**: 分布式系统，跨机器通信
- **RPC队列**: 异构系统集成
- **SAGE队列**: 高性能场景

### 2. 序列化使用
- 跨进程传递时使用可序列化的描述符
- 避免在序列化的描述符中包含队列实例
- 使用 `to_serializable_descriptor()` 安全转换

### 3. 懒加载优化
- 大批量创建队列描述符时利用懒加载特性
- 不需要立即使用的队列描述符保持未初始化状态
- 合理使用 `clear_cache()` 管理内存

### 4. 错误处理
```python
try:
    queue_desc.put("item")
except Exception as e:
    logger.error(f"Queue operation failed: {e}")
    # 处理队列操作失败
```

## 总结

UnifiedQueueDescriptor 提供了一个强大而灵活的队列描述符系统，具有以下优势：

1. **统一接口**: 所有队列类型使用相同的接口，简化了使用
2. **高性能**: 懒加载和缓存机制优化了性能
3. **跨进程安全**: 智能序列化支持安全的跨进程通信
4. **易于扩展**: 插件化架构支持添加新的队列类型
5. **向后兼容**: 保持与现有代码的兼容性
6. **类型安全**: 自动处理序列化和类型安全问题

这个设计为异构分布式系统提供了一个统一、高效、安全的队列通信抽象层。
