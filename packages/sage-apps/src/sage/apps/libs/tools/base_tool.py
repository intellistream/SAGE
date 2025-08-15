"""
工具基类 - 所有工具的基础接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseTool(ABC):
    """工具基类 - 定义所有工具的标准接口"""
    
    def __init__(
        self,
        tool_name: str,
        tool_description: str,
        input_types: List[str] = None,
        output_type: str = "str",
        demo_commands: List[str] = None,
        require_llm_engine: bool = False
    ):
        self.tool_name = tool_name
        self.tool_description = tool_description
        self.input_types = input_types or ["str"]
        self.output_type = output_type
        self.demo_commands = demo_commands or []
        self.require_llm_engine = require_llm_engine
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """执行工具的核心功能"""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取工具元数据"""
        return {
            "name": self.tool_name,
            "description": self.tool_description,
            "input_types": self.input_types,
            "output_type": self.output_type,
            "demo_commands": self.demo_commands,
            "require_llm_engine": self.require_llm_engine
        }
    
    def __str__(self) -> str:
        return f"Tool({self.tool_name})"
    
    def __repr__(self) -> str:
        return f"Tool(name='{self.tool_name}', description='{self.tool_description}')"
