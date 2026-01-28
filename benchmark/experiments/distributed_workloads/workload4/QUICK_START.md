# Workload 4 快速配置指南

## 概述

Workload 4 支持**双流数据源**（查询流 + 文档流），提供灵活的配置方式。

## 配置双流数据源的三种方法

### 方法 1：使用配置类（推荐）

```python
from workload4 import Workload4Config

config = Workload4Config(
    num_tasks=100,           # 查询数量
    query_qps=40.0,          # 查询流 QPS
    doc_qps=25.0,            # 文档流 QPS
    
    # 查询类型分布
    query_type_distribution={
        "factual": 0.4,      # 事实性 40%
        "analytical": 0.35,  # 分析性 35%
        "exploratory": 0.25, # 探索性 25%
    },
    
    # 类别分布
    category_distribution={
        "finance": 0.30,
        "healthcare": 0.25,
        "technology": 0.25,
        "general": 0.20,
    },
    
    # Embedding 服务
    embedding_base_url="http://11.11.11.7:8090/v1",
    embedding_model="BAAI/bge-large-en-v1.5",
)

# 验证配置
config.validate()
```

### 方法 2：从 YAML 加载

创建 `config.yaml`:

```yaml
num_tasks: 100
query_qps: 40.0
doc_qps: 25.0

query_type_distribution:
  factual: 0.4
  analytical: 0.35
  exploratory: 0.25

category_distribution:
  finance: 0.30
  healthcare: 0.25
  technology: 0.25
  general: 0.20

embedding_base_url: "http://11.11.11.7:8090/v1"
embedding_model: "BAAI/bge-large-en-v1.5"
```

加载配置：

```python
import yaml
from workload4 import Workload4Config

with open("config.yaml") as f:
    config_dict = yaml.safe_load(f)

config = Workload4Config(**config_dict)
```

### 方法 3：使用工厂函数

```python
from workload4 import create_query_source, create_document_source

# 直接从配置字典创建
query_source = create_query_source({
    "num_tasks": 100,
    "query_qps": 40.0,
    "query_type_distribution": {"factual": 0.5, "analytical": 0.3, "exploratory": 0.2},
})

doc_source = create_document_source({
    "num_docs": 62,  # (100 / 40) * 25 ≈ 62
    "doc_qps": 25.0,
})
```

## 数据源路径选项

### 选项 1：内置模板生成（默认）

**不需要任何外部文件**，使用内置模板自动生成：

```python
from workload4 import Workload4DocumentSource

# 默认使用内置模板
doc_source = Workload4DocumentSource(
    num_docs=100,
    qps=25.0,
)
```

**特点**：
- ✅ 零配置，开箱即用
- ✅ 高多样性：45 个查询模板 × 160+ 占位符 = 数万种组合
- ✅ 适合基准测试和快速验证

### 选项 2：自定义知识库（内存）

从 Python 列表加载知识库：

```python
knowledge_base = [
    {"id": "doc_001", "title": "Title 1", "content": "Content 1"},
    {"id": "doc_002", "title": "Title 2", "content": "Content 2"},
    # ...
]

doc_source = Workload4DocumentSource(
    num_docs=100,
    qps=25.0,
    knowledge_base=knowledge_base,  # 从列表采样
)
```

### 选项 3：外部文件加载

从 JSONL 或 Parquet 文件加载：

```python
doc_source = Workload4DocumentSource(
    num_docs=100,
    qps=25.0,
    knowledge_base_path="/path/to/corpus.jsonl",  # 支持 .jsonl 或 .parquet
)
```

**JSONL 格式示例**：

```json
{"id": "doc_001", "title": "Title 1", "content": "Content 1"}
{"id": "doc_002", "title": "Title 2", "content": "Content 2"}
```

### 选项 4：FiQA 数据集（已注册服务）

使用 HuggingFace 的 FiQA-2018 数据集：

```python
from workload4.services import register_fiqa_vdb_service

# 注册 FiQA 服务（自动下载数据集）
fiqa_vdb, collection = register_fiqa_vdb_service()

# 使用 FiQA 数据
doc_source = Workload4DocumentSource(
    num_docs=100,
    qps=25.0,
    use_fiqa=True,  # 从 FiQA 采样
)
```

## Pipeline 集成示例

