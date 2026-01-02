# Task 4: Tools Implementation (工具层实现)

## 任务概述

实现 Multi-Agent 系统所需的具体工具。这些工具将被 AgentOrchestrator 调用，执行实际的任务，如知识检索、代码执行、API 查询等。

**优先级**: P1 (中)\
**预计工时**: 2-3 天\
**可并行**: 是（依赖 Task 2 接口）

## 目标

1. **标准化接口**: 所有工具遵循统一的 `BaseTool` 接口
1. **自描述**: 每个工具包含详细的描述和参数 schema，便于 LLM 理解
1. **安全性**: 对敏感操作（如代码执行）实施安全限制
1. **复用现有资产**: 优先复用 `sage-libs` 和 `examples` 中的现有工具实现

## 复用策略

SAGE 项目中已存在大量高质量工具，应优先复用：

1. **sage-libs**: `sage.libs.foundation.tools` 和 `sage.libs.agentic.tools`
1. **examples**: `examples/tutorials/L3-libs/agents/arxiv_search_tool.py` (Arxiv 搜索)
1. **sage-benchmark**: `sage.benchmark.benchmark_agent.tools_loader` (1000+ 工具集)

## 文件位置

```
packages/sage-studio/src/sage/studio/tools/__init__.py
packages/sage-studio/src/sage/studio/tools/base.py
packages/sage-studio/src/sage/studio/tools/knowledge_search.py
packages/sage-studio/src/sage/studio/tools/api_docs.py
packages/sage-studio/src/sage/studio/tools/code_executor.py
packages/sage-studio/src/sage/studio/tools/arxiv_search.py  # [新增] 复用 ArxivSearchTool
packages/sage-studio/tests/unit/tools/test_tools.py
```

## 接口设计

### 1. BaseTool (工具基类)

```python
"""
Base Tool Interface for SAGE Studio

Layer: L6 (sage-studio)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel

# 尝试复用 sage-libs 的 BaseTool
try:
    from sage.libs.foundation.tools.tool import BaseTool as LibBaseTool
except ImportError:
    LibBaseTool = object

class BaseTool(LibBaseTool, ABC):
    """工具基类

    如果 sage-libs 可用，继承自 LibBaseTool 以保持兼容性。
    否则使用本地定义的接口。
    """

    name: str
    """工具名称，如 'knowledge_search'"""

    description: str
    """工具描述，用于 LLM 理解工具用途"""

    args_schema: Type[BaseModel] | None = None
    """参数 Schema，用于验证输入"""

    @abstractmethod
    async def _run(self, *args, **kwargs) -> Any:
        """执行工具逻辑"""
        pass

    async def run(self, *args, **kwargs) -> Dict[str, Any]:
        """统一执行入口，包含错误处理和日志"""
        try:
            # 参数验证（如果提供了 schema）
            if self.args_schema:
                # ... validate args ...
                pass

            result = await self._run(*args, **kwargs)
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

### 2. KnowledgeSearchTool (知识检索工具)

封装 `KnowledgeManager` 的检索功能。

```python
from pydantic import BaseModel, Field
from sage.studio.services.knowledge_manager import KnowledgeManager

class SearchInput(BaseModel):
    query: str = Field(..., description="检索关键词或问题")
    sources: list[str] | None = Field(None, description="指定检索源，如 ['sage_docs', 'user_uploads']")
    top_k: int = Field(5, description="返回结果数量")

class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    description = "检索 SAGE 框架的相关知识、文档、示例代码以及用户上传的文件"
    args_schema = SearchInput

    def __init__(self, knowledge_manager: KnowledgeManager):
        self.km = knowledge_manager

    async def _run(self, query: str, sources: list[str] = None, top_k: int = 5):
        # 确保源已加载
        if sources:
            for source in sources:
                await self.km.ensure_source_loaded(source)

        results = await self.km.search(query, sources, top_k)
        return [
            {
                "content": r.content,
                "source": r.source,
                "score": r.score
            }
            for r in results
        ]
```

### 3. APIDocsTool (API 文档工具)

专门用于检索 Python API 文档（通过静态分析或运行时检查）。

```python
class APIDocsInput(BaseModel):
    symbol: str = Field(..., description="要查询的类名、函数名或模块名")

