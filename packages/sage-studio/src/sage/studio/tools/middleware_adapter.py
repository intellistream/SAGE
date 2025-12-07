"""
Middleware Tool Adapter - 将 sage-middleware 算子适配为 Studio 工具

Layer: L6 (sage-studio)
"""

import asyncio
import inspect
from typing import Any

from pydantic import BaseModel, Field, create_model

from sage.libs.foundation.tools.tool import BaseTool as MiddlewareBaseTool
from sage.studio.tools.base import BaseTool as StudioBaseTool


class MiddlewareToolAdapter(StudioBaseTool):
    """
    通用适配器：将同步的 Middleware 工具转换为异步的 Studio 工具
    """

    def __init__(self, middleware_tool: MiddlewareBaseTool):
        self._middleware_tool = middleware_tool

        # 动态生成 Pydantic Schema
        args_schema = self._generate_schema(middleware_tool)

        # 设置实例属性覆盖类属性
        self.name = getattr(
            middleware_tool, "tool_name", getattr(middleware_tool, "name", "unknown_tool")
        )
        self.description = getattr(
            middleware_tool, "tool_description", getattr(middleware_tool, "description", "")
        )
        self.args_schema = args_schema

        super().__init__()

    def _parse_type_string(self, type_str: str) -> Any:
        """解析类型字符串为 Python 类型"""
        type_str = type_str.lower().strip()
        if type_str in ["int", "integer"]:
            return int
        elif type_str in ["str", "string"]:
            return str
        elif type_str in ["bool", "boolean"]:
            return bool
        elif type_str in ["float", "number"]:
            return float
        elif type_str in ["list", "array"]:
            return list
        elif type_str in ["dict", "object"]:
            return dict
        return Any

    def _generate_schema(self, middleware_tool: MiddlewareBaseTool) -> type[BaseModel]:
        """
        根据 Middleware 工具的 input_types 和 execute 方法签名生成 Pydantic Schema
        """
        schema_fields = {}

        # 1. 分析 execute 方法签名
        sig = inspect.signature(middleware_tool.execute)

        # 2. 获取 input_types 定义 (如果是字典)
        input_types = getattr(middleware_tool, "input_types", {})
        if not isinstance(input_types, dict):
            input_types = {}

        # 3. 合并参数来源
        # 优先使用签名中的参数，但也包含 input_types 中定义但签名中未显式列出的参数 (可能通过 **kwargs 传递)
        all_param_names = set(sig.parameters.keys()) | set(input_types.keys())

        for name in all_param_names:
            if name in ["self", "args", "kwargs"]:
                continue

            # 默认值
            py_type = Any
            default_value = ...  # Ellipsis 表示必填
            description = ""

            # 从签名中获取信息
            if name in sig.parameters:
                param = sig.parameters[name]
                if param.default != inspect.Parameter.empty:
                    default_value = param.default

                if param.annotation != inspect.Parameter.empty:
                    py_type = param.annotation

            # 从 input_types 中获取信息 (类型描述和文档)
            if name in input_types:
                type_desc = input_types[name]
                # 解析 "type - description" 格式
                if isinstance(type_desc, str) and " - " in type_desc:
                    type_str, desc_str = type_desc.split(" - ", 1)
                    description = desc_str

                    # 如果签名中没有类型注解，尝试从字符串解析
                    if py_type == Any:
                        py_type = self._parse_type_string(type_str)
                else:
                    description = str(type_desc)

            # 构建 Field
            field_kwargs = {"description": description}
            if default_value is not ...:
                field_kwargs["default"] = default_value

            schema_fields[name] = (py_type, Field(**field_kwargs))

        # 如果没有发现任何参数，创建一个空的 Schema
        tool_name = getattr(
            middleware_tool, "tool_name", getattr(middleware_tool, "name", "unknown_tool")
        )
        if not schema_fields:
            return create_model(f"{tool_name}Schema")

        return create_model(f"{tool_name}Schema", **schema_fields)

    async def _run(self, *args, **kwargs) -> Any:
        """运行 middleware 工具 (支持同步和异步)"""

        # 1. 检查 execute 是否为异步方法
        if inspect.iscoroutinefunction(self._middleware_tool.execute):
            return await self._middleware_tool.execute(*args, **kwargs)

        # 2. 如果是同步方法，在线程池中运行以避免阻塞事件循环
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

    args_schema: type[BaseModel] = Input

    def __init__(self):
        from sage.middleware.operators.tools.nature_news_fetcher import Nature_News_Fetcher_Tool

        self._tool = Nature_News_Fetcher_Tool()
        super().__init__()

    async def _run(self, num_articles: int = 5, max_pages: int = 1) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._tool.execute(num_articles=num_articles, max_pages=max_pages)
        )
