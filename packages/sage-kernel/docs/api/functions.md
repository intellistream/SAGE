# 函数接口 (Functions)

SAGE Kernel 提供了丰富的函数接口，支持用户定义各种数据处理逻辑。所有函数都继承自基础函数类，提供类型安全和性能优化。

## 🧩 函数类型概览

```
BaseFunction (抽象基类)
├── MapFunction          # 一对一转换
├── FlatMapFunction      # 一对多转换  
├── FilterFunction       # 过滤操作
├── ReduceFunction       # 归约操作
├── AggregateFunction    # 聚合操作
├── ProcessFunction      # 通用处理函数
├── SinkFunction         # 输出函数
├── SourceFunction       # 数据源函数
├── KeySelector          # 键选择器
├── JoinFunction         # 连接函数
└── CoMapFunction        # 协同映射函数
```

## 🔄 转换函数

### MapFunction - 一对一转换

```python
from sage.core.api.function import MapFunction
from typing import TypeVar

T = TypeVar('T')
U = TypeVar('U')

class MapFunction(BaseFunction[T, U]):
    """一对一转换函数基类"""
    
    def map(self, value: T) -> U:
        """转换单个元素"""
        raise NotImplementedError()

# 示例实现
class SquareFunction(MapFunction[int, int]):
    def map(self, value: int) -> int:
        return value * value

class ParseJsonFunction(MapFunction[str, dict]):
    def map(self, json_str: str) -> dict:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"error": "invalid_json", "raw": json_str}

class UserProfileExtractor(MapFunction[dict, UserProfile]):
    def map(self, user_data: dict) -> UserProfile:
        return UserProfile(
            id=user_data["id"],
            name=user_data["name"],
            email=user_data.get("email"),
            age=user_data.get("age", 0)
        )

# 使用方式
numbers.map(SquareFunction())
json_lines.map(ParseJsonFunction())
user_data.map(UserProfileExtractor())
```

### FlatMapFunction - 一对多转换

```python
from sage.core.api.function import FlatMapFunction
from typing import Iterable

class FlatMapFunction(BaseFunction[T, Iterable[U]]):
    """一对多转换函数基类"""
    
    def flat_map(self, value: T) -> Iterable[U]:
        """将一个元素转换为多个元素"""
        raise NotImplementedError()

# 示例实现
class SplitWordsFunction(FlatMapFunction[str, str]):
    def flat_map(self, sentence: str) -> Iterable[str]:
        return sentence.lower().split()

class ExpandEventsFunction(FlatMapFunction[dict, dict]):
    def flat_map(self, batch: dict) -> Iterable[dict]:
        for event in batch.get("events", []):
            event["batch_id"] = batch["id"]
            event["batch_timestamp"] = batch["timestamp"]
            yield event

class GenerateNGramsFunction(FlatMapFunction[str, str]):
    def __init__(self, n: int = 2):
        self.n = n
    
    def flat_map(self, text: str) -> Iterable[str]:
        words = text.split()
        for i in range(len(words) - self.n + 1):
            yield " ".join(words[i:i + self.n])

# 使用方式
sentences.flat_map(SplitWordsFunction())
batches.flat_map(ExpandEventsFunction())
text.flat_map(GenerateNGramsFunction(3))  # 3-grams
```

### FilterFunction - 过滤操作

```python
from sage.core.api.function import FilterFunction

class FilterFunction(BaseFunction[T, bool]):
    """过滤函数基类"""
    
    def filter(self, value: T) -> bool:
        """判断是否保留该元素"""
        raise NotImplementedError()

# 示例实现
class AdultUserFilter(FilterFunction[dict]):
    def filter(self, user: dict) -> bool:
        return user.get("age", 0) >= 18

class ValidEmailFilter(FilterFunction[str]):
    def filter(self, email: str) -> bool:
        return "@" in email and "." in email.split("@")[1]

class PriceRangeFilter(FilterFunction[dict]):
    def __init__(self, min_price: float, max_price: float):
        self.min_price = min_price
        self.max_price = max_price
    
    def filter(self, product: dict) -> bool:
        price = product.get("price", 0)
        return self.min_price <= price <= self.max_price

# 使用方式
users.filter(AdultUserFilter())
emails.filter(ValidEmailFilter())
products.filter(PriceRangeFilter(10.0, 100.0))
```

## 🔑 键值函数

