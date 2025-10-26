# Function 基类

SAGE Kernel 中的算子函数全部继承自
`BaseFunction`（`packages/sage-kernel/src/sage/core/api/function/base_function.py`）。`BaseFunction`
定义了以下重要特性：

## 函数类型支持情况一览

| 函数类型                    | 状态   | 说明             |
| --------------------------- | ------ | ---------------- |
| MapFunction                 | 已实现 | 支持             |
| FlatMapFunction             | 已实现 | 支持             |
| FilterFunction              | 已实现 | 支持             |
| KeyByFunction               | 已实现 | 支持             |
| JoinFunction                | 已实现 | 支持             |
| SourceFunction              | 已实现 | 支持             |
| SinkFunction                | 已实现 | 支持             |
| SimpleBatchIteratorFunction | 已实现 | 支持             |
| ProcessFunction             | 未支持 | 计划中，尚未实现 |
| AggregateFunction           | 未支持 | 计划中，尚未实现 |
| ReduceFunction              | 未支持 | 计划中，尚未实现 |
| Side Output（副输出）       | 未支持 | 计划中，尚未实现 |

## 尚未实现的类型

目前仓库尚未提供 `ProcessFunction`、`AggregateFunction`、`ReduceFunction`、副输出（Side Output）等接口，已实现的算子能力仅限于前文列出的
`Map` / `FlatMap` / `Filter` / `KeyBy` / `Join` 等类型。如果需要更细粒度的算子语义，可以：

- 参考 `packages/sage-kernel/src/sage/core/operator` 下现有算子的实现方式，自行编写继承自 `BaseFunction` 的子类；
- 或者直接在运算符层扩展新的 Operator，再在内部组合现有函数类型来完成需求。

此外，Kafka Source 的示例实现位于
`KafkaSourceFunction`（`packages/sage-kernel/src/sage/core/api/function/kafka_source.py`），该类继承自
`SourceFunction` 并提供了 `run/execute/cancel` 等行为，能够满足实时消费 Kafka 的需求。

### SinkFunction - 数据输出

`SinkFunction` 是 `BaseFunction` 的子类，实际接口非常精简：只需要实现 `execute(self, data) -> None`，框架不会期望额外的
`open/sink/close` 生命周期方法。

```python
from sage.core.api.function.sink_function import SinkFunction


class PrintSink(SinkFunction):
    def execute(self, data):
        print(f"[sink] {data}")
```

如果需要管理外部资源（文件句柄、数据库连接等），可以在 `__init__` 中接受配置，通过惰性初始化或上下文注入的方式自行控制生命周期。下面给出一个更完整的示例：

```python
class FileSink(SinkFunction):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self._fh = None

    def execute(self, data):
        if self._fh is None:
            self._fh = open(self.path, "a", encoding="utf-8")
        self._fh.write(f"{data}\n")
        self._fh.flush()

    def __del__(self):
        if self._fh:
            self._fh.close()
```

在数据流中，通过 `DataStream.sink(PrintSink())` 或 `ConnectedStreams.sink(...)` 即可将流结束于一个输出函数。
`simple_batch_function.py` 提供了几个开箱即用的批处理函数实现：

- `SimpleBatchIteratorFunction`：遍历内存列表；
- `FileBatchIteratorFunction`：逐行读取文件；
- `RangeBatchIteratorFunction`：遍历数值区间；
- `GeneratorBatchIteratorFunction`：包装自定义生成器。

它们都继承自 `BaseFunction`，并遵循“返回值为 `None` 时结束”这一约定，可直接用于 `env.from_batch`。

## 键控与多流函数

### KeyByFunction / FieldKeyByFunction

```python
from sage.core.api.function.keyby_function import KeyByFunction, FieldKeyByFunction


class ExtractUser(KeyByFunction):
    def execute(self, data):
        return data["user_id"]


class ExtractRegion(FieldKeyByFunction):
    field_name = "location.region"
```

- 用于 `DataStream.keyby` 或 `ConnectedStreams.keyby`；
- 要求返回可哈希对象；
- `FieldKeyByFunction` 支持通过 `field_name` 指定嵌套字段，并自带校验。

### BaseCoMapFunction

