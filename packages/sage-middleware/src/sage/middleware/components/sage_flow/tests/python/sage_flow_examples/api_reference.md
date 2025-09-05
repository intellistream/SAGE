# SAGE Flow Python API 参考

本文档提供了 SAGE Flow Python 绑定的完整 API 参考。

## 📦 模块导入

```python
import sage_flow_datastream as sfd
```

## 🏗️ 核心类

### Environment 类

环境管理类，用于创建和管理数据流。

```python
class Environment:
    def __init__(self, job_name: str)
    def create_datastream(self) -> DataStream
    def submit(self) -> None
    def close(self) -> None
```

**方法说明：**
- `__init__(job_name)`: 创建环境实例
- `create_datastream()`: 创建新的数据流
- `submit()`: 提交作业执行
- `close()`: 关闭环境并清理资源

### DataStream 类

数据流处理的核心类。

```python
class DataStream:
    def from_source(self, source_func) -> DataStream
    def map(self, map_func) -> DataStream
    def filter(self, filter_func) -> DataStream
    def sink(self, sink_func) -> None
    def execute(self) -> None
    def execute_async(self) -> None
    def stop(self) -> None
```

**方法说明：**
- `from_source(source_func)`: 设置数据源函数
- `map(map_func)`: 添加映射转换
- `filter(filter_func)`: 添加过滤条件
- `sink(sink_func)`: 设置数据输出函数
- `execute()`: 同步执行流处理
- `execute_async()`: 异步执行流处理
- `stop()`: 停止流处理

### MultiModalMessage 类

多模态消息类，用于封装各种类型的数据。

```python
class MultiModalMessage:
    def __init__(self, uid: int, content_type: ContentType, content)
    def get_uid(self) -> int
    def get_content_type(self) -> ContentType
    def get_content(self)
    def get_metadata(self) -> dict
    def set_content(self, content) -> None
    def set_metadata(self, key: str, value) -> None
```

**属性说明：**
- `uid`: 消息唯一标识符
- `content_type`: 内容类型（TEXT, BINARY, IMAGE, etc.）
- `content`: 消息内容
- `metadata`: 元数据字典

## 🔧 工具函数

### 消息创建函数

```python
def create_text_message(uid: int, text: str) -> MultiModalMessage
def create_binary_message(uid: int, data: bytes) -> MultiModalMessage
```

**参数说明：**
- `uid`: 消息唯一标识符
- `text`: 文本内容
- `data`: 二进制数据

### 内容类型枚举

```python
class ContentType:
    TEXT = "text"
    BINARY = "binary"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    EMBEDDING = "embedding"
    METADATA = "metadata"
```

## 📊 数据源类

### FileDataSource 类

文件数据源，用于从文件系统读取数据。

```python
class FileDataSource(DataSource):
    def __init__(self)
    def initialize(self, config: DataSourceConfig) -> bool
    def has_next(self) -> bool
    def next_message(self) -> MultiModalMessage
    def close(self) -> None
```

**支持的文件格式：**
- 纯文本文件 (.txt)
- CSV 文件 (.csv)
- JSON 文件 (.json)
- 其他结构化格式

### KafkaDataSource 类

Kafka 数据源，用于从 Kafka 主题消费消息。

```python
class KafkaDataSource(DataSource):
    def __init__(self)
    def initialize(self, config: DataSourceConfig) -> bool
    def has_next(self) -> bool
    def next_message(self) -> MultiModalMessage
    def close(self) -> None
```

**配置参数：**
- `broker_list`: Kafka broker 列表
- `topic`: 主题名称
- `consumer_group`: 消费者组
- `auto_offset_reset`: 偏移量重置策略

## ⚙️ 配置类

### DataSourceConfig 类

数据源配置类。

```python
class DataSourceConfig:
    def __init__(self)
    def set_property(self, key: str, value) -> None
    def get_property(self, key: str)
```

### EnvironmentConfig 类

环境配置类。

```python
class EnvironmentConfig:
    def __init__(self, job_name: str = "")
    @property
    def job_name(self) -> str
    @property
    def memory_config(self)
    @property
    def properties(self) -> dict
```

