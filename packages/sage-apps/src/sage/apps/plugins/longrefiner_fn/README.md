# LongRefiner 功能模块

LongRefiner功能模块为SAGE框架提供长文本智能精炼能力，通过AI技术实现文本内容的高质量压缩和优化。

## 模块概述

本模块集成了LongRefiner长文本处理引擎，提供标准化的文本精炼服务，支持多种精炼策略和处理模式。

## 核心组件

### [LongRefiner核心](./longrefiner/)
- 完整的文本精炼算法实现
- 多种精炼策略支持
- 智能提示词模板管理
- 任务指令和配置系统

### `longrefiner_adapter.py`
SAGE框架适配器：
- 将LongRefiner集成到SAGE流处理管道
- 提供标准的SAGE函数接口
- 支持流式文本处理
- 包含错误处理和监控

## 主要特性

- **无缝集成**: 与SAGE数据流管道完美集成
- **流式处理**: 支持实时文本流的精炼处理
- **多种模式**: 摘要、提取、压缩等多种处理模式
- **高性能**: 优化的批处理和并行处理能力
- **易配置**: 丰富的配置选项和参数调优

## 在SAGE中的使用

```python
from sage.api.env import LocalEnvironment
from sage.plugins.longrefiner_fn import LongRefinerFunction

# 创建环境
env = LocalEnvironment("text_refinement")

# 创建数据流
text_stream = env.source(TextSource, file_path="long_documents.txt")

# 应用文本精炼
refined_stream = text_stream.map(
    LongRefinerFunction,
    strategy="summary",
    max_length=300
)

# 输出结果
refined_stream.sink(FileSink, output_path="refined_texts.txt")

# 执行管道
env.execute()
```

## 支持的处理模式

### 批处理模式
- 处理完整的文档集合
- 适用于离线处理场景
- 支持大规模文档处理

### 流式处理模式
- 实时处理文本流
- 适用于在线内容处理
- 支持增量更新

### 交互式模式
- 支持用户交互式精炼
- 提供实时反馈和调整
- 适用于内容创作场景

## 配置和调优

### 基础配置
```python
config = {
    "strategy": "summary",        # 精炼策略
    "max_length": 500,           # 最大输出长度
    "language": "zh",            # 处理语言
    "quality_threshold": 0.8     # 质量阈值
}
```

### 高级配置
```python
advanced_config = {
    "model_name": "gpt-4",       # AI模型选择
    "batch_size": 32,            # 批处理大小
    "parallel_workers": 4,       # 并行工作进程
    "cache_enabled": True,       # 启用结果缓存
    "retry_count": 3             # 重试次数
}
```

## 应用场景

- **内容管理系统**: 长文档的自动摘要生成
- **新闻聚合**: 新闻文章的智能精炼
- **研究助手**: 学术论文的关键信息提取
- **企业知识库**: 内部文档的结构化处理
- **社交媒体**: 长内容的智能压缩

## 性能指标

- **处理速度**: 支持每秒处理数千个文档
- **精炼质量**: 信息保真度 > 85%
- **资源效率**: 内存使用优化，支持大文档处理
- **并发能力**: 支持多用户并发处理

## 扩展能力

- 支持自定义精炼策略
- 可集成第三方AI模型
- 支持特定领域的精炼优化
- 提供插件式扩展机制
