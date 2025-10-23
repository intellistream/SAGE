# ConnectedStreams API

`ConnectedStreams`（`packages/sage-kernel/src/sage/core/api/connected_streams.py`）用于在同一 `Environment` 内组合多个 `DataStream`，并提供 `comap`、`join` 等多输入算子。本节介绍已经落地的接口以及主要约束。

## 构造方式

通常不需要直接实例化 `ConnectedStreams`。`DataStream.connect()` 会自动创建：

```python
stream_a = env.from_batch([1, 2, 3])
stream_b = env.from_batch(["a", "b", "c"])

connected = stream_a.connect(stream_b)
```

`connect` 还支持将一个已有的 `ConnectedStreams` 再次连接新的 `DataStream` 或另一个 `ConnectedStreams`，内部会把 `_environment` 与 `transformation` 列表按顺序拼接。

## 链式操作

### map / sink / print

与 `DataStream` 上的同名方法类似，但作用于每个连接流：

```python
connected.map(lambda value: f"stream item: {value}")
connected.sink(lambda value: print("sink", value))
connected.print(prefix="[connected]")
```

- 支持 `callable` 与 `BaseFunction` 子类；
- `print` 内部调用 `sage_libs.io.sink.PrintSink`（注意命名空间与 `DataStream.print` 略有不同）。

### connect

在已有的 `ConnectedStreams` 上继续追加其他流：

```python
third = env.from_batch([True, False])

combined = connected.connect(third)
```

返回的新对象会包含前一个 `ConnectedStreams` 的所有 transformation，并保持原有顺序。

### keyby

为组合流统一或分别指定键选择函数：

```python
from sage.core.api.function.keyby_function import KeyByFunction

class KeyA(KeyByFunction):
    def execute(self, data):
        return data["user_id"]

class KeyB(KeyByFunction):
    def execute(self, data):
        return data["user"]

# 相同的 key 规则应用于所有流
same_key = connected.keyby(KeyA)

# 针对每个流提供不同的 key 函数
per_stream_key = connected.keyby([KeyA, KeyB])
```

- 目前只接受 `BaseFunction` 子类或可包装的 `callable`；
- 当提供列表时，长度必须与连接的流数量一致。

## CoMap

`comap` 适用于对每个输入流分别处理，再返回一个新的 `DataStream`。

```python
from sage.core.api.function.comap_function import BaseCoMapFunction

class RouteEvents(BaseCoMapFunction):
    def map0(self, data):
        return {"user": data["user_id"], "type": "user_event"}

    def map1(self, data):
        return {"user": data["user"], "type": "system_event"}

result_stream = connected.comap(RouteEvents)
result_stream.print()
```

关键点：

- `comap` 仅接受 `BaseCoMapFunction` 的子类；传入 lambda 会触发 `NotImplementedError`；
- 类必须实现与输入流数量匹配的 `mapN` 方法（`map0`、`map1`…）。源码会在调用前检查缺失的方法并抛出 `TypeError`；
- 可选地，通过 `parallelism` 参数为底层 `CoMapTransformation` 设置并行度。

## Join

`join` 用于两个 **已按键分区** 的流之间的操作。

```python
from sage.core.api.function.join_function import BaseJoinFunction

class MergeUserOrder(BaseJoinFunction):
    def execute(self, payload, key, tag):
        # tag: 0 表示来自第一个流，1 表示来自第二个流
        left, right = payload
        user, order = left, right
        if user and order:
            return [{
                "user_id": key,
                "user_name": user.get("name"),
                "order_id": order.get("id"),
            }]
        return []

users = stream_a.keyby(lambda data: data["user_id"])
orders = stream_b.keyby(lambda data: data["user"])

joined_stream = users.connect(orders).join(MergeUserOrder)
```

- 只能在 **两个** 输入流上调用；否则会抛出 `ValueError`；
- `function` 必须继承 `BaseJoinFunction`，并实现 `execute(self, payload, key, tag)`；
- 当前实现中尚未强制校验输入是否已经 keyby，相关 TODO 见源码（issue #225）。

## 错误处理与限制

- `ConnectedStreams` 构造函数要求至少输入两个 `Transformation`，并确保它们来自同一个环境；否则会抛出 `ValueError`；
- `comap`、`keyby` 等方法对 lambda 的支持有限，必要时请显式编写函数类；
- 尚未实现的特性：窗口、状态共享、错误处理回调、背压配置等；这些功能当前版本尚未提供，请以源码为准。

## 调试提示

1. `connected.transformations` 保存了当前所有上游 transformation，可用于排查链路顺序。
2. 通过 `connected.connect(other)` 生成的新对象会重新验证环境一致性，若混用了不同 Environment 创建的流，会立即报错。
3. `comap` 里的 `BaseCoMapFunction` 可使用普通属性记录状态；执行时同样能通过 `self.call_service` 调用环境内注册的服务。

了解更多：
- [DataStream API](datastreams.md) —— 获取 `ConnectedStreams` 的入口；
- `packages/sage-kernel/src/sage/core/transformation/join_transformation.py` —— 了解 join 的底层实现。

# Connect them
connected = ConnectedStreams([stream1, stream2])
```

### With Functions API

```python
from sage.core.api.functions import register_function

@register_function
def connected_processor(connected_streams):
    return connected_streams.process(my_processor)
```

This Connected Streams API enables sophisticated stream processing patterns while maintaining the simplicity and flexibility of the SAGE kernel architecture.
