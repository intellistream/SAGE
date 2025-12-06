"""
Middleware Tool Adapter - 将 sage-middleware 算子适配为 Studio 工具

Layer: L6 (sage-studio)
"""

import asyncio
from typing import Any, Type

from pydantic import BaseModel, Field, create_model

from sage.libs.foundation.tools.tool import BaseTool as MiddlewareBaseTool
from sage.studio.tools.base import BaseTool as StudioBaseTool


class MiddlewareToolAdapter(StudioBaseTool):
    """
    通用适配器：将同步的 Middleware 工具转换为异步的 Studio 工具
    """

    def __init__(self, middleware_tool: MiddlewareBaseTool):
        self._middleware_tool = middleware_tool
        
        # 动态生成 Pydantic Schema (简化版，实际可能需要更复杂的类型解析)
        # 这里我们假设 middleware 工具的 input_types 描述了参数
        # 为了安全起见，我们暂时使用一个通用的 Dict 接收参数，或者由子类指定 Schema
        # 在这个通用适配器中，我们尝试根据 input_types 生成简单的 Schema
        
        schema_fields = {}
        if hasattr(middleware_tool, "input_types") and isinstance(middleware_tool.input_types, dict):
            for param_name, param_desc in middleware_tool.input_types.items():
                # 默认所有参数为可选字符串，实际应根据描述解析类型
                schema_fields[param_name] = (Any, Field(default=None, description=str(param_desc)))
        
        args_schema = create_model(
            f"{middleware_tool.tool_name}Schema",
            **schema_fields
        )

        super().__init__(
            name=middleware_tool.tool_name,
            description=middleware_tool.tool_description,
            args_schema=args_schema
        )

    async def _run(self, *args, **kwargs) -> Any:
        """在线程池中运行同步的 middleware 工具"""
        loop = asyncio.get_running_loop()
        
        # Middleware 工具通常使用 execute() 方法
        def run_sync():
            return self._middleware_tool.execute(*args, **kwargs)
            
        return await loop.run_in_executor(None, run_sync)


# 具体工具的适配示例 (为了更好的类型支持，建议为常用工具单独写适配类)

class NatureNewsTool(StudioBaseTool):
    """Nature News Fetcher Adapter"""
    
    name = "nature_news_fetcher"
    description = "Fetch latest news articles from Nature.com"
    
    class Input(BaseModel):
        num_articles: int = Field(5, description="Number of articles to fetch")
        max_pages: int = Field(1, description="Max pages to crawl")

    args_schema: Type[BaseModel] = Input

    def __init__(self):
        from sage.middleware.operators.tools.nature_news_fetcher import Nature_News_Fetcher_Tool
        self._tool = Nature_News_Fetcher_Tool()
        super().__init__()

    async def _run(self, num_articles: int = 5, max_pages: int = 1) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self._tool.execute(num_articles=num_articles, max_pages=max_pages)
        )
