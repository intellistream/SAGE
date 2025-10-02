# SAGE Runtime

`sage.kernel.runtime` 将 JobManager 编译出的执行图落实到具体的任务、服务和通信资源上。代码完全在 Python 中实现，默认在本地进程内运行，同时保留 Ray 作为可选的远端执行后端。

## 模块总览

```
runtime/
├── dispatcher.py           # 提交执行图、创建任务/服务并负责生命周期
├── task/                   # BaseTask + 本地/Ray 任务实现
├── service/                # ServiceTask 基类、本地/Ray 服务实现、ServiceManager
├── proxy/                  # ProxyManager，封装 ServiceManager + 队列缓存
├── context/                # TaskContext / ServiceContext / BaseRuntimeContext
├── communication/          # 队列描述符、Router、Packet 定义
└── factory/                # 运行时构建 Operator/Task/Service 的工厂
```

核心职责：

1. **Dispatcher**：根据执行图生成任务、服务实例，并统一启动/停止；处理 stop signal、日志、Ray 初始化等。
2. **Task 子系统**：`BaseTask` 负责工作线程循环、从输入队列取包、调用算子、传播停止信号；`local_task.py` 在进程内运行任务，`ray_task.py` 则包装 Ray actor。
3. **Service 子系统**：`BaseServiceTask` 监听请求队列、调用用户服务对象、把结果写回响应队列；`local_service_task.py` 使用标准队列，`ray_service_task.py` 通过 Ray actor 托管服务；`service_caller.py` 的 `ServiceManager` 负责请求/响应匹配与 Future 管理。
4. **Proxy 层**：`ProxyManager` 嵌入到所有 `BaseRuntimeContext`，为 `call_service` / `call_service_async` 提供缓存和统一超时时间。
5. **Runtime Context**：`TaskContext`/`ServiceContext` 封装日志、队列描述符、下游路由、stop 信号回传、服务队列映射等运行信息，暴露给任务与函数实例。
6. **Communication**：`queue_descriptor` 提供可序列化的队列描述；`router` 负责 Round-Robin/Hash/Broadcast 路由以及 stop signal 广播。

## 执行流程速览

1. **Dispatcher.submit**
  - 遍历 `ExecutionGraph.service_nodes`，通过 `service_task_factory.create_service_task(ctx)` 创建服务任务，并保存到 `Dispatcher.services`。
  - 遍历 `ExecutionGraph.nodes`，使用 `task_factory.create_task` 创建任务实例，注入 `TaskContext`。
2. **Dispatcher.start**
  - 先启动所有服务任务（确保请求队列监听线程已运行），再启动每个任务的工作线程。
3. **任务循环** (`BaseTask._worker_loop`)
  - Source 节点直接调用 `operator.receive_packet`；其他节点从 `input_qd.get()` 取包。
  - 收到数据时调用算子处理；收到 `StopSignal` 时根据算子类型执行自定义收尾（Join/Sink 等）并向下游传播，同时通知 JobManager。
4. **服务调用**
  - 任意运行时函数通过 `TaskContext.call_service(...)` → `ProxyManager.call_sync` 发送请求。
  - `ServiceManager` 缓存服务队列，构造请求并写入队列，同时监听响应队列把结果放入 Future。
  - `BaseServiceTask` 从请求队列取出消息，调用目标方法（默认 `process`），把结果写回响应队列。
5. **停止与清理**
  - Dispatcher 收到所有停止信号或显式 `stop()` 时，逐个停止任务/服务，等待线程退出，并调用 `cleanup()` 释放队列资源、关闭 Ray actor。

## 关键交互

- **QueueDescriptor**：ExecutionGraph 在 JobManager 阶段构建所有队列描述符并写入 `TaskContext`/`ServiceContext`，运行时只需 `queue_descriptor.get_queue()` 即可拿到真实队列。
- **Router**：`TaskContext.send_packet` 封装路由行为，算子只依赖 `ctx.send_packet` 而无需感知通信细节。
- **Stop Signal**：`StopSignal` 在任务和服务之间沿着执行图传播，Dispatcher 用来判断作业是否完成，并触发服务补充清理。
- **Ray 支持**：当环境的 `platform == "remote"` 时，Dispatcher 会保证 Ray 初始化，并把任务/服务包装成 `ActorWrapper` 以便在 Ray 上运行。

## 扩展点

- **自定义任务实现**：实现新的 `TaskFactory` 或扩展 `BaseTask`，可引入其他执行后端（如多进程、容器）。
- **新的通信机制**：通过自定义 `QueueDescriptor` 或 `Connection`，即可接入不同的消息队列实现。
- **服务拦截器**：`ServiceManager` 目前集中处理请求/响应匹配，可在此添加指标、拦截器或故障注入逻辑。

参考文档：

- `docs-public/docs_src/kernel/architecture.md`
- `docs-public/docs_src/kernel/runtime_tasks.md`
- `docs-public/docs_src/kernel/runtime_services.md`
- `docs-public/docs_src/kernel/runtime_communication.md`