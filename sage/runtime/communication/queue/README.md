# Queue Descriptor - 统一通信描述符系统

## 概述

Queue Descriptor 是一个统一的通信描述符系统，用于在异构通信环境中管理各种类型的队列通信方式。它提供了一个可序列化的描述符结构，支持本地队列、共享内存队列、Ray Actor队列、RPC队列等多种通信方式。

## 🆕 增强功能

### 序列化控制
- **can_serialize 字段**: 控制描述符是否可以序列化
- **智能序列化**: 自动检测和防止不可序列化对象的序列化

### 专用描述符类
- **LocalQueueDescriptor**: 包含队列对象引用，支持直接操作，不可序列化
- **RemoteQueueDescriptor**: 支持懒加载和缓存，可序列化，适合跨进程通信

### 直接队列操作
- 描述符本身支持队列操作（put、get、empty、qsize等）
- 无需额外的 resolve_descriptor 调用

## 核心功能

- **统一接口**: 为不同类型的队列提供统一的 `QueueLike` 协议
- **可序列化**: 支持跨进程传递队列引用
- **可扩展**: 支持动态注册新的队列类型实现
- **类型安全**: 使用 Python 类型提示和协议检查

## 核心组件

### 1. QueueDescriptor

可序列化的队列描述符，包含以下字段：

- `queue_id`: 队列的唯一标识符
- `queue_type`: 通信方式类型（如 "local", "shm", "ray_actor", "rpc" 等）
- `metadata`: 保存额外参数的字典（如 shm 名称、socket 地址、ray actor name 等）
- `can_serialize`: 是否可序列化（新增）
- `created_timestamp`: 创建时间戳

### 2. LocalQueueDescriptor

本地队列描述符，继承自 QueueDescriptor：

- 包含对实际队列对象的引用
- 支持直接的队列操作（put、get、empty、qsize等）
- `can_serialize = False`（不可序列化）
- 可转换为可序列化版本

### 3. RemoteQueueDescriptor  

远程队列描述符，继承自 QueueDescriptor：

- 支持懒加载：首次访问时才创建队列实例
- 支持缓存管理：可清除和重新初始化
- `can_serialize = True`（可序列化）
- 适合跨进程通信场景

### 2. QueueLike 协议

定义所有队列类型必须实现的方法：

```python
def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None
def get(self, block: bool = True, timeout: Optional[float] = None) -> Any
def empty(self) -> bool
def qsize(self) -> int
```

### 3. 解析和注册系统

- `resolve_descriptor(desc: QueueDescriptor) -> QueueLike`: 根据描述符创建队列实例
- `register_queue_implementation(queue_type: str, implementation_class)`: 注册队列类型实现
- `get_registered_queue_types()`: 获取已注册的队列类型

## 使用方法

### 基本用法（传统方式）

```python
from sage.runtime.communication.queue_descriptor import (
    QueueDescriptor, resolve_descriptor, register_queue_implementation
)

# 1. 创建队列描述符
desc = QueueDescriptor(queue_id="sink1", queue_type="shm", metadata={"shm_name": "shm_abc"})

# 2. 注册队列实现（需要先实现对应的队列类）
register_queue_implementation("shm", YourShmQueueImplementation)

# 3. 解析描述符获取队列对象
queue = resolve_descriptor(desc)

# 4. 使用队列
queue.put("test")
data = queue.get()  # 返回 "test"
```

### 🆕 增强用法

#### 直接队列操作（LocalQueueDescriptor）

```python
import queue
from sage.runtime.communication.queue_descriptor import create_local_queue_descriptor_with_ref

# 从现有队列创建描述符
python_queue = queue.Queue(maxsize=10)
local_desc = create_local_queue_descriptor_with_ref(
    queue_obj=python_queue,
    queue_id="my_queue",
    maxsize=10
)

# 直接通过描述符操作队列
local_desc.put("message1")
local_desc.put("message2")
print(f"队列大小: {local_desc.qsize()}")
data = local_desc.get()  # 返回 "message1"

# 注意：LocalQueueDescriptor 不可序列化
print(f"可序列化: {local_desc.can_serialize}")  # False
```

#### 懒加载远程队列（RemoteQueueDescriptor）

```python
from sage.runtime.communication.queue_descriptor import QueueDescriptor

# 创建远程队列描述符（可序列化）
remote_desc = QueueDescriptor.create_shm_queue("my_shm", "remote_queue")

# 直接操作，首次访问时自动初始化
remote_desc.put("lazy_message")  # 触发懒加载
data = remote_desc.get()

# 可以序列化传递
json_data = remote_desc.to_json()
# 在另一个进程中...
restored_desc = QueueDescriptor.from_json(json_data)
```

