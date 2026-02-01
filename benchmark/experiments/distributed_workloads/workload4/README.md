# Workload 4: 极致复杂的分布式 CPU 密集型工作流

## 概述

Workload 4 是 SAGE Benchmark 中最复杂的分布式工作流，用于压测 SAGE 的极限调度能力。

### 架构特点

- **双流输入**: Query (40 QPS) + Document (25 QPS)
- **60s 大窗口 Semantic Join**: 语义匹配，窗口内 ~1500 docs
- **双路 4-stage VDB 检索**: 专业知识库 + 通用知识库
- **图遍历内存检索**: BFS 遍历 100-200 节点
- **DBSCAN 聚类去重**: 智能去重，相似度矩阵 + 聚类
- **5 维评分重排序**: semantic + freshness + diversity + authority + coverage
- **双层 Batch 聚合**: Category-level + Global batch
- **MMR 多样性过滤**: Maximal Marginal Relevance

### 预期性能

- **CPU 利用率**: 85-95% (极高，接近满负载)
- **吞吐量**: 10-15 QPS
- **P50 延迟**: 1200ms
- **P95 延迟**: 2000ms
- **P99 延迟**: 3000ms

### 关键瓶颈

1. **Semantic Join**: 61.4M ops/s (40 queries × 1500 docs × 1024 dim)
1. **DeduplicationMap**: O(n²) 相似度矩阵 + DBSCAN 聚类
1. **FinalRerankMap**: 100 次多维度评分 (20 candidates × 5 dimensions)
1. **Graph Memory**: BFS 遍历 + 路径权重计算

## 文件结构

```
workload4/
├── __init__.py              # 导出所有模型和配置
├── models.py                # ✅ 10 个数据模型（Task 1）
├── config.py                # ✅ 配置管理（Task 1）
├── sources.py               # ✅ 双流源算子（Task 2）
├── examples_sources.py      # ✅ 源算子使用示例（Task 2）
├── semantic_join.py         # 语义 Join（Task 3）
├── vdb_retrieval.py         # VDB 检索分支（Task 4）
├── graph_memory.py          # 图遍历（Task 5）
├── clustering.py            # 聚类去重（Task 6）
├── reranking.py             # 重排序和评分（Task 7）
├── batching.py              # 批处理聚合（Task 8）
├── generation.py            # 生成和 Sink（Task 9）
├── pipeline.py              # Pipeline 工厂（Task 10）
├── examples.py              # ✅ 使用示例（Task 1）
├── TASK1_COMPLETE.md        # ✅ Task 1 完成报告
├── TASK2_COMPLETE.md        # ✅ Task 2 完成报告
├── TASK2_SUMMARY.md         # ✅ Task 2 总结
└── tests/
    ├── __init__.py          # ✅ 完整测试套件
    ├── test_models.py       # ✅ 数据模型测试（Task 1）
    ├── test_config.py       # ✅ 配置管理测试（Task 1）
    └── test_sources.py      # ✅ 源算子测试（Task 2, 14 个测试全部通过）
```

## 实现进度

| Task    | 模块                 | 状态 | 测试     | 说明                          |
| ------- | -------------------- | ---- | -------- | ----------------------------- |
| Task 1  | models.py, config.py | ✅   | ✅       | 数据模型和配置管理            |
| Task 2  | sources.py           | ✅   | ✅ 14/14 | 双流源算子，QPS 控制精度 0.0% |
| Task 3  | semantic_join.py     | ⏳   | -        | 60s 窗口 Semantic Join        |
| Task 4  | vdb_retrieval.py     | ⏳   | -        | 双路 4-stage VDB 检索         |
| Task 5  | graph_memory.py      | ⏳   | -        | 图遍历内存检索                |
| Task 6  | clustering.py        | ⏳   | -        | DBSCAN 聚类去重               |
| Task 7  | reranking.py         | ⏳   | -        | 5 维评分重排序                |
| Task 8  | batching.py          | ⏳   | -        | 双层 Batch 聚合               |
| Task 9  | generation.py        | ⏳   | -        | LLM 生成和 Sink               |
| Task 10 | pipeline.py          | ⏳   | -        | Pipeline 工厂和集成           |

