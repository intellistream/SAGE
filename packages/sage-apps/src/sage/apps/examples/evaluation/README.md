# 评估示例 (Evaluation Examples)

这个目录包含模型和系统性能评估的各种方法示例，帮助用户评估RAG系统、问答模型和其他AI组件的效果。

## 📁 文件列表

### `qa_evaluate.py`
问答系统综合评估示例，包含：
- **准确性评估** - F1-Score, 精确率, 召回率
- **语义评估** - BERT评分, 语义相似度
- **生成质量** - ROUGE, BLEU评分
- **效率评估** - 响应时间, 吞吐量
- **检索质量** - 检索准确率, 上下文相关性

#### 评估维度：
1. **Answer Quality** - 答案质量评估
2. **Retrieval Effectiveness** - 检索效果评估
3. **System Performance** - 系统性能评估
4. **Cost Analysis** - 成本分析

## 🔍 评估指标

### 文本相似度指标
- **F1 Score** - 精确率和召回率的调和平均
- **ROUGE-L** - 最长公共子序列评分
- **BERT Score** - 基于BERT的语义相似度

### 检索相关指标
- **Context Recall** - 上下文召回率
- **Compression Rate** - 信息压缩率
- **Retrieval Precision** - 检索精确度

### 系统性能指标
- **Latency** - 响应延迟
- **Throughput** - 处理吞吐量
- **Token Count** - 生成的token数量

## 🚀 运行方式

### 基础评估
```bash
python qa_evaluate.py
```

### 自定义评估
```python
from sage.apps.lib.rag.evaluate import F1Evaluate, BertRecallEvaluate

# 配置评估器
evaluators = [
    F1Evaluate(config["f1_evaluate"]),
    BertRecallEvaluate(config["bert_evaluate"])
]

# 运行评估
for evaluator in evaluators:
    results = evaluator.evaluate(predictions, ground_truth)
    print(f"{evaluator.__class__.__name__}: {results}")
```

## ⚙️ 配置文件

使用 `../../config/config_evaluate.yaml` 配置：

```yaml
evaluation:
  metrics:
    - f1_score
    - rouge_l
    - bert_score
    - context_recall
  
  datasets:
    test_set: "data/test_qa.json"
    ground_truth: "data/ground_truth.json"
  
  output:
    report_path: "evaluation_report.json"
    detailed_results: true
```

## 📊 评估报告

评估完成后会生成详细报告：

```json
{
  "overall_scores": {
    "f1_score": 0.85,
    "rouge_l": 0.78,
    "bert_score": 0.82
  },
  "detailed_results": [
    {
      "question_id": 1,
      "question": "什么是机器学习？",
      "predicted_answer": "...",
      "ground_truth": "...",
      "scores": {
        "f1": 0.9,
        "rouge_l": 0.85
      }
    }
  ],
  "performance_metrics": {
    "avg_latency": 1.2,
    "throughput": 50
  }
}
```

## 🎯 评估最佳实践

### 数据集准备
1. **质量控制** - 确保标注数据的准确性
2. **多样性** - 覆盖不同类型的问题
3. **规模适当** - 足够的评估样本

### 评估策略
1. **多维度评估** - 结合多种评估指标
2. **A/B测试** - 比较不同模型版本
3. **持续评估** - 定期评估系统性能

### 结果分析
1. **错误分析** - 分析失败案例
2. **性能瓶颈** - 识别系统瓶颈
3. **改进建议** - 提出优化方案

## 🔧 扩展评估

### 添加自定义评估器
```python
from sage.apps.lib.rag.evaluate import BaseEvaluate

class CustomEvaluate(BaseEvaluate):
    def evaluate(self, predicted, ground_truth):
        # 实现自定义评估逻辑
        score = calculate_custom_score(predicted, ground_truth)
        return {"custom_score": score}
```

### 批量评估
```python
# 批量评估多个模型
models = ["model_v1", "model_v2", "model_v3"]
results = {}

for model in models:
    results[model] = run_evaluation(model, test_data)
    
compare_models(results)
```

## 🔗 相关资源

- [评估模块文档](../../packages/sage-userspace/src/sage/lib/rag/evaluate.py)
- [基准测试数据集](../../data/sample/)
- [评估工具集](../../packages/sage-userspace/src/sage/lib/rag/)
