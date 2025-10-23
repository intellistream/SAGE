## SAGE Kernel 总览

SAGE Kernel 是 SAGE 平台中负责构建与提交数据处理流水线的运行时核心。它提供一组轻量级的 Python API，用于描述数据来源、转换算子和服务调用，并将这些描述交给本地或远程的 JobManager 执行。

本章节聚焦于**源码中已经实现的能力**，帮助你快速定位可用的编程接口并避免依赖尚未落地的特性。

## 核心组成

- **Environment**：包装运行配置并维护流水线中产生的所有 `Transformation`。
- **DataStream**：描述单输入算子链，提供 `map`、`filter`、`flatmap`、`keyby`、`sink` 等操作。
- **ConnectedStreams**：在多个 `DataStream` 之间建立逻辑连接以支持 `comap`、`join` 等多流算子。
- **Function 基类族**：约束算子实现所需的方法（例如 `MapFunction.execute`）。

所有 API 都位于 `packages/sage-kernel/src/sage/core/api` 目录下，可直接对照源码了解行为。

## 执行模型

1. **创建环境**：实例化 `LocalEnvironment` 或 `RemoteEnvironment`。
2. **声明数据源**：调用 `from_batch`、`from_collection`、`from_kafka_source` 等方法获取 `DataStream`。
3. **链接转换算子**：在 `DataStream` 上调用 `map`、`filter`、`flatmap`、`keyby` 等操作。
4. **选择输出方式**：使用 `sink`/`print` 或将多个流通过 `connect()`/`comap()` 组合。
5. **提交运行**：调用 `env.submit(autostop=True)` 将流水线交给 JobManager 执行。

### 最小化示例

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("numbers-demo")

stream = (
    env.from_batch([1, 2, 3, 4, 5])
       .map(lambda value: value * 2)
       .filter(lambda value: value > 5)
)

stream.print(prefix="[result]")

# autostop=True 会等待批任务结束并清理资源
env.submit(autostop=True)
```

以上代码与 `packages/sage-kernel/src/sage/core/api` 中的实现完全一致：

- `from_batch` 使用 `BatchTransformation`，每次调用底层函数的 `execute`，返回 `None` 时结束批处理；
- `map`/`filter` 自动将普通 `callable` 包装成匿名 `BaseFunction` 子类（参见 `lambda_function.wrap_lambda`）；
- `print` 是 `sink(PrintSink, ...)` 的便捷写法，底层使用 `sage.libs.io_utils.sink.PrintSink`。

## 数据源能力

`BaseEnvironment` 当前提供的入口包括：

| 方法 | 说明 |
| ---- | ---- |
| `from_batch(source)` | 批量数据迭代器，支持 `BaseFunction` 子类、`list/tuple` 以及任意可迭代对象。 |
| `from_collection(function)` | 保留的历史 API，内部同样走批处理路径。 |
| `from_source(function)` | 适合实现自定义实时数据源，`function` 通常继承 `SourceFunction`。 |
| `from_kafka_source(...)` | 使用 `KafkaSourceFunction` 构建消费任务，要求传入 bootstrap、topic、group 等参数。 |
| `from_future(name)` | 声明一个占位流，稍后可以通过 `DataStream.fill_future` 建立反馈边。 |

所有方法都会返回 `DataStream` 对象并把对应的 `Transformation` 累加到 `env.pipeline`。因此，在提交前可以多次组合重用，无需立即执行。

## 转换与终端算子

`DataStream` 支持以下算子（位于 `datastream.py`）：

- `map(function, *, parallelism=None)`
- `filter(function, *, parallelism=None)`
- `flatmap(function, *, parallelism=None)`
- `keyby(function, strategy="hash", *, parallelism=None)`
- `sink(function, *, parallelism=None)`
- `print(prefix="", separator=" | ", colored=True)` —— `sink(PrintSink, ...)` 的语法糖
- `connect(other)` —— 返回 `ConnectedStreams`
- `fill_future(future_stream)` —— 与 `from_future` 配合形成反馈闭环

所有算子都会创建对应的 `Transformation` 并追加到环境的 `pipeline`，但不会立即触发执行。你可以链式书写，也可以把中间 `DataStream` 保存为变量后继续扩展。

### Feedback Loop 示例

```python
future = env.from_future("feedback")

processed = (
    env.from_batch(["a", "b", "c"])
       .connect(future)
       .comap(MyCoMapFunction)    # 详见 ConnectedStreams 文档
)

processed.fill_future(future)
env.submit(autostop=True)
```

`fill_future` 会调用 `FutureTransformation.fill_with_transformation`，把真实的上游替换掉之前声明的占位符，从而形成 DAG 中的回边。

## 服务注册

`BaseEnvironment.register_service(name, service_class, *args, **kwargs)` 和 `register_service_factory` 会把服务包装成 `ServiceFactory` 并在 `submit()` 时交给 JobManager。算子内部可通过 `BaseFunction.call_service` 与运行时服务交互。若当前平台为 `local`，日志会以 "Registered local service" 的形式打印。

## Local 与 Remote 环境

| 能力 | `LocalEnvironment` | `RemoteEnvironment` |
| ---- | ------------------ | ------------------- |
| 提交 | `submit(autostop=False)`，依赖本地 `JobManager` 单例 | `submit(autostop=False)`，序列化后经 `JobManagerClient` 发送到远端 |
| 任务监控 | `_wait_for_completion()` 轮询本地 `JobManager` 状态 | `_wait_for_completion()` 通过 `client.get_job_status` 轮询远程状态 |
| 停止/关闭 | `stop()`、`close()` | `stop()`、`close()`、`health_check()`、`get_job_status()` |

在两种环境下，`autostop=True` 都会调用 `_wait_for_completion`，默认超时 5 分钟，可根据需要在应用层自行扩展。

## 后续阅读

- [Environment API](api/environments.md)：详解 `LocalEnvironment` / `RemoteEnvironment` 的方法和行为。
- [DataStream API](api/datastreams.md)：逐个说明支持的链式算子及其限制。
- [ConnectedStreams API](api/connected-streams.md)：介绍多流连接、`comap` 与 `join` 的使用方式。
- [Function 基类](api/functions.md)：列出各类函数接口的签名与实现注意事项。

阅读这些文档时，可随时与 `packages/sage-kernel/src/sage/core/api`、`.../transformation`、`.../jobmanager` 等源码相比对，确保文档内容与实现保持一致。

- [GitHub Issues](https://github.com/intellistream/SAGE/issues) - 报告问题
- [讨论区](https://github.com/intellistream/SAGE/discussions) - 社区讨论
- [官方文档](https://intellistream.github.io/SAGE-Pub/) - 完整文档

## 📄 许可证

MIT License - 详见 LICENSE 文件