from typing import List, Tuple
from sage_core.function.filter_function import FilterFunction
from sage_core.function.map_function import MapFunction
from sage_library.utils.template import AI_Template

class SearchBotFilter(FilterFunction):
    """过滤分配给搜索Bot的任务"""
    def execute(self, data: Tuple[AI_Template, str]) -> bool:
        _, resource_name = data
        return resource_name == "search_bot"

class AnalysisBotFilter(FilterFunction):
    """过滤分配给分析Bot的任务"""
    def execute(self, data: Tuple[AI_Template, str]) -> bool:
        _, resource_name = data
        return resource_name == "analysis_bot"

class ResourceExtractor(MapFunction):
    """提取template用于后续处理"""
    def execute(self, data: Tuple[AI_Template, str]) -> AI_Template:
        template, resource_name = data
        # 可以在这里记录资源分配信息
        if not template.response:
            template.response = f"Allocated to resource: {resource_name}"
        return template