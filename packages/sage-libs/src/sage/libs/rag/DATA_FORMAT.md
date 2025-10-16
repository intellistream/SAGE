# RAG 统一数据格式规范

## 概述

本文档定义了 SAGE RAG 框架中所有算子(Operator)使用的统一数据格式。所有算子均采用 **字典(dict)** 作为输入输出格式,遵循统一的字段命名规范。

## 设计原则

1. **统一性**: 所有算子使用相同的数据结构和命名规范
2. **可追溯性**: 每个阶段的输出都保留在数据流中,便于调试和分析
3. **类型安全**: 使用 TypedDict 定义明确的数据类型
4. **字段命名规范**: 采用 `{stage}_{type}` 模式,避免字段名冲突

## 命名规范

### 字段命名模式

```
{stage}_{type}
```

- **stage**: 处理阶段 (retrieval, reranking, refining, generation)
- **type**: 数据类型 (results, docs, time)

### 示例

| 阶段 | results 字段 | docs 字段 | time 字段 |
|------|-------------|----------|-----------|
| Retrieval (检索) | `retrieval_results` | `retrieval_docs` | `retrieval_time` |
| Reranking (重排) | `reranking_results` | `reranking_docs` | `reranking_time` |
| Refining (精炼) | `refining_results` | `refining_docs` | `refining_time` |
| Generation (生成) | - | `generated` | `generation_time` |

## 核心数据结构

### RAGData (TypedDict)

完整的 RAG 数据流包含以下字段:

```python
from typing import TypedDict, List, Dict, Any, Optional

class RAGData(TypedDict, total=False):
    """RAG 统一数据格式"""
    
    # 基础字段
    query: str                          # 用户查询
    question: Dict[str, Any]           # 原始问题数据 (包含 references 等)
    references: List[str]              # 标准答案列表
    
    # Retrieval 阶段
    retrieval_results: List[Dict[str, Any]]  # 检索结果详细信息
    retrieval_docs: List[str]                # 检索到的文档文本列表
    retrieval_time: float                    # 检索耗时(秒)
    
    # Reranking 阶段
    reranking_results: List[Dict[str, Any]]  # 重排序结果详细信息
    reranking_docs: List[str]                # 重排序后的文档列表
    reranking_time: float                    # 重排序耗时(秒)
    
    # Refining 阶段
    refining_results: List[Dict[str, Any]]   # 精炼结果详细信息
    refining_docs: List[str]                 # 精炼后的文档列表
    refining_time: float                     # 精炼耗时(秒)
    
    # Generation 阶段
    prompt: str                        # 最终生成的提示词
    generated: str                     # 生成的答案
    generation_time: float             # 生成耗时(秒)
    
    # 其他元数据
    input: Any                         # 原始输入数据
```

## 各阶段详细说明

### 1. Retrieval (检索阶段)

**算子**: `Wiki18FAISSRetriever`, `ChromaRetriever`, `MilvusRetriever` 等

**输入**:
```python
{
    "query": "什么是机器学习?",
    "question": {...}  # 可选
}
```

**输出**:
```python
{
    "query": "什么是机器学习?",
    "retrieval_results": [
        {"text": "文档1内容", "score": 0.95, "metadata": {...}},
        {"text": "文档2内容", "score": 0.89, "metadata": {...}},
        ...
    ],
    "retrieval_docs": [
        "文档1内容",
        "文档2内容",
        ...
    ],
    "retrieval_time": 0.123  # 秒
}
```

**字段说明**:
- `retrieval_results`: List[Dict] - 完整的检索结果,包含文本、分数、元数据等
- `retrieval_docs`: List[str] - 纯文本文档列表,方便后续算子直接使用
- `retrieval_time`: float - 检索操作耗时

### 2. Reranking (重排序阶段)

**算子**: `BGEReranker`, `LLMbased_Reranker`

**输入**: 继承 Retrieval 阶段的输出

**输出**: 在输入基础上追加:
```python
{
    # ...继承所有 retrieval_* 字段
    "reranking_results": [
        {"text": "文档2内容", "score": 0.97},
        {"text": "文档1内容", "score": 0.92},
        ...
    ],
    "reranking_docs": [
        "文档2内容",  # 重排序后文档1变成第2
        "文档1内容",  # 重排序后文档2变成第1
        ...
    ],
    "reranking_time": 0.056
}
```

