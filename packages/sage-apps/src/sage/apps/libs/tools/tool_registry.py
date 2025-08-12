"""
工具注册表 - 管理和发现工具
"""

from typing import Dict, List, Optional
from .base_tool import BaseTool


class ToolRegistry:
    """工具注册表 - 单例模式管理所有工具"""
    
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """注册一个工具"""
        if not isinstance(tool, BaseTool):
            raise TypeError("Tool must be an instance of BaseTool")
        
        self._tools[tool.tool_name] = tool
    
    def unregister(self, name: str) -> None:
        """取消注册一个工具"""
        if name in self._tools:
            del self._tools[name]
    
    def get(self, name: str) -> Optional[BaseTool]:
        """根据名称获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """列出所有已注册的工具"""
        return list(self._tools.values())
    
    def list_tool_names(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
