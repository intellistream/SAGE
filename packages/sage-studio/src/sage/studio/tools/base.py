"""
Studio Tool Base Classes - 工具层基础设施

Layer: L6 (sage-studio)

Provides:
- BaseTool: 异步工具基类，支持 Pydantic 参数验证和 OpenAI function calling 格式
- ToolRegistry: 工具注册表，管理所有可用工具
- get_tool_registry: 获取全局工具注册表实例

Note:
    sage-libs 中有 BaseTool 定义 (sage.libs.foundation.tools.tool.BaseTool)，
    但该实现是同步的且缺少 Pydantic schema 支持。Studio 工具层需要异步执行
    和 OpenAI function calling 格式输出，因此定义独立的基类。
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Studio 工具基类

    为 Multi-Agent 系统提供统一的工具接口，支持:
    - 异步执行 (async/await)
    - Pydantic 参数验证
    - OpenAI function calling 格式输出
    - 统一的错误处理和日志

    Attributes:
        name: 工具名称，如 'knowledge_search'
        description: 工具描述，用于 LLM 理解工具用途
        args_schema: Pydantic 模型，定义参数 Schema

    Example:
        >>> from pydantic import BaseModel, Field
        >>>
        >>> class SearchInput(BaseModel):
        ...     query: str = Field(..., description="检索关键词")
        ...     top_k: int = Field(5, description="返回数量")
        >>>
        >>> class MySearchTool(BaseTool):
        ...     name = "my_search"
        ...     description = "搜索文档"
        ...     args_schema = SearchInput
        ...
        ...     async def _run(self, query: str, top_k: int = 5) -> list[str]:
        ...         return ["result1", "result2"]
    """

    # 类属性，子类应覆盖
    name: ClassVar[str] = "base_tool"
    description: ClassVar[str] = "Base tool description"
    args_schema: ClassVar[type[BaseModel] | None] = None

    # 可选：执行超时（秒），None 表示无限制
    timeout: ClassVar[float | None] = None

    @abstractmethod
    async def _run(self, **kwargs: Any) -> Any:
        """实际执行逻辑（子类必须实现）

        Args:
            **kwargs: 经过验证的参数

        Returns:
            工具执行结果，类型由具体工具定义

        Raises:
            任何执行过程中的异常都会被 run() 捕获并转换为错误响应
        """
        raise NotImplementedError

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """统一执行入口

        包含参数验证、超时控制、错误处理和日志记录。

        Args:
            **kwargs: 工具参数

        Returns:
            dict: 包含 status 和 result/error 的字典
                - status: "success" 或 "error"
                - result: 成功时的执行结果
                - error: 失败时的错误信息
        """
        logger.info(f"Tool [{self.name}] executing with args: {kwargs}")

        try:
            # 参数验证
            validated_kwargs = self._validate_args(kwargs)

            # 执行（可选超时）
            if self.timeout is not None:
                result = await asyncio.wait_for(
                    self._run(**validated_kwargs),
                    timeout=self.timeout,
                )
            else:
                result = await self._run(**validated_kwargs)

            logger.info(f"Tool [{self.name}] completed successfully")
            return {"status": "success", "result": result}

        except ValidationError as e:
            error_msg = f"参数验证失败: {e}"
            logger.error(f"Tool [{self.name}] validation error: {e}")
            return {"status": "error", "error": error_msg}

        except TimeoutError:
            error_msg = f"执行超时 ({self.timeout}s)"
            logger.error(f"Tool [{self.name}] timeout after {self.timeout}s")
            return {"status": "error", "error": error_msg}

        except Exception as e:
            logger.exception(f"Tool [{self.name}] execution error: {e}")
            return {"status": "error", "error": str(e)}

    def _validate_args(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """验证并转换参数

        Args:
            kwargs: 原始参数字典

        Returns:
            验证后的参数字典

        Raises:
            ValidationError: 参数验证失败
        """
        if self.args_schema is None:
            return kwargs

        validated = self.args_schema(**kwargs)
        return validated.model_dump()

    def run_sync(self, **kwargs: Any) -> dict[str, Any]:
        """同步执行入口（用于非异步环境）

        Args:
            **kwargs: 工具参数

        Returns:
            dict: 同 run() 方法
        """
        return asyncio.run(self.run(**kwargs))

    def get_schema(self) -> dict[str, Any]:
        """返回 OpenAI function calling 格式的 schema

        Returns:
            dict: 符合 OpenAI API 格式的工具定义
                {
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "description": "tool description",
                        "parameters": { ... JSON Schema ... }
                    }
                }
        """
        schema: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
            },
        }

        if self.args_schema is not None:
            # 获取 Pydantic 模型的 JSON Schema
            json_schema = self.args_schema.model_json_schema()
            # 移除 title 字段（OpenAI 不需要）
            json_schema.pop("title", None)
            schema["function"]["parameters"] = json_schema
        else:
            # 无参数
            schema["function"]["parameters"] = {
                "type": "object",
                "properties": {},
                "required": [],
            }

        return schema

    def __str__(self) -> str:
        return f"Tool({self.name})"

    def __repr__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description}')"


class ToolRegistry:
    """工具注册表

    管理所有可用工具，支持注册、查询和列出工具。
    与 sage-libs 的 ToolRegistry 不同，这里不使用单例模式，
    允许创建多个独立的注册表实例。

    Example:
        >>> registry = ToolRegistry()
        >>> registry.register(MySearchTool())
        >>> tool = registry.get("my_search")
        >>> schemas = registry.list_schemas()  # 用于 LLM
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具

        Args:
            tool: BaseTool 实例

        Raises:
            TypeError: tool 不是 BaseTool 实例
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool instance, got {type(tool).__name__}")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """取消注册工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功取消注册
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """获取工具

        Args:
            name: 工具名称

        Returns:
            BaseTool 实例或 None
        """
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """列出所有工具实例

        Returns:
            所有已注册的工具列表
        """
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """列出所有工具名称

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def list_schemas(self) -> list[dict[str, Any]]:
        """列出所有工具的 OpenAI schema

        用于传递给 LLM 的 tools 参数。

        Returns:
            工具 schema 列表
        """
        return [tool.get_schema() for tool in self._tools.values()]

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        logger.info("Tool registry cleared")

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())


# 全局注册表实例
_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表实例

    Returns:
        ToolRegistry: 全局注册表单例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry() -> None:
    """重置全局工具注册表（主要用于测试）"""
    global _global_registry
    if _global_registry is not None:
        _global_registry.clear()
    _global_registry = None
