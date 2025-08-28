# SAGE Lib工具库

Lib工具库为SAGE框架特定的工具和过滤器提供实用功能。

## 模块概述

本模块包含SAGE库特有的工具函数和过滤器，主要用于数据流处理中的特定操作和上下文管理。

## 核心组件

### `context_sink.py`
上下文数据接收器：
- 将处理结果写入特定上下文
- 支持上下文格式化和结构化
- 提供上下文数据的持久化
- 包含上下文质量验证
- 支持多种输出格式

### `context_source.py`
上下文数据源：
- 从上下文环境读取数据
- 支持上下文数据的解析
- 提供上下文历史管理
- 包含上下文数据验证
- 支持增量数据读取

### `evaluate_filter.py`
评估过滤器：
- 对数据流进行质量评估
- 基于评估结果过滤数据
- 支持多维度评估标准
- 提供评估结果统计
- 包含自适应阈值调整

### `tool_filter.py`
工具过滤器：
- 集成各种工具的过滤功能
- 支持工具链式过滤
- 提供工具性能监控
- 包含工具结果验证
- 支持条件化工具调用

### `OpenAIClient.py`
OpenAI客户端工具：
- OpenAI API的专门封装
- 针对SAGE场景的优化
- 支持批量请求处理
- 提供错误恢复机制
- 包含使用量统计和限制

## 主要特性

- **上下文感知**: 深度集成SAGE的上下文系统
- **流式处理**: 专为数据流管道设计
- **质量控制**: 内置质量评估和过滤机制
- **工具集成**: 与SAGE工具生态系统无缝集成
- **性能优化**: 针对SAGE场景的性能优化

## 使用场景

- **上下文管理**: 在数据流中管理上下文信息
- **质量控制**: 对数据流进行质量评估和过滤
- **工具集成**: 在数据流中集成各种工具
- **API调用**: 在流式处理中调用外部API

## 快速开始

```python
from sage.lib.utils import ContextSink, EvaluateFilter
from sage.api.env import LocalEnvironment

# 创建环境
env = LocalEnvironment("context_processing")

# 创建数据流
data_stream = env.source(DataSource, data_path="input.json")

# 应用评估过滤
filtered_stream = data_stream.filter(
    EvaluateFilter,
    quality_threshold=0.8,
    evaluation_metrics=["relevance", "accuracy"]
)

# 输出到上下文
filtered_stream.sink(
    ContextSink,
    context_type="processed_data",
    output_format="structured"
)

# 执行管道
env.execute()
```

## 配置选项

### 上下文配置
```python
context_config = {
    "context_type": "qa_session",
    "format": "json",
    "compression": True,
    "max_size": 1000000,
    "retention_days": 30
}
```

### 评估配置
```python
evaluation_config = {
    "metrics": ["quality", "relevance", "completeness"],
    "threshold": 0.75,
    "adaptive_threshold": True,
    "feedback_learning": True
}
```

### 工具配置
```python
tool_config = {
    "tools": ["text_analyzer", "sentiment_detector"],
    "parallel_execution": True,
    "timeout": 30,
    "retry_count": 3
}
```

## 集成示例

### 上下文管理流
```python
# 读取历史上下文 → 处理数据 → 更新上下文
context_stream = env.source(ContextSource, context_id="session_123")
processed_stream = context_stream.map(ProcessFunction)
processed_stream.sink(ContextSink, context_id="session_123", append=True)
```

### 质量控制流
```python
# 数据输入 → 质量评估 → 过滤 → 输出高质量数据
raw_stream = env.source(RawDataSource)
evaluated_stream = raw_stream.map(EvaluateFilter, threshold=0.8)
high_quality_stream = evaluated_stream.filter(lambda x: x.quality_score > 0.9)
high_quality_stream.sink(QualityDataSink)
```

## 性能考量

- **缓存机制**: 上下文数据的智能缓存
- **批量处理**: 支持批量评估和过滤
- **异步处理**: 非阻塞的工具调用
- **资源优化**: 内存和计算资源的优化使用
