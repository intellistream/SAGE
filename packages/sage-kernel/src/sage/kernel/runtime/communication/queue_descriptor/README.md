# Queue Descriptor 概览

`queue_descriptor` 子包为运行时通信提供统一的描述符抽象。实际实现侧重于 Python 标准队列和 Ray 队列，另有一个尚未完整落地的 RPC 描述符。

当前可用的类：

| 类 | 用途 | 备注 |
| --- | --- | --- |
| `BaseQueueDescriptor` | 抽象基类，定义 `queue_type`、`queue_instance`、序列化接口。 | 不直接实例化。|
| `PythonQueueDescriptor` | 懒加载 `queue.Queue`，支持配置 `maxsize`。 | 适合本地线程通信；`use_multiprocessing` 字段目前未启用。|
| `RayQueueDescriptor` | 通过全局 `RayQueueManager` Actor 管理队列，分布式模式使用 `ray.util.Queue`，本地模式回退到 `queue.Queue`。 | 需要提前 `ray.init()`；如果 Ray 不可用会抛异常。|
| `RPCQueueDescriptor` | 计划对接远程 RPC 队列。 | 依赖 `communication.rpc.rpc_queue.RPCQueue`，仓库未包含该实现。|

## 常用模式

### 创建本地队列描述符

```python
from sage.kernel.runtime.communication.queue_descriptor import PythonQueueDescriptor

qd = PythonQueueDescriptor(maxsize=1024)
queue = qd.queue_instance  # 第一次访问时创建 queue.Queue
queue.put({"payload": 1})
```

### 创建 Ray 队列描述符

```python
import ray
from sage.kernel.runtime.communication.queue_descriptor import RayQueueDescriptor

ray.init(ignore_reinit_error=True)
qd = RayQueueDescriptor(maxsize=1000)
queue = qd.queue_instance  # 返回 RayQueueProxy，内部通过 Ray Actor 访问队列
queue.put({"event": "start"})
```

### 序列化与克隆

```python
qd = PythonQueueDescriptor(maxsize=10)
descriptor_data = qd.to_dict()  # 仅在队列尚未初始化时可序列化

copy_qd = qd.clone()
copy_qd.clear_cache()  # 确保新副本不携带旧的队列实例
```

## 注意事项

- **懒加载**：所有描述符都会在首次访问 `queue_instance` 时创建实际队列。若需跨进程传输，请在另一端重新实例化或调用 `clear_cache()` 清除缓存。
- **序列化限制**：当底层队列已经创建时，`can_serialize` 会返回 `False`。可以使用 `to_serializable_descriptor()` 获取不包含实例的副本。
- **Ray 管理器**：`RayQueueDescriptor` 将命名为 `global_ray_queue_manager` 的 Actor 作为单例，如果并发创建，内部已带重试逻辑；退出前无需手动清理。
- **RPC 描述符状态**：由于缺少 `RPCQueue` 的具体实现，构造 `RPCQueueDescriptor` 会在 `_create_queue_instance` 中抛出 `RuntimeError`。在补齐依赖前请避免使用。

## 与执行图的关系

JobManager 在构建 `ExecutionGraph` 时，会为每个任务节点、服务节点创建适当的队列描述符。运行时由 `TaskContext` / `ServiceContext` 维护这些描述符，任务和服务通过 `queue_descriptor.get_queue()` 获取真正的队列对象，实现数据流和服务请求/响应。

更多背景可参考：

- `../README.md`
- `../../runtime_tasks.md`（公开文档）
- `../../runtime_services.md`（公开文档）
