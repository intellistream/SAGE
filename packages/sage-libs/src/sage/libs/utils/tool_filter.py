import json
from typing import List, Union, Set
from sage.core.api.function.filter_function import FilterFunction
from sage.libs.context.model_context import ModelContext, QualityLabel


class ToolFilter(FilterFunction):
    """
    工具过滤器 - 只接受config配置
    """
    
    def __init__(self, config: dict = None, **kwargs):
        """
        初始化工具过滤器
        
        Args:
            config: 配置字典，支持：
                   - "tools": str | List[str] | JSON字符串 - 目标工具列表
                   - "exclude": str | List[str] | JSON字符串 - 排除工具列表  
                   - "include_unknown": bool - 是否接受无工具名的模板
        """
        super().__init__(**kwargs)
        
        if not config:
            config = {}
        
        self.target_tools: Set[str] = self._parse_tools(config.get("tools"))
        self.exclude_tools: Set[str] = self._parse_tools(config.get("exclude"))
        self.include_unknown: bool = config.get("include_unknown", False)
    
    def _parse_tools(self, tools_input) -> Set[str]:
        """解析工具输入为工具集合"""
        if not tools_input:
            return set()
        
        if isinstance(tools_input, (list, set)):
            return set(str(tool) for tool in tools_input)
        
        if isinstance(tools_input, str):
            # JSON字符串
            if tools_input.strip().startswith('['):
                try:
                    parsed = json.loads(tools_input)
                    return set(str(tool) for tool in parsed)
                except json.JSONDecodeError:
                    pass
            
            # 逗号分隔
            if ',' in tools_input:
                return {tool.strip() for tool in tools_input.split(',') if tool.strip()}
            
            # 单个工具
            return {tools_input.strip()}
        
        return set()
    
    def execute(self, template: ModelContext) -> bool:
        """执行工具过滤逻辑"""
        tool_name = template.tool_name
        
        # 排除列表检查
        if tool_name and tool_name in self.exclude_tools:
            return False
        
        # 无工具名处理
        if not tool_name:
            return self.include_unknown
        
        # 目标工具检查
        if self.target_tools:
            return tool_name in self.target_tools
        
        # 默认接受（如果没有指定目标工具且不在排除列表中）
        return True