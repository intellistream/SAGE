# SAGE Kernel 架构概览

SAGE Kernel 完全由 Python 实现，主要分布在 `packages/sage-kernel/src/sage` 目录下。框架以“声明式 API → 执行图编译 → JobManager 调度 → Runtime 执行”的流程组织代码。下面的内容全部可在仓库中对应的模块找到实现。

## 分层全景

```
┌─────────────────────────┐
│ 用户代码 (examples/, 应用) │
├─────────────────────────┤
│ sage.core.api           │ 公开 API：Environment / DataStream / Function
├─────────────────────────┤
│ sage.core.transformation│ 计算图节点、算子定义
│ sage.core.operator      │ (进行中) operator 封装
├─────────────────────────┤
│ sage.kernel.jobmanager  │ 执行图编译、作业生命周期
├─────────────────────────┤
│ sage.kernel.runtime     │ Dispatcher、Task、Service、Proxy
└─────────────────────────┘
```

## `sage.core`：声明式 API 与算子描述

目录：`packages/sage-kernel/src/sage/core`

- **`api/`**：向用户暴露的编程接口。
  - `base_environment.py` 定义 `BaseEnvironment` 以及 `LocalEnvironment`/`RemoteEnvironment` 的公共行为。
  - `datastream.py`、`connected_streams.py` 描述数据流以及多流连接算子的链式 API。
  - `function/` 下的基类（`MapFunction`、`FlatMapFunction`、`SinkFunction`、`KeyByFunction`、`BaseCoMapFunction`、`BaseJoinFunction` 等）约束算子代码需要实现的 `execute`/`mapN` 方法。
- **`transformation/`**：每个链式调用都会生成一个 `BaseTransformation` 子类实例（`MapTransformation`、`FilterTransformation`、`SinkTransformation` 等），用于构建执行图节点。
- **`factory/`**：`ServiceFactory` 将用户注册的服务描述为可序列化的构造信息，提交时注入 JobManager。
- **`communication/`** 与 **`operator/`**：提供运行时通信、算子包装等基础设施，随着 runtime 改造逐步完善。

小结：`sage.core` 负责“描述”流水线，不直接执行任务。所有 API 都以 Python 对象存在，方便 `JobManager` 序列化后传递给执行端。

## `sage.kernel.jobmanager`：执行图编译与生命周期管理

目录：`packages/sage-kernel/src/sage/kernel/jobmanager`

- **`job_manager.py`**：`JobManager` 单例，负责
  1. 接收 `Environment`，生成作业 UUID；
  2. 调用 `compiler/execution_graph.py` 把 `env.pipeline` 转换成执行图；
  3. 创建 `Dispatcher` 并提交运行；
  4. 维护 `jobs` 字典、`pause_job` 等运维操作。
- **`job_manager_server.py`** 与 **`jobmanager_client.py`**：提供可选的 TCP Daemon，支持 `RemoteEnvironment` 通过网络提交作业并获取状态。
- **`compiler/`**：`ExecutionGraph`、`logical_plan`、`physical_plan` 等组件将 `Transformation` 链编译为运行时可消费的节点描述。
- **`job_info.py`**：记录作业状态、是否启用 `autostop`、关联的 `Dispatcher` 等信息。

小结：JobManager 层面没有 C++ 依赖，也未引入外部调度器。一切控制逻辑都在 `job_manager.py` 及其子模块里。

## `sage.kernel.runtime`：Dispatcher 与运行时服务

目录：`packages/sage-kernel/src/sage/kernel/runtime`

- **`dispatcher.py`**：根据执行图创建任务、管理生命周期、处理停止/暂停。
- **`task/`**：实现任务抽象以及本地任务执行循环。
- **`service/`**：`service_caller.py`、`service_worker.py` 等模块用于处理服务化算子，负责队列监听、请求/响应调度。
- **`proxy/`**：`proxy_manager.py` 为 `TaskContext` 提供 `call_service`/`call_service_async`，并缓存服务队列描述符。
- **`context/`**：`task_context.py`、`base_context.py` 把日志、服务代理、配置注入到函数实例中。
- **`communication/`**：维护队列、管道和消息分发；当前实现主要面向本地进程通信。

小结：Runtime 接管编译好的执行图，启动任务进程/线程，负责数据通路与服务调用，最终驱动用户实现的函数运行。

## 流水线生命周期

1. **构建管道** (`sage.core.api`)
   - 用户调用 `env.from_batch(...).map(...).sink(...)`，每一步都会把新的 `Transformation` 附加到 `env.pipeline` 列表。

2. **提交执行** (`JobManager`)
   - `env.submit(autostop=True)` → `JobManager.submit_job` 创建 UUID，编译执行图，实例化 `Dispatcher`。

3. **任务部署** (`Dispatcher`)
   - 为每个算子节点创建任务对象；为注册的服务创建服务任务；连接消息队列。

4. **运行与监控**
   - 任务循环从上游队列读取数据，调用用户函数（`BaseFunction.execute`/`mapN`），把结果写入下游。
   - 服务化调用通过 `ProxyManager` → `ServiceManager` 走消息队列，支持同步/异步调用、超时控制。

5. **收尾**
   - 对于批处理作业，函数返回 `None` 或 `FutureTransformation` 被填充后会触发停止信号。
   - `autostop=True` 时，`_wait_for_completion()` 轮询 JobManager 状态并在管道结束后触发清理。

## 服务注册与调用机制

相关代码：

- `sage.core.api.base_environment.register_service`
- `sage.core.api.function.base_function.BaseFunction.call_service`
- `sage.kernel.runtime.proxy.proxy_manager.ProxyManager`
- `sage.kernel.runtime.service.service_caller.ServiceManager`

设计要点：

1. **服务注册即部署**：`register_service("cache", ServiceClass)` 会把构造信息放入 `env.service_factories`，提交时由 JobManager 插入执行图并创建对应服务任务。
2. **统一调用接口**：无论在算子内部还是在独立脚本中，都通过 `call_service`/`call_service_async` 访问服务。默认方法名为 `process`，也可以显式传入 `method`。
3. **队列描述符缓存**：`ProxyManager` 在首次调用时保留服务描述符，后续调用避免重复查询控制面，提升吞吐。
4. **超时与 Future**：同步调用允许自定义超时；异步调用返回可等待的 Future 对象。

示例：

```python
class Enrich(MapFunction):
    def execute(self, data):
        profile = self.call_service("user_profile", data["user_id"])
        return {**data, "profile": profile}
```

## 设计原则（与实现对齐）

- **声明式 + 延迟执行**：`DataStream` 只负责描述算子链，真正的执行延后到 `env.submit()`。
- **纯 Python、易追踪**：没有额外的 C++ 内核或 CLI 依赖，定位问题时可直接在源码中查找。
- **单实例 JobManager**：`JobManager` 作为单例保障提交入口唯一，`RemoteEnvironment` 通过 TCP 客户端复用相同逻辑。
- **服务化优先**：运行时提供统一的服务调用通道，让“流水线调用流水线”成为常规操作。
- **可扩展执行后端**：`task/` 和 `communication/` 中保留了针对多进程、Ray 等模式的扩展点，通过新增 Task 实现即可接入新的后端。

以上就是当前仓库中 SAGE Kernel 的实际结构。阅读时建议结合相应模块的 README 与源码一起查看，能快速定位到具体的实现细节。