**字段说明**:
- `reranking_results`: List[Dict] - 重排序后的结果,包含新的相关性分数
- `reranking_docs`: List[str] - 重排序后的文档列表
- `reranking_time`: float - 重排序操作耗时

**读取优先级**: Reranker 会优先从 `refining_docs` 读取,其次是 `retrieval_docs`

### 3. Refining (上下文精炼阶段)

**算子**: `RefinerOperator` (使用 LongRefiner 算法)

**输入**: 继承前序阶段的输出

**输出**: 在输入基础上追加:
```python
{
    # ...继承所有前序字段
    "refining_results": [
        {
            "text": "压缩后的文档1",
            "original_length": 1000,
            "refined_length": 300,
            "compression_ratio": 0.3
        },
        ...
    ],
    "refining_docs": [
        "压缩后的文档1",
        "压缩后的文档2",
        ...
    ],
    "refining_time": 1.234
}
```

**字段说明**:
- `refining_results`: List[Dict] - 精炼结果,包含压缩信息
- `refining_docs`: List[str] - 精炼后的文档列表(通常更短,更相关)
- `refining_time`: float - 精炼操作耗时

**读取优先级**: Refiner 会优先从 `reranking_docs` 读取,其次是 `retrieval_docs`

### 4. Prompting (提示词生成阶段)

**算子**: `QAPromptor`

**输入**: 继承前序阶段的输出

**输出**: 在输入基础上追加:
```python
{
    # ...继承所有前序字段
    "prompt": "根据以下上下文回答问题:\n上下文: 压缩后的文档1...\n问题: 什么是机器学习?\n答案:"
}
```

**字段说明**:
- `prompt`: str - 生成的完整提示词,包含上下文和问题

**读取优先级**: 
1. `refining_docs` (最高优先级,使用精炼后的文档)
2. `reranking_docs` (次优先级,使用重排序后的文档)
3. `retrieval_docs` (最低优先级,使用原始检索文档)

### 5. Generation (答案生成阶段)

**算子**: `OpenAIGenerator`

**输入**: 继承前序阶段的输出 (必须包含 `prompt` 字段)

**输出**: 在输入基础上追加:
```python
{
    # ...继承所有前序字段
    "generated": "机器学习是人工智能的一个分支,它使计算机系统能够从数据中学习...",
    "generation_time": 0.789
}
```

**字段说明**:
- `generated`: str - 模型生成的答案文本
- `generation_time`: float - 生成操作耗时

## 评估阶段

### Evaluate Operators

评估算子从数据流中读取相应字段进行评估:

#### AccuracyEvaluate
```python
# 读取字段
generated = data.get("generated")
references = data.get("references")
```

#### TokenCountEvaluate
```python
# 读取优先级: refining_docs > reranking_docs > retrieval_docs
docs = data.get("refining_docs") or data.get("reranking_docs") or data.get("retrieval_docs")
```

#### CompressionRateEvaluate
```python
# 对比检索和精炼的文档长度
retrieval_docs = data.get("retrieval_docs")
refining_docs = data.get("refining_docs")
compression_rate = len(refining_docs) / len(retrieval_docs)
```

#### LatencyEvaluate
```python
# 累加各阶段耗时
total_latency = data.get("refining_time", 0.0) + data.get("generation_time", 0.0)
```

#### ContextRecallEvaluate
```python
# 检查生成答案是否包含参考答案中的关键信息
generated = data.get("generated")
references = data.get("references")
```

## 完整数据流示例

