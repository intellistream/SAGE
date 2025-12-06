# Task 4.2: KnowledgeSearchTool 实现

## 目标
实现知识库检索工具，封装 KnowledgeManager 的检索功能。

## 依赖
- Task 4.1 (BaseTool)
- Task 2.4 (KnowledgeManager)

## 文件位置
`packages/sage-studio/src/sage/studio/tools/knowledge_search.py`

## 提示词

```
请实现 KnowledgeSearchTool，封装 KnowledgeManager 的检索功能。

## 背景
KnowledgeSearchTool 是 Multi-Agent 系统的核心工具，用于检索：
- SAGE 官方文档
- 代码示例
- 用户上传的文档

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/tools/knowledge_search.py

2. 继承 BaseTool:
   ```python
   class KnowledgeSearchTool(BaseTool):
       name = "knowledge_search"
       description = "搜索 SAGE 知识库，包括文档、示例和用户上传的资料"
   ```

3. 支持参数:
   - query: 搜索查询
   - sources: 要搜索的来源列表 (可选)
   - top_k: 返回结果数量 (默认 5)

4. 返回格式:
   ```python
   {
       "status": "success",
       "result": [
           {
               "content": "文档内容片段",
               "source": "sage_docs",
               "metadata": {"file": "...", "section": "..."},
               "score": 0.95
           }
       ]
   }
   ```

## 代码模板
```python
from __future__ import annotations

import logging
from typing import Any

from sage.studio.tools.base import BaseTool, ToolParameter
from sage.studio.services.knowledge_manager import KnowledgeManager

logger = logging.getLogger(__name__)


class KnowledgeSearchTool(BaseTool):
    """知识库检索工具"""

    name = "knowledge_search"
    description = "搜索 SAGE 知识库，包括文档、示例代码和用户上传的资料"

    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="搜索查询内容",
            required=True,
        ),
        ToolParameter(
            name="sources",
            type="array",
            description="要搜索的来源，可选值: sage_docs, examples, user_uploads",
            required=False,
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="返回结果数量",
            required=False,
        ),
    ]

    def __init__(self, knowledge_manager: KnowledgeManager):
        super().__init__()
        self.km = knowledge_manager

    async def run(
        self,
        query: str,
        sources: list[str] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """执行知识库检索"""
        sources = sources or ["sage_docs", "examples"]

        try:
            results = await self.km.search(
                query=query,
                sources=sources,
                top_k=top_k,
            )

            return {
                "status": "success",
                "result": [
                    {
                        "content": doc.content,
                        "source": doc.source.value,
                        "metadata": doc.metadata,
                        "score": doc.score,
                    }
                    for doc in results
                ]
            }
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
```

## 注意
- 依赖注入 KnowledgeManager
- 默认搜索 sage_docs 和 examples
- 返回统一的结果格式
```

## 验收标准
- [ ] 继承 BaseTool
- [ ] 参数定义完整
- [ ] 调用 KnowledgeManager.search()
- [ ] 错误处理完善
