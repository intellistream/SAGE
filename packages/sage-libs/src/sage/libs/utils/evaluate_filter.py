import json
from typing import List, Union, Set
from sage.core.api.function.filter_function import FilterFunction
from ..context.model_context import ModelContext, QualityLabel


class EvaluateFilter(FilterFunction):
    """
    评估过滤器 - 基于质量标签上下界过滤
    """
    
    def __init__(self, config: dict = None, **kwargs):
        """
        初始化评估过滤器
        
        Args:
            config: 配置字典，支持：
                   - "upper_bound": str - 质量上界标签
                   - "lower_bound": str - 质量下界标签
                   
        质量标签优先级（从高到低）：
        1. COMPLETE_EXCELLENT
        2. COMPLETE_GOOD  
        3. PARTIAL_NEEDS_IMPROVEMENT
        4. INCOMPLETE_MISSING_INFO
        5. FAILED_POOR_QUALITY
        6. ERROR_INVALID
        """
        super().__init__(**kwargs)
        
        if not config:
            config = {}
        
        # 质量标签优先级映射
        self.quality_priority = {
            QualityLabel.COMPLETE_EXCELLENT: 1,
            QualityLabel.COMPLETE_GOOD: 2,
            QualityLabel.PARTIAL_NEEDS_IMPROVEMENT: 3,
            QualityLabel.INCOMPLETE_MISSING_INFO: 4,
            QualityLabel.FAILED_POOR_QUALITY: 5,
            QualityLabel.ERROR_INVALID: 6
        }
        
        # 解析上下界
        self.upper_bound = self._parse_label(config.get("upper_bound"))
        self.lower_bound = self._parse_label(config.get("lower_bound"))
        
        # 计算上下界优先级
        self.upper_priority = self.quality_priority.get(self.upper_bound, 1) if self.upper_bound else 1
        self.lower_priority = self.quality_priority.get(self.lower_bound, 6) if self.lower_bound else 6
    
    def _parse_label(self, label_input) -> QualityLabel:
        """解析质量标签"""
        if not label_input:
            return None
        
        if isinstance(label_input, QualityLabel):
            return label_input
        
        if isinstance(label_input, str):
            try:
                return QualityLabel(label_input)
            except ValueError:
                return None
        
        return None
    
    def execute(self, template: ModelContext) -> bool:
        """执行评估过滤逻辑"""
        evaluation = template.evaluation
        
        # 如果没有评估，返回False
        if not evaluation:
            return False
        
        # 获取当前质量标签的优先级
        current_priority = self.quality_priority.get(evaluation.label, 6)
        
        # 检查是否在上下界范围内
        # 优先级数字越小质量越高，所以要在upper_priority和lower_priority之间
        return self.upper_priority <= current_priority <= self.lower_priority