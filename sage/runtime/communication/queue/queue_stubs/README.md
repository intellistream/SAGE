# Queue Stubs - 统一队列转换系统

## 概述

Queue Stubs 是 SAGE 框架中的统一队列通信系统，提供了 SAGE Queue、Ray Queue 和其他队列类型与 Queue Descriptor 之间的双向转换功能。

## 核心特性

- **统一接口**: 所有队列类型都实现 `QueueLike` 协议
- **双向转换**: 支持 Queue ↔ Descriptor 的互相转换
- **跨进程传递**: 通过可序列化的 Descriptor 实现跨进程队列引用传递
- **自动选择**: 根据运行环境自动选择最适合的队列类型
- **扩展性**: 易于添加新的队列类型支持

## 支持的队列类型

| 队列类型 | 描述 | 适用场景 |
|---------|------|----------|
| `sage_queue` | SAGE 高性能队列 | 高性能、跨进程通信 |
| `ray_queue` | Ray 分布式队列 | 分布式计算环境 |
| `ray_actor` | Ray Actor 队列 | Ray Actor 之间通信 |
| `local` | 本地进程内队列 | 单进程内线程通信 |
| `shm` | 共享内存队列 | 多进程通信 |

## 快速开始

### 1. 基本使用

```python
from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor

# 创建队列描述符
descriptor = QueueDescriptor.create_sage_queue(
    queue_id="my_sage_queue",
    maxsize=1024 * 1024,
    auto_cleanup=True
)

# 从描述符创建队列
queue = resolve_descriptor(descriptor)

# 使用队列
queue.put("Hello World!")
message = queue.get()
print(message)  # 输出: Hello World!

# 关闭队列
queue.close()
```

### 2. 便利函数使用

```python
from sage.runtime.communication.queue_stubs import (
    create_sage_queue,
    create_ray_queue,
    create_local_queue,
    create_auto_queue
)

# 直接创建各种类型的队列
sage_queue = create_sage_queue("sage_test", maxsize=2048)
ray_queue = create_ray_queue("ray_test", maxsize=100)  
local_queue = create_local_queue("local_test", maxsize=50)

# 自动选择最适合的队列类型
auto_queue = create_auto_queue("auto_test", maxsize=500)
```

### 3. 从现有队列创建描述符

```python
from queue import Queue
from sage.runtime.communication.queue_stubs import LocalQueueStub

# 从现有 Python Queue 创建
python_queue = Queue(maxsize=10)
local_stub = LocalQueueStub.from_queue(python_queue, queue_id="existing_queue")
descriptor = local_stub.to_descriptor()

print(f"描述符: {descriptor}")
```

### 4. 跨进程队列传递

```python
import multiprocessing
from sage.runtime.communication.queue_descriptor import QueueDescriptor, resolve_descriptor

def worker_process(descriptor_json):
    # 在子进程中从 JSON 恢复描述符
    descriptor = QueueDescriptor.from_json(descriptor_json)
    queue = resolve_descriptor(descriptor)
    
    # 使用队列进行通信
    task = queue.get()
    result = f"处理结果: {task}"
    queue.put(result)

# 主进程
descriptor = QueueDescriptor.create_shm_queue("shared_queue", "cross_process")
queue = resolve_descriptor(descriptor)

# 启动子进程，传递序列化的描述符
process = multiprocessing.Process(
    target=worker_process, 
    args=(descriptor.to_json(),)
)
process.start()

# 与子进程通信
queue.put("任务数据")
result = queue.get()
print(result)

process.join()
```

## API 参考

### QueueDescriptor

核心的队列描述符类，用于描述和序列化队列信息。

```python
@dataclass
class QueueDescriptor:
    queue_id: str          # 队列唯一标识
    queue_type: str        # 队列类型
    metadata: Dict[str, Any]  # 队列配置元数据
    created_timestamp: Optional[float] = None
```

#### 创建方法

```python
# SAGE Queue
QueueDescriptor.create_sage_queue(queue_id, maxsize, auto_cleanup, namespace, enable_multi_tenant)

# Ray Queue  
QueueDescriptor.create_ray_queue(queue_id, maxsize)
QueueDescriptor.create_ray_actor_queue(actor_name, queue_id, maxsize)

# 本地队列
QueueDescriptor.create_local_queue(queue_id, maxsize)

# 共享内存队列
QueueDescriptor.create_shm_queue(shm_name, queue_id, maxsize)
```

#### 序列化方法

```python
descriptor = QueueDescriptor.create_sage_queue("test")

# 序列化为 JSON
json_str = descriptor.to_json()

# 从 JSON 反序列化
restored = QueueDescriptor.from_json(json_str)

# 转换为字典
dict_data = descriptor.to_dict()

# 从字典创建
restored = QueueDescriptor.from_dict(dict_data)
```

