# Distributed CPU-Intensive Workloads for SAGE Benchmark

4个递进式复杂度的分布式CPU密集型工作负载，用于测试SAGE的分布式调度能力和CPU密集型计算性能。

## 🎯 设计目标

- **分布式优先**: 充分利用SAGE的KeyBy、Join、Batch等分布式算子
- **CPU密集型**: 增加检索、重排序、聚合等CPU操作的数量和复杂度
- **减少LLM依赖**: 使用小模型（Qwen2.5-3B）或限制生成长度
- **多阶段处理**: 通过多个Map、Filter、Join步骤增加pipeline复杂度

## 📦 工作负载概览

| Workload | CPU占用 | QPS | 主要特性 | 关键算子 |
|----------|---------|-----|---------|---------|
| Workload 1 | 30-50% | 20 | 基准RAG Pipeline | EmbeddingMap, VDBRetrieve |
| Workload 2 | 50-70% | 30 | 多阶段RAG + 三路Join | SessionContext, 3-way Join, RerankMap |
| Workload 3 | 70-85% | 25+15 | **双流Semantic Join** + 双VDB | **Connect+Join(30s)**, Deduplication |
| Workload 4 | 85-95% | 40+25 | 极致复杂度 + 双层Batch | **Connect+Join(60s)**, DBSCAN, 5维评分 |

**🔥 NEW**: Workload 3/4现使用SAGE标准双流Join模式（`keyby().connect().join()`）

## 📋 文件结构

```
distributed_workloads/
├── __init__.py                 # 模块初始化
├── workload_config.py          # 统一配置管理
├── workload_operators.py       # 专用算子实现（Source, Map, Sink）
├── join_operators.py           # 双流Join算子（NEW）
├── workload_pipelines.py       # Pipeline构建器
├── workload_runner.py          # 运行脚本
├── test_workload_join.py       # Join功能测试（NEW）
├── DUAL_STREAM_JOIN.md         # 双流Join实现说明（NEW）
└── README.md                   # 本文档
```

## 🚀 快速开始

### 1. 运行单个工作负载

```bash
# 运行Workload 1（基准）
cd /home/sage/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments
python -m distributed_workloads.workload_runner run workload_1

# 运行Workload 3（双流Join）
python -m distributed_workloads.workload_runner run workload_3

# 自定义参数
python -m distributed_workloads.workload_runner run workload_1 \
    --qps 30 \
    --num-tasks 500 \
    --parallelism 16 \
    --scheduler load_aware
```

### 2. 运行测试场景

```bash
# 运行预定义测试场景
python -m distributed_workloads.workload_runner scenario scenario_1_baseline
python -m distributed_workloads.workload_runner scenario scenario_3_high
```

### 3. 运行所有工作负载

```bash
# 依次运行所有4个工作负载
python -m distributed_workloads.workload_runner all
```

## 🔧 配置说明

### 统一配置类 (`WorkloadConfig`)

所有工作负载使用统一的配置类，自动根据workload_name设置默认参数。

```python
from distributed_workloads import get_config

# 获取Workload 3的默认配置
config = get_config("workload_3")

# 修改配置
config.query_qps = 30.0
config.keyby_parallelism = 16
config.scheduler_type = "load_aware"
```

### 关键配置项

| 配置项 | 说明 | Workload 1 | Workload 3 | Workload 4 |
|--------|------|-----------|-----------|-----------|
| `query_qps` | 查询QPS | 20 | 25 | 40 |
| `doc_qps` | 文档QPS（双流） | - | 15 | 25 |
| `join_window` | Join窗口（秒） | - | 30.0 | 60.0 |
| `keyby_parallelism` | KeyBy并行度 | 8 | 8 | 16 |
| `vdb_top_k` | VDB检索Top-K | 15 | 20 | 25 |
| `batch_size` | 批量大小 | 8 | 8 | 12 |

## 📊 算子说明

### Source算子

- **WorkloadQuerySource**: 统一查询生成源，支持QPS控制、查询类型标签
- **WorkloadDocSource**: 文档更新流（双流Join专用）

### Processing算子

- **EmbeddingMapOperator**: Embedding计算（支持批量调用）
- **VDBRetrieveOperator**: VDB检索（SageVDB后端）
- **BM25RerankOperator**: BM25重排序（CPU密集: TF-IDF）
- **SemanticRerankOperator**: 语义重排序（Embedding相似度）
- **SemanticJoinOperator**: 语义Join（CPU密集: 窗口内向量计算）
- **DeduplicationOperator**: 去重（SimHash + O(n²)相似度矩阵 + DBSCAN）

### Sink算子

- **WorkloadMetricsSink**: 指标收集，输出CSV格式结果

## 🎨 Pipeline设计

### Workload 1: 基准RAG Pipeline

