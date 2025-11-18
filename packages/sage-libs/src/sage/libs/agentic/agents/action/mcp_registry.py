# refactor_wxh/MemoRAG/packages/sage-libs/src/sage/libs/agentic/agents/action/mcp_registry.py
from __future__ import annotations

from typing import Any


class MCPRegistry:
    """
    MCP 工具注册表：
    - register(tool): tool 需至少具备 name/description/input_schema/call(arguments)
    - describe(): 给 planner 使用的工具清单（MCP 三要素）
    - call(name, arguments): 执行工具
    """

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, tool_obj: Any) -> None:
        if not hasattr(tool_obj, "name") or not hasattr(tool_obj, "call"):
            raise TypeError("Tool must have `name` and `call(arguments)`")
        self._tools[tool_obj.name] = tool_obj

    def describe(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "description": getattr(t, "description", ""),
                "input_schema": getattr(t, "input_schema", {}),
            }
            for name, t in self._tools.items()
        }

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name].call(arguments)

    def execute(self, data: Any = None) -> Any:
        """
        支持两类输入：
        1) None / "describe" / {"op": "describe"} → 返回工具清单（给 planner 用）
        2) {"name": <tool_name>, "arguments": {...}} 或 {"op": "call", "name": ..., "arguments": {...}}
           → 调用对应工具并返回结果
        """
        # 情况 1：描述工具清单
        if (
            data is None
            or data == "describe"
            or (
                isinstance(data, dict)
                and data.get("op", "describe") == "describe"
                and "name" not in data
            )
        ):
            return self.describe()

        # 情况 2：按名调用工具
        if isinstance(data, dict):
            if data.get("op") not in (None, "call", "describe"):
                raise ValueError(f"Unsupported op: {data.get('op')}")
            name = data.get("name")
            arguments = data.get("arguments", {})
            if not isinstance(name, str) or not name:
                raise ValueError("Missing or invalid 'name' when calling a tool.")
            if not isinstance(arguments, dict):
                raise TypeError("'arguments' must be a dict.")
            return self.call(name, arguments)

        raise TypeError(
            "MCPRegistry.execute expects None/'describe' or a dict like "
            "{'name': str, 'arguments': dict} (optionally with 'op': 'call')."
        )
