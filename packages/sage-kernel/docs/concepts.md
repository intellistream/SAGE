# 核心概念

理解 SAGE Kernel 的核心概念是高效使用框架的基础。本文档介绍框架中的关键概念和术语。

## 🌊 数据流 (DataStream)

### 定义
DataStream 是 SAGE Kernel 中的核心抽象，代表一个**有界**或**无界**的数据序列。

### 特性
- **不可变性**: 每次转换都创建新的数据流
- **延迟执行**: 构建阶段只创建计算图，调用 `submit()` 时才执行
- **类型安全**: 基于泛型的编译时类型检查
- **链式调用**: 支持函数式编程风格

### 示例
```python
# 有界数据流（批处理）
batch_stream = env.from_batch([1, 2, 3, 4, 5])

# 无界数据流（流处理）
stream = env.from_kafka_source("localhost:9092", "events", "group1")

# 链式转换
result = (stream
    .map(parse_json)
    .filter(is_valid)
    .key_by(extract_key)
    .reduce(aggregate))
```

## 🏗️ 环境 (Environment)

### 定义
Environment 定义了数据流应用的执行上下文，管理计算资源、调度策略和服务配置。

### 类型
- **LocalEnvironment**: 本地单机环境
  - 适用于开发、测试和小规模处理
  - 简单易用，无需额外配置
  
- **RemoteEnvironment**: 分布式集群环境
  - 适用于生产环境和大规模处理
  - 支持容错、状态管理、弹性伸缩

### 示例
```python
# 本地环境
local_env = LocalEnvironment("my_app", config={
    "parallelism": 4,
    "buffer_size": 10000
})

# 远程环境
remote_env = RemoteEnvironment("production_app", config={
    "jobmanager_host": "cluster-master",
    "jobmanager_port": 8081,
    "parallelism": 16
})
```

## 🔄 转换 (Transformation)

### 定义
转换是对数据流的操作，将一个数据流转换为另一个数据流。

### 分类

#### 1. 一对一转换
- **Map**: `f(x) → y`
- **Filter**: `f(x) → boolean`

```python
# Map 示例
numbers.map(lambda x: x * 2)

# Filter 示例  
numbers.filter(lambda x: x > 0)
```

#### 2. 一对多转换
- **FlatMap**: `f(x) → [y1, y2, ...]`

```python
# FlatMap 示例
sentences.flat_map(lambda s: s.split())
```

#### 3. 聚合转换
- **Reduce**: 同键值归约
- **Aggregate**: 自定义聚合逻辑

```python
# Reduce 示例
keyed_stream.reduce(lambda a, b: a + b)

# Aggregate 示例
keyed_stream.aggregate(CountAggregateFunction())
```

## 🔑 键值流 (Keyed Stream)

### 定义
通过 `key_by()` 操作将数据流按键分区，相同键的元素路由到同一个处理器。

### 用途
- 状态管理：每个键维护独立状态
- 并行处理：不同键可以并行处理
- 一致性保证：同键元素有序处理

### 示例
```python
# 按用户ID分组
user_events = events.key_by(lambda event: event["user_id"])

# 用户会话统计
user_sessions = user_events.reduce(merge_sessions)

# 复合键
sales.key_by(lambda sale: (sale["region"], sale["category"]))
```

## ⏰ 时间语义

### 时间类型

#### 1. 事件时间 (Event Time)
- 数据实际发生的时间
- 内嵌在数据中
- 支持乱序处理

#### 2. 处理时间 (Processing Time)
- 数据被处理的时间
- 系统时钟时间
- 简单但不准确

#### 3. 摄入时间 (Ingestion Time)
- 数据进入系统的时间
- 事件时间和处理时间的折中

### 示例
```python
# 配置事件时间
env.set_time_characteristic(TimeCharacteristic.EVENT_TIME)

# 提取时间戳
stream.assign_timestamps_and_watermarks(
    timestamp_extractor=lambda event: event["timestamp"],
    watermark_strategy=BoundedOutOfOrdernessWatermarks(Duration.seconds(5))
)
```

## 🪟 窗口 (Window)

### 定义
窗口将无界流分割成有界的数据块，支持在流上进行聚合操作。

### 窗口类型

#### 1. 时间窗口
- **滚动窗口**: 固定大小，无重叠
- **滑动窗口**: 固定大小，可重叠
- **会话窗口**: 动态大小，基于活动间隔

```python
# 滚动时间窗口 - 每5分钟
windowed = keyed_stream.window(TumblingTimeWindows.of(Duration.minutes(5)))

# 滑动时间窗口 - 10分钟窗口，每1分钟滑动
windowed = keyed_stream.window(SlidingTimeWindows.of(
    Duration.minutes(10), Duration.minutes(1)))

# 会话窗口 - 30秒不活跃关闭
windowed = keyed_stream.window(SessionWindows.withGap(Duration.seconds(30)))
```

#### 2. 计数窗口
- **滚动计数窗口**: 固定元素数量
- **滑动计数窗口**: 固定数量，可重叠

