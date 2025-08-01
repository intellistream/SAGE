# SAGE Universal Queue Implementation Issue

## 问题描述 (Issue Description)

SAGE框架需要一个统一的队列通信系统，能够支持异构复杂通信场景。当前系统缺乏一个通用的队列抽象层，导致不同通信方式之间的集成困难。

## 解决方案概述 (Solution Overview)

实现基于**Queue Descriptor + 多态Queue**的通用队列系统，通过可序列化的描述符实现跨进程队列传递和动态队列构造。

## 核心设计理念 (Core Design Principles)

### 1. 双向转换机制
- **Queue → Descriptor**: 从现有队列对象生成可序列化的描述符
- **Descriptor → Queue**: 从描述符反向构造对应的队列实例

### 2. 多态队列支持
支持多种队列类型的统一接口：
- `local`: 本地进程内队列 (queue.Queue)
- `shm`: 共享内存队列 (multiprocessing)
- `ray_actor`: Ray Actor队列
- `ray_queue`: Ray分布式队列
- `rpc`: RPC网络队列
- `sage_queue`: SAGE高性能自定义队列

### 3. 跨进程序列化
- 描述符完全可序列化 (JSON/Pickle)
- 支持跨进程、跨机器传递
- 保持队列连接信息的完整性

## 技术实现方案 (Technical Implementation)

### 当前已实现部分

```python
# 已实现的核心组件
@dataclass
class QueueDescriptor:
    queue_id: str
    queue_type: str  
    metadata: Dict[str, Any]
    created_timestamp: Optional[float] = None

# 协议接口
@runtime_checkable  
class QueueLike(Protocol):
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None: ...
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any: ...
    def empty(self) -> bool: ...
    def qsize(self) -> int: ...

# 注册机制
QUEUE_STUB_MAPPING = {}  # queue_type -> implementation_class
```

### 需要实现的队列实现类

#### 1. LocalQueueStub
```python
class LocalQueueStub:
    def __init__(self, descriptor: QueueDescriptor):
        self.descriptor = descriptor
        self._queue = queue.Queue(maxsize=descriptor.metadata.get('maxsize', 0))
    
    def put(self, item, block=True, timeout=None): ...
    def get(self, block=True, timeout=None): ...
    # ... 其他QueueLike方法
```

#### 2. SharedMemoryQueueStub  
```python
class SharedMemoryQueueStub:
    def __init__(self, descriptor: QueueDescriptor):
        shm_name = descriptor.metadata['shm_name']
        # 连接到已存在的共享内存队列或创建新的
        self._queue = multiprocessing.Queue(maxsize=descriptor.metadata.get('maxsize', 1000))
```

#### 3. RayActorQueueStub
```python  
class RayActorQueueStub:
    def __init__(self, descriptor: QueueDescriptor):
        actor_name = descriptor.metadata['actor_name']
        self._actor = ray.get_actor(actor_name)
    
    def put(self, item, block=True, timeout=None):
        return ray.get(self._actor.put.remote(item))
```

#### 4. SAGEQueueStub (高性能自定义实现)
```python
class SAGEQueueStub:
    def __init__(self, descriptor: QueueDescriptor):
        # 使用SAGE框架的高性能队列实现
        # 可能基于无锁数据结构、RDMA等
        pass
```

## 使用场景示例 (Usage Scenarios)

### 场景1: 跨进程队列传递
```python
# 进程A: 创建队列和描述符
queue = get_local_queue(maxsize=100)
descriptor = create_descriptor_from_existing_queue(queue, "local", maxsize=100)

# 序列化描述符并传递给进程B
json_desc = descriptor.to_json()
send_to_process_b(json_desc)

# 进程B: 从描述符重建队列连接
received_desc = QueueDescriptor.from_json(json_desc)  
queue_connection = resolve_descriptor(received_desc)
```

### 场景2: 异构通信适配
```python
# 根据运行环境动态选择队列类型
if ray.is_initialized():
    desc = QueueDescriptor.create_ray_queue(maxsize=1000)
elif multiprocessing_available:
    desc = QueueDescriptor.create_shm_queue("shared_queue_1")
else:
    desc = QueueDescriptor.create_local_queue(maxsize=100)

# 统一的队列操作接口
queue = resolve_descriptor(desc)
queue.put(data)
result = queue.get()
```

### 场景3: 分布式作业通信
```python
# JobManager创建通信拓扑
job_queues = {
    "input": QueueDescriptor.create_ray_actor_queue("input_actor"),
    "processing": QueueDescriptor.create_sage_queue(maxsize=10000),  
    "output": QueueDescriptor.create_rpc_queue("output_server", 8080)
}

# 将描述符分发给各个worker
for worker in workers:
    worker.setup_communication(job_queues)
```

## 实现优先级 (Implementation Priority)

### Phase 1: 基础实现
- [ ] `LocalQueueStub` - 本地队列实现
- [ ] `SharedMemoryQueueStub` - 共享内存队列
- [ ] 完善注册和解析机制
- [ ] 基础单元测试

### Phase 2: 分布式支持  
- [ ] `RayActorQueueStub` - Ray Actor队列
- [ ] `RayQueueStub` - Ray分布式队列
- [ ] 跨进程序列化测试

### Phase 3: 高级特性
- [ ] `RPCQueueStub` - RPC网络队列
- [ ] `SAGEQueueStub` - 高性能自定义队列
- [ ] 性能基准测试和优化

### Phase 4: 集成和优化
- [ ] 与JobManager集成
- [ ] 错误恢复和重连机制
- [ ] 监控和诊断工具

## 技术挑战 (Technical Challenges)

1. **序列化兼容性**: 确保描述符在不同Python版本和环境中的兼容性
2. **资源管理**: 队列的生命周期管理，避免资源泄漏
3. **错误处理**: 网络中断、进程崩溃等异常情况的处理
4. **性能优化**: 在灵活性和性能之间找到平衡
5. **线程安全**: 多线程环境下的队列操作安全性

## 预期收益 (Expected Benefits)

1. **统一接口**: 所有队列类型使用相同的API，简化代码维护
2. **动态适配**: 根据运行环境自动选择最适合的通信方式
3. **扩展性**: 易于添加新的队列类型和通信协议
4. **可测试性**: 便于进行单元测试和集成测试
5. **跨平台**: 支持不同的部署环境和硬件平台

## 相关文件 (Related Files)

- `sage/runtime/communication/queue_descriptor.py` - 核心描述符实现
- `sage/runtime/communication/queue_stubs/` - 各种队列实现目录
- `sage/jobmanager/job_manager.py` - JobManager集成点
- `sage/runtime/dispatcher.py` - 分发器集成点

## 测试计划 (Testing Plan)

1. **单元测试**: 每个队列实现的基本功能测试
2. **集成测试**: 描述符序列化和反序列化测试
3. **性能测试**: 不同队列类型的吞吐量和延迟对比
4. **压力测试**: 高并发和大数据量场景测试
5. **故障测试**: 网络中断、进程崩溃恢复测试

---

**分配给**: @开发团队
**标签**: `enhancement`, `communication`, `architecture`  
**里程碑**: v0.2.0
**优先级**: High
