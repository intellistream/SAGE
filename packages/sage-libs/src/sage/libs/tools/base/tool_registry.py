from .base_tool import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具实例"""
        if tool.tool_name is None:
            raise ValueError("Tool must have a non-None tool_name to be registered")
        self._tools[tool.tool_name] = tool

    def unregister(self, name: str) -> None:
        """移除一个工具"""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> dict[str, BaseTool]:
        """返回所有已注册工具的字典"""
        return dict(self._tools)

    def clear(self) -> None:
        """清空所有注册工具"""
        self._tools.clear()
