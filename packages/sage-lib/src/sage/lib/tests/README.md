# SAGE Lib模块测试

Lib模块的综合测试套件，覆盖核心功能和组件集成测试。

## 测试概述

本目录包含对SAGE Lib模块主要组件的测试，确保各个功能模块的正确性和性能。

## 测试文件

### `retriever_test.py`
检索器测试：
- 向量检索功能测试
- 搜索准确性验证
- 检索性能基准测试
- 多种检索策略测试

### `generator_test.py`
生成器测试：
- 文本生成质量测试
- 生成参数影响测试
- 多模型兼容性测试
- 生成性能测试

### `reranker_test.py`
重排序器测试：
- 排序算法正确性测试
- 排序质量评估测试
- 多维度排序测试
- 排序性能测试

### `evaluate_test.py`
评估系统测试：
- 评估指标准确性测试
- 多种评估方法测试
- 评估结果一致性测试
- 自动化评估流程测试

### `prompt_test.py`
提示词测试：
- 提示词模板测试
- 动态提示词生成测试
- 多语言提示词测试
- 提示词效果评估测试

## 测试数据

### 检索测试数据
- 多领域文档集合
- 查询-文档相关性标注
- 不同规模的测试集
- 多语言测试数据

### 生成测试数据
- 标准生成任务数据集
- 多种文本类型样本
- 质量评估参考答案
- 创意生成测试用例

### 评估测试数据
- 标准评估数据集
- 人工标注参考答案
- 多维度评估样本
- 边界条件测试用例

## 运行测试

```bash
# 运行所有Lib测试
python -m pytest sage/lib/tests/

# 运行特定组件测试
python -m pytest sage/lib/tests/retriever_test.py
python -m pytest sage/lib/tests/generator_test.py

# 运行性能测试
python -m pytest sage/lib/tests/ -m "performance"

# 运行集成测试
python -m pytest sage/lib/tests/ -m "integration"
```

## 测试指标

### 功能指标
- 检索准确率: Precision@K, Recall@K
- 生成质量: BLEU, ROUGE, BERTScore
- 排序效果: NDCG, MRR
- 评估一致性: Correlation, Agreement

### 性能指标
- 检索延迟: < 100ms
- 生成速度: > 50 tokens/s
- 排序效率: < 10ms per query
- 内存使用: < 2GB

## 测试配置

```python
TEST_CONFIG = {
    "data_path": "test_data/",
    "model_cache": "model_cache/",
    "timeout": 60,
    "batch_size": 32,
    "gpu_enabled": True,
    "parallel_workers": 4
}
```

## 持续集成

- 自动化测试执行
- 性能回归检测
- 测试覆盖率监控
- 质量门禁控制
