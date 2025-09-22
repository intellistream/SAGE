# SAGE 上下文管理模块

上下文管理模块提供智能的上下文信息管理和处理能力，支持多种上下文类型的存储、检索和分析。

## 模块概述

上下文模块负责管理AI系统运行过程中的各种上下文信息，包括对话历史、搜索结果、模型状态、质量评估等，为智能决策提供丰富的背景信息。

## 核心组件

### `model_context.py`
模型上下文管理：
- 管理AI模型的运行上下文
- 保存模型状态和配置信息
- 支持上下文的持久化存储
- 提供上下文版本管理

### `search_session.py`
搜索会话管理：
- 管理搜索会话的生命周期
- 追踪搜索历史和状态
- 支持会话恢复和续接
- 提供会话分析和统计

### `search_result.py`
搜索结果封装：
- 标准化搜索结果格式
- 包含结果元数据和评分
- 支持结果排序和过滤
- 提供结果质量评估

### `search_query_results.py`
查询结果集管理：
- 管理查询相关的所有结果
- 支持批量结果处理
- 提供结果聚合和分析
- 支持结果缓存和复用

### `quality_label.py`
质量标签系统：
- 定义各种质量评估标签
- 支持多维度质量评估
- 提供标签分类和层次结构
- 支持自定义质量标准

### `critic_evaluation.py`
批判性评估：
- 实现智能的评估算法
- 提供多角度的内容评估
- 支持评估结果的可解释性
- 包含评估质量的反馈机制

## 主要特性

- **多维度上下文**: 支持多种类型的上下文信息
- **智能管理**: 自动的上下文生命周期管理
- **持久化存储**: 支持上下文的长期保存
- **快速检索**: 高效的上下文查询和检索
- **质量保证**: 完善的质量评估和控制

## 上下文类型

### 对话上下文
- 用户对话历史
- 多轮对话状态
- 对话意图和实体
- 情感和语调分析

### 搜索上下文
- 搜索查询历史
- 搜索结果和评分
- 搜索策略和参数
- 用户反馈和偏好

### 模型上下文
- 模型配置和参数
- 推理历史和结果
- 性能指标和监控
- 错误日志和调试信息

### 业务上下文
- 用户画像和偏好
- 业务规则和约束
- 历史行为和模式
- 领域知识和专业信息

## 使用场景

- **对话系统**: 维护多轮对话的上下文连贯性
- **推荐系统**: 基于历史上下文的个性化推荐
- **搜索引擎**: 改进搜索结果的相关性和质量
- **决策支持**: 基于丰富上下文的智能决策
- **内容生成**: 上下文感知的内容创作

## 快速开始

```python
from sage.lib.context import ModelContext, SearchSession, QualityLabel

# 创建模型上下文
model_ctx = ModelContext(
    model_name="gpt-4",
    config={"temperature": 0.7, "max_tokens": 1000}
)

# 管理搜索会话
search_session = SearchSession(user_id="user123")
search_session.add_query("机器学习基础知识")

# 质量评估
quality = QualityLabel()
score = quality.evaluate_answer(answer_text, context=model_ctx)
```

## 上下文操作

### 创建和初始化
```python
# 创建新的上下文
context = ModelContext()
context.initialize(config_dict)

# 从已有数据恢复上下文
context = ModelContext.restore(saved_data)
```

### 更新和维护
```python
# 更新上下文信息
context.update("last_query", "新的查询内容")
context.add_history("user_action", action_data)

# 清理过期信息
context.cleanup(max_age=3600)  # 清理1小时前的数据
```

### 查询和检索
```python
# 查询上下文信息
recent_queries = context.get_recent("queries", limit=10)
user_preferences = context.get("user_preferences")

# 条件查询
results = context.search(
    criteria={"type": "search_result", "score": ">0.8"}
)
```

## 高级功能

### 上下文融合
```python
from sage.lib.context import ContextFusion

fusion = ContextFusion()
combined_context = fusion.merge([context1, context2, context3])
```

### 上下文分析
```python
from sage.lib.context import ContextAnalyzer

analyzer = ContextAnalyzer()
insights = analyzer.analyze(context)
patterns = analyzer.find_patterns(context_history)
```

### 上下文优化
```python
from sage.lib.context import ContextOptimizer

optimizer = ContextOptimizer()
optimized_context = optimizer.optimize(context, constraints)
```

## 配置选项

- `max_context_size`: 最大上下文大小
- `ttl`: 上下文生存时间
- `compression_enabled`: 是否启用压缩
- `persistence_mode`: 持久化模式
- `cache_strategy`: 缓存策略

## 性能优化

- 分层存储策略
- 智能缓存机制
- 异步处理支持
- 内存使用优化
