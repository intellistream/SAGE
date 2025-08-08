# 数据流处理 (DataStreams)

DataStream 是 SAGE Kernel 的核心抽象，代表一个数据流。它提供了丰富的转换操作，支持函数式编程风格的链式调用。

## 🌊 DataStream 基础

### 创建数据流

```python
from sage.core.api.local_environment import LocalEnvironment

env = LocalEnvironment("stream_demo")

# 从集合创建
numbers = env.from_batch([1, 2, 3, 4, 5])

# 从文件创建
lines = env.from_text_file("data.txt")

# 从Kafka创建
events = env.from_kafka_source(
    bootstrap_servers="localhost:9092",
    topic="events",
    group_id="processors"
)
```

### 基本概念

```python
from typing import TypeVar, Generic

T = TypeVar('T')  # 元素类型
U = TypeVar('U')  # 转换后类型

class DataStream(Generic[T]):
    """类型安全的数据流"""
    
    def map(self, func: Callable[[T], U]) -> DataStream[U]:
        """一对一转换"""
        
    def filter(self, predicate: Callable[[T], bool]) -> DataStream[T]:
        """过滤操作"""
        
    def flat_map(self, func: Callable[[T], Iterable[U]]) -> DataStream[U]:
        """一对多转换"""
```

## 🔄 转换操作

### Map 转换

一对一的元素转换操作。

```python
# 使用Lambda函数
numbers = env.from_batch([1, 2, 3, 4, 5])
squared = numbers.map(lambda x: x * x)

# 使用命名函数
def double(x: int) -> int:
    return x * 2

doubled = numbers.map(double)

# 使用自定义函数类
class SquareFunction(MapFunction[int, int]):
    def map(self, value: int) -> int:
        return value * value

squared = numbers.map(SquareFunction())

# 复杂转换
class ParseJson(MapFunction[str, dict]):
    def map(self, json_str: str) -> dict:
        try:
            return json.loads(json_str)
        except:
            return {"error": "invalid_json", "raw": json_str}

parsed = json_lines.map(ParseJson())
```

### Filter 操作

根据条件过滤元素。

```python
# 简单过滤
even_numbers = numbers.filter(lambda x: x % 2 == 0)

# 复杂过滤条件
class ValidUserFilter(FilterFunction[dict]):
    def filter(self, user: dict) -> bool:
        return (user.get("age", 0) >= 18 and 
                user.get("email") is not None and
                "@" in user.get("email", ""))

valid_users = users.filter(ValidUserFilter())

# 空值过滤
non_null = stream.filter(lambda x: x is not None)
```

### FlatMap 转换

一对多的转换操作，将每个元素转换为多个元素。

```python
# 字符串分词
sentences = env.from_batch(["hello world", "sage kernel", "stream processing"])
words = sentences.flat_map(lambda s: s.split())

# 自定义FlatMap
class SplitLines(FlatMapFunction[str, str]):
    def flat_map(self, value: str) -> Iterable[str]:
        return value.strip().split('\n')

lines = text_blocks.flat_map(SplitLines())

# 数据展开
class ExpandEvents(FlatMapFunction[dict, dict]):
    def flat_map(self, batch: dict) -> Iterable[dict]:
        events = batch.get("events", [])
        for event in events:
            event["batch_id"] = batch["id"]
            yield event

events = batches.flat_map(ExpandEvents())
```

## 🔑 键值操作

### KeyBy 分组

根据键对数据流进行分区，相同键的元素会路由到同一个处理器。

```python
# 简单键提取
user_events = events.key_by(lambda event: event["user_id"])

# 复杂键提取
class UserRegionKeySelector(KeySelector[dict, tuple]):
    def get_key(self, event: dict) -> tuple:
        return (event["user_id"], event["region"])

grouped = events.key_by(UserRegionKeySelector())

# 聚合操作
class SumAggregator(AggregateFunction[int, int, int]):
    def add(self, acc: int, value: int) -> int:
        return acc + value
    
    def get_result(self, acc: int) -> int:
        return acc
    
    def create_accumulator(self) -> int:
        return 0

# 按键聚合
sums = numbers.key_by(lambda x: x % 2).aggregate(SumAggregator())
```