```python
from sage.kernel.runtime import RemoteEnvironment
from workload4 import (
    Workload4Config,
    Workload4QuerySource,
    Workload4DocumentSource,
    EmbeddingPrecompute,
)

# 1. 创建配置
config = Workload4Config(
    num_tasks=100,
    query_qps=40.0,
    doc_qps=25.0,
    use_remote=True,
    num_nodes=8,
)

# 2. 创建分布式环境
env = RemoteEnvironment(
    name="workload4_dual_stream",
    num_nodes=config.num_nodes,
    head_node=config.head_node,
)

# 3. 构建查询流
query_stream = env.from_source(
    Workload4QuerySource,
    num_tasks=config.num_tasks,
    qps=config.query_qps,
)
query_stream = query_stream.map(
    EmbeddingPrecompute,
    embedding_base_url=config.embedding_base_url,
    embedding_model=config.embedding_model,
)

# 4. 构建文档流
doc_stream = env.from_source(
    Workload4DocumentSource,
    num_docs=int(config.num_tasks / config.query_qps * config.doc_qps),
    qps=config.doc_qps,
)
doc_stream = doc_stream.map(
    EmbeddingPrecompute,
    embedding_base_url=config.embedding_base_url,
    embedding_model=config.embedding_model,
)

# 5. 后续 stages（Task 3-10 实现后可用）
# - Semantic Join (60s 窗口)
# - Dual VDB Retrieval (VDB1 + VDB2)
# - Graph Memory Traversal
# - DBSCAN Clustering
# - 5-Dimensional Reranking
# - Batch Aggregation
# - LLM Generation

# 6. 执行 Pipeline
env.submit(autostop=True)
```

## 关键参数说明

| 参数 | 说明 | 默认值 | 范围 |
|------|------|--------|------|
| `num_tasks` | 查询数量 | 100 | > 0 |
| `query_qps` | 查询流 QPS | 40.0 | > 0 |
| `doc_qps` | 文档流 QPS | 25.0 | > 0 |
| `query_type_distribution` | 查询类型分布 | 见配置 | 总和 = 1.0 |
| `category_distribution` | 类别分布 | 见配置 | 总和 = 1.0 |
| `embedding_base_url` | Embedding 服务 URL | - | 必填 |
| `embedding_model` | Embedding 模型 | - | 必填 |
| `knowledge_base` | 内存知识库 | None | 可选 |
| `knowledge_base_path` | 外部知识库文件 | None | 可选 |

## QPS 计算

**预计运行时长**：
```
duration = num_tasks / query_qps
```

**预计文档数**：
```
num_docs = duration * doc_qps = (num_tasks / query_qps) * doc_qps
```

**示例**：
- `num_tasks = 100`, `query_qps = 40.0`, `doc_qps = 25.0`
- 运行时长：`100 / 40 = 2.5` 秒
- 文档数：`2.5 * 25 = 62.5` ≈ 62 个文档

## 常见问题

### Q1: 必须提供外部知识库文件吗？

**不需要**。默认使用内置模板生成，零配置即可运行。

### Q2: 如何验证 QPS 控制精度？

运行测试验证（Task 2 已验证 0.0% 误差）：

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_sage/experiments/distributed_workloads/workload4
python examples_sources.py  # 示例 4
```

### Q3: 如何自定义查询/文档模板？

修改 `sources.py` 中的 `QUERY_TEMPLATES` 和 `DOCUMENT_TEMPLATES` 字典。

### Q4: 支持哪些知识库格式？

- **JSONL**: `{"id": "...", "title": "...", "content": "..."}`
- **Parquet**: 相同字段结构
- **Memory**: Python `list[dict]`

## 相关文档

- [TASK2_COMPLETE.md](TASK2_COMPLETE.md) - Task 2 完整实现报告
- [DATA_SOURCE_CONFIG_GUIDE.md](DATA_SOURCE_CONFIG_GUIDE.md) - 详细配置指南
- [workload4_config.yaml](workload4_config.yaml) - 完整 YAML 配置模板
- [examples_sources.py](examples_sources.py) - 5 个交互式示例

## 下一步

- ✅ Task 1: 数据模型（已完成）
- ✅ Task 2: 双流源算子（已完成，14/14 测试通过）
- ⏳ **Task 3: Semantic Join** - 60s 窗口双流 Join（下一个任务）
- ⏳ Task 4-10: 后续 stages

---

**当前状态**: Task 2 已完成，可以开始 Task 3（Semantic Join）的实现。