#### 序列化控制

```python
# 检查是否可序列化
if desc.can_serialize:
    json_data = desc.to_json()
else:
    # 转换为可序列化版本
    serializable_desc = desc.to_serializable_descriptor()
    json_data = serializable_desc.to_json()
```

### 工厂方法

```python
# 创建本地队列
local_desc = QueueDescriptor.create_local_queue("my_local", maxsize=100)

# 创建共享内存队列
shm_desc = QueueDescriptor.create_shm_queue("my_shm", "shm_name", maxsize=1000)

# 创建Ray Actor队列
ray_actor_desc = QueueDescriptor.create_ray_actor_queue("my_actor", "actor_name")

# 创建Ray分布式队列
ray_queue_desc = QueueDescriptor.create_ray_queue("my_ray", maxsize=50)

# 创建RPC队列
rpc_desc = QueueDescriptor.create_rpc_queue("localhost", 8080, "my_rpc")

# 创建SAGE高性能队列
sage_desc = QueueDescriptor.create_sage_queue("my_sage", maxsize=200)
```

### 序列化和跨进程传输

```python
# 序列化
desc = QueueDescriptor.create_local_queue("test")
json_str = desc.to_json()

# 反序列化
desc2 = QueueDescriptor.from_json(json_str)

# 在另一个进程中使用
queue = resolve_descriptor(desc2)
```

### 便利函数

```python
from sage.runtime.communication.queue_descriptor import (
    get_local_queue, attach_to_shm_queue, get_sage_queue
)

# 直接获取队列对象（需要先注册相应实现）
local_queue = get_local_queue("test_local", maxsize=10)
shm_queue = attach_to_shm_queue("test_shm", "shm_queue", maxsize=100)
sage_queue = get_sage_queue("test_sage", maxsize=200)
```

## 实现自定义队列类型

### 1. 实现队列类

```python
from sage.runtime.communication.queue_descriptor import QueueDescriptor
import queue

class MyCustomQueue:
    def __init__(self, descriptor: QueueDescriptor):
        self.descriptor = descriptor
        self.queue_id = descriptor.queue_id
        self.metadata = descriptor.metadata
        # 根据 metadata 初始化你的队列
        self._queue = queue.Queue()
    
    def put(self, item, block=True, timeout=None):
        self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block=True, timeout=None):
        return self._queue.get(block=block, timeout=timeout)
    
    def empty(self):
        return self._queue.empty()
    
    def qsize(self):
        return self._queue.qsize()
```

### 2. 注册实现

```python
from sage.runtime.communication.queue_descriptor import register_queue_implementation

register_queue_implementation("my_custom", MyCustomQueue)
```

### 3. 创建和使用

```python
desc = QueueDescriptor(
    queue_id="custom_test",
    queue_type="my_custom",
    metadata={"custom_param": "value"}
)

queue = resolve_descriptor(desc)
queue.put("Hello Custom Queue!")
```

## 支持的队列类型

系统设计支持以下队列类型（具体实现需要单独注册）：

- **local**: 本地内存队列
- **shm**: 共享内存队列
- **ray_actor**: Ray Actor 队列
- **ray_queue**: Ray 分布式队列
- **rpc**: RPC 队列
- **sage_queue**: SAGE 高性能队列

## 测试

系统提供了完整的测试套件，包含各种队列类型的存根实现：

```bash
cd /api-rework
python sage/runtime/communication/test_queue_descriptor.py
```

或者运行简单测试：

```bash
python simple_test.py
```

## 在 SAGE 系统中的应用

Queue Descriptor 系统专为 SAGE 引擎的异构通信需求设计，可以在以下场景中使用：

1. **跨进程任务通信**: 在 Dispatcher 中传递队列引用
2. **服务间通信**: 统一不同服务的通信接口
3. **本地/远程切换**: 根据运行环境动态选择通信方式
4. **资源管理**: 统一管理和清理各种通信资源

## 架构优势

- **解耦**: 队列描述符与具体实现分离
- **灵活**: 支持运行时动态注册新的队列类型
- **一致性**: 为所有队列类型提供统一的接口
- **可维护性**: 集中管理通信逻辑
- **可测试性**: 提供存根实现便于单元测试

## 扩展指南

要添加新的队列类型：

1. 实现 `QueueLike` 协议的队列类
2. 在构造函数中接受 `QueueDescriptor` 参数
3. 使用 `register_queue_implementation` 注册实现
4. 可选：在 `QueueDescriptor` 中添加工厂方法
5. 可选：在便利函数中添加快捷方法

这个设计确保了系统的可扩展性和向后兼容性。
