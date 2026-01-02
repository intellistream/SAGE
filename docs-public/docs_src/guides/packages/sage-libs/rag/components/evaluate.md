# 评估组件 (Evaluation Components)

本文档详细介绍SAGE框架中`sage.libs.rag.evaluate`模块的评估组件。评估组件为RAG系统提供多维度的性能评估指标，支持系统优化和质量控制。

## 组件概述

### 核心功能

评估组件在RAG系统中承担以下关键职责：

- **多指标评估**：提供多种评估维度和指标
- **标准化接口**：所有评估函数继承自`MapFunction`基类
- **链式调用**：支持在数据处理管道中的无缝集成
- **结果可视化**：提供彩色格式的评估结果输出

### 设计架构

所有评估组件遵循统一的处理流程：

1. **输入验证**：检查预测结果和参考答案的数据格式
1. **指标计算**：执行相应的评估算法
1. **结果展示**：以标准化格式输出评估分数
1. **数据传递**：返回原始数据以支持链式调用

### 评估数据格式

标准评估输入格式：

```python
data = {"references": List[str], "generated": str}  # 参考答案列表  # 系统生成的答案
```

## 文本匹配评估组件

### F1Evaluate

#### 组件描述

F1分数评估器计算预测文本与参考答案之间的F1分数，综合考虑精确率和召回率。

#### 技术规格

- **评估指标**：F1-Score (调和平均数)
- **计算方式**：F1 = 2 × (Precision × Recall) / (Precision + Recall)
- **适用场景**：需要平衡精确率和召回率的评估任务

#### 实现示例

```python
from sage.libs.rag.evaluate import F1Evaluate

# 初始化评估器
f1_evaluator = F1Evaluate()

# 准备评估数据
data = {
    "references": ["SAGE是一个先进的RAG框架", "SAGE框架支持多种文本分块方法"],
    "generated": "SAGE是支持RAG的先进框架",
}

# 执行评估
result = f1_evaluator.execute(data)
# 输出示例: [F1] : 0.7500
```

### RecallEvaluate

#### 组件描述

召回率评估器计算预测文本相对于参考答案的召回率，衡量系统捕获相关信息的能力。

#### 技术规格

- **评估指标**：Recall (召回率)
- **计算方式**：Recall = TP / (TP + FN)
- **适用场景**：重视信息完整性的评估任务

#### 实现示例

```python
from sage.libs.rag.evaluate import RecallEvaluate

recall_evaluator = RecallEvaluate()
result = recall_evaluator.execute(data)
# 输出示例: [Recall] : 0.8000
```

#### AccuracyEvaluate - 准确率评估

检查预测文本是否与任一参考答案完全匹配。

**使用方法：**

```python
from sage.libs.rag.evaluate import AccuracyEvaluate

accuracy_evaluator = AccuracyEvaluate()
result = accuracy_evaluator.execute(data)
```

**输出示例：** `[Acc] : 1.0000`

### 2. 语义相似度评估

#### BertRecallEvaluate - BERT语义召回率

使用BERT模型计算预测文本与参考答案之间的语义相似度。

**依赖：** 需要安装`transformers`库

**使用方法：**

```python
from sage.libs.rag.evaluate import BertRecallEvaluate

# 注意：首次使用会下载BERT模型
bert_evaluator = BertRecallEvaluate()
result = bert_evaluator.execute(data)
```

**输出示例：** `[BertRecall] : 0.8534`

### 3. ROUGE评估

#### RougeLEvaluate - ROUGE-L评估

计算ROUGE-L分数，衡量最长公共子序列的质量。

**依赖：** 需要安装`rouge`库

**使用方法：**

```python
from sage.libs.rag.evaluate import RougeLEvaluate

rouge_evaluator = RougeLEvaluate()
result = rouge_evaluator.execute(data)
```

**输出示例：** `[ROUGE-L] : 0.6667`

### 4. 字符级评估

#### BRSEvaluate - 字符集召回率

计算预测文本与参考答案字符集的重叠比例。

**使用方法：**

```python
from sage.libs.rag.evaluate import BRSEvaluate

brs_evaluator = BRSEvaluate()
result = brs_evaluator.execute(data)
```

**输出示例：** `[BRS] : 0.7500`

### 5. 性能指标

#### TokenCountEvaluate - 令牌计数

统计预测文本中的令牌数量。

**使用方法：**

```python
from sage.libs.rag.evaluate import TokenCountEvaluate

token_evaluator = TokenCountEvaluate()
data_with_pred = {"pred": "这是一个测试句子"}
result = token_evaluator.execute(data_with_pred)
```