### Reduce 操作

对相同键的元素进行归约操作。

```python
# 简单归约
max_values = keyed_stream.reduce(lambda a, b: max(a, b))

# 自定义归约
class MergeUsers(ReduceFunction[dict]):
    def reduce(self, user1: dict, user2: dict) -> dict:
        # 合并用户信息，保留最新数据
        result = user1.copy()
        result.update(user2)
        result["last_updated"] = max(
            user1.get("last_updated", 0),
            user2.get("last_updated", 0)
        )
        return result

merged_users = user_updates.key_by(lambda u: u["id"]).reduce(MergeUsers())
```

## 🏪 窗口操作

### 时间窗口

```python
from sage.core.api.window import TumblingTimeWindows, SlidingTimeWindows
from datetime import timedelta

# 滚动时间窗口
windowed = events.key_by(lambda e: e["sensor_id"]) \
    .window(TumblingTimeWindows.of(timedelta(minutes=5))) \
    .aggregate(AvgAggregator())

# 滑动时间窗口  
sliding = events.key_by(lambda e: e["user_id"]) \
    .window(SlidingTimeWindows.of(
        size=timedelta(minutes=10),
        slide=timedelta(minutes=1)
    )) \
    .aggregate(CountAggregator())
```

### 计数窗口

```python
from sage.core.api.window import TumblingCountWindows

# 每100个元素一个窗口
count_windowed = stream.key_by(key_selector) \
    .window(TumblingCountWindows.of(100)) \
    .aggregate(SumAggregator())
```

### 会话窗口

```python
from sage.core.api.window import SessionWindows

# 会话窗口 - 30秒不活跃则关闭窗口
session_windowed = events.key_by(lambda e: e["session_id"]) \
    .window(SessionWindows.with_gap(timedelta(seconds=30))) \
    .aggregate(SessionAggregator())
```

## 🔗 连接操作

### Join 连接

```python
# 内连接
joined = stream1.join(stream2) \
    .where(lambda x: x["id"]) \
    .equal_to(lambda y: y["user_id"]) \
    .window(TumblingTimeWindows.of(timedelta(minutes=5))) \
    .apply(JoinFunction())

# 自定义连接函数
class UserOrderJoin(JoinFunction[dict, dict, dict]):
    def join(self, user: dict, order: dict) -> dict:
        return {
            "user_name": user["name"],
            "order_id": order["id"],
            "order_amount": order["amount"],
            "join_time": time.time()
        }

result = users.join(orders) \
    .where(lambda u: u["id"]) \
    .equal_to(lambda o: o["user_id"]) \
    .window(TumblingTimeWindows.of(timedelta(hours=1))) \
    .apply(UserOrderJoin())
```

### CoMap 协同处理

```python
# 连接两个流
connected = stream1.connect(stream2)

# 协同处理函数
class AlertCoMapFunction(CoMapFunction[dict, dict, str]):
    def map1(self, user_event: dict) -> str:
        if user_event["action"] == "login_failed":
            return f"Failed login: {user_event['user_id']}"
        return None
    
    def map2(self, system_event: dict) -> str:
        if system_event["level"] == "ERROR":
            return f"System error: {system_event['message']}"
        return None

alerts = connected.map(AlertCoMapFunction()).filter(lambda x: x is not None)
```

## 📤 输出操作

### Sink 操作