### KeySelector - 键选择器

```python
from sage.core.api.function import KeySelector

K = TypeVar('K')  # 键类型

class KeySelector(BaseFunction[T, K]):
    """键选择器基类"""
    
    def get_key(self, value: T) -> K:
        """提取元素的键"""
        raise NotImplementedError()

# 示例实现
class UserIdKeySelector(KeySelector[dict, str]):
    def get_key(self, user: dict) -> str:
        return user["id"]

class TimestampKeySelector(KeySelector[dict, int]):
    def get_key(self, event: dict) -> int:
        # 按小时分组
        return event["timestamp"] // 3600

class CompositeKeySelector(KeySelector[dict, tuple]):
    def get_key(self, record: dict) -> tuple:
        return (record["category"], record["region"])

# 使用方式
users.key_by(UserIdKeySelector())
events.key_by(TimestampKeySelector())
sales.key_by(CompositeKeySelector())
```

### ReduceFunction - 归约操作

```python
from sage.core.api.function import ReduceFunction

class ReduceFunction(BaseFunction[T, T]):
    """归约函数基类"""
    
    def reduce(self, value1: T, value2: T) -> T:
        """合并两个相同键的值"""
        raise NotImplementedError()

# 示例实现
class SumReduceFunction(ReduceFunction[int]):
    def reduce(self, value1: int, value2: int) -> int:
        return value1 + value2

class MaxReduceFunction(ReduceFunction[float]):
    def reduce(self, value1: float, value2: float) -> float:
        return max(value1, value2)

class MergeUserFunction(ReduceFunction[dict]):
    def reduce(self, user1: dict, user2: dict) -> dict:
        # 合并用户信息，保留最新时间戳的数据
        if user1.get("timestamp", 0) >= user2.get("timestamp", 0):
            result = user1.copy()
            result.update({k: v for k, v in user2.items() if k != "timestamp"})
        else:
            result = user2.copy()
            result.update({k: v for k, v in user1.items() if k != "timestamp"})
        return result

# 使用方式
numbers.key_by(lambda x: x % 2).reduce(SumReduceFunction())
scores.key_by(lambda x: x["user_id"]).reduce(MaxReduceFunction())
user_updates.key_by(lambda x: x["id"]).reduce(MergeUserFunction())
```

## 📊 聚合函数

### AggregateFunction - 聚合操作

```python
from sage.core.api.function import AggregateFunction

ACC = TypeVar('ACC')  # 累加器类型
OUT = TypeVar('OUT')  # 输出类型

class AggregateFunction(BaseFunction[T, ACC, OUT]):
    """聚合函数基类"""
    
    def create_accumulator(self) -> ACC:
        """创建累加器初始值"""
        raise NotImplementedError()
    
    def add(self, accumulator: ACC, value: T) -> ACC:
        """将新值添加到累加器"""
        raise NotImplementedError()
    
    def get_result(self, accumulator: ACC) -> OUT:
        """从累加器获取最终结果"""
        raise NotImplementedError()
    
    def merge(self, acc1: ACC, acc2: ACC) -> ACC:
        """合并两个累加器（用于分布式聚合）"""
        raise NotImplementedError()

# 示例实现
class CountAggregateFunction(AggregateFunction[Any, int, int]):
    def create_accumulator(self) -> int:
        return 0
    
    def add(self, accumulator: int, value: Any) -> int:
        return accumulator + 1
    
    def get_result(self, accumulator: int) -> int:
        return accumulator
    
    def merge(self, acc1: int, acc2: int) -> int:
        return acc1 + acc2

class AvgAggregateFunction(AggregateFunction[float, tuple, float]):
    def create_accumulator(self) -> tuple:
        return (0.0, 0)  # (sum, count)
    
    def add(self, accumulator: tuple, value: float) -> tuple:
        sum_val, count = accumulator
        return (sum_val + value, count + 1)
    
    def get_result(self, accumulator: tuple) -> float:
        sum_val, count = accumulator
        return sum_val / count if count > 0 else 0.0
    
    def merge(self, acc1: tuple, acc2: tuple) -> tuple:
        return (acc1[0] + acc2[0], acc1[1] + acc2[1])

class TopKAggregateFunction(AggregateFunction[int, list, list]):
    def __init__(self, k: int = 10):
        self.k = k
    
    def create_accumulator(self) -> list:
        return []
    
    def add(self, accumulator: list, value: int) -> list:
        accumulator.append(value)
        accumulator.sort(reverse=True)
        return accumulator[:self.k]
    
    def get_result(self, accumulator: list) -> list:
        return accumulator
    
    def merge(self, acc1: list, acc2: list) -> list:
        merged = acc1 + acc2
        merged.sort(reverse=True)
        return merged[:self.k]
```

