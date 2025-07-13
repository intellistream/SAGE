from typing import List, Tuple
from sage_core.function.filter_function import FilterFunction
from sage_core.function.map_function import MapFunction
from sage_library.utils.template import AI_Template
from ..agent.critic_bot import CriticEvaluation, QualityLabel

class TemplateExtractor(MapFunction):
    """从critic结果中提取AI_Template用于输出"""
    
    def execute(self, data: Tuple[AI_Template, CriticEvaluation]) -> AI_Template:
        template, evaluation = data
        
        # 可以在这里添加最终的输出格式化
        if not template.response:
            template.response = "Processing completed with critic evaluation."
        
        return template
    
    


class ReadyForOutputFilter(FilterFunction):
    """过滤可以直接输出的高质量结果"""
    
    def execute(self, data: Tuple[AI_Template, CriticEvaluation]) -> bool:
        template, evaluation = data
        return evaluation.ready_for_output and evaluation.label in [
            QualityLabel.COMPLETE_EXCELLENT,
            QualityLabel.COMPLETE_GOOD
        ]

class NeedsReprocessingFilter(FilterFunction):
    """过滤需要返回给Chief重新处理的结果"""
    
    def execute(self, data: Tuple[AI_Template, CriticEvaluation]) -> bool:
        template, evaluation = data
        return evaluation.should_return_to_chief

class PartialQualityFilter(FilterFunction):
    """过滤部分质量可接受的结果（可能需要轻微改进）"""
    
    def execute(self, data: Tuple[AI_Template, CriticEvaluation]) -> bool:
        template, evaluation = data
        return evaluation.label == QualityLabel.PARTIAL_NEEDS_IMPROVEMENT

class FailedQualityFilter(FilterFunction):
    """过滤质量差需要重新处理的结果"""
    
    def execute(self, data: Tuple[AI_Template, CriticEvaluation]) -> bool:
        template, evaluation = data
        return evaluation.label in [
            QualityLabel.FAILED_POOR_QUALITY,
            QualityLabel.ERROR_INVALID
        ]

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