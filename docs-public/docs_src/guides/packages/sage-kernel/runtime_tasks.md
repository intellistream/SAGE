# Kernel Runtime Tasks

SAGE 的运行时任务由 `packages/sage-kernel/src/sage/kernel/runtime/task` 与 `context`、`communication` 模块共同实现。本文基于当前源码梳理任务执行、消息传递与停止信号的真实行为，帮助你在调试与扩展时快速定位关键逻辑。

## 目录结构速览

- `task/base_task.py`：通用任务循环、线程管理、停止信号处理。
- `task/local_task.py`：默认的本地任务实现，直接复用 `BaseTask`。
- `task/ray_task.py`：Ray Actor 版本的任务封装，目前作为远程环境的实验性后端。
- `context/task_context.py`：为任务、算子、函数提供统一的运行时上下文（日志、队列、路由、服务调用等）。
- `communication/queue_descriptor/`：可序列化的队列描述符，运行时通过它们获取真实队列实例。
- `communication/router/`：`BaseRouter` 封装下游连接与路由策略（Round-Robin、Hash、Broadcast）。

## 任务生命周期

1. **构建上下文**：JobManager 在编译 `ExecutionGraph` 时，为每个节点生成 `TaskContext`，注入输入队列、下游连接、服务队列以及日志路径等信息。
2. **创建任务**：`Dispatcher.submit()` 调用每个节点的 `task_factory.create_task(name, ctx)`，返回 `BaseTask` 子类实例并存入 `Dispatcher.tasks`。
3. **启动**：`Dispatcher.start()` 依次执行 `task.start_running()`，为每个任务创建后台线程并清除停止事件。
4. **运行循环**：`BaseTask._worker_loop()` 不断从输入队列拉取 `Packet`，交给算子（`operator.receive_packet`）处理。Source 节点没有输入队列，会直接触发算子生成数据。
5. **停止处理**：当收到 `StopSignal` 时，根据算子类型（Sink、Join、普通中间算子）执行专门的收尾逻辑，并通过 `TaskContext.send_stop_signal_back()` 通知 JobManager。
6. **清理**：作业结束或手动停止时，`Dispatcher.cleanup()` 会调用任务的 `cleanup()`，关闭队列描述符、清除上下文并回收线程。

## TaskContext 能力概览

`TaskContext` 位于 `context/task_context.py`，是算子与运行时之间的主要桥梁：

- **日志**：懒加载 `CustomLogger`，日志文件写入环境目录；控制台等级继承自 `Environment`。
- **队列描述符**：
  - `input_qd`：上游数据输入队列（`queue_instance` 懒取）。
  - `downstream_groups`：路由所需的连接信息列表。
  - `response_qd` 与 `service_qds`：服务调用时使用的响应/请求队列描述符。
- **服务调用**：继承自 `BaseRuntimeContext` 的 `call_service` / `call_service_async`，内部持有 `ProxyManager`，自动缓存服务队列。
- **路由接口**：通过 `send_packet()` 和 `send_stop_signal()` 隐藏 `BaseRouter` 细节，算子只需调用上下文方法即可转发消息。
- **停止信号回传**：`send_stop_signal_back(node_name)` 会优先尝试本地 JobManager 引用，否则通过 `JobManagerClient` 发送 TCP 请求。

## 路由与数据包

`communication/router/router.py` 中的 `BaseRouter` 根据 `Packet` 的分区策略选择目标：

- **Round-Robin**（默认）：在同一广播组内均匀分发。
- **Hash 分区**：使用 `packet.partition_key` 对并行度取模。
- **Broadcast**：向所有并行实例发送克隆包。

`Packet` 对象还会携带 `input_index`，用于标记下游算子的输入口，方便多输入算子处理不同来源的数据。

## 停止信号与批处理结束

- `StopSignal` 通过路由在执行图中传播。
- 中间算子会立即转发信号并调用 `ctx.send_stop_signal_back()`。
- `JoinOperator` / `SinkOperator` 有定制逻辑：
  - Join 会统计来自不同上游的停止信号，全部到齐后再继续传播。
  - Sink 会执行 `_drain_inflight_messages()`，确保队列中剩余数据被消费后再最终停止。
- `BaseTask.stop()` 会设置 `ctx.stop_event`，线程循环检测该事件来退出。

Dispatcher 在收到所有必需的停止信号后：

1. 标记作业完成。
2. 对批处理作业，调用 `_cleanup_services_after_batch_completion()`，停止所有服务任务。
3. 触发任务与服务的 `cleanup()`，释放队列和上下文资源。

## 常见扩展点

- **自定义任务行为**：实现新的 `TaskFactory` 或扩展 `BaseTask` 以支持多进程、容器或其他调度器。
- **路由策略**：在 `BaseRouter` 上添加新的 `partition_strategy`，例如按负载或自定义键。
- **指标采集**：
  - `BaseTask` 暴露 `_processed_count` 等计数器，可在自定义子类中刷新指标。
  - `TaskContext.get_routing_info()` 可返回下游连接和队列 ID，方便可视化。
- **停止控制**：通过覆盖 `BaseTask._handle_sink_stop_signal` 或在算子中添加 `handle_stop_signal`，实现更复杂的收尾策略。

## 调试建议

- 检查环境目录下的 `Dispatcher.log`、`Error.log` 以及每个任务的 `<task>_debug.log`、`<task>_info.log`。
- 使用 `TaskContext.router.get_connections_info()` 查看当前的下游连接和队列。
- 若服务调用阻塞，确认 `TaskContext.response_qd` 与 `ServiceManager` 是否指向同一个响应队列实例。
- 开发 Ray 模式时，确保 `ensure_ray_initialized()` 在 Dispatcher 构造阶段被调用，并确认 `ActorWrapper` 的远程方法已注册。

## 关联资源

- 运行时主线文档：`docs-public/docs_src/kernel/architecture.md`
- 服务化调用详解：`docs-public/docs_src/kernel/runtime_services.md`
- 通信层细节：`docs-public/docs_src/kernel/runtime_communication.md`
- 源码目录：`packages/sage-kernel/src/sage/kernel/runtime`
