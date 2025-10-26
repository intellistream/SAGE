# DataStream API

`DataStream`（`packages/sage-kernel/src/sage/core/api/datastream.py`）是 SAGE Kernel
中对“单输入算子链”的抽象。它负责记录上游 `Transformation`，在链式调用时持续构建执行图，而不会立即启动任务。

本文档覆盖源码中已经实现的操作，帮助你在阅读/修改代码时快速定位相关接口。

## 创建 DataStream

只有 `Environment` 可以创建 `DataStream` 实例。常见入口：

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("stream-demo")

# 批处理源（列表、迭代器、BatchFunction 子类等）
numbers = env.from_batch([1, 2, 3, 4])

# 自定义实时源
custom = env.from_source(MySourceFunction)

# Kafka 源
kafka = env.from_kafka_source(
    bootstrap_servers="localhost:9092",
    topic="events",
    group_id="demo-consumer",
)
```

每个 `DataStream` 都持有一个 `_environment` 引用和一个 `transformation`，后续操作会基于这些信息创建新的 `Transformation` 并返回新的
`DataStream`。

## 可用算子

### map

```python
numbers = env.from_batch([1, 2, 3])

doubled = numbers.map(lambda value: value * 2)


class Multiply(MapFunction):
    def execute(self, data):
        return data * 10


times_ten = doubled.map(Multiply)
```

- 传入的 `function` 可以是 `BaseFunction` 子类或普通 `callable`；普通函数会通过 `wrap_lambda(function, "map")`
  自动封装成内置的匿名函数。
- `parallelism` 参数当前主要用于透传到 `Transformation`，默认值为 1。

### filter

```python
evens = numbers.filter(lambda value: value % 2 == 0)


class NonEmpty(FilterFunction):
    def execute(self, data):
        return bool(data)


non_empty = stream.filter(NonEmpty)
```

过滤函数应返回布尔值；源码中通过 `FilterTransformation` 和 `FilterFunction._process_output` 统一转换为 `bool`。

### flatmap

```python
sentences = env.from_batch(["hello world", "sage kernel"])

words = sentences.flatmap(lambda text: text.split())


class EmitChars(FlatMapFunction):
    def execute(self, data):
        for ch in data:
            self.collect(ch)


letters = sentences.flatmap(EmitChars)
```

- 可以返回可迭代对象，也可以调用 `self.collect()` 多次发送数据；
- 当返回值为 `None` 时，仅保留通过 `collect` 发出的元素。

### sink

```python
numbers.sink(lambda value: print(f"sink: {value}"))


class PrintSink(SinkFunction):
    def execute(self, data):
        print(f"[sink] {data}")


numbers.map(lambda v: v * 2).sink(PrintSink)
```

`sink` 是终端算子，执行后返回当前 `DataStream`（而不是新建一个），以便在调用链上继续使用同一个引用。

### print

```python
numbers.print(prefix="[result]")
```

`print` 是对 `sink(PrintSink, ...)` 的封装，使用 `sage.libs.io_utils.sink.PrintSink`（请注意命名空间，与
`ConnectedStreams.print` 中的 sink 实现不完全相同）。

### keyby

```python
from sage.core.api.function.keyby_function import KeyByFunction


class UserKey(KeyByFunction):
    def execute(self, data):
        return data["user_id"]


keyed = events.keyby(UserKey)
```

- 传入的函数需要返回可哈希的键；
- 支持传入 `BaseFunction` 子类或普通 `callable`，后者同样会通过 `wrap_lambda` 适配；
- `strategy` 参数目前接受 `"hash"`、`"broadcast"`、`"round_robin"`，实际行为取决于下游调度实现。

### connect

```python
stream_a = env.from_batch([1, 2])
stream_b = env.from_batch(["a", "b"])

connected = stream_a.connect(stream_b)
```

返回 `ConnectedStreams`，可用于 `comap`、`join` 等多流操作（见 `connected-streams.md`）。

### fill_future

```python
future = env.from_future("loop")

upstream = env.from_batch(["hello"])
upstream.fill_future(future)
```

如果尝试向非 `FutureTransformation` 填充或重复填充，会抛出错误。`fill_future` 常与 `ConnectedStreams` 配合构建反馈边。

## 类型追踪

构造函数中会尝试通过 `__orig_class__` 捕获泛型参数，用于调试日志输出；若无法解析，则默认为 `typing.Any`。这不会影响运行结果，主要用于观察。

## 调试建议

1. 所有算子都会把新建的 `Transformation` 追加到 `env.pipeline`。在提交前打印 `len(env.pipeline)` 可以快速核对算子数量。

1. `DataStream.logger` 默认使用 `CustomLogger`（`sage.common.utils.logging.custom_logger`），可通过环境的
   `set_console_log_level` 控制输出级别。

1. 如果链式调用中需要复用中间结果，可直接保存 `DataStream` 引用，API 不会进行真实复制：

   ```python
   base = env.from_batch(range(10))
   evens = base.filter(lambda v: v % 2 == 0)
   odds = base.filter(lambda v: v % 2 == 1)
   ```

1. `sink` 返回原始 `DataStream`，避免了 `None` 破坏链式写法；若需要阻止后续调用，可自行忽略返回值。

## 尚未实现的能力

- DataStream 目前不包含 `reduce`、`aggregate`、`window`、`process`、`union` 等接口；
- 并行度控制仅在算子创建时接受参数，尚未提供 `set_parallelism` 之类的链式方法；
- 侧输出、副输出流、定时器等功能在源码中暂未实现。

如果需要这些高级特性，请关注仓库中的相关 Issue 或自行扩展 `transformation` 与 `operator` 层，并同步更新文档。 self.reuse_dict\["input"\]
= value self.reuse_dict\["processed"\] = process(value) return self.reuse_dict

````

### 缓冲设置

```python
# 设置缓冲区大小
stream.map(function).set_buffer_timeout(100)  # 100ms
stream.map(function).set_buffer_size(1000)    # 1000条记录
````

## 🏷️ 类型系统

### 泛型支持

```python
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")


class TypedDataStream(Generic[T]):
    def map(self, func: Callable[[T], U]) -> "TypedDataStream[U]":
        """类型安全的map操作"""

    def filter(self, predicate: Callable[[T], bool]) -> "TypedDataStream[T]":
        """类型安全的filter操作"""

    def key_by(self, key_selector: Callable[[T], K]) -> "KeyedStream[T, K]":
        """类型安全的keyBy操作"""
```

### 类型转换

```python
# 显式类型转换
str_stream: DataStream[str] = numbers.map(str)
int_stream: DataStream[int] = str_stream.map(int)


# 类型注解
def process_user(user: dict) -> UserProfile:
    return UserProfile(**user)


profiles: DataStream[UserProfile] = users.map(process_user)
```

## 📚 最佳实践

1. **链式调用**: 使用链式调用构建清晰的数据处理管道
1. **函数重用**: 将复杂逻辑封装为可重用的函数类
1. **错误处理**: 实现适当的错误处理和数据验证
1. **性能优化**: 合理设置并行度和缓冲区参数
1. **类型安全**: 使用类型注解提高代码可读性和安全性

## 📖 相关文档

- [函数接口](functions.md) - 详细的函数接口说明
- [连接流](connected-streams.md) - 多流处理

<!-- - [性能优化](../guides/performance.md) - 性能调优指南 -->

- 性能优化 - 性能调优指南
