# SAGE 数据类型架构设计

## 架构概览

SAGE 采用分层的数据类型系统，从通用到专用逐层继承：

```
┌─────────────────────────────────────────────────────┐
│ sage.common.core.data_types (框架基础层)              │
│ - BaseDocument, BaseQueryResult                     │
│ - 适用于所有类型的算子                                 │
└──────────────────┬──────────────────────────────────┘
                   │ 继承
┌──────────────────┴──────────────────────────────────┐
│ sage.middleware.operators.rag.types (RAG 专用层)     │
│ - RAGDocument, RAGQuery, RAGResponse                │
│ - 添加 RAG 特定字段（relevance_score, generated 等）  │
└─────────────────────────────────────────────────────┘
                   │ 使用
┌──────────────────┴──────────────────────────────────┐
│ RAG Operators                                       │
│ - Retriever, Reranker, Generator, Refiner...       │
└─────────────────────────────────────────────────────┘
```

## 设计原则

### 1. 单一真相来源（Single Source of Truth）

**通用类型定义在 `sage-common`**：
- 位置：`packages/sage-common/src/sage/common/core/data_types.py`
- 目的：框架级别的基础数据结构
- 适用：所有类型的算子（RAG、搜索、多模态、分析等）

**领域特定类型继承通用类型**：
- RAG：`packages/sage-middleware/src/sage/middleware/operators/rag/types.py`
- 搜索：可创建 `packages/sage-middleware/src/sage/middleware/operators/search/types.py`
- 多模态：可创建 `packages/sage-middleware/src/sage/middleware/operators/multimodal/types.py`

### 2. 继承而非重复

```python
# ❌ 错误：每个领域都定义自己的类型
class RAGQueryResult(TypedDict):
    query: str
    results: List[Any]

class SearchQueryResult(TypedDict):
    query: str
    results: List[Any]

# ✅ 正确：继承通用类型
class RAGQueryResult(BaseQueryResult, total=False):
    # 只添加 RAG 特有的字段
    generated: Optional[str]

class SearchQueryResult(BaseQueryResult, total=False):
    # 只添加搜索特有的字段
    search_engine: Optional[str]
```

### 3. 类型安全与灵活性并重

```python
# 严格的输出类型
def execute(self, data: RAGInput) -> RAGResponse:
    ...

# 但支持灵活的输入格式（向后兼容）
RAGInput = Union[RAGQuery, Dict[str, Any], tuple, list]
```

## 类型继承树

### 文档类型

```
BaseDocument (sage.common)
├── text: str (必需)
├── id, title, source, score, rank, metadata (可选)
│
└── RAGDocument (sage.middleware.rag)
    ├── 继承所有 BaseDocument 字段
    └── 新增：relevance_score, embedding, chunk_id, references
```

### 查询-结果类型

```
BaseQueryResult (sage.common)
├── query: str (必需)
└── results: List[Any] (必需)
│
├── ExtendedQueryResult (sage.common)
│   ├── 继承 BaseQueryResult
│   └── 新增：query_id, timestamp, execution_time, metadata
│
└── RAGQuery / RAGResponse (sage.middleware.rag)
    ├── 继承 BaseQueryResult / ExtendedQueryResult
    └── 新增：generated, context, refined_docs, refine_metrics
```

## 使用示例

### 通用算子（使用基础类型）

```python
from sage.common.core.data_types import (
    BaseQueryResult,
    extract_query,
    extract_results,
    create_query_result,
)

class GenericOperator(MapOperator):
    def execute(self, data) -> BaseQueryResult:
        query = extract_query(data)
        results = self.process(query)
        return create_query_result(query, results)
```

### RAG 算子（使用 RAG 类型）

```python
from sage.middleware.operators.rag import (
    RAGInput,
    RAGResponse,
    extract_query,
    extract_results,
    create_rag_response,
)

class RAGOperator(MapOperator):
    def execute(self, data: RAGInput) -> RAGResponse:
        query = extract_query(data)
        results = self.process(query)
        return create_rag_response(
            query=query,
            results=results,
            generated="答案...",  # RAG 特有
        )
```

### 跨领域兼容性

```python
# RAG 算子的输出可以传递给通用算子
rag_output: RAGResponse = rag_operator.execute(data)

# 因为 RAGResponse 继承自 BaseQueryResult
generic_output = generic_operator.execute(rag_output)  # ✅ 类型兼容
```

## 扩展指南

### 为新领域添加类型

假设要为"搜索"领域添加专用类型：

1. **创建类型文件**：
   ```
   packages/sage-middleware/src/sage/middleware/operators/search/types.py
   ```

2. **继承基础类型**：
   ```python
   from sage.common.core.data_types import BaseDocument, BaseQueryResult
   
   class SearchDocument(BaseDocument, total=False):
       """搜索文档 - 添加搜索特有字段"""
       url: Optional[str]
       snippet: Optional[str]
       search_rank: Optional[int]
   
   class SearchResponse(BaseQueryResult, total=False):
       """搜索响应 - 添加搜索特有字段"""
       search_engine: Optional[str]
       total_results: Optional[int]
       search_time: Optional[float]
   ```

3. **导出类型**：
   ```python
   # packages/sage-middleware/src/sage/middleware/operators/search/__init__.py
   from sage.middleware.operators.search.types import SearchDocument, SearchResponse
   
   __all__ = ["SearchDocument", "SearchResponse", ...]
   ```

4. **算子使用**：
   ```python
   from sage.middleware.operators.search import SearchResponse, create_search_response
   
   class WebSearchOperator(MapOperator):
       def execute(self, data) -> SearchResponse:
           ...
   ```

## 优势总结

### 🎯 代码重用
- 基础类型定义一次，多处使用
- 减少重复代码

### 🔒 类型安全
- 完整的 Pylance/IDE 支持
- 编译时类型检查

### 🔄 向后兼容
- 支持多种输入格式（dict、tuple、list）
- 现有代码无需修改

### 📈 易于扩展
- 新领域继承基础类型
- 保持架构一致性

### 🤝 跨域兼容
- 不同领域的算子可以互操作
- 统一的数据流接口

## 相关文档

- 基础类型定义：`packages/sage-common/src/sage/common/core/data_types.py`
- RAG 类型定义：`packages/sage-middleware/src/sage/middleware/operators/rag/types.py`
- RAG 使用指南：`docs/dev-notes/RAG_DATA_TYPES_GUIDE.md`