```python
# 滚动计数窗口 - 每100个元素
windowed = keyed_stream.window(TumblingCountWindows.of(100))

# 滑动计数窗口 - 100个元素，每10个滑动
windowed = keyed_stream.window(SlidingCountWindows.of(100, 10))
```

## 🚰 水位线 (Watermark)

### 定义
水位线是衡量事件时间进度的机制，用于处理乱序数据和触发窗口计算。

### 特性
- 表示"时间戳T之前的事件已全部到达"
- 允许一定程度的延迟和乱序
- 触发窗口的关闭和计算

### 示例
```python
# 固定延迟水位线
watermark_strategy = BoundedOutOfOrdernessWatermarks(Duration.seconds(5))

# 自定义水位线生成器
class CustomWatermarkStrategy(WatermarkStrategy):
    def create_watermark_generator(self):
        return CustomWatermarkGenerator()

stream.assign_timestamps_and_watermarks(watermark_strategy)
```

## 🔄 状态管理

### 状态类型

#### 1. 键控状态 (Keyed State)
- 与特定键关联
- 自动分区和恢复
- 支持多种状态类型

```python
class StatefulFunction(ProcessFunction):
    def __init__(self):
        self.value_state = None  # 单值状态
        self.list_state = None   # 列表状态
        self.map_state = None    # 映射状态
    
    def open(self, context):
        # 初始化状态
        self.value_state = context.get_keyed_state("count", int, 0)
        self.list_state = context.get_list_state("history", str)
        self.map_state = context.get_map_state("cache", str, dict)
```

#### 2. 算子状态 (Operator State)
- 与算子实例关联
- 手动分区和恢复
- 用于非键控场景

### 状态后端
- **内存状态后端**: 快速但不持久
- **文件系统状态后端**: 持久化到磁盘
- **RocksDB状态后端**: 大状态支持

## 🛡️ 容错机制

### 检查点 (Checkpoint)

#### 定义
定期保存应用状态快照，用于故障恢复。

#### 特性
- 分布式快照算法
- 精确一次语义保证
- 异步非阻塞

```python
# 启用检查点
env.enable_checkpointing(Duration.seconds(30))

# 检查点配置
env.set_checkpoint_config(CheckpointConfig(
    min_pause_between_checkpoints=Duration.seconds(5),
    max_concurrent_checkpoints=1,
    checkpoint_timeout=Duration.minutes(10)
))
```

### 保存点 (Savepoint)

#### 定义
手动触发的检查点，用于应用升级、迁移等场景。

```python
# 创建保存点
savepoint_path = env.create_savepoint()

# 从保存点恢复
env.restore_from_savepoint("hdfs://path/to/savepoint")
```

### 重启策略

```python
# 固定延迟重启
env.set_restart_strategy(RestartStrategies.fixed_delay(
    restart_attempts=3,
    delay=Duration.seconds(10)
))

# 指数退避重启
env.set_restart_strategy(RestartStrategies.exponential_delay(
    initial_backoff=Duration.seconds(1),
    max_backoff=Duration.minutes(1),
    backoff_multiplier=2.0,
    reset_backoff_threshold=Duration.minutes(10)
))
```

## 🔗 连接器 (Connector)

### 定义
连接器是连接外部系统的组件，包括数据源和数据汇。

### 常用连接器

#### 数据源
- **KafkaSource**: 从Kafka消费数据
- **FileSource**: 从文件系统读取
- **SocketSource**: 从Socket连接读取

#### 数据汇
- **KafkaSink**: 写入Kafka
- **FileSink**: 写入文件系统
- **DatabaseSink**: 写入数据库

### 示例
```python
# Kafka源
kafka_source = env.from_kafka_source(
    bootstrap_servers="localhost:9092",
    topic="input_topic",
    group_id="my_consumer_group"
)

# 文件汇
result.sink_to_file("output.txt", format="json")
```

## 📊 执行图 (Execution Graph)

### 定义
执行图是数据流应用的内部表示，描述了数据流动和转换关系。

### 组成
- **节点**: 转换算子
- **边**: 数据流动
- **分区**: 数据分布策略

### 优化
- 算子链接 (Operator Chaining)
- 算子融合 (Operator Fusion)
- 资源分配优化

## 🎯 语义保证

### 精确一次 (Exactly-Once)
- 每条记录被精确处理一次
- 需要支持的源和汇
- 开启检查点

### 至少一次 (At-Least-Once)
- 每条记录至少被处理一次
- 可能有重复处理
- 更容易实现

### 至多一次 (At-Most-Once)
- 每条记录最多被处理一次
- 可能有数据丢失
- 性能最好

## 📚 总结

这些核心概念构成了 SAGE Kernel 的理论基础：

1. **DataStream**: 数据抽象
2. **Environment**: 执行上下文
3. **Transformation**: 数据转换
4. **Time & Window**: 时间处理
5. **State**: 状态管理
6. **Fault Tolerance**: 容错机制

理解这些概念将帮助你更好地设计和实现流数据处理应用。