```python
# 1. 初始输入
data = {
    "query": "什么是深度学习?",
    "question": {
        "id": "q001",
        "references": ["深度学习是机器学习的子集..."]
    },
    "references": ["深度学习是机器学习的子集..."]
}

# 2. 经过 Retriever
data = {
    "query": "什么是深度学习?",
    "question": {...},
    "references": [...],
    "retrieval_results": [{...}, {...}, ...],
    "retrieval_docs": ["文档1", "文档2", ...],
    "retrieval_time": 0.123
}

# 3. 经过 Reranker (可选)
data = {
    # ...所有前序字段
    "reranking_results": [{...}, {...}, ...],
    "reranking_docs": ["文档2", "文档1", ...],  # 重排序
    "reranking_time": 0.056
}

# 4. 经过 Refiner
data = {
    # ...所有前序字段
    "refining_results": [{...}, {...}, ...],
    "refining_docs": ["压缩文档1", "压缩文档2", ...],
    "refining_time": 1.234
}

# 5. 经过 Promptor
data = {
    # ...所有前序字段
    "prompt": "根据以下上下文回答问题:..."
}

# 6. 经过 Generator
data = {
    # ...所有前序字段
    "generated": "深度学习是机器学习的一个子集...",
    "generation_time": 0.789
}

# 7. 经过 Evaluate
# 各评估器读取相应字段进行评估,不修改 data
```

## 迁移指南

### 从旧格式迁移

如果你的代码使用了旧的字段名,请按以下映射更新:

| 旧字段名 | 新字段名 | 说明 |
|---------|---------|------|
| `results` | `retrieval_results` 或 `refining_results` | 根据上下文判断 |
| `retrieved_docs` | `retrieval_docs` | 检索文档列表 |
| `refined_docs` | `refining_docs` | 精炼文档列表 |
| `refine_time` | `refining_time` | 精炼耗时 |
| `generate_time` | `generation_time` | 生成耗时 |
| `pred` | `generated` | 生成的答案 |
| `golds` | `references` | 参考答案 |

### 不再支持的格式

1. **Tuple 格式**: 旧版本支持 `(query, docs)` 元组格式,现已移除
2. **嵌套 metrics**: 如 `refine_metrics.refine_time`,已扁平化为 `refining_time`
3. **多义字段**: 如 `results` 在不同阶段有不同含义,已拆分为明确的 `{stage}_results`

## 最佳实践

### 1. 使用 TypedDict 进行类型检查

```python
from typing import TypedDict, List, Dict, Any

class RAGData(TypedDict, total=False):
    query: str
    retrieval_docs: List[str]
    generated: str
    # ... 其他字段

def my_operator(data: RAGData) -> RAGData:
    # IDE 会提供自动补全和类型检查
    docs = data.get("retrieval_docs", [])
    return data
```

### 2. 使用 data.update() 追加字段

```python
def execute(self, data: dict) -> dict:
    # 处理逻辑
    results = self.process(data["query"])
    
    # 使用 update 追加新字段
    data.update({
        "retrieval_results": results,
        "retrieval_docs": [r["text"] for r in results],
        "retrieval_time": elapsed_time
    })
    
    return data
```

### 3. 遵循读取优先级

```python
# 在 Promptor 中读取文档
docs = (
    data.get("refining_docs") or      # 优先使用精炼后的文档
    data.get("reranking_docs") or     # 其次使用重排序的文档
    data.get("retrieval_docs", [])    # 最后使用原始检索文档
)
```

### 4. 保留所有阶段数据

```python
# ✅ 正确: 追加新字段,保留旧字段
data.update({"reranking_docs": new_docs})

# ❌ 错误: 覆盖旧字段
data["retrieval_docs"] = new_docs  # 丢失了原始检索结果
```

## 常见问题

### Q1: 为什么要使用 {stage}_{type} 命名模式?

**A**: 避免字段名冲突。旧版本中 `results` 字段在 retriever 和 refiner 中都被使用,导致后者覆盖前者的数据。新格式确保每个阶段的数据都有唯一标识。

### Q2: 如果某个阶段被跳过怎么办?

**A**: 后续算子会根据优先级读取可用字段。例如,如果没有 reranking 阶段,promptor 会直接读取 `retrieval_docs`。

### Q3: 为什么需要同时保留 results 和 docs 字段?

**A**: 
- `*_results`: 包含完整信息(文本、分数、元数据),用于调试、分析和存档
- `*_docs`: 纯文本列表,方便后续算子直接使用,无需解析复杂结构

### Q4: 如何添加自定义字段?

**A**: 可以在 data 中添加任意字段,但建议:
1. 使用命名空间前缀避免冲突,如 `custom_my_field`
2. 在 TypedDict 中声明(如果使用类型检查)
3. 不要覆盖标准字段
