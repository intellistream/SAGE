# RAG 标准数据类型使用指南

## 概述

SAGE 现在提供了一套分层的标准化数据类型系统：

```
sage.common.core.data_types (通用基础层)
    ↓ 继承
sage.middleware.operators.rag.types (RAG 专用层)
    ↓ 使用
RAG Operators (Retriever, Reranker, Generator...)
```

**设计理念**：
- 通用基础类型在 `sage-common` 中定义，适用于所有类型的算子
- RAG 专用类型继承基础类型，添加 RAG 特定的字段
- 其他领域（搜索、多模态等）可以类似地继承基础类型

## 类型继承关系

### 文档类型继承

```python
BaseDocument (通用)
    ├── text: str                    # 文档内容
    ├── id, title, source            # 基础元数据
    └── score, rank, metadata        # 通用字段

    ↓ 继承

RAGDocument (RAG 专用)
    ├── 继承所有 BaseDocument 字段
    └── 新增：
        ├── relevance_score          # RAG 相关性分数
        ├── embedding                # 向量嵌入
        ├── chunk_id                 # 分块ID
        └── references               # 引用列表
```

### 查询-结果类型继承

```python
BaseQueryResult (通用)
    ├── query: str                   # 查询文本
    └── results: List[Any]           # 结果列表

    ↓ 继承

ExtendedQueryResult (通用扩展)
    ├── 继承 BaseQueryResult
    └── 新增：query_id, timestamp, execution_time, metadata...

    ↓ 继承

RAGQuery / RAGResponse (RAG 专用)
    ├── 继承 ExtendedQueryResult / BaseQueryResult
    └── 新增：
        ├── generated                # 生成的答案
        ├── context                  # 上下文
        ├── refined_docs             # 精炼文档
        └── refine_metrics           # 精炼指标
```

## 核心类型

### 通用基础类型（sage.common.core.data_types）

### 通用基础类型（sage.common.core.data_types）

这些类型可以被任何算子使用，不限于 RAG：

```python
from sage.common.core.data_types import (
    BaseDocument,         # 基础文档结构
    BaseQueryResult,      # 基础查询-结果对
    ExtendedQueryResult,  # 扩展查询-结果对
    # 辅助函数
    extract_query,
    extract_results,
    create_query_result,
)

# 基础查询-结果对
result: BaseQueryResult = {
    "query": "用户查询",
    "results": ["结果1", "结果2"]
}

# 扩展格式（添加更多字段）
extended: ExtendedQueryResult = {
    "query": "用户查询",
    "results": ["结果1", "结果2"],
    "execution_time": 0.5,
    "metadata": {"model": "gpt-4"}
}
```

### RAG 专用类型（sage.middleware.operators.rag.types）

继承通用类型，添加 RAG 特定字段：

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
