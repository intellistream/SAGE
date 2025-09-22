from enum import Enum


class QualityLabel(Enum):
    """质量评估标签"""
    COMPLETE_EXCELLENT = "complete_excellent"
    COMPLETE_GOOD = "complete_good"
    PARTIAL_NEEDS_IMPROVEMENT = "partial_needs_improvement"
    INCOMPLETE_MISSING_INFO = "incomplete_missing_info"
    FAILED_POOR_QUALITY = "failed_poor_quality"
    ERROR_INVALID = "error_invalid"