# Task 4.1: BaseTool 基类

## 目标

定义工具基类，为所有工具提供统一接口。

## 文件位置

`packages/sage-studio/src/sage/studio/tools/base.py`

## 提示词

````
请实现 Studio 工具层的基类。

## 背景
sage-libs 中已有 BaseTool 定义:
- sage.libs.foundation.tools.tool.BaseTool

我们应该尽量复用，但也需要适配 Studio 的异步需求。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/tools/base.py

2. 定义 BaseTool 抽象基类:
   ```python
   from abc import ABC, abstractmethod
   from typing import Any, Dict, Type
   from pydantic import BaseModel

   class BaseTool(ABC):
       name: str                              # 工具名称
       description: str                       # 工具描述 (给 LLM 看)
       args_schema: Type[BaseModel] | None    # 参数 Schema

       @abstractmethod
       async def _run(self, **kwargs) -> Any:
           """实际执行逻辑（子类实现）"""
           pass

       async def run(self, **kwargs) -> Dict[str, Any]:
           """统一入口，包含验证、错误处理、日志"""
           pass

       def get_schema(self) -> dict:
           """返回 OpenAI function calling 格式的 schema"""
           pass
````

3. 兼容性考虑:

   - 尝试继承 sage.libs.foundation.tools.tool.BaseTool
   - 如果不可用，使用独立定义
   - 支持同步和异步执行

1. 工具注册机制:

   ```python
   class ToolRegistry:
       def __init__(self):
           self._tools: dict[str, BaseTool] = {}

       def register(self, tool: BaseTool) -> None:
           self._tools[tool.name] = tool

       def get(self, name: str) -> BaseTool | None:
           return self._tools.get(name)

       def list_tools(self) -> list[dict]:
           """返回所有工具的 schema 列表（用于 LLM）"""
           return [t.get_schema() for t in self._tools.values()]
   ```

## 代码模板

```python
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# 尝试复用 sage-libs 的 BaseTool
try:
    from sage.libs.foundation.tools.tool import BaseTool as LibBaseTool
    HAS_LIB_TOOL = True
except ImportError:
    LibBaseTool = object
    HAS_LIB_TOOL = False


class BaseTool(LibBaseTool if HAS_LIB_TOOL else ABC):
    """Studio 工具基类

    提供统一的工具接口，支持:
    - 参数验证 (via Pydantic)
    - 错误处理
    - 执行日志
    - OpenAI function calling 格式输出
    """

    name: str = "base_tool"
    description: str = "Base tool description"
    args_schema: Type[BaseModel] | None = None

    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        """实际执行逻辑（子类必须实现）"""
        raise NotImplementedError

    async def run(self, **kwargs) -> Dict[str, Any]:
        """统一执行入口"""
        logger.info(f"Tool [{self.name}] executing with args: {kwargs}")

        try:
            # 参数验证
            if self.args_schema:
                validated = self.args_schema(**kwargs)
                kwargs = validated.model_dump()

            # 执行
            result = await self._run(**kwargs)

            logger.info(f"Tool [{self.name}] completed successfully")
            return {"status": "success", "result": result}

        except ValidationError as e:
            logger.error(f"Tool [{self.name}] validation error: {e}")
            return {"status": "error", "error": f"参数验证失败: {e}"}

        except Exception as e:
            logger.error(f"Tool [{self.name}] execution error: {e}")
            return {"status": "error", "error": str(e)}

    def get_schema(self) -> dict:
        """返回 OpenAI function calling 格式"""
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
            }
        }

        if self.args_schema:
            schema["function"]["parameters"] = self.args_schema.model_json_schema()

        return schema


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [t.get_schema() for t in self._tools.values()]

    def __iter__(self):
        return iter(self._tools.values())


# 全局注册表实例
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry
```

## 注意

- 保持与 OpenAI function calling 格式兼容
- 日志要包含足够的调试信息
- 考虑工具超时机制

```

## 验收标准
- [ ] BaseTool 抽象类定义完整
- [ ] ToolRegistry 支持注册和查询
- [ ] get_schema() 输出符合 OpenAI 格式
- [ ] 错误处理覆盖常见情况
```
