# Benchmark Refiner

**Refiner算法评测套件** - 用于评测各种上下文压缩算法在RAG场景下的性能。

## 概述

`benchmark_refiner` 提供了一套完整的Refiner算法评测框架，包括：
- 多种SOTA压缩算法的评测Pipeline
- 注意力头分析工具（用于REFORM等方法）
- 统一的评测指标和可视化

## 已实现的算法

| 算法 | 描述 | 论文 |
|------|------|------|
| **Baseline** | 无压缩基线 | - |
| **LongRefiner** | 三阶段压缩：Query Analysis → Doc Structuring → Global Selection | [arXiv](https://arxiv.org/abs/2411.08147) |
| **REFORM** | 基于注意力头的token级压缩，支持KV cache优化 | [arXiv](https://arxiv.org/abs/2503.00822) |
| **Provence** | 句子级上下文剪枝，基于DeBERTa-v3 | [arXiv](https://arxiv.org/abs/2501.16214) |

## 评测指标

评测使用 `sage.middleware.operators.rag.evaluate` 中的标准指标：

| 指标 | 类 | 说明 |
|------|-----|------|
| F1 Score | `F1Evaluate` | Token级别F1分数 |
| Token Count | `TokenCountEvaluate` | 压缩后送入生成器的token数 |
| Latency | `LatencyEvaluate` | Retrieve/Refine/Generate各阶段延迟 |
| Compression Rate | `CompressionRateEvaluate` | 原始token数 / 压缩后token数 |
| ROUGE-L | `RougeLEvaluate` | ROUGE-L F1分数 |
| Recall | `RecallEvaluate` | 召回率 |

## 快速开始

### 1. 准备环境

```bash
# 安装SAGE（开发模式）
./quickstart.sh --dev --yes

# 确保有FAISS索引文件
# index_path, documents_path, mapping_path 需要预先构建
```

### 2. 运行评测Pipeline

```bash
# Baseline（无压缩）
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.baseline_rag

# LongRefiner
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.longrefiner_rag

# REFORM
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.reform_rag

# Provence
python -m sage.benchmark.benchmark_refiner.implementations.pipelines.provence_rag
```

### 3. 注意力头分析（REFORM专用）

```bash
# 分析模型的注意力头，找出最适合检索的头
python -m sage.benchmark.benchmark_refiner.analysis.find_heads \
    --config packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/head_analysis_config.yaml
```

## 目录结构

```
benchmark_refiner/
├── __init__.py                 # 模块入口
├── README.md                   # 本文档
│
├── analysis/                   # 注意力头分析工具
│   ├── __init__.py
│   ├── head_analysis.py        # MNR指标计算、Hook提取器
│   ├── find_heads.py           # 重要头发现脚本
│   └── visualization.py        # MNR曲线绘制
│
├── config/                     # 配置文件
│   ├── config_baseline.yaml
│   ├── config_longrefiner.yaml
│   ├── config_reform.yaml
│   ├── config_provence.yaml
│   └── head_analysis_config.yaml
│
└── implementations/            # Pipeline实现
    └── pipelines/
        ├── baseline_rag.py     # 无压缩基线
        ├── longrefiner_rag.py  # LongRefiner Pipeline
        ├── reform_rag.py       # REFORM Pipeline
        └── provence_rag.py     # Provence Pipeline
```

## 配置说明

### Pipeline配置示例 (config_longrefiner.yaml)

```yaml
pipeline:
  name: "sage-benchmark-longrefiner-rag"
  description: "LongRefiner RAG Pipeline"

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
  faiss:
    index_path: "${HOME}/wiki18_maxp.index"
    documents_path: "${HOME}/wiki18_fulldoc.jsonl"

generator:
  vllm:
    model_name: "Llama-3.1-8B-Instruct"
    base_url: "http://localhost:8000/v1"

longrefiner:
  enabled: true
  base_model_path: "Qwen/Qwen2.5-3B-Instruct"
  budget: 2048
```

### 注意力头分析配置 (head_analysis_config.yaml)

```yaml
model: "/path/to/Llama-3.1-8B-Instruct"
dataset: "nq"
num_samples: 100
device: "cuda"
dtype: "bfloat16"
top_k: 20
output_dir: "results/head_analysis"
```

## 添加新算法

1. **实现Compressor类** (在 `sageRefiner/sage_refiner/algorithms/`)
2. **实现Operator类** (包装为SAGE Pipeline算子)
3. **添加配置文件** (在 `config/`)
4. **创建Pipeline** (在 `implementations/pipelines/`)

参考模板：`sage.libs.foundation.context.compression.algorithms.refiner_template`

## 性能基准

在 NQ 数据集上的典型结果（RTX 3090）：

| 算法 | F1 Score | Compression Rate | Latency |
|------|----------|------------------|---------|
| Baseline | 0.35 | 1.0x | 2.5s |
| LongRefiner | 0.38 | 3.2x | 3.2s |
| REFORM | 0.36 | 2.5x | 2.8s |
| Provence | 0.37 | 2.0x | 2.6s |

*注：实际结果取决于模型、数据集和配置*

## 相关资源

- **算法实现**: `packages/sage-middleware/src/sage/middleware/components/sage_refiner/`
- **sageRefiner子模块**: `sageRefiner/` (独立库)
- **评测指标**: `packages/sage-middleware/src/sage/middleware/operators/rag/evaluate.py`
- **开发文档**: `docs/dev-notes/l5-benchmark/README.md`

## TODO

- [ ] 添加 LLMLingua 基线
- [ ] 添加 RECOMP 基线
- [ ] 实现 ECoRAG 算法
- [ ] 实现 xRAG 算法
- [ ] 统一CLI入口 (`sage-refiner-bench`)