class APIDocsTool(BaseTool):
    name = "api_docs_lookup"
    description = "查询 SAGE 框架的 API 文档、参数说明和函数签名"
    args_schema = APIDocsInput

    async def _run(self, symbol: str):
        # 1. 尝试导入符号
        # 2. 获取 docstring 和 signature
        # 3. 返回格式化的文档
        pass
```

### 4. ArxivSearchTool (论文搜索工具 - 复用)

复用 `examples/tutorials/L3-libs/agents/arxiv_search_tool.py` 中的实现。

````python
# packages/sage-studio/src/sage/studio/tools/arxiv_search.py

from typing import Any, Dict
from pydantic import BaseModel, Field
from sage.studio.tools.base import BaseTool

# 尝试导入示例中的实现，或者直接复制其逻辑
try:
    # 注意：这需要 examples 目录在 PYTHONPATH 中，或者将其逻辑复制过来
    # 推荐做法：将 examples 中的逻辑复制到这里，使其成为正式组件
    from examples.tutorials.L3_libs.agents.arxiv_search_tool import ArxivSearchTool as OriginalArxivTool
except ImportError:
    # 备选：如果无法导入，则在此处重新实现（参考 examples 中的代码）
    class OriginalArxivTool:
        def call(self, arguments): pass
        # ... (复制核心逻辑)

class ArxivSearchInput(BaseModel):
    query: str = Field(..., description="论文搜索关键词")
    max_results: int = Field(5, description="最大返回数量")

class ArxivSearchTool(BaseTool):
    name = "arxiv_search"
    description = "搜索 ArXiv 上的学术论文，获取标题、作者、摘要和链接"
    args_schema = ArxivSearchInput

    def __init__(self):
        self._impl = OriginalArxivTool()

    async def _run(self, query: str, max_results: int = 5) -> Any:
        # 适配接口：BaseTool -> OriginalArxivTool
        return self._impl.call({
            "query": query,
            "max_results": max_results,
            "size": 25,
            "with_abstract": True
        })
```        pass
````

### 4. CodeExecutorTool (代码执行工具) - 可选/高级

用于执行生成的代码片段（需谨慎实现，建议先做沙箱或仅支持特定操作）。

```python
class CodeExecutorTool(BaseTool):
    name = "python_repl"
    description = "执行 Python 代码片段（仅限数据处理逻辑）"

    async def _run(self, code: str):
        # 简单实现：使用 exec() 但限制 globals
        # 高级实现：使用 docker 或 jupyter kernel
        pass
```

## 工具注册表

在 `packages/sage-studio/src/sage/studio/tools/__init__.py` 中提供统一的工具获取接口。

```python
from .knowledge_search import KnowledgeSearchTool
from .api_docs import APIDocsTool
# ...

def get_all_tools(knowledge_manager) -> list[BaseTool]:
    return [
        KnowledgeSearchTool(knowledge_manager),
        APIDocsTool(),
        # ...
    ]
```

## 测试计划

```python
# tests/unit/tools/test_tools.py

import pytest
from sage.studio.tools.knowledge_search import KnowledgeSearchTool
from sage.studio.tools.api_docs import APIDocsTool

class TestTools:

    @pytest.mark.asyncio
    async def test_knowledge_search(self, mock_knowledge_manager):
        tool = KnowledgeSearchTool(mock_knowledge_manager)
        result = await tool.run(query="pipeline", sources=["sage_docs"])
        assert result["status"] == "success"
        assert len(result["result"]) > 0

    @pytest.mark.asyncio
    async def test_api_docs(self):
        tool = APIDocsTool()
        # 测试查询真实存在的 API
        result = await tool.run(symbol="sage.llm.UnifiedInferenceClient")
        assert result["status"] == "success"
        assert "UnifiedInferenceClient" in result["result"]
```

## 提示词（复制使用）

```
请在 SAGE 项目中实现 Multi-Agent 工具层。

## 背景
SAGE Studio 的 Agent 需要一系列工具来执行实际任务，如检索知识、查询 API 等。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/tools/
2. 实现 BaseTool 抽象基类 (base.py)
3. 实现 KnowledgeSearchTool (knowledge_search.py)，集成 KnowledgeManager
4. 实现 APIDocsTool (api_docs.py)，用于动态获取 Python 对象的文档
5. 在 __init__.py 中导出工具注册函数
6. 使用 Pydantic 定义参数 Schema

## 注意
- 工具应具有良好的错误处理机制
- APIDocsTool 应能处理导入错误和属性查找
- 保持接口异步 (async/await)
```
