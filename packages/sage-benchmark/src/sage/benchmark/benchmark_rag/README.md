# SAGE RAG Benchmarking Guide

## 概述

SAGE RAG benchmarking 框架提供了一套完整的 RAG 系统性能评估工具，包括：

- **implementations/**: 各种 RAG 实现方案（dense, sparse, hybrid, multimodal）
- **evaluation/**: 评测管道、指标计算和结果分析
- **config/**: 各种 RAG 配置文件
- **data/**: 测试数据集和查询

## 目录结构

```
benchmark_rag/
├── implementations/     # RAG 实现方案
│   ├── pipelines/      # RAG pipeline 实现
│   │   ├── qa_dense_retrieval_milvus.py   # Milvus 密集检索
│   │   ├── qa_sparse_retrieval_milvus.py  # Milvus 稀疏检索
│   │   ├── qa_hybrid_retrieval_milvus.py  # 混合检索
│   │   ├── qa_multimodal_fusion.py        # 多模态融合
│   │   └── ...
│   └── tools/          # 辅助工具
│       ├── build_chroma_index.py          # ChromaDB 索引构建
│       ├── build_milvus_dense_index.py    # Milvus 密集索引
│       └── loaders/                       # 文档加载器
├── evaluation/          # 评测框架
│   ├── pipeline_experiment.py         # 实验管道
│   ├── evaluate_results.py            # 结果评估
│   └── config/                        # 评测配置
├── config/              # RAG 配置文件
└── data/                # 测试数据
```

## 核心组件

### 1. RAG 实现方案 (implementations/)

提供多种 RAG 实现用于性能对比：

**向量数据库支持**:

- Milvus (dense, sparse, hybrid)
- ChromaDB (local, easy setup)
- FAISS (efficient search)

**检索方法**:

- Dense retrieval (embedding-based)
- Sparse retrieval (BM25, sparse vectors)
- Hybrid retrieval (combining both)
- Multimodal fusion (text + image + video)

### 2. 评测框架 (evaluation/)

基于 SAGE 框架的 benchmark 管道，包含四个主要算子：

- **BatchFileSource**: 批量文件数据源算子，支持设置 batch_size 参数
- **Generator**: 生成算子，支持控制是否使用检索上下文
- **PostProcessor**: 后处理算子，处理答案并提取预测结果
- **Sink**: 结果保存算子，保存 benchmark 结果到文件

评估指标：

- **Accuracy**: 准确率评估
- **F1 Score**: F1分数计算
- **Exact Match**: 精确匹配评估
- **检索质量分析**: 分析检索上下文的相关性和覆盖率

## 数据来源

### SelfRAG 数据集

Benchmark 使用的评估数据主要来自 [Self-RAG 仓库](https://github.com/AkariAsai/self-rag) 的任务评估数据。

> **数据下载**:
> [Self-RAG 官方数据链接](https://drive.google.com/file/d/1TLKhWjez63H4uBtgCxyoyJsZi-IMgnDb/view?usp=share_link)
> 下载评估数据。

#### 数据特点

- **预处理完成**: 每个文件已经包含了检索到的文档
- **即用性**: 如果不想运行检索器作为推理的一部分，可以直接加载 `contexts` 字段中的检索文档
- **格式统一**: 所有数据文件采用统一的JSON Lines格式

#### 数据格式

```json
{
  "id": "sample_id",
  "question": "问题文本",
  "answers": ["答案1", "答案2"],
  "ctxs": [
    {
      "title": "文档标题",
      "text": "文档内容",
      "score": 0.95
    }
  ]
}
```

## 使用方法

### 1. 准备数据和索引

首先构建向量索引：

```bash
# Build ChromaDB index
python -m sage.benchmark.benchmark_rag.implementations.tools.build_chroma_index

# Build Milvus dense index
python -m sage.benchmark.benchmark_rag.implementations.tools.build_milvus_dense_index
```

### 2. 运行 RAG Pipeline

```bash
# Dense retrieval with Milvus
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval_milvus

# Sparse retrieval with Milvus
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_sparse_retrieval_milvus

# Hybrid retrieval
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_hybrid_retrieval_milvus
```

### 3. 运行 Benchmark 实验

使用默认配置文件运行实验：

```bash
python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment
```

### 4. 配置文件设置

编辑 `evaluation/config/experiment_config.yaml`:

```yaml
source:
  data_path: "path/to/your/data.jsonl"
  max_samples: 100  # 限制处理样本数，可选
  batch_size: 10    # 批处理大小

generator:
  model_name: "Mistral-7B-Instruct-v0.1"
  use_context: true  # 是否使用检索上下文
  top_k: 3          # 使用的检索文档数量

post_processor:
  extract_prediction: true

sink:
  output_path: "./experiment/results/experiment_results.json"
  save_mode: "incremental"  # 保存模式: incremental 或 final
```

### 3. 评估结果

````bash
### 4. 评估结果

```bash
# 评估实验结果
python -m sage.benchmark.benchmark_rag.evaluation.evaluate_results \
  --results-file experiment_results.json \
  --metric all \
  --show-details

# 指定输出文件
python -m sage.benchmark.benchmark_rag.evaluation.evaluate_results \
  --results-file experiment_results.json \
  --output evaluation_report.json
````

--metric accuracy \
--output "./experiment/results/evaluation_output.json"

````

### 4. 支持的评估指标

- `accuracy`: 准确率评估
- `f1`: F1分数计算  
- `exact_match`: 精确匹配
- `all`: 计算所有指标

## 实验配置示例

### 无上下文实验

```yaml
generator:
  model_name: "Mistral-7B-Instruct-v0.1"
  use_context: false  # 不使用检索上下文
````

### 有上下文实验

```yaml
generator:
  model_name: "Mistral-7B-Instruct-v0.1"
  use_context: true   # 使用检索上下文
  top_k: 5           # 使用前5个检索文档
```

### 批处理配置

```yaml
source:
  batch_size: 20     # 每批处理20个样本
  max_samples: 1000  # 最多处理1000个样本

sink:
  save_mode: "incremental"  # 每批次后保存结果
```

## 输出格式

### 实验结果格式

```json
{
  "experiment_config": {
    "model_name": "Mistral-7B-Instruct-v0.1",
    "use_context": true,
    "top_k": 3,
    "batch_size": 10,
    "timestamp": "2025-08-19T03:26:14.446465",
    "total_samples": 100,
    "completed_batches": "10/10"
  },
  "results": [
    {
      "id": "sample_id",
      "question": "问题文本",
      "ground_truth": ["正确答案1", "正确答案2"],
      "model_output": "模型生成的答案",
      "retrieved_context": ["检索文档1", "检索文档2"]
    }
  ]
}
```

### 评估结果格式

```json
{
  "experiment_config": { ... },
  "overall_scores": {
    "accuracy": 85.6,
    "f1": 78.3,
    "exact_match": 72.1
  },
  "retrieval_analysis": {
    "context_coverage": 0.95,
    "avg_context_count": 3.2,
    "context_relevance_rate": 0.78
  },
  "detailed_results": [ ... ]
}
```

## 相关资源

- [SAGE 框架文档](../docs/)
- [SelfRAG 论文](https://arxiv.org/abs/2310.11511)
- [评估数据下载](https://github.com/AkariAsai/self-rag#data)
