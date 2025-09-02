# refactor_wxh/MemoRAG/packages/sage-libs/src/sage/libs/agents/action/mcp_registry.py
from __future__ import annotations
from typing import Dict, Any

class MCPRegistry:
    """
    MCP 工具注册表：
    - register(tool): tool 需至少具备 name/description/input_schema/call(arguments)
    - describe(): 给 planner 使用的工具清单（MCP 三要素）
    - call(name, arguments): 执行工具
    """
    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}

    def register(self, tool_obj: Any) -> None:
        if not hasattr(tool_obj, "name") or not hasattr(tool_obj, "call"):
            raise TypeError("Tool must have `name` and `call(arguments)`")
        self._tools[tool_obj.name] = tool_obj

    def describe(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "description": getattr(t, "description", ""),
                "input_schema": getattr(t, "input_schema", {}),
            }
            for name, t in self._tools.items()
        }

    def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name].call(arguments)