### Queue Stubs

各种队列类型的具体实现类。

#### SageQueueStub

```python
from sage.runtime.communication.queue_stubs import SageQueueStub

# 从描述符创建
stub = SageQueueStub.from_descriptor(descriptor)

# 从现有 SAGE Queue 创建
stub = SageQueueStub.from_sage_queue(sage_queue, queue_id="existing")

# 队列操作
stub.put(data)
result = stub.get()
stats = stub.get_stats()
stub.close()

# 转换为描述符
descriptor = stub.to_descriptor()
```

#### RayQueueStub

```python
from sage.runtime.communication.queue_stubs import RayQueueStub

# 从描述符创建
stub = RayQueueStub.from_descriptor(descriptor)

# 从现有 Ray Queue 创建
stub = RayQueueStub.from_ray_queue(ray_queue, queue_type="ray_queue")

# 队列操作
stub.put(data)
result = stub.get()
```

#### LocalQueueStub

```python
from sage.runtime.communication.queue_stubs import LocalQueueStub

# 从描述符创建
stub = LocalQueueStub.from_descriptor(descriptor)

# 从现有 Queue 创建
stub = LocalQueueStub.from_queue(python_queue, queue_id="local")
```

### 便利函数

```python
from sage.runtime.communication.queue_stubs import (
    create_sage_queue,
    create_ray_queue, 
    create_ray_actor_queue,
    create_local_queue,
    create_shm_queue,
    create_auto_queue,
    auto_select_queue_type,
    list_supported_queue_types
)

# 创建队列
queue = create_sage_queue("sage_test", maxsize=1024)
queue = create_ray_queue("ray_test", maxsize=100)
queue = create_local_queue("local_test", maxsize=50)

# 自动选择
selected_type = auto_select_queue_type()
auto_queue = create_auto_queue("auto_test")

# 获取支持的队列类型
types = list_supported_queue_types()
```

## 高级用法

### 自定义队列类型

要添加新的队列类型支持，需要：

1. 实现 `QueueLike` 协议的队列 Stub 类
2. 注册到全局映射表
3. 添加对应的描述符创建方法

```python
from sage.runtime.communication.queue_descriptor import (
    QueueLike, QueueDescriptor, register_queue_implementation
)

class CustomQueueStub:
    def __init__(self, descriptor: QueueDescriptor):
        # 初始化逻辑
        pass
    
    def put(self, item, block=True, timeout=None):
        # 实现 put 方法
        pass
    
    def get(self, block=True, timeout=None):
        # 实现 get 方法  
        pass
    
    # ... 其他 QueueLike 方法

# 注册新的队列类型
register_queue_implementation("custom", CustomQueueStub)
```

### 错误处理

```python
from queue import Empty, Full

try:
    # 非阻塞操作
    item = queue.get_nowait()
except Empty:
    print("队列为空")

try:
    queue.put_nowait(data)
except Full:
    print("队列已满")
```

### 性能监控

```python
# 对于 SAGE Queue，可以获取详细统计信息
if hasattr(queue, 'get_stats'):
    stats = queue.get_stats()
    print(f"队列利用率: {stats.get('utilization', 0):.2%}")
    print(f"读取字节数: {stats.get('total_bytes_read', 0)}")
    print(f"写入字节数: {stats.get('total_bytes_written', 0)}")
```

## 测试

运行测试用例：

```bash
# 运行基础测试
python -m unittest sage.runtime.communication.test_queue_stubs

# 运行示例代码
python sage/runtime/communication/queue_conversion_examples.py
```

## 注意事项

1. **资源清理**: 使用完队列后记得调用 `close()` 方法
2. **线程安全**: 所有队列 Stub 都是线程安全的
3. **序列化限制**: 队列中的数据必须是可序列化的
4. **超时处理**: 不同队列类型的超时行为可能略有差异
5. **依赖检查**: Ray 和 SAGE Queue 需要相应的库才能使用

## 故障排除

### 常见问题

1. **ImportError**: 确保相关库已安装（Ray, SAGE Queue等）
2. **Queue Full/Empty**: 使用适当的 maxsize 和超时设置
3. **序列化错误**: 确保队列中的数据类型支持序列化
4. **跨进程问题**: 验证共享内存权限和进程间通信设置

### 调试技巧

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('sage.runtime.communication')
logger.setLevel(logging.DEBUG)

# 检查支持的队列类型
from sage.runtime.communication.queue_stubs import list_supported_queue_types
print(f"支持的队列类型: {list_supported_queue_types()}")
```

## 贡献

欢迎为 Queue Stubs 系统贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支
3. 添加测试用例
4. 提交 Pull Request

## 许可证

本项目使用 Apache 2.0 许可证。