```python
from sage.core.api.function.comap_function import BaseCoMapFunction


class Route(BaseCoMapFunction):
    def map0(self, data):
        return {"stream": 0, "payload": data}

    def map1(self, data):
        return {"stream": 1, "payload": data}
```

- 与 `ConnectedStreams.comap` 搭配使用；
- 需要实现与输入流数量一致的 `mapN` 方法；
- `execute` 被重写为抛出 `NotImplementedError`，提醒不要直接调用。

### BaseJoinFunction

```python
from sage.core.api.function.join_function import BaseJoinFunction


class SimpleJoin(BaseJoinFunction):
    def __init__(self):
        super().__init__()
        self.buffer = {}

    def execute(self, payload, key, tag):
        if tag == 0:  # 第一个流
            self.buffer[key] = payload
            return []
        # 第二个流到达
        left = self.buffer.get(key)
        if left:
            return [{"key": key, "left": left, "right": payload}]
        return []
```

- 由 `ConnectedStreams.join` 调用；
- `payload`、`key`、`tag` 会由运行时构造，其中 `tag` 标识输入流（0 或 1）；
- 需要自行管理状态和输出格式（返回列表）。

## Lambda 包装

`DataStream` 与 `ConnectedStreams` 的大部分算子都允许传入普通 `callable`。实现位于
`lambda_function.wrap_lambda`，会根据操作类型生成一个临时的 `BaseFunction` 子类。例如：

```python
stream.map(lambda value: value + 1)
```

内部会被转化为：

```python
class _LambdaMap(MapFunction):
    def execute(self, data):
        return lambda_body(data)
```

因此在调试日志中看到的函数名可能是 `_LambdaMap` 等包装类。

## 使用建议

1. **管理状态**：`BaseFunction` 没有内置状态快照功能，如需持久化请自行实现或关注 TODO。仓库内的 `StatefulFunction` 注释展示了潜在方向。
1. **服务调用**：通过 `call_service` 获得环境中注册的服务，例如缓存、外部 API 客户端等。
1. **日志记录**：合理使用 `self.logger.debug/info` 观察函数行为；环境可通过 `set_console_log_level` 控制输出级别。
1. **异常处理**：抛出的异常会由运行时捕获并记录，必要时可在函数内自行捕获并返回默认值。

## 尚未实现的类型

`ProcessFunction`、`AggregateFunction`、`ReduceFunction`、副输出（Side Output）等接口目前尚未在
`sage.core.api.function` 目录下提供。如果需要这些能力，需要参考 `Operator` 层实现并自行扩展。 def __init__(self,
bootstrap_servers: str, topic: str, group_id: str): self.bootstrap_servers = bootstrap_servers
self.topic = topic self.group_id = group_id self.running = True

```
def run(self, ctx: SourceContext[dict]):
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        self.topic,
        bootstrap_servers=self.bootstrap_servers,
        group_id=self.group_id,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        if not self.running:
            break
        ctx.emit(message.value)

def cancel(self):
    self.running = False
```

````

### SinkFunction - 数据输出

```python
from sage.core.api.function import SinkFunction

class SinkFunction(BaseFunction[T, None]):
    """数据输出函数基类"""

    def open(self, context) -> None:
        """初始化资源"""
        pass

    def sink(self, value: T) -> None:
        """输出单个元素"""
        raise NotImplementedError()

    def close(self) -> None:
        """清理资源"""
        pass

# 示例实现
class PrintSinkFunction(SinkFunction[Any]):
    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def sink(self, value: Any):
        print(f"{self.prefix}{value}")

class FileSinkFunction(SinkFunction[str]):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file = None

    def open(self, context):
        self.file = open(self.file_path, 'w')

    def sink(self, value: str):
        self.file.write(f"{value}\n")
        self.file.flush()

    def close(self):
        if self.file:
            self.file.close()

class DatabaseSinkFunction(SinkFunction[dict]):
    def __init__(self, connection_string: str, table_name: str):
        self.connection_string = connection_string
        self.table_name = table_name
        self.connection = None

    def open(self, context):
        import psycopg2
        self.connection = psycopg2.connect(self.connection_string)

    def sink(self, record: dict):
        cursor = self.connection.cursor()
        columns = list(record.keys())
        values = list(record.values())

        query = f"INSERT INTO {self.table_name} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(values))})"
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def close(self):
        if self.connection:
            self.connection.close()
````

## 🔗 连接函数

### JoinFunction - 流连接

```python
from sage.core.api.function import JoinFunction