```
QuerySource → EmbeddingMap → KeyBy → VDBRetrieve 
    → FilterTopK → Batch → MetricsSink
```

**特点**: 单流、简单pipeline、CPU占用30-50%

### Workload 2: 多阶段RAG + 三路Join

```
QuerySource → SessionContext → KeyBy(user_id) → MemoryRetrieve
    → ContextEnhancement
    → (VDB1 + VDB2 + VDB3)  # 三路并行
    → Join → FinalRerank → Batch → MetricsSink
```

**特点**: 三路并行检索、Join汇聚、CPU占用50-70%

### Workload 3: 双流Semantic Join + 双VDB

```
QuerySource ────┐
                ├→ SemanticJoin(30s) → KeyBy → MemoryRetrieve
DocSource ──────┘        → ContextFusion
                         → (VDB1 + VDB2)
                         → Join → FinalRerank → Deduplication
                         → Batch → MetricsSink
```

**特点**: 双流Join、30s窗口、CPU占用70-85%

**关键**: Semantic Join是最大瓶颈（11.5M ops/s向量计算）

### Workload 4: 极致复杂度 + 双层Batch

```
QuerySource ────┐
                ├→ SemanticJoin(60s) → KeyBy(16并行)
DocSource ──────┘        → GraphMemoryRetrieve
                         → EmbeddingFusion
                         → (VDB1-4stage + VDB2-4stage)
                         → Join → Deduplication(DBSCAN)
                         → FinalRerank(5维度) → DiversityFilter
                         → KeyBy(category) → CategoryAgg
                         → GlobalBatch → MetricsSink
```

**特点**: 
- 60s大窗口Join（1500 docs）
- DBSCAN聚类去重
- 双层Batch聚合
- CPU占用85-95%

**关键**: Semantic Join是最大瓶颈（61.4M ops/s向量计算）

## 📈 性能预期

### CPU利用率

| Workload | 预期CPU | 主要瓶颈 |
|----------|---------|---------|
| Workload 1 | 30-50% | VDB检索 |
| Workload 2 | 50-70% | 三路Join + Rerank |
| Workload 3 | 70-85% | Semantic Join(11.5M ops/s) + 去重 |
| Workload 4 | 85-95% | Semantic Join(61.4M ops/s) + DBSCAN |

### 延迟预期

| Workload | P50 | P95 | P99 |
|----------|-----|-----|-----|
| Workload 1 | 200ms | 400ms | 600ms |
| Workload 2 | 500ms | 1000ms | 1500ms |
| Workload 3 | 800ms | 1500ms | 2000ms |
| Workload 4 | 1200ms | 2000ms | 3000ms |

## 🔍 指标收集

所有workload的指标自动收集到CSV文件：

```bash
/tmp/sage_workload_metrics/workload_metrics_<timestamp>.csv
```

CSV格式：
```csv
task_id,query,total_latency,stage_1_latency,stage_2_latency,
stage_3_latency,stage_4_latency,num_retrieved,num_matched,
dedup_rate,timestamp
```

## 🛠️ 扩展开发

### 添加新算子

```python
# 在 workload_operators.py 中添加
class MyCustomOperator(MapFunction):
    def __init__(self, stage: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.stage_num = stage
    
    def execute(self, data):
        # 你的处理逻辑
        data.stage = self.stage_num
        return data
```

### 添加新Pipeline

```python
# 在 workload_pipelines.py 中添加
def build_workload_5(self) -> WorkloadPipelineFactory:
    env = self._create_environment("workload_5")
    
    (
        env.from_source(WorkloadQuerySource, ...)
        .map(MyCustomOperator, ...)
        .sink(WorkloadMetricsSink, ...)
    )
    
    return self
```

## 📚 相关文档

- **设计文档**: `/home/sage/SAGE/WORKLOAD_DESIGNS.md`
- **SAGE架构**: `docs-public/docs_src/dev-notes/package-architecture.md`
- **Operator开发**: `docs-public/docs_src/dev-notes/l4-middleware/operators.md`

## ⚠️ 注意事项

1. **Semantic Join优化**: Workload 3/4的关键瓶颈，需使用NumPy向量化计算
2. **Embedding批量**: 建议batch_size=32-128减少网络往返
3. **内存管理**: 60s Join窗口可能占用1.5MB per window
4. **GPU资源**: LLM推理和Rerank可能竞争GPU，建议使用小模型
5. **硬件要求**: 
   - 最低: 8节点 × 8核 = 64核
   - 推荐: 16节点 × 8核 = 128核（Workload 4）

## 🎓 引用

如果使用这些workload进行论文实验，请引用：

```bibtex
@article{sage2025,
  title={SAGE: Stream Analytics for Generative AI Engines},
  author={Your Team},
  journal={Your Conference},
  year={2025}
}
```
