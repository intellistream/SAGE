from dataclasses import dataclass, field

from .quality_label import QualityLabel


@dataclass
class CriticEvaluation:
    """Critic评估结果"""

    label: QualityLabel
    confidence: float  # 0.0-1.0
    reasoning: str
    specific_issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    should_return_to_chief: bool = False
    ready_for_output: bool = False
