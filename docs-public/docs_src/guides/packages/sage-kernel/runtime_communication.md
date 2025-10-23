# Kernel Runtime Communication

本页总结运行时通信层的真实实现，涵盖队列描述符、路由策略以及它们与任务/服务的衔接方式。源码位于 `packages/sage-kernel/src/sage/kernel/runtime/communication`。

## 模块概览

```
communication/
├── README.md
├── queue_descriptor/
│   ├── base_queue_descriptor.py
│   ├── python_queue_descriptor.py
│   ├── ray_queue_descriptor.py
│   └── rpc_queue_descriptor.py
└── router/
    ├── router.py
    ├── packet.py
    └── connection.py
```

### 队列描述符（QueueDescriptor）

| 描述符 | 说明 |
| --- | --- |
| `PythonQueueDescriptor` | 默认实现，懒加载 `queue.Queue`，适合本地线程内通信。`maxsize` 可配置，首次访问前可序列化。 |
| `RayQueueDescriptor` | 通过命名的 `RayQueueManager` Actor 共享 `ray.util.Queue`。若运行在 Ray local mode，会回退到本地 `queue.Queue`。需要在使用前 `ray.init()`。 |
| `RPCQueueDescriptor` | 预留的远端队列描述符，依赖尚未随仓库发布的 `communication.rpc.rpc_queue.RPCQueue`，目前使用会抛出 `RuntimeError`。 |

公共基类 `BaseQueueDescriptor` 负责：

- 提供统一的队列接口（`put`/`get`/`qsize` 等）并转发到实际队列。
- 懒加载与缓存管理（`clear_cache()`、`trim()`）。
- 序列化方法 `to_dict()` / `to_json()` / `to_serializable_descriptor()`。
- `clone()` 创建同类型的新描述符（不带队列实例）。

### 路由层（Router）

- `Packet`：封装 `payload`、`input_index`、`partition_key`、`partition_strategy`，用于数据传递。
- `StopSignal`：流水线停止时传播的事件，记录来源 `source` 与时间戳。
- `Connection`：保存下游节点名称、并行索引以及队列描述符；`get_buffer_load()` 可读取底层队列的 `qsize/maxsize` 估算负载。
- `BaseRouter`：由 `TaskContext` 实例化并持有下游连接，提供三种路由策略：
  - **Round-Robin**：默认策略，沿广播组轮询每个并行实例。
  - **Hash**：当 `partition_strategy == "hash"` 且携带 `partition_key` 时，根据哈希值选择目标。
  - **Broadcast**：当策略为 `"broadcast"` 时，对该组所有连接发送副本。

## 生命周期与数据流

1. JobManager 编译执行图，生成输入/输出/服务队列描述符，并将它们绑定到节点上下文。
2. `Dispatcher.submit()` 创建任务和服务实例，`TaskContext`/`ServiceContext` 保存相关描述符。
3. 任务运行时通过 `ctx.send_packet()` 调用 `BaseRouter.send()`，从而根据策略把 `Packet` 写入目标队列。
4. 服务调用依赖相同的描述符：`ServiceManager` 通过 `service_qds` 找到 `QueueDescriptor`，写入请求并监听响应队列。
5. 批处理作业结束时，下游收到 `StopSignal`，`TaskContext.send_stop_signal()` 将其沿图传播，Dispatcher 根据收到的信号数量触发清理流程。

## 调试建议

- **查看路由拓扑**：`TaskContext.get_routing_info()` 会返回每个广播组的连接、目标名称与队列 ID。
- **队列占用**：`Connection.get_buffer_load()` 能在日志中反映队列占用率（仅对支持 `qsize/maxsize` 的队列准确）。
- **Ray 依赖**：若使用 `RayQueueDescriptor`，请确认运行环境已安装 `ray` 并在 Dispatcher 构造前调用 `ray.init()`。本地模式会自动回退到简单队列，但行为与真实分布式队列略有不同。
- **RPC 描述符**：由于缺少 `RPCQueue` 实现，使用该描述符时 `_create_queue_instance()` 会抛错，可在补齐网络层后再启用。

## 相关文档

- `runtime_tasks.md`：任务与上下文的整体执行流程。
- `runtime_services.md`：Pipeline-as-Service 与服务队列的使用方式。
- `architecture.md`：内核层级视图与模块关系。
