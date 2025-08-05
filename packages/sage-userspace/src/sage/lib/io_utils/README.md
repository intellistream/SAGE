# SAGE 输入输出模块

IO模块提供统一的数据输入输出接口，支持多种数据源和输出目标，是SAGE数据流管道的基础组件。

## 模块概述

IO模块实现了SAGE框架的数据输入输出抽象层，提供标准化的数据源（Source）和数据接收器（Sink）接口，支持各种数据格式和存储系统。

## 核心组件

### `source.py`
数据源接口和实现：
- 定义统一的数据源抽象接口
- 支持多种数据源类型（文件、数据库、API等）
- 提供流式读取和批量读取模式
- 包含数据源连接和资源管理
- 支持数据源的监控和故障恢复

#### 主要数据源类型：
- **FileSource**: 文件数据源（CSV、JSON、XML等）
- **DatabaseSource**: 数据库数据源（MySQL、PostgreSQL等）
- **APISource**: REST API数据源
- **StreamSource**: 实时数据流源（Kafka、RabbitMQ等）
- **CloudSource**: 云存储数据源（AWS S3、阿里云OSS等）

### `sink.py`
数据接收器接口和实现：
- 定义统一的数据输出抽象接口
- 支持多种输出目标（文件、数据库、消息队列等）
- 提供批量写入和实时写入模式
- 包含数据格式转换和序列化
- 支持数据验证和质量控制

#### 主要接收器类型：
- **FileSink**: 文件输出接收器
- **DatabaseSink**: 数据库输出接收器
- **ConsoleSink**: 控制台输出接收器
- **APISink**: REST API输出接收器
- **StreamSink**: 消息流输出接收器

### `batch.py`
批处理工具：
- 实现数据的批量处理逻辑
- 支持可配置的批处理大小和策略
- 提供批处理性能优化
- 包含批处理状态管理和错误处理
- 支持批处理的监控和度量

### [测试模块](./tests/)
完整的IO功能测试覆盖。

## 主要特性

- **统一接口**: 为不同数据源和输出提供一致的API
- **插件化设计**: 易于扩展新的数据源和输出类型
- **高性能**: 优化的IO操作和批处理能力
- **容错性**: 完善的错误处理和重试机制
- **监控友好**: 丰富的监控指标和日志记录

## 数据流集成

```python
from sage.api.env import LocalEnvironment
from sage.lib.io.source import FileSource
from sage.lib.io.sink import FileSink, ConsoleSink

# 创建执行环境
env = LocalEnvironment("data_processing")

# 创建数据流
data_stream = env.source(
    FileSource, 
    file_path="input.csv",
    format="csv"
)

# 处理数据
processed_stream = data_stream.map(ProcessFunction)

# 输出到多个目标
processed_stream.sink(FileSink, output_path="output.json", format="json")
processed_stream.sink(ConsoleSink, prefix="[RESULT]")

# 执行管道
env.execute()
```

## 支持的数据格式

### 结构化数据
- **CSV**: 逗号分隔值文件
- **JSON**: JavaScript对象表示法
- **XML**: 可扩展标记语言
- **Parquet**: 列式存储格式
- **Avro**: 数据序列化系统

### 半结构化数据
- **YAML**: YAML配置文件
- **TOML**: 配置文件格式
- **LOG**: 各种日志文件格式

### 二进制数据
- **Images**: 图像文件（PNG、JPG、GIF等）
- **Audio**: 音频文件（WAV、MP3等）
- **Video**: 视频文件（MP4、AVI等）
- **Archives**: 压缩文件（ZIP、TAR.GZ等）

## 配置选项

### 数据源配置
```python
source_config = {
    "file_path": "/path/to/data.csv",
    "format": "csv",
    "encoding": "utf-8",
    "delimiter": ",",
    "skip_rows": 1,
    "chunk_size": 1000,
    "timeout": 30
}

source = FileSource(config=source_config)
```

### 数据接收器配置
```python
sink_config = {
    "output_path": "/path/to/output.json",
    "format": "json",
    "encoding": "utf-8",
    "batch_size": 100,
    "compression": "gzip",
    "create_dirs": True
}

sink = FileSink(config=sink_config)
```

## 性能优化

### 批处理优化
- 可配置的批处理大小
- 内存使用优化
- 异步IO操作
- 并行处理支持

### 缓存机制
- 智能数据缓存
- 预读取优化
- 写入缓冲
- 压缩传输

### 监控指标
- 数据处理速度
- 内存使用情况
- 错误率统计
- 延迟监控

## 扩展开发

### 自定义数据源
```python
from sage.lib.io.source import BaseSource

class CustomSource(BaseSource):
    def __init__(self, config):
        super().__init__(config)
        self.initialize()
    
    def read(self):
        # 实现数据读取逻辑
        return data_iterator
    
    def close(self):
        # 清理资源
        pass
```

### 自定义接收器
```python
from sage.lib.io.sink import BaseSink

class CustomSink(BaseSink):
    def __init__(self, config):
        super().__init__(config)
        self.initialize()
    
    def write(self, data):
        # 实现数据写入逻辑
        pass
    
    def flush(self):
        # 刷新缓冲区
        pass
```

## 最佳实践

1. **资源管理**: 及时关闭文件句柄和数据库连接
2. **错误处理**: 实现完善的异常处理和重试逻辑
3. **性能监控**: 监控IO操作的性能指标
4. **数据验证**: 在读取和写入时验证数据格式
5. **安全考虑**: 对文件路径和数据内容进行安全检查