class JoinFunction(BaseFunction[T1, T2, OUT]):
    """连接函数基类"""

    def join(self, left: T1, right: T2) -> OUT:
        """连接两个流的元素"""
        raise NotImplementedError()


# 示例实现
class UserOrderJoinFunction(JoinFunction[dict, dict, dict]):
    def join(self, user: dict, order: dict) -> dict:
        return {
            "order_id": order["id"],
            "user_name": user["name"],
            "user_email": user["email"],
            "order_amount": order["amount"],
            "order_time": order["timestamp"],
        }


class ClickImpressionJoinFunction(JoinFunction[dict, dict, dict]):
    def join(self, click: dict, impression: dict) -> dict:
        return {
            "ad_id": click["ad_id"],
            "user_id": click["user_id"],
            "click_time": click["timestamp"],
            "impression_time": impression["timestamp"],
            "conversion_delay": click["timestamp"] - impression["timestamp"],
        }
```

### CoMapFunction - 协同映射

```python
from sage.core.api.function import CoMapFunction


class CoMapFunction(BaseFunction[T1, T2, OUT]):
    """协同映射函数基类"""

    def map1(self, value: T1) -> OUT:
        """处理第一个流的元素"""
        raise NotImplementedError()

    def map2(self, value: T2) -> OUT:
        """处理第二个流的元素"""
        raise NotImplementedError()


# 示例实现
class AlertCoMapFunction(CoMapFunction[dict, dict, str]):
    def map1(self, user_action: dict) -> str:
        if user_action["action"] == "login_failed":
            return (
                f"Security Alert: Failed login attempt by user {user_action['user_id']}"
            )
        return None

    def map2(self, system_event: dict) -> str:
        if system_event["level"] == "ERROR":
            return f"System Alert: {system_event['message']}"
        return None


class MetricsCoMapFunction(CoMapFunction[dict, dict, dict]):
    def map1(self, user_metric: dict) -> dict:
        return {
            "type": "user_metric",
            "metric": user_metric["metric_name"],
            "value": user_metric["value"],
            "timestamp": user_metric["timestamp"],
        }

    def map2(self, system_metric: dict) -> dict:
        return {
            "type": "system_metric",
            "metric": system_metric["metric_name"],
            "value": system_metric["value"],
            "timestamp": system_metric["timestamp"],
        }
```

## 🎯 最佳实践

### 1. 函数状态管理

```python
class StatefulProcessFunction(ProcessFunction[str, int]):
    def __init__(self):
        self.word_count = {}  # 状态

    def process(self, word: str, ctx: ProcessContext[int]):
        self.word_count[word] = self.word_count.get(word, 0) + 1
        ctx.emit(self.word_count[word])
```

### 2. 错误处理

```python
class RobustMapFunction(MapFunction[str, dict]):
    def map(self, json_str: str) -> dict:
        try:
            return json.loads(json_str)
        except Exception as e:
            return {"error": str(e), "raw_input": json_str, "timestamp": time.time()}
```

### 3. 性能优化

```python
class OptimizedAggregateFunction(AggregateFunction[int, int, int]):
    def __init__(self):
        self.batch_size = 1000
        self.batch = []

    def add(self, accumulator: int, value: int) -> int:
        self.batch.append(value)
        if len(self.batch) >= self.batch_size:
            # 批量处理
            accumulator += sum(self.batch)
            self.batch.clear()
        return accumulator
```

### 4. 资源管理

```python
class DatabaseSinkFunction(SinkFunction[dict]):
    def open(self, context):
        self.connection_pool = create_connection_pool()

    def sink(self, record: dict):
        with self.connection_pool.get_connection() as conn:
            # 使用连接池
            self.insert_record(conn, record)

    def close(self):
        self.connection_pool.close()
```

## 📚 相关文档

- [数据流处理](datastreams.md) - 数据流操作详解
- [连接流](connected-streams.md) - 多流处理
- [环境管理](environments.md) - 执行环境配置
