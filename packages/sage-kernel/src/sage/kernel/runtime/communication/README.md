# Communication 模块

`packages/sage-kernel/src/sage/kernel/runtime/communication` 收拢了运行时的数据通路：

- `queue_descriptor/` 定义可序列化的队列描述符，执行图编译阶段会为节点和服务生成这些描述符并挂载到 `TaskContext` / `ServiceContext`。
- `router/` 提供 `BaseRouter`、`Connection`、`Packet`、`StopSignal`，在任务运行时负责选择下游队列并写入数据包。

以下内容基于当前仓库中的实现，不包含文档中未出现的“共享内存队列”“自动负载均衡”等尚未落地的特性。

## 队列描述符一览

| 类名 | 对应文件 | 说明 |
| --- | --- | --- |
| `PythonQueueDescriptor` | `python_queue_descriptor.py` | 默认实现，懒加载 `queue.Queue`，适合本地线程内通信。`maxsize` 可配置，未调用前可序列化。|
| `RayQueueDescriptor` | `ray_queue_descriptor.py` | 在 Ray 环境下通过命名 `RayQueueManager` Actor 共享队列；本地模式下退化为 `SimpleTestQueue`。需要在调用前确保 Ray 已初始化。|
| `RPCQueueDescriptor` | `rpc_queue_descriptor.py` | 预留的远程队列描述符，依赖尚未随仓库发布的 `communication.rpc.rpc_queue`，目前不建议在生产中启用。|

公共基类 `BaseQueueDescriptor` 提供：

- 队列接口代理：`put` / `get` / `qsize` / `empty` 等调用会转发给实际队列对象。
- 懒加载：第一次访问 `queue_instance` 时才创建底层队列，可通过 `clear_cache()` 重置。
- 序列化：`to_dict()` / `to_json()` 仅包含可序列化字段；若需跨进程传输，请在初始化前调用，或使用 `to_serializable_descriptor()` 去除队列实例。
- 克隆：`clone()` 会生成同类型的新描述符，常用于为下游任务分配独立队列 ID。

## 路由层核心

- `Packet`：数据包载体，携带 `payload`、`input_index` 以及可选的 `partition_key` 与 `partition_strategy`。支持 `inherit_partition_info()`、`update_key()` 等便捷方法。
- `StopSignal`：停止信号，沿执行图传播，用于批处理作业的收尾。
- `Connection`：封装下游节点的 `queue_descriptor`、并行度索引和输入端口。包含基础的负载记录字段，但当前实现仅用于日志/调试，没有自动调度逻辑。
- `BaseRouter`：由 `TaskContext` 在运行时实例化。核心能力包括：
  - Round-Robin：所有未指定策略的数据包按广播组轮询发送。
  - Hash：当 `Packet.partition_strategy == "hash"` 且携带 `partition_key` 时，根据哈希值选择并行实例。
  - Broadcast：当策略为 `"broadcast"` 时，对同一广播组所有连接逐一写入。
  - Stop 信号广播：`send_stop_signal()` 将 `StopSignal` 投递给所有下游队列。

### 与任务执行的关系

1. JobManager 编译执行图时，为每个节点生成输入队列描述符和下游连接映射。
2. `TaskContext` 保存这些信息并暴露 `send_packet()` / `send_stop_signal()` API，算子层只需调用上下文接口即可发送数据。
3. 运行时由 `Dispatcher` 启动任务线程，`BaseTask` 从 `input_qd` 读取 `Packet`，处理后通过 `ctx.send_packet()` 写入下游队列。
4. 停止信号传播依赖相同的路由机制，最终由 Dispatcher 汇总并触发资源清理。

## 调试与注意事项

- **队列实例为空**：`PythonQueueDescriptor` 在调用 `queue_instance` 前不可序列化，跨进程传递时请在另一端重新实例化或调用 `clear_cache()`。
- **Ray 模式**：确保 `ray.init()` 已运行，否则 `RayQueueDescriptor` 会因找不到全局管理器而抛错；本地单机测试时会自动回退到 `SimpleTestQueue`。
- **RPC 描述符**：仓库中未包含 `RPCQueue` 的实现，如需远程队列请自行补全或避免使用该类。
- **负载信息**：`Connection.get_buffer_load()` 仅在底层队列支持 `qsize/maxsize` 时返回有效值，当前版本没有根据该指标自动调整速率。

## 关联文档

- `docs-public/docs_src/kernel/runtime_tasks.md`
- `docs-public/docs_src/kernel/runtime_services.md`
- `docs-public/docs_src/kernel/runtime_communication.md`