## 🔄 操作符类

### BaseOperator 类

基础操作符类。

```python
class BaseOperator:
    def get_type(self) -> OperatorType
    def get_name(self) -> str
    def set_name(self, name: str) -> None
    def get_processed_count(self) -> int
    def get_output_count(self) -> int
    def reset_counters(self) -> None
```

### 操作符类型枚举

```python
class OperatorType:
    SOURCE = "source"
    MAP = "map"
    FILTER = "filter"
    SINK = "sink"
```

## 📈 向量数据类

### VectorData 类

向量数据处理类。

```python
class VectorData:
    def __init__(self, data: List[float], dimension: int)
    def get_data(self) -> List[float]
    def get_dimension(self) -> int
    def dot_product(self, other: VectorData) -> float
    def cosine_similarity(self, other: VectorData) -> float
    def euclidean_distance(self, other: VectorData) -> float
```

**方法说明：**
- `dot_product()`: 计算点积
- `cosine_similarity()`: 计算余弦相似度
- `euclidean_distance()`: 计算欧几里得距离

## 🎯 使用模式

### 基础流处理模式

```python
# 1. 创建环境
env = sfd.Environment("my_job")

# 2. 创建数据流
stream = env.create_datastream()

# 3. 配置处理管道
(
    stream
    .from_source(my_source_function)
    .filter(my_filter_function)
    .map(my_map_function)
    .sink(my_sink_function)
)

# 4. 执行处理
stream.execute()

# 5. 清理资源
env.close()
```

### 高级流处理模式

```python
# 使用多个数据流
stream1 = env.create_datastream()
stream2 = env.create_datastream()

# 连接流
stream1.connect(stream2)

# 并行处理
stream1.execute_async()
stream2.execute_async()

# 等待完成
stream1.wait()
stream2.wait()
```

### 错误处理模式

```python
try:
    # 流处理代码
    stream.execute()
except Exception as e:
    print(f"处理错误: {e}")
    # 错误恢复逻辑
    stream.stop()
    stream.reset()
finally:
    # 清理资源
    env.close()
```

## ⚡ 性能优化

### 批处理优化

```python
# 使用批处理提高性能
def batch_processor(items: List[dict]) -> List[dict]:
    # 批量处理逻辑
    return processed_items

# 配置批处理
stream.map(lambda batch: batch_processor(batch))
```

### 并发优化

```python
# 使用多线程处理
import concurrent.futures

def parallel_process(item):
    # 并行处理逻辑
    return processed_item

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = list(executor.map(parallel_process, data))
```

### 内存优化

```python
# 分批处理大文件
def process_large_file(file_path: str, batch_size: int = 1000):
    with open(file_path, 'r') as f:
        batch = []
        for line in f:
            batch.append(line.strip())
            if len(batch) >= batch_size:
                process_batch(batch)
                batch = []  # 释放内存

        if batch:
            process_batch(batch)
```

## 🔍 监控和调试

### 性能监控

```python
# 获取操作符统计
operator = stream.get_operator("my_map")
print(f"处理数量: {operator.get_processed_count()}")
print(f"输出数量: {operator.get_output_count()}")
```

### 调试模式

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 添加调试断点
def debug_filter(item):
    print(f"处理项目: {item}")
    return True

stream.filter(debug_filter)
```

## 🚨 常见问题

### 1. 内存不足错误

**问题：** 处理大数据集时出现内存错误
**解决方案：**
- 使用批处理
- 及时清理对象
- 增加系统内存

### 2. 连接超时

**问题：** Kafka 或其他外部服务连接超时
**解决方案：**
- 检查网络连接
- 调整超时设置
- 验证服务状态

### 3. 序列化错误

**问题：** 复杂对象序列化失败
**解决方案：**
- 使用简单的数据类型
- 实现自定义序列化
- 验证对象结构

## 📚 相关文档

- [用户指南](README.md)
- [性能调优指南](performance_guide.md)
- [故障排除](troubleshooting.md)
- [示例代码](../examples/)