```python
# 简单输出
numbers.sink(print)

# 自定义Sink
class DatabaseSink(SinkFunction[dict]):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
    
    def open(self, context):
        self.connection = create_connection(self.connection_string)
    
    def sink(self, record: dict):
        insert_query = "INSERT INTO events VALUES (%s, %s, %s)"
        self.connection.execute(insert_query, 
            (record["id"], record["timestamp"], record["data"]))
    
    def close(self):
        if self.connection:
            self.connection.close()

events.sink(DatabaseSink("postgresql://localhost/mydb"))

# 文件输出
results.sink_to_file("./output/results.txt")

# Kafka输出
events.sink_to_kafka(
    bootstrap_servers="localhost:9092",
    topic="processed_events",
    serializer="json"
)
```

### 副输出流

```python
# 定义副输出标签
error_tag = OutputTag("errors", str)
warning_tag = OutputTag("warnings", str)

# 在处理函数中使用副输出
class ValidateAndRoute(ProcessFunction[dict, dict]):
    def process(self, record: dict, ctx: ProcessContext[dict]):
        if not self.is_valid(record):
            ctx.output(error_tag, f"Invalid record: {record}")
            return
        
        if self.is_suspicious(record):
            ctx.output(warning_tag, f"Suspicious record: {record}")
        
        yield record  # 主输出

main_stream = events.process(ValidateAndRoute())
error_stream = main_stream.get_side_output(error_tag)
warning_stream = main_stream.get_side_output(warning_tag)
```

## 🔀 流控制操作

### Split 分流

```python
# 条件分流
even_tag = OutputTag("even", int)
odd_tag = OutputTag("odd", int)

class SplitByParity(ProcessFunction[int, int]):
    def process(self, value: int, ctx: ProcessContext[int]):
        if value % 2 == 0:
            ctx.output(even_tag, value)
        else:
            ctx.output(odd_tag, value)

split_stream = numbers.process(SplitByParity())
even_stream = split_stream.get_side_output(even_tag)
odd_stream = split_stream.get_side_output(odd_tag)
```

### Union 合流

```python
# 合并多个流
all_events = stream1.union(stream2, stream3)

# 类型必须相同
numbers1 = env.from_batch([1, 2, 3])
numbers2 = env.from_batch([4, 5, 6])
all_numbers = numbers1.union(numbers2)
```

## ⚡ 性能优化

### 并行度设置

```python
# 设置算子并行度
processed = stream.map(heavy_computation).set_parallelism(8)

# 设置全局并行度
env.set_parallelism(4)
```

### 对象重用

```python
# 启用对象重用（减少GC压力）
env.enable_object_reuse()

# 在函数中重用对象
class ReuseObjectMap(MapFunction[str, dict]):
    def __init__(self):
        self.reuse_dict = {}  # 重用的字典对象
    
    def map(self, value: str) -> dict:
        self.reuse_dict.clear()
        self.reuse_dict["input"] = value
        self.reuse_dict["processed"] = process(value)
        return self.reuse_dict
```

### 缓冲设置

```python
# 设置缓冲区大小
stream.map(function).set_buffer_timeout(100)  # 100ms
stream.map(function).set_buffer_size(1000)    # 1000条记录
```

## 🏷️ 类型系统

### 泛型支持

```python
from typing import TypeVar, Generic, Callable

T = TypeVar('T')
U = TypeVar('U')
K = TypeVar('K')

class TypedDataStream(Generic[T]):
    def map(self, func: Callable[[T], U]) -> 'TypedDataStream[U]':
        """类型安全的map操作"""
        
    def filter(self, predicate: Callable[[T], bool]) -> 'TypedDataStream[T]':
        """类型安全的filter操作"""
        
    def key_by(self, key_selector: Callable[[T], K]) -> 'KeyedStream[T, K]':
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
2. **函数重用**: 将复杂逻辑封装为可重用的函数类
3. **错误处理**: 实现适当的错误处理和数据验证
4. **性能优化**: 合理设置并行度和缓冲区参数
5. **类型安全**: 使用类型注解提高代码可读性和安全性

## 📖 相关文档

- [函数接口](functions.md) - 详细的函数接口说明
- [连接流](connected-streams.md) - 多流处理
- [性能优化](../guides/performance.md) - 性能调优指南
