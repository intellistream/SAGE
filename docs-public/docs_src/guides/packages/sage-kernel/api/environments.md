# Environment API

`BaseEnvironment`（见 `packages/sage-kernel/src/sage/core/api/base_environment.py`）负责维护运行配置、构建 `Transformation` 管道以及与 JobManager 交互。本页只记录**当前源码中已经实现**的接口。

## 核心属性与通用方法

| 属性/方法 | 说明 |
| --------- | ---- |
| `name` | 环境名称，在提交到 JobManager 时会随配置一起传输。 |
| `config` | 以 `dict` 形式保存的用户配置。构造函数会拷贝传入的字典，避免外部突变。 |
| `pipeline` | `List[BaseTransformation]`，按照声明顺序记录所有算子。`from_*`/`map` 等接口都会向其中追加元素。 |
| `set_console_log_level(level)` | 调整环境 logger 的控制台输出级别，仅接受 `DEBUG/INFO/WARNING/ERROR`。 |
| `register_service(name, cls, *args, **kwargs)` | 使用 `ServiceFactory` 包装服务并在提交时交给 JobManager。 |
| `register_service_factory(name, factory)` | 注册已有的 `ServiceFactory` 实例。 |

### 数据源创建

`BaseEnvironment` 暴露了多种 `from_*` 方法，它们都会返回一个新的 `DataStream`：

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.simple_batch_function import SimpleBatchIteratorFunction

env = LocalEnvironment("demo")

# 1. 批数据（列表、迭代器或者 BaseFunction 子类）
numbers = env.from_batch([1, 2, 3, 4])

# 2. 任意 SourceFunction / BatchFunction 子类
records = env.from_source(SimpleBatchIteratorFunction(["a", "b"]))

# 3. Kafka 数据源
kafka_stream = env.from_kafka_source(
    bootstrap_servers="localhost:9092",
    topic="events",
    group_id="demo-consumer",
)

# 4. Future 占位流，用于反馈边
future_stream = env.from_future("feedback")
```

实现细节：

- `from_batch` 会选择 `BatchTransformation`，当底层函数的 `execute()` 返回 `None` 时终止；
- `from_collection` 是旧接口，内部同样会走 `BatchTransformation` 路径；
- `from_source` 使用 `SourceTransformation`；
- `from_future` 使用 `FutureTransformation`，需要配合 `DataStream.fill_future()`。

## LocalEnvironment

源代码：`packages/sage-kernel/src/sage/core/api/local_environment.py`

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment(name="local-demo")

dataset = env.from_batch(["a", "b", "c"])
dataset.print()

# autostop=True 会阻塞至 JobManager 完成并执行 `_wait_for_completion()`
env.submit(autostop=True)
```

### 行为说明

- 构造函数将 `platform` 固定为 `"local"`，并把 `_engine_client` 设为 `None`，表示直接使用本地 `JobManager` 实例；
- `jobmanager` 属性懒加载 `JobManager()` 单例，后续提交/停止都会复用该对象；
- `submit(autostop: bool = False)` 会调用 `jobmanager.submit_job(self)`，返回生成的 `env_uuid`；
- 当 `autostop=True` 时，`_wait_for_completion()` 会轮询 `jobmanager.jobs` 中的任务状态，最长等待 5 分钟，然后尝试调用 `stop()` 清理；
- `stop()` 与 `close()` 都通过 `jobmanager.pause_job(env_uuid)` 停止任务，后者额外会清空 `pipeline` 并重置 `env_uuid`。

> 注意：`LocalEnvironment` 默认不会启动后台线程或进程，一切逻辑都在 JobManager 的控制下运行。

## RemoteEnvironment

源代码：`packages/sage-kernel/src/sage/core/api/remote_environment.py`

```python
from sage.core.api.remote_environment import RemoteEnvironment

env = RemoteEnvironment(
    name="remote-demo",
    host="127.0.0.1",
    port=19001,
)

stream = env.from_batch(range(3))
stream.print()

env.submit(autostop=True)
```

### 行为说明

- 构造函数会保存远程 JobManager 的 `host` / `port`，并把这些信息写入 `config`，便于调试；
- `client` 属性延迟实例化 `JobManagerClient`，用于 RPC；
- `submit(autostop=False)`：
  1. 调用 `trim_object_for_ray(self)` 剔除不可序列化字段；
  2. 使用 `serialize_object`（dill）对环境进行序列化；
  3. 通过 `client.submit_job(serialized_env, autostop)` 将任务发送给远程 JobManager；
- `autostop=True` 同样会触发 `_wait_for_completion()`，该方法周期性调用 `client.get_job_status` 检查作业状态；
- 额外提供的运维接口：
  - `stop()`：调用 `pause_job`，返回服务端响应；
  - `close()`：在 `stop()` 的基础上重置本地状态；
  - `health_check()`：调用 `client.health_check()`；
  - `get_job_status()`：查询当前环境对应的远程作业状态。

## 常见模式

### 使用 autostop 等待批任务完成

```python
env = LocalEnvironment("batch-job")

env.from_batch(["a", "b", "c"]).print()

# 如果不传 autostop，submit 会立即返回，任务在后台继续运行
env.submit(autostop=True)
```

### 注册运行时服务

```python
from sage.core.api.local_environment import LocalEnvironment

class KVService:
    def __init__(self):
        self.store = {}

    def process(self, payload):
        command, *args = payload
        if command == "set":
            key, value = args
            self.store[key] = value
            return "ok"
        if command == "get":
            (key,) = args
            return self.store.get(key)
        raise ValueError(f"Unknown command {command}")

env = LocalEnvironment("service-demo")
env.register_service("memory_kv", KVService)

stream = env.from_batch([("set", "x", 1), ("get", "x")])

class CallServiceFunction(MapFunction):
    def execute(self, data):
        return self.call_service("memory_kv", data)

stream.map(CallServiceFunction).print()
env.submit(autostop=True)
```

### 创建反馈边

```python
future = env.from_future("loop")

updated = (
    env.from_batch([1, 2, 3])
       .connect(future)
       .comap(MyCoMapFunction)
)

updated.fill_future(future)
env.submit(autostop=True)
```

`fill_future` 会替换 `FutureTransformation` 的输入，确保 DAG 闭合。请确保在提交前完成 `fill_future` 调用。

## 尚未提供的接口

以下方法目前**尚未在源码中实现**：

- `submit_async`、`cancel`、`resume`、`create_savepoint` 等运行时控制接口；
- `set_parallelism`、`enable_object_reuse`、`set_managed_memory_fraction` 等执行参数调优接口；
- Metric/Logger 管理相关的 `enable_metrics`、`set_log_file` 等方法。

若需要这些能力，请结合 `JobManager`／`JobManagerClient` 的现有实现自行扩展，并在文档或代码中明确标注。

## 诊断建议

1. 提交前检查 `env.pipeline` 是否为空；如果为空，JobManager 仍会创建任务但不会执行任何算子。
2. 使用 `set_console_log_level("DEBUG")` 可以在控制台看到算子提交、服务注册等调试信息。
3. 远程部署时，建议先调用 `health_check()`，确认 JobManager 端口可达。
4. 如果 `autostop=True` 且任务超过 5 分钟未完成，`_wait_for_completion` 会尝试调用 `stop()`；可以根据需要在应用层捕获并重试。