**输出示例：** `[Token Count] : 5`

#### LatencyEvaluate - 延迟评估

计算系统总延迟时间。

**使用方法：**

```python
from sage.libs.rag.evaluate import LatencyEvaluate

latency_evaluator = LatencyEvaluate()
data_with_time = {"refine_time": 0.5, "generate_time": 1.2}
result = latency_evaluator.execute(data_with_time)
```

**输出示例：** `[Latency] : 1.70s`

### 6. 检索评估

#### ContextRecallEvaluate - 上下文召回率

评估检索到的文档是否包含支持事实。

**使用方法：**

```python
from sage.libs.rag.evaluate import ContextRecallEvaluate

context_evaluator = ContextRecallEvaluate()
data_with_context = {
    "metadata": {"supporting_facts": {"sent_id": ["doc1_sent1", "doc2_sent3"]}},
    "retrieved_sent_ids": ["doc1_sent1", "doc3_sent2"],
}
result = context_evaluator.execute(data_with_context)
```

**输出示例：** `[Context Recall] : 0.5000`

#### CompressionRateEvaluate - 压缩率评估

计算文档压缩比率。

**使用方法：**

```python
from sage.libs.rag.evaluate import CompressionRateEvaluate

compression_evaluator = CompressionRateEvaluate()
data_with_docs = {
    "retrieved_docs": ["很长的原始文档内容", "另一个很长的文档"],
    "refined_docs": ["精炼后的内容"],
}
result = compression_evaluator.execute(data_with_docs)
```

**输出示例：** `[Compression Rate] : 3.50×`

## 数据格式要求

### 基本数据结构

```python
{
    "references": ["参考答案1", "参考答案2"],  # 必需：参考答案列表
    "generated": "生成的预测答案",  # 必需：模型生成的答案
    "pred": "预测文本",  # 可选：用于令牌计数
    "refine_time": 0.5,  # 可选：精炼时间
    "generate_time": 1.2,  # 可选：生成时间
    "retrieved_docs": ["文档1", "文档2"],  # 可选：检索到的文档
    "refined_docs": ["精炼文档"],  # 可选：精炼后的文档
    "retrieved_sent_ids": ["id1", "id2"],  # 可选：检索到的句子ID
    "metadata": {"supporting_facts": {"sent_id": ["支持事实ID"]}},  # 可选：元数据
}
```

## 完整使用示例

```python
from sage.libs.rag.evaluate import (
    F1Evaluate,
    RecallEvaluate,
    AccuracyEvaluate,
    BertRecallEvaluate,
    RougeLEvaluate,
    BRSEvaluate,
    TokenCountEvaluate,
    LatencyEvaluate,
    ContextRecallEvaluate,
    CompressionRateEvaluate,
)

# 准备测试数据
test_data = {
    "references": ["北京是中国的首都", "中国的首都是北京"],
    "generated": "北京是中华人民共和国的首都",
    "pred": "北京是中华人民共和国的首都",
    "refine_time": 0.3,
    "generate_time": 0.8,
    "retrieved_docs": [
        "北京，中华人民共和国首都，位于华北平原北部",
        "北京是政治文化中心",
    ],
    "refined_docs": ["北京是中国首都"],
    "retrieved_sent_ids": ["doc1_sent1", "doc2_sent1"],
    "metadata": {"supporting_facts": {"sent_id": ["doc1_sent1", "doc2_sent2"]}},
}

# 创建评估器列表
evaluators = [
    F1Evaluate(),
    RecallEvaluate(),
    AccuracyEvaluate(),
    BertRecallEvaluate(),
    RougeLEvaluate(),
    BRSEvaluate(),
    TokenCountEvaluate(),
    LatencyEvaluate(),
    ContextRecallEvaluate(),
    CompressionRateEvaluate(),
]

# 执行所有评估
print("开始RAG系统评估：")
result = test_data
for evaluator in evaluators:
    result = evaluator.execute(result)

print("评估完成！")
```

## 扩展开发

如果需要添加新的评估指标，可以继承`MapFunction`基类：

```python
from sage.core.api.function.map_function import MapFunction


class CustomEvaluate(MapFunction):
    def execute(self, data: dict):
        # 实现自定义评估逻辑
        score = self.calculate_custom_score(data)
        print(f"\033[93m[Custom] : {score:.4f}\033[0m")
        return data

    def calculate_custom_score(self, data):
        # 自定义评估算法
        return 0.0
```
