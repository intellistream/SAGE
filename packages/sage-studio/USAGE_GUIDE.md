# SAGE Studio 使用指南

> 低代码可视化 RAG 流水线构建器

## 目录

- [快速开始](#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
- [核心概念](#%E6%A0%B8%E5%BF%83%E6%A6%82%E5%BF%B5)
- [创建流水线](#%E5%88%9B%E5%BB%BA%E6%B5%81%E6%B0%B4%E7%BA%BF)
- [使用示例](#%E4%BD%BF%E7%94%A8%E7%A4%BA%E4%BE%8B)
- [节点类型参考](#%E8%8A%82%E7%82%B9%E7%B1%BB%E5%9E%8B%E5%8F%82%E8%80%83)
- [高级用法](#%E9%AB%98%E7%BA%A7%E7%94%A8%E6%B3%95)
- [最佳实践](#%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5)

______________________________________________________________________

## 快速开始

### 启动 Studio

```bash
# 启动 Studio 服务器
sage studio start

# 检查状态
sage studio status

# 停止服务器
sage studio stop
```

### 第一个流水线

```python
from sage.studio.models import VisualNode, VisualConnection, VisualPipeline
from sage.studio.services import PipelineBuilder

# 1. 创建节点
retriever = VisualNode(
    id="retriever1",
    type="chroma_retriever",
    label="Document Retriever",
    config={"collection_name": "docs", "top_k": 5},
    position={"x": 100, "y": 100},
)

generator = VisualNode(
    id="generator1",
    type="openai_generator",
    label="Answer Generator",
    config={"model": "gpt-4"},
    position={"x": 300, "y": 100},
)

# 2. 创建连接
connection = VisualConnection(
    id="conn1",
    source_node_id="retriever1",
    source_port="output",
    target_node_id="generator1",
    target_port="input",
)

# 3. 创建流水线
pipeline = VisualPipeline(
    id="simple_rag",
    name="Simple RAG Pipeline",
    nodes=[retriever, generator],
    connections=[connection],
)

# 4. 构建并执行
builder = PipelineBuilder()
env = builder.build(pipeline)
job = env.execute()
```

______________________________________________________________________

## 核心概念

### VisualNode (可视化节点)

表示流水线中的一个操作单元：

```python
node = VisualNode(
    id="unique_id",  # 唯一标识符
    type="operator_type",  # 节点类型（如 generator, retriever）
    label="Display Name",  # 显示名称
    config={...},  # 节点配置参数
    position={"x": 0, "y": 0},  # UI 位置（可选）
)
```

### VisualConnection (可视化连接)

表示节点之间的数据流：

```python
connection = VisualConnection(
    id="conn1",
    source_node_id="node1",
    source_port="output",
    target_node_id="node2",
    target_port="input",
    label="data_flow",  # 可选标签
)
```

### VisualPipeline (可视化流水线)

完整的流水线定义：

```python
pipeline = VisualPipeline(
    id="pipeline_id",
    name="Pipeline Name",
    description="Description",  # 可选
    nodes=[...],
    connections=[...],
    tags=["rag", "qa"],  # 可选标签
)
```

______________________________________________________________________

## 创建流水线

### 方式 1: Python API

```python
from sage.studio.models import VisualNode, VisualConnection, VisualPipeline

# 直接创建 Python 对象
nodes = [
    VisualNode(
        id="n1",
        type="retriever",
        label="Retriever",
        config={"top_k": 5},
        position={"x": 100, "y": 100},
    ),
    VisualNode(
        id="n2",
        type="generator",
        label="Generator",
        config={"model": "gpt-4"},
        position={"x": 300, "y": 100},
    ),
]

connections = [
    VisualConnection(
        id="c1",
        source_node_id="n1",
        source_port="output",
        target_node_id="n2",
        target_port="input",
    )
]

pipeline = VisualPipeline(
    id="my_pipeline", name="My RAG Pipeline", nodes=nodes, connections=connections
)
```

### 方式 2: 从 JSON 字典

```python
pipeline_dict = {
    "id": "json_pipeline",
    "name": "Pipeline from JSON",
    "nodes": [
        {
            "id": "node1",
            "type": "retriever",
            "label": "Retriever",
            "config": {"top_k": 5},
            "position": {"x": 100, "y": 100},
        },
        {
            "id": "node2",
            "type": "generator",
            "label": "Generator",
            "config": {"model": "gpt-3.5-turbo"},
            "position": {"x": 300, "y": 100},
        },
    ],
    "connections": [
        {
            "source": "node1",
            "sourcePort": "output",
            "target": "node2",
            "targetPort": "input",
        }
    ],
}

# 从字典创建
pipeline = VisualPipeline.from_dict(pipeline_dict)

# 转换回字典
pipeline_dict = pipeline.to_dict()
```

### 方式 3: Web UI

1. 访问 `http://localhost:8000`
1. 拖拽节点到画布
1. 连接节点
1. 配置参数
1. 保存并执行

______________________________________________________________________

## 使用示例

### 示例 1: 基本 RAG 流水线

```python
from sage.studio.models import VisualNode, VisualConnection, VisualPipeline
from sage.studio.services import get_pipeline_builder

# 创建检索器
retriever = VisualNode(
    id="retriever1",
    type="chroma_retriever",
    label="Vector Retriever",
    config={
        "collection_name": "knowledge_base",
        "top_k": 5,
        "embedding_model": "text-embedding-ada-002",
    },
    position={"x": 100, "y": 100},
)

# 创建生成器
generator = VisualNode(
    id="generator1",
    type="openai_generator",
    label="Answer Generator",
    config={"model": "gpt-4-turbo", "temperature": 0.7, "max_tokens": 500},
    position={"x": 300, "y": 100},
)

# 创建流水线
pipeline = VisualPipeline(
    id="basic_rag",
    name="Basic RAG Pipeline",
    description="Simple retrieval-augmented generation",
    nodes=[retriever, generator],
    connections=[
        VisualConnection(
            id="c1",
            source_node_id="retriever1",
            source_port="output",
            target_node_id="generator1",
            target_port="input",
        )
    ],
    tags=["rag", "qa"],
)

# 构建并执行
builder = get_pipeline_builder()
env = builder.build(pipeline)
job = env.execute()
```

### 示例 2: 带重排序的 RAG

```python
# 创建 Retriever -> Reranker -> Generator 流水线
retriever = VisualNode(
    id="retriever1",
    type="chroma_retriever",
    label="Initial Retrieval",
    config={"collection_name": "docs", "top_k": 20},
    position={"x": 100, "y": 100},
)

reranker = VisualNode(
    id="reranker1",
    type="bge_reranker",
    label="BGE Reranker",
    config={"model": "BAAI/bge-reranker-large", "top_k": 5},
    position={"x": 300, "y": 100},
)

promptor = VisualNode(
    id="promptor1",
    type="qa_promptor",
    label="QA Promptor",
    config={"template": "Context: {context}\n\nQuestion: {question}\n\nAnswer:"},
    position={"x": 500, "y": 100},
)

generator = VisualNode(
    id="generator1",
    type="openai_generator",
    label="Answer Generator",
    config={"model": "gpt-4", "temperature": 0.3},
    position={"x": 700, "y": 100},
)

pipeline = VisualPipeline(
    id="rag_with_reranker",
    name="RAG with Reranker",
    nodes=[retriever, reranker, promptor, generator],
    connections=[
        VisualConnection(
            id="c1",
            source_node_id="retriever1",
            source_port="output",
            target_node_id="reranker1",
            target_port="input",
        ),
        VisualConnection(
            id="c2",
            source_node_id="reranker1",
            source_port="output",
            target_node_id="promptor1",
            target_port="context",
        ),
        VisualConnection(
            id="c3",
            source_node_id="promptor1",
            source_port="output",
            target_node_id="generator1",
            target_port="input",
        ),
    ],
)

builder = get_pipeline_builder()
env = builder.build(pipeline)
```

### 示例 3: 多检索器融合

```python
# 使用多个检索器并融合结果
chroma_retriever = VisualNode(
    id="ret_chroma",
    type="chroma_retriever",
    label="Chroma Retriever",
    config={"collection_name": "chroma_docs", "top_k": 5},
    position={"x": 100, "y": 50},
)

milvus_retriever = VisualNode(
    id="ret_milvus",
    type="milvus_dense_retriever",
    label="Milvus Retriever",
    config={"collection_name": "milvus_docs", "top_k": 5},
    position={"x": 100, "y": 150},
)

fusion = VisualNode(
    id="fusion1",
    type="map",
    label="Result Fusion",
    config={"strategy": "reciprocal_rank_fusion"},
    position={"x": 300, "y": 100},
)

generator = VisualNode(
    id="gen1",
    type="generator",
    label="Generator",
    config={"model": "gpt-4"},
    position={"x": 500, "y": 100},
)

pipeline = VisualPipeline(
    id="multi_retriever",
    name="Multi-Retriever Fusion",
    nodes=[chroma_retriever, milvus_retriever, fusion, generator],
    connections=[
        VisualConnection(
            id="c1",
            source_node_id="ret_chroma",
            source_port="output",
            target_node_id="fusion1",
            target_port="input1",
        ),
        VisualConnection(
            id="c2",
            source_node_id="ret_milvus",
            source_port="output",
            target_node_id="fusion1",
            target_port="input2",
        ),
        VisualConnection(
            id="c3",
            source_node_id="fusion1",
            source_port="output",
            target_node_id="gen1",
            target_port="input",
        ),
    ],
)
```

### 示例 4: 文档处理流水线

```python
# 文档分块 -> 向量化 -> 存储
chunker = VisualNode(
    id="chunker1",
    type="character_splitter",
    label="Text Splitter",
    config={"chunk_size": 1000, "overlap": 100},
    position={"x": 100, "y": 100},
)

# 这个示例展示了如何处理文档
# 实际执行需要配置 Source (输入) 和 Sink (输出)

pipeline = VisualPipeline(
    id="doc_processing", name="Document Processing", nodes=[chunker], connections=[]
)
```

### 示例 5: 带评估的 RAG

```python
# RAG 流水线 + 答案评估
retriever = VisualNode(
    id="ret1",
    type="retriever",
    label="Retriever",
    config={"top_k": 5},
    position={"x": 100, "y": 100},
)

generator = VisualNode(
    id="gen1",
    type="generator",
    label="Generator",
    config={"model": "gpt-4"},
    position={"x": 300, "y": 100},
)

evaluator = VisualNode(
    id="eval1",
    type="accuracy_evaluate",
    label="Accuracy Evaluator",
    config={"threshold": 0.8},
    position={"x": 500, "y": 100},
)

pipeline = VisualPipeline(
    id="rag_with_eval",
    name="RAG with Evaluation",
    nodes=[retriever, generator, evaluator],
    connections=[
        VisualConnection(
            id="c1",
            source_node_id="ret1",
            source_port="output",
            target_node_id="gen1",
            target_port="input",
        ),
        VisualConnection(
            id="c2",
            source_node_id="gen1",
            source_port="output",
            target_node_id="eval1",
            target_port="input",
        ),
    ],
)
```

______________________________________________________________________

## 节点类型参考

### Generators (生成器)

| 类型               | 描述                | 主要配置                             |
| ------------------ | ------------------- | ------------------------------------ |
| `generator`        | 默认生成器 (OpenAI) | `model`, `temperature`, `max_tokens` |
| `openai_generator` | OpenAI API          | `model`, `api_key`, `temperature`    |
| `hf_generator`     | HuggingFace 模型    | `model_name`, `device`               |

**示例**:

```python
VisualNode(
    id="gen1",
    type="openai_generator",
    label="GPT-4",
    config={
        "model": "gpt-4-turbo",
        "temperature": 0.7,
        "max_tokens": 1000,
        "top_p": 0.9,
    },
)
```

### Retrievers (检索器)

| 类型                      | 描述                | 主要配置                                      |
| ------------------------- | ------------------- | --------------------------------------------- |
| `retriever`               | 默认检索器 (Chroma) | `top_k`, `collection_name`                    |
| `chroma_retriever`        | ChromaDB            | `collection_name`, `top_k`, `embedding_model` |
| `milvus_dense_retriever`  | Milvus 密集向量     | `collection_name`, `top_k`                    |
| `milvus_sparse_retriever` | Milvus 稀疏向量     | `collection_name`, `top_k`                    |

**示例**:

```python
VisualNode(
    id="ret1",
    type="chroma_retriever",
    label="Vector Search",
    config={
        "collection_name": "knowledge_base",
        "top_k": 10,
        "embedding_model": "text-embedding-ada-002",
        "metric": "cosine",
    },
)
```

### Rerankers (重排序器)

| 类型           | 描述           | 主要配置         |
| -------------- | -------------- | ---------------- |
| `reranker`     | 默认重排序器   | `top_k`          |
| `bge_reranker` | BGE 重排序模型 | `model`, `top_k` |

**示例**:

```python
VisualNode(
    id="rerank1",
    type="bge_reranker",
    label="Reranker",
    config={"model": "BAAI/bge-reranker-large", "top_k": 5, "batch_size": 32},
)
```

### Promptors (提示词模板)

| 类型                     | 描述       | 主要配置                 |
| ------------------------ | ---------- | ------------------------ |
| `promptor`               | 通用提示词 | `template`               |
| `qa_promptor`            | 问答模板   | `template`               |
| `summarization_promptor` | 摘要模板   | `template`, `max_length` |

**示例**:

```python
VisualNode(
    id="prompt1",
    type="qa_promptor",
    label="QA Template",
    config={
        "template": """Based on the following context:
{context}

Question: {question}

Please provide a detailed answer:"""
    },
)
```

### Chunkers (分块器)

| 类型                 | 描述       | 主要配置                             |
| -------------------- | ---------- | ------------------------------------ |
| `chunker`            | 默认分块器 | `chunk_size`, `overlap`              |
| `character_splitter` | 字符分割   | `chunk_size`, `overlap`, `separator` |

**示例**:

```python
VisualNode(
    id="chunk1",
    type="character_splitter",
    label="Text Splitter",
    config={"chunk_size": 1000, "overlap": 200, "separator": "\n\n"},
)
```

### Evaluators (评估器)

| 类型                | 描述        | 主要配置              |
| ------------------- | ----------- | --------------------- |
| `evaluator`         | 默认评估器  | `metric`, `threshold` |
| `accuracy_evaluate` | 准确性评估  | `threshold`           |
| `f1_evaluate`       | F1 分数评估 | `threshold`           |
| `recall_evaluate`   | 召回率评估  | `threshold`           |

**示例**:

```python
VisualNode(
    id="eval1",
    type="accuracy_evaluate",
    label="Accuracy Check",
    config={"threshold": 0.85, "metric": "exact_match"},
)
```

### 其他节点

| 类型      | 描述          | 主要配置               |
| --------- | ------------- | ---------------------- |
| `map`     | 映射/转换操作 | `function`, `strategy` |
| `refiner` | 结果精炼      | `strategy`, `params`   |

______________________________________________________________________

## 高级用法

### 自定义节点类型

```python
from sage.studio.services.node_registry import get_node_registry

# 注册自定义 Operator
registry = get_node_registry()
registry.register("my_custom_op", MyCustomOperator)

# 在流水线中使用
node = VisualNode(
    id="custom1",
    type="my_custom_op",
    label="Custom Operation",
    config={"param1": "value1"},
)
```

### 条件流水线

```python
# 使用 map 节点实现条件逻辑
condition_node = VisualNode(
    id="condition1",
    type="map",
    label="Condition Check",
    config={
        "function": "lambda x: x if x['score'] > 0.8 else None",
        "filter_none": True,
    },
)
```

### 并行执行

```python
# 创建并行分支
branch1 = VisualNode(
    id="b1", type="generator", label="Branch 1", config={"model": "gpt-4"}
)
branch2 = VisualNode(
    id="b2", type="generator", label="Branch 2", config={"model": "claude-3"}
)

# 两个分支从同一个源节点获取输入
connections = [
    VisualConnection(
        id="c1",
        source_node_id="source",
        source_port="output",
        target_node_id="b1",
        target_port="input",
    ),
    VisualConnection(
        id="c2",
        source_node_id="source",
        source_port="output",
        target_node_id="b2",
        target_port="input",
    ),
]
```

______________________________________________________________________

## 最佳实践

### 1. 命名约定

```python
# ✅ 好的命名
VisualNode(
    id="doc_retriever_1",  # 清晰的 ID
    type="chroma_retriever",
    label="Document Retriever",  # 人类可读的标签
)

# ❌ 避免
VisualNode(id="n1", type="retriever", label="node1")  # ID 太简单  # 标签不清晰
```

### 2. 配置管理

```python
# ✅ 使用配置对象
retriever_config = {
    "collection_name": "knowledge_base",
    "top_k": 10,
    "embedding_model": "text-embedding-ada-002",
}

retriever = VisualNode(
    id="retriever1", type="chroma_retriever", label="Retriever", config=retriever_config
)

# 可以重用配置
retriever2 = VisualNode(
    id="retriever2",
    type="chroma_retriever",
    label="Backup Retriever",
    config=retriever_config,
)
```

### 3. 错误处理

```python
from sage.studio.services import get_pipeline_builder

try:
    builder = get_pipeline_builder()
    env = builder.build(pipeline)
    job = env.execute()
except ValueError as e:
    print(f"Pipeline validation error: {e}")
except Exception as e:
    print(f"Execution error: {e}")
```

### 4. 流水线版本控制

```python
# 使用标签和描述进行版本管理
pipeline = VisualPipeline(
    id="rag_v2",
    name="RAG Pipeline v2.0",
    description="Added reranker and improved prompts",
    nodes=[...],
    connections=[...],
    tags=["v2.0", "production", "rag"],
)

# 序列化保存
import json

with open("pipeline_v2.json", "w") as f:
    json.dump(pipeline.to_dict(), f, indent=2)
```

### 5. 测试流水线

```python
import pytest
from sage.studio.models import VisualNode, VisualPipeline
from sage.studio.services import get_pipeline_builder


def test_my_pipeline():
    """测试流水线构建"""
    pipeline = VisualPipeline(
        id="test",
        name="Test Pipeline",
        nodes=[
            VisualNode(
                id="n1", type="generator", label="Gen", config={"model": "gpt-4"}
            )
        ],
        connections=[],
    )

    builder = get_pipeline_builder()
    env = builder.build(pipeline)

    assert env is not None
```

### 6. 性能优化

```python
# 配置合适的批处理大小
retriever = VisualNode(
    id="ret1",
    type="chroma_retriever",
    label="Retriever",
    config={
        "top_k": 10,
        "batch_size": 32,  # 批处理提高效率
        "cache_results": True,  # 缓存结果
    },
)

# 使用较小的模型进行开发测试
dev_generator = VisualNode(
    id="gen1",
    type="generator",
    label="Dev Generator",
    config={"model": "gpt-3.5-turbo", "max_tokens": 100},  # 开发用轻量模型
)
```

______________________________________________________________________

## 相关文档

- [SOURCE_SINK_CONFIG.md](./SOURCE_SINK_CONFIG.md) - Source/Sink 配置指南
- [REFACTORING_SUMMARY.md](./REFACTORING_SUMMARY.md) - 重构总结
- [PACKAGE_ARCHITECTURE.md](../../docs-public/docs_src/dev-notes/package-architecture.md) - 包架构文档

______________________________________________________________________

## 故障排查

### 问题: "Unknown node type" 错误

```python
# 检查可用的节点类型
from sage.studio.services.node_registry import get_node_registry

registry = get_node_registry()
print(registry.list_types())
```

### 问题: 流水线无法构建

```python
# 启用详细日志
import logging

logging.basicConfig(level=logging.DEBUG)

# 验证流水线结构
builder = get_pipeline_builder()
try:
    env = builder.build(pipeline)
except ValueError as e:
    print(f"Validation failed: {e}")
```

### 问题: 节点连接错误

确保：

1. 所有 `source_node_id` 和 `target_node_id` 对应实际存在的节点
1. 端口名称正确（通常为 `input` 和 `output`）
1. 没有循环依赖

______________________________________________________________________

## 贡献

欢迎贡献新的节点类型、示例和文档改进！

请参阅 [CONTRIBUTING.md](../../CONTRIBUTING.md) 了解详情。