### Task 2 完成详情

**实现内容**:

- ✅ `Workload4QuerySource` - 查询源（40 QPS，3 种类型，4 个类别）
- ✅ `Workload4DocumentSource` - 文档源（25 QPS，知识库集成）
- ✅ `EmbeddingPrecompute` - Embedding 预计算（OpenAI 兼容 API）
- ✅ 45 个查询模板，12 个文档模板，160+ 占位符
- ✅ 工厂函数和配置集成
- ✅ 14 个单元测试全部通过
- ✅ QPS 控制精度验证：0.0% 误差

**使用示例**:

```bash
# 运行源算子示例
cd workload4
python examples_sources.py

# 选项：
# 1. 基本使用
# 2. 配置和工厂函数
# 3. Embedding 预计算
# 4. QPS 控制（验证精度）
# 5. 知识库集成
```

## 快速开始

### 安装依赖

```bash
cd /home/sage/SAGE
pip install -e packages/sage-benchmark
```

### 运行测试

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/distributed_workloads
python workload4/tests/__init__.py
```

### 查看示例

```bash
python workload4/examples.py
```

## 使用示例

### 基本数据模型

```python
from workload4 import QueryEvent, DocumentEvent, JoinedEvent

# 创建查询事件
query = QueryEvent(
    query_id="q001",
    query_text="What is the impact of AI on finance?",
    query_type="analytical",
    category="finance",
    timestamp=time.time(),
)

# 创建文档事件
doc = DocumentEvent(
    doc_id="d001",
    doc_text="AI is transforming the financial industry...",
    doc_category="finance",
    timestamp=time.time(),
)

# Join 后的事件
joined = JoinedEvent(
    joined_id="q001_12345",
    query=query,
    matched_docs=[doc],
    join_timestamp=time.time(),
    semantic_score=0.85,
)
```

### 配置管理

```python
from workload4 import (
    get_default_config,
    get_light_config,
    get_cpu_optimized_config,
)

# 默认配置（标准压测）
config = get_default_config()
print(f"Query QPS: {config.query_qps}")
print(f"Join window: {config.join_window_seconds}s")

# 轻量配置（快速测试）
light_config = get_light_config()  # 5分钟，QPS 20+15

# CPU优化配置（适配实际硬件）
cpu_config = get_cpu_optimized_config()  # 并行度32，batch 128
```

### 性能指标

```python
from workload4 import Workload4Metrics

metrics = Workload4Metrics(task_id="task_001", query_id="q001")

# 填充时间戳
metrics.query_arrival_time = base_time
metrics.join_time = base_time + 0.5
metrics.end_to_end_time = base_time + 3.0

