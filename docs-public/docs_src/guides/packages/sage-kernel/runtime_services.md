# Kernel Runtime Services

流水线在提交时会自动把注册的服务转换成运行时任务，形成 “Pipeline as Service” 模式。本页根据
`packages/sage-kernel/src/sage/kernel/runtime/service` 与 `proxy` 模块的实现，说明当前可用的能力。

## 目录速览

- `base_service_task.py`：公共的服务任务基类，包含请求队列监听、调用调度、响应回写与资源清理。
- `local_service_task.py`：默认的本地实现，基于 Python 标准队列。
- `ray_service_task.py`：可选的 Ray Actor 封装，配合 `RemoteEnvironment` 使用。
- `service_caller.py`：`ServiceManager`，统一同步/异步调用、响应匹配、Future 管理与队列缓存。
- `proxy/proxy_manager.py`：运行时上下文内的轻量代理，为 `call_service` / `call_service_async` 提供缓存和默认超时时间。

## 生命周期概览

1. **注册**：`BaseEnvironment.register_service("name", ServiceClass)` 保存到环境的 `service_factories`。
1. **编译**：JobManager 构建 `ExecutionGraph` 时，为每个服务生成 `ServiceContext`，包含请求队列/响应队列描述符。
1. **部署**：Dispatcher 在 `submit()` 中调用 `service_task_factory.create_service_task(ctx)`，得到
   `BaseServiceTask` 子类实例并启动监听线程。
1. **调用**：算子或脚本通过 `TaskContext.call_service` → `ProxyManager.call_sync` 发送请求，`ServiceManager`
   负责写入服务队列并等待结果。
1. **执行**：`BaseServiceTask` 从请求队列取出消息，调用目标方法（默认 `process`），将结果放入响应队列。
1. **清理**：Dispatcher 停止任务时会调用 `service_task.stop()/cleanup()`，同时重置 Proxy 缓存并关闭队列。

## 关键组件

### BaseServiceTask

- 构造时使用 `ServiceFactory.create_service(ctx)` 实例化用户服务，并注入 `ServiceContext`。
- 启动独立的监听线程 `_queue_listener_loop`，从请求队列读取 `dict` 结构的请求：
  ```python
  {
      "request_id": str,
      "method_name": "process" | 自定义,
      "args": tuple,
      "kwargs": dict,
      "response_queue": queue.Queue 实例,
      "timeout": float,
  }
  ```
- 调用 `call_method` 执行服务逻辑，构造包含 `success/result/error/execution_time` 的响应并写回指定队列。
- 提供 `start_running()`、`stop()`、`cleanup()` 等生命周期钩子，保证监听线程与队列被正确关闭。

### Local vs. Ray Service Task

| 功能点   | `LocalServiceTask`      | `RayServiceTask`                      |
| -------- | ----------------------- | ------------------------------------- |
| 队列实现 | Python `queue.Queue`    | Ray 队列/Actor                        |
| 服务实例 | 直接在当前进程持有      | 运行在 Ray Actor 内，通过远程调用执行 |
| 适用场景 | 默认模式、开发/单机部署 | 远程平台或需要跨节点伸缩时            |

Ray 模式会在 Dispatcher 初始化时调用 `ensure_ray_initialized()`，并用 `ActorWrapper` 托管服务任务；当前仓库仍以本地模式为主。

### ServiceManager & ProxyManager

- `ServiceManager.call_sync()` 负责：
  1. 获取/缓存服务请求队列（来自 `TaskContext.service_qds` 或传入的描述符）。
  1. 构造请求并写入队列。
  1. 在单独的 listener 线程里消费响应队列，将结果写入 `_request_results`，唤醒等待的事件。
  1. 超时时抛出 `TimeoutError`，失败时抛出 `RuntimeError`。
- `call_async()` 简单地把同步调用包进线程池返回 `Future`。
- `ProxyManager` 内置在 `BaseRuntimeContext`，提供缓存和默认超时：
  ```python
  result = ctx.call_service("profile", user_id)
  future = ctx.call_service_async("model", payload, timeout=15)
  ```
- 首次调用会读取 `context.service_qds` 的队列描述符，并缓存在 Proxy 内，后续调用不需要再次触达 JobManager。

## 与执行图的集成

- 服务请求队列、响应队列、日志记录器全部由 `ServiceContext` 统一提供；`BaseServiceTask` 不创建新的队列，而是复用 Graph 上的描述符。
- Task 侧通过 `TaskContext.response_qd` 接收响应，确保一个算子可以发起多个并发请求。
- 停止信号：批处理场景下，Dispatcher 在所有计算任务结束后会调用
  `_cleanup_services_after_batch_completion()`，主动停止服务线程，避免遗留后台线程。

## 使用示例

```python
from sage.core.api import LocalEnvironment, MapFunction

env = LocalEnvironment("demo")


@env.register_service("profile")
class ProfileService:
    def process(self, user_id: str):
        return {"user_id": user_id, "score": 0.9}


class Enrich(MapFunction):
    def execute(self, record):
        profile = self.call_service("profile", record["user_id"])
        return {**record, "profile": profile}


env.from_batch([{"user_id": "42"}]).map(Enrich()).sink(print)
env.submit()
```

## 当前特性与局限

- ✅ 同步/异步调用、超时控制、请求 ID 匹配、Future 支持。
- ✅ 可复用的 Proxy 缓存，避免重复查询服务队列。
- ✅ 支持在算子内部、独立脚本（通过 sugar API）进行服务调用。
- ⚠️ 监控、健康检查、自动重试等功能暂无正式实现；如需这些能力需自行扩展。
- ⚠️ Ray 模式仍在演进中，生产部署前需要补充持久化和容错策略。

## 延伸阅读

- `packages/sage-kernel/src/sage/kernel/runtime/service/README.md`
- `packages/sage-kernel/src/sage/kernel/runtime/proxy/proxy_manager.py`
- `guides/packages/sage-kernel/runtime_tasks.md`
- `guides/packages/sage-kernel/runtime_communication.md`
- `guides/packages/sage-kernel/architecture.md`
