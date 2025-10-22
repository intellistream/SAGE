# RAG 标准数据类型使用指南

## 概述

为了解决 SAGE RAG operators 之间数据格式不统一的问题，我们引入了标准化的数据类型系统。

## 核心类型

### RAGResponse
最基本的响应格式，所有算子都应该返回这个格式：

```python
from sage.middleware.operators.rag import RAGResponse, create_rag_response

# 标准格式
response: RAGResponse = {
    "query": "用户的查询",
    "results": ["结果1", "结果2", "结果3"]
}

# 使用辅助函数创建
response = create_rag_response(
    query="用户的查询",
    results=["结果1", "结果2"],
    # 可选的额外字段
    generated="生成的答案",
    refine_metrics={"compression_rate": 0.5}
)
```

### RAGInput
灵活的输入类型，支持多种格式：

```python
from sage.middleware.operators.rag import RAGInput

# 支持的输入格式：
# 1. 字典格式（推荐）
data1: RAGInput = {"query": "问题", "results": ["doc1", "doc2"]}

# 2. 元组格式（兼容旧代码）
data2: RAGInput = ("问题", ["doc1", "doc2"])

# 3. 列表格式
data3: RAGInput = ["问题", ["doc1", "doc2"]]
```

### RAGDocument
标准化的文档格式：

```python
from sage.middleware.operators.rag import RAGDocument

doc: RAGDocument = {
    "text": "文档内容",
    "title": "文档标题",
    "relevance_score": 0.95,
    "metadata": {"source": "wikipedia"}
}
```

## 辅助函数

### extract_query()
从任意格式提取查询文本：

```python
from sage.middleware.operators.rag import extract_query

# 从字典提取
query = extract_query({"query": "问题", "results": []})  # "问题"

# 从元组提取
query = extract_query(("问题", ["doc1"]))  # "问题"

# 从字符串提取
query = extract_query("直接的问题")  # "直接的问题"
```

### extract_results()
从任意格式提取结果列表：

```python
from sage.middleware.operators.rag import extract_results

# 从字典提取
results = extract_results({"query": "问题", "results": ["a", "b"]})  # ["a", "b"]

# 从元组提取
results = extract_results(("问题", ["a", "b"]))  # ["a", "b"]
```

### ensure_rag_response()
确保数据符合标准格式：

```python
from sage.middleware.operators.rag import ensure_rag_response

# 转换各种格式
response = ensure_rag_response(("query", ["results"]))
# 结果: {"query": "query", "results": ["results"]}

response = ensure_rag_response({"query": "q", "other_field": "value"})
# 结果: {"query": "q", "results": []}
```

## 在 Operator 中使用

### 标准模式

```python
from sage.kernel.operators import MapOperator
from sage.middleware.operators.rag import (
    RAGInput,
    RAGResponse,
    extract_query,
    extract_results,
    create_rag_response,
)

class MyRAGOperator(MapOperator):
    def execute(self, data: RAGInput) -> RAGResponse:
        # 1. 提取输入数据（自动处理各种格式）
        query = extract_query(data)
        docs = extract_results(data)
        
        # 2. 执行你的逻辑
        processed_docs = self.process(query, docs)
        
        # 3. 返回标准格式
        return create_rag_response(
            query=query,
            results=processed_docs,
            # 可选的额外信息
            processing_time=elapsed_time
        )
```

### 兼容旧代码

如果你的代码原来接受元组 `(query, docs)`，现在可以这样改：

```python
# 旧代码
def execute(self, data: Tuple[str, List[str]]) -> Tuple[str, List[str]]:
    query, docs = data
    processed = self.process(query, docs)
    return (query, processed)

# 新代码（完全兼容）
from sage.middleware.operators.rag import RAGInput, RAGResponse, extract_query, extract_results, create_rag_response

def execute(self, data: RAGInput) -> RAGResponse:
    query = extract_query(data)  # 自动从元组或字典提取
    docs = extract_results(data)
    processed = self.process(query, docs)
    return create_rag_response(query, processed)
```

## 实际案例

### Retriever → Reranker → Generator Pipeline

```python
from sage.middleware.operators.rag import (
    ChromaRetriever,
    BGEReranker,
    OpenAIGenerator,
)

# 1. Retriever 返回标准格式
retriever_output = retriever.execute({"query": "什么是机器学习?"})
# {"query": "什么是机器学习?", "results": ["doc1", "doc2", "doc3"]}

# 2. Reranker 接受并返回标准格式
reranked = reranker.execute(retriever_output)
# {"query": "什么是机器学习?", "results": ["doc2", "doc1", "doc3"]}

# 3. Generator 使用标准格式
response = generator.execute(reranked)
# {"query": "什么是机器学习?", "generated": "答案...", "results": [...]}
```

## 迁移检查清单

如果你要更新现有的 RAG operator：

- [ ] 导入类型：`from sage.middleware.operators.rag import RAGInput, RAGResponse, ...`
- [ ] 更新方法签名：`def execute(self, data: RAGInput) -> RAGResponse`
- [ ] 使用 `extract_query()` 和 `extract_results()` 提取数据
- [ ] 使用 `create_rag_response()` 创建返回值
- [ ] 删除手动格式判断代码（`if isinstance(data, dict)` 等）
- [ ] 运行测试确保兼容性

## 优势

✅ **类型安全**：IDE 和 Pylance 可以提供完整的类型检查和自动补全
✅ **向后兼容**：支持元组、列表、字典等多种格式
✅ **易于扩展**：可以轻松添加新字段而不破坏现有代码
✅ **统一接口**：所有 RAG operators 使用相同的数据格式
✅ **减少错误**：消除了 "Type X is not assignable to Y" 类型的错误

## 问题反馈

如果遇到问题或有改进建议，请：
1. 检查 `packages/sage-middleware/src/sage/middleware/operators/rag/types.py`
2. 查看实际使用案例（reranker.py, retriever.py 等）
3. 提出 issue 或 PR
