# 文章监控系统

基于 SAGE 框架构建的智能文章监控系统，从 arXiv 获取最新论文，通过多级过滤为用户推荐相关文献。

## 概述

文章监控系统演示了 SAGE 在实时数据流处理和内容过滤方面的能力。系统持续监控 arXiv 的最新论文，通过关键词匹配和语义分析为研究人员提供个性化的论文推荐。

## 核心功能

### 1. 实时数据获取

- 从 arXiv API 获取最新论文
- 支持多个学科分类（cs.AI, cs.LG, cs.CL 等）
- 可配置获取数量和频率

### 2. 多级过滤

**关键词过滤**：

- 基于词袋模型的快速筛选
- 支持自定义关键词列表
- 可配置最低匹配分数

**语义过滤**：

- 基于 Jaccard 相似度的语义匹配
- 支持自定义兴趣主题
- 提取与研究方向最相关的论文

### 3. 智能排序

- 综合关键词分数和语义分数
- 自动排序推荐结果
- 提供详细的评分解释

## 技术架构

### SAGE 算子管道

```python
ArxivSource (BatchFunction)
    ↓
KeywordFilter (MapFunction)
    ↓
SemanticFilter (MapFunction)
    ↓
ArticleScorer (MapFunction)
    ↓
ArticleRankingSink (SinkFunction)
```

### 算子说明

| 算子               | 类型          | 功能                            |
| ------------------ | ------------- | ------------------------------- |
| ArxivSource        | BatchFunction | 从 arXiv API 获取论文，逐条发送 |
| KeywordFilter      | MapFunction   | 基于关键词过滤论文              |
| SemanticFilter     | MapFunction   | 基于语义相似度过滤论文          |
| ArticleScorer      | MapFunction   | 计算综合评分                    |
| ArticleRankingSink | SinkFunction  | 收集并展示排序结果              |

## 使用方法

### 基本使用

```python
from sage.apps.article_monitoring import run_article_monitoring_pipeline

# 使用默认配置
run_article_monitoring_pipeline()
```

### 自定义配置

```python
run_article_monitoring_pipeline(
    keywords=["transformer", "attention", "bert", "nlp"],
    interest_topics=[
        "natural language processing and transformers",
        "machine translation and multilingual models"
    ],
    category="cs.CL",
    max_articles=30
)
```

### 命令行使用

```bash
# 默认配置
python -m sage.apps.article_monitoring.pipeline

# 自定义参数
python -m sage.apps.article_monitoring.pipeline \
    --keywords "graph,neural,network,gnn" \
    --topics "graph neural networks and applications" \
    --category cs.LG \
    --max-articles 20 \
    --verbose

# 使用示例脚本
python examples/apps/run_article_monitoring.py --category cs.AI
```

## 配置选项

### 关键词设置

```python
keywords = [
    "machine learning",
    "deep learning",
    "neural network",
    "transformer",
    "attention mechanism"
]
```

### 兴趣主题

```python
interest_topics = [
    "artificial intelligence and machine learning applications",
    "natural language processing and text generation",
    "computer vision and image analysis"
]
```

### arXiv 分类

常用分类：

- `cs.AI` - Artificial Intelligence
- `cs.LG` - Machine Learning
- `cs.CL` - Computation and Language
- `cs.CV` - Computer Vision
- `cs.NE` - Neural and Evolutionary Computing
- `stat.ML` - Machine Learning (Statistics)

完整列表：https://arxiv.org/category_taxonomy

## 输出示例

```
======================================================================
🔍 SAGE Article Monitoring System
======================================================================
Category: cs.AI
Max Articles: 10
Keywords: ['machine learning', 'deep learning', 'neural network']
Interest Topics: artificial intelligence and machine...
======================================================================

📡 Starting pipeline...

======================================================================
📚 Recommended Articles (5 found)
======================================================================

1. Deep Learning for Time Series Forecasting in Stream Processing
   Authors: John Doe, Jane Smith
   Score: 3.45 (keyword: 3.0, semantic: 0.45)
   URL: http://arxiv.org/abs/2401.00001
   Abstract: We propose a novel deep learning approach for time series...

2. Machine Learning Pipeline Optimization
   Authors: David Lee
   Score: 2.30 (keyword: 2.0, semantic: 0.30)
   URL: http://arxiv.org/abs/2401.00004
   Abstract: Optimizing machine learning pipelines for better...

======================================================================
✅ Pipeline completed in 2.34s
   Recommended 5 articles
======================================================================
```

## 应用场景

### 学术研究

- 跟踪特定领域的最新进展
- 发现相关研究工作
- 文献综述自动化

### 研究团队

- 团队成员共享感兴趣的论文
- 定期推送领域动态
- 知识管理

### 个人学习

- 探索新的研究方向
- 学习最新技术
- 建立个人知识库

## 扩展功能

### 持续监控（Future）

```python
from sage.apps.article_monitoring import ArticleMonitorPipeline

# 持续监控，每小时检查一次
pipeline = ArticleMonitorPipeline(...)
pipeline.run_continuous(interval=3600)
```

### 通知集成（Future）

- 邮件通知
- Slack/Discord 集成
- RSS 订阅

### 存储集成（Future）

```python
# 集成 SageDB 存储历史记录
from sage.middleware.components.sage_db import SageDBService

# 存储推荐结果
db = SageDBService()
db.store("articles", recommended_articles)
```

## 性能优化

### 批量处理

- 调整 `max_articles` 控制批量大小
- 平衡获取速度和网络负载

### 过滤策略

- 先使用关键词快速过滤
- 再使用语义分析精细筛选
- 减少不必要的计算

### 缓存机制（Future）

- 缓存已处理的论文
- 避免重复获取
- 提高响应速度

## 相关资源

- [源代码](https://github.com/intellistream/SAGE/tree/main/packages/sage-apps/src/sage/apps/article_monitoring)
- [示例脚本](https://github.com/intellistream/SAGE/tree/main/examples/apps/run_article_monitoring.py)
- [API 文档](../api-reference/index.md)
- [SAGE Kernel](packages/sage-kernel/README.md)

## 下一步

- 尝试 [智能家居系统](smart-home.md)
- 探索 [自动扩缩容系统](auto-scaling-chat.md)
- 查看更多 [应用示例](applications.md)