# 计算延迟
latencies = metrics.compute_latencies()
print(f"E2E latency: {latencies['e2e_latency']:.3f}s")
```

## 配置选项

### 预定义配置

| 配置                         | QPS (Q+D) | 窗口 | 并行度 | 时长  | 用途     |
| ---------------------------- | --------- | ---- | ------ | ----- | -------- |
| `get_default_config()`       | 40+25     | 60s  | 16     | 20min | 标准压测 |
| `get_light_config()`         | 20+15     | 30s  | 16     | 5min  | 快速测试 |
| `get_extreme_config()`       | 50+30     | 90s  | 32     | 30min | 极限压力 |
| `get_cpu_optimized_config()` | 30+20     | 40s  | 32     | 20min | CPU优化  |

### 关键参数

**双流配置**:

- `query_qps`: Query 流 QPS (默认 40.0)
- `doc_qps`: Document 流 QPS (默认 25.0)

**Semantic Join**:

- `join_window_seconds`: 窗口大小 (默认 60s)
- `join_threshold`: 相似度阈值 (默认 0.70)
- `join_parallelism`: 并行度 (默认 16)

**VDB 检索**:

- `vdb1_top_k`: 专业知识库 Top-K (默认 25)
- `vdb2_top_k`: 通用知识库 Top-K (默认 25)
- `vdb_filter_threshold`: 过滤阈值 (默认 0.6)

**图遍历**:

- `graph_max_depth`: 最大深度 (默认 3)
- `graph_max_nodes`: 最大节点数 (默认 200)

**聚类去重**:

- `clustering_algorithm`: 算法 ("dbscan")
- `dbscan_eps`: 邻域半径 (默认 0.15)
- `dedup_similarity_threshold`: 去重阈值 (默认 0.95)

**重排序**:

- `rerank_top_k`: 最终 Top-K (默认 15)
- `rerank_score_weights`: 5 维权重
- `mmr_lambda`: MMR 多样性系数 (默认 0.7)

**批处理**:

- `category_batch_size`: Category 批次大小 (默认 5)
- `global_batch_size`: Global 批次大小 (默认 12)

## 开发进度

| Task    | 状态      | 说明           |
| ------- | --------- | -------------- |
| Task 1  | ✅ 完成   | 数据模型和配置 |
| Task 2  | 🔲 待开发 | 双流源算子     |
| Task 3  | 🔲 待开发 | Semantic Join  |
| Task 4  | 🔲 待开发 | VDB 检索分支   |
| Task 5  | 🔲 待开发 | 图遍历         |
| Task 6  | 🔲 待开发 | 聚类去重       |
| Task 7  | 🔲 待开发 | 重排序和评分   |
| Task 8  | 🔲 待开发 | 批处理聚合     |
| Task 9  | 🔲 待开发 | 生成和 Sink    |
| Task 10 | 🔲 待开发 | Pipeline 工厂  |
| Task 11 | 🔲 待开发 | 执行脚本       |
| Task 12 | 🔲 待开发 | 文档           |

## 性能优化建议

### CPU 优化

1. **使用 NumPy 向量化**: Semantic Join 使用 NumPy/MKL 加速
1. **启用 SimHash 粗筛**: 减少 O(n²) 去重计算
1. **增加并行度**: `join_parallelism=32` 充分利用 128 核心

### 网络优化

1. **激进的 Embedding 批量**: `embedding_batch_size=128` 减少往返
1. **Rerank 批量调用**: `rerank_batch_size=64`

### 内存优化

1. **降低窗口大小**: 考虑 40s 窗口（减少 33% 状态）
1. **分区数对齐节点数**: `join_parallelism=16` (8 节点 × 2)

### GPU 优化

1. **LLM 批量推理**: `llm_batch_size=12`
1. **Rerank CPU fallback**: 轻量模型可用 CPU

## 硬件需求

### 最小配置

- **节点数**: 8
- **CPU**: 8 核/节点 (总 128 核)
- **内存**: 16GB/节点 (总 256GB)
- **GPU**: A6000 48GB (宿主机)

### 实际配置（当前集群）

- ✅ 1 台 A6000 机器 + 16 个容器节点
- ✅ 128 核心 CPU + 256GB 内存
- ✅ LLM: Qwen-3B-Instruct (轻量模型)
- ✅ Embedding: 远程访问 (11.11.11.7:8090)

## 相关文档

- **设计文档**: `/home/sage/SAGE/WORKLOAD_DESIGNS.md` (Workload 4 章节)
- **实现任务**: `../WORKLOAD4_IMPLEMENTATION_TASKS.md` (Task 分解)
- **测试报告**: `../WORKLOAD4_RESULTS.md` (性能评估报告)
- **Task 1 报告**: `TASK1_COMPLETE.md`
- **Task 2 报告**: `TASK2_COMPLETE.md`
- **使用示例**: `examples.py`, `examples_sources.py`

## 贡献

欢迎贡献代码和测试用例！

**开发流程**:

1. 阅读 `WORKLOAD4_IMPLEMENTATION_TASKS.md` 了解任务分解
1. 选择一个任务 (Task 2-12)
1. 实现算子/函数
1. 编写单元测试
1. 更新文档

## License

MIT License - Copyright (c) 2026 IntelliStream Team
