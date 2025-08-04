# LongRefiner 核心模块

LongRefiner是一个专门用于长文本精炼和优化的AI模块，提供文本摘要、内容提取和语言优化功能。

## 模块概述

LongRefiner模块实现了智能的长文本处理算法，能够将冗长的文本内容精炼为关键信息，同时保持原文的核心含义和重要细节。

## 核心组件

### `refiner.py`
文本精炼器核心实现：
- 主要的文本精炼算法
- 支持多种精炼策略（摘要、关键点提取、内容压缩）
- 提供可配置的精炼参数
- 支持批量文本处理

### `prompt_template.py`
提示词模板管理：
- 预定义的AI提示词模板
- 支持不同精炼任务的模板
- 模板参数化和动态生成
- 多语言提示词支持

### `task_instruction.py`
任务指令定义：
- 标准化的任务指令格式
- 不同类型文本精炼的指令集
- 指令优化和效果评估
- 自定义指令支持

### `quick_start.py`
快速开始工具：
- 简化的API接口
- 常见场景的快速配置
- 示例代码和使用指南
- 性能基准测试

### `version.py`
版本管理：
- 模块版本信息
- 兼容性检查
- 功能特性列表
- 更新日志

## 主要特性

- **智能精炼**: 基于AI的智能文本内容精炼
- **多策略支持**: 摘要、提取、压缩等多种处理策略
- **高质量输出**: 保持原文核心信息的高质量精炼
- **批量处理**: 支持大规模文本的批量处理
- **可定制化**: 丰富的配置选项和自定义能力

## 精炼策略

### 摘要模式 (Summary)
- 生成原文的简洁摘要
- 保留关键信息和主要观点
- 可配置摘要长度和详细程度

### 提取模式 (Extract)
- 提取文本中的关键信息点
- 结构化输出关键内容
- 支持实体识别和关系提取

### 压缩模式 (Compress)
- 保持原文结构的内容压缩
- 去除冗余信息
- 保持逻辑连贯性

## 使用场景

- **文档处理**: 长文档的摘要和精炼
- **内容创作**: 文章内容的优化和精简
- **信息提取**: 从长文本中提取关键信息
- **知识管理**: 知识库内容的结构化处理

## 快速开始

```python
from sage.plugins.longrefiner_fn.longrefiner import LongRefiner
from sage.plugins.longrefiner_fn.longrefiner.quick_start import QuickStart

# 使用快速开始接口
quick_refiner = QuickStart()
refined_text = quick_refiner.refine("这里是很长的文本内容...")

# 使用完整接口
refiner = LongRefiner(
    strategy="summary",
    max_length=500,
    language="zh"
)

result = refiner.refine(long_text)
```

## 配置选项

- `strategy`: 精炼策略（summary/extract/compress）
- `max_length`: 输出最大长度
- `language`: 处理语言
- `model`: 使用的AI模型
- `temperature`: 生成随机性控制
- `quality_threshold`: 质量阈值

## 性能优化

- 文本分块处理
- 并行处理支持
- 结果缓存机制
- 增量更新能力

## 质量保证

- 输出质量评估
- 信息保真度检查
- 多轮优化机制
- 人工审核接口