## 🔧 处理函数

### ProcessFunction - 通用处理

```python
from sage.core.api.function import ProcessFunction, ProcessContext

class ProcessFunction(BaseFunction[T, U]):
    """通用处理函数，支持副输出、定时器等高级功能"""
    
    def process(self, value: T, ctx: ProcessContext[U]) -> None:
        """处理单个元素"""
        raise NotImplementedError()
    
    def on_timer(self, timestamp: int, ctx: ProcessContext[U]) -> None:
        """定时器回调"""
        pass

# 示例实现
class ValidationFunction(ProcessFunction[dict, dict]):
    def process(self, record: dict, ctx: ProcessContext[dict]):
        # 数据验证
        if self.is_valid(record):
            ctx.emit(record)  # 输出到主流
        else:
            # 输出到错误流
            ctx.output_to_side("errors", f"Invalid: {record}")
    
    def is_valid(self, record: dict) -> bool:
        required_fields = ["id", "timestamp", "data"]
        return all(field in record for field in required_fields)

class SessionTimeoutFunction(ProcessFunction[dict, dict]):
    def __init__(self, timeout_ms: int = 30000):
        self.timeout_ms = timeout_ms
        self.sessions = {}
    
    def process(self, event: dict, ctx: ProcessContext[dict]):
        session_id = event["session_id"]
        current_time = ctx.timestamp()
        
        # 更新会话
        self.sessions[session_id] = current_time
        
        # 设置超时定时器
        ctx.register_timer(current_time + self.timeout_ms)
        
        ctx.emit(event)
    
    def on_timer(self, timestamp: int, ctx: ProcessContext[dict]):
        # 清理超时会话
        expired_sessions = [
            sid for sid, last_time in self.sessions.items()
            if timestamp - last_time >= self.timeout_ms
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            ctx.output_to_side("timeouts", {"session_id": session_id, "timeout": timestamp})
```

## 📤 输入输出函数

### SourceFunction - 数据源

```python
from sage.core.api.function import SourceFunction, SourceContext

class SourceFunction(BaseFunction[None, T]):
    """数据源函数基类"""
    
    def run(self, ctx: SourceContext[T]) -> None:
        """生成数据"""
        raise NotImplementedError()
    
    def cancel(self) -> None:
        """取消数据源"""
        pass

# 示例实现
class CounterSourceFunction(SourceFunction[int]):
    def __init__(self, max_count: int = 100, interval_ms: int = 1000):
        self.max_count = max_count
        self.interval_ms = interval_ms
        self.running = True
    
    def run(self, ctx: SourceContext[int]):
        count = 0
        while self.running and count < self.max_count:
            ctx.emit(count)
            count += 1
            time.sleep(self.interval_ms / 1000.0)
    
    def cancel(self):
        self.running = False

class FileSourceFunction(SourceFunction[str]):
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def run(self, ctx: SourceContext[str]):
        with open(self.file_path, 'r') as f:
            for line in f:
                ctx.emit(line.strip())

class KafkaSourceFunction(SourceFunction[dict]):
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.running = True
    
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
```

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
            "order_time": order["timestamp"]
        }

class ClickImpressionJoinFunction(JoinFunction[dict, dict, dict]):
    def join(self, click: dict, impression: dict) -> dict:
        return {
            "ad_id": click["ad_id"],
            "user_id": click["user_id"],
            "click_time": click["timestamp"],
            "impression_time": impression["timestamp"],
            "conversion_delay": click["timestamp"] - impression["timestamp"]
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
            return f"Security Alert: Failed login attempt by user {user_action['user_id']}"
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
            "timestamp": user_metric["timestamp"]
        }
    
    def map2(self, system_metric: dict) -> dict:
        return {
            "type": "system_metric", 
            "metric": system_metric["metric_name"],
            "value": system_metric["value"],
            "timestamp": system_metric["timestamp"]
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
            return {
                "error": str(e),
                "raw_input": json_str,
                "timestamp": time.time()
            }
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
