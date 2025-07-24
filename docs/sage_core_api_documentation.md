# SAGE 核心 API 文档

## 概述

SAGE (Stream Analytics General Engine) 是一个高性能的流式数据处理框架，提供了丰富的API来构建和执行数据处理管道。本文档详细介绍了SAGE核心模块的API设计和使用方法。

## 目录

1. [环境管理 (Environment)](#环境管理)
2. [数据流 (DataStream)](#数据流)
3. [连接流 (ConnectedStreams)](#连接流)
4. [函数 (Functions)](#函数)
5. [操作符 (Operators)](#操作符)
6. [使用示例](#使用示例)

---

## 环境管理

### BaseEnvironment

环境是SAGE框架的入口点，负责管理数据流管道的生命周期和执行。

#### 类层次结构
```python
BaseEnvironment (抽象基类)
├── LocalEnvironment     # 本地执行环境
└── RemoteEnvironment    # 远程分布式执行环境
```

#### 核心方法

##### 数据源创建

```python
def from_source(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> DataStream:
    """
    创建数据源流
    
    Args:
        function: 源函数类或lambda函数
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        DataStream: 可用于构建管道的数据流
        
    Example:
        # 使用类
        stream = env.from_source(MySourceFunction, param1="value")
        
        # 使用lambda (会自动包装)
        stream = env.from_source(lambda: generate_data())
    """
```

```python
def from_kafka_source(self, 
                     bootstrap_servers: str,
                     topic: str,
                     group_id: str,
                     auto_offset_reset: str = 'latest',
                     value_deserializer: str = 'json',
                     buffer_size: int = 10000,
                     max_poll_records: int = 500,
                     **kafka_config) -> DataStream:
    """
    创建Kafka数据源，采用Flink兼容的架构设计
    
    Args:
        bootstrap_servers: Kafka集群地址 (例: "localhost:9092")
        topic: Kafka主题名称
        group_id: 消费者组ID，用于offset管理
        auto_offset_reset: offset重置策略 ('latest'/'earliest'/'none')
        value_deserializer: 反序列化方式 ('json'/'string'/'bytes'或自定义函数)
        buffer_size: 本地缓冲区大小，防止数据丢失
        max_poll_records: 每次poll的最大记录数，控制批处理大小
        **kafka_config: 其他Kafka Consumer配置参数
        
    Returns:
        DataStream: 可用于构建处理pipeline的数据流
        
    Example:
        kafka_stream = env.from_kafka_source(
            bootstrap_servers="localhost:9092",
            topic="user_events", 
            group_id="sage_consumer"
        )
        
        result = (kafka_stream
                 .map(ProcessEventFunction)
                 .filter(FilterFunction)
                 .sink(OutputSinkFunction))
    """
```

```python
def from_future(self, name: str) -> DataStream:
    """
    创建future stream，用于构建具有循环依赖的管道
    
    Args:
        name: future stream的唯一名称
        
    Returns:
        DataStream: future数据流，需要后续通过fill_future()填充
        
    Example:
        # 1. 声明future stream
        future_stream = env.from_future("feedback_loop")
        
        # 2. 构建包含future stream的管道
        result = source.connect(future_stream).comap(CombineFunction)
        
        # 3. 创建反馈边
        processed = result.filter(SomeFilter)
        processed.fill_future(future_stream)
    """
```

##### 内存管理

```python
def set_memory(self, config=None):
    """
    设置环境的内存配置
    
    Args:
        config: 内存配置参数
    """
```

##### 环境控制

```python
@abstractmethod
def submit(self):
    """提交环境，开始执行管道"""
    
def close(self):
    """关闭环境，停止所有任务"""
```

### LocalEnvironment

本地执行环境，在单机上运行数据处理管道。

```python
class LocalEnvironment(BaseEnvironment):
    """本地环境，直接使用本地JobManager实例"""

    def __init__(self, name: str, config: dict | None = None):
        """
        初始化本地环境
        
        Args:
            name: 环境名称
            config: 环境配置
        """
```

### RemoteEnvironment

远程分布式执行环境，通过客户端连接远程JobManager。

```python
class RemoteEnvironment(BaseEnvironment):
    """远程环境，通过客户端连接远程JobManager"""

    def __init__(self, name: str, config: dict | None = None, host: str = "127.0.0.1", port: int = 19001):
        """
        初始化远程环境
        
        Args:
            name: 环境名称
            config: 环境配置
            host: 远程JobManager主机地址
            port: 远程JobManager端口
        """
```

---

## 数据流

### DataStream[T]

表示单个transformation生成的流结果，是SAGE中最核心的抽象。

#### 基础变换操作

##### map() - 一对一变换
```python
def map(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
    """
    对每个数据元素应用变换函数
    
    Args:
        function: 映射函数类或lambda函数
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        DataStream: 变换后的数据流
        
    Example:
        # 使用类
        stream.map(AddOneFunction)
        
        # 使用lambda
        stream.map(lambda x: x + 1)
        
        # 带参数
        stream.map(MultiplyFunction, factor=2)
    """
```

##### filter() - 过滤
```python
def filter(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
    """
    过滤数据元素
    
    Args:
        function: 过滤函数，返回True的元素被保留
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        DataStream: 过滤后的数据流
        
    Example:
        # 过滤偶数
        stream.filter(lambda x: x % 2 == 0)
        
        # 使用类
        stream.filter(PositiveNumberFilter)
    """
```

##### flatmap() - 一对多变换
```python
def flatmap(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
    """
    将每个元素展开为多个元素
    
    Args:
        function: 展开函数，返回可迭代对象
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        DataStream: 展开后的数据流
        
    Example:
        # 将字符串拆分为单词
        stream.flatmap(lambda text: text.split())
        
        # 生成数字序列
        stream.flatmap(lambda n: range(n))
    """
```

##### keyby() - 分区
```python
def keyby(self, function: Union[Type[BaseFunction], callable],
          strategy: str = "hash", *args, **kwargs) -> "DataStream":
    """
    按键对数据流进行分区
    
    Args:
        function: 键提取函数
        strategy: 分区策略 ("hash", "round_robin", "custom")
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        DataStream: 按键分区的数据流
        
    Example:
        # 按用户ID分区
        stream.keyby(lambda record: record["user_id"])
        
        # 按多个字段分区
        stream.keyby(lambda record: (record["dept"], record["team"]))
    """
```

##### sink() - 数据输出
```python
def sink(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> "DataStream":
    """
    将数据输出到外部系统
    
    Args:
        function: 输出函数类或lambda函数
        *args, **kwargs: 传递给函数的参数
        
    Returns:
        DataStream: 当前流（用于链式调用）
        
    Example:
        # 输出到文件
        stream.sink(FileSink, path="/tmp/output.txt")
        
        # 输出到数据库
        stream.sink(DatabaseSink, connection_string="...")
        
        # 输出到控制台
        stream.sink(lambda data: print(data))
    """
```

#### 流连接操作

##### connect() - 连接流
```python
def connect(self, other: Union["DataStream", "ConnectedStreams"]) -> 'ConnectedStreams':
    """
    连接两个数据流，返回ConnectedStreams
    
    Args:
        other: 另一个DataStream或ConnectedStreams实例
        
    Returns:
        ConnectedStreams: 新的连接流，按顺序包含所有transformation
        
    Example:
        # 连接两个流
        connected = stream1.connect(stream2)
        
        # 连接多个流
        multi_connected = stream1.connect(stream2).connect(stream3)
    """
```

##### fill_future() - 填充future流
```python
def fill_future(self, future_stream: "DataStream") -> None:
    """
    将当前数据流填充到预先声明的future stream中，创建反馈边
    
    Args:
        future_stream: 需要被填充的future stream
        
    Raises:
        ValueError: 如果目标stream不是future stream
        RuntimeError: 如果future stream已经被填充过
        
    Example:
        # 1. 声明future stream
        future_stream = env.from_future("feedback_loop")
        
        # 2. 构建pipeline，使用future stream
        result = source.connect(future_stream).comap(CombineFunction)
        
        # 3. 填充future stream，创建反馈边
        processed_result = result.filter(SomeFilter)
        processed_result.fill_future(future_stream)
    """
```

#### 便捷方法

##### print() - 快速调试
```python
def print(self, prefix: str = "", separator: str = " | ", colored: bool = True) -> "DataStream":
    """
    便捷的打印方法 - 将数据流输出到控制台
    
    Args:
        prefix: 输出前缀，默认为空
        separator: 前缀与内容之间的分隔符，默认为 " | "
        colored: 是否启用彩色输出，默认为True
        
    Returns:
        DataStream: 返回新的数据流用于链式调用
        
    Example:
        stream.map(some_function).print("Debug").sink(FileSink, config)
        stream.print("结果: ")  # 带前缀打印
        stream.print()  # 简单打印
    """
```

---

## 连接流

### ConnectedStreams

表示多个transformation连接后的流结果，支持多流操作。

#### 基础变换操作

ConnectedStreams支持与DataStream相同的基础操作：`map()`, `sink()`, `print()`, `connect()`。

#### 多流专用操作

##### comap() - 协同映射
```python
def comap(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> 'DataStream':
    """
    Apply a CoMap function that processes each connected stream separately
    
    CoMap (Co-processing Map) enables parallel processing of multiple input streams
    where each stream is processed independently using dedicated mapN methods.
    
    Args:
        function: CoMap function class that implements map0, map1, ..., mapN methods
        *args: Additional constructor arguments for the function class
        **kwargs: Additional constructor arguments for the function class
        
    Returns:
        DataStream: Result stream from coordinated processing of all input streams
        
    Raises:
        NotImplementedError: Lambda functions are not supported for comap operations
        TypeError: If function is not a valid CoMap function
        ValueError: If function doesn't support the required number of input streams
        
    Example:
        class ProcessorCoMap(BaseCoMapFunction):
            def map0(self, data):
                return f"Stream 0: {data}"
            
            def map1(self, data):
                return f"Stream 1: {data * 2}"
        
        result = (stream1
            .connect(stream2)
            .comap(ProcessorCoMap)
            .print("CoMap Result"))
    """
```

##### join() - 流连接
```python
def join(self, function: Union[Type[BaseJoinFunction], callable], *args, **kwargs) -> 'DataStream':
    """
    Join two keyed streams using a join function.
    
    Args:
        function: Join function class implementing BaseJoinFunction
        *args, **kwargs: Arguments passed to join function constructor
        
    Returns:
        DataStream: Stream of join results
        
    Example:
        class UserOrderJoin(BaseJoinFunction):
            def execute(self, payload, key, tag):
                # tag 0: user data, tag 1: order data
                # 实现join逻辑并返回结果列表
                return [joined_result] if match else []
        
        result = (user_stream
            .keyby(lambda x: x["user_id"])
            .connect(order_stream.keyby(lambda x: x["user_id"]))
            .join(UserOrderJoin)
            .sink(OutputSink))
    """
```

---

## 函数

### 函数层次结构

```python
BaseFunction (抽象基类)
├── SourceFunction          # 数据源函数
├── MapFunction             # 映射函数  
├── FilterFunction          # 过滤函数
├── FlatMapFunction         # 展开映射函数
├── KeyByFunction           # 分区键提取函数
├── SinkFunction            # 数据输出函数
├── BaseCoMapFunction       # 协同映射函数
├── BaseJoinFunction        # 流连接函数
├── MemoryFunction          # 内存相关函数
└── StatefulFunction        # 有状态函数
```

### BaseFunction

所有函数的基类，定义了核心接口。

```python
class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    """
    
    def __init__(self, ctx: 'RuntimeContext' = None, **kwargs):
        """
        初始化函数
        
        Args:
            ctx: 运行时上下文，包含日志器、配置等
            **kwargs: 其他初始化参数
        """
        
    @property
    def logger(self):
        """获取日志器"""
        
    @property  
    def name(self):
        """获取函数名称"""
        
    @abstractmethod
    def execute(self, data: Any):
        """
        执行函数逻辑
        
        Args:
            data: 输入数据
            
        Returns:
            处理后的数据
        """
```

### SourceFunction

数据源函数，不接收输入数据，只产生输出数据。

```python
class SourceFunction(BaseFunction):
    """
    源函数基类 - 数据生产者
    """
    
    @abstractmethod
    def execute(self) -> Any:
        """
        执行源函数逻辑，生产数据
        
        Returns:
            生产的数据，返回None表示数据源结束
            
        Example:
            class NumberSource(SourceFunction):
                def __init__(self, **kwargs):
                    super().__init__(**kwargs)
                    self.current = 0
                    self.max_count = 10
                
                def execute(self):
                    if self.current >= self.max_count:
                        return None  # 数据源结束
                    
                    result = self.current
                    self.current += 1
                    return result
        """
```

### MapFunction

一对一数据变换函数。

```python
class MapFunction(BaseFunction):
    """
    映射函数基类 - 一对一数据变换
    """
    
    @abstractmethod
    def execute(self, data: Any) -> Any:
        """
        执行映射变换
        
        Args:
            data: 输入数据
            
        Returns:
            变换后的数据
            
        Example:
            class AddOneFunction(MapFunction):
                def execute(self, data):
                    return data + 1
                    
            class FormatFunction(MapFunction):
                def __init__(self, template="{}", **kwargs):
                    super().__init__(**kwargs)
                    self.template = template
                    
                def execute(self, data):
                    return self.template.format(data)
        """
```

### BaseCoMapFunction

协同映射函数，处理多输入流的分别处理操作。

```python
class BaseCoMapFunction(BaseFunction):
    """
    Base class for CoMap functions that process multiple inputs separately.
    """
    
    @property 
    def is_comap(self) -> bool:
        """Identify this as a CoMap function for operator routing"""
        return True
    
    @abstractmethod
    def map0(self, data: Any) -> Any:
        """
        Process data from input stream 0 (required)
        
        Args:
            data: Data from the first input stream
            
        Returns:
            Processed result for stream 0
        """
    
    @abstractmethod
    def map1(self, data: Any) -> Any:
        """
        Process data from input stream 1 (required)
        
        Args:
            data: Data from the second input stream
            
        Returns:
            Processed result for stream 1
        """
    
    def map2(self, data: Any) -> Any:
        """Process data from input stream 2 (optional)"""
        raise NotImplementedError(f"map2 not implemented for {self.__class__.__name__}")
        
    # ... 支持更多mapN方法
    
    def execute(self, data: Any) -> Any:
        """
        Standard execute method for compatibility.
        For CoMap functions, this should not be called directly.
        """
        raise NotImplementedError("CoMap functions use mapN methods, not execute")

# Example:
class OrderPaymentCoMap(BaseCoMapFunction):
    def map0(self, order_data):
        # 处理订单流
        return {
            "type": "processed_order",
            "order_id": order_data["id"],
            "amount": order_data["amount"]
        }
    
    def map1(self, payment_data):
        # 处理支付流
        return {
            "type": "processed_payment", 
            "payment_id": payment_data["id"],
            "status": payment_data["status"]
        }
```

### BaseJoinFunction

流连接函数，处理多流数据的连接操作。

```python
class BaseJoinFunction(BaseFunction):
    """
    Base class for Join functions that handle multi-stream data joining.
    """
    
    @property 
    def is_join(self) -> bool:
        """Identify this as a Join function for operator routing"""
        return True
    
    @abstractmethod
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        """
        Process data from a specific stream and return join results.
        
        Args:
            payload: The actual data from the stream
            key: The partition key (extracted by keyby)
            tag: Stream identifier (0=left/first stream, 1=right/second stream)
            
        Returns:
            List[Any]: List of join results to emit (can be empty)
        """

# Example: Inner Join
class UserOrderInnerJoin(BaseJoinFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}      # {user_id: user_data}
        self.order_cache = {}     # {user_id: [order_data, ...]}
    
    def execute(self, payload: Any, key: Any, tag: int) -> List[Any]:
        results = []
        
        if tag == 0:  # 用户数据流
            self.user_cache[key] = payload
            
            # 检查是否有对应的订单
            if key in self.order_cache:
                user_data = payload
                for order_data in self.order_cache[key]:
                    joined = {
                        "user_id": key,
                        "user_name": user_data.get("name"),
                        "order_id": order_data.get("id"),
                        "order_amount": order_data.get("amount")
                    }
                    results.append(joined)
                del self.order_cache[key]
                
        elif tag == 1:  # 订单数据流
            if key in self.user_cache:
                user_data = self.user_cache[key]
                joined = {
                    "user_id": key,
                    "user_name": user_data.get("name"),
                    "order_id": payload.get("id"),
                    "order_amount": payload.get("amount")
                }
                results.append(joined)
            else:
                # 缓存订单等待用户数据
                if key not in self.order_cache:
                    self.order_cache[key] = []
                self.order_cache[key].append(payload)
        
        return results
```

### StatefulFunction

有状态函数，支持状态自动持久化和恢复。

```python
class StatefulFunction(BaseFunction):
    """
    有状态算子基类：自动在init恢复状态，并可通过save_state()持久化。
    """
    # 子类可覆盖：只保存include中字段
    __state_include__ = []
    # 默认排除logger、私有属性和runtime_context
    __state_exclude__ = ['logger', '_logger', 'ctx']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 自动恢复上次checkpoint
        chkpt_dir = os.path.join(self.ctx.env_base_dir, ".sage_checkpoints")
        chkpt_path = os.path.join(chkpt_dir, f"{self.ctx.name}.chkpt")
        load_function_state(self, chkpt_path)

    def save_state(self):
        """将当前对象状态持久化到disk"""
        base = os.path.join(self.ctx.env_base_dir, ".sage_checkpoints")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{self.ctx.name}.chkpt")
        save_function_state(self, path)

# Example:
class CounterFunction(StatefulFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0  # 这个状态会被自动持久化
        
    def execute(self, data):
        self.count += 1
        if self.count % 100 == 0:
            self.save_state()  # 定期保存状态
        return f"Processed {self.count} items: {data}"
```

---

## 操作符

操作符是执行函数的运行时组件，负责数据包的接收、处理和转发。

### BaseOperator

所有操作符的基类。

```python
class BaseOperator(ABC):
    """所有操作符的基类"""
    
    def __init__(self, 
                 function_factory: 'FunctionFactory', 
                 ctx: 'RuntimeContext', 
                 *args, **kwargs):
        """
        初始化操作符
        
        Args:
            function_factory: 函数工厂，用于创建函数实例
            ctx: 运行时上下文
        """
        
    def receive_packet(self, packet: 'Packet'):
        """接收数据包并处理"""
        
    @abstractmethod
    def process_packet(self, packet: 'Packet' = None):
        """处理数据包（子类实现）"""
        
    def handle_stop_signal(self, stop_signal: StopSignal):
        """处理停止信号"""
```

### SourceOperator

源操作符，负责生成数据。

```python
class SourceOperator(BaseOperator):
    """源操作符 - 数据生产者"""
    
    def process_packet(self, packet: 'Packet' = None):
        """
        处理数据包，调用源函数生成数据
        """
        try:
            result = self.function.execute()
            
            if isinstance(result, StopSignal):
                # 数据源结束
                self.router.send_stop_signal(result)
                self.task.stop()
                return
                
            if result is not None:
                self.router.send(Packet(result))
                
        except Exception as e:
            self.logger.error(f"Error in {self.name}.process(): {e}")
```

### CoMapOperator

协同映射操作符，处理多输入流的分别处理。

```python
class CoMapOperator(BaseOperator):
    """
    CoMap操作符 - 处理多输入流的分别处理操作
    """
    
    def process_packet(self, packet: 'Packet' = None):
        """CoMap处理多输入，保持分区信息"""
        try:
            if packet is None or packet.payload is None:
                return
            
            # 根据输入索引调用对应的mapN方法
            input_index = packet.input_index
            map_method = getattr(self.function, f'map{input_index}')
            result = map_method(packet.payload)
            
            if result is not None:
                # 继承原packet的分区信息
                result_packet = packet.inherit_partition_info(result)
                self.router.send(result_packet)
                
        except Exception as e:
            self.logger.error(f"Error in CoMapOperator {self.name}: {e}")
```

---

## 使用示例

### 基础数据处理管道

```python
from sage_core.api.local_environment import LocalEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.map_function import MapFunction
from sage_core.function.filter_function import FilterFunction
from sage_core.function.sink_function import SinkFunction

# 1. 创建环境
env = LocalEnvironment("basic_pipeline")

# 2. 定义函数
class NumberSource(SourceFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current = 0
        self.max_count = 100
    
    def execute(self):
        if self.current >= self.max_count:
            return None
        result = self.current
        self.current += 1
        return result

class SquareFunction(MapFunction):
    def execute(self, data):
        return data * data

class EvenFilter(FilterFunction):
    def execute(self, data):
        return data % 2 == 0

class PrintSink(SinkFunction):
    def execute(self, data):
        print(f"Result: {data}")

# 3. 构建管道
result = (env
    .from_source(NumberSource)
    .map(SquareFunction)
    .filter(EvenFilter)
    .sink(PrintSink)
)

# 4. 执行
env.submit()
```

### Kafka数据处理

```python
# 1. 创建Kafka数据源
kafka_stream = env.from_kafka_source(
    bootstrap_servers="localhost:9092",
    topic="user_events",
    group_id="sage_analytics"
)

# 2. 处理事件数据
class EventParser(MapFunction):
    def execute(self, kafka_record):
        return {
            "user_id": kafka_record["user_id"],
            "event_type": kafka_record["event_type"], 
            "timestamp": kafka_record["timestamp"],
            "properties": kafka_record.get("properties", {})
        }

class ImportantEventFilter(FilterFunction):
    def execute(self, event):
        important_events = ["purchase", "signup", "login"]
        return event["event_type"] in important_events

# 3. 构建处理管道
result = (kafka_stream
    .map(EventParser)
    .filter(ImportantEventFilter)
    .keyby(lambda event: event["user_id"])
    .sink(DatabaseSink, connection_string="postgresql://..."))

env.submit()
```

### 多流CoMap处理

```python
class OrderPaymentCoMap(BaseCoMapFunction):
    def map0(self, order_data):
        return {
            "type": "processed_order",
            "order_id": order_data["id"],
            "user_id": order_data["user_id"],
            "amount": order_data["amount"]
        }
    
    def map1(self, payment_data):
        return {
            "type": "processed_payment",
            "payment_id": payment_data["id"],
            "order_id": payment_data["order_id"],
            "status": payment_data["status"]
        }

# 构建CoMap管道
order_stream = env.from_source(OrderSource)
payment_stream = env.from_source(PaymentSource)

result = (order_stream
    .connect(payment_stream)
    .comap(OrderPaymentCoMap)
    .print("CoMap Result")
    .sink(OutputSink))
```

### 流连接(Join)处理

```python
class UserOrderJoin(BaseJoinFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_cache = {}
        self.order_cache = {}
    
    def execute(self, payload, key, tag):
        results = []
        
        if tag == 0:  # 用户流
            self.user_cache[key] = payload
            if key in self.order_cache:
                for order in self.order_cache[key]:
                    results.append(self._join_user_order(payload, order, key))
                del self.order_cache[key]
        
        elif tag == 1:  # 订单流
            if key in self.user_cache:
                user = self.user_cache[key]
                results.append(self._join_user_order(user, payload, key))
            else:
                if key not in self.order_cache:
                    self.order_cache[key] = []
                self.order_cache[key].append(payload)
        
        return results
    
    def _join_user_order(self, user, order, user_id):
        return {
            "user_id": user_id,
            "user_name": user["name"],
            "order_id": order["id"],
            "amount": order["amount"]
        }

# 构建Join管道
user_stream = env.from_source(UserSource)
order_stream = env.from_source(OrderSource)

result = (user_stream
    .keyby(lambda user: user["id"])
    .connect(order_stream.keyby(lambda order: order["user_id"]))
    .join(UserOrderJoin)
    .sink(ResultSink))
```

### Future流和反馈边

```python
# 1. 创建future流用于反馈
feedback_stream = env.from_future("iteration_feedback")

# 2. 构建包含反馈的管道
source = env.from_source(InitialDataSource)

# 主处理流
main_result = (source
    .connect(feedback_stream)
    .comap(CombineInputsCoMap)
    .map(ProcessFunction))

# 3. 创建反馈边
feedback_data = (main_result
    .filter(lambda x: x["should_feedback"])
    .map(lambda x: x["feedback_value"]))

# 4. 填充future流
feedback_data.fill_future(feedback_stream)

# 5. 输出最终结果
main_result.filter(lambda x: x["is_final"]).sink(OutputSink)

env.submit()
```

## 最佳实践

### 1. 错误处理

```python
class SafeMapFunction(MapFunction):
    def execute(self, data):
        try:
            return self.process_data(data)
        except Exception as e:
            self.logger.error(f"Error processing data {data}: {e}")
            return None  # 或返回默认值
    
    def process_data(self, data):
        # 具体的处理逻辑
        return data * 2
```

### 2. 状态管理

```python
class WindowedAggregator(StatefulFunction):
    __state_include__ = ['window_data', 'window_start']
    
    def __init__(self, window_size_ms=5000, **kwargs):
        super().__init__(**kwargs)
        self.window_size_ms = window_size_ms
        self.window_data = []
        self.window_start = None
        
    def execute(self, data):
        current_time = int(time.time() * 1000)
        
        # 初始化窗口
        if self.window_start is None:
            self.window_start = current_time
            
        # 检查是否需要触发窗口
        if current_time - self.window_start >= self.window_size_ms:
            result = self.compute_window_result()
            self.reset_window(current_time)
            self.save_state()  # 保存状态
            return result
            
        # 添加数据到窗口
        self.window_data.append(data)
        return None
```

### 3. 资源清理

```python
class DatabaseSink(SinkFunction):
    def __init__(self, connection_string, **kwargs):
        super().__init__(**kwargs)
        self.connection_string = connection_string
        self.connection = None
        
    def execute(self, data):
        if self.connection is None:
            self.connection = create_connection(self.connection_string)
        
        try:
            self.insert_data(data)
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            # 重连逻辑
            self.connection = create_connection(self.connection_string)
            
    def __del__(self):
        if self.connection:
            self.connection.close()
```

### 4. 性能优化

```python
class BatchProcessor(MapFunction):
    def __init__(self, batch_size=100, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.batch = []
        
    def execute(self, data):
        self.batch.append(data)
        
        if len(self.batch) >= self.batch_size:
            result = self.process_batch(self.batch)
            self.batch = []
            return result
            
        return None  # 批次未满，不输出
        
    def process_batch(self, batch):
        # 批量处理逻辑
        return [self.transform(item) for item in batch]
```

---

## 总结

SAGE框架提供了完整的流式数据处理API，主要特点包括：

1. **简洁的API设计**：链式调用，易于构建复杂管道
2. **丰富的操作类型**：支持map、filter、join、comap等多种操作
3. **灵活的执行环境**：本地和远程执行支持
4. **强大的状态管理**：自动状态持久化和恢复
5. **高度可扩展**：基于函数和操作符的插件式架构

通过合理使用这些API，可以构建高性能、可靠的流式数据处理应用。
