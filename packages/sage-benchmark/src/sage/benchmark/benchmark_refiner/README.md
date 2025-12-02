# Benchmark Refiner

**Refiner 算法评测套件** - 用于评测各种上下文压缩算法在 RAG 场景下的性能。

## 概述

`benchmark_refiner` 提供了一套完整的 Refiner 算法评测框架，包括：

- 多种 SOTA 压缩算法的评测 Pipeline
- 注意力头分析工具（用于 REFORM 等方法）
- 统一的评测指标和可视化
- 统计显著性检验

## 已实现的算法

| 算法              | 类型             | 描述                                                            | 论文                                      |
| ----------------- | ---------------- | --------------------------------------------------------------- | ----------------------------------------- |
| **Baseline**      | 截断             | 无压缩基线                                                      | -                                         |
| **LongRefiner**   | LLM-based        | 三阶段压缩：Query Analysis → Doc Structuring → Global Selection | [arXiv](https://arxiv.org/abs/2411.08147) |
| **REFORM**        | Attention-based  | 基于注意力头的 token 级压缩，支持 KV cache 优化                 | [arXiv](https://arxiv.org/abs/2503.00822) |
| **Provence**      | Provenance-aware | 句子级上下文剪枝，基于 DeBERTa-v3                               | [arXiv](https://arxiv.org/abs/2501.16214) |
| **LongLLMLingua** | LLM-PPL          | 问题感知的长文档压缩，使用对比 perplexity                       | [arXiv](https://arxiv.org/abs/2310.06839) |
| **LLMLingua-2**   | BERT-based       | 快速 token 分类压缩，多语言支持                                 | [arXiv](https://arxiv.org/abs/2403.12968) |

### 算法特性对比

| 算法          | 速度   | 压缩质量 | 多语言 | 需要 GPU    |
| ------------- | ------ | -------- | ------ | ----------- |
| Baseline      | 极快   | 差       | ✅     | ❌          |
| LongRefiner   | 慢     | 高       | ❌     | ✅ (LLM)    |
| REFORM        | 中     | 高       | ❌     | ✅ (LLM)    |
| Provence      | 中     | 中       | ❌     | ✅ (LLM)    |
| LongLLMLingua | 慢     | 高       | ❌     | ✅ (7B LLM) |
| LLMLingua-2   | **快** | 中       | ✅     | ✅ (BERT)   |

## 评测指标

评测使用 `sage.middleware.operators.rag.evaluate` 中的标准指标：

| 指标             | 类                        | 说明                                |
| ---------------- | ------------------------- | ----------------------------------- |
| F1 Score         | `F1Evaluate`              | Token 级别 F1 分数                  |
| Token Count      | `TokenCountEvaluate`      | 压缩后送入生成器的 token 数         |
| Latency          | `LatencyEvaluate`         | Retrieve/Refine/Generate 各阶段延迟 |
| Compression Rate | `CompressionRateEvaluate` | 原始 token 数 / 压缩后 token 数     |
| ROUGE-L          | `RougeLEvaluate`          | ROUGE-L F1 分数                     |
| Recall           | `RecallEvaluate`          | 召回率                              |

## 快速开始

### 1. 准备环境

```bash
# 安装 SAGE（开发模式）
./quickstart.sh --dev --yes

# 确保有 FAISS 索引文件
# index_path, documents_path, mapping_path 需要预先构建
```

### 2. 使用 CLI 工具

```bash
# 运行单个算法
sage-refiner-bench run baseline --samples 10

# 多算法对比
sage-refiner-bench compare \
    --algorithms baseline,longrefiner,reform,longllmlingua,llmlingua2 \
    --samples 100 \
    --output results/comparison.json
```

### 3. 直接运行 Pipeline

```bash
# Baseline（无压缩）
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.baseline_rag

# LongRefiner
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.longrefiner_rag

# REFORM
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.reform_rag

# Provence
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.provence_rag

# LongLLMLingua
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.longllmlingua_rag

# LLMLingua-2
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.llmlingua2_rag
```

### 4. 注意力头分析（REFORM 专用）

```bash
# 分析模型的注意力头，找出最适合检索的头
python -m sage.benchmark.benchmark_refiner.analysis.find_heads \
    --config packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/head_analysis_config.yaml
```

## 目录结构

```
benchmark_refiner/
├── __init__.py                 # 模块入口
├── cli.py                      # CLI 入口 (sage-refiner-bench)
├── README.md                   # 本文档
│
├── analysis/                   # 分析工具
│   ├── __init__.py
│   ├── head_analysis.py        # MNR 指标计算、Hook 提取器
│   ├── find_heads.py           # 重要头发现脚本
│   ├── statistical.py          # 统计显著性检验
│   └── visualization.py        # MNR 曲线绘制
│
├── config/                     # 配置文件
│   ├── config_baseline.yaml
│   ├── config_longrefiner.yaml
│   ├── config_reform.yaml
│   ├── config_provence.yaml
│   ├── config_longllmlingua.yaml
│   ├── config_llmlingua2.yaml
│   └── head_analysis_config.yaml
│
├── experiments/                # 实验框架
│   ├── __init__.py
│   ├── base_experiment.py      # 实验基类
│   ├── comparison_experiment.py # 多算法对比实验
│   ├── results_collector.py    # 结果收集器
│   └── runner.py               # 实验运行器
│
└── implementations/            # Pipeline 实现
    └── pipelines/
        ├── baseline_rag.py
        ├── longrefiner_rag.py
        ├── reform_rag.py
        ├── provence_rag.py
        ├── longllmlingua_rag.py
        └── llmlingua2_rag.py
```

## 配置说明

### Pipeline 配置示例 (config_longllmlingua.yaml)

```yaml
pipeline:
  name: "sage-benchmark-longllmlingua-rag"
  description: "LongLLMLingua RAG Pipeline"

source:
  type: "hf"
  hf_dataset_name: "RUC-NLPIR/FlashRAG_datasets"
  hf_dataset_config: "nq"
  hf_split: "test"
  max_samples: 20

retriever:
  type: "wiki18_faiss"
  dimension: 1024
  top_k: 100

generator:
  vllm:
    model_name: "Llama-3.1-8B-Instruct"
    base_url: "http://localhost:8000/v1"

longllmlingua:
  enabled: true
  model_name: "NousResearch/Llama-2-7b-hf"
  rate: 0.55                          # Paper baseline
  condition_in_question: "after"
  condition_compare: true
  reorder_context: "sort"
```

## 统计检验

`analysis/statistical.py` 提供了 ICML 论文所需的统计检验功能：

```python
from sage.benchmark.benchmark_refiner.analysis.statistical import (
    paired_t_test,
    bootstrap_confidence_interval,
    cohens_d,
    generate_significance_report,
)

# 配对 t 检验
result = paired_t_test(baseline_scores, method_scores)
# {"t_statistic": 2.5, "p_value": 0.01, "significant": True}

# Bootstrap 置信区间
ci = bootstrap_confidence_interval(scores, confidence=0.95)
# (0.35, 0.40)

# 生成完整报告
report = generate_significance_report(
    {"baseline": [...], "longrefiner": [...], "llmlingua2": [...]},
    baseline_name="baseline"
)
```

## 性能基准

在 NQ 数据集上的典型结果（RTX 3090）：

| 算法          | F1 Score | Compression Rate | Latency |
| ------------- | -------- | ---------------- | ------- |
| Baseline      | 0.35     | 1.0x             | 2.5s    |
| LongRefiner   | 0.38     | 3.2x             | 3.2s    |
| REFORM        | 0.36     | 2.5x             | 2.8s    |
| Provence      | 0.37     | 2.0x             | 2.6s    |
| LongLLMLingua | 0.38     | 3.0x             | 4.0s    |
| LLMLingua-2   | 0.36     | 2.5x             | 1.5s    |

*注：实际结果取决于模型、数据集和配置*

## 相关资源

- **算法实现**: `packages/sage-middleware/src/sage/middleware/components/sage_refiner/`
- **sageRefiner 子模块**: `sageRefiner/` (独立库)
- **评测指标**: `packages/sage-middleware/src/sage/middleware/operators/rag/evaluate.py`
- **开发文档**: `docs/dev-notes/l5-benchmark/ICML_REFINER_TASKS.md`

## 添加新算法

1. **实现 Compressor 类** (在 `sageRefiner/sage_refiner/algorithms/`)
1. **实现 Operator 类** (包装为 SAGE Pipeline 算子)
1. **添加配置文件** (在 `config/`)
1. **创建 Pipeline** (在 `implementations/pipelines/`)

参考模板：`sage.libs.foundation.context.compression.algorithms.refiner_template`
