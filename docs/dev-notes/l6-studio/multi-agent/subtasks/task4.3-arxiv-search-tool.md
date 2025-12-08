# Task 4.3: ArxivSearchTool 论文搜索工具

## 目标
封装 Arxiv 论文搜索功能，支持研究论文辅导场景。

## 依赖
- Task 4.1 (BaseTool)

## 文件位置
`packages/sage-studio/src/sage/studio/tools/arxiv_search.py`

## 提示词

```
请实现 Arxiv 论文搜索工具，复用 examples 中的现有实现。

## 背景
SAGE 项目在 examples/tutorials/L3-libs/agents/arxiv_search_tool.py 中已有完整的 Arxiv 搜索实现。
我们需要将其封装为 Studio 的标准工具。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/tools/arxiv_search.py

2. 复用现有实现:
   - 导入 examples 中的 ArxivSearchTool
   - 或复制核心逻辑到此文件

3. 实现 StudioArxivSearchTool:
   ```python
   from pydantic import BaseModel, Field
   from sage.studio.tools.base import BaseTool

   class ArxivSearchInput(BaseModel):
       query: str = Field(..., description="论文搜索关键词，如 'transformer attention mechanism'")
       max_results: int = Field(5, description="最大返回论文数量", ge=1, le=20)
       with_abstract: bool = Field(True, description="是否包含摘要")

   class ArxivSearchTool(BaseTool):
       name = "arxiv_search"
       description = "搜索 ArXiv 学术论文库，获取相关论文的标题、作者、摘要和链接。适用于学术研究、文献调研、技术学习等场景。"
       args_schema = ArxivSearchInput

       async def _run(self, query: str, max_results: int = 5, with_abstract: bool = True) -> list[dict]:
           """执行 Arxiv 搜索"""
           pass
   ```

4. 返回格式:
   ```python
   [
       {
           "title": "Attention Is All You Need",
           "authors": ["Vaswani, A.", "Shazeer, N.", ...],
           "abstract": "The dominant sequence transduction models...",
           "link": "https://arxiv.org/abs/1706.03762",
           "published": "2017-06-12",
           "categories": ["cs.CL", "cs.LG"],
       },
       ...
   ]
   ```

5. 错误处理:
   - 网络超时
   - Arxiv 服务不可用
   - 无搜索结果

## 代码模板
```python
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from sage.studio.tools.base import BaseTool

logger = logging.getLogger(__name__)

# 尝试导入 examples 中的实现
try:
    from examples.tutorials.L3_libs.agents.arxiv_search_tool import ArxivSearchTool as OriginalArxivTool
    HAS_ORIGINAL_IMPL = True
except ImportError:
    HAS_ORIGINAL_IMPL = False
    OriginalArxivTool = None


class ArxivSearchInput(BaseModel):
    """Arxiv 搜索参数"""
    query: str = Field(..., description="论文搜索关键词")
    max_results: int = Field(5, description="最大返回数量", ge=1, le=20)
    with_abstract: bool = Field(True, description="是否包含摘要")


class ArxivSearchTool(BaseTool):
    """Arxiv 论文搜索工具

    搜索 ArXiv 学术论文库，支持:
    - 关键词搜索
    - 作者搜索
    - 论文 ID 查询

    适用场景:
    - 学术研究
    - 文献调研
    - 技术学习
    - 论文辅导
    """

    name = "arxiv_search"
    description = (
        "搜索 ArXiv 学术论文库，获取相关论文的标题、作者、摘要和链接。"
        "适用于学术研究、文献调研、技术学习、论文辅导等场景。"
        "支持关键词搜索，如 'machine learning', 'transformer attention' 等。"
    )
    args_schema = ArxivSearchInput

    def __init__(self):
        if HAS_ORIGINAL_IMPL:
            self._impl = OriginalArxivTool()
        else:
            self._impl = None
            logger.warning("Original ArxivSearchTool not available, using fallback")

    async def _run(
        self,
        query: str,
        max_results: int = 5,
        with_abstract: bool = True,
    ) -> list[dict[str, Any]]:
        """执行 Arxiv 搜索"""

        if self._impl:
            # 使用原有实现
            result = self._impl.call({
                "query": query,
                "max_results": max_results,
                "with_abstract": with_abstract,
                "size": 25,
            })
            return result.get("output", [])

        # Fallback: 直接实现搜索逻辑
        return await self._search_arxiv_directly(query, max_results, with_abstract)

    async def _search_arxiv_directly(
        self,
        query: str,
        max_results: int,
        with_abstract: bool,
    ) -> list[dict[str, Any]]:
        """直接实现 Arxiv 搜索（备用方案）"""
        import aiohttp
        from bs4 import BeautifulSoup

        base_url = "https://arxiv.org/search/"
        params = {
            "query": query,
            "searchtype": "all",
            "abstracts": "show" if with_abstract else "hide",
            "size": min(max_results * 2, 50),  # 多取一些以防过滤
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params, timeout=30) as resp:
                    if resp.status != 200:
                        raise Exception(f"Arxiv returned status {resp.status}")
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            results = []

            for item in soup.select("li.arxiv-result")[:max_results]:
                title_elem = item.select_one("p.title")
                authors_elem = item.select_one("p.authors")
                abstract_elem = item.select_one("span.abstract-full")
                link_elem = item.select_one("p.list-title a")

                results.append({
                    "title": title_elem.get_text(strip=True) if title_elem else "",
                    "authors": [a.get_text(strip=True) for a in authors_elem.select("a")] if authors_elem else [],
                    "abstract": abstract_elem.get_text(strip=True) if abstract_elem and with_abstract else "",
                    "link": link_elem["href"] if link_elem else "",
                })

            return results

        except Exception as e:
            logger.error(f"Arxiv search failed: {e}")
            raise


# 注册工具
def register_arxiv_tool():
    from sage.studio.tools.base import get_tool_registry
    registry = get_tool_registry()
    registry.register(ArxivSearchTool())
```

## 注意
- 处理网络超时（设置合理的 timeout）
- 缓存搜索结果（可选）
- 遵守 Arxiv 的使用规范（不要频繁请求）
```

## 验收标准
- [ ] 搜索功能正常工作
- [ ] 返回格式正确
- [ ] 错误处理完善
- [ ] 与 BaseTool 接口兼容